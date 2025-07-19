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



load_dotenv() 

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "defaultsecretky")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'


UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER): 
    os.makedirs(UPLOAD_FOLDER)


db.init_app(app)


@app.context_processor
def inject_globals(): 
    subject_colours = {code: info["colour"] for code,info in subject_data.items()}
    subject_names = {code: info["name"] for code, info in subject_data.items()}

    return dict(
        subject_colours = subject_colours, 
        subject_names = subject_names
    )


@app.route('/')
def landing():
    return render_template('landing.html')

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

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST': 
        # Escape user input to prevent XSS attacks 

        firstname = escape(request.form.get('first-name'))
        lastname = escape(request.form.get('last-name'))
        email = escape(request.form.get('email')).lower()
        password = request.form.get('password') #passwords are not rendered into HTML, therefore not an XSS vector
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
    
@app.route('/logout')
def logout(): 
    session.clear()
    return redirect(url_for('landing', message='Logged out successfully', type='success'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: 
        return redirect(url_for('login', message='Please log in to continue', type='error'))

    user = User.query.get(session['user_id'])

    '''
    to show upcoming assessments on the dashboard
    '''

    now = datetime.now()

    #retrieve upcoming assessments 

    assessments = [a for a in user.assessments if a.due_date >= now] 

    #sort assessments by due date

    sorted_assessments = sorted(assessments, key=lambda a: a.due_date)

    #list of assessments that are due within the next week (within 7 days): 

    upcoming_this_week = [a for a in sorted_assessments if 0 <= (a.due_date - now).days <= 7]


    '''
    to show upcoming session on the dashboard
    '''

    #get todays date
    today = now.date() 

    #query and filter users upcoming sessions 

    upcoming_sessions = StudySession.query.filter(
        StudySession.user_id == user.id, 
        StudySession.date >= today 
    ).order_by(StudySession.date, StudySession.time).limit(5).all()

    for studysession in upcoming_sessions: 
        code = studysession.assessment.subject_code
        subject_info = subject_data.get(code)
        studysession.subject_name = subject_info["name"] if subject_info else code 
        studysession.subject_colour = subject_info["colour"] if subject_info else "gray"



    return render_template(
        'dashboard.html',
        user=user, 
        now = now,
        sorted_assessments = sorted_assessments,
        num_close_assessments=len(upcoming_this_week), 
        upcoming_sessions = upcoming_sessions
    )


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('login', message='Please log in to continue', type='error'))

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

@app.route('/commit-assessments', methods=['POST'])
def commit_assessments():
    if 'user_id' not in session:
        return jsonify(False), 401
    
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
                due_date=datetime.fromisoformat(info['due_date'])
            )
            db.session.add(new_assessment)
            committed += 1
        except Exception as e:
            print('Error committing assessment:', e)

    db.session.commit()

    # generate study sessions for any newly committed assessments 
    generate_schedule_for_new_assessments(user_id)

    return jsonify({'success': True, 'message': f'{committed} assessments commited'})



@app.route('/clear-parsed', methods=['POST'])
def clear_parsed(): 
    if 'parsed_assessments' in session: 
        session.pop('parsed_assessments')
        session.modified = True 

    return jsonify(True)


@app.route('/schedule')
def schedule():
    if 'user_id' not in session: 
        return redirect(url_for('login', message='Please log in to continue', type='error'))
    
    user = User.query.get(session['user_id'])


    #get week offset
    week_offset = int(request.args.get('week', 0))

    # Find monday of the current week then shift by week_offset
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=7)

    # filter to find sessions that fall between monday and sunday inclusive
    study_sessions = StudySession.query.filter(
        StudySession.user_id == user.id,
        StudySession.date >= start_of_week,
        StudySession.date < end_of_week
    ).order_by(StudySession.date, StudySession.time).all()


    #convert the list to a hashmap for fast lookups in the frontend 

    session_map = defaultdict(list)
    for studys in study_sessions: 
        session_map[(studys.date, studys.time)].append(studys)



    #get weekly summary 

    weekly_summary = calculate_weekly_stats(study_sessions)


    return render_template(
        'schedule.html', 
        user=user, 
        study_sessions=study_sessions, 
        session_map = session_map,
        week_start=start_of_week, 
        week_offset=week_offset, 
        weekly_summary = weekly_summary,
        timedelta=timedelta
        )


@app.route('/check_email', methods=['POST'])
def check_email():
    email = request.json.get('email')
    exists = User.query.filter_by(email=email).first() is not None
    return jsonify({'exists': exists})

@app.route('/export-calendar')
def export_calendar(): 
    if 'user_id' not in session: 
        return redirect(url_for('login', message='Please log in to continue', type='error'))
    
    user = User.query.get(session['user_id'])

    # get all sessions for the user 

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
        to_zone = pytz.utc

        # treat session time as AEST 
        local_dt = from_zone.localize(datetime.combine(session_obj.date, time(hour=session_obj.time)))

        #convert to utc for the ics file 

        start_dt = local_dt.astimezone(to_zone)
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


@app.route('/assessments')
def assessments(): 
    if 'user_id' not in session:
        return redirect(url_for('login', message='Please log in to continue', type='error'))

    user = User.query.get(session['user_id'])
    now = datetime.now()

    
    formatted_assessments = []

    # Sort assessments by due date
    sorted_assessments = sorted(user.assessments, key=lambda assessment: assessment.due_date)

    # Build list of future assessments
    for assessment in sorted_assessments:
        if assessment.due_date >= now:
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
                "due_date_input": due_date_input
            }

            formatted_assessments.append(assessment_entry)

    return render_template('assessments.html', assessments=formatted_assessments, subject_data=subject_data)

@app.route('/edit-assessment', methods=['POST'])
def edit_assessment(): 
    if 'user_id' not in session: 
        return redirect(url_for('login', message='Please log in to continue', type='error'))
    
    # get data from form 

    assessment_id = request.form.get('assessment_id')
    title = request.form.get('title')
    subject_code = request.form.get('subject_code')
    description = request.form.get('description')
    due_date_str = request.form.get('due_date')

    #parse due date 
    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%dT%H:%M")
    except ValueError:
        return redirect(url_for('assessments', message='Please enter a correct date', type='error'))
    
    # find assessment 

    assessment = Assessment.query.get(assessment_id)

    if assessment and assessment.user_id == session['user_id']:

        due_date_changed = (assessment.due_date != due_date)

        assessment.title = title
        assessment.subject_code = subject_code
        assessment.description = description
        assessment.due_date = due_date

        db.session.commit()

        if due_date_changed: 
            StudySession.query.filter_by(assessment_id=assessment.id).delete() 
            db.session.commit()

            #regenerate study sessions 
            generate_schedule_for_new_assessments(assessment.user_id)

            return redirect(url_for('assessments', message='Due date changed - sessions regenerated.', type='success'))

        return redirect(url_for('assessments', message='Assessment updated successfully', type='success'))
    else:
        return redirect(url_for('assessments', message='Assessment not found', type='error'))
    

@app.route('/delete-assessment', methods=['POST'])
def delete_assessment():
    if 'user_id' not in session:
        return redirect(url_for('login', message='Please log in to continue', type='error'))

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

if __name__ == '__main__': 
    app.run(debug=True)