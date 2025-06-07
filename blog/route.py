from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime
from extensions import mongo  # make sure this is imported correctly
from bson.objectid import ObjectId



blog_bp = Blueprint("blog", __name__, url_prefix="/blog")


def add_reaction(blog_id, reaction_type):
    return mongo.db.blogs.update_one(
        {"_id": ObjectId(blog_id)},
        {"$inc": {f"reactions.{reaction_type}": 1}}
    )





@blog_bp.route("/react/<blog_id>/<reaction_type>", methods=["POST"])
def react(blog_id, reaction_type):
    if "user_id" not in session:
        return jsonify({"success": False, "error": "Authentication required."}), 401

    valid_reactions = ["like", "love", "funny", "wow", "dislike"]
    if reaction_type not in valid_reactions:
        return jsonify({"success": False, "error": "Invalid reaction."}), 400

    user_id = session["user_id"]
    blog = mongo.db.blogs.find_one({"_id": ObjectId(blog_id)})
    if not blog:
        return jsonify({"success": False, "error": "Blog not found."}), 404

    reactions = blog.get("reactions", {})
    user_reactions = reactions.get("user_reactions", {})

    user_reactions[user_id] = reaction_type
    reactions["user_reactions"] = user_reactions

    mongo.db.blogs.update_one(
        {"_id": ObjectId(blog_id)},
        {"$set": {"reactions": reactions}}
    )

    # Recalculate counts for each reaction type
    counts = {r: list(user_reactions.values()).count(r) for r in valid_reactions}

    return jsonify({
        "success": True,
        "user_reaction": reaction_type,
        "counts": counts
    })



@blog_bp.route("/create", methods=["GET", "POST"])
def create():
    
    if session.get("user_role") not in ["admin", "author"]:
        flash("You are not authorized to create blog posts.", "danger")
        return redirect(url_for("blog.list_all"))
    
    if request.method == "POST":
        title = request.form.get("title")
        category = request.form.get("category")
        content = request.form.get("content")
        author = session.get("user_email", "Anonymous")

        blog_data = {
            "title": title,
            "category": category,
            "content": content,
            "author": author,
            "created_at": datetime.utcnow(),
            "reactions": {
  "user_reactions": {
    "user_id_1": "like",
    "user_id_2": "dislike"
  }
}


        }

        mongo.db.blogs.insert_one(blog_data)
        flash("Blog post published successfully!", "success")
        return redirect(url_for("blog.list_all"))

    return render_template("blog.html")

@blog_bp.route("/blogs")
def blog_list():
    user_id = session.get("user_id")
    blogs = list(mongo.db.blogs.find())

    # Load current user's reactions separately
    reactions = mongo.db.reactions.find({"user_id": ObjectId(user_id)})
    user_reactions = {str(r["blog_id"]): r["reaction"] for r in reactions}

    return render_template("blog/list.html", blogs=blogs, user_reactions=user_reactions)


@blog_bp.route("/all")
def list_all():
    blogs = mongo.db.blogs.find().sort("created_at", -1)
    return render_template("blog_list.html", blogs=blogs)



   

    # rest of your form logic...
