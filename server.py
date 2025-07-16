from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from markupsafe import escape
from dotenv import load_dotenv
from models import db, User, Assessment, StudySession
import fitz
from auth import validate_user_signup, validate_user_login, create_user, allowed_file
import os 
from datetime import datetime, timedelta
from pdf_utils import process_file
from werkzeug.utils import secure_filename
from schedule_generator import generate_schedule_for_new_assessments
from collections import defaultdict
from schedule_stats import calculate_weekly_stats
from subject_config import subject_data



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


    now = datetime.now()

    #retrieve upcoming assessments 

    assessments = [a for a in user.assessments if a.due_date >= now] 

    #sort assessments by due date

    sorted_assessments = sorted(assessments, key=lambda a: a.due_date)

    #list of assessments that are due within the next week (within 7 days): 

    upcoming_this_week = [a for a in sorted_assessments if 0 <= (a.due_date - now).days <= 7]


    return render_template(
        'dashboard.html',
        user=user, 
        now = now,
        sorted_assessments = sorted_assessments,
        num_close_assessments=len(upcoming_this_week), 
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



if __name__ == '__main__': 
    app.run(debug=True)