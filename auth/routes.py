from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, current_app
)
from werkzeug.security import check_password_hash
from models import User, ROLE_USER
from bson.objectid import ObjectId

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# -----------------------------------------------------------
# LOGIN
# -----------------------------------------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email", "").lower()
        password = request.form.get("password", "")

        db = current_app.db                           # <-- single source of DB
        user_data = User.get_by_email(db, email)      # <-- pass db + email

        if user_data and User.verify_password(user_data["password"], password):
            #session["user_id"]    = str(user_data["_id"])
            session["user_email"] = user_data["email"]
            session["user_role"]  = user_data.get("role", ROLE_USER)
            flash("Logged in successfully!", "success")
            return redirect(url_for("home"))

        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html")


# -----------------------------------------------------------
# LOGOUT
# -----------------------------------------------------------
@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


# -----------------------------------------------------------
# REGISTER
# -----------------------------------------------------------
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email    = request.form.get("email", "").lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")
        fname = request.form.get("firstname", "")
        sname = request.form.get("sname", "")
        tname = request.form.get("tname", "")

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

        User.create_user(db, {"email": email, "password": password, "role": ROLE_USER})
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")
