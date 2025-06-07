from flask import Blueprint, render_template, request
from extensions import mongo

books_bp = Blueprint('books', __name__)

@books_bp.route("/books")
def all_books():
    search_query = request.args.get("q", "").strip()
    category_filter = request.args.get("category", "").strip()

    query = {"approved": True}

    if search_query:
        query["$or"] = [
            {"title": {"$regex": search_query, "$options": "i"}},
            {"author": {"$regex": search_query, "$options": "i"}}
        ]

    if category_filter:
        query["category"] = category_filter

    books = list(mongo.db.books.find(query))
    categories = mongo.db.books.distinct("category")
    return render_template("books/all_books.html", books=books, categories=categories)
