import json
import os
from typing import Dict, List, Optional
from datetime import datetime

class DataManager:
    """Manages JSON-based data storage for the timetable application"""
    
    def __init__(self):
        self.data_dir = "data"
        self.ensure_data_directory()
        self.init_default_data()
    
    def ensure_data_directory(self):
        """Create data directory if it doesn't exist"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def load_json(self, filename: str) -> Dict:
        """Load data from JSON file"""
        filepath = os.path.join(self.data_dir, filename)
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}
    
    def save_json(self, filename: str, data: Dict):
        """Save data to JSON file"""
        filepath = os.path.join(self.data_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def init_default_data(self):
        """Initialize default data if files don't exist"""
        # Default academic structure
        if not os.path.exists(os.path.join(self.data_dir, "academic_structure.json")):
            default_structure = {
                "years": 3,
                "divisions_per_year": 2,
                "batches_per_division": 3,
                "theory_duration": 60,  # minutes
                "practical_duration": 120,  # minutes
                "time_slots": [
                    "09:00-10:00",
                    "10:00-11:00",
                    "11:15-12:15",
                    "12:15-13:15",
                    "14:15-15:15",
                    "15:15-16:15",
                    "16:30-17:30",
                    "17:30-18:30"
                ],
                "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            }
            self.save_json("academic_structure.json", default_structure)
        
        # Default subjects
        if not os.path.exists(os.path.join(self.data_dir, "subjects.json")):
            default_subjects = {
                "subjects": []
            }
            self.save_json("subjects.json", default_subjects)
        
        # Default faculty
        if not os.path.exists(os.path.join(self.data_dir, "faculty.json")):
            default_faculty = {
                "faculty": []
            }
            self.save_json("faculty.json", default_faculty)
        
        # Default rooms
        if not os.path.exists(os.path.join(self.data_dir, "rooms.json")):
            default_rooms = {
                "rooms": []
            }
            self.save_json("rooms.json", default_rooms)
        
        # Default saved timetables
        if not os.path.exists(os.path.join(self.data_dir, "saved_timetables.json")):
            default_saved = {
                "timetables": []
            }
            self.save_json("saved_timetables.json", default_saved)
    
    def get_academic_structure(self) -> Dict:
        """Get academic structure configuration"""
        return self.load_json("academic_structure.json")
    
    def update_academic_structure(self, structure: Dict):
        """Update academic structure configuration"""
        self.save_json("academic_structure.json", structure)
    
    def get_subjects(self) -> List[Dict]:
        """Get all subjects"""
        data = self.load_json("subjects.json")
        return data.get("subjects", [])
    
    def add_subject(self, subject: Dict):
        """Add a new subject"""
        data = self.load_json("subjects.json")
        subjects = data.get("subjects", [])
        subject["id"] = len(subjects) + 1
        subjects.append(subject)
        data["subjects"] = subjects
        self.save_json("subjects.json", data)
    
    def update_subject(self, subject_id: int, subject: Dict):
        """Update an existing subject"""
        data = self.load_json("subjects.json")
        subjects = data.get("subjects", [])
        for i, s in enumerate(subjects):
            if s.get("id") == subject_id:
                subject["id"] = subject_id
                subjects[i] = subject
                break
        data["subjects"] = subjects
        self.save_json("subjects.json", data)
    
    def delete_subject(self, subject_id: int):
        """Delete a subject"""
        data = self.load_json("subjects.json")
        subjects = data.get("subjects", [])
        subjects = [s for s in subjects if s.get("id") != subject_id]
        data["subjects"] = subjects
        self.save_json("subjects.json", data)
    
    def get_faculty(self) -> List[Dict]:
        """Get all faculty members"""
        data = self.load_json("faculty.json")
        return data.get("faculty", [])
    
    def add_faculty(self, faculty: Dict):
        """Add a new faculty member"""
        data = self.load_json("faculty.json")
        faculty_list = data.get("faculty", [])
        faculty["id"] = len(faculty_list) + 1
        faculty_list.append(faculty)
        data["faculty"] = faculty_list
        self.save_json("faculty.json", data)
    
    def update_faculty(self, faculty_id: int, faculty: Dict):
        """Update an existing faculty member"""
        data = self.load_json("faculty.json")
        faculty_list = data.get("faculty", [])
        for i, f in enumerate(faculty_list):
            if f.get("id") == faculty_id:
                faculty["id"] = faculty_id
                faculty_list[i] = faculty
                break
        data["faculty"] = faculty_list
        self.save_json("faculty.json", data)
    
    def delete_faculty(self, faculty_id: int):
        """Delete a faculty member"""
        data = self.load_json("faculty.json")
        faculty_list = data.get("faculty", [])
        faculty_list = [f for f in faculty_list if f.get("id") != faculty_id]
        data["faculty"] = faculty_list
        self.save_json("faculty.json", data)
    
    def get_rooms(self) -> List[Dict]:
        """Get all rooms"""
        data = self.load_json("rooms.json")
        return data.get("rooms", [])
    
    def add_room(self, room: Dict):
        """Add a new room"""
        data = self.load_json("rooms.json")
        rooms = data.get("rooms", [])
        room["id"] = len(rooms) + 1
        rooms.append(room)
        data["rooms"] = rooms
        self.save_json("rooms.json", data)
    
    def update_room(self, room_id: int, room: Dict):
        """Update an existing room"""
        data = self.load_json("rooms.json")
        rooms = data.get("rooms", [])
        for i, r in enumerate(rooms):
            if r.get("id") == room_id:
                room["id"] = room_id
                rooms[i] = room
                break
        data["rooms"] = rooms
        self.save_json("rooms.json", data)
    
    def delete_room(self, room_id: int):
        """Delete a room"""
        data = self.load_json("rooms.json")
        rooms = data.get("rooms", [])
        rooms = [r for r in rooms if r.get("id") != room_id]
        data["rooms"] = rooms
        self.save_json("rooms.json", data)
    
    def save_timetable(self, timetable: Dict, name: Optional[str] = None) -> Dict:
        """Save a timetable with metadata"""
        data = self.load_json("saved_timetables.json")
        saved_timetables = data.get("timetables", [])
        
        # Create timetable entry
        timetable_entry = {
            "id": len(saved_timetables) + 1,
            "name": name or f"Timetable {len(saved_timetables) + 1}",
            "timetable": timetable,
            "saved_at": datetime.now().isoformat(),
            "saved_at_formatted": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        saved_timetables.append(timetable_entry)
        data["timetables"] = saved_timetables
        self.save_json("saved_timetables.json", data)
        
        return timetable_entry
    
    def get_saved_timetables(self) -> List[Dict]:
        """Get all saved timetables"""
        data = self.load_json("saved_timetables.json")
        timetables = data.get("timetables", [])
        # Sort by saved_at descending (newest first)
        timetables.sort(key=lambda x: x.get("saved_at", ""), reverse=True)
        return timetables
    
    def get_saved_timetable(self, timetable_id: int) -> Optional[Dict]:
        """Get a specific saved timetable by ID"""
        data = self.load_json("saved_timetables.json")
        timetables = data.get("timetables", [])
        for tt in timetables:
            if tt.get("id") == timetable_id:
                return tt
        return None
    
    def delete_saved_timetable(self, timetable_id: int):
        """Delete a saved timetable"""
        data = self.load_json("saved_timetables.json")
        timetables = data.get("timetables", [])
        timetables = [tt for tt in timetables if tt.get("id") != timetable_id]
        data["timetables"] = timetables
        self.save_json("saved_timetables.json", data)

# Global data manager instance
data_manager = DataManager()
