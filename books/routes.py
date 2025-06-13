from flask import Blueprint, render_template, request, session
from bson.objectid import ObjectId
from extensions import mongo

books_bp = Blueprint('books', __name__)

@books_bp.route('/books')
def view_books():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    filters = {'status': 'approved'}

    if query:
        filters['title'] = {'$regex': query, '$options': 'i'}

    if category:
        filters['category'] = category

    books = list(mongo.db.books.find(filters))

    user_id = session.get("user_id")
    purchased_ids = []

    if user_id:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if user:
            purchased_ids = [str(book_id) for book_id in user.get("purchased_books", [])]

    return render_template(
        'shop/view_books.html',
        books=books,
        user_logged_in=bool(user_id),
        purchased_ids=purchased_ids,
        search_query=query,
        selected_category=category,
        str=str
    )
    #return render_template('shop/view_books.html', books=books, user_logged_in=user_logged_in, purchased_ids=purchased_ids, str=str)
