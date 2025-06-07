import os
from flask import Flask, g, render_template, send_from_directory
from extensions import mongo, login_manager       # mongo = PyMongo()
from config import Config
from flask_dance.contrib.google import make_google_blueprint
from auth.routes   import auth_bp
from admin.routes  import admin_bp
from author.routes import author_bp
from books.routes import books_bp
from blog.route import blog_bp
from shop.routes import shop_bp
from models import User                            # User expects db argument






# --------------------------------------------------
# App & Config
# --------------------------------------------------
app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config["SECRET_KEY"]

# --------------------------------------------------
# PyMongo (cluster URI + DB name)
# --------------------------------------------------
mongo.init_app(app)        # uses MONGO_URI & MONGO_DBNAME
app.db = mongo.db          # now you can use current_app.db or g.db

# --------------------------------------------------
# Flask-Login
# --------------------------------------------------
login_manager.init_app(app)
login_manager.login_view = "auth.login"



@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(app.db, user_id)   # returns User object or None

# attach db to g for convenience
@app.before_request
def attach_db():
    g.db = app.db

# --------------------------------------------------
# Upload folder
# --------------------------------------------------
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

# --------------------------------------------------
# Google OAuth
# --------------------------------------------------
google_bp = make_google_blueprint(
    client_id=app.config["GOOGLE_OAUTH_CLIENT_ID"],
    client_secret=app.config["GOOGLE_OAUTH_CLIENT_SECRET"],
    scope=["profile", "email"],
    redirect_url="/auth/google/authorized",
)
app.register_blueprint(google_bp, url_prefix="/auth/google")

# --------------------------------------------------
# Blueprints
# --------------------------------------------------
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp,  url_prefix="/admin")
app.register_blueprint(author_bp, url_prefix="/author")
app.register_blueprint(books_bp, url_prefix="/books")
app.register_blueprint(blog_bp, url_prefix="/blog")
app.register_blueprint(shop_bp, url_prefix='/')
# --------------------------------------------------
# Routes
# --------------------------------------------------
@app.route("/")
def home():
    featured_books = list(app.db.books.find({"approved": True}).limit(5))
    bestsellers = list(app.db.books.find({"approved": True}).limit(5))
    recent_books = list(app.db.books.find({"approved": True}).sort("uploaded_at", -1).limit(5))

    return render_template(
        "home.html",
        featured_books=featured_books,
        bestsellers=bestsellers,
        recent_books=recent_books,
    )



@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --------------------------------------------------
# Main
# --------------------------------------------------
if __name__ == "__main__":
    print("✔  MONGO_URI   :", app.config['MONGO_URI'])
    print("✔  MONGO_DBNAME:", app.config['MONGO_DBNAME'])
    app.run(debug=True)
