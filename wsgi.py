# wsgi.py
# This file serves as the entry point for running the Flask application.

from app import create_app

# Create the Flask application instance by calling the factory function
app = create_app()

# This 'app' object is what Flask's 'flask run' command will look for by default
# when FLASK_APP is set to 'wsgi.py'.