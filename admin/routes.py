import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from bson.objectid import ObjectId
from utils import admin_required
from werkzeug.utils import secure_filename
from functools import wraps
from models import User, Book, ROLE_AUTHOR, ROLE_ADMIN, ROLE_USER
from datetime import datetime




admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ALLOWED_EXTENSIONS = {"pdf"}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# utils.py
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("You must be logged in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper


@admin_bp.route("/dashboard")
def dashboard():
    if session.get("user_role") != ROLE_ADMIN:
        flash("Access denied: Admins only", "danger")
        return redirect(url_for("home"))
    
    
    db = current_app.db
    user_id = session.get("user_id")

    approved_books = list(db.books.find({"author_id": ObjectId(user_id), "approved": True}))
    pending_books = list(db.books.find({"author_id": ObjectId(user_id), "approved": False}))

    return render_template("admin/dashboard.html",
                           approved_books=approved_books,
                           pending_books=pending_books)




@admin_bp.route("/books/pending")
def pending_books():
    if session.get("user_role") != ROLE_ADMIN:
        flash("Admins only!", "danger")
        return redirect(url_for("home"))

    books = Book.get_unapproved_books()
    return render_template("admin/pending_books.html", books=books)


@admin_bp.route("/books")
def manage_books():
    if session.get("user_role") != ROLE_ADMIN:
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    db = current_app.db
    pending_books = list(db.books.find({"approved": False}))
    approved_books = list(db.books.find({"approved": True}))

    return render_template("admin/manage_books.html",
                           pending_books=pending_books,
                           approved_books=approved_books)


@admin_bp.route("/books/approve/<book_id>")
def approve_book(book_id):
    if session.get("user_role") != ROLE_ADMIN:
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    db = current_app.db
    db.books.update_one({"_id": ObjectId(book_id)}, {"$set": {"approved": True}})
    flash("Book approved!", "success")
    return redirect(url_for("admin.manage_books"))


@admin_bp.route("/books/delete/<book_id>")
def delete_book(book_id):
    if session.get("user_role") != ROLE_ADMIN:
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    db = current_app.db
    db.books.delete_one({"_id": ObjectId(book_id)})
    flash("Book deleted.", "info")
    return redirect(url_for("admin.manage_books"))



@admin_bp.route("/upload", methods=["GET", "POST"])
def upload_book():
    if session.get("user_role") != ROLE_ADMIN:
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":
        title = request.form.get("title")
        file = request.files.get("file")
        price = request.form.get("price")
        description = request.form.get("description")

        if not title or not file:
            flash("Both title and file are required.", "warning")
            return redirect(url_for("author.upload_book"))

        if not allowed_file(file.filename):
            flash("Only PDF files are allowed.", "warning")
            return redirect(url_for("author.upload_book"))

        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        # Save to database
        book_doc = {
            "title": title,
            "author": session.get("user_email"),
            "description": description,
            "file_path": filename,
            "category": "category",
            "approved": False,
            "price": price,
            "author_email": session.get("user_email"),
            "uploaded_at": datetime.utcnow()
        }


        db = current_app.db
        db.books.insert_one(book_doc)
        flash("Book uploaded! Awaiting approval.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/upload.html")
