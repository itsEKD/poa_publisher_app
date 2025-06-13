import os
from flask_pymongo import PyMongo
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_dance.contrib.google import make_google_blueprint
from flask_pymongo import PyMongo
from flask_login import LoginManager
import stripe
from flask_wtf.csrf import CSRFProtect



stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

mongo = PyMongo()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
csrf = CSRFProtect()

# Create a “blank” Google blueprint; we’ll configure client_id/secret in app.py
google_bp = make_google_blueprint(
    client_id=None,
    client_secret=None,
    scope=["profile", "email"],
    redirect_url="/auth/google/authorized"
)
