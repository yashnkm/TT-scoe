import logging
from ortools.sat.python import cp_model
from typing import Dict, List, Optional
from models import data_manager

class SimpleTimetableSolver:
    """Simplified timetable generator using OR-Tools CP-SAT solver"""
    
    def __init__(self):
        self.model = None
        self.solver = None
        self.variables = {}
        
    def generate_timetable(self, semester_mode: Optional[str] = None) -> Dict:
        """Generate timetable based on actual data - simple and straightforward"""
        try:
            # Load current data
            structure = data_manager.get_academic_structure()
            subjects = data_manager.get_subjects()
            faculty = data_manager.get_faculty()
            rooms = data_manager.get_rooms()
            
            # Validate data exists
            if not subjects or not faculty or not rooms:
                return {"error": "Please configure subjects, faculty, and rooms first."}
            
            # Initialize solver
            self.model = cp_model.CpModel()
            self.variables = {}
            
            # Academic structure
            years = list(range(1, structure.get("years", 4) + 1))
            divisions = ["A", "B"][:structure.get("divisions_per_year", 2)]
            batches = list(range(1, structure.get("batches_per_division", 4) + 1))
            days = structure.get("days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
            time_slots = structure.get("time_slots", ["09:15-10:15", "10:15-11:15"])
            
            # Get session durations from structure
            theory_duration = structure.get("theory_duration", 60)  # minutes
            practical_duration = structure.get("practical_duration", 120)  # minutes
            
            # Assume each time slot is 60 minutes (standard)
            slot_duration = 60  # minutes
            practical_slots_needed = practical_duration // slot_duration  # Should be 2 for 120 minutes
            
            # Define break periods (used to prevent practicals from spanning breaks)
            breaks = {
                "11:15-11:30": {"type": "recess", "label": "Short Break"},
                "13:30-14:30": {"type": "lunch", "label": "Lunch Break"}
            }
            
            # Filter subjects by semester if specified
            if semester_mode:
                selected_sem = 1 if semester_mode == 'odd' else 2
                subjects = [s for s in subjects if s.get("semester") == selected_sem]
            
            # Build list of required classes (subject-year-division-semester combinations)
            required_classes = self._get_required_classes(subjects, years, divisions)
            
            if not required_classes:
                return {"error": "No classes to schedule for selected semester."}
            
            # Create scheduling variables
            sessions = self._create_session_variables(required_classes, days, time_slots, practical_slots_needed, breaks)
            
            if not sessions:
                return {"error": "Failed to create scheduling variables."}
            
            # Add constraints
            self._add_hour_constraints(sessions, required_classes, practical_slots_needed, slot_duration)
            self._add_faculty_constraints(sessions, faculty, days, time_slots, practical_slots_needed)
            self._add_room_constraints(sessions, rooms, days, time_slots, practical_slots_needed)
            self._add_no_conflict_constraints(sessions, days, time_slots, practical_slots_needed)
            self._add_max_practical_per_day_constraint(sessions, years, divisions, days)
            
            # Solve
            self.solver = cp_model.CpSolver()
            self.solver.parameters.max_time_in_seconds = 20.0
            self.solver.parameters.num_search_workers = 4
            status = self.solver.Solve(self.model)
            
            if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                return self._build_timetable(sessions, structure, required_classes)
            else:
                return {"error": "Could not generate feasible timetable. Check faculty/room availability."}
                
        except Exception as e:
            logging.error(f"Timetable generation error: {str(e)}")
            return {"error": f"Error: {str(e)}"}
    
    def _get_required_classes(self, subjects, years, divisions):
        """Get list of all classes that need to be scheduled"""
        faculty = data_manager.get_faculty()
        required = []
        
        for subject in subjects:
            subject_year = subject.get("year", 0)
            subject_semester = subject.get("semester", 1)
            subject_type = subject.get("type", "theory")
            
            # Only process subjects for configured years
            if subject_year not in years:
                continue
            
            # Check if any faculty teaches this subject
            faculty_for_subject = self._get_faculty_for_subject(subject["id"], faculty, divisions)
            
            if not faculty_for_subject:
                continue  # Skip if no faculty assigned
            
            # Add class for each available division
            for division in divisions:
                required.append({
                    "subject_id": subject["id"],
                    "subject": subject,
                    "year": subject_year,
                    "division": division,
                    "semester": subject_semester,
                    "type": subject_type
                })
        
        return required
    
    def _get_faculty_for_subject(self, subject_id, faculty_list, divisions):
        """Get list of faculty who can teach a subject"""
        faculty_for_subject = []
        
        for fac in faculty_list:
            subjects = fac.get("subjects", []) or []
            
            # Handle legacy format (list of subject IDs)
            if subjects and not isinstance(subjects[0], dict):
                if subject_id in subjects:
                    faculty_for_subject.append(fac)
            else:
                # Handle new format (list of dicts with subject_id and divisions)
                for assignment in subjects:
                    if assignment.get("subject_id") == subject_id:
                        allowed_divs = assignment.get("divisions", [])
                        # If no divisions specified, faculty can teach all divisions
                        if not allowed_divs:
                            faculty_for_subject.append(fac)
                            break
        
        return faculty_for_subject
    
    def _create_session_variables(self, required_classes, days, time_slots, practical_slots_needed=2, breaks=None):
        """Create boolean variables for each possible session"""
        if breaks is None:
            breaks = {}
        
        sessions = []
        
        # Helper function to check if two consecutive slots have a break between them
        def has_break_between_slots(slot1, slot2):
            """Check if there's a break period between two time slots"""
            # Extract end time of slot1 and start time of slot2
            slot1_end = slot1.split('-')[1]
            slot2_start = slot2.split('-')[0]
            
            # Check if any break period falls between these times
            for break_slot, break_info in breaks.items():
                break_start, break_end = break_slot.split('-')
                # If break starts after slot1 ends and ends before slot2 starts, there's a break
                if slot1_end <= break_start and break_end <= slot2_start:
                    return True
            return False
        
        for req_class in required_classes:
            subject_type = req_class["subject"].get("type", "theory")
            
            for day in days:
                # For practical sessions, only create variables for slots where a practical CAN start
                # (i.e., not the last slot if we need multiple slots)
                max_start_slot = len(time_slots) if subject_type == "theory" else len(time_slots) - practical_slots_needed + 1
                
                for slot_idx in range(max_start_slot):
                    time_slot = time_slots[slot_idx]
                    
                    # For practical sessions, check if consecutive slots would span across a break
                    if subject_type == "practical":
                        # Check if we can get all required consecutive slots
                        can_span = True
                        spanned_slots = [time_slot]
                        
                        for i in range(1, practical_slots_needed):
                            if slot_idx + i >= len(time_slots):
                                can_span = False
                                break
                            
                            next_slot = time_slots[slot_idx + i]
                            prev_slot = time_slots[slot_idx + i - 1]
                            
                            # Check if there's a break between consecutive slots
                            if has_break_between_slots(prev_slot, next_slot):
                                can_span = False
                                break
                            
                            spanned_slots.append(next_slot)
                        
                        # Skip creating variable if practical would span across a break
                        if not can_span or len(spanned_slots) < practical_slots_needed:
                            continue
                    else:
                        # For theory sessions, just use the single slot
                        spanned_slots = [time_slot]
                    
                    var_name = f"{req_class['subject_id']}_{req_class['year']}_{req_class['division']}_{day}_{time_slot}"
                    var = self.model.NewBoolVar(var_name)
                    self.variables[var_name] = var
                    
                    sessions.append({
                        "variable": var,
                        "subject_id": req_class["subject_id"],
                        "subject": req_class["subject"],
                        "year": req_class["year"],
                        "division": req_class["division"],
                        "day": day,
                        "time_slot": time_slot,  # Starting time slot
                        "spanned_slots": spanned_slots,  # All slots this session occupies
                        "slot_index": slot_idx  # Index of starting slot
                    })
        
        return sessions
    
    def _add_hour_constraints(self, sessions, required_classes, practical_slots_needed=2, slot_duration=60):
        """Ensure each class is scheduled the required hours per week"""
        for req_class in required_classes:
            hours_per_week = req_class["subject"].get("hours_per_week", 3)
            subject_type = req_class["subject"].get("type", "theory")
            
            # For practicals, calculate how many sessions are needed
            # If practical_duration is 120 minutes and each slot is 60 minutes,
            # then each practical session spans 2 slots, so we need hours_per_week sessions
            # For theory, each session is 1 slot, so we need hours_per_week slots
            if subject_type == "practical":
                # Each practical session spans practical_slots_needed slots
                # So we need hours_per_week practical sessions (not slots)
                sessions_needed = hours_per_week
            else:
                # For theory, each session is 1 slot
                sessions_needed = hours_per_week
            
            class_sessions = [
                s["variable"] for s in sessions
                if s["subject_id"] == req_class["subject_id"] and
                   s["year"] == req_class["year"] and
                   s["division"] == req_class["division"]
            ]
            
            if class_sessions:
                self.model.Add(sum(class_sessions) == sessions_needed)
    
    def _add_faculty_constraints(self, sessions, faculty_list, days, time_slots, practical_slots_needed=2):
        """Ensure each faculty member teaches only one class per time slot"""
        for fac in faculty_list:
            for day in days:
                for slot_idx, time_slot in enumerate(time_slots):
                    # Find all sessions this faculty can teach that occupy this time slot
                    faculty_sessions = []
                    
                    for s in sessions:
                        if s["day"] == day and self._faculty_can_teach(fac, s):
                            # Check if this session occupies the current time slot
                            if time_slot in s.get("spanned_slots", [s["time_slot"]]):
                                faculty_sessions.append(s["variable"])
                    
                    if faculty_sessions:
                        self.model.Add(sum(faculty_sessions) <= 1)
    
    def _faculty_can_teach(self, faculty, session):
        """Check if faculty can teach this session"""
        subjects = faculty.get("subjects", []) or []
        
        # Legacy format
        if subjects and not isinstance(subjects[0], dict):
            return session["subject_id"] in subjects
        
        # New format
        for assignment in subjects:
            if assignment.get("subject_id") == session["subject_id"]:
                allowed_divs = assignment.get("divisions", [])
                if not allowed_divs:
                    return True
                # Convert division letter to number
                div_map = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}
                return div_map.get(session["division"]) in allowed_divs
        
        return False
    
    def _add_room_constraints(self, sessions, rooms_list, days, time_slots, practical_slots_needed=2):
        """Ensure room capacity is not exceeded"""
        classrooms = [r for r in rooms_list if r.get("type") in ["classroom", "both"]]
        labs = [r for r in rooms_list if r.get("type") in ["lab", "both"]]
        
        for day in days:
            for slot_idx, time_slot in enumerate(time_slots):
                # Theory sessions that occupy this slot
                theory_sessions = []
                for s in sessions:
                    if (s["day"] == day and
                        s["subject"].get("type") == "theory" and
                        time_slot in s.get("spanned_slots", [s["time_slot"]])):
                        theory_sessions.append(s["variable"])
                
                if theory_sessions and classrooms:
                    self.model.Add(sum(theory_sessions) <= len(classrooms))
                
                # Practical sessions that occupy this slot
                practical_sessions = []
                for s in sessions:
                    if (s["day"] == day and
                        s["subject"].get("type") == "practical" and
                        time_slot in s.get("spanned_slots", [s["time_slot"]])):
                        practical_sessions.append(s["variable"])
                
                if practical_sessions and labs:
                    self.model.Add(sum(practical_sessions) <= len(labs))
    
    def _add_no_conflict_constraints(self, sessions, days, time_slots, practical_slots_needed=2):
        """Ensure students don't have conflicting classes"""
        for year in range(1, 5):
            for division in ["A", "B"]:
                for day in days:
                    for slot_idx, time_slot in enumerate(time_slots):
                        # Find all sessions for this division that occupy this time slot
                        div_sessions = []
                        for s in sessions:
                            if (s["year"] == year and
                                s["division"] == division and
                                s["day"] == day and
                                time_slot in s.get("spanned_slots", [s["time_slot"]])):
                                div_sessions.append(s["variable"])
                        
                        if div_sessions:
                            # Only one class per division-time slot
                            self.model.Add(sum(div_sessions) <= 1)
    
    def _add_max_practical_per_day_constraint(self, sessions, years, divisions, days):
        """Ensure no more than 2 practical sessions (120min each) per day per division"""
        for year in years:
            for division in divisions:
                for day in days:
                    # Find all practical sessions for this division on this day
                    practical_sessions = [
                        s["variable"] for s in sessions
                        if (s["year"] == year and
                            s["division"] == division and
                            s["day"] == day and
                            s["subject"].get("type") == "practical")
                    ]
                    
                    if practical_sessions:
                        # Maximum 2 practical sessions per day per division
                        self.model.Add(sum(practical_sessions) <= 2)
    
    def _build_timetable(self, sessions, structure, required_classes):
        """Extract solution and build timetable"""
        timetable = {}
        
        years = list(range(1, structure.get("years", 4) + 1))
        divisions = ["A", "B"][:structure.get("divisions_per_year", 2)]
        days = structure.get("days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
        time_slots = structure.get("time_slots", ["09:15-10:15", "10:15-11:15"])
        
        # Define break periods
        breaks = {
            "11:15-11:30": {"type": "recess", "label": "Short Break"},
            "13:30-14:30": {"type": "lunch", "label": "Lunch Break"}
        }
        
        # Create extended time slots list with breaks inserted
        extended_time_slots = self._insert_breaks_into_time_slots(time_slots, breaks)
        
        # Initialize timetable structure with extended time slots
        for year in years:
            for division in divisions:
                key = f"Year_{year}_Division_{division}"
                timetable[key] = {day: {slot: None for slot in extended_time_slots} for day in days}
                
                # Add break periods for all days
                for day in days:
                    for break_slot, break_info in breaks.items():
                        timetable[key][day][break_slot] = {
                            "subject": break_info["label"],
                            "type": "break",
                            "faculty": "",
                            "room": "",
                            "code": "",
                            "break_type": break_info["type"]
                        }
        
        # Fill scheduled classes
        for session in sessions:
            if self.solver.Value(session["variable"]) == 1:
                year = session["year"]
                division = session["division"]
                day = session["day"]
                subject = session["subject"]
                subject_type = subject.get("type", "theory")
                
                # Get faculty and room
                faculty_name = self._get_faculty_name(subject["id"], division)
                room = self._get_room_for_type(subject_type)
                
                key = f"Year_{year}_Division_{division}"
                
                # Get all slots this session spans
                spanned_slots = session.get("spanned_slots", [session["time_slot"]])
                
                # For practicals, assign to all spanned slots with span metadata
                # For theory, assign to the single slot
                total_span = len(spanned_slots)
                for slot_pos, slot in enumerate(spanned_slots):
                    # Only assign if slot exists in extended time slots (not a break slot)
                    if slot in extended_time_slots:
                        session_data = {
                            "subject": subject["name"],
                            "type": subject_type,
                            "faculty": faculty_name,
                            "room": room,
                            "code": subject.get("code", "")
                        }
                        # Add span metadata for multi-slot sessions (practicals)
                        if total_span > 1:
                            session_data["span"] = total_span
                            if slot_pos == 0:
                                session_data["slot_position"] = "start"
                            else:
                                session_data["slot_position"] = "continuation"
                        timetable[key][day][slot] = session_data
        
        return {"timetable": timetable, "success": True}
    
    def _insert_breaks_into_time_slots(self, time_slots, breaks):
        """Insert break periods into time slots list in chronological order"""
        # Define break periods
        break_slots = list(breaks.keys())
        
        # Combine all slots and breaks, then sort chronologically
        all_slots = list(time_slots) + break_slots
        
        # Sort by start time
        def get_start_time(slot):
            return slot.split('-')[0]
        
        all_slots.sort(key=get_start_time)
        
        return all_slots
    
    def _get_faculty_name(self, subject_id, division):
        """Get faculty name for a subject and division"""
        faculty = data_manager.get_faculty()
        div_map = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}
        div_num = div_map.get(division, 1)
        
        for fac in faculty:
            subjects = fac.get("subjects", []) or []
            
            # Legacy format
            if subjects and not isinstance(subjects[0], dict):
                if subject_id in subjects:
                    return fac.get("name", "Unassigned")
            else:
                # New format
                for assignment in subjects:
                    if assignment.get("subject_id") == subject_id:
                        allowed_divs = assignment.get("divisions", [])
                        if not allowed_divs or div_num in allowed_divs:
                            return fac.get("name", "Unassigned")
        
        return "Unassigned"
    
    def _get_room_for_type(self, session_type):
        """Get a room for the session type"""
        rooms = data_manager.get_rooms()
        
        for room in rooms:
            if session_type == "theory" and room.get("type") in ["classroom", "both"]:
                return room.get("name", "Room TBD")
            elif session_type == "practical" and room.get("type") in ["lab", "both"]:
                return room.get("name", "Lab TBD")
        
        return "TBD"


# Global solver instance
timetable_solver = SimpleTimetableSolver()
