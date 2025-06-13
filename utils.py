from functools import wraps
from flask import redirect, url_for, flash, session
from flask_login import current_user
from itsdangerous import URLSafeTimedSerializer
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

load_dotenv()

EMAIL = os.getenv("EMAIL_USER")
PASSWORD = os.getenv("EMAIL_PASS")
SECRET_KEY = os.getenv('SECRET_KEY', 'your-default-secret')
SECURITY_SALT = 'password-reset-salt'





def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("You need to be logged in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        if current_user.role != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("shop.home"))  # Or another safe default page
        return f(*args, **kwargs)
    return decorated_function

def author_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Login required.", "warning")
            return redirect(url_for("auth.login"))
        if current_user.role != "author":
            flash("Author access only.", "danger")
            return redirect(url_for("shop.home"))
        return f(*args, **kwargs)
    return decorated_function

def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Login required.", "warning")
            return redirect(url_for("auth.login"))
        if current_user.role != "user":
            flash("User access only.", "danger")
            return redirect(url_for("shop.home"))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):  # Accepts multiple roles
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = session.get("user_role")
            if user_role not in roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("main.home"))  # Or wherever makes sense
            return f(*args, **kwargs)
        return decorated_function
    return decorator

SECRET_KEY = os.getenv('SECRET_KEY', 'your-default-secret')
SECURITY_SALT = 'password-reset-salt'

def generate_reset_token(email):
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    return serializer.dumps(email, salt=SECURITY_SALT)

def verify_reset_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    try:
        email = serializer.loads(token, salt=SECURITY_SALT, max_age=expiration)
    except Exception:
        return None
    return email


def send_reset_email(user_email, token):
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    subject = "Reset your password"
    body = f"Click the link to reset your password: {reset_url}\n\nIf you didn’t request this, ignore this email."

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = 'no-reply@poapublishers.com'
    msg['To'] = user_email

    # Example: use Gmail SMTP
    with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
        smtp.starttls()
        smtp.login(EMAIL, PASSWORD)
        smtp.send_message(msg)
