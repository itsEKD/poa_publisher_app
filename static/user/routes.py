import os
from flask import (Blueprint, render_template, request, redirect, url_for, flash, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from extensions import mongo
from models import Book, ROLE_AUTHOR
from utils import role_required
from utils import user_required

author_bp = Blueprint("user", __name__, template_folder="templates/user")
ALLOWED_EXTENSIONS = {"pdf"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS



@author_bp.route("/dashboard")
@user_required
def dashboard():
    ...

