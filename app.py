from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import uuid
import threading
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename

# --- Services & Utils ---
from utils.auth import AuthManager
from utils.reminder import ReminderManager
from utils.pharmacy_locator import PharmacyLocator
from utils.otc_manager import OTCManager
from utils.utils import setup_logger, ensure_directory
from utils.extractor import PrescriptionExtractor
from utils.vector_store import VectorStoreManager
from utils.memory import MemoryManager
from services.scheduler import SchedulerService
from services.mail_service import MailService
from services.validator import Validator

try:
    from utils.graph import RAGGraph
except ImportError:
    RAGGraph = None

# --- App Config ---
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "pharmaBuddy_secret_key_2026")
logger = setup_logger(__name__)

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'data', 'input')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg'}
ensure_directory(UPLOAD_FOLDER)

# --- Initialize Core Services ---
auth_manager = AuthManager()
reminder_manager = ReminderManager()
pharmacy_locator = PharmacyLocator()
otc_manager = OTCManager()
extractor = PrescriptionExtractor()
vector_store = VectorStoreManager()
memory_manager = MemoryManager()
mail_service = MailService()
scheduler_service = SchedulerService() # Starts background scheduler

rag_graph = None
try:
    if RAGGraph:
        rag_graph = RAGGraph().build_graph()
except Exception as e:
    logger.error(f"RAG Init Error: {e}")

# --- Helper Logic ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Error Handling ---
@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error="Internal Server Error"), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error="Page Not Found"), 404

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled Exception: {e}", exc_info=True)
    return render_template('error.html', error=str(e)), 500

# --- Routes ---
@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username')
        password = request.form.get('password')
        
        valid_err = Validator.validate_login(username, password)
        if valid_err:
            flash(valid_err, "danger")
            return render_template('index.html')

        if action == 'register':
            email = request.form.get('email', '')
            success, msg = auth_manager.register_user(username, password, email)
            if success:
                flash("Account created! Please login.", "success")
            else:
                flash(msg, "danger")
        else:
            success, msg = auth_manager.login_user(username, password)
            if success:
                session['user'] = username
                profile = auth_manager.get_user_profile(username)
                session['display_name'] = profile.get('display_name') or username
                session['theme'] = profile.get('theme', 'dark')
                session['language'] = profile.get('language', 'en')
                session['avatar'] = profile.get('avatar', '')
                session['email'] = profile.get('email', '')
                return redirect(url_for('dashboard'))
            else:
                flash(msg, "danger")
                
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user = session['user']
    
    if request.method == 'POST':
        if 'prescription' in request.files:
            file = request.files['prescription']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                
                # Check duplication
                existing_id = memory_manager.get_prescription_by_filename(user, filename)
                if existing_id:
                    flash("Prescription already exists.", "info")
                    return redirect(url_for('dashboard', view=existing_id))
                
                file_id = str(uuid.uuid4())
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
                
                try:
                    data = extractor.extract_data(file_path)
                    if data:
                        med_details = []
                        for m in data.get('medicines', []):
                            timing = m.get('timing', {})
                            
                            # Handle Instruction
                            instr = timing.get('food_timing') or timing.get('instruction', '')
                            instr_str = f" I:{instr.replace(' ', '_')}" if instr else ""
                            
                            # Default to 0 if missing
                            m_time = timing.get('morning', '0')
                            a_time = timing.get('afternoon', '0')
                            n_time = timing.get('night', '0')
                            
                            timing_str = f"M:{m_time} A:{a_time} N:{n_time}{instr_str}"
                            
                            # Handle dosage/quantity fallback
                            dose = m.get('dosage') or m.get('quantity') or ''
                            if dose == 'None': dose = ''
                            
                            # Handle Caution
                            caution = m.get('caution', '')
                            caution_str = f" C:{caution.replace(' ', '_')}" if caution else ""
                            
                            med_details.append(f"- {m.get('name')} {dose}: {timing_str}{caution_str}")
                        
                        meds_str = "\n".join(med_details)
                        consult_needed = data.get('requires_doctor_consultation', False)
                        consult_reason = data.get('consultation_reason', '')
                        consult_str = f"\n⚠️ Doctor Consultation: {consult_reason}" if consult_needed else ""
                        
                        full_text = f"Date: {data.get('date')}\n{meds_str}\nNotes: {data.get('notes')}{consult_str}"
                        
                        vector_store.add_prescription(file_id, [full_text], {"filename": filename})
                        
                        title = f"Rx: {filename}"
                        if data.get('medicines'):
                            title = f"Rx: {data['medicines'][0].get('name')}..."
                            
                        memory_manager.get_or_create_session(user, file_id, title=title, filename=filename, details=meds_str + consult_str)
                        flash("Prescription analyzed successfully!", "success")
                        return redirect(url_for('dashboard', view=file_id))
                    else:
                        flash("Could not extract data from file.", "warning")
                except Exception as e:
                    logger.error(f"Processing Error: {e}")
                    flash(f"Error processing prescription: {e}", "danger")

    prescriptions = memory_manager.get_user_prescriptions(user)
    
    active_id = request.args.get('view')
    active_p = None
    chat_history = []
    
    if active_id:
        active_p = next((p for p in prescriptions if p['id'] == active_id), None)
        if active_p:
            sess_id, details_text = memory_manager.get_or_create_session(user, active_id)
            active_p['details'] = details_text
            
            # Parse details for card view
            med_list = []
            if details_text:
                lines = details_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('- '):
                        try:
                            # Format: "- Name Dosage: M:1 A:0 N:1 I:Before_Meal"
                            content = line[2:] # Strip "- "
                            if ':' in content:
                                parts = content.split(':', 1)
                                name_dose = parts[0].strip()
                                timing_str = parts[1].strip()
                                
                                # Parse timing
                                timing = {'M': 0, 'A': 0, 'N': 0, 'I': '', 'C': ''}
                                for t_part in timing_str.split():
                                    if ':' in t_part:
                                        k, v = t_part.split(':', 1)
                                        if k in timing:
                                            timing[k] = v
                                
                                med_list.append({
                                    'name_dosage': name_dose,
                                    'timing': timing,
                                    'frequency': f"{timing['M']}-{timing['A']}-{timing['N']}"
                                })
                            else:
                                # Fallback if no colon
                                med_list.append({'name_dosage': content, 'timing': None})
                        except Exception as e:
                            logger.error(f"Error parsing med line: {line} - {e}")
            
            active_p['med_list'] = med_list
            chat_history = memory_manager.get_history(sess_id)

    return render_template('dashboard.html', 
                           user=user, 
                           prescriptions=prescriptions, 
                           active_p=active_p, 
                           chat_history=chat_history)

@app.route('/api/prescription/delete', methods=['POST'])
@login_required
def delete_prescription():
    data = request.json
    p_id = data.get('id')
    
    if not p_id:
        return jsonify({'error': 'ID required'}), 400
        
    try:
        # Delete from DB
        success = memory_manager.delete_session(session['user'], p_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Prescription not found'}), 404
            
    except Exception as e:
        logger.error(f"Delete Prescription Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    data = request.json
    msg = data.get('message')
    pid = data.get('prescription_id')
    
    if not msg or not pid:
        return jsonify({'error': 'Invalid request'}), 400
        
    try:
        sess_id, _ = memory_manager.get_or_create_session(session['user'], pid)
        
        if not rag_graph:
            return jsonify({'answer': 'AI Service Unavailable. Check API keys.'})
            
        result = rag_graph.invoke({
            "question": msg,
            "prescription_id": pid,
            "session_id": sess_id,
            "context": [],
            "answer": ""
        })
        return jsonify({'answer': result.get("answer", "No response generated")})
    except Exception as e:
        logger.error(f"Chat API Error: {e}")
        return jsonify({'answer': f"Error: {str(e)}"}), 500

@app.route('/medications', methods=['GET', 'POST'])
@login_required
def medications():
    if request.method == 'POST':
        # Safely extract form data
        form_data = {
            'name': request.form.get('name'),
            'dosage': request.form.get('dosage'),
            'frequency': request.form.get('frequency'),
            'times': request.form.getlist('times'),
            'duration': int(request.form.get('duration', 7)),
            'start_date': request.form.get('start_date'),
            'email_notification': 'email_notification' in request.form,
            'notification_email': request.form.get('notification_email', ''),
            'calendar_sync': 'calendar' in request.form,
            'instructions': request.form.get('instructions')
        }
        
        # Validation
        validation_errors = Validator.validate_medication_input(form_data)
        if validation_errors:
            for err in validation_errors:
                flash(err, "danger")
        else:
            try:
                res = reminder_manager.add_reminder(
                    session['user'],
                    form_data['name'],
                    form_data['dosage'],
                    form_data['frequency'],
                    form_data['times'],
                    form_data['duration'],
                    form_data['start_date'],

                    email_notification=form_data['email_notification'],
                    notification_email=form_data['notification_email'],
                    instructions=form_data['instructions']
                )
                
                if res['success']:
                    flash("Medication schedule added successfully!", "success")
                    # Save email to profile if user provided one and none is saved yet
                    provided_email = form_data['notification_email']
                    if provided_email and not session.get('email'):
                        auth_manager.update_user_profile(session['user'], {'email': provided_email})
                        session['email'] = provided_email
                    
                    if form_data['calendar_sync']:
                        from utils.calendar_integration import CalendarIntegration
                        cal = CalendarIntegration()
                        if cal.available:
                            # Use first time for simple event logic usually, but here we can iterate
                            # For simplicity in calendar integration call (assuming it handles list or we iterate)
                            # Looking at old code, it handles creating events for duration.
                            # We pass the list of times.
                            cal_res = cal.create_multiple_reminder_events(
                                form_data['name'],
                                form_data['dosage'],
                                form_data['times'],
                                form_data['start_date'],
                                form_data['duration']
                            )
                            if cal_res['success']:
                                flash(f"Synced {cal_res['created']} events to Google Calendar.", "info")
                        else:
                            flash("Google Calendar not configured.", "warning")
                else:
                    flash(f"Error adding reminder: {res.get('error')}", "danger")
            except Exception as e:
                flash(f"System Error: {e}", "danger")
                logger.error(f"Medication Add Error: {e}")
            
    reminders = reminder_manager.get_user_reminders(session['user'])
    todays_doses = reminder_manager.get_todays_reminders(session['user'])
    stats = reminder_manager.get_adherence_stats(session['user'])
    
    return render_template('medications.html',
                           user=session['user'],
                           user_email=session.get('email', ''),
                           reminders=reminders,
                           todays_doses=todays_doses,
                           stats=stats,
                           now=datetime.now().strftime("%Y-%m-%d"))

@app.route('/api/notifications')
@login_required
def api_notifications():
    try:
        user_id = session['user']
        todays = reminder_manager.get_todays_reminders(user_id)
        current_time = datetime.now().strftime('%H:%M')
        notifications = []
        unread = 0
        for dose in todays:
            med  = dose['medicine_name']
            t    = dose['time']
            if dose['taken']:
                notifications.append({'type': 'taken',   'icon': '✅', 'title': f'{med} taken',     'body': f'Dose at {t} — logged',              'time': t})
            elif t < current_time:
                notifications.append({'type': 'missed',  'icon': '⚠️', 'title': f'Missed: {med}',  'body': f'Scheduled at {t} — not logged',     'time': t})
                unread += 1
            else:
                food = ' — take with food' if dose.get('with_food') else ''
                notifications.append({'type': 'upcoming','icon': '💊', 'title': f'Upcoming: {med}', 'body': f'Due at {t}{food}',                  'time': t})
        return jsonify({'notifications': notifications, 'count': unread})
    except Exception as e:
        return jsonify({'notifications': [], 'count': 0})

@app.route('/api/medication/status', methods=['POST'])
@login_required
def update_medication_status():
    data = request.json
    action = data.get('action') # 'taken' or 'skipped'
    med_name = data.get('medicine_name')
    time = data.get('scheduled_time')
    
    if not all([action, med_name, time]):
        return jsonify({'error': 'Missing required fields'}), 400
        
    try:
        if action == 'taken':
            res = reminder_manager.mark_as_taken(session['user'], med_name, time)
        elif action == 'skipped':
            res = reminder_manager.mark_as_skipped(session['user'], med_name, time, reason=data.get('reason'))
        else:
            return jsonify({'error': 'Invalid action'}), 400
            
        return jsonify(res)
    except Exception as e:
        logger.error(f"Status Update Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/report/email', methods=['POST'])
@login_required
def email_report():
    data = request.json
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email required'}), 400

    user = session['user']

    def _send():
        try:
            stats = reminder_manager.get_adherence_stats(user)
            mail_service.send_performance_report(email, stats)
        except Exception as e:
            logger.error(f"Email Report Error for {user}: {e}")

    threading.Thread(target=_send, daemon=True).start()
    return jsonify({'success': True, 'message': 'Report is being prepared and will be sent shortly.'})

@app.route('/pharmacy')
@login_required
def pharmacy():
    return render_template('pharmacy.html', user=session['user'])

@app.route('/api/pharmacy/search', methods=['POST'])
@login_required
def pharmacy_search():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        location_query = data.get('location')
        lat = data.get('lat')
        lng = data.get('lng')
        radius = data.get('radius', 5000)

        # Validate radius
        try:
            radius = int(radius)
            if radius < 1000 or radius > 50000:
                radius = 5000
        except (ValueError, TypeError):
            radius = 5000

        search_lat = lat
        search_lng = lng

        # Handle text location search if provided
        if location_query:
            coords = pharmacy_locator.geocode_address(location_query)
            if coords:
                search_lat, search_lng = coords
            else:
                return jsonify({'error': f'Location "{location_query}" not found. Try a different city or area.'}), 404

        # Validate coordinates
        if not search_lat or not search_lng:
            return jsonify({'error': 'Missing location data. Please enter a location or enable GPS.'}), 400

        # Convert and validate coordinates
        try:
            search_lat = float(search_lat)
            search_lng = float(search_lng)
            if search_lat < -90 or search_lat > 90 or search_lng < -180 or search_lng > 180:
                return jsonify({'error': 'Invalid coordinates'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid coordinates format'}), 400

        try:
            results = pharmacy_locator.find_nearby_pharmacies(search_lat, search_lng, radius)

            # Validate results
            if not isinstance(results, list):
                results = []

            # Return results AND the center coordinates used for the map
            return jsonify({
                'results': results,
                'center': {'lat': search_lat, 'lng': search_lng}
            })
        except Exception as e:
            logger.error(f"Pharmacy search error: {e}", exc_info=True)
            return jsonify({'error': 'Unable to search pharmacies. Please try again.'}), 500

    except Exception as e:
        logger.error(f"Pharmacy API error: {e}", exc_info=True)
        return jsonify({'error': 'Server error. Please try again.'}), 500

@app.route('/safety')
@login_required
def safety():
    query = request.args.get('q')
    results = []
    if query:
        results = otc_manager.search_otc_db(query)
    else:
        results = otc_manager.get_otc_list()
    return render_template('safety.html', user=session['user'], results=results, query=query)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = session['user']
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'change_password':
            current_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')
            if not all([current_pw, new_pw, confirm_pw]):
                flash("All password fields are required.", "danger")
            elif new_pw != confirm_pw:
                flash("New passwords do not match.", "danger")
            elif len(new_pw) < 8:
                flash("New password must be at least 8 characters.", "danger")
            else:
                ok, msg = auth_manager.change_password(user, current_pw, new_pw)
                flash(msg, "success" if ok else "danger")
            return redirect(url_for('profile'))

        # Default: save profile settings
        updates = {}
        display_name = request.form.get('display_name', '').strip()
        language = request.form.get('language', 'en')
        theme = request.form.get('theme', 'dark')
        updates['display_name'] = display_name
        if language in ('en', 'hi', 'ta', 'es', 'fr', 'de'):
            updates['language'] = language
        if theme in ('dark', 'light'):
            updates['theme'] = theme
        auth_manager.update_user_profile(user, updates)
        session['display_name'] = display_name or user
        session['theme'] = updates.get('theme', session.get('theme', 'dark'))
        session['language'] = updates.get('language', session.get('language', 'en'))
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    profile_data = auth_manager.get_user_profile(user)
    prescriptions = memory_manager.get_user_prescriptions(user)
    reminders = reminder_manager.get_user_reminders(user, active_only=False)
    return render_template('profile.html',
                           user=user,
                           profile=profile_data,
                           prescriptions=prescriptions,
                           reminders=reminders)

@app.route('/api/profile/avatar', methods=['POST'])
@login_required
def update_avatar():
    data = request.json
    avatar = data.get('avatar', '')
    if len(avatar) > 200000:
        return jsonify({'error': 'Image too large. Please use an image under 150KB.'}), 400
    auth_manager.update_user_profile(session['user'], {'avatar': avatar})
    session['avatar'] = avatar
    return jsonify({'success': True})

@app.route('/api/profile/theme', methods=['POST'])
@login_required
def update_theme():
    data = request.json
    theme = data.get('theme', 'dark')
    if theme not in ('dark', 'light'):
        return jsonify({'error': 'Invalid theme'}), 400
    auth_manager.update_user_profile(session['user'], {'theme': theme})
    session['theme'] = theme
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False) # Loader false for scheduler
