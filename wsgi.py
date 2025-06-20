# wsgi.py
from app import create_app

app = create_app()  # This is now the WSGI callable
