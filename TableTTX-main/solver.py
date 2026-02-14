import logging
from ortools.sat.python import cp_model
from typing import Dict, List, Optional
from models import data_manager

logger = logging.getLogger(__name__)

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

            # --- Basic data validation ---
            missing = []
            if not subjects:
                missing.append("subjects")
            if not faculty:
                missing.append("faculty")
            if not rooms:
                missing.append("rooms")
            if missing:
                return {"error": f"Please configure {', '.join(missing)} first."}

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
            practical_duration = structure.get("practical_duration", 120)  # minutes

            # Assume each time slot is 60 minutes (standard)
            slot_duration = 60  # minutes
            practical_slots_needed = practical_duration // slot_duration  # Should be 2 for 120 minutes

            # Define break periods (used to prevent practicals from spanning breaks)
            breaks = {
                "11:15-11:30": {"type": "recess", "label": "Short Break"},
                "13:30-14:30": {"type": "lunch", "label": "Lunch Break"}
            }

            total_slots = len(time_slots) * len(days)
            logger.info(f"=== Timetable Generation Started ===")
            logger.info(f"Semester: {semester_mode or 'all'} | Years: {years} | Divisions: {divisions} | Batches: {len(batches)}")
            logger.info(f"Schedule: {len(days)} days x {len(time_slots)} slots = {total_slots} slots/week")

            # Filter subjects by semester if specified
            if semester_mode:
                selected_sem = 1 if semester_mode == 'odd' else 2
                all_count = len(subjects)
                subjects = [s for s in subjects if s.get("semester") == selected_sem]
                logger.info(f"Semester filter: {all_count} total subjects -> {len(subjects)} for semester {selected_sem}")

            if not subjects:
                return {"error": f"No subjects found for {'odd' if semester_mode == 'odd' else 'even'} semester. Check that subjects have the correct semester value (1 for odd, 2 for even)."}

            # Build list of required classes
            required_classes = self._get_required_classes(subjects, years, divisions, batches)

            if not required_classes:
                # Detailed diagnosis: find why no classes were created
                skipped_reasons = self._diagnose_no_classes(subjects, years, divisions, batches, faculty)
                return {"error": f"No classes to schedule. {skipped_reasons}"}

            # --- Pre-solve feasibility validation ---
            validation_result = self._validate_feasibility(
                required_classes, subjects, faculty, rooms, years, divisions, batches,
                days, time_slots, practical_slots_needed, breaks
            )
            if validation_result.get("error"):
                return validation_result

            # Create scheduling variables
            sessions = self._create_session_variables(required_classes, days, time_slots, practical_slots_needed, breaks)

            if not sessions:
                return {"error": "Failed to create scheduling variables. Check that time slots are configured correctly."}

            logger.info(f"Created {len(sessions)} scheduling variables for {len(required_classes)} required classes")

            # Add constraints
            self._add_hour_constraints(sessions, required_classes, practical_slots_needed, slot_duration)
            self._add_faculty_constraints(sessions, faculty, days, time_slots, practical_slots_needed)
            self._add_room_constraints(sessions, rooms, days, time_slots, practical_slots_needed)
            self._add_no_conflict_constraints(sessions, days, time_slots, practical_slots_needed, batches)
            self._add_max_practical_per_day_constraint(sessions, years, divisions, batches, days)

            # Solve
            self.solver = cp_model.CpSolver()
            self.solver.parameters.max_time_in_seconds = 120.0
            self.solver.parameters.num_search_workers = 4
            logger.info("Solving... (timeout: 120s)")
            status = self.solver.Solve(self.model)

            status_name = {
                cp_model.OPTIMAL: "OPTIMAL",
                cp_model.FEASIBLE: "FEASIBLE",
                cp_model.INFEASIBLE: "INFEASIBLE",
                cp_model.MODEL_INVALID: "MODEL_INVALID",
                cp_model.UNKNOWN: "UNKNOWN"
            }.get(status, f"STATUS_{status}")
            logger.info(f"Solver result: {status_name} (wall time: {self.solver.WallTime():.1f}s)")

            if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                result = self._build_timetable(sessions, structure, required_classes, batches)
                # Attach warnings if any
                if validation_result.get("warnings"):
                    result["warnings"] = validation_result["warnings"]
                return result

            # --- Detailed failure diagnosis ---
            if status == cp_model.INFEASIBLE:
                diagnosis = self._diagnose_infeasibility(
                    required_classes, rooms, years, divisions, batches,
                    days, time_slots, practical_slots_needed
                )
                return {"error": f"Timetable is INFEASIBLE — no valid schedule exists with current data.\n\n{diagnosis}"}

            if status == cp_model.UNKNOWN:
                return {"error": f"Solver timed out after {self.solver.WallTime():.0f}s without finding a solution. The problem may be too complex. Try reducing practical hours for high-hour subjects (e.g., Project Stage 2: 10hrs)."}

            return {"error": f"Solver returned unexpected status: {status_name}. Please check your data configuration."}

        except Exception as e:
            logger.error(f"Timetable generation error: {str(e)}", exc_info=True)
            return {"error": f"Error: {str(e)}"}

    def _diagnose_no_classes(self, subjects, years, divisions, batches, faculty):
        """Diagnose why no required classes were created."""
        issues = []

        year_mismatch = []
        no_faculty = []

        for subject in subjects:
            subj_year = subject.get("year", 0)
            subj_name = subject.get("name", "Unknown")
            subj_id = subject.get("id")

            if subj_year not in years:
                year_mismatch.append(f"'{subj_name}' (Year {subj_year})")
                continue

            fac_list = self._get_faculty_for_subject(subj_id, faculty, divisions)
            if not fac_list:
                no_faculty.append(f"'{subj_name}' (ID: {subj_id})")

        if year_mismatch:
            issues.append(f"Subjects outside configured years ({years}): {', '.join(year_mismatch[:5])}")
        if no_faculty:
            issues.append(f"Subjects with no faculty assigned: {', '.join(no_faculty[:5])}")
        if not year_mismatch and not no_faculty:
            issues.append("All subjects were filtered out — check year and faculty configuration.")

        return " | ".join(issues)

    def _validate_feasibility(self, required_classes, subjects, faculty, rooms, years,
                              divisions, batches, days, time_slots, practical_slots_needed, breaks):
        """Pre-solve validation — catch impossible scenarios early with clear messages."""
        warnings = []
        errors = []

        num_labs = len([r for r in rooms if r.get("type") in ["lab", "both"]])
        num_classrooms = len([r for r in rooms if r.get("type") in ["classroom", "both"]])
        total_slots = len(time_slots) * len(days)
        num_batches_total = len(years) * len(divisions) * len(batches)

        logger.info(f"Resources: {num_classrooms} classrooms, {num_labs} labs, {total_slots} slots/week")

        # --- 1. Check subjects without faculty ---
        subjects_no_faculty = []
        for subj in subjects:
            fac = self._get_faculty_for_subject(subj["id"], faculty, divisions)
            if not fac:
                subjects_no_faculty.append(subj.get("name", f"ID:{subj['id']}"))
        if subjects_no_faculty:
            warnings.append(f"Subjects with no faculty (skipped): {', '.join(subjects_no_faculty)}")
            logger.warning(f"Skipped subjects (no faculty): {subjects_no_faculty}")

        # --- 2. Lab capacity analysis ---
        total_practical_slots = 0
        practical_by_year = {}
        high_hour_practicals = []

        for rc in required_classes:
            if rc["type"] != "practical":
                continue
            hours = rc["subject"].get("hours_per_week", 0)
            if hours < practical_slots_needed:
                sessions_needed = 1
                span = hours
            else:
                sessions_needed = hours // practical_slots_needed
                span = practical_slots_needed

            slots_used = sessions_needed * span
            total_practical_slots += slots_used

            year = rc["year"]
            practical_by_year.setdefault(year, 0)
            practical_by_year[year] += slots_used

            if hours >= 8:
                high_hour_practicals.append(
                    f"'{rc['subject']['name']}' (Year {year}, {hours}hrs → {sessions_needed} sessions/batch)"
                )

        lab_capacity = num_labs * total_slots
        lab_utilization = (total_practical_slots / lab_capacity * 100) if lab_capacity > 0 else 999

        logger.info(f"Lab demand: {total_practical_slots} lab-slots needed / {lab_capacity} available ({lab_utilization:.1f}% utilization)")
        for yr, slots in sorted(practical_by_year.items()):
            logger.info(f"  Year {yr}: {slots} lab-slots")

        if high_hour_practicals:
            warnings.append(f"High-hour practicals (may cause scheduling issues): {'; '.join(set(high_hour_practicals))}")

        if lab_utilization > 100:
            errors.append(
                f"Lab capacity EXCEEDED: Need {total_practical_slots} lab-slots but only {lab_capacity} available "
                f"({lab_utilization:.0f}% utilization). "
                f"You have {num_labs} labs and {total_slots} slots/week. "
                f"Reduce practical hours or add more labs."
            )
        elif lab_utilization > 85:
            warnings.append(
                f"Lab utilization very high ({lab_utilization:.0f}%). "
                f"Need {total_practical_slots}/{lab_capacity} lab-slots. "
                f"Solver may fail or take long. Consider reducing high-hour practicals."
            )

        # --- 3. Classroom capacity analysis ---
        total_theory_sessions = 0
        theory_by_year = {}
        for rc in required_classes:
            if rc["type"] in ["theory", "tutorial"]:
                hours = rc["subject"].get("hours_per_week", 0)
                total_theory_sessions += hours
                year = rc["year"]
                theory_by_year.setdefault(year, 0)
                theory_by_year[year] += hours

        classroom_capacity = num_classrooms * total_slots
        classroom_util = (total_theory_sessions / classroom_capacity * 100) if classroom_capacity > 0 else 999

        logger.info(f"Classroom demand: {total_theory_sessions} sessions / {classroom_capacity} available ({classroom_util:.1f}%)")

        if classroom_util > 100:
            errors.append(
                f"Classroom capacity EXCEEDED: Need {total_theory_sessions} theory sessions but only "
                f"{classroom_capacity} classroom-slots available ({num_classrooms} classrooms x {total_slots} slots). "
                f"Add more classrooms or reduce theory hours."
            )

        # --- 4. Per-batch slot feasibility ---
        for year in years:
            for div in divisions:
                theory_hrs = 0
                prac_hrs_per_batch = 0
                for rc in required_classes:
                    if rc["year"] != year or rc["division"] != div:
                        continue
                    hours = rc["subject"].get("hours_per_week", 0)
                    if rc["type"] in ["theory", "tutorial"]:
                        theory_hrs += hours
                    elif rc["type"] == "practical" and rc.get("batch") == batches[0]:
                        # Count for one batch (all batches have same load)
                        if hours < practical_slots_needed:
                            prac_hrs_per_batch += hours
                        else:
                            prac_hrs_per_batch += (hours // practical_slots_needed) * practical_slots_needed

                total_per_batch = theory_hrs + prac_hrs_per_batch
                if total_per_batch > total_slots:
                    errors.append(
                        f"Year {year} Division {div}: Each batch needs {total_per_batch} slots/week "
                        f"({theory_hrs} theory + {prac_hrs_per_batch} practical) but only {total_slots} slots available. "
                        f"Reduce subject hours for this year."
                    )
                elif total_per_batch > total_slots * 0.9:
                    warnings.append(
                        f"Year {year} Division {div}: Very tight — {total_per_batch}/{total_slots} slots per batch "
                        f"({theory_hrs} theory + {prac_hrs_per_batch} practical). May be hard to schedule."
                    )

        # --- 5. Faculty overload check ---
        for fac in faculty:
            fac_name = fac.get("name", "Unknown")
            theory_load = 0
            fac_subjects = fac.get("subjects", []) or []

            for assignment in fac_subjects:
                if isinstance(assignment, dict):
                    sid = assignment.get("subject_id")
                else:
                    sid = assignment

                for rc in required_classes:
                    if rc["subject_id"] == sid and rc["type"] in ["theory", "tutorial"]:
                        # Check division match
                        if isinstance(assignment, dict):
                            allowed_divs = assignment.get("divisions", [])
                            div_map = {"A": 1, "B": 2, "C": 3, "D": 4}
                            if allowed_divs and div_map.get(rc["division"]) not in allowed_divs:
                                continue
                        theory_load += rc["subject"].get("hours_per_week", 0)

            if theory_load > total_slots:
                errors.append(
                    f"Faculty '{fac_name}' has {theory_load} theory hours/week but only {total_slots} slots exist. "
                    f"Reduce their teaching load."
                )
            elif theory_load > total_slots * 0.7:
                warnings.append(f"Faculty '{fac_name}' has heavy theory load: {theory_load}/{total_slots} slots.")

        # --- Return result ---
        if errors:
            error_msg = "Pre-solve validation failed:\n\n" + "\n\n".join(f"• {e}" for e in errors)
            if warnings:
                error_msg += "\n\nWarnings:\n" + "\n".join(f"  ⚠ {w}" for w in warnings)
            return {"error": error_msg}

        if warnings:
            logger.warning(f"Validation warnings: {warnings}")

        return {"warnings": warnings if warnings else None}

    def _diagnose_infeasibility(self, required_classes, rooms, years, divisions, batches,
                                days, time_slots, practical_slots_needed):
        """Generate detailed diagnosis when solver returns INFEASIBLE."""
        num_labs = len([r for r in rooms if r.get("type") in ["lab", "both"]])
        num_classrooms = len([r for r in rooms if r.get("type") in ["classroom", "both"]])
        total_slots = len(time_slots) * len(days)

        lines = ["Diagnosis:"]

        # Lab usage breakdown
        total_prac_slots = 0
        year_prac = {}
        worst_subjects = []
        for rc in required_classes:
            if rc["type"] != "practical":
                continue
            hours = rc["subject"].get("hours_per_week", 0)
            sessions = max(1, hours // practical_slots_needed) if hours >= practical_slots_needed else 1
            span = practical_slots_needed if hours >= practical_slots_needed else hours
            slots = sessions * span
            total_prac_slots += slots
            yr = rc["year"]
            year_prac.setdefault(yr, 0)
            year_prac[yr] += slots
            if hours >= 6:
                worst_subjects.append(f"{rc['subject']['name']} (Year {yr}, {hours}hrs = {sessions} sessions/batch)")

        lab_cap = num_labs * total_slots
        util = (total_prac_slots / lab_cap * 100) if lab_cap > 0 else 0

        lines.append(f"• Lab utilization: {total_prac_slots}/{lab_cap} slots ({util:.0f}%) — {'OVER CAPACITY' if util > 100 else 'VERY TIGHT' if util > 80 else 'OK'}")

        for yr in sorted(year_prac):
            lines.append(f"  Year {yr}: {year_prac[yr]} lab-slots")

        if worst_subjects:
            lines.append(f"• High-hour practicals causing bottleneck: {', '.join(set(worst_subjects))}")

        # Suggestion
        lines.append("")
        lines.append("Suggestions:")
        if util > 85:
            lines.append("  1. Reduce hours for high-hour practical subjects (e.g., Project Stage)")
            lines.append("  2. Change project-type subjects from 'practical' to 'tutorial' (no lab needed)")
            lines.append("  3. Add more lab rooms")
        else:
            lines.append("  1. Check if faculty are overloaded (teaching too many subjects)")
            lines.append("  2. Check for subjects that need more slots than available per week")
            lines.append("  3. Try increasing solver timeout")

        return "\n".join(lines)

    def _get_required_classes(self, subjects, years, divisions, batches):
        """Get list of all classes that need to be scheduled.
        Theory: division-level entries.
        Practicals: batch-level entries (one per batch per division).
        """
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

            for division in divisions:
                if subject_type == "practical":
                    # Create one entry per batch for practicals
                    for batch in batches:
                        required.append({
                            "subject_id": subject["id"],
                            "subject": subject,
                            "year": subject_year,
                            "division": division,
                            "batch": batch,
                            "semester": subject_semester,
                            "type": "practical"
                        })
                else:
                    # Theory/tutorial: division-level (all batches together)
                    required.append({
                        "subject_id": subject["id"],
                        "subject": subject,
                        "year": subject_year,
                        "division": division,
                        "batch": None,
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
                        # Faculty teaches this subject (divisions checked later during assignment)
                        faculty_for_subject.append(fac)
                        break

        return faculty_for_subject

    def _create_session_variables(self, required_classes, days, time_slots, practical_slots_needed=2, breaks=None):
        """Create boolean variables for each possible session.
        Theory: variable name {subj}_{year}_{div}_{day}_{slot}
        Practical: variable name {subj}_{year}_{div}_B{batch}_{day}_{slot}
        """
        if breaks is None:
            breaks = {}

        sessions = []

        def has_break_between_slots(slot1, slot2):
            """Check if there's a break period between two time slots"""
            slot1_end = slot1.split('-')[1]
            slot2_start = slot2.split('-')[0]
            for break_slot, break_info in breaks.items():
                break_start, break_end = break_slot.split('-')
                if slot1_end <= break_start and break_end <= slot2_start:
                    return True
            return False

        for req_class in required_classes:
            subject_type = req_class["subject"].get("type", "theory")
            is_practical = subject_type == "practical"
            hours_per_week = req_class["subject"].get("hours_per_week", 3)

            # Determine how many slots this session spans
            if is_practical:
                if hours_per_week < practical_slots_needed:
                    # Special case: Seminar (1hr) = single slot
                    session_span = hours_per_week
                else:
                    session_span = practical_slots_needed
            else:
                session_span = 1

            for day in days:
                max_start_slot = len(time_slots) - session_span + 1

                for slot_idx in range(max_start_slot):
                    time_slot = time_slots[slot_idx]

                    # For multi-slot sessions, check if consecutive slots would span across a break
                    if session_span > 1:
                        can_span = True
                        spanned_slots = [time_slot]

                        for i in range(1, session_span):
                            if slot_idx + i >= len(time_slots):
                                can_span = False
                                break
                            next_slot = time_slots[slot_idx + i]
                            prev_slot = time_slots[slot_idx + i - 1]
                            if has_break_between_slots(prev_slot, next_slot):
                                can_span = False
                                break
                            spanned_slots.append(next_slot)

                        if not can_span or len(spanned_slots) < session_span:
                            continue
                    else:
                        spanned_slots = [time_slot]

                    # Build variable name
                    if is_practical:
                        var_name = f"{req_class['subject_id']}_{req_class['year']}_{req_class['division']}_B{req_class['batch']}_{day}_{time_slot}"
                    else:
                        var_name = f"{req_class['subject_id']}_{req_class['year']}_{req_class['division']}_{day}_{time_slot}"

                    var = self.model.NewBoolVar(var_name)
                    self.variables[var_name] = var

                    sessions.append({
                        "variable": var,
                        "subject_id": req_class["subject_id"],
                        "subject": req_class["subject"],
                        "year": req_class["year"],
                        "division": req_class["division"],
                        "batch": req_class.get("batch"),
                        "day": day,
                        "time_slot": time_slot,
                        "spanned_slots": spanned_slots,
                        "slot_index": slot_idx,
                        "session_span": session_span
                    })

        return sessions

    def _add_hour_constraints(self, sessions, required_classes, practical_slots_needed=2, slot_duration=60):
        """Ensure each class is scheduled the required hours per week.
        Theory: sessions_needed = hours_per_week
        Practical: sessions_needed = hours_per_week // practical_slots_needed
        Special case: if hours < practical_slots_needed (e.g. Seminar 1hr), sessions_needed = 1
        """
        for req_class in required_classes:
            hours_per_week = req_class["subject"].get("hours_per_week", 3)
            subject_type = req_class["subject"].get("type", "theory")

            if subject_type == "practical":
                if hours_per_week < practical_slots_needed:
                    # Special case: Seminar 1hr = 1 session of 1 slot
                    sessions_needed = 1
                else:
                    sessions_needed = hours_per_week // practical_slots_needed
            else:
                sessions_needed = hours_per_week

            # Match sessions for this specific required class
            class_sessions = []
            for s in sessions:
                if s["subject_id"] != req_class["subject_id"]:
                    continue
                if s["year"] != req_class["year"]:
                    continue
                if s["division"] != req_class["division"]:
                    continue
                if s["batch"] != req_class.get("batch"):
                    continue
                class_sessions.append(s["variable"])

            if class_sessions:
                self.model.Add(sum(class_sessions) == sessions_needed)

    def _add_faculty_constraints(self, sessions, faculty_list, days, time_slots, practical_slots_needed=2):
        """Ensure each faculty member teaches only one THEORY/TUTORIAL class per time slot.
        Practicals are handled by post-solve greedy assignment since in practice
        faculty rotate between labs and lab assistants help supervise batches.
        """
        for fac in faculty_list:
            for day in days:
                for slot_idx, time_slot in enumerate(time_slots):
                    faculty_sessions = []

                    for s in sessions:
                        # Only constrain theory/tutorial — practicals are assigned post-solve
                        if s["subject"].get("type") == "practical":
                            continue
                        if s["day"] == day and self._faculty_can_teach(fac, s):
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
                div_map = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}
                return div_map.get(session["division"]) in allowed_divs

        return False

    def _add_room_constraints(self, sessions, rooms_list, days, time_slots, practical_slots_needed=2):
        """Ensure room capacity is not exceeded.
        Counts ALL practical sessions (across all years, divisions, batches) globally.
        """
        classrooms = [r for r in rooms_list if r.get("type") in ["classroom", "both"]]
        labs = [r for r in rooms_list if r.get("type") in ["lab", "both"]]

        for day in days:
            for slot_idx, time_slot in enumerate(time_slots):
                # Theory sessions that occupy this slot
                theory_sessions = []
                for s in sessions:
                    if (s["day"] == day and
                        s["subject"].get("type") in ["theory", "tutorial"] and
                        time_slot in s.get("spanned_slots", [s["time_slot"]])):
                        theory_sessions.append(s["variable"])

                if theory_sessions and classrooms:
                    self.model.Add(sum(theory_sessions) <= len(classrooms))

                # Practical sessions that occupy this slot (ALL batches, all years, all divisions)
                practical_sessions = []
                for s in sessions:
                    if (s["day"] == day and
                        s["subject"].get("type") == "practical" and
                        time_slot in s.get("spanned_slots", [s["time_slot"]])):
                        practical_sessions.append(s["variable"])

                if practical_sessions and labs:
                    self.model.Add(sum(practical_sessions) <= len(labs))

    def _add_no_conflict_constraints(self, sessions, days, time_slots, practical_slots_needed, batches):
        """Ensure students don't have conflicting classes.
        For each (year, division, batch, day, slot):
          theory sessions for that division + practical sessions for that specific batch <= 1
        """
        for year in range(1, 5):
            for division in ["A", "B"]:
                for batch in batches:
                    for day in days:
                        for slot_idx, time_slot in enumerate(time_slots):
                            batch_sessions = []
                            for s in sessions:
                                if (s["year"] == year and
                                    s["division"] == division and
                                    s["day"] == day and
                                    time_slot in s.get("spanned_slots", [s["time_slot"]])):
                                    # Theory/tutorial: applies to all batches (batch is None)
                                    if s["batch"] is None:
                                        batch_sessions.append(s["variable"])
                                    # Practical: only applies to this specific batch
                                    elif s["batch"] == batch:
                                        batch_sessions.append(s["variable"])

                            if batch_sessions:
                                self.model.Add(sum(batch_sessions) <= 1)

    def _add_max_practical_per_day_constraint(self, sessions, years, divisions, batches, days):
        """Ensure no more than 2 practical sessions per day per batch"""
        for year in years:
            for division in divisions:
                for batch in batches:
                    for day in days:
                        practical_sessions = [
                            s["variable"] for s in sessions
                            if (s["year"] == year and
                                s["division"] == division and
                                s["batch"] == batch and
                                s["day"] == day and
                                s["subject"].get("type") == "practical")
                        ]

                        if practical_sessions:
                            self.model.Add(sum(practical_sessions) <= 2)

    def _build_timetable(self, sessions, structure, required_classes, batches):
        """Extract solution and build timetable with dual output:
        - Division keys (Year_X_Division_Y): theory + practical_block entries
        - Batch keys (Year_X_Division_Y_Batch_Z): theory + individual batch practicals
        """
        timetable = {}

        years = list(range(1, structure.get("years", 4) + 1))
        divisions = ["A", "B"][:structure.get("divisions_per_year", 2)]
        days = structure.get("days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
        time_slots = structure.get("time_slots", ["09:15-10:15", "10:15-11:15"])

        breaks = {
            "11:15-11:30": {"type": "recess", "label": "Short Break"},
            "13:30-14:30": {"type": "lunch", "label": "Lunch Break"}
        }

        extended_time_slots = self._insert_breaks_into_time_slots(time_slots, breaks)

        # Collect all active sessions first
        active_sessions = []
        for session in sessions:
            if self.solver.Value(session["variable"]) == 1:
                active_sessions.append(session)

        # Build conflict-aware faculty/room assignment maps
        faculty_assignment, room_assignment = self._assign_faculty_and_rooms(active_sessions, days, time_slots)

        # Initialize division-level and batch-level timetable structures
        for year in years:
            for division in divisions:
                # Division key
                div_key = f"Year_{year}_Division_{division}"
                timetable[div_key] = {day: {slot: None for slot in extended_time_slots} for day in days}

                # Batch keys
                for batch in batches:
                    batch_letter = chr(ord('A') + batch - 1)
                    batch_key = f"Year_{year}_Division_{division}_Batch_{batch_letter}"
                    timetable[batch_key] = {day: {slot: None for slot in extended_time_slots} for day in days}

                # Add break periods
                for day in days:
                    for break_slot, break_info in breaks.items():
                        break_data = {
                            "subject": break_info["label"],
                            "type": "break",
                            "faculty": "",
                            "room": "",
                            "code": "",
                            "break_type": break_info["type"]
                        }
                        timetable[div_key][day][break_slot] = break_data
                        for batch in batches:
                            batch_letter = chr(ord('A') + batch - 1)
                            batch_key = f"Year_{year}_Division_{division}_Batch_{batch_letter}"
                            timetable[batch_key][day][break_slot] = break_data.copy()

        # Fill scheduled classes
        for session in active_sessions:
            year = session["year"]
            division = session["division"]
            batch = session["batch"]
            day = session["day"]
            subject = session["subject"]
            subject_type = subject.get("type", "theory")

            # Get assigned faculty and room for this session
            session_key = self._session_key(session)
            fac_name = faculty_assignment.get(session_key, "Unassigned")
            room_name = room_assignment.get(session_key, "TBD")

            div_key = f"Year_{year}_Division_{division}"
            spanned_slots = session.get("spanned_slots", [session["time_slot"]])
            total_span = len(spanned_slots)

            if subject_type in ["theory", "tutorial"]:
                # Theory/tutorial: fill division view and ALL batch views
                for slot_pos, slot in enumerate(spanned_slots):
                    if slot in extended_time_slots:
                        session_data = {
                            "subject": subject["name"],
                            "type": subject_type,
                            "faculty": fac_name,
                            "room": room_name,
                            "code": subject.get("code", "")
                        }
                        if total_span > 1:
                            session_data["span"] = total_span
                            session_data["slot_position"] = "start" if slot_pos == 0 else "continuation"

                        timetable[div_key][day][slot] = session_data

                        # Copy to all batch views
                        for b in batches:
                            bl = chr(ord('A') + b - 1)
                            bk = f"Year_{year}_Division_{division}_Batch_{bl}"
                            timetable[bk][day][slot] = session_data.copy()

            else:
                # Practical: fill batch view for this specific batch
                batch_letter = chr(ord('A') + batch - 1)
                batch_key = f"Year_{year}_Division_{division}_Batch_{batch_letter}"

                for slot_pos, slot in enumerate(spanned_slots):
                    if slot in extended_time_slots:
                        session_data = {
                            "subject": subject["name"],
                            "type": "practical",
                            "faculty": fac_name,
                            "room": room_name,
                            "code": subject.get("code", ""),
                            "batch": batch,
                            "batch_letter": batch_letter
                        }
                        if total_span > 1:
                            session_data["span"] = total_span
                            session_data["slot_position"] = "start" if slot_pos == 0 else "continuation"

                        timetable[batch_key][day][slot] = session_data

        # Build practical_block entries in division views
        self._build_practical_blocks(timetable, active_sessions, years, divisions, batches,
                                     days, extended_time_slots, faculty_assignment, room_assignment)

        return {"timetable": timetable, "success": True}

    def _build_practical_blocks(self, timetable, active_sessions, years, divisions, batches,
                                days, extended_time_slots, faculty_assignment, room_assignment):
        """Build practical_block entries in division views showing all batches side-by-side."""
        for year in years:
            for division in divisions:
                div_key = f"Year_{year}_Division_{division}"
                for day in days:
                    for slot in extended_time_slots:
                        # Skip break slots
                        current = timetable[div_key][day][slot]
                        if current and current.get("type") == "break":
                            continue
                        # Skip if already has theory/tutorial
                        if current and current.get("type") in ["theory", "tutorial"]:
                            continue

                        # Check if any batch has a practical starting at this slot
                        batch_info = {}
                        has_any_practical = False
                        block_span = 1

                        for batch in batches:
                            batch_letter = chr(ord('A') + batch - 1)
                            batch_key = f"Year_{year}_Division_{division}_Batch_{batch_letter}"
                            batch_session = timetable[batch_key][day].get(slot)

                            if (batch_session and
                                batch_session.get("type") == "practical" and
                                batch_session.get("slot_position", "start") != "continuation"):
                                has_any_practical = True
                                batch_info[batch] = {
                                    "subject": batch_session["subject"],
                                    "faculty": batch_session.get("faculty", ""),
                                    "room": batch_session.get("room", ""),
                                    "code": batch_session.get("code", "")
                                }
                                if batch_session.get("span", 1) > block_span:
                                    block_span = batch_session["span"]
                            else:
                                batch_info[batch] = None

                        if has_any_practical:
                            # Also check for continuation practicals at this slot
                            # (some batches may have a practical continuing here from a prev slot)
                            for batch in batches:
                                if batch_info[batch] is not None:
                                    continue
                                batch_letter = chr(ord('A') + batch - 1)
                                batch_key = f"Year_{year}_Division_{division}_Batch_{batch_letter}"
                                batch_session = timetable[batch_key][day].get(slot)
                                if (batch_session and
                                    batch_session.get("type") == "practical" and
                                    batch_session.get("slot_position") == "continuation"):
                                    # This batch has a continuation here — it started earlier
                                    # Don't include it in this block start
                                    pass

                            timetable[div_key][day][slot] = {
                                "type": "practical_block",
                                "batches": batch_info,
                                "span": block_span,
                                "slot_position": "start"
                            }

                            # Mark continuation slots in division view
                            if block_span > 1:
                                slot_list = [s for s in extended_time_slots
                                            if s != slot and not any(
                                                b.get("type") == "break"
                                                for b in [timetable[div_key][day].get(s, {}) or {}]
                                                if isinstance(b, dict)
                                            )]
                                # Find the index of current slot in extended_time_slots
                                try:
                                    slot_idx = extended_time_slots.index(slot)
                                except ValueError:
                                    continue

                                continuation_count = 0
                                for next_idx in range(slot_idx + 1, len(extended_time_slots)):
                                    if continuation_count >= block_span - 1:
                                        break
                                    next_slot = extended_time_slots[next_idx]
                                    existing = timetable[div_key][day].get(next_slot)
                                    if existing and existing.get("type") == "break":
                                        continue  # Skip break slots

                                    timetable[div_key][day][next_slot] = {
                                        "type": "practical_block",
                                        "batches": batch_info,
                                        "span": block_span,
                                        "slot_position": "continuation"
                                    }
                                    continuation_count += 1

    def _assign_faculty_and_rooms(self, active_sessions, days, time_slots):
        """Conflict-aware faculty and room assignment for all active sessions.
        Returns two dicts mapping session_key -> faculty_name and session_key -> room_name.
        """
        faculty_list = data_manager.get_faculty()
        rooms_list = data_manager.get_rooms()
        labs = [r for r in rooms_list if r.get("type") in ["lab", "both"]]
        classrooms = [r for r in rooms_list if r.get("type") in ["classroom", "both"]]

        # Track used faculty and rooms per (day, slot)
        used_faculty = {}  # (day, slot) -> set of faculty names
        used_rooms = {}    # (day, slot) -> set of room names

        for day in days:
            for slot in time_slots:
                used_faculty[(day, slot)] = set()
                used_rooms[(day, slot)] = set()

        faculty_assignment = {}
        room_assignment = {}

        # Sort sessions: theory first, then practicals (to give theory priority)
        sorted_sessions = sorted(active_sessions, key=lambda s: (
            0 if s["subject"].get("type") in ["theory", "tutorial"] else 1,
            s["year"], s["division"], s.get("batch") or 0
        ))

        for session in sorted_sessions:
            skey = self._session_key(session)
            subject_type = session["subject"].get("type", "theory")
            spanned_slots = session.get("spanned_slots", [session["time_slot"]])
            day = session["day"]

            # Assign faculty
            fac_name = self._assign_faculty_for_session(
                session, faculty_list, day, spanned_slots, used_faculty
            )
            faculty_assignment[skey] = fac_name

            # Mark faculty as used for all spanned slots
            if fac_name != "Unassigned":
                for slot in spanned_slots:
                    if (day, slot) in used_faculty:
                        used_faculty[(day, slot)].add(fac_name)

            # Assign room
            if subject_type == "practical":
                room_pool = labs
            else:
                room_pool = classrooms

            room_name = self._assign_room_for_session(
                room_pool, day, spanned_slots, used_rooms
            )
            room_assignment[skey] = room_name

            # Mark room as used for all spanned slots
            if room_name not in ["TBD", "Lab TBD", "Room TBD"]:
                for slot in spanned_slots:
                    if (day, slot) in used_rooms:
                        used_rooms[(day, slot)].add(room_name)

        return faculty_assignment, room_assignment

    def _assign_faculty_for_session(self, session, faculty_list, day, spanned_slots, used_faculty):
        """Pick a faculty member for this session that isn't already used at any of its slots."""
        div_map = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}
        div_num = div_map.get(session["division"], 1)

        for fac in faculty_list:
            subjects = fac.get("subjects", []) or []
            can_teach = False

            if subjects and not isinstance(subjects[0], dict):
                if session["subject_id"] in subjects:
                    can_teach = True
            else:
                for assignment in subjects:
                    if assignment.get("subject_id") == session["subject_id"]:
                        allowed_divs = assignment.get("divisions", [])
                        if not allowed_divs or div_num in allowed_divs:
                            can_teach = True
                        break

            if not can_teach:
                continue

            # Check if this faculty is free at all spanned slots
            fac_name = fac.get("name", "Unassigned")
            is_free = True
            for slot in spanned_slots:
                if (day, slot) in used_faculty and fac_name in used_faculty[(day, slot)]:
                    is_free = False
                    break

            if is_free:
                return fac_name

        return "Unassigned"

    def _assign_room_for_session(self, room_pool, day, spanned_slots, used_rooms):
        """Pick a room from the pool that isn't already used at any of this session's slots."""
        for room in room_pool:
            room_name = room.get("name", "TBD")
            is_free = True
            for slot in spanned_slots:
                if (day, slot) in used_rooms and room_name in used_rooms[(day, slot)]:
                    is_free = False
                    break
            if is_free:
                return room_name

        return "TBD"

    def _session_key(self, session):
        """Unique key for a session to use in assignment dicts."""
        batch_part = f"_B{session['batch']}" if session.get("batch") else ""
        return f"{session['subject_id']}_{session['year']}_{session['division']}{batch_part}_{session['day']}_{session['time_slot']}"

    def _insert_breaks_into_time_slots(self, time_slots, breaks):
        """Insert break periods into time slots list in chronological order"""
        break_slots = list(breaks.keys())
        all_slots = list(time_slots) + break_slots

        def get_start_time(slot):
            return slot.split('-')[0]

        all_slots.sort(key=get_start_time)
        return all_slots


# Global solver instance
timetable_solver = SimpleTimetableSolver()
