from werkzeug.security import generate_password_hash, check_password_hash
from models import User, db
from flask import flash, redirect, url_for
import re

def validate_user_signup(fname, lname, email, pword, cpword, terms):
    msg = ''

    # First name criteria: more than 1 and less than 25 alphanumeric characters
    
    if len(fname) < 2 or len(fname) > 25:
        msg = 'Invalid first name.'
        return False, msg
    elif not fname.isalnum():
        msg = 'Invalid first name.'
        return False, msg
    
    # Last name criteria: more than 1 and less than 25 alphanumeric characters

    if len(lname) < 2 or len(lname) > 25:
        msg = 'Invalid last name.'
        return False, msg
    elif not lname.isalnum():
        msg = 'Invalid last name.'
        return False, msg
    
    # Email criteria: Must be a valid email, not in use

    pattern = r'^[\w\.-]+@[a-zA-Z\d-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        pass
    else:
        msg = 'Invalid email address.'
        return False, msg
    
    existing_user = User.query.filter_by(email=email).first()
    if existing_user: 
        msg = 'User already exists.'
        return False, msg
    
    # Password criteria: at least 8 characters, One uppercase, one lowercase, one number, match the confirmpassword

    if len(pword) < 8:
        msg = 'Invalid password.'
        return False, msg
    elif not re.search(r'[A-Z]', pword):
        msg = 'Invalid password.'
        return False, msg

    elif not re.search(r'[a-z]', pword):
        msg = 'Invalid password.'
        return False, msg
    
    elif not re.search(r'\d', pword):  
        msg = 'Invalid password.'
        return False, msg
    
    if pword != cpword: 
        msg = 'Passwords do not match.'
        return False, msg
    

    # make sure the terms and conditions checkbox is checked 

    if not terms: 
        msg = 'Please accept the terms and conditions.'
        return False, msg

    return True, msg


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