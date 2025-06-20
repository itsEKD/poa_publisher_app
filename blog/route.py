# blog/routes.py

import os
import uuid
from datetime import datetime
from bson.objectid import ObjectId
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, jsonify, current_app, abort
)
from werkzeug.utils import secure_filename

from extensions import mongo, csrf
from utils import role_required
from models import ROLE_AUTHOR, ROLE_ADMIN

blog_bp = Blueprint("blog", __name__, url_prefix="/blog", template_folder="templates/blog")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ------------------------
# Blog Creation
# ------------------------
@blog_bp.route("/create", methods=["POST", "GET"])
@csrf.exempt
@role_required(ROLE_AUTHOR, ROLE_ADMIN)
def create():
    if request.method == "GET":
        return render_template("blog/create.html")

    title = request.form.get("title", "").strip()
    category = request.form.get("category", "").strip()
    summary = request.form.get("summary", "").strip()
    tags_raw = request.form.get("tags", "").strip()
    content = request.form.get("content", "").strip()
    action = request.form.get("action")

    tags = [tag.strip() for tag in tags_raw.split(",") if tag.strip()] if tags_raw else []

    cover_image = request.files.get('cover_image')
    cover_path = None
    temp_path = None
    if cover_image and allowed_file(cover_image.filename):
        extension = secure_filename(cover_image.filename).rsplit('.', 1)[1].lower()
        unique_name = f"{uuid.uuid4()}.{extension}"
        upload_folder = os.path.join(current_app.root_path, "static", "temp", "blog_covers")
        os.makedirs(upload_folder, exist_ok=True)
        temp_path = os.path.join(upload_folder, unique_name)
        cover_image.save(temp_path)
        cover_path = f"/static/temp/blog_covers/{unique_name}"

    if action == "preview":
        return render_template("blog/preview.html", blog={
            "title": title,
            "category": category,
            "summary": summary,
            "tags": tags,
            "content": content,
            "cover_image": cover_path,
            "author_email": session.get("user_email"),
            "created_at": datetime.utcnow(),
        })

    if not title or not category or not content:
        flash("Title, Category, and Content are required.", "danger")
        return redirect(url_for("blog.create"))

    cover_filename = None
    if cover_path and temp_path:
        new_folder = os.path.join(current_app.root_path, "static", "uploads", "blog_covers")
        os.makedirs(new_folder, exist_ok=True)
        final_path = os.path.join(new_folder, os.path.basename(cover_path))
        os.rename(temp_path, final_path)
        cover_filename = os.path.basename(final_path)

    # Auto-approve if admin, otherwise mark as pending
    user_role = session.get("user_role")
    is_approved = user_role == ROLE_ADMIN

    blog_doc = {
        "title": title,
        "author_email": session.get("user_email"),
        "category": category,
        "summary": summary,
        "tags": tags,
        "content": content,
        "cover_image": cover_filename,
        "created_at": datetime.utcnow(),
        "approved": is_approved,
        "views": 0
    }

    try:
        mongo.db.blogs.insert_one(blog_doc)
        if is_approved:
            flash("✅ Blog post published successfully!", "success")
        else:
            flash("🎉 Blog post created successfully! Awaiting admin approval.", "info")
        return redirect(url_for("blog.view_blog"))
    except Exception as e:
        current_app.logger.error(f"Error saving blog post: {e}")
        flash("Failed to save blog post.", "danger")
        return redirect(url_for("blog.create"))



# ------------------------
# Edit Blog
# ------------------------
@blog_bp.route("/edit/<blog_id>", methods=["GET", "POST"])
@role_required(ROLE_AUTHOR, ROLE_ADMIN)
def edit_blog(blog_id):
    blog = mongo.db.blogs.find_one({"_id": ObjectId(blog_id)})
    if not blog:
        abort(404)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        summary = request.form.get("summary", "").strip()
        tags_raw = request.form.get("tags", "").strip()
        content = request.form.get("content", "").strip()
        action = request.form.get("action")

        tags = [tag.strip() for tag in tags_raw.split(",") if tag.strip()] if tags_raw else []

        cover_image = request.files.get('cover_image')
        cover_path = None
        if cover_image and allowed_file(cover_image.filename):
            extension = secure_filename(cover_image.filename).rsplit('.', 1)[1].lower()
            unique_name = f"{uuid.uuid4()}.{extension}"
            upload_folder = os.path.join(current_app.root_path, "static", "temp", "blog_covers")
            os.makedirs(upload_folder, exist_ok=True)
            temp_path = os.path.join(upload_folder, unique_name)
            cover_image.save(temp_path)
            cover_path = f"/static/temp/blog_covers/{unique_name}"

        if action == "preview":
            return render_template("blog/preview.html", blog={
                "title": title,
                "category": category,
                "summary": summary,
                "tags": tags,
                "content": content,
                "cover_image": cover_path or f"/static/uploads/blog_covers/{blog.get('cover_image')}",
                "author_email": blog.get("author_email"),
                "created_at": blog.get("created_at", datetime.utcnow())
            })

        update_data = {
            "title": title,
            "category": category,
            "summary": summary,
            "tags": tags,
            "content": content,
            "approved": False
        }

        if cover_path:
            new_folder = os.path.join(current_app.root_path, "static", "uploads", "blog_covers")
            os.makedirs(new_folder, exist_ok=True)
            final_path = os.path.join(new_folder, os.path.basename(cover_path))
            os.rename(temp_path, final_path)
            update_data["cover_image"] = os.path.basename(final_path)

        mongo.db.blogs.update_one({"_id": ObjectId(blog_id)}, {"$set": update_data})
        return redirect(url_for("blog.view", blog_id=blog_id))

    return render_template("blog/edit_blog.html", blog=blog)


# ------------------------
# Approve Blog
# ------------------------
@blog_bp.route('/approve/<blog_id>', methods=['POST'])
@role_required(ROLE_ADMIN)
@csrf.exempt
def approve(blog_id):
    mongo.db.blogs.update_one({"_id": ObjectId(blog_id)}, {"$set": {"approved": True}})
    flash("Blog post approved!", "success")
    return redirect(url_for("blog.view_blogs"))


# ------------------------
# Delete Blog
# ------------------------
@blog_bp.route('/delete/<blog_id>', methods=['POST'])
@role_required(ROLE_ADMIN, ROLE_AUTHOR)
def delete(blog_id):
    blog = mongo.db.blogs.find_one({"_id": ObjectId(blog_id)})
    if not blog:
        flash("Blog not found.", "danger")
        return redirect(url_for("blog.view_blogs"))

    email = session.get("user_email")
    role = session.get("user_role")
    if role != ROLE_ADMIN and blog.get("author_email") != email:
        flash("You can't delete this blog post.", "danger")
        return redirect(url_for("blog.view_blogs"))

    mongo.db.blogs.delete_one({"_id": ObjectId(blog_id)})
    flash("Blog post deleted.", "success")
    return redirect(url_for("blog.view_blogs"))


# ------------------------
# Comment on Blog
# ------------------------
@blog_bp.route("/comment/<blog_id>", methods=["POST"])
@csrf.exempt
def add_comment(blog_id):
    comment_text = request.form.get("comment", "").strip()
    if not comment_text:
        flash("Comment cannot be empty.", "warning")
        return redirect(url_for("blog.view", blog_id=blog_id))

    comment = {
        "blog_id": ObjectId(blog_id),
        "user": session.get("user_email", "Guest"),
        "text": comment_text,
        "timestamp": datetime.utcnow()
    }

    mongo.db.comments.insert_one(comment)
    flash("Your comment was added!", "success")
    return redirect(url_for("blog.view", blog_id=blog_id))


# ------------------------
# React to Blog Post
# ------------------------
@blog_bp.route('/react', methods=['POST'])
@csrf.exempt
def react():
    try:
        data = request.get_json()
        blog_id = data.get('blog_id')
        reaction = data.get('reaction')

        if not blog_id or reaction is None:
            return jsonify({'error': 'Missing blog_id or reaction'}), 400

        blog = mongo.db.blogs.find_one({'_id': ObjectId(blog_id)})
        if not blog:
            return jsonify({'error': 'Blog not found'}), 404

        user_id = str(session.get('user_id') or request.remote_addr)
        user_reactions = blog.get('reactions', {}).get('user_reactions', {}) or {}

        user_reactions.pop(user_id, None)
        if reaction != 'none':
            user_reactions[user_id] = reaction

        mongo.db.blogs.update_one(
            {'_id': ObjectId(blog_id)},
            {'$set': {'reactions.user_reactions': user_reactions}}
        )

        counts = {r: list(user_reactions.values()).count(r) for r in ["like", "dislike", "love", "funny", "wow"]}
        return jsonify({'user_reaction': user_reactions.get(user_id), 'counts': counts})

    except Exception as e:
        current_app.logger.error(f"Error in react route: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ------------------------
# View Dashboard
# ------------------------
@blog_bp.route("/dashboard")
@role_required(ROLE_ADMIN, ROLE_AUTHOR)
def view_blogs():
    blogs = list(mongo.db.blogs.find().sort("created_at", -1))
    for blog in blogs:
        blog["_id"] = str(blog["_id"])
    return render_template("blog/list_all.html", blogs=blogs)


# ------------------------
# List All Blogs (Public)
# ------------------------
@blog_bp.route('/blogs')
def list_all():
    page = int(request.args.get('page', 1))
    per_page = 6
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '')

    query = {}
    if search:
        query['title'] = {'$regex': search, '$options': 'i'}
    if category:
        query['category'] = category

    role = session.get('user_role')
    if role not in ['admin', 'author']:
        query['approved'] = True

    blogs_cursor = mongo.db.blogs.find(query).sort('created_at', -1)
    blogs = list(blogs_cursor.skip((page - 1) * per_page).limit(per_page))
    categories = mongo.db.blogs.distinct('category')
    total = mongo.db.blogs.count_documents(query)
    total_pages = (total + per_page - 1) // per_page

    return render_template("blog/list_all.html", blogs=blogs, categories=categories, page=page, total_pages=total_pages)


# ------------------------
# View Single Blog (LAST)
# ------------------------
@blog_bp.route('/<blog_id>')
def view(blog_id):
    try:
        blog = mongo.db.blogs.find_one({"_id": ObjectId(blog_id)})
    except Exception:
        abort(404)

    if not blog:
        abort(404)

    user_email = session.get("user_email")
    role = session.get("user_role")
    is_admin = role == ROLE_ADMIN
    is_author = blog.get("author_email") == user_email

    if not blog.get("approved") and not (is_admin or is_author):
        flash("This blog post is under review.", "warning")
        return redirect(url_for("blog.list_all"))

    if blog.get("approved"):
        mongo.db.blogs.update_one({"_id": ObjectId(blog_id)}, {"$inc": {"views": 1}})

    comments = mongo.db.comments.find({"blog_id": ObjectId(blog_id)}).sort("timestamp", -1)
    return render_template("blog/single_view.html", blog=blog, comments=comments, can_edit=is_admin or is_author)
