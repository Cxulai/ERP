from app import app

# Vercel WSGI entry point
# The Vercel Python runtime looks for a variable named 'app' which is a WSGI callable.
# Flask's `app` instance is already a WSGI callable.
