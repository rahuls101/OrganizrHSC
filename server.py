from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from markupsafe import escape
from dotenv import load_dotenv
from models import db, User, Assessment, StudySession
import fitz
from auth import validate_user_signup, validate_user_login, create_user, allowed_file
import os 
from datetime import datetime, timedelta, time
from pdf_utils import process_file
from werkzeug.utils import secure_filename
from schedule_generator import generate_schedule_for_new_assessments
from collections import defaultdict
from schedule_stats import calculate_weekly_stats
from subject_config import subject_data, name_to_code
from ics import Calendar, Event
import pytz
from flask_wtf import CSRFProtect
from functools import wraps

# Load environment variables from .env file
load_dotenv() 

app = Flask(__name__)
csrf = CSRFProtect(app)
app.secret_key = os.getenv("SECRET_KEY", "defaultsecretky")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

# Set up upload folder for PDF files
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER): 
    os.makedirs(UPLOAD_FOLDER)

# Initialize database with Flask app
db.init_app(app)

# Create database if it doesn't exist (for deployment environments)
with app.app_context(): 
    if not os.path.exists('database.db'):
        print("Database not found, creating one instead") # For platforms that spin down storage
        db.create_all() # Creates an empty database

# Decorator to require login for certain routes
def login_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', message='Please log in to continue', type='error'))
        return route_function(*args, **kwargs)
    return wrapper

# Inject subject colours and names into all templates
@app.context_processor
def inject_globals(): 
    subject_colours = {code: info["colour"] for code,info in subject_data.items()}
    subject_names = {code: info["name"] for code, info in subject_data.items()}
    return dict(
        subject_colours = subject_colours, 
        subject_names = subject_names
    )

# Landing page route
@app.route('/')
def landing():
    return render_template('landing.html')

# Login route (GET and POST)
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = escape(request.form.get('email'))
        password = request.form.get('password')

        user = validate_user_login(email, password)

        if user: 
            session['user_id'] = user.id 
            return redirect(url_for('dashboard', message='Logged in succesfully!', type='success'))
        else: 
            return redirect(url_for('login', message='Invalid email or password', type='error'))
    else: 
        return render_template('login.html')

# Signup route (GET and POST)
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST': 
        # Escape user input to prevent XSS attacks 
        firstname = escape(request.form.get('first-name'))
        lastname = escape(request.form.get('last-name'))
        email = escape(request.form.get('email')).lower()
        password = request.form.get('password') # Passwords are not rendered into HTML
        confirmpassword = request.form.get('confirm-password')
        terms = request.form.get('terms')

        valid = validate_user_signup(firstname, lastname, email, password, confirmpassword, terms)
        if valid:
            create_user(firstname, lastname, email, password)
            return redirect(url_for('login', message='Account created successfully, please log in', type='success'))
        else: 
            return redirect(url_for('signup', message='Signup failed. Please try again.', type='error'))
    else:   
        return render_template('signup.html')
    
# Logout route
@app.route('/logout')
def logout(): 
    session.clear()
    return redirect(url_for('landing', message='Logged out successfully', type='success'))

# Dashboard route (shows upcoming assessments and sessions)
@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])

    # Get current time
    now = datetime.now()

    # Retrieve upcoming assessments
    assessments = [a for a in user.assessments if a.due_date >= now] 

    # Sort assessments by due date
    sorted_assessments = sorted(assessments, key=lambda a: a.due_date)

    # Assessments due within the next week
    upcoming_this_week = [a for a in sorted_assessments if 0 <= (a.due_date - now).days <= 7]

    # Get today's date
    today = now.date() 

    # Query and filter user's upcoming study sessions (limit 5)
    upcoming_sessions = StudySession.query.filter(
        StudySession.user_id == user.id, 
        StudySession.date >= today 
    ).order_by(StudySession.date, StudySession.time).limit(5).all()

    # Add subject name and colour to each session for display
    for studysession in upcoming_sessions: 
        code = studysession.assessment.subject_code
        subject_info = subject_data.get(code)
        studysession.subject_name = subject_info["name"] if subject_info else code 
        studysession.subject_colour = subject_info["colour"] if subject_info else "gray"

    return render_template(
        'dashboard.html',
        user=user, 
        now=now,
        sorted_assessments=sorted_assessments,
        num_close_assessments=len(upcoming_this_week), 
        upcoming_sessions=upcoming_sessions
    )

# Upload route (GET and POST for PDF assessment notifications)
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        files = request.files.getlist('file') 
        if not files:
            return jsonify({})

        parsed_assessments = session.get('parsed_assessments', {})
        results = {}

        for file in files:
            filename = file.filename
            if not file or not allowed_file(filename):
                results[filename] = False
                continue

            result = process_file(file, app.config['UPLOAD_FOLDER'])
            if not result:
                results[filename] = False
                continue

            parsed_assessments[result['filename']] = result
            results[filename] = True

        session['parsed_assessments'] = parsed_assessments
        session.modified = True

        return jsonify(results)  

    return render_template('upload.html', user=user)

# Commit parsed assessments to database
@app.route('/commit-assessments', methods=['POST'])
@login_required
def commit_assessments():
    user_id = session['user_id']
    data = request.get_json()
    filenames = data.get('filenames', [])

    if not filenames:
        return jsonify(False), 400

    parsed = session.get('parsed_assessments', {})

    committed = 0
    for fname in filenames:
        secure_name = secure_filename(fname)
        info = parsed.get(secure_name)
        if not info:
            continue  

        # Check for duplicate assessment
        exists = Assessment.query.filter_by(
            user_id=user_id,
            title=info['title'],
            due_date=datetime.fromisoformat(info['due_date'])
        ).first()

        if exists:
            continue

        try:
            new_assessment = Assessment(
                user_id=user_id,
                subject_code=info['subject_code'],
                title=info['title'],
                description=info['description'],
                due_date=datetime.fromisoformat(info['due_date']),
                weighting=info.get('weighting')
            )
            db.session.add(new_assessment)
            committed += 1
        except Exception as e:
            print('Error committing assessment:', e)

    db.session.commit()

    # Generate study sessions for new assessments
    generate_schedule_for_new_assessments(user_id)

    return jsonify({'success': True, 'message': f'{committed} assessments commited'})

# Clear parsed assessments from session
@app.route('/clear-parsed', methods=['POST'])
@login_required
def clear_parsed(): 
    if 'parsed_assessments' in session: 
        session.pop('parsed_assessments')
        session.modified = True 
    return jsonify(True)

# Weekly study schedule route
@app.route('/schedule')
@login_required
def schedule():
    user = User.query.get(session['user_id'])

    # Get week offset from query string
    week_offset = int(request.args.get('week', 0))

    # Find Monday of the current week, then shift by week_offset
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=7)

    # Filter sessions that fall between Monday and Sunday inclusive
    study_sessions = StudySession.query.filter(
        StudySession.user_id == user.id,
        StudySession.date >= start_of_week,
        StudySession.date < end_of_week
    ).order_by(StudySession.date, StudySession.time).all()

    # Convert list to hashmap for fast lookups in frontend
    session_map = defaultdict(list)
    for studys in study_sessions: 
        session_map[(studys.date, studys.time)].append(studys)

    # Get weekly summary statistics
    weekly_summary = calculate_weekly_stats(study_sessions)

    return render_template(
        'schedule.html', 
        user=user, 
        study_sessions=study_sessions, 
        session_map=session_map,
        week_start=start_of_week, 
        week_offset=week_offset, 
        weekly_summary=weekly_summary,
        timedelta=timedelta
    )

# AJAX endpoint for checking if email is already registered
@app.route('/check_email', methods=['POST'])
def check_email():
    email = request.json.get('email')
    exists = User.query.filter_by(email=email).first() is not None
    return jsonify({'exists': exists})

# Export study sessions as an ICS calendar file
@app.route('/export-calendar')
@login_required
def export_calendar(): 
    user = User.query.get(session['user_id'])

    # Get all sessions for the user
    sessions = StudySession.query.filter(
        StudySession.user_id == user.id
    ).order_by(StudySession.date, StudySession.time).all()

    if not sessions: 
        return redirect(url_for('schedule', message="You have no study sessions to export.", type="error"))
    
    cal = Calendar()

    for session_obj in sessions:
        assessment = session_obj.assessment
        subject_code = assessment.subject_code
        subject_info = subject_data.get(subject_code, {})
        subject_name = subject_info.get('name', subject_code)
        
        from_zone = pytz.timezone("Australia/Sydney")

        # Localise the session time and KEEP it in AEST
        start_dt = from_zone.localize(datetime.combine(session_obj.date, time(hour=session_obj.time)))
        end_dt = start_dt + timedelta(hours=2)

        event = Event()
        event.name = f"Study Session: {subject_name}"
        event.begin = start_dt
        event.end = end_dt
        event.description = assessment.title

        cal.events.add(event)

    response = make_response(str(cal))
    response.headers['Content-Disposition'] = 'attachment; filename=OrganizrHSC_studyschedule.ics'
    response.headers['Content-Type'] = 'text/calendar'
    return response

# Assessments page route (view, edit, add, delete)
@app.route('/assessments')
@login_required
def assessments(): 
    user = User.query.get(session['user_id'])
    now = datetime.now()

    formatted_assessments = []

    # Stats counters
    total = 0 
    due_this_week = 0 
    due_next_week = 0 
    due_later = 0 

    # Sort assessments by due date
    sorted_assessments = sorted(user.assessments, key=lambda assessment: assessment.due_date)

    # Build list of future assessments
    for assessment in sorted_assessments:
        if assessment.due_date >= now:
            total += 1

            days_until_due = (assessment.due_date - now).days

            if days_until_due <= 7:
                due_this_week += 1
            elif days_until_due <= 14:
                due_next_week += 1
            else:
                due_later += 1

            subject_code = assessment.subject_code
            subject_info = subject_data.get(subject_code, {})

            subject_name = subject_info.get("name", subject_code)
            subject_colour = subject_info.get("colour", "gray")

            days_until_due = (assessment.due_date - now).days
            if days_until_due < 0:
                days_until_due = 0

            due_date_str = assessment.due_date.strftime("%B %d, %Y at %I:%M %p")
            due_date_input = assessment.due_date.strftime("%Y-%m-%dT%H:%M")

            assessment_entry = {
                "id": assessment.id,
                "subject_code": subject_code,
                "title": assessment.title,
                "subject": subject_name,
                "subject_colour": subject_colour,
                "description": assessment.description,
                "days_until_due": days_until_due,
                "due_date_str": due_date_str,
                "due_date_input": due_date_input,
                "weighting": assessment.weighting
            }

            formatted_assessments.append(assessment_entry)

    assessments_summary = [total, due_this_week, due_next_week, due_later]

    return render_template('assessments.html', assessments=formatted_assessments, subject_data=subject_data, assessments_summary=assessments_summary)

# Edit assessment route
@app.route('/edit-assessment', methods=['POST'])
@login_required
def edit_assessment(): 
    # Get data from form 
    assessment_id = request.form.get('assessment_id')
    title = request.form.get('title')
    subject_code = request.form.get('subject_code')
    description = request.form.get('description')
    due_date_str = request.form.get('due_date')
    weighting = request.form.get('weighting', type=int)

    # Parse due date 
    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%dT%H:%M")
    except ValueError:
        return redirect(url_for('assessments', message='Please enter a correct date', type='error'))
    
    # Find assessment 
    assessment = Assessment.query.get(assessment_id)

    if assessment and assessment.user_id == session['user_id']:
        due_date_changed = (assessment.due_date != due_date)
        weighting_changed = (assessment.weighting != weighting)

        assessment.title = title
        assessment.subject_code = subject_code
        assessment.description = description
        assessment.due_date = due_date
        assessment.weighting = weighting

        db.session.commit()

        # If due date or weighting changed, regenerate study sessions
        if due_date_changed or weighting_changed: 
            StudySession.query.filter_by(assessment_id=assessment.id).delete() 
            db.session.commit()
            generate_schedule_for_new_assessments(assessment.user_id)
            return redirect(url_for('assessments', message='Due date or weighting changed - sessions regenerated.', type='success'))

        return redirect(url_for('assessments', message='Assessment updated successfully', type='success'))
    else:
        return redirect(url_for('assessments', message='Assessment not found', type='error'))

# Delete assessment route
@app.route('/delete-assessment', methods=['POST'])
@login_required
def delete_assessment():
    assessment_id = request.form.get('assessment_id')
    assessment = Assessment.query.get(assessment_id)

    if assessment and assessment.user_id == session['user_id']:
        # Delete related study sessions first
        StudySession.query.filter_by(assessment_id=assessment.id).delete()
        # Then delete the assessment
        db.session.delete(assessment)
        db.session.commit()
        return redirect(url_for('assessments', message='Assessment and study sessions deleted.', type='success'))
    
    return redirect(url_for('assessments', message='Assessment not found or unauthorized.', type='error'))

# Add assessment route
@app.route('/add-assessment', methods=['POST'])
@login_required
def add_assessment():
    title = request.form.get('title')
    subject_code = request.form.get('subject_code')
    description = request.form.get('description')
    due_date_str = request.form.get('due_date')
    weighting = request.form.get('weighting', type=int)

    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%dT%H:%M")
    except ValueError:
        return redirect(url_for('assessments', message='Invalid due date format', type='error'))

    new_assessment = Assessment(
        user_id=session['user_id'],
        title=title,
        subject_code=subject_code,
        description=description,
        due_date=due_date,
        weighting=weighting
    )

    db.session.add(new_assessment)
    db.session.commit()

    # Generate study sessions for new assessment
    generate_schedule_for_new_assessments(session['user_id'])

    return redirect(url_for('assessments', message='Assessment added successfully', type='success'))

# Route to initialize the database (admin only)
@app.route('/init-db')
def init_db():
    provided_key = request.args.get('key')
    expected_key = os.getenv("ADMIN_SECRET", "devmode")

    if provided_key != expected_key:
        return "Unauthorized", 403

    db.create_all()
    return 'Database initialized!'

# Main entry point for running the Flask app
if __name__ == '__main__': 
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)