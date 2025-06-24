from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class User(db.Model): 
    id = db.Column(db.Integer, primary_key = True)
    firstname = db.Column(db.String(25), nullable=False)
    lastname = db.Column(db.String(25), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    assessments = db.relationship('Assessment', backref='user', lazy=True) #links to the assessment model below - one to many


class Assessment(db.Model): 
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False) 
    subject_code = db.Column(db.String(10), nullable = False) #e.g MAT
    title = db.Column(db.String(100), nullable = False)
    description = db.Column(db.Text, nullable = True)
    due_date = db.Column(db.DateTime, nullable = False)

