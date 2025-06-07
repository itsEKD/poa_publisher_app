from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import mongo







# Roles
ROLE_USER = "user"
ROLE_AUTHOR = "author"
ROLE_ADMIN = "admin"

class User:
    def __init__(self, user_data):
        self.id = str(user_data["_id"])
        self.email = user_data["email"]
        self.name = user_data.get("name", "")
        self.role = user_data.get("role", "user")  # default to 'user'

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    @staticmethod
    def get_by_email(db, email):
        return db.users.find_one({"email": email})

    @staticmethod
    def create_user(db, user_doc):  # user_doc has email/password/role
        user_doc["password"] = generate_password_hash(user_doc["password"])
        return db.users.insert_one(user_doc)

    @staticmethod
    def verify_password(stored_hash, plain_pw):
        return check_password_hash(stored_hash, plain_pw)

@staticmethod
def add_reaction(blog_id, reaction_type):
    return mongo.db.blogs.update_one(
        {"_id": ObjectId(blog_id)},
        {"$inc": {f"reactions.{reaction_type}": 1}}
    )


class Book:
    @staticmethod
    def create_book(book_data):
        """Insert new book document."""
        return mongo.db.books.insert_one(book_data)

    @staticmethod
    def get_by_id(book_id):
        """Find book by _id."""
        try:
            oid = ObjectId(book_id)
        except:
            return None
        return mongo.db.books.find_one({"_id": oid})

    @staticmethod
    def update_book(book_id, updates):
        """Update book document fields."""
        try:
            oid = ObjectId(book_id)
        except:
            return None
        return mongo.db.books.update_one({"_id": oid}, {"$set": updates})

    @staticmethod
    def delete_book(book_id):
        """Delete book document."""
        try:
            oid = ObjectId(book_id)
        except:
            return None
        return mongo.db.books.delete_one({"_id": oid})

@staticmethod
def create_book(book_data):
    book_data["approved"] = False  # Add default approval status
    return mongo.db.books.insert_one(book_data)

@staticmethod
def get_unapproved_books():
    return list(mongo.db.books.find({"approved": False}))

@staticmethod
def approve_book(book_id):
    return mongo.db.books.update_one(
        {"_id": ObjectId(book_id)},
        {"$set": {"approved": True}}
    )





__all__ = ["User", "Book", "ROLE_AUTHOR", "ROLE_ADMIN", ...]

