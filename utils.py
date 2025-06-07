from functools import wraps
from flask import redirect, url_for, flash, session
from flask_login import current_user



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


def role_required(role):
    """
    Decorator to restrict routes by user role.
    Example:
        @role_required('admin')
        def admin_dashboard(): ...
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role != role:
                flash("You do not have permission to access that page.", "warning")
                return redirect(url_for("shop.index"))
            return f(*args, **kwargs)
        return wrapped
    return decorator
