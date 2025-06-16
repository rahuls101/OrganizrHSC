from werkzeug.security import generate_password_hash, check_password_hash
from models import User, db
from flask import flash, redirect, url_for
import re

def validate_user_signup(fname, lname, email, pword, cpword, terms):

    # First name criteria: less than 25 alphanumeric characters
    
    if len(fname) < 1 or len(fname) > 25:
        return False
    elif not fname.isalnum():
        return False
    
    # Last name criteria: less than 25 alphanumeric characters

    if len(lname) < 1 or len(lname) > 25:
        return False
    elif not lname.isalnum():
        return False
    
    # Email criteria: Must be a valid email, not in use

    pattern = r'^[\w\.-]+@[a-zA-Z\d-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        pass
    else:
        return False
    
    existing_user = User.query.filter_by(email=email).first()
    if existing_user: 
        return False
    
    # Password criteria: at least 8 characters, One uppercase, one lowercase, one number, match the confirmpassword

    if len(pword) < 8:
        return False
    elif not re.search(r'[A-Z]', pword):
        return False

    elif not re.search(r'[a-z]', pword):
        return False
    
    elif not re.search(r'\d', pword):  
        return False
    
    if pword != cpword: 
        return False
    

    # make sure the terms and conditions checkbox is checked 

    if not terms: 
        return False

    return True


def validate_user_login(email, password): 
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        return user 
    return None


def create_user(fname, lname, email, pword):
    hashed_pw = generate_password_hash(pword)
    new_user = User(firstname=fname, lastname=lname, email=email, password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()