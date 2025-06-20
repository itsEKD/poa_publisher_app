import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app, session
from bson.objectid import ObjectId
from extensions import mongo
from utils import admin_required
from werkzeug.utils import secure_filename
from datetime import datetime
from extensions import csrf
import uuid
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ALLOWED_EXTENSIONS = {"pdf"}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


ALLOWED_PDF_EXTENSIONS = {"pdf"}
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
ALLOWED_BLOG_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
BLOG_COVER_UPLOAD_FOLDER = 'static/uploads/blog_covers/' # Assuming you have this

# --------------------
# Admin Dashboard
# --------------------

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    users_count = mongo.db.users.count_documents({})
    books_count = mongo.db.books.count_documents({})
    pending_count = mongo.db.books.count_documents({'approved': False})  # or your status logic

    return render_template(
        'admin/dashboard.html',
        total_users=users_count,
        total_books=books_count,
        pending_books=pending_count
    )
# --------------------
# Book Management
# --------------------

def preprocess_books(books):
    processed = []
    for book in books:
        book['_id'] = str(book['_id'])
        # Format uploaded_at if it exists and is datetime
        if 'uploaded_at' in book and isinstance(book['uploaded_at'], datetime):
            book['uploaded_at'] = book['uploaded_at'].strftime('%Y-%m-%d')
        # Default empty tags list
        if 'tags' not in book:
            book['tags'] = []
        # Price and free flag fallback
        book['price'] = float(book.get('price', 0))
        book['is_free'] = book.get('is_free', False)
        processed.append(book)
    return processed

@admin_bp.route('/admin/manage_books')
def manage_books():
    from datetime import datetime

    pending_books = list(mongo.db.books.find({'status': {'$ne': 'approved'}}))
    approved_books = list(mongo.db.books.find({'status': 'approved'}))

    def format_dates(book_list):
        for book in book_list:
            uploaded_at = book.get('uploaded_at')
            if isinstance(uploaded_at, datetime):
                book['uploaded_at'] = uploaded_at.strftime('%Y-%m-%d')
            elif isinstance(uploaded_at, str) and 'T' in uploaded_at:
                try:
                    dt = datetime.fromisoformat(uploaded_at.replace('Z', '+00:00'))
                    book['uploaded_at'] = dt.strftime('%Y-%m-%d')
                except:
                    book['uploaded_at'] = uploaded_at

    format_dates(pending_books)
    format_dates(approved_books)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/manage_books_partial.html',
                               pending_books=pending_books,
                               approved_books=approved_books)

    return render_template('admin/manage_books.html',
                           pending_books=pending_books,
                           approved_books=approved_books)


@admin_bp.route("/books/pending")
def pending_books():
    books = list(current_app.db.books.find({"approved": False}))
    return render_template("admin/pending_books.html", books=books)

@admin_bp.route("/books/delete/<book_id>", methods=["POST"])
@admin_required
@csrf.exempt
def delete_book(book_id):
    current_app.db.books.delete_one({"_id": ObjectId(book_id)})
    flash("Book deleted.", "info")
    return redirect(url_for("admin.manage_books"))


UPLOAD_FOLDER_PDF = 'static/uploads/book_pdfs/'
UPLOAD_FOLDER_COVER = 'static/uploads/book_covers/'


@admin_bp.route('/upload', methods=['GET', 'POST'])
@csrf.exempt
def upload():
    template = "admin/upload.html"

    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        description = request.form.get('description')
        category = request.form.get('category')
        price = float(request.form.get('price', 0))
        is_free = 'is_free' in request.form
        tags = [tag.strip() for tag in request.form.get('tags', '').split(',') if tag.strip()]
        
        pdf_file = request.files.get('pdf_file')
        cover_image = request.files.get('cover_image')

        if not pdf_file or pdf_file.filename == '':
            flash("PDF file is required.", "danger")
            return redirect(request.url)

        # Save PDF with relative path
        pdf_filename = secure_filename(pdf_file.filename)
        pdf_relative_path = f"static/uploads/book_pdfs/{pdf_filename}"
        pdf_full_path = os.path.join(current_app.root_path, pdf_relative_path)
        os.makedirs(os.path.dirname(pdf_full_path), exist_ok=True)
        pdf_file.save(pdf_full_path)

        # Save cover image (if provided) with relative path
        cover_relative_path = ""
        if cover_image and cover_image.filename:
            cover_filename = secure_filename(cover_image.filename)
            cover_relative_path = f"static/uploads/book_covers/{cover_filename}"
            cover_full_path = os.path.join(current_app.root_path, cover_relative_path)
            os.makedirs(os.path.dirname(cover_full_path), exist_ok=True)
            cover_image.save(cover_full_path)

        # Validate price for paid books
        if not is_free and not price:
            flash('Price is required for paid books.', 'danger')
            return redirect(request.url)

        # Save to MongoDB
        mongo.db.books.insert_one({
            "title": title,
            "author_name": author,
            "author_id": ObjectId(session.get('user_id')),
            "description": description,
            "category": category,
            "price": 0.0 if is_free else float(price),
            "is_free": is_free,
            "tags": tags,
            "pdf_path": pdf_relative_path,            # ⬅️ store relative path
            "cover_image": cover_relative_path,       # ⬅️ store relative path
            "featured": False,
            "status": "approved",
            "uploaded_at": datetime.utcnow()
        })

        flash("✅ Book uploaded and approved successfully.", "success")
        return redirect(url_for('admin.upload'))

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template(template)
    else:
        return render_template("admin/dashboard.html", content_template=template)




# --------------------
# Contact Messages
# --------------------
@admin_bp.route('/admin/view_messages')
def view_messages():
    messages = mongo.db.messages.find().sort('submitted_at', -1)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/view_messages_partial.html', messages=messages)
    return render_template('admin/view_messages.html', messages=messages)



@admin_bp.route('/messages/delete/<message_id>')

def delete_message(message_id):
    mongo.db.contacts.delete_one({"_id": ObjectId(message_id)})
    flash("Message deleted.", "info")
    return redirect(url_for('admin.view_messages'))

@admin_bp.route('/messages/<message_id>', methods=['GET', 'POST'])

def view_single_message(message_id):
    message = mongo.db.contacts.find_one({"_id": ObjectId(message_id)})

    if not message:
        flash("Message not found.", "danger")
        return redirect(url_for('admin.view_messages'))

    if request.method == 'POST':
        reply = request.form.get('reply')
        if reply:
            mongo.db.contacts.update_one(
                {"_id": ObjectId(message_id)},
                {"$set": {"reply": reply, "replied_at": datetime.utcnow()}}
            )
            flash("Reply saved.", "success")
            return redirect(url_for('admin.view_single_message', message_id=message_id))

    return render_template('admin/single_message.html', message=message)

@admin_bp.route('/manage_users')
@admin_required
def manage_users():
    users = list(mongo.db.users.find())
    return render_template('admin/manage_users.html', users=users)


@admin_bp.route('/manage_comments')
@admin_required
def manage_comments():
    comments = list(mongo.db.comments.find({'approved': False}))
    return render_template('admin/manage_comments.html', comments=comments)


@admin_bp.route("/comments/delete/<comment_id>", methods=["POST"])
def delete_comment(comment_id):
    current_app.db.comments.delete_one({"_id": ObjectId(comment_id)})
    flash("Comment deleted.", "info")
    return redirect(url_for("admin.manage_comments"))



# --------------------
# User Management
# --------------------
@admin_bp.route('/users/delete/<user_id>')
def delete_user(user_id):
    mongo.db.users.delete_one({"_id": ObjectId(user_id)})
    flash("User deleted.", "info")
    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/promote/<user_id>')
def promote_user(user_id):
    mongo.db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"role": "author"}})
    flash("User promoted to author.", "success")
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/comments/<comment_id>', methods=['GET', 'POST'])
def view_single_comment(comment_id):
    db = current_app.db
    comment = db.comments.find_one({"_id": ObjectId(comment_id)})

    if not comment:
        flash("Comment not found.", "danger")
        return redirect(url_for("admin.manage_comments"))

    if request.method == "POST":
        reply = request.form.get("reply", "").strip()
        if reply:
            db.comments.update_one(
                {"_id": ObjectId(comment_id)},
                {"$set": {
                    "admin_reply": reply,
                    "admin_replied_at": datetime.utcnow()
                }}
            )
            flash("Reply sent to comment.", "success")
            return redirect(url_for("admin.view_single_comment", comment_id=comment_id))
        else:
            flash("Reply cannot be empty.", "warning")

    return render_template("admin/single_comment.html", comment=comment)

@admin_bp.route('/admin/normalize_books', methods=['POST'])
@csrf.exempt
def normalize_books():
    from bson.decimal128 import Decimal128
    from datetime import datetime

    books = mongo.db.books.find()
    updated_count = 0

    for book in books:
        update_fields = {}

        # Price normalization
        if 'price' not in book or book['price'] in [None, '']:
            update_fields['price'] = Decimal128('0.00')
        else:
            try:
                if not isinstance(book['price'], Decimal128):
                    update_fields['price'] = Decimal128(str(book['price']))
            except (ValueError, TypeError):
                update_fields['price'] = Decimal128('0.00')

        # uploaded_at normalization
        if 'uploaded_at' in book and isinstance(book['uploaded_at'], str):
            try:
                update_fields['uploaded_at'] = datetime.fromisoformat(book['uploaded_at'].replace('Z', '+00:00'))
            except:
                update_fields['uploaded_at'] = datetime.utcnow()

        # Add defaults
        if 'author_name' not in book:
            update_fields['author_name'] = "Unknown"
        if 'pdf_path' not in book and 'file_path' in book:
            update_fields['pdf_path'] = f"static/uploads/book_pdfs/{book['file_path']}"
        if 'cover_image' not in book:
            update_fields['cover_image'] = ""
        if 'category' not in book:
            update_fields['category'] = "Uncategorized"
        if 'tags' not in book:
            update_fields['tags'] = []
        if 'is_free' not in book:
            update_fields['is_free'] = False
        if 'status' not in book:
            update_fields['status'] = "approved" if book.get('approved') else "pending"

        if update_fields:
            mongo.db.books.update_one({'_id': book['_id']}, {'$set': update_fields})
            updated_count += 1

    flash(f"{updated_count} books normalized successfully.", "success")
    return redirect(url_for('admin.manage_books'))



@admin_bp.route('/approve_book/<book_id>', methods=['POST'])
@csrf.exempt  # Remove this line if you are using Flask-WTF with csrf_token in form
def approve_book(book_id):
    db = current_app.db
    db.books.update_one({"_id": ObjectId(book_id)}, {"$set": {"status": "approved"}})
    flash("Book approved successfully!", "success")
    return redirect(url_for('admin.manage_books'))


@admin_bp.route('/reject_book/<book_id>')
@csrf.exempt
def reject_book(book_id):
    db = current_app.db
    db.books.delete_one({"_id": ObjectId(book_id)})
    flash("Book rejected and deleted.", "warning")
    return redirect(url_for('admin.manage_books'))

@admin_bp.route('/book_feedback/<book_id>', methods=['GET', 'POST'])
def book_feedback(book_id):
    db = current_app.db
    book = db.books.find_one({"_id": ObjectId(book_id)})
    if not book:
        flash("Book not found.", "danger")
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        feedback = request.form.get('feedback', '').strip()
        if feedback:
            # Store feedback (you may want to store feedback in a separate collection or in the book document)
            db.books.update_one({"_id": ObjectId(book_id)}, {"$set": {"admin_feedback": feedback}})
            flash("Feedback saved successfully.", "success")
            return redirect(url_for('admin.dashboard'))
        else:
            flash("Feedback cannot be empty.", "danger")

    return render_template('admin/book_feedback.html', book=book)
@admin_bp.route("/create_blog_post", methods=["POST"])
@admin_required
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
        return redirect(url_for("admin.blog_page"))

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
        return redirect(url_for("admin.blog_page")) # Redirect back to blog form or a "my_blog_posts" section
    except Exception as e:
        current_app.logger.error(f"Error inserting blog post into DB: {e}")
        flash(f"Failed to save blog post: {e}", "danger")
        return redirect(url_for("admin.blog_page"))

@admin_bp.route("/create", methods=["GET"])
@admin_required  # or adjust role as needed (admin?)
def create_blog_form():
    return render_template("blog/create_blog.html")

@admin_bp.route('/blog')
def blog():
    return render_template('admin/blog.html')  # Ensure this template exists

@admin_bp.route("/review_blogs")
@admin_required
def review_blogs():
    db = current_app.db
    blogs = list(db.blogs.find({"is_approved": False}))
    return render_template("admin/review_blogs.html", blogs=blogs)



@admin_bp.route("/approve_blog/<blog_id>", methods=["POST"])
@admin_required
def approve_blog(blog_id):
    current_app.db.blogs.update_one(
        {"_id": ObjectId(blog_id)},
        {"$set": {"is_approved": True}}
    )
    flash("✅ Blog approved.", "success")
    return redirect(url_for("admin.review_blogs"))


@admin_bp.route("/reject_blog/<blog_id>", methods=["POST"])
@admin_required
def reject_blog(blog_id):
    current_app.db.blogs.delete_one({"_id": ObjectId(blog_id)})
    flash("❌ Blog rejected and deleted.", "danger")
    return redirect(url_for("admin.review_blogs"))

