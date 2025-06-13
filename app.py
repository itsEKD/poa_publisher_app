import os
from flask import Flask, g, render_template, send_from_directory, flash, redirect, url_for
from flask_pymongo import PyMongo
from flask_login import LoginManager
from flask_dance.contrib.google import make_google_blueprint
from bson.objectid import ObjectId
from extensions import mongo, login_manager, csrf
from config import Config
from models import User
from auth.routes import auth_bp
from admin.routes import admin_bp
from author.routes import author_bp
from books.routes import books_bp
from blog.route import blog_bp
from shop.routes import shop_bp
from flask_wtf.csrf import CSRFProtect, CSRFError
from datetime import timedelta


login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = app.config["SECRET_KEY"]
    mongo.init_app(app)
    app.db = mongo.db
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    csrf.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        user_data = User.get_by_id(mongo.db, user_id)
        if user_data:
            return User(user_data)
        return None
    @app.before_request
    def attach_db():
            g.db = app.db

    # Upload folder
    upload_folder = os.path.join(os.getcwd(), "uploads")
    os.makedirs(upload_folder, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = upload_folder
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
    app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads", "book_pdfs")
    app.config["COVER_UPLOAD_FOLDER"] = os.path.join("static", "uploads", "book_covers")
    app.config["BLOG_COVER_UPLOAD_FOLDER"] = os.path.join("static", "uploads", "blog_covers")
    os.makedirs(app.config["BLOG_COVER_UPLOAD_FOLDER"], exist_ok=True) # Ensure directory exists
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)
    
    # Google OAuth
    google_bp = make_google_blueprint(
        client_id=app.config["GOOGLE_OAUTH_CLIENT_ID"],
        client_secret=app.config["GOOGLE_OAUTH_CLIENT_SECRET"],
        scope=["profile", "email"],
        redirect_url="/auth/google/authorized",
    )
    app.register_blueprint(google_bp, url_prefix="/auth/google")

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(author_bp, url_prefix="/author")
    app.register_blueprint(books_bp, url_prefix="/books")
    app.register_blueprint(blog_bp, url_prefix="/blog")
    app.register_blueprint(shop_bp, url_prefix="/")

    # Home route
    @app.route("/")
    def home():
        featured_books = list(app.db.books.find({"approved": True}).limit(5))
        bestsellers = list(app.db.books.find({"approved": True}).limit(5))
        recent_books = list(app.db.books.find({"approved": True}).sort("uploaded_at", -1).limit(5))
        return render_template("home.html", featured_books=featured_books, bestsellers=bestsellers, recent_books=recent_books)

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        flash('The form session expired or was tampered with. Please try again.', 'danger')
        return redirect(url_for('shop.contact'))
    return app
@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(mongo.db, user_id)
    

# ✅ Required to run the app
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
    