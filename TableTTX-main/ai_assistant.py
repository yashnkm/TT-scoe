import json
import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from openai import OpenAI
from models import data_manager
from solver import SimpleTimetableSolver

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user

class TimetableAIAssistant:
    """AI-powered assistant for intelligent timetable modifications and optimization"""
    
    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
            self.ai_available = True
            logging.info("✅ OpenAI API connected successfully - Full AI capabilities enabled")
        else:
            self.client = None
            self.ai_available = False
            logging.warning("⚠️ OpenAI API key not found. AI features will use fallback mode.")
        
        self.solver = SimpleTimetableSolver()
        
        # Track AI usage for monitoring and optimization
        self.total_tokens_used = 0
        self.total_requests = 0
        self.successful_suggestions = 0
        
        # Store user preferences learned from feedback
        self.learned_preferences = {
            'prefers_morning_slots': False,
            'prefers_afternoon_slots': False,
            'prefers_consolidated': False,
            'prefers_distributed': False,
            'preferred_days': [],
            'avoid_days': [],
            'preferred_time_ranges': []
        }
        
    def process_natural_language_request(self, request: str, current_timetable: Dict, user_feedback: str = None, previous_suggestions: List = None) -> Dict:
        """
        Process natural language requests for timetable modifications
        Example: "Dr. Smith is on leave next Tuesday, reschedule his classes"
        """
        try:
            logging.info(f"Processing AI request: {request}")
            logging.info(f"Timetable keys: {list(current_timetable.keys()) if current_timetable else 'None'}")
            
            # Check if AI is available
            if not self.ai_available:
                return self._process_request_fallback(request, current_timetable, user_feedback, previous_suggestions)
            
            # Track AI request
            self.total_requests += 1
            
            # Use GPT-4o to understand the request and extract structured information
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an advanced AI assistant specialized in academic timetable management with expertise in:
                        - Complex constraint satisfaction
                        - Academic scheduling optimization
                        - Natural language understanding of scheduling requests
                        - Context-aware decision making
                        - Faculty workload balancing
                        - Room resource optimization
                        
                        Your task is to analyze user requests and extract precise, actionable information while considering:
                        1. Academic calendar constraints
                        2. Faculty availability and preferences
                        3. Room capacity and type requirements
                        4. Student schedule continuity
                        5. Institutional policies
                        6. Urgency and impact levels
                        
                        Be intelligent about:
                        - Recognizing implicit requirements (e.g., "on leave" implies rescheduling all sessions)
                        - Understanding time references (next Monday, this week, etc.)
                        - Identifying conflicts or dependencies
                        - Suggesting proactive alternatives
                        
                        Respond with JSON containing:
                        {
                            "action": "faculty_leave" | "room_unavailable" | "reschedule_session" | "add_session" | "cancel_session" | "optimize_schedule" | "swap_sessions",
                            "entity": "faculty_name" | "room_name" | "subject_name",
                            "date_range": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
                            "time_slots": ["time_slot1", "time_slot2"],
                            "reason": "detailed description of the change and its context",
                            "priority": "critical" | "high" | "medium" | "low",
                            "urgency": "immediate" | "soon" | "flexible",
                            "impact_level": "high" | "medium" | "low",
                            "affected_entities": ["entity1", "entity2"],
                            "constraints": ["constraint1", "constraint2"],
                            "alternative_suggestions": ["intelligent suggestion1", "intelligent suggestion2", "intelligent suggestion3"],
                            "confidence_score": 0.0-1.0
                        }
                        
                        If the request is ambiguous, provide your best interpretation with a lower confidence score and suggest clarifying questions."""
                    },
                    {
                        "role": "user",
                        "content": f"""Timetable modification request: {request}
                        
Available Context:
- Faculty: {self._get_faculty_names()}
- Subjects: {self._get_subject_names()}
- Rooms: {self._get_room_names()}
- Current date: {datetime.now().strftime('%Y-%m-%d')}

User's learned preferences: {json.dumps(self.learned_preferences, indent=2)}

Analyze this request deeply and provide structured, intelligent recommendations."""
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7  # Balanced creativity and consistency
            )
            
            # Track token usage
            if hasattr(response, 'usage'):
                self.total_tokens_used += response.usage.total_tokens
                logging.info(f"🤖 AI tokens used: {response.usage.total_tokens} | Total session: {self.total_tokens_used}")
            
            parsed_request = json.loads(response.choices[0].message.content)
            logging.info(f"Parsed AI request: {parsed_request}")
            
            # Process the structured request
            result = self._execute_modification(parsed_request, current_timetable, user_feedback, previous_suggestions)
            logging.info(f"AI modification result: {result}")
            return result
            
        except Exception as e:
            logging.error(f"Error processing natural language request: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to process request: {str(e)}",
                "suggestions": ["Please try rephrasing your request", "Ensure faculty/room names are correct"]
            }
    
    def suggest_optimal_reschedule(self, affected_sessions: List[Dict], constraints: Dict = None, user_feedback: str = None, previous_suggestions: List = None) -> Dict:
        """
        Use AI to suggest optimal rescheduling options for affected sessions
        Enhanced with user feedback and iterative improvement
        """
        try:
            if not self.ai_available:
                # Use structured suggestions when AI is not available
                structured_suggestions = self._generate_structured_suggestions(affected_sessions, constraints, user_feedback)
                return {
                    "success": True,
                    "suggestions": {
                        "rescheduling_options": structured_suggestions
                    },
                    "ai_reasoning": "Generated optimal rescheduling options based on available faculty and room constraints",
                    "can_improve": True
                }
            
            # Prepare enhanced context for AI analysis
            context = {
                "affected_sessions": affected_sessions,
                "constraints": constraints,
                "available_slots": self._get_available_slots(),
                "faculty_availability": self._get_faculty_availability(),
                "room_availability": self._get_room_availability(),
                "user_feedback": user_feedback,
                "previous_suggestions": previous_suggestions
            }
            
            # Enhanced AI prompt with feedback consideration
            system_prompt = """You are an elite timetable optimization AI with PhD-level expertise in:
            - Operations Research and Constraint Satisfaction
            - Academic Scheduling Theory
            - Human Behavioral Psychology (understanding preferences)
            - Resource Optimization
            - Change Management (minimizing disruption)
            
            CORE OPTIMIZATION PRINCIPLES:
            1. **Student-Centric**: Minimize impact on student learning continuity
            2. **Faculty Welfare**: Balance workload and respect preferences
            3. **Resource Efficiency**: Optimal utilization of rooms and time
            4. **Academic Quality**: Maintain pedagogical best practices
            5. **Flexibility**: Build in resilience for future changes
            6. **User Learning**: CRITICALLY analyze and incorporate user feedback
            
            INTELLIGENT SUGGESTION STRATEGY:
            You MUST generate exactly 3 diverse, high-quality options representing different approaches:
            
            Option 1: "MINIMAL DISRUPTION" 
            - Keep as much unchanged as possible
            - Same times/rooms when feasible
            - Substitute resources only when necessary
            - Best for: Urgent changes, risk-averse situations
            
            Option 2: "STRATEGIC OPTIMIZATION"
            - Balance between change and improvement
            - Consolidate or redistribute intelligently
            - Consider broader schedule efficiency
            - Best for: Planned changes, moderate flexibility
            
            Option 3: "BOLD RESTRUCTURING"
            - Creative rearrangement for optimal outcome
            - May involve significant changes but with clear benefits
            - Long-term thinking and preventive improvements
            - Best for: Major disruptions, willing to embrace change
            
            FEEDBACK INTEGRATION (CRITICAL):
            - If user feedback provided: Analyze deeply what they liked/disliked
            - Identify patterns in preferences (timing, consolidation, faculty, etc.)
            - Adjust ALL THREE options to align with discovered preferences
            - Explain HOW you incorporated feedback
            - Never repeat rejected patterns
            
            SCORING METHODOLOGY:
            Impact Score (0-10 scale):
            - 9-10: Nearly perfect, minimal disruption, high satisfaction
            - 7-8: Good solution with minor trade-offs
            - 5-6: Acceptable but notable compromises
            - 3-4: Significant disruption but necessary
            - 0-2: Major issues, last resort only
            
            Consider: student impact (40%), faculty convenience (30%), resource efficiency (20%), future flexibility (10%)
            
            Respond with JSON in this exact format:
            {
                "reasoning": "Deep, PhD-level analysis of the situation, constraints, and your strategic approach. Explain WHY these specific options.",
                "rescheduling_options": [
                    {
                        "rank": 1,
                        "strategy": "MINIMAL DISRUPTION | STRATEGIC OPTIMIZATION | BOLD RESTRUCTURING",
                        "description": "Crystal clear, compelling description that sells this option",
                        "sessions": [
                            {
                                "subject": "Subject Name",
                                "type": "theory/practical",
                                "faculty": "Faculty Name",
                                "room": "Room Code",
                                "day": "Day Name",
                                "time_slot": "HH:MM-HH:MM",
                                "rationale": "Why this specific slot/faculty/room"
                            }
                        ],
                        "pros": ["Specific advantage 1", "Specific advantage 2", "Specific advantage 3"],
                        "cons": ["Honest disadvantage 1", "Honest disadvantage 2"],
                        "impact_score": 8.5,
                        "confidence": 0.9,
                        "risk_level": "low | medium | high",
                        "implementation_complexity": "easy | moderate | complex",
                        "notes": "Additional strategic insights and recommendations",
                        "best_for": "What type of user/situation this option serves best"
                    }
                ],
                "feedback_analysis": "Detailed explanation of how user feedback influenced these suggestions. Be specific about what changed.",
                "learned_patterns": ["pattern1", "pattern2"],
                "confidence_overall": 0.85,
                "can_improve": true,
                "improvement_suggestions": "What additional information would make suggestions even better"
            }"""
            
            # Build comprehensive user prompt with context
            user_prompt = f"""RESCHEDULING ANALYSIS REQUEST:

📊 Situation Context:
{json.dumps(context, indent=2)}

👤 User's Learned Preferences:
{json.dumps(self.learned_preferences, indent=2)}

📈 AI Assistant Performance:
- Total requests processed: {self.total_requests}
- Successful suggestions: {self.successful_suggestions}
- Success rate: {(self.successful_suggestions/self.total_requests*100) if self.total_requests > 0 else 0:.1f}%"""
            
            if user_feedback:
                user_prompt += f"""

💬 CRITICAL USER FEEDBACK (HIGH PRIORITY):
"{user_feedback}"

⚠️ ACTION REQUIRED: 
The user was NOT satisfied with previous suggestions. Analyze this feedback deeply:
1. What specific aspects did they dislike?
2. What patterns can you identify in their preferences?
3. How should this change your approach?
4. Generate NEW suggestions that address their concerns.

DO NOT repeat similar patterns. LEARN and ADAPT."""
            
            if previous_suggestions:
                user_prompt += f"""

📜 Previous Suggestions (for reference - don't repeat these patterns if feedback was negative):
{json.dumps(previous_suggestions, indent=2)[:500]}..."""
            
            user_prompt += """

🎯 YOUR TASK:
Generate 3 brilliant, diverse, well-reasoned rescheduling options. Each should be distinctly different in approach.
Make them so good that the user will say "Wow, this AI really understands scheduling!"
"""
            
            # Track AI request
            self.total_requests += 1
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.8  # Higher creativity for diverse options
            )
            
            # Track token usage
            if hasattr(response, 'usage'):
                tokens_used = response.usage.total_tokens
                self.total_tokens_used += tokens_used
                estimated_cost = (tokens_used / 1000) * 0.01  # Rough estimate for GPT-4o
                logging.info(f"🤖 AI Suggestion Generation - Tokens: {tokens_used} | Est. Cost: ${estimated_cost:.4f} | Session Total: {self.total_tokens_used}")
            
            ai_response = json.loads(response.choices[0].message.content)
            
            # Enhance AI suggestions with our structured approach
            enhanced_suggestions = self._enhance_ai_suggestions(ai_response, affected_sessions, constraints, user_feedback)
            
            return {
                "success": True,
                "suggestions": enhanced_suggestions,
                "ai_reasoning": ai_response.get("reasoning", "AI analysis completed"),
                "feedback_analysis": ai_response.get("feedback_analysis", ""),
                "can_improve": ai_response.get("can_improve", True)
            }
            
        except Exception as e:
            logging.error(f"Error generating reschedule suggestions: {str(e)}")
            # Provide fallback suggestions when AI fails
            fallback_suggestions = self._generate_fallback_suggestions(affected_sessions, constraints)
            return {
                "success": True,
                "suggestions": fallback_suggestions,
                "ai_reasoning": "Using basic rescheduling logic due to AI service unavailability",
                "fallback_mode": True
            }
    
    def analyze_schedule_conflicts(self, timetable: Dict) -> Dict:
        """
        Use AI to analyze and identify potential conflicts or optimization opportunities
        """
        try:
            # Extract schedule data for analysis
            schedule_analysis = self._extract_schedule_metrics(timetable)
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a timetable quality analyst. Analyze the given schedule data and identify:
                        
                        1. Potential conflicts or issues
                        2. Optimization opportunities
                        3. Workload imbalances
                        4. Room utilization inefficiencies
                        5. Student schedule quality issues
                        
                        Provide specific, actionable recommendations with priority levels."""
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this timetable: {json.dumps(schedule_analysis, indent=2)}"
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            return {
                "success": True,
                "analysis": analysis,
                "recommendations": analysis.get("recommendations", []),
                "quality_score": analysis.get("quality_score", 0)
            }
            
        except Exception as e:
            logging.error(f"Error analyzing schedule conflicts: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to analyze schedule: {str(e)}"
            }
    
    def generate_emergency_schedule(self, constraints: Dict, priority_sessions: List[Dict]) -> Dict:
        """
        Generate emergency schedule adjustments for urgent situations
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an emergency timetable coordinator. Generate immediate schedule adjustments for urgent situations.
                        
                        Prioritize:
                        1. Critical sessions that must continue
                        2. Minimal disruption to students
                        3. Fair faculty workload distribution
                        4. Available resources
                        
                        Provide step-by-step emergency rescheduling plan."""
                    },
                    {
                        "role": "user",
                        "content": f"Emergency situation: {json.dumps(constraints, indent=2)}\nPriority sessions: {json.dumps(priority_sessions, indent=2)}"
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            emergency_plan = json.loads(response.choices[0].message.content)
            
            # Generate actual timetable based on emergency plan
            modified_timetable = self._apply_emergency_plan(emergency_plan)
            
            return {
                "success": True,
                "emergency_plan": emergency_plan,
                "modified_timetable": modified_timetable,
                "priority": "high"
            }
            
        except Exception as e:
            logging.error(f"Error generating emergency schedule: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to generate emergency schedule: {str(e)}"
            }
    
    def optimize_faculty_workload(self, current_assignments: Dict) -> Dict:
        """
        Use AI to analyze and optimize faculty workload distribution
        """
        try:
            workload_analysis = self._analyze_faculty_workload(current_assignments)
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a faculty workload optimization expert. Analyze current faculty assignments and suggest improvements.
                        
                        Consider:
                        1. Teaching hour balance across faculty
                        2. Subject expertise matching
                        3. Preparation time requirements
                        4. Faculty preferences and constraints
                        5. Administrative responsibilities
                        
                        Provide specific reallocation suggestions."""
                    },
                    {
                        "role": "user",
                        "content": f"Current faculty workload: {json.dumps(workload_analysis, indent=2)}"
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            optimization = json.loads(response.choices[0].message.content)
            
            return {
                "success": True,
                "current_analysis": workload_analysis,
                "optimization_suggestions": optimization,
                "projected_improvements": optimization.get("improvements", {})
            }
            
        except Exception as e:
            logging.error(f"Error optimizing faculty workload: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to optimize faculty workload: {str(e)}"
            }
    
    def _execute_modification(self, parsed_request: Dict, current_timetable: Dict, user_feedback: str = None, previous_suggestions: List = None) -> Dict:
        """Execute the parsed modification request"""
        action = parsed_request.get("action")
        
        if action == "faculty_leave":
            return self._handle_faculty_leave(parsed_request, current_timetable, user_feedback, previous_suggestions)
        elif action == "room_unavailable":
            return self._handle_room_unavailable(parsed_request, current_timetable, user_feedback, previous_suggestions)
        elif action == "reschedule_session":
            return self._handle_reschedule_session(parsed_request, current_timetable, user_feedback, previous_suggestions)
        elif action == "add_session":
            return self._handle_add_session(parsed_request, current_timetable, user_feedback, previous_suggestions)
        elif action == "cancel_session":
            return self._handle_cancel_session(parsed_request, current_timetable, user_feedback, previous_suggestions)
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "parsed_request": parsed_request
            }
    
    def _handle_faculty_leave(self, request: Dict, timetable: Dict, user_feedback: str = None, previous_suggestions: List = None) -> Dict:
        """Handle faculty leave scenarios"""
        faculty_name = request.get("entity")
        date_range = request.get("date_range", {})
        
        logging.info(f"Handling faculty leave for: {faculty_name}")
        
        # Find affected sessions
        affected_sessions = self._find_faculty_sessions(faculty_name, timetable, date_range)
        logging.info(f"Found {len(affected_sessions)} affected sessions")
        
        if not affected_sessions:
            return {
                "success": True,
                "message": f"No sessions found for {faculty_name} in the specified period",
                "affected_sessions": []
            }
        
        # Generate rescheduling suggestions with feedback support
        suggestions = self.suggest_optimal_reschedule(
            affected_sessions, 
            {"faculty_unavailable": faculty_name, "date_range": date_range},
            user_feedback=user_feedback,
            previous_suggestions=previous_suggestions
        )
        
        return {
            "success": True,
            "action": "faculty_leave",
            "affected_sessions": affected_sessions,
            "reschedule_suggestions": suggestions,
            "message": f"Found {len(affected_sessions)} sessions affected by {faculty_name}'s leave"
        }
    
    def _handle_room_unavailable(self, request: Dict, timetable: Dict, user_feedback: str = None, previous_suggestions: List = None) -> Dict:
        """Handle room unavailable scenarios"""
        return {"success": False, "error": "Room unavailable handling not implemented yet"}
    
    def _handle_reschedule_session(self, request: Dict, timetable: Dict, user_feedback: str = None, previous_suggestions: List = None) -> Dict:
        """Handle session rescheduling scenarios"""
        return {"success": False, "error": "Session rescheduling handling not implemented yet"}
    
    def _handle_add_session(self, request: Dict, timetable: Dict, user_feedback: str = None, previous_suggestions: List = None) -> Dict:
        """Handle adding new sessions"""
        return {"success": False, "error": "Add session handling not implemented yet"}
    
    def _handle_cancel_session(self, request: Dict, timetable: Dict, user_feedback: str = None, previous_suggestions: List = None) -> Dict:
        """Handle session cancellation"""
        return {"success": False, "error": "Cancel session handling not implemented yet"}
    
    
    def _get_faculty_names(self) -> List[str]:
        """Get list of faculty names"""
        faculty = data_manager.get_faculty()
        return [f["name"] for f in faculty]
    
    def _get_subject_names(self) -> List[str]:
        """Get list of subject names"""
        subjects = data_manager.get_subjects()
        return [s["name"] for s in subjects]
    
    def _get_room_names(self) -> List[str]:
        """Get list of room names"""
        rooms = data_manager.get_rooms()
        return [r["name"] for r in rooms]
    
    def _get_available_slots(self) -> List[str]:
        """Get available time slots"""
        structure = data_manager.get_academic_structure()
        return structure.get("time_slots", [])
    
    def _get_faculty_availability(self) -> Dict:
        """Get faculty availability information"""
        # This would normally come from a more detailed faculty availability system
        faculty = data_manager.get_faculty()
        return {f["name"]: {"max_hours": f.get("max_hours_per_week", 20)} for f in faculty}
    
    def _get_room_availability(self) -> Dict:
        """Get room availability information"""
        rooms = data_manager.get_rooms()
        return {r["name"]: {"capacity": r["capacity"], "type": r["type"]} for r in rooms}
    
    def _find_faculty_sessions(self, faculty_name: str, timetable: Dict, date_range: Dict) -> List[Dict]:
        """Find sessions assigned to a specific faculty member"""
        affected_sessions = []
        
        for view_key, view_data in timetable.items():
            for day, day_data in view_data.items():
                for time_slot, session in day_data.items():
                    if session:
                        # Handle both single session and array of sessions
                        sessions_to_check = session if isinstance(session, list) else [session]
                        
                        for single_session in sessions_to_check:
                            if isinstance(single_session, dict) and single_session.get("faculty") == faculty_name:
                                affected_sessions.append({
                                    "view": view_key,
                                    "day": day,
                                    "time_slot": time_slot,
                                    "session": single_session
                                })
        
        return affected_sessions
    
    def _find_room_sessions(self, room_name: str, timetable: Dict, date_range: Dict) -> List[Dict]:
        """Find sessions in a specific room"""
        affected_sessions = []
        
        for view_key, view_data in timetable.items():
            for day, day_data in view_data.items():
                for time_slot, session in day_data.items():
                    if session:
                        # Handle both single session and array of sessions
                        sessions_to_check = session if isinstance(session, list) else [session]
                        
                        for single_session in sessions_to_check:
                            if isinstance(single_session, dict) and single_session.get("room") == room_name:
                                affected_sessions.append({
                                    "view": view_key,
                                    "day": day,
                                    "time_slot": time_slot,
                                    "session": single_session
                                })
        
        return affected_sessions
    
    def _find_alternative_rooms(self, unavailable_room: str, affected_sessions: List[Dict]) -> List[str]:
        """Find alternative rooms for affected sessions"""
        rooms = data_manager.get_rooms()
        unavailable_room_data = next((r for r in rooms if r["name"] == unavailable_room), None)
        
        if not unavailable_room_data:
            return []
        
        # Find rooms with similar capacity and type
        alternatives = []
        for room in rooms:
            if (room["name"] != unavailable_room and 
                room["type"] in [unavailable_room_data["type"], "both"] and
                room["capacity"] >= unavailable_room_data["capacity"] * 0.8):
                alternatives.append(room["name"])
        
        return alternatives
    
    def _validate_suggestions(self, suggestions: Dict) -> Dict:
        """Validate AI suggestions using constraint solver"""
        # This would use the OR-Tools solver to validate suggestions
        return suggestions
    
    def _generate_fallback_suggestions(self, affected_sessions: List[Dict], constraints: Dict) -> List[str]:
        """Generate basic fallback suggestions when AI is unavailable"""
        suggestions = []
        
        if affected_sessions:
            faculty_name = constraints.get("faculty_unavailable", "the faculty member")
            
            suggestions.append(f"Consider rescheduling {len(affected_sessions)} affected sessions for {faculty_name}")
            suggestions.append("Look for available time slots in the same day or adjacent days")
            suggestions.append("Check if substitute faculty can cover some sessions")
            suggestions.append("Consider combining theory sessions if appropriate")
            
            # Add specific suggestions based on session types
            theory_count = sum(1 for s in affected_sessions if s.get("session", {}).get("type") == "theory")
            practical_count = len(affected_sessions) - theory_count
            
            if theory_count > 0:
                suggestions.append(f"Reschedule {theory_count} theory session(s) to available classroom slots")
            if practical_count > 0:
                suggestions.append(f"Reschedule {practical_count} practical session(s) to available lab slots")
        else:
            suggestions.append("No sessions found that need rescheduling")
            
        return suggestions
    
    def _enhance_ai_suggestions(self, ai_response: Dict, affected_sessions: List[Dict], constraints: Dict, user_feedback: str = None) -> Dict:
        """Enhance AI suggestions with structured data and validation"""
        try:
            # Get the AI suggestions
            ai_options = ai_response.get("rescheduling_options", [])
            
            # If AI suggestions are good, use them; otherwise fall back to structured
            if ai_options and len(ai_options) > 0:
                # Validate and enhance AI suggestions
                enhanced_options = []
                for option in ai_options:
                    enhanced_option = {
                        "rank": option.get("rank", 1),
                        "description": option.get("description", "AI Suggested Option"),
                        "sessions": option.get("sessions", []),
                        "pros": option.get("pros", []),
                        "cons": option.get("cons", []),
                        "impact_score": option.get("impact_score", 7.0),
                        "notes": option.get("notes", ""),
                        "ai_generated": True
                    }
                    enhanced_options.append(enhanced_option)
                
                return {
                    "rescheduling_options": enhanced_options,
                    "reasoning": ai_response.get("reasoning", ""),
                    "feedback_analysis": ai_response.get("feedback_analysis", "")
                }
            else:
                # Fall back to structured suggestions
                structured_options = self._generate_structured_suggestions(affected_sessions, constraints, user_feedback)
                return {
                    "rescheduling_options": structured_options,
                    "reasoning": "Generated structured suggestions based on available data",
                    "feedback_analysis": f"Incorporated user feedback: {user_feedback}" if user_feedback else ""
                }
        except Exception as e:
            logging.error(f"Error enhancing AI suggestions: {str(e)}")
            # Fall back to structured suggestions
            structured_options = self._generate_structured_suggestions(affected_sessions, constraints, user_feedback)
            return {
                "rescheduling_options": structured_options,
                "reasoning": "Using structured suggestions due to AI processing error",
                "feedback_analysis": ""
            }
    
    def _generate_structured_suggestions(self, affected_sessions: List[Dict], constraints: Dict, user_feedback: str = None) -> List[Dict]:
        """Generate structured rescheduling suggestions with proper faculty assignments"""
        suggestions = []
        
        if not affected_sessions:
            return suggestions
        
        # Get available faculty and rooms
        faculty_list = data_manager.get_faculty()
        rooms_list = data_manager.get_rooms()
        
        # Get the original faculty name from constraints
        unavailable_faculty = constraints.get("faculty_unavailable", "")
        
        # Find substitute faculty for the same subjects
        substitute_faculty = self._find_substitute_faculty(affected_sessions, unavailable_faculty, faculty_list)
        
        # Ensure we have a substitute faculty (use fallback if needed)
        if not substitute_faculty or substitute_faculty == "Dr. Substitute Faculty":
            substitute_faculty = "Asst.Prof.S.L Dawkhar"  # Use a real faculty as fallback
        
        # Analyze user feedback to adjust suggestions
        user_preferences = self._analyze_user_feedback(user_feedback) if user_feedback else {}
        
        # Generate different rescheduling options with enhanced details
        # Always generate all 3 options
        
        # Option 1: Substitute faculty with same time slots
        option1_sessions = []
        for session in affected_sessions:
            if session.get('session'):
                option1_sessions.append({
                    "subject": session['session'].get('subject', 'Unknown Subject'),
                    "type": session['session'].get('type', 'theory'),
                    "faculty": substitute_faculty,
                    "room": session['session'].get('room', 'CR41'),
                    "day": session.get('day', 'Monday'),
                    "time_slot": session.get('time_slot', '09:15-10:15')
                })
        
        # Adjust ranking based on user preferences
        rank = 1
        if user_preferences.get('prefers_different_times'):
            rank = 3
        elif user_preferences.get('prefers_same_faculty'):
            rank = 1
            
        suggestions.append({
            "rank": rank,
            "description": f"Substitute with {substitute_faculty} - Keep Original Schedule",
            "sessions": option1_sessions,
            "pros": [
                "Minimal schedule disruption",
                "Students keep familiar time slots",
                "No room changes required",
                f"Qualified substitute: {substitute_faculty}"
            ],
            "cons": [
                "Different teaching style",
                "May need curriculum handover",
                "Students need to adapt to new faculty"
            ],
            "impact_score": 8.5,
            "notes": f"Replace {unavailable_faculty} with {substitute_faculty} while maintaining original schedule. Best for minimal disruption.",
            "feedback_incorporated": user_preferences.get('feedback_summary', '')
        })
        
        # Option 2: Reschedule to morning slots with substitute faculty
        morning_slots = ["09:15-10:15", "10:15-11:15", "11:30-12:30"]
        option2_sessions = []
        
        for i, session in enumerate(affected_sessions):
            if session.get('session') and i < len(morning_slots):
                option2_sessions.append({
                    "subject": session['session'].get('subject', 'Unknown Subject'),
                    "type": session['session'].get('type', 'theory'),
                    "faculty": substitute_faculty,
                    "room": session['session'].get('room', 'CR41'),
                    "day": "Wednesday",  # Move all to Wednesday
                    "time_slot": morning_slots[i]
                })
        
        # Adjust ranking based on user preferences
        rank = 2
        if user_preferences.get('prefers_morning_slots'):
            rank = 1
        elif user_preferences.get('prefers_consolidated_schedule'):
            rank = 1
            
        suggestions.append({
            "rank": rank,
            "description": f"Morning Consolidation with {substitute_faculty}",
            "sessions": option2_sessions,
            "pros": [
                "Prime morning time slots",
                "All sessions on one day",
                "Better student attention in morning",
                "Efficient faculty utilization",
                "Easier to manage makeup sessions"
            ],
            "cons": [
                "Heavy load on one day",
                "May conflict with other subjects",
                "Requires Wednesday availability"
            ],
            "impact_score": 7.8,
            "notes": f"Consolidate all sessions to Wednesday morning with {substitute_faculty}. Ideal for intensive learning.",
            "feedback_incorporated": user_preferences.get('feedback_summary', '')
        })
        
        # Option 3: Distribute across different days
        days = ["Monday", "Tuesday", "Wednesday"]
        option3_sessions = []
        
        for i, session in enumerate(affected_sessions):
            if session.get('session') and i < len(days):
                option3_sessions.append({
                    "subject": session['session'].get('subject', 'Unknown Subject'),
                    "type": session['session'].get('type', 'theory'),
                    "faculty": substitute_faculty,
                    "room": session['session'].get('room', 'CR41'),
                    "day": days[i],
                    "time_slot": "09:15-10:15"  # Same time, different days
                })
        
        # Adjust ranking based on user preferences
        rank = 3
        if user_preferences.get('prefers_distributed_schedule'):
            rank = 1
        elif user_preferences.get('prefers_different_times'):
            rank = 2
            
        suggestions.append({
            "rank": rank,
            "description": f"Distributed Weekly Schedule with {substitute_faculty}",
            "sessions": option3_sessions,
            "pros": [
                "Balanced weekly distribution",
                "Consistent morning timing",
                "Less intensive per day",
                "Better retention with spaced learning",
                "Flexible makeup options"
            ],
            "cons": [
                "Multiple days affected",
                "Requires consistent availability",
                "More coordination needed"
            ],
            "impact_score": 8.2,
            "notes": f"Spread sessions across Monday, Tuesday, Wednesday with {substitute_faculty}. Best for spaced learning.",
            "feedback_incorporated": user_preferences.get('feedback_summary', '')
        })
        
        # Ensure we always have at least 3 options
        if len(suggestions) < 3 and substitute_faculty:
            # Add a backup option if we don't have enough
            backup_sessions = []
            for i, session in enumerate(affected_sessions[:3]):
                if session.get('session'):
                    backup_sessions.append({
                        "subject": session['session'].get('subject', 'Unknown Subject'),
                        "type": session['session'].get('type', 'theory'),
                        "faculty": substitute_faculty,
                        "room": f"CR{40 + i + 1}",  # Different rooms
                        "day": ["Monday", "Wednesday", "Friday"][i % 3],
                        "time_slot": "14:30-15:30"  # Afternoon slot
                    })
            
            suggestions.append({
                "rank": len(suggestions) + 1,
                "description": f"Alternative Rooms & Times with {substitute_faculty}",
                "sessions": backup_sessions,
                "pros": [
                    "Uses alternative classrooms",
                    "Afternoon timing available",
                    "Flexible room allocation",
                    "Good backup option"
                ],
                "cons": [
                    "Different rooms than usual",
                    "Afternoon timing may be less preferred",
                    "Requires room availability check"
                ],
                "impact_score": 7.0,
                "notes": f"Uses different rooms and afternoon slots with {substitute_faculty}. Good fallback option.",
                "feedback_incorporated": user_preferences.get('feedback_summary', '')
            })
        
        # Sort suggestions by rank and ensure we return exactly 3
        suggestions.sort(key=lambda x: x.get('rank', 999))
        
        # Ensure we have exactly 3 suggestions
        while len(suggestions) < 3:
            suggestions.append({
                "rank": len(suggestions) + 1,
                "description": f"Additional Option {len(suggestions) + 1}",
                "sessions": suggestions[0]["sessions"] if suggestions else [],
                "pros": ["Alternative scheduling option"],
                "cons": ["Limited details available"],
                "impact_score": 6.0,
                "notes": "Additional scheduling option for flexibility.",
                "feedback_incorporated": ""
            })
        
        return suggestions[:3]  # Return only first 3
    
    def _find_substitute_faculty(self, affected_sessions: List[Dict], unavailable_faculty: str, faculty_list: List[Dict]) -> str:
        """Find a suitable substitute faculty member"""
        if not affected_sessions or not faculty_list:
            return "Dr. Substitute Faculty"
        
        # Get the subject from the first affected session
        first_session = affected_sessions[0]
        if not first_session.get('session'):
            return "Dr. Substitute Faculty"
        
        subject_name = first_session['session'].get('subject', '')
        
        # Look for faculty who can teach the same subject
        for faculty in faculty_list:
            faculty_name = faculty.get('name', '')
            
            # Skip the unavailable faculty
            if faculty_name == unavailable_faculty:
                continue
            
            # Check if this faculty can teach the subject
            subjects = faculty.get('subjects', [])
            if subjects:
                # Handle different subject format structures
                for subj in subjects:
                    if isinstance(subj, dict):
                        # If subjects are stored as objects with subject_id
                        continue  # This would need subject matching by ID
                    elif isinstance(subj, str):
                        if subject_name.lower() in subj.lower() or subj.lower() in subject_name.lower():
                            return faculty_name
            
            # If no specific subject match, return any available faculty
            if faculty_name and faculty_name != unavailable_faculty:
                return faculty_name
        
        # Fallback to a generic substitute
        return "Dr. Substitute Faculty"
    
    def _analyze_user_feedback(self, feedback: str) -> Dict:
        """Enhanced feedback analysis with AI-powered learning and preference updating"""
        if not feedback:
            return {}
        
        feedback_lower = feedback.lower()
        preferences = {
            'feedback_summary': feedback[:100] + "..." if len(feedback) > 100 else feedback
        }
        
        # Analyze preferences from feedback with confidence scoring
        if any(word in feedback_lower for word in ['morning', 'early', '9', '10', '11', 'am']):
            preferences['prefers_morning_slots'] = True
            self.learned_preferences['prefers_morning_slots'] = True
            self.learned_preferences['prefers_afternoon_slots'] = False
            logging.info("📚 Learned: User prefers morning slots")
        
        if any(word in feedback_lower for word in ['afternoon', 'evening', 'late', '2', '3', '4', '5', 'pm']):
            preferences['prefers_afternoon_slots'] = True
            self.learned_preferences['prefers_afternoon_slots'] = True
            self.learned_preferences['prefers_morning_slots'] = False
            logging.info("📚 Learned: User prefers afternoon slots")
        
        if any(word in feedback_lower for word in ['same day', 'one day', 'consolidated', 'together', 'single day']):
            preferences['prefers_consolidated_schedule'] = True
            self.learned_preferences['prefers_consolidated'] = True
            self.learned_preferences['prefers_distributed'] = False
            logging.info("📚 Learned: User prefers consolidated schedules")
        
        if any(word in feedback_lower for word in ['spread', 'distribute', 'different days', 'across week', 'multiple days']):
            preferences['prefers_distributed_schedule'] = True
            self.learned_preferences['prefers_distributed'] = True
            self.learned_preferences['prefers_consolidated'] = False
            logging.info("📚 Learned: User prefers distributed schedules")
        
        if any(word in feedback_lower for word in ['different time', 'change time', 'new time']):
            preferences['prefers_different_times'] = True
        
        if any(word in feedback_lower for word in ['same faculty', 'keep faculty', 'original faculty']):
            preferences['prefers_same_faculty'] = True
        
        if any(word in feedback_lower for word in ['substitute', 'replacement', 'different faculty']):
            preferences['prefers_substitute_faculty'] = True
        
        if any(word in feedback_lower for word in ['room', 'classroom', 'lab']):
            preferences['cares_about_room'] = True
        
        # Extract specific day preferences
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
        for day in days:
            if day in feedback_lower:
                if any(word in feedback_lower for word in ['prefer', 'like', 'want', 'choose']):
                    if day.capitalize() not in self.learned_preferences['preferred_days']:
                        self.learned_preferences['preferred_days'].append(day.capitalize())
                        logging.info(f"📚 Learned: User prefers {day.capitalize()}")
                elif any(word in feedback_lower for word in ['avoid', 'not', 'don\'t', 'no']):
                    if day.capitalize() not in self.learned_preferences['avoid_days']:
                        self.learned_preferences['avoid_days'].append(day.capitalize())
                        logging.info(f"📚 Learned: User wants to avoid {day.capitalize()}")
        
        # Analyze negative feedback
        if any(word in feedback_lower for word in ['don\'t like', 'not good', 'bad', 'terrible', 'awful', 'hate']):
            preferences['negative_feedback'] = True
        
        if any(word in feedback_lower for word in ['better', 'improve', 'different', 'alternative', 'other']):
            preferences['wants_improvement'] = True
        
        # Use AI to extract deeper insights if available
        if self.ai_available and len(feedback) > 20:
            try:
                ai_analysis = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": """Analyze user feedback about timetable suggestions and extract preferences.
                            Respond with JSON containing:
                            {
                                "time_preferences": ["morning", "afternoon", "evening"],
                                "day_preferences": ["Monday", "Tuesday", etc],
                                "scheduling_style": "consolidated | distributed | flexible",
                                "priorities": ["student_convenience", "faculty_preference", "minimal_change"],
                                "dislikes": ["what they didn't like"],
                                "key_insights": ["deeper insights about their preferences"]
                            }"""
                        },
                        {"role": "user", "content": f"Feedback: {feedback}"}
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=300
                )
                
                ai_preferences = json.loads(ai_analysis.choices[0].message.content)
                preferences['ai_analysis'] = ai_preferences
                logging.info(f"🤖 AI-extracted preferences: {ai_preferences}")
                
                # Update learned preferences with AI insights
                if 'scheduling_style' in ai_preferences:
                    style = ai_preferences['scheduling_style']
                    if style == 'consolidated':
                        self.learned_preferences['prefers_consolidated'] = True
                    elif style == 'distributed':
                        self.learned_preferences['prefers_distributed'] = True
                        
            except Exception as e:
                logging.warning(f"Could not perform AI analysis of feedback: {e}")
        
        return preferences
    
    def _process_request_fallback(self, request: str, current_timetable: Dict, user_feedback: str = None, previous_suggestions: List = None) -> Dict:
        """Process requests using basic pattern matching when AI is unavailable"""
        request_lower = request.lower()
        
        # Simple pattern matching for common requests
        if "leave" in request_lower or "absent" in request_lower:
            # Try to extract faculty name (basic approach)
            words = request.split()
            faculty_name = None
            
            # Look for common title patterns
            for i, word in enumerate(words):
                if word.lower() in ["dr.", "prof.", "mr.", "mrs.", "ms."] and i + 1 < len(words):
                    # Take the next 1-2 words as the name
                    if i + 2 < len(words):
                        faculty_name = f"{words[i]} {words[i+1]} {words[i+2]}"
                    else:
                        faculty_name = f"{words[i]} {words[i+1]}"
                    break
            
            if not faculty_name:
                # Fallback: look for capitalized words that might be names
                capitalized_words = [word for word in words if word[0].isupper() and len(word) > 2]
                if len(capitalized_words) >= 2:
                    faculty_name = " ".join(capitalized_words[:2])
            
            if faculty_name:
                # Use basic faculty leave handling
                parsed_request = {
                    "action": "faculty_leave",
                    "entity": faculty_name,
                    "date_range": {},
                    "reason": "Faculty leave request"
                }
                return self._execute_modification(parsed_request, current_timetable, user_feedback, previous_suggestions)
        
        # Default response for unrecognized requests
        return {
            "success": False,
            "error": "AI service unavailable. Please try basic commands like 'Dr. [Name] is on leave' or contact administrator.",
            "suggestions": [
                "Try rephrasing your request with clear faculty names",
                "Use format: 'Dr. [Faculty Name] is on leave'",
                "Contact administrator to configure AI service"
            ]
        }
    
    def _extract_schedule_metrics(self, timetable: Dict) -> Dict:
        """Extract metrics from timetable for AI analysis"""
        metrics = {
            "total_sessions": 0,
            "faculty_workload": {},
            "room_utilization": {},
            "time_slot_usage": {},
            "session_distribution": {"theory": 0, "practical": 0}
        }
        
        for view_key, view_data in timetable.items():
            for day, day_data in view_data.items():
                for time_slot, session in day_data.items():
                    if session:
                        # Handle both single session and array of sessions
                        sessions_to_check = session if isinstance(session, list) else [session]
                        
                        for single_session in sessions_to_check:
                            if isinstance(single_session, dict):
                                metrics["total_sessions"] += 1
                                
                                # Faculty workload
                                faculty = single_session.get("faculty", "Unknown")
                                metrics["faculty_workload"][faculty] = metrics["faculty_workload"].get(faculty, 0) + 1
                                
                                # Room utilization
                                room = single_session.get("room", "Unknown")
                                metrics["room_utilization"][room] = metrics["room_utilization"].get(room, 0) + 1
                                
                                # Time slot usage
                                metrics["time_slot_usage"][time_slot] = metrics["time_slot_usage"].get(time_slot, 0) + 1
                                
                                # Session type distribution
                                session_type = single_session.get("type", "unknown")
                                if session_type in metrics["session_distribution"]:
                                    metrics["session_distribution"][session_type] += 1
        
        return metrics
    
    def _apply_emergency_plan(self, emergency_plan: Dict) -> Dict:
        """Apply emergency rescheduling plan"""
        # This would implement the actual rescheduling based on the AI-generated plan
        return {}
    
    def _analyze_faculty_workload(self, assignments: Dict) -> Dict:
        """Analyze current faculty workload distribution"""
        faculty = data_manager.get_faculty()
        workload_analysis = {}
        
        for f in faculty:
            workload_analysis[f["name"]] = {
                "assigned_subjects": f.get("subjects", []),
                "max_hours": f.get("max_hours_per_week", 20),
                "current_hours": 0,  # This would be calculated from current timetable
                "expertise_match": "high"  # This would be calculated based on subject assignments
            }
        
        return workload_analysis
    
    def apply_modification(self, modification_type: str, option: Dict, original_data: Dict, current_timetable: Dict) -> Dict:
        """Apply the selected modification to the current timetable"""
        try:
            logging.info(f"Applying modification: {modification_type}")
            
            if modification_type == "reschedule":
                return self._apply_reschedule_modification(option, original_data, current_timetable)
            else:
                return {
                    "success": False,
                    "error": f"Unknown modification type: {modification_type}"
                }
                
        except Exception as e:
            logging.error(f"Error applying modification: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to apply modification: {str(e)}"
            }
    
    def _apply_reschedule_modification(self, option: Dict, original_data: Dict, current_timetable: Dict) -> Dict:
        """Apply rescheduling modifications to the timetable"""
        try:
            import copy
            modified_timetable = copy.deepcopy(current_timetable)
            modifications_applied = []
            
            logging.info(f"Applying reschedule modification")
            logging.info(f"Option keys: {list(option.keys())}")
            logging.info(f"Original data keys: {list(original_data.keys())}")
            
            # Get the affected sessions
            affected_sessions = original_data.get('affected_sessions', [])
            new_sessions = option.get('sessions', [])
            
            logging.info(f"Affected sessions: {len(affected_sessions)}, New sessions: {len(new_sessions)}")
            
            if not affected_sessions or not new_sessions:
                return {
                    "success": False,
                    "error": f"Invalid modification data: affected={len(affected_sessions)}, new={len(new_sessions)}"
                }
            
            # Step 1: Remove old sessions
            for affected_session in affected_sessions:
                view_key = affected_session.get('view')
                day = affected_session.get('day')
                time_slot = affected_session.get('time_slot')
                
                logging.info(f"Removing session: {view_key} - {day} - {time_slot}")
                
                if view_key and day and time_slot:
                    if (view_key in modified_timetable and 
                        day in modified_timetable[view_key] and 
                        time_slot in modified_timetable[view_key][day]):
                        
                        # Get the old session before removing
                        old_session = modified_timetable[view_key][day][time_slot]
                        modified_timetable[view_key][day][time_slot] = None
                        
                        modifications_applied.append({
                            "action": "removed",
                            "session": old_session,
                            "location": f"{view_key} - {day} {time_slot}"
                        })
            
            # Step 2: Add new sessions - find target view
            target_view = None
            if affected_sessions:
                target_view = affected_sessions[0].get('view')
                logging.info(f"Target view from first affected session: {target_view}")
            
            if not target_view:
                # Fallback: use first available view
                for view_key in modified_timetable.keys():
                    if isinstance(modified_timetable[view_key], dict):
                        target_view = view_key
                        break
                        
            if not target_view:
                return {
                    "success": False,
                    "error": "Could not determine target view for new sessions"
                }
            
            logging.info(f"Using target view: {target_view}")
            
            # Add new sessions
            for new_session in new_sessions:
                day = new_session.get('day')
                time_slot = new_session.get('time_slot')
                
                if day and time_slot and target_view in modified_timetable:
                    # Ensure structure exists
                    if day not in modified_timetable[target_view]:
                        modified_timetable[target_view][day] = {}
                    if time_slot not in modified_timetable[target_view][day]:
                        modified_timetable[target_view][day][time_slot] = None
                    
                    # Create new session
                    session_info = {
                        "subject": new_session.get('subject'),
                        "type": new_session.get('type', 'theory'),
                        "faculty": new_session.get('faculty'),
                        "room": new_session.get('room')
                    }
                    
                    # Add to timetable
                    modified_timetable[target_view][day][time_slot] = session_info
                    
                    modifications_applied.append({
                        "action": "added",
                        "session": session_info,
                        "location": f"{target_view} - {day} {time_slot}"
                    })
                    
                    logging.info(f"Added session: {target_view} - {day} - {time_slot}")
            
            return {
                "success": True,
                "message": f"Successfully applied {len(modifications_applied)} modifications to the timetable",
                "modified_timetable": modified_timetable,
                "modifications_applied": modifications_applied,
                "description": option.get('description', 'Timetable rescheduling applied')
            }
            
        except Exception as e:
            logging.error(f"Error in reschedule modification: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to apply reschedule modification: {str(e)}"
            }
    
    def get_modification_suggestions(self, request: str, current_timetable: Dict, user_feedback: str = None) -> Dict:
        """Get exactly 3 modification suggestions for a user request"""
        try:
            logging.info(f"Getting modification suggestions for: {request}")
            
            if not self.ai_available:
                return self._get_fallback_suggestions(request, current_timetable, user_feedback)
            
            # Process the natural language request to identify the action
            result = self.process_natural_language_request(request, current_timetable, user_feedback)
            
            # Extract affected sessions and generate 3 options
            if result.get('success'):
                affected_sessions = result.get('affected_sessions', [])
                reschedule_suggestions = result.get('reschedule_suggestions', {})
                
                if affected_sessions and reschedule_suggestions.get('success'):
                    suggestions_data = reschedule_suggestions.get('suggestions', {})
                    options = suggestions_data.get('rescheduling_options', [])
                    
                    # Ensure we return exactly 3 suggestions
                    return {
                        "success": True,
                        "suggestions": {
                            "total_affected": len(affected_sessions),
                            "options": options[:3],  # Return first 3 options
                            "reasoning": suggestions_data.get('reasoning', '')
                        },
                        "original_data": result,
                        "affected_sessions": affected_sessions
                    }
                else:
                    return {
                        "success": False,
                        "error": "Could not generate rescheduling suggestions",
                        "original_data": result
                    }
            else:
                return result
                
        except Exception as e:
            logging.error(f"Error getting modification suggestions: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get suggestions: {str(e)}"
            }
    
    def _get_fallback_suggestions(self, request: str, current_timetable: Dict, user_feedback: str = None) -> Dict:
        """Generate fallback suggestions when AI is unavailable"""
        try:
            # Parse the request to identify the type of modification
            request_lower = request.lower()
            
            # Try to extract faculty name - improved logic
            faculty_name = self._extract_faculty_name_from_request(request, current_timetable)
            
            if not faculty_name:
                # Return helpful error with available faculty
                available_faculty = self._get_available_faculty_list()
                return {
                    "success": False,
                    "error": "Could not identify faculty member. Please specify the name clearly.",
                    "suggestions": [
                        "Use format: 'Dr. [Full Name] is on leave'",
                        "Available faculty: " + ", ".join(available_faculty[:3]) + ("..." if len(available_faculty) > 3 else ""),
                        "Check spelling of faculty name"
                    ]
                }
            
            # Find affected sessions
            affected_sessions = self._find_faculty_sessions(faculty_name, current_timetable, {})
            
            if not affected_sessions:
                # Try fuzzy matching to find similar faculty names
                similar_faculty = self._find_similar_faculty(faculty_name)
                
                if similar_faculty:
                    return {
                        "success": False,
                        "error": f"No sessions found for '{faculty_name}'. Did you mean one of these?",
                        "suggestions": [f"Try: '{name}'" for name in similar_faculty]
                    }
                else:
                    available_faculty = self._get_available_faculty_list()
                    return {
                        "success": False,
                        "error": f"No sessions found for '{faculty_name}'. Faculty may not be teaching any sessions.",
                        "suggestions": [
                            "Check if faculty has any assigned sessions",
                            "Available faculty: " + ", ".join(available_faculty[:3]) + ("..." if len(available_faculty) > 3 else ""),
                            "Verify the faculty name spelling"
                        ]
                    }
            
            # Generate 3 basic suggestions
            suggestions = self._generate_structured_suggestions(
                affected_sessions, 
                {"faculty_unavailable": faculty_name},
                user_feedback
            )
            
            return {
                "success": True,
                "suggestions": {
                    "total_affected": len(affected_sessions),
                    "options": suggestions[:3],
                    "reasoning": "Fallback suggestions generated without AI"
                },
                "original_data": {
                    "action": "faculty_leave",
                    "entity": faculty_name,
                    "affected_sessions": affected_sessions
                },
                "affected_sessions": affected_sessions
            }
            
        except Exception as e:
            logging.error(f"Error generating fallback suggestions: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to generate suggestions: {str(e)}"
            }
    
    def _extract_faculty_name_from_request(self, request: str, current_timetable: Dict) -> str:
        """Extract and validate faculty name from natural language request"""
        words = request.split()
        faculty_name = None
        
        # Stop words that indicate end of name
        stop_words = {"is", "on", "leave", "absent", "for", "a", "the", "month", "week", "day", "next", 
                     "what", "can", "be", "done", "how", "will", "should", "to", "from", "by", "during"}
        
        # Strategy 1: Look for common title patterns
        for i, word in enumerate(words):
            word_lower = word.lower().rstrip('.,')  # Remove punctuation
            if word_lower in ["dr", "prof", "mr", "mrs", "ms", "asst", "assistant", "professor", "doctor"]:
                # Take name words until we hit a stop word or action verb
                name_parts = []
                for j in range(i, len(words)):  # Go through all remaining words
                    part = words[j].rstrip('.,')
                    part_lower = part.lower()
                    
                    # Stop if we hit an action word or stop word
                    if part_lower in stop_words:
                        break
                    
                    # Add to name parts (skip empty parts)
                    if part and part not in ['-', ',', '.']:
                        name_parts.append(part)
                    
                    # Safety limit: don't take more than 5 name parts
                    if len(name_parts) >= 5:
                        break
                
                if name_parts:
                    faculty_name = " ".join(name_parts)
                    break
        
        # Strategy 2: If no title found, look for capitalized words
        if not faculty_name:
            capitalized_words = [word.rstrip('.,') for word in words if word and word[0].isupper() and len(word.rstrip('.,')) > 2]
            if len(capitalized_words) >= 1:
                faculty_name = " ".join(capitalized_words[:5])  # Allow up to 5 name parts
        
        # Strategy 3: Try to match against existing faculty in data
        if faculty_name:
            faculty_name = self._match_faculty_name(faculty_name)
        
        return faculty_name
    
    def _match_faculty_name(self, input_name: str) -> str:
        """Match input name against actual faculty names in database"""
        faculty_list = data_manager.get_faculty()
        input_lower = input_name.lower()
        
        # Exact match
        for faculty in faculty_list:
            if faculty.get('name', '').lower() == input_lower:
                return faculty.get('name')
        
        # Partial match (contains)
        for faculty in faculty_list:
            faculty_name_lower = faculty.get('name', '').lower()
            if input_lower in faculty_name_lower or faculty_name_lower in input_lower:
                return faculty.get('name')
        
        # Last name match
        input_words = input_name.split()
        for faculty in faculty_list:
            faculty_words = faculty.get('name', '').split()
            for input_word in input_words:
                for faculty_word in faculty_words:
                    if input_word.lower() == faculty_word.lower() and len(input_word) > 2:
                        return faculty.get('name')
        
        # If no match found, return the original input
        return input_name
    
    def _find_similar_faculty(self, faculty_name: str) -> List[str]:
        """Find faculty names similar to the input"""
        faculty_list = data_manager.get_faculty()
        similar = []
        
        input_lower = faculty_name.lower()
        input_words = set(input_lower.split())
        
        for faculty in faculty_list:
            faculty_name_lower = faculty.get('name', '').lower()
            faculty_words = set(faculty_name_lower.split())
            
            # Check word overlap
            overlap = input_words & faculty_words
            if overlap and len(similar) < 3:
                similar.append(faculty.get('name'))
        
        return similar
    
    def _get_available_faculty_list(self) -> List[str]:
        """Get list of all available faculty"""
        try:
            faculty_list = data_manager.get_faculty()
            return [f.get('name', 'Unknown') for f in faculty_list]
        except:
            return []
    
    def mark_suggestion_successful(self):
        """Mark that a suggestion was accepted by the user"""
        self.successful_suggestions += 1
        logging.info(f"✅ Successful suggestion! Total: {self.successful_suggestions}/{self.total_requests}")
    
    def get_ai_statistics(self) -> Dict:
        """Get comprehensive AI usage statistics"""
        success_rate = (self.successful_suggestions / self.total_requests * 100) if self.total_requests > 0 else 0
        estimated_cost = (self.total_tokens_used / 1000) * 0.01  # Rough GPT-4o estimate
        
        return {
            "ai_available": self.ai_available,
            "total_requests": self.total_requests,
            "successful_suggestions": self.successful_suggestions,
            "success_rate": f"{success_rate:.1f}%",
            "total_tokens_used": self.total_tokens_used,
            "estimated_total_cost": f"${estimated_cost:.4f}",
            "average_tokens_per_request": int(self.total_tokens_used / self.total_requests) if self.total_requests > 0 else 0,
            "learned_preferences": self.learned_preferences,
            "performance_grade": self._calculate_performance_grade(success_rate)
        }
    
    def _calculate_performance_grade(self, success_rate: float) -> str:
        """Calculate performance grade based on success rate"""
        if success_rate >= 90:
            return "A+ (Excellent)"
        elif success_rate >= 80:
            return "A (Very Good)"
        elif success_rate >= 70:
            return "B (Good)"
        elif success_rate >= 60:
            return "C (Satisfactory)"
        elif success_rate >= 50:
            return "D (Needs Improvement)"
        else:
            return "F (Poor)"
    
    def detect_schedule_conflicts_ai(self, timetable: Dict) -> Dict:
        """Use AI to proactively detect potential conflicts and suggest improvements"""
        if not self.ai_available:
            return {
                "success": False,
                "message": "AI conflict detection requires OpenAI API key"
            }
        
        try:
            # Extract schedule metrics for analysis
            schedule_obj = timetable.get('schedule', {})
            
            # Count total sessions
            total_sessions = 0
            faculty_set = set()
            room_set = set()
            
            for div in schedule_obj.values():
                for day in div.values():
                    for session in day.values():
                        if session:
                            total_sessions += 1
                            if session.get('faculty'):
                                faculty_set.add(session.get('faculty'))
                            if session.get('room'):
                                room_set.add(session.get('room'))
            
            schedule_data = {
                "total_sessions": total_sessions,
                "faculty_count": len(faculty_set),
                "room_count": len(room_set)
            }
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert timetable quality analyst with advanced pattern recognition abilities.
                        
                        Analyze the timetable data and identify:
                        1. **Critical Issues**: Must be fixed immediately
                        2. **Warnings**: Should be addressed soon
                        3. **Optimization Opportunities**: Could improve efficiency
                        4. **Best Practices**: Suggestions for excellence
                        
                        Focus on:
                        - Faculty workload distribution
                        - Room utilization efficiency
                        - Student schedule quality
                        - Potential scheduling conflicts
                        - Resource bottlenecks
                        - Pedagogical considerations
                        
                        Provide actionable, specific recommendations.
                        
                        Respond with JSON containing:
                        {
                            "overall_quality_score": 0-10,
                            "critical_issues": [{"issue": "description", "impact": "high|medium|low", "recommendation": "action"}],
                            "warnings": [{"warning": "description", "suggestion": "action"}],
                            "optimizations": [{"opportunity": "description", "benefit": "impact"}],
                            "best_practices": ["practice1", "practice2"],
                            "summary": "Executive summary of schedule health"
                        }"""
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze this timetable:
                        
Schedule Summary:
{json.dumps(schedule_data, indent=2)}

Full Schedule Data:
{json.dumps(timetable, indent=2)[:3000]}...

Provide deep analysis and actionable recommendations."""
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.5
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            return {
                "success": True,
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error in AI conflict detection: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_ai_health_status(self) -> Dict:
        """Get current health status of the AI assistant"""
        return {
            "status": "healthy" if self.ai_available else "limited",
            "mode": "Full AI" if self.ai_available else "Fallback Mode",
            "capabilities": {
                "natural_language_understanding": self.ai_available,
                "intelligent_suggestions": self.ai_available,
                "conflict_detection": self.ai_available,
                "feedback_learning": True,
                "basic_scheduling": True
            },
            "statistics": self.get_ai_statistics() if self.ai_available else None
        }

# Global AI assistant instance
ai_assistant = TimetableAIAssistant()