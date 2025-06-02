from flask import Flask, render_template
from dotenv import load_dotenv
import os 

load_dotenv() 

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "defaultsecretkey")

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/upload')
def upload():
    return render_template('upload.html')

@app.route('/schedule')
def schedule():
    return render_template('schedule.html')

if __name__ == '__main__': 
    app.run(debug=True)