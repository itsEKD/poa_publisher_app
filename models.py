from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import mongo

# Roles
ROLE_USER = "user"
ROLE_AUTHOR = "author"
ROLE_ADMIN = "admin"



class User:
    def __init__(self, user_data):
        if isinstance(user_data, dict):
            self.id = str(user_data["_id"])
            self.email = user_data["email"]
            self.name = user_data.get("name", "")
            self.role = user_data.get("role", "user")
            self.password_hash = user_data.get("password")
        elif isinstance(user_data, User):
            self.id = user_data.id
            self.email = user_data.email
            self.name = user_data.name
            self.role = user_data.role
            self.password_hash = user_data.password_hash
        else:
            raise TypeError("Expected user_data to be a dict or User instance, got {}".format(type(user_data)))
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    @classmethod
    def get_by_email(cls, db, email):
        user_data = db.users.find_one({"email": email})
        return cls(user_data) if user_data else None

    @staticmethod
    def get_by_id(db, user_id):
        try:
            user_doc = db.users.find_one({"_id": ObjectId(user_id)})
            return User(user_doc) if user_doc else None  # ✅ wrapped into User
        except:
            return None

    @classmethod
    def create_user(cls, db, user_dict):
        user_dict["password"] = generate_password_hash(user_dict["password"])
        db.users.insert_one(user_dict)
        return cls(user_dict)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id


class Book:
    @staticmethod
    def create_book(book_data):
        book_data["approved"] = False  # Default to unapproved
        return mongo.db.books.insert_one(book_data)

    @staticmethod
    def get_by_id(book_id):
        try:
            oid = ObjectId(book_id)
            return mongo.db.books.find_one({"_id": oid})
        except:
            return None

    @staticmethod
    def update_book(book_id, updates):
        try:
            oid = ObjectId(book_id)
            return mongo.db.books.update_one({"_id": oid}, {"$set": updates})
        except:
            return None

    @staticmethod
    def delete_book(book_id):
        try:
            oid = ObjectId(book_id)
            return mongo.db.books.delete_one({"_id": oid})
        except:
            return None

    @staticmethod
    def get_unapproved_books():
        return list(mongo.db.books.find({"approved": False}))

    @staticmethod
    def approve_book(book_id):
        return mongo.db.books.update_one(
            {"_id": ObjectId(book_id)},
            {"$set": {"approved": True}}
        )


# Optional: You can add this if you're importing with wildcard `from models import *`
__all__ = ["User", "Book", "ROLE_USER", "ROLE_AUTHOR", "ROLE_ADMIN"]
