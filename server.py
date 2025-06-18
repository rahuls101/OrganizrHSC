from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from markupsafe import escape
from dotenv import load_dotenv
from models import db, User
from auth import validate_user_signup, validate_user_login, create_user
import os 
from datetime import datetime, timezone

load_dotenv() 

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "defaultsecretkey")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)

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

@app.route('/upload')
def upload():
    if 'user_id' not in session: 
        return redirect(url_for('login', message='Please log in to continue', type='error'))
    
    user = User.query.get(session['user_id'])
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