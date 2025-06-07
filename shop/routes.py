from flask import Blueprint, render_template, request, redirect, url_for, session
from bson.objectid import ObjectId
import stripe
import os

from extensions import mongo

shop_bp = Blueprint("shop", __name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# 🔹 Route to handle book purchase with Stripe
@shop_bp.route("/buy/<book_id>", methods=["POST"])
def buy_book(book_id):
    book = mongo.db.books.find_one({"_id": ObjectId(book_id)})

    if not book:
        return "Book not found", 404

    session_data = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': book['title'],
                },
                'unit_amount': int(float(book['price']) * 100),  # Price in cents
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=url_for('shop.purchase_success', book_id=book_id, _external=True),
        cancel_url=url_for('shop.index', _external=True)
    )

    return redirect(session_data.url)


# 🔹 Route for purchase success
@shop_bp.route("/purchase-success/<book_id>")
def purchase_success(book_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$addToSet": {"purchased_books": ObjectId(book_id)}}
    )

    book = mongo.db.books.find_one({"_id": ObjectId(book_id)})
    return render_template("shop/purchase_success.html", book=book)


# 🔹 Main book shop/index route
@shop_bp.route("/shop", endpoint="index")
def show_books():
    query = request.args.get("q", "")
    category = request.args.get("category", "")

    # Filter query
    filters = {"approved": True}
    if query:
        filters["title"] = {"$regex": query, "$options": "i"}
    if category:
        filters["category"] = category

    books = list(mongo.db.books.find(filters))
    categories = mongo.db.books.distinct("category")

    # Check which books the user has purchased
    purchased_ids = []
    if "user_id" in session:
        user = mongo.db.users.find_one({"_id": ObjectId(session["user_id"])})
        purchased_ids = [str(book_id) for book_id in user.get("purchased_books", [])]

    return render_template(
        "shop/index.html",
        books=books,
        categories=categories,
        purchased_ids=purchased_ids
    )


# 🔹 Route to show purchased books
@shop_bp.route("/my-library")
def my_library():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    book_ids = user.get("purchased_books", [])
    books = mongo.db.books.find({"_id": {"$in": book_ids}})

    return render_template("shop/my_library.html", books=books)
