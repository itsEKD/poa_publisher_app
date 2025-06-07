import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from models import Book, ROLE_AUTHOR
from utils import role_required
from models import User, Book, ROLE_AUTHOR
from datetime import datetime





author_bp = Blueprint("author", __name__, template_folder="templates/author")

ALLOWED_EXTENSIONS = {"pdf"}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@author_bp.route("/dashboard")
def dashboard():
    if session.get("user_role") != ROLE_AUTHOR:
        flash("Access denied: Authors only", "danger")
        return redirect(url_for("home"))

    db = current_app.db
    email = session.get("user_email")
    approved_books = list(db.books.find({"author_email": email, "approved": True}))
    pending_books = list(db.books.find({"author_email": email, "approved": False}))

    return render_template("author/dashboard.html",
                           approved_books=approved_books,
                           pending_books=pending_books)


@author_bp.route("/manage-books")
def manage_books():
    # logic here
    return render_template("author/manage_books.html")



# Ensure UPLOAD_FOLDER is set in your app config
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@author_bp.route("/upload", methods=["GET", "POST"])
def upload_book():
    if session.get("user_role") != ROLE_AUTHOR:
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
        return redirect(url_for("author.dashboard"))

    return render_template("author/upload.html")



# Edit Book
@author_bp.route("/edit/<book_id>", methods=["GET", "POST"])
def edit_book(book_id):
    if session.get("user_role") != "author":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    db = current_app.db
    user_id = session.get("user_id")

    book = db.books.find_one({"_id": ObjectId(book_id), "author_id": ObjectId(user_id)})
    if not book:
        flash("Book not found or not authorized.", "danger")
        return redirect(url_for("author.dashboard"))

    if request.method == "POST":
        title = request.form.get("title")
        file = request.files.get("file")

        update_fields = {"title": title, "approved": False}

        if file and file.filename.endswith(".pdf"):
            filename = secure_filename(file.filename)
            file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
            update_fields["file_path"] = filename

        db.books.update_one(
            {"_id": ObjectId(book_id)},
            {"$set": update_fields}
        )

        flash("Book updated and sent for re-approval.", "success")
        return redirect(url_for("author.dashboard"))

    return render_template("author/edit_book.html", book=book)

# Delete Book
@author_bp.route("/delete/<book_id>")
def delete_book(book_id):
    if session.get("user_role") != "author":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    db = current_app.db
    user_id = session.get("user_id")

    book = db.books.find_one({"_id": ObjectId(book_id), "author_id": ObjectId(user_id)})
    if book:
        db.books.delete_one({"_id": ObjectId(book_id)})
        flash("Book deleted.", "info")
    else:
        flash("Not authorized or book not found.", "danger")

    return redirect(url_for("author.dashboard"))
