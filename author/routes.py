# author_routes.py (Revised)

import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from utils import role_required
from models import User, Book, ROLE_AUTHOR # Assuming these models are defined
from datetime import datetime
import uuid
from extensions import csrf # Assuming csrf is initialized in app.py


author_bp = Blueprint("author", __name__, template_folder="templates/author")



# Define your upload folders here (or ensure they are in app.py config)
UPLOAD_FOLDER_PDF = 'static/uploads/book_pdfs/'
UPLOAD_FOLDER_COVER = 'static/uploads/book_covers/'
BLOG_COVER_UPLOAD_FOLDER = 'static/uploads/blog_covers/' # Assuming you have this

ALLOWED_PDF_EXTENSIONS = {"pdf"}
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
ALLOWED_BLOG_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename, allowed_exts):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_exts

# --- Helper to determine if request is AJAX ---
def is_ajax():
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'

# --- Main Dashboard Entry Point (Initial Load) ---
@author_bp.route("/dashboard")
@role_required(ROLE_AUTHOR)
def dashboard():
    db = current_app.db
    user_id = session.get("user_id")

    total_users = db.users.count_documents({})
    total_books = db.books.count_documents({})
    pending_books_count = db.books.count_documents({"approved": False})
    my_pending_books = db.books.count_documents({"uploaded_by": ObjectId(user_id), "approved": False})
    books = list(db.books.find({"uploaded_by": ObjectId(user_id)}))

    return render_template("author/dashboard.html",
                           total_users=total_users,
                           total_books=total_books,
                           pending_books=pending_books_count,
                           my_pending_books=my_pending_books,
                           books=books)

# --- Route for "Manage Books" (My Uploaded Books) ---
@author_bp.route("/manage_my_books")
@role_required(ROLE_AUTHOR)
def manage_my_books():
    db = current_app.db
    user_email = session.get("user_email")

    approved_books = list(db.books.find({"author_email": user_email, "approved": True}))
    pending_books = list(db.books.find({"author_email": user_email, "approved": False}))

    context = {
        "approved_books": approved_books,
        "pending_books": pending_books
    }

    if is_ajax():
        # If AJAX, render only the partial for injection
        return render_template("author/my_books_overview.html", **context)
    else:
        # If not AJAX (direct access/refresh), render full dashboard with partial
        total_users = db.users.count_documents({})
        total_books = db.books.count_documents({})
        pending_books_count = len(pending_books)  # or just use len() since it's already queried

        return render_template(
            "author/dashboard.html",
            content_template="author/my_books_overview.html",
            total_users=total_users,
            total_books=total_books,
            pending_books_count=pending_books_count,  # ✅ renamed to avoid conflict
            **context
        )

# --- Route for "Upload a new book" ---
@author_bp.route("/upload")
@role_required(ROLE_AUTHOR)
def upload_page(): # Renamed from 'upload' to 'upload_page' for clarity, as 'upload' is used for POST
    db = current_app.db
    if is_ajax():
        return render_template("author/upload.html")
    else:
        # Fetch initial stats for the dashboard base here too
        total_users = db.users.count_documents({})
        total_books = db.books.count_documents({})
        pending_books_count = db.books.count_documents({"author_email": session.get("user_email"), "approved": False})
        return render_template("author/dashboard.html",
                               content_template="author/upload.html",
                               total_users=total_users,
                               total_books=total_books,
                               pending_books=pending_books_count)


# --- POST route for book upload form submission ---
@author_bp.route('/upload', methods=['GET', 'POST'])
@role_required(ROLE_AUTHOR)
@csrf.exempt
def upload():
    db = current_app.db

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        tags = request.form.get('tags', '').split(',')
        price = float(request.form.get('price') or 0.0)
        is_free = 'is_free' in request.form
        if is_free:
            price = 0.0

        pdf_file = request.files.get('pdf_file')
        cover_image = request.files.get('cover_image')

        if not pdf_file or pdf_file.filename == '':
            flash('PDF file is required.', 'danger')
            return redirect(url_for('author.upload'))

        os.makedirs(UPLOAD_FOLDER_PDF, exist_ok=True)
        os.makedirs(UPLOAD_FOLDER_COVER, exist_ok=True)

        pdf_filename = f"{uuid.uuid4().hex}_{secure_filename(pdf_file.filename)}"
        pdf_path = os.path.join(UPLOAD_FOLDER_PDF, pdf_filename)
        pdf_file.save(os.path.join(current_app.root_path, pdf_path))

        cover_path = "static/default_cover.jpg"
        if cover_image and cover_image.filename != '':
            if allowed_file(cover_image.filename, ALLOWED_IMAGE_EXTENSIONS):
                cover_filename = f"{uuid.uuid4().hex}_{secure_filename(cover_image.filename)}"
                cover_path = os.path.join(UPLOAD_FOLDER_COVER, cover_filename)
                cover_image.save(os.path.join(current_app.root_path, cover_path))
            else:
                flash("Invalid image file type.", "danger")
                return redirect(url_for("author.upload"))

        user_id = session.get('user_id')
        user = db.users.find_one({"_id": ObjectId(user_id)})
        author_name = user.get('name', 'Unknown')

        book_doc = {
            "title": title,
            "author": author_name,
            "description": description,
            "category": category,
            "tags": [tag.strip() for tag in tags if tag.strip()],
            "price": price,
            "is_free": is_free,
            "pdf_path": pdf_path,
            "cover_image": cover_path,
            "uploaded_by": ObjectId(user_id),
            "author_id": ObjectId(user_id),
            "author_email": session.get("user_email"),
            "status": "pending",
            "approved": False,
            "created_at": datetime.utcnow(),
            "ratings": [],
            "downloads": 0
        }

        db.books.insert_one(book_doc)
        flash("Book uploaded successfully and is pending approval.", "success")
        return redirect(url_for('author.manage_my_books'))

    # Render upload form inside dashboard with partial content
    return render_template("author/dashboard.html",
                           content_template="author/upload.html",
                           editing=False,
                           form_action=url_for('author.upload'))




# --- Route for "Manage Comments" ---
@author_bp.route("/manage_comments")
@role_required(ROLE_AUTHOR)
def manage_comments():
    db = current_app.db
    author_email = session.get("user_email")

    # Get the author's books
    books = list(db.books.find({"author_email": author_email}))
    book_ids = [book["_id"] for book in books]

    # Fetch comments for the author's books only
    comments_cursor = db.comments.find({"book_id": {"$in": book_ids}}).sort("created_at", -1)
    comments = []
    for comment in comments_cursor:
        # Match book to comment
        book = next((b for b in books if b["_id"] == comment["book_id"]), None)
        comments.append({
            "book_title": book["title"] if book else "Unknown",
            "comment_text": comment.get("text", ""),
            "commenter_email": comment.get("email", "Anonymous"),
            "created_at": comment.get("created_at"),
            "_id": comment["_id"]
        })

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("author/manage_comments.html", comments=comments)
    else:
        total_users = db.users.count_documents({})
        total_books = db.books.count_documents({})
        pending_books_count = db.books.count_documents({
            "author_email": author_email,
            "approved": False
        })
        return render_template("author/dashboard.html",
                               content_template="author/manage_comments.html",
                               total_users=total_users,
                               total_books=total_books,
                               pending_books=pending_books_count,
                               comments=comments)

# --- Route for "Write a Blog" ---
@author_bp.route("/blog")
@role_required(ROLE_AUTHOR)
def blog_page(): # Renamed from 'blog' to 'blog_page' for clarity
    db = current_app.db
    if is_ajax():
        return render_template("author/blog.html")
    else:
        # Fetch initial stats for dashboard base
        total_users = db.users.count_documents({})
        total_books = db.books.count_documents({})
        pending_books_count = db.books.count_documents({"author_email": session.get("user_email"), "approved": False})
        return render_template("author/dashboard.html",
                               content_template="author/blog.html",
                               total_users=total_users,
                               total_books=total_books,
                               pending_books=pending_books_count)

# --- POST route for blog post creation ---
@author_bp.route("/create_blog_post", methods=["POST"])
@role_required(ROLE_AUTHOR)
@csrf.exempt
def create_blog_post():
    db = current_app.db
    # ... (Your existing create_blog_post logic from author_routes.py) ...
    # Ensure BLOG_COVER_UPLOAD_FOLDER is accessible via current_app.config or defined globally.
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "").strip()
    summary = request.form.get("summary", "").strip()
    tags_raw = request.form.get("tags", "").strip()
    content = request.form.get("content", "").strip()

    if not title or not category or not content:
        flash("Title, Category, and Content are required.", "danger")
        return redirect(url_for("author.blog_page"))

    tags = [tag.strip() for tag in tags_raw.split(",") if tag.strip()] if tags_raw else []

    cover_filename_for_db = None
    if 'cover_image' in request.files:
        cover_image = request.files['cover_image']
        if cover_image.filename != '':
            if not allowed_file(cover_image.filename, ALLOWED_BLOG_IMAGE_EXTENSIONS):
                flash("Invalid blog cover image file type.", "danger")
                return redirect(url_for("author.blog_page"))

            unique_cover_base_name = str(uuid.uuid4())
            cover_extension = secure_filename(cover_image.filename).rsplit('.', 1)[1].lower()
            cover_filename_for_db = f"{unique_cover_base_name}.{cover_extension}"
            blog_cover_upload_folder = os.path.join(current_app.root_path, BLOG_COVER_UPLOAD_FOLDER) # Ensure path is correct
            os.makedirs(blog_cover_upload_folder, exist_ok=True)
            cover_full_path = os.path.join(blog_cover_upload_folder, cover_filename_for_db)

            try:
                cover_image.save(cover_full_path)
            except Exception as e:
                current_app.logger.error(f"Error saving blog cover image: {e}")
                flash(f"Error saving cover image: {e}", "danger")
                return redirect(url_for("author.blog_page"))

    author_email = session.get("user_email")
    if not author_email:
        flash("Author email not found in session. Please log in again.", "danger")
        return redirect(url_for("auth.login"))

    blog_post_doc = {
        "title": title,
        "author_email": author_email,
        "category": category,
        "summary": summary,
        "tags": tags,
        "content": content,
        "cover_image": cover_filename_for_db,
        "created_at": datetime.utcnow(),
        "approved": False,
        "views": 0
    }

    try:
        db.blog_posts.insert_one(blog_post_doc)
        flash("🎉 Blog post created successfully! Awaiting review.", "success")
        return redirect(url_for("author.blog_page")) # Redirect back to blog form or a "my_blog_posts" section
    except Exception as e:
        current_app.logger.error(f"Error inserting blog post into DB: {e}")
        flash(f"Failed to save blog post: {e}", "danger")
        return redirect(url_for("author.blog_page"))


# --- Other Author-specific routes (ensure they exist and are correctly implemented) ---

@author_bp.route("/edit_book/<book_id>", methods=["GET", "POST"])
@role_required(ROLE_AUTHOR)
def edit_book(book_id):
    db = current_app.db
    user_email = session.get("user_email")
    book = db.books.find_one({"_id": ObjectId(book_id), "author_email": user_email})
    
    if not book:
        flash("Book not found or unauthorized.", "danger")
        return redirect(url_for('author.manage_my_books'))

    if request.method == "POST":
        # Process the form data
        updated_data = {
            "title": request.form.get('title'),
            "author": request.form.get('author'),
            "description": request.form.get('description'),
            "category": request.form.get('category'),
            "price": float(request.form.get('price', 0)) if 'is_free' not in request.form else 0.0,
            "is_free": 'is_free' in request.form,
            "tags": [tag.strip() for tag in request.form.get('tags', '').split(',') if tag.strip()]
        }

        # Optional: handle file uploads here...

        db.books.update_one({"_id": ObjectId(book_id)}, {"$set": updated_data})
        flash("Book updated successfully!", "success")
        return redirect(url_for('author.manage_my_books'))

    # GET request — render the shared upload template in dashboard
    return render_template("author/dashboard.html",
                           content_template="author/upload.html",
                           editing=True,
                           book=book,
                           form_action=url_for("author.edit_book", book_id=book_id))


@author_bp.route("/delete_book/<book_id>", methods=["POST"])
@role_required(ROLE_AUTHOR)
@csrf.exempt # If submitting via form, might need csrf exempt
def delete_book(book_id):
    db = current_app.db
    # Ensure only author can delete their own book
    book = db.books.find_one({"_id": ObjectId(book_id), "author_email": session.get("user_email")})
    if book:
        # Optionally delete associated files (PDF, cover image) from disk
        if book.get('file_path'):
            pdf_path = os.path.join(current_app.root_path, UPLOAD_FOLDER_PDF, book['file_path'])
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        if book.get('cover_image') and book['cover_image'] != 'default-book.png':
            cover_path = os.path.join(current_app.root_path, UPLOAD_FOLDER_COVER, book['cover_image'])
            if os.path.exists(cover_path):
                os.remove(cover_path)

        db.books.delete_one({"_id": ObjectId(book_id)})
        flash("Book deleted successfully!", "info")
    else:
        flash("Book not found or unauthorized.", "danger")
    return redirect(url_for('author.manage_my_books'))

@author_bp.route('/book_feedback/<book_id>')
@role_required(ROLE_AUTHOR)
def book_feedback_page(book_id):
    db = current_app.db
    book = db.books.find_one({"_id": ObjectId(book_id), "author_email": session.get("user_email")})
    if not book:
        flash("Book not found or unauthorized access.", "danger")
        return redirect(url_for("author.manage_my_books"))

    feedback = book.get("admin_feedback", "No feedback available yet.") # Assuming admin feedback is stored here
    if is_ajax():
        return render_template("author/book_feedback.html", book=book, feedback=feedback)
    else:
        # Fetch initial stats for dashboard base
        total_users = db.users.count_documents({})
        total_books = db.books.count_documents({})
        pending_books_count = db.books.count_documents({"author_email": session.get("user_email"), "approved": False})
        return render_template("author/dashboard.html",
                               content_template="author/book_feedback.html",
                               total_users=total_users,
                               total_books=total_books,
                               pending_books=pending_books_count,
                               book=book,
                               feedback=feedback)
        
@author_bp.route('/author/view_messages')
def view_messages():
    db = current_app.db
    messages = db.messages.find().sort('submitted_at', -1)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/view_messages_partial.html', messages=messages)
    return render_template('admin/view_messages.html', messages=messages)


# DELETE COMMENT
@author_bp.route('/comments/delete/<comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    db = current_app.db
    try:
        result = db.comments.delete_one({'_id': ObjectId(comment_id)})
        if is_ajax():
            return jsonify(success=bool(result.deleted_count))
        flash("Comment deleted.", "success")
    except Exception as e:
        if is_ajax():
            return jsonify(success=False, message=str(e))
        flash("Failed to delete comment.", "danger")
    return redirect(url_for('author.manage_comments'))

# REPLY TO COMMENT
@author_bp.route('/comments/reply/<comment_id>', methods=['POST'])
@login_required
def reply_comment(comment_id):
    db = current_app.db
    reply_text = request.form.get('reply_text', '').strip()
    if not reply_text:
        if is_ajax():
            return jsonify(success=False, message="Reply text cannot be empty.")
        flash("Reply text is required.", "warning")
        return redirect(url_for('author.manage_comments'))

    reply_data = {
        "text": reply_text,
        "created_at": datetime.utcnow(),
        "author_email": session.get("user_email")
    }

    try:
        db.comments.update_one(
            {"_id": ObjectId(comment_id)},
            {"$push": {"replies": reply_data}}
        )
        if is_ajax():
            return jsonify(success=True)
        flash("Reply added.", "success")
    except Exception as e:
        if is_ajax():
            return jsonify(success=False, message=str(e))
        flash("Failed to add reply.", "danger")

    return redirect(url_for('author.manage_comments'))

@author_bp.route('/manage_blogs')
@role_required(ROLE_AUTHOR)
def manage_blogs():
    db = current_app.db
    user_email = session.get("user_email")
    blogs = list(db.blogs.find({"author_email": user_email}))
    return render_template("author/manage_blogs.html", blogs=blogs)

# Delete blog
@author_bp.route('/delete_blog/<blog_id>', methods=["POST"])
@role_required(ROLE_AUTHOR)
def delete_blog(blog_id):
    db = current_app.db
    user_email = session.get("user_email")
    result = db.blogs.delete_one({"_id": ObjectId(blog_id), "author_email": user_email})
    flash("Blog deleted." if result.deleted_count else "Blog not found or unauthorized.", "info")
    return redirect(url_for("author.manage_blogs"))

# Edit blog (renders the same form used for creation, pre-filled)
@author_bp.route('/edit_blog/<blog_id>', methods=["GET", "POST"])
@role_required(ROLE_AUTHOR)
def edit_blog(blog_id):
    db = current_app.db
    blog = db.blogs.find_one({"_id": ObjectId(blog_id), "author_email": session.get("user_email")})
    if not blog:
        flash("Blog not found or access denied.", "danger")
        return redirect(url_for('author.manage_blogs'))

    if request.method == "POST":
        updated = {
            "title": request.form.get("title"),
            "summary": request.form.get("summary"),
            "category": request.form.get("category"),
            "tags": [tag.strip() for tag in request.form.get("tags", "").split(",") if tag.strip()],
            "content": request.form.get("content"),
        }
        db.blogs.update_one({"_id": ObjectId(blog_id)}, {"$set": updated})
        flash("Blog updated successfully!", "success")
        return redirect(url_for('author.manage_blogs'))

    return render_template("author/upload_blog.html", blog=blog, editing=True)
