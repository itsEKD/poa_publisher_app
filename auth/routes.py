from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, current_app
)
from flask_login import login_user
from werkzeug.security import check_password_hash, generate_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from extensions import mongo
from utils import send_reset_email
from models import User, ROLE_USER
from extensions import csrf  # ✅ Import csrf from the main app module where it's initialized


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# -------------------------------
# Token Utilities
# -------------------------------

def generate_reset_token(email):
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return s.dumps(email, salt="password-reset-salt")

def verify_reset_token(token, max_age=3600):
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        return s.loads(token, salt="password-reset-salt", max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


# -------------------------------
# LOGIN
# -------------------------------

@auth_bp.route("/login", methods=["GET", "POST"])
@csrf.exempt
def login():
    if request.method == "POST":
        email = request.form.get("email", "").lower()
        password = request.form.get("password", "")

        db = current_app.db
        user_data = User.get_by_email(db, email)

        if user_data and user_data.verify_password(password):
            user = user_data
            login_user(user)

            session["user_id"] = str(user.id)
            session["user_email"] = user.email
            session["user_role"] = user.role

            flash("✅ Logged in successfully!", "success")
            return redirect(url_for("home"))

        flash("❌ Invalid email or password.", "danger")

    return render_template("auth/login.html")




# -------------------------------
# LOGOUT
# -------------------------------
@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


# -------------------------------
# REGISTER
# -------------------------------
@auth_bp.route("/register", methods=["GET", "POST"])
@csrf.exempt
def register():
    if request.method == "POST":
        fname = request.form.get("firstname", "")
        sname = request.form.get("sname", "")
        tname = request.form.get("tname", "")
        email = request.form.get("email", "").lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not email or not password:
            flash("Email and password are required.", "warning")
            return redirect(url_for("auth.register"))

        if password != confirm:
            flash("Passwords do not match.", "warning")
            return redirect(url_for("auth.register"))

        db = current_app.db
        if User.get_by_email(db, email):
            flash("Email already registered.", "warning")
            return redirect(url_for("auth.register"))

        full_name = " ".join(filter(None, [fname, sname, tname]))
        User.create_user(db, {
            "email": email,
            "password": password,
            "role": ROLE_USER,
            "name": full_name
        })

        flash("✅ Registration successful! Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


# -------------------------------
# PASSWORD RESET REQUEST
# -------------------------------
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@csrf.exempt
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email").lower()
        user = mongo.db.users.find_one({"email": email})

        if user:
            token = generate_reset_token(email)
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            send_reset_email(email, token)

        flash("📩 If an account exists, a reset link has been sent to your email.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


# -------------------------------
# PASSWORD RESET CONFIRMATION
# -------------------------------
@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
@csrf.exempt
def reset_password(token):
    email = verify_reset_token(token)
    if not email:
        flash("❌ The reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        new_password = request.form.get("password")
        if not new_password:
            flash("Password cannot be empty.", "warning")
            return redirect(request.url)

        hashed_pw = generate_password_hash(new_password)
        mongo.db.users.update_one({"email": email}, {"$set": {"password": hashed_pw}})
        flash("✅ Password updated! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", token=token)


@auth_bp.route("/whoami")
def whoami():
    return f"ID: {session.get('user_id')} | Email: {session.get('user_email')} | Role: {session.get('user_role')}"


