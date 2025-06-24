from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from markupsafe import escape
from dotenv import load_dotenv
from models import db, User, Assessment
import fitz
from auth import validate_user_signup, validate_user_login, create_user, allowed_file
import os 
from datetime import datetime, timezone

load_dotenv() 

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "defaultsecretkey")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'


UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER): 
    os.makedirs(UPLOAD_FOLDER)


db.init_app(app)


# make utility functions for parsing pdfs


def extract_subject_code(pdf): 
    subject_map = {
        "English": "ENG",
        "Mathematics": "MAT",
        "Physics": "PHY",
        # Add every HSC subject later
    }
    text = pdf.get_text()
    for subjectname, code in subject_map.items():
        if subjectname in text:
            return code
    return "GEN"


def extract_due_date(pdf): 
    # search for the keyword which is 'due date'
    text_instances = pdf.search_for('Due Date')

    for inst in text_instances:
        # expand the rectangle to the right to capture the value next to it
        extended_rect = fitz.Rect(inst.x1, inst.y0, inst.x1 + 200, inst.y1)  # adjust width as needed
        date = pdf.get_text("text", clip=extended_rect).strip()
        return date
    
def parse_date(date_str): 
    try: 
        return datetime.strptime(date_str, "%A, %d %B %Y")
    except ValueError: 
        return None

def extract_title(pdf): 
    # search for the keyword which is 'due date'
    text_instances = pdf.search_for('Task title')

    for inst in text_instances:
        # expand the rectangle to the right to capture the value next to it
        extended_rect = fitz.Rect(inst.x1, inst.y0, inst.x1 + 200, inst.y1)  # adjust width as needed
        title = pdf.get_text("text", clip=extended_rect).strip()
        return title

def extract_description(pdf): 
    return 'Placeholder description'




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
    session.pop('user_id', None)
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
        files = request.files.getlist('files')
        results = []

        if not files:
            return jsonify({'error': 'No files provided'}), 400

        for file in files:
            if not file or not allowed_file(file.filename):
                results.append({
                    'filename': file.filename if file else 'unknown',
                    'error': 'Invalid file type'
                })
                continue

            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                doc = fitz.open(filepath)
                page = doc[0]

                subject_code = extract_subject_code(page)
                title = extract_title(page)
                due_date_raw = extract_due_date(page)
                due_date = parse_date(due_date_raw)
                description = extract_description(page)

                doc.close()
                os.remove(filepath)

                results.append({
                    'filename': filename,
                    'subject_code': subject_code,
                    'title': title,
                    'description': description,
                    'due_date': due_date.isoformat() if due_date else None
                })

            except Exception as e:
                results.append({
                    'filename': filename,
                    'error': str(e)
                })

        return jsonify({'results': results})

    return render_template('upload.html', user=user)

@app.route('/schedule')
def schedule():
    if 'user_id' not in session: 
        return redirect(url_for('login', message='Please log in to continue', type='error'))
    
    user = User.query.get(session['user_id'])
    return render_template('schedule.html')


@app.route('/check_email', methods=['POST'])
def check_email():
    email = request.json.get('email')
    exists = User.query.filter_by(email=email).first() is not None
    return jsonify({'exists': exists})



if __name__ == '__main__': 
    app.run(debug=True)