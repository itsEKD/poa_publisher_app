import os
from dotenv import load_dotenv

load_dotenv()                         #  <-- make sure this is called once

class Config:
    MONGO_URI   = os.getenv("MONGO_URI")      # cluster-only
    MONGO_DBNAME = os.getenv("MONGO_DBNAME")  # db name
    SECRET_KEY  = os.getenv("SECRET_KEY")
    GOOGLE_OAUTH_CLIENT_ID     = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")
    