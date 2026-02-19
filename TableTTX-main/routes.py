from flask import render_template, request, jsonify, redirect, url_for, flash, session, send_file
from app import app
from models import data_manager
from solver import timetable_solver
from ai_assistant import ai_assistant
from datetime import datetime
import logging
from io import BytesIO
from functools import wraps
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# Authentication credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin@123'

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password. Please try again.', 'error')
    
    # If already logged in, redirect to home
    if session.get('logged_in'):
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/configure')
@login_required
def configure():
    """Academic structure configuration page"""
    structure = data_manager.get_academic_structure()
    return render_template('configure.html', structure=structure)

@app.route('/configure', methods=['POST'])
@login_required
def update_configure():
    """Update academic structure configuration"""
    try:
        structure = {
            "years": int(request.form.get('years', 3)),
            "divisions_per_year": int(request.form.get('divisions_per_year', 2)),
            "batches_per_division": int(request.form.get('batches_per_division', 3)),
            "theory_duration": int(request.form.get('theory_duration', 60)),
            "practical_duration": int(request.form.get('practical_duration', 120)),
            "time_slots": request.form.get('time_slots', '').split('\n'),
            "days": request.form.getlist('days')
        }
        
        # Clean up time slots (remove empty lines)
        structure["time_slots"] = [slot.strip() for slot in structure["time_slots"] if slot.strip()]
        
        if not structure["time_slots"]:
            structure["time_slots"] = [
                "09:00-10:00", "10:00-11:00", "11:15-12:15", "12:15-13:15",
                "14:15-15:15", "15:15-16:15", "16:30-17:30", "17:30-18:30"
            ]
        
        if not structure["days"]:
            structure["days"] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        
        data_manager.update_academic_structure(structure)
        flash('Academic structure updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating configuration: {str(e)}', 'error')
    
    return redirect(url_for('configure'))

@app.route('/subjects')
@login_required
def subjects():
    """Subjects management page"""
    subjects_list = data_manager.get_subjects()
    return render_template('subjects.html', subjects=subjects_list)

@app.route('/subjects/add', methods=['POST'])
@login_required
def add_subject():
    """Add a new subject"""
    try:
        subject = {
            "name": request.form.get('name'),
            "type": request.form.get('type'),
            "code": request.form.get('code'),
            "hours_per_week": int(request.form.get('hours_per_week', 3)),
            "year": int(request.form.get('year', 1)),
            "semester": int(request.form.get('semester', 1))
        }
        data_manager.add_subject(subject)
        flash('Subject added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding subject: {str(e)}', 'error')
    
    return redirect(url_for('subjects'))

@app.route('/subjects/edit/<int:subject_id>', methods=['POST'])
@login_required
def edit_subject(subject_id):
    """Edit/update an existing subject"""
    try:
        subject = {
            "name": request.form.get('name'),
            "type": request.form.get('type'),
            "code": request.form.get('code'),
            "hours_per_week": int(request.form.get('hours_per_week', 3)),
            "year": int(request.form.get('year', 1)),
            "semester": int(request.form.get('semester', 1))
        }
        data_manager.update_subject(subject_id, subject)
        flash('Subject updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating subject: {str(e)}', 'error')
    
    return redirect(url_for('subjects'))

@app.route('/subjects/delete/<int:subject_id>')
@login_required
def delete_subject(subject_id):
    """Delete a subject"""
    try:
        data_manager.delete_subject(subject_id)
        flash('Subject deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting subject: {str(e)}', 'error')
    
    return redirect(url_for('subjects'))

@app.route('/faculty')
@login_required
def faculty():
    """Faculty management page"""
    faculty_list = data_manager.get_faculty()
    subjects_list = data_manager.get_subjects()
    structure = data_manager.get_academic_structure()

    # Group subjects by academic year for simpler rendering in the template
    subjects_by_year = {}
    years_with_subjects = []
    for subject in subjects_list:
        try:
            year_value = subject.get('year') if isinstance(subject, dict) else getattr(subject, 'year', None)
        except Exception:
            year_value = None
        if year_value is None:
            continue
        if year_value not in subjects_by_year:
            subjects_by_year[year_value] = []
            years_with_subjects.append(year_value)
        subjects_by_year[year_value].append(subject)

    years_with_subjects = sorted(years_with_subjects)

    # Divisions per year from configuration
    divisions_per_year = int(structure.get('divisions_per_year', 2) or 2)
    available_divisions = list(range(1, divisions_per_year + 1))
    # Batches per division (for practicals) and user-friendly letters A, B, C, ...
    batches_per_division = int(structure.get('batches_per_division', 3) or 3)
    available_batches = list(range(1, batches_per_division + 1))
    available_batch_letters = [chr(ord('A') + i) for i in range(batches_per_division)]

    # Build a quick lookup for pre-filling edit modals: member_id -> {subject_id: divisions}
    faculty_assignments_map = {}
    for member in faculty_list:
        subject_to_divisions = {}
        assignments = member.get('subjects', []) or []
        for a in assignments:
            if isinstance(a, dict):
                sid = a.get('subject_id')
                divisions = a.get('divisions', []) or []
                batches = a.get('batches', []) or []
            else:
                sid = a
                divisions = []
                batches = []
            if sid is not None:
                subject_to_divisions[sid] = {"divisions": divisions, "batches": batches}
        faculty_assignments_map[member.get('id')] = subject_to_divisions

    # Compute hours/week for each faculty based on assigned subjects
    # Practicals: hours × batch_count (each batch is a separate session)
    # Theory/Tutorial: hours × division_count (same lecture repeated per division)
    subject_lookup_map = {s.get('id'): s for s in subjects_list}
    for member in faculty_list:
        total_hours = 0
        for a in member.get('subjects', []) or []:
            if isinstance(a, dict):
                sid = a.get('subject_id')
                subj = subject_lookup_map.get(sid, {})
                base_hours = int(subj.get('hours_per_week', 0) or 0)
                subj_type = subj.get('type', 'theory')
                if subj_type == 'practical':
                    batch_count = len(a.get('batches', []))
                    total_hours += base_hours * max(batch_count, 1)
                else:
                    div_count = len(a.get('divisions', []))
                    total_hours += base_hours * max(div_count, 1)
            else:
                sid = a
                total_hours += int(subject_lookup_map.get(sid, {}).get('hours_per_week', 0) or 0)
        member['hours_per_week'] = total_hours

    return render_template(
        'faculty.html',
        faculty=faculty_list,
        subjects=subjects_list,
        subjects_by_year=subjects_by_year,
        years_with_subjects=years_with_subjects,
        available_divisions=available_divisions,
        available_batches=available_batches,
        available_batch_letters=available_batch_letters,
        faculty_assignments_map=faculty_assignments_map,
    )

@app.route('/faculty/add', methods=['POST'])
@login_required
def add_faculty():
    """Add a new faculty member"""
    try:
        # Collect selected subjects and their division assignments
        selected_subject_ids = [int(s) for s in request.form.getlist('subjects') if s]
        subjects_list = data_manager.get_subjects()
        subject_lookup = {s.get('id'): s for s in subjects_list}

        assignments = []
        for sid in selected_subject_ids:
            divisions_key = f'divisions_{sid}'
            divisions = [int(d) for d in request.form.getlist(divisions_key)]
            # Optional batches per subject (for practicals)
            batches_key = f'batches_{sid}'
            batches = [int(b) for b in request.form.getlist(batches_key)]
            subj = subject_lookup.get(sid, {})
            assignments.append({
                'subject_id': sid,
                'year': int(subj.get('year', 0) or 0),
                'semester': int(subj.get('semester', 0) or 0),
                'divisions': divisions,
                'batches': batches
            })

        # Compute hours/week from selected subjects
        # Practicals: hours × batch_count; Theory: hours × division_count
        hours_per_week = 0
        for a in assignments:
            sid = a.get('subject_id')
            subj = subject_lookup.get(sid, {})
            base_hours = int(subj.get('hours_per_week', 0) or 0)
            if subj.get('type') == 'practical':
                batch_count = len(a.get('batches', []))
                hours_per_week += base_hours * max(batch_count, 1)
            else:
                div_count = len(a.get('divisions', []))
                hours_per_week += base_hours * max(div_count, 1)

        faculty_member = {
            "name": request.form.get('name'),
            "initials": request.form.get('initials', '').upper(),
            "department": request.form.get('department'),
            "subjects": assignments,
            "hours_per_week": hours_per_week
        }

        data_manager.add_faculty(faculty_member)
        flash('Faculty member added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding faculty member: {str(e)}', 'error')
    
    return redirect(url_for('faculty'))

@app.route('/faculty/edit/<int:faculty_id>', methods=['POST'])
@login_required
def edit_faculty(faculty_id):
    """Edit/update an existing faculty member"""
    try:
        selected_subject_ids = [int(s) for s in request.form.getlist('subjects') if s]
        subjects_list = data_manager.get_subjects()
        subject_lookup = {s.get('id'): s for s in subjects_list}

        assignments = []
        for sid in selected_subject_ids:
            divisions_key = f'divisions_{sid}'
            divisions = [int(d) for d in request.form.getlist(divisions_key)]
            batches_key = f'batches_{sid}'
            batches = [int(b) for b in request.form.getlist(batches_key)]
            subj = subject_lookup.get(sid, {})
            assignments.append({
                'subject_id': sid,
                'year': int(subj.get('year', 0) or 0),
                'semester': int(subj.get('semester', 0) or 0),
                'divisions': divisions,
                'batches': batches
            })

        # Compute hours/week from selected subjects
        # Practicals: hours × batch_count; Theory: hours × division_count
        hours_per_week = 0
        for a in assignments:
            sid = a.get('subject_id')
            subj = subject_lookup.get(sid, {})
            base_hours = int(subj.get('hours_per_week', 0) or 0)
            if subj.get('type') == 'practical':
                batch_count = len(a.get('batches', []))
                hours_per_week += base_hours * max(batch_count, 1)
            else:
                div_count = len(a.get('divisions', []))
                hours_per_week += base_hours * max(div_count, 1)

        faculty_member = {
            "name": request.form.get('name'),
            "initials": request.form.get('initials', '').upper(),
            "department": request.form.get('department'),
            "subjects": assignments,
            "hours_per_week": hours_per_week
        }

        data_manager.update_faculty(faculty_id, faculty_member)
        flash('Faculty member updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating faculty member: {str(e)}', 'error')
    
    return redirect(url_for('faculty'))

@app.route('/faculty/delete/<int:faculty_id>')
@login_required
def delete_faculty(faculty_id):
    """Delete a faculty member"""
    try:
        data_manager.delete_faculty(faculty_id)
        flash('Faculty member deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting faculty member: {str(e)}', 'error')
    
    return redirect(url_for('faculty'))

@app.route('/rooms')
@login_required
def rooms():
    """Rooms management page"""
    rooms_list = data_manager.get_rooms()
    return render_template('rooms.html', rooms=rooms_list)

@app.route('/rooms/add', methods=['POST'])
@login_required
def add_room():
    """Add a new room"""
    try:
        room = {
            "name": request.form.get('name'),
            "type": request.form.get('type'),
            "capacity": int(request.form.get('capacity', 60)),
            "building": request.form.get('building', ''),
            "equipment": request.form.get('equipment', '')
        }
        data_manager.add_room(room)
        flash('Room added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding room: {str(e)}', 'error')
    
    return redirect(url_for('rooms'))

@app.route('/rooms/delete/<int:room_id>')
@login_required
def delete_room(room_id):
    """Delete a room"""
    try:
        data_manager.delete_room(room_id)
        flash('Room deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting room: {str(e)}', 'error')
    
    return redirect(url_for('rooms'))

@app.route('/generate')
@login_required
def generate():
    """Timetable generation page"""
    return render_template('generate.html')

@app.route('/generate', methods=['POST'])
@login_required
def generate_timetable():
    """Generate timetable using AI solver"""
    try:
        # Read semester mode from form: 'odd' or 'even'
        semester_mode = request.form.get('semester_mode', 'odd')
        result = timetable_solver.generate_timetable(semester_mode=semester_mode)
        
        if "error" in result:
            flash(f'Error generating timetable: {result["error"]}', 'error')
            return redirect(url_for('generate'))

        # Show warnings if any
        if result.get("warnings"):
            for warning in result["warnings"]:
                flash(f'Warning: {warning}', 'warning')

        # Store the result in session for AI Assistant use
        if "timetable" in result:
            session['current_timetable'] = result["timetable"]
            session['timetable_saved_at'] = datetime.now().isoformat()

            # Auto-save timetable (overwrites if same config fingerprint)
            try:
                data_manager.save_timetable(
                    result["timetable"],
                    semester_mode=semester_mode,
                    auto_save=True
                )
                flash('Timetable auto-saved.', 'info')
            except Exception as save_err:
                logging.error(f"Auto-save failed: {save_err}")

        return render_template('timetable.html', result=result)
        
    except Exception as e:
        logging.error(f"Error in generate_timetable: {str(e)}")
        flash(f'Error generating timetable: {str(e)}', 'error')
        return redirect(url_for('generate'))

@app.route('/api/timetable', methods=['POST'])
@login_required
def api_generate_timetable():
    """API endpoint for timetable generation"""
    try:
        result = timetable_solver.generate_timetable()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/current-timetable', methods=['GET'])
@login_required
def api_get_current_timetable():
    """API endpoint to get current timetable from session"""
    try:
        current_timetable = session.get('current_timetable', {})
        if current_timetable:
            return jsonify({
                "success": True,
                "timetable": current_timetable,
                "saved_at": session.get('timetable_saved_at', '')
            })
        else:
            return jsonify({
                "success": False,
                "error": "No timetable available in session"
            })
    except Exception as e:
        logging.error(f"Error getting current timetable: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/structure')
@login_required
def api_get_structure():
    """API endpoint to get academic structure"""
    structure = data_manager.get_academic_structure()
    return jsonify(structure)

@app.route('/api/subjects')
@login_required
def api_get_subjects():
    """API endpoint to get subjects"""
    subjects_list = data_manager.get_subjects()
    return jsonify({"subjects": subjects_list})

@app.route('/api/faculty')
@login_required
def api_get_faculty():
    """API endpoint to get faculty"""
    faculty_list = data_manager.get_faculty()
    return jsonify({"faculty": faculty_list})

@app.route('/api/rooms')
@login_required
def api_get_rooms():
    """API endpoint to get rooms"""
    rooms_list = data_manager.get_rooms()
    return jsonify({"rooms": rooms_list})

# AI-Powered Timetable Modification Routes

@app.route('/ai-assistant')
@login_required
def ai_assistant_page():
    """AI Assistant page for timetable modifications"""
    return render_template('ai_assistant.html')

@app.route('/api/ai/process-request', methods=['POST'])
@login_required
def api_ai_process_request():
    """API endpoint for processing natural language timetable requests with feedback support"""
    try:
        data = request.get_json()
        user_request = data.get('request', '')
        user_feedback = data.get('user_feedback', '')
        current_timetable = session.get('current_timetable', {})
        
        if not user_request:
            return jsonify({"error": "Request cannot be empty"}), 400
        
        # Get previous suggestions from session for context
        previous_suggestions = session.get('last_suggestions', [])
        
        # Process the request with feedback support
        result = ai_assistant.process_natural_language_request(
            user_request, 
            current_timetable, 
            user_feedback=user_feedback,
            previous_suggestions=previous_suggestions
        )
        
        # Store suggestions for future feedback
        if result.get('success') and result.get('reschedule_suggestions'):
            session['last_suggestions'] = result.get('reschedule_suggestions', {}).get('rescheduling_options', [])
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error processing AI request: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/analyze-conflicts', methods=['POST'])
@login_required
def api_ai_analyze_conflicts():
    """API endpoint for AI-powered conflict analysis"""
    try:
        data = request.get_json()
        timetable = data.get('timetable', {})
        
        if not timetable:
            return jsonify({"error": "Timetable data required"}), 400
        
        result = ai_assistant.analyze_schedule_conflicts(timetable)
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error analyzing conflicts: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/suggest-reschedule', methods=['POST'])
@login_required
def api_ai_suggest_reschedule():
    """API endpoint for AI-powered rescheduling suggestions"""
    try:
        data = request.get_json()
        affected_sessions = data.get('affected_sessions', [])
        constraints = data.get('constraints', {})
        
        result = ai_assistant.suggest_optimal_reschedule(affected_sessions, constraints)
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error generating reschedule suggestions: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/emergency-schedule', methods=['POST'])
@login_required
def api_ai_emergency_schedule():
    """API endpoint for emergency schedule generation"""
    try:
        data = request.get_json()
        constraints = data.get('constraints', {})
        priority_sessions = data.get('priority_sessions', [])
        
        result = ai_assistant.generate_emergency_schedule(constraints, priority_sessions)
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error generating emergency schedule: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/optimize-workload', methods=['POST'])
@login_required
def api_ai_optimize_workload():
    """API endpoint for faculty workload optimization"""
    try:
        data = request.get_json()
        current_assignments = data.get('assignments', {})
        
        result = ai_assistant.optimize_faculty_workload(current_assignments)
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error optimizing workload: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/saved-timetables')
@login_required
def saved_timetables_page():
    """Saved timetables list page"""
    timetables = data_manager.get_saved_timetables()
    return render_template('saved_timetables.html', timetables=timetables)

@app.route('/saved-timetables/<int:timetable_id>')
@login_required
def saved_timetable_view(timetable_id):
    """View a specific saved timetable with Division/Batch/Faculty toggle"""
    saved = data_manager.get_saved_timetable(timetable_id)
    if not saved:
        flash('Timetable not found.', 'error')
        return redirect(url_for('saved_timetables_page'))
    return render_template('saved_timetables_view.html', saved=saved)

@app.route('/saved-timetables/delete/<int:timetable_id>', methods=['POST'])
@login_required
def delete_saved_timetable_page(timetable_id):
    """Delete a saved timetable and redirect back to list"""
    try:
        data_manager.delete_saved_timetable(timetable_id)
        flash('Timetable deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting timetable: {str(e)}', 'error')
    return redirect(url_for('saved_timetables_page'))

@app.route('/schedule-modifications')
@login_required
def schedule_modifications():
    """Schedule modifications management page"""
    return render_template('schedule_modifications.html')

@app.route('/api/save-timetable', methods=['POST'])
@login_required
def api_save_timetable():
    """Save current timetable to session for AI operations"""
    try:
        data = request.get_json()
        timetable = data.get('timetable', {})
        
        session['current_timetable'] = timetable
        session['timetable_saved_at'] = datetime.now().isoformat()
        
        return jsonify({"success": True, "message": "Timetable saved successfully"})
        
    except Exception as e:
        logging.error(f"Error saving timetable: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/timetable/save-permanent', methods=['POST'])
@login_required
def api_save_timetable_permanent():
    """Save timetable permanently to database"""
    try:
        data = request.get_json()
        timetable = data.get('timetable', {})
        name = data.get('name', None)
        
        if not timetable or not timetable.keys():
            return jsonify({"error": "No timetable data provided"}), 400
        
        saved_entry = data_manager.save_timetable(timetable, name)
        
        return jsonify({
            "success": True,
            "message": "Timetable saved successfully",
            "timetable": saved_entry
        })
        
    except Exception as e:
        logging.error(f"Error saving timetable permanently: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/timetable/saved-list', methods=['GET'])
@login_required
def api_get_saved_timetables():
    """Get list of all saved timetables"""
    try:
        timetables = data_manager.get_saved_timetables()
        return jsonify({
            "success": True,
            "timetables": timetables
        })
    except Exception as e:
        logging.error(f"Error getting saved timetables: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/timetable/load-saved/<int:timetable_id>', methods=['POST'])
@login_required
def api_load_saved_timetable(timetable_id):
    """Load a saved timetable into session"""
    try:
        saved_timetable = data_manager.get_saved_timetable(timetable_id)
        
        if not saved_timetable:
            return jsonify({"error": "Timetable not found"}), 404
        
        # Load into session
        session['current_timetable'] = saved_timetable['timetable']
        session['timetable_saved_at'] = saved_timetable['saved_at']
        
        return jsonify({
            "success": True,
            "message": "Timetable loaded successfully",
            "timetable": saved_timetable['timetable'],
            "saved_at": saved_timetable['saved_at']
        })
        
    except Exception as e:
        logging.error(f"Error loading saved timetable: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/timetable/delete-saved/<int:timetable_id>', methods=['DELETE'])
@login_required
def api_delete_saved_timetable(timetable_id):
    """Delete a saved timetable"""
    try:
        data_manager.delete_saved_timetable(timetable_id)
        return jsonify({
            "success": True,
            "message": "Timetable deleted successfully"
        })
    except Exception as e:
        logging.error(f"Error deleting saved timetable: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/get-suggestions', methods=['POST'])
@login_required
def api_ai_get_suggestions():
    """API endpoint to get 3 AI suggestions for a modification request"""
    try:
        data = request.get_json()
        user_request = data.get('request', '')
        current_timetable = session.get('current_timetable', {})
        user_feedback = data.get('user_feedback', '')
        
        if not user_request:
            return jsonify({"error": "Request cannot be empty"}), 400
        
        # Process the request to get suggestions
        result = ai_assistant.get_modification_suggestions(
            user_request, 
            current_timetable, 
            user_feedback=user_feedback
        )
        
        # Store the request context for applying modifications
        session['last_modification_request'] = {
            'request': user_request,
            'timetable': current_timetable,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error getting suggestions: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/apply-modification', methods=['POST'])
@login_required
def api_apply_modification():
    """Apply AI-suggested timetable modifications"""
    try:
        data = request.get_json()
        modification_type = data.get('modification_type')
        option = data.get('option', {})
        original_data = data.get('original_data', {})
        
        current_timetable = session.get('current_timetable', {})
        if not current_timetable:
            return jsonify({"error": "No current timetable found. Please load a timetable first."}), 400
        
        # Apply the modification using AI assistant
        result = ai_assistant.apply_modification(modification_type, option, original_data, current_timetable)
        
        if result.get('success'):
            # Save the modified timetable back to session
            if result.get('modified_timetable'):
                session['current_timetable'] = result['modified_timetable']
                session['timetable_saved_at'] = datetime.now().isoformat()
                session['modification_history'] = session.get('modification_history', []) + [{
                    'timestamp': datetime.now().isoformat(),
                    'type': modification_type,
                    'description': option.get('description', 'Timetable modification'),
                    'applied_by': 'AI Assistant'
                }]
            
            # Mark as successful suggestion for tracking
            ai_assistant.mark_suggestion_successful()
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error applying modification: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/statistics', methods=['GET'])
@login_required
def get_ai_statistics():
    """Get AI assistant usage statistics and performance metrics"""
    try:
        stats = ai_assistant.get_ai_statistics()
        return jsonify({
            "success": True,
            "statistics": stats
        })
    except Exception as e:
        logging.error(f"Error getting AI statistics: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/health', methods=['GET'])
@login_required
def get_ai_health():
    """Get AI assistant health status and capabilities"""
    try:
        health = ai_assistant.get_ai_health_status()
        return jsonify({
            "success": True,
            "health": health
        })
    except Exception as e:
        logging.error(f"Error getting AI health: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/detect-conflicts', methods=['POST'])
@login_required
def detect_conflicts():
    """Use AI to detect schedule conflicts and suggest improvements"""
    try:
        data = request.get_json()
        timetable = data.get('timetable') or session.get('current_timetable', {})
        
        if not timetable:
            return jsonify({"error": "No timetable data provided"}), 400
        
        result = ai_assistant.detect_schedule_conflicts_ai(timetable)
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error detecting conflicts: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/timetable/export/pdf', methods=['POST'])
@login_required
def export_timetable_pdf():
    """Export ALL divisions/batches in timetable to PDF"""
    try:
        data = request.get_json()
        timetable = data.get('timetable')
        
        if not timetable:
            return jsonify({"error": "No timetable data provided"}), 400
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), 
                              rightMargin=30, leftMargin=30, 
                              topMargin=30, bottomMargin=30)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Main Title
        title = Paragraph("<b>Complete Timetable - All Divisions</b>", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Add timestamp
        timestamp = Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", 
                            styles['Normal'])
        elements.append(timestamp)
        elements.append(Spacer(1, 0.3*inch))
        
        # Sort views - divisions first (without "Batch"), then batches
        all_views = sorted(timetable.keys())
        division_views = [v for v in all_views if 'Batch' not in v]
        batch_views = [v for v in all_views if 'Batch' in v]
        sorted_views = division_views + batch_views
        
        # Create a page for each division/batch
        for idx, view_key in enumerate(sorted_views):
            view_data = timetable[view_key]
            view_name = view_key.replace('_', ' ')
            
            # Add page break between views (except first)
            if idx > 0:
                elements.append(PageBreak())
            
            # View title
            view_title = Paragraph(f"<b>{view_name}</b>", styles['Heading1'])
            elements.append(view_title)
            elements.append(Spacer(1, 0.2*inch))
            
            # Get data - viewData structure is {Day: {TimeSlot: [sessions]}}
            days = list(view_data.keys())
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            days.sort(key=lambda x: day_order.index(x) if x in day_order else 999)
            
            # Get time slots from first day
            time_slots = list(view_data[days[0]].keys()) if days and days[0] in view_data else []
            
            # Create table data
            table_data = []
            
            # Header row
            header = ['Time Slot'] + days
            table_data.append(header)
            
            # Data rows - skip continuation slots for practicals
            for time_slot in time_slots:
                row = [time_slot]
                for day in days:
                    # Get sessions for this day and time slot
                    slot_sessions = view_data.get(day, {}).get(time_slot, [])

                    # Ensure it's a list
                    if not isinstance(slot_sessions, list):
                        slot_sessions = [slot_sessions] if slot_sessions else []

                    if slot_sessions:
                        cell_text = []
                        for session in slot_sessions:
                            if session:  # Check session is not None
                                # Skip continuation slots - they're part of a multi-hour practical
                                if session.get('slot_position') == 'continuation':
                                    cell_text.append('↑ (contd.)')
                                    continue

                                session_type = session.get('type', '')

                                # Handle practical_block type (division view)
                                if session_type == 'practical_block':
                                    span = session.get('span', 1)
                                    duration_label = f" ({span} hrs)" if span > 1 else ""
                                    cell_text.append(f"Practicals{duration_label}")
                                    batches = session.get('batches', {})
                                    for b_num in sorted(batches.keys(), key=lambda x: int(x)):
                                        b_letter = chr(64 + int(b_num))
                                        b_info = batches[b_num]
                                        if b_info:
                                            cell_text.append(f"Batch {b_letter}: {b_info.get('subject', '')} ({b_info.get('room', '')})")
                                        else:
                                            cell_text.append(f"Batch {b_letter}: Free")
                                    cell_text.append('')
                                    continue

                                subject = session.get('subject', '')
                                faculty = session.get('faculty', '')
                                room = session.get('room', '')
                                span = session.get('span', 1)

                                duration_label = f" ({span} hrs)" if span > 1 else ""

                                if session_type:
                                    cell_text.append(f"{subject} ({session_type}){duration_label}")
                                else:
                                    cell_text.append(f"{subject}{duration_label}")

                                if faculty:
                                    cell_text.append(f"Faculty: {faculty}")
                                if room:
                                    cell_text.append(f"Room: {room}")
                                cell_text.append('')  # Empty line between sessions

                        row.append('\n'.join(cell_text).strip())
                    else:
                        row.append('-')

                table_data.append(row)
            
            # Create table
            table = Table(table_data, repeatRows=1)
            
            # Style the table
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#343a40')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.2*inch))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Generate filename
        filename = f"Complete_Timetable_All_Divisions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return send_file(buffer, 
                        mimetype='application/pdf',
                        as_attachment=True,
                        download_name=filename)
        
    except Exception as e:
        logging.error(f"Error exporting PDF: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/timetable/export/excel', methods=['POST'])
@login_required
def export_timetable_excel():
    """Export ALL divisions/batches in timetable to Excel with separate sheets"""
    try:
        data = request.get_json()
        timetable = data.get('timetable')
        
        if not timetable:
            return jsonify({"error": "No timetable data provided"}), 400
        
        # Create workbook
        wb = Workbook()
        # Remove default sheet
        wb.remove(wb.active)
        
        # Define enhanced styles (similar to reference image)
        # Header style - Teal/Green color like reference image
        header_font = Font(bold=True, color="FFFFFF", size=12)
        header_fill = PatternFill(start_color="2C7873", end_color="2C7873", fill_type="solid")
        
        # Time column style
        time_font = Font(bold=True, size=11, color="FFFFFF")
        time_fill = PatternFill(start_color="3D5A59", end_color="3D5A59", fill_type="solid")
        
        # Break style (for merged break cells)
        break_font = Font(bold=True, size=11, color="FFFFFF")
        break_fill = PatternFill(start_color="5A7D7A", end_color="5A7D7A", fill_type="solid")
        
        # Regular cell style
        regular_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        break_alignment = Alignment(horizontal='center', vertical='center')
        
        # Border styles
        border = Border(
            left=Side(style='thin', color='000000'),
            right=Side(style='thin', color='000000'),
            top=Side(style='thin', color='000000'),
            bottom=Side(style='thin', color='000000')
        )
        
        # Sort views - divisions first (without "Batch"), then batches
        all_views = sorted(timetable.keys())
        division_views = [v for v in all_views if 'Batch' not in v]
        batch_views = [v for v in all_views if 'Batch' in v]
        sorted_views = division_views + batch_views
        
        # Create a sheet for each division/batch
        for view_key in sorted_views:
            view_data = timetable[view_key]
            view_name = view_key.replace('_', ' ')
            
            # Create sheet with truncated name (Excel limit is 31 chars)
            sheet_name = view_name[:31]
            ws = wb.create_sheet(title=sheet_name)
            
            # Get data - viewData structure is {Day: {TimeSlot: [sessions]}}
            days = list(view_data.keys())
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            days.sort(key=lambda x: day_order.index(x) if x in day_order else 999)
            
            # Get time slots from first day
            time_slots = list(view_data[days[0]].keys()) if days and days[0] in view_data else []
            
            # Add title
            merge_range = f'A1:{chr(65 + len(days))}1'
            ws.merge_cells(merge_range)
            title_cell = ws['A1']
            title_cell.value = view_name
            title_cell.font = Font(bold=True, size=14, color="2C7873")
            title_cell.alignment = Alignment(horizontal='center', vertical='center')
            ws.row_dimensions[1].height = 25
            
            # Add timestamp
            merge_range_2 = f'A2:{chr(65 + len(days))}2'
            ws.merge_cells(merge_range_2)
            timestamp_cell = ws['A2']
            timestamp_cell.value = f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
            timestamp_cell.font = Font(size=10, italic=True)
            timestamp_cell.alignment = Alignment(horizontal='center', vertical='center')
            ws.row_dimensions[2].height = 20
            
            # Header row (row 4)
            header_row = 4
            ws.cell(row=header_row, column=1).value = 'Time'
            for col_idx, day in enumerate(days, start=2):
                ws.cell(row=header_row, column=col_idx).value = day
            
            # Apply header style
            for col in range(1, len(days) + 2):
                cell = ws.cell(row=header_row, column=col)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border
            ws.row_dimensions[header_row].height = 25
            
            # Helper function to check if a time slot is a break
            def is_break_slot(time_slot, days_data):
                """Check if all days have the same break for this time slot"""
                break_keywords = ['break', 'lunch', 'recess']
                first_day_sessions = days_data.get(days[0], {}).get(time_slot, [])
                
                if not first_day_sessions:
                    return None
                
                # Ensure it's a list
                if not isinstance(first_day_sessions, list):
                    first_day_sessions = [first_day_sessions] if first_day_sessions else []
                
                # Check if first session is a break
                if not first_day_sessions or not first_day_sessions[0]:
                    return None
                    
                first_subject = first_day_sessions[0].get('subject', '').lower()
                
                # Check if it's a break
                is_break = any(keyword in first_subject for keyword in break_keywords)
                if not is_break:
                    return None
                
                # Check if all days have the same break
                break_name = first_day_sessions[0].get('subject', '')
                for day in days:
                    day_sessions = days_data.get(day, {}).get(time_slot, [])
                    if not isinstance(day_sessions, list):
                        day_sessions = [day_sessions] if day_sessions else []
                    
                    if not day_sessions or not day_sessions[0]:
                        return None
                    
                    if day_sessions[0].get('subject', '') != break_name:
                        return None
                
                return break_name
            
            # Data rows
            current_row = header_row + 1
            for time_slot in time_slots:
                # Check if this is a break slot
                break_name = is_break_slot(time_slot, view_data)
                
                if break_name:
                    # This is a break - merge cells across all days
                    # Time slot cell
                    time_cell = ws.cell(row=current_row, column=1)
                    time_cell.value = time_slot
                    time_cell.font = time_font
                    time_cell.fill = time_fill
                    time_cell.alignment = break_alignment
                    time_cell.border = border
                    
                    # Merge cells for break across all days
                    merge_range = f'{chr(65 + 1)}{current_row}:{chr(65 + len(days))}{current_row}'
                    ws.merge_cells(merge_range)
                    
                    # Set break cell value and style
                    break_cell = ws.cell(row=current_row, column=2)
                    break_cell.value = break_name
                    break_cell.font = break_font
                    break_cell.fill = break_fill
                    break_cell.alignment = break_alignment
                    break_cell.border = border
                    
                    # Apply border to all merged cells
                    for col in range(2, len(days) + 2):
                        ws.cell(row=current_row, column=col).border = border
                    
                    ws.row_dimensions[current_row].height = 30
                    
                else:
                    # Regular time slot
                    # Time slot cell
                    time_cell = ws.cell(row=current_row, column=1)
                    time_cell.value = time_slot
                    time_cell.font = time_font
                    time_cell.fill = time_fill
                    time_cell.alignment = Alignment(horizontal='center', vertical='center')
                    time_cell.border = border
                    
                    # Day cells
                    max_lines = 1
                    for col_idx, day in enumerate(days, start=2):
                        cell = ws.cell(row=current_row, column=col_idx)
                        # Get sessions for this day and time slot
                        slot_sessions = view_data.get(day, {}).get(time_slot, [])

                        # Ensure it's a list
                        if not isinstance(slot_sessions, list):
                            slot_sessions = [slot_sessions] if slot_sessions else []

                        if slot_sessions:
                            cell_text = []
                            for session_item in slot_sessions:
                                if session_item:  # Check session is not None
                                    # Show continuation marker for multi-hour practicals
                                    if session_item.get('slot_position') == 'continuation':
                                        cell_text.append('↑ (contd.)')
                                        continue

                                    session_type = session_item.get('type', '')

                                    # Handle practical_block type (division view)
                                    if session_type == 'practical_block':
                                        span = session_item.get('span', 1)
                                        duration_label = f" ({span} hrs)" if span > 1 else ""
                                        cell_text.append(f"Practicals{duration_label}")
                                        batches = session_item.get('batches', {})
                                        for b_num in sorted(batches.keys(), key=lambda x: int(x)):
                                            b_letter = chr(64 + int(b_num))
                                            b_info = batches[b_num]
                                            if b_info:
                                                cell_text.append(f"Batch {b_letter}: {b_info.get('subject', '')} ({b_info.get('room', '')})")
                                            else:
                                                cell_text.append(f"Batch {b_letter}: Free")
                                        cell_text.append('')
                                        continue

                                    subject = session_item.get('subject', '')
                                    faculty = session_item.get('faculty', '')
                                    room = session_item.get('room', '')
                                    span = session_item.get('span', 1)

                                    duration_label = f" ({span} hrs)" if span > 1 else ""

                                    if session_type:
                                        cell_text.append(f"{subject} ({session_type}){duration_label}")
                                    else:
                                        cell_text.append(f"{subject}{duration_label}")

                                    if faculty:
                                        cell_text.append(f"Faculty: {faculty}")
                                    if room:
                                        cell_text.append(f"Room: {room}")
                                    cell_text.append('')  # Empty line between sessions

                            cell_value = '\n'.join(cell_text).strip()
                            cell.value = cell_value
                            max_lines = max(max_lines, len(cell_value.split('\n')))
                        else:
                            cell.value = '-'

                        cell.alignment = regular_alignment
                        cell.border = border

                    # Set row height based on content
                    ws.row_dimensions[current_row].height = max(40, max_lines * 15)
                
                current_row += 1
            
            # Set column widths
            ws.column_dimensions['A'].width = 18
            for col_idx in range(2, len(days) + 2):
                col_letter = chr(64 + col_idx)  # Convert column index to letter
                ws.column_dimensions[col_letter].width = 28
        
        # Save to buffer
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        # Generate filename
        filename = f"Complete_Timetable_All_Divisions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(buffer,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        as_attachment=True,
                        download_name=filename)
        
    except Exception as e:
        logging.error(f"Error exporting Excel: {str(e)}")
        return jsonify({"error": str(e)}), 500
