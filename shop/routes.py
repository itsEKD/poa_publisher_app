from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from bson.objectid import ObjectId
from datetime import datetime
from extensions import mongo
import stripe
import os
from extensions import csrf
shop_bp = Blueprint("shop", __name__)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


# 🔹 Route: Homepage - Featured Books Only
@shop_bp.route("/", endpoint="home")
def homepage():
    featured_books = list(
        mongo.db.books.find({"featured": "True", "status": "approved"}).sort("created_at", -1).limit(6)
    )
    return render_template("home.html", books=featured_books)


# 🔹 Route: Book Storefront - Search, Filter, Browse All Approved Books
@shop_bp.route("/shop", endpoint="index")
def show_books():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    filters = {"status": "approved"}
    if query:
        filters["title"] = {"$regex": query, "$options": "i"}
    if category:
        filters["category"] = category

    books = list(mongo.db.books.find(filters).sort("created_at", -1))
    categories = mongo.db.books.distinct("category")

    purchased_ids = []
    user_id = session.get("user_id")
    if user_id:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if user:
            purchased_ids = [str(book_id) for book_id in user.get("purchased_books", [])]

    return render_template(
        "shop/index.html",
        books=books,
        categories=categories,
        purchased_ids=purchased_ids
    )


# 🔹 Route: Purchase a Book (Stripe Checkout)
@shop_bp.route("/buy/<book_id>", methods=["POST"])
@csrf.exempt
def buy_book(book_id):
    book = mongo.db.books.find_one({"_id": ObjectId(book_id)})
    if not book:
        return "Book not found", 404

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": book["title"]},
                "unit_amount": int(float(book["price"]) * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=url_for("shop.purchase_success", book_id=book_id, _external=True),
        cancel_url=url_for("shop.index", _external=True),
    )

    return redirect(checkout_session.url)


# 🔹 Route: Handle Successful Purchase
@shop_bp.route("/purchase-success/<book_id>")
def purchase_success(book_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in to complete the purchase.", "danger")
        return redirect(url_for("auth.login"))

    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$addToSet": {"purchased_books": ObjectId(book_id)}}
    )

    book = mongo.db.books.find_one({"_id": ObjectId(book_id)})
    return render_template("shop/purchase_success.html", book=book)


# 🔹 Route: Download Book (Only If Free or Purchased)
@shop_bp.route("/download/<book_id>")
def download_book(book_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Please login to download books.", "warning")
        return redirect(url_for("auth.login"))

    book = mongo.db.books.find_one({"_id": ObjectId(book_id)})
    if not book:
        return "Book not found", 404

    if book.get("price", 0) > 0:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if ObjectId(book_id) not in user.get("purchased_books", []):
            flash("You need to purchase this book first.", "danger")
            return redirect(url_for("shop.index"))

    return redirect(url_for("static", filename="uploads/book_pdfs/" + book["pdf_file"]))


# 🔹 Route: View Purchased Books
@shop_bp.route("/my-library")
def my_library():
    user_id = session.get("user_id")
    if not user_id:
        flash("Login to view your library.", "warning")
        return redirect(url_for("auth.login"))

    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    book_ids = user.get("purchased_books", [])
    books = list(mongo.db.books.find({"_id": {"$in": book_ids}}))

    return render_template("shop/my_library.html", books=books)


# 🔹 Route: About Page
@shop_bp.route("/about")
def about():
    return render_template("about.html")


# 🔹 Route: Contact Page
@shop_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        subject = request.form.get("subject")
        message = request.form.get("message")

        if not all([name, email, subject, message]):
            flash("Please fill in all fields.", "danger")
            return redirect(url_for("shop.contact"))

        contact_entry = {
            "name": name,
            "email": email,
            "subject": subject,
            "message": message,
            "submitted_at": datetime.utcnow(),
        }
        mongo.db.contacts.insert_one(contact_entry)
        flash("Message sent successfully!", "success")
        return redirect(url_for("shop.contact"))

    return render_template("contact.html")
