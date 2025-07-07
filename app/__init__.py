from flask import Flask
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

def create_app():
    """
    Factory function to create and configure the Flask application.
    """
    app = Flask(__name__, instance_relative_config=True)

    # Load default configuration from instance/config.py
    app.config.from_pyfile('config.py', silent=True)

    # Load the configuration from environment variables (e.g., SECRET_KEY, DATABASE_URL)
    # This overrides values from config.py if environment variables are set.
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key') # Fallback for development
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///vertical_search.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Suppress warning

    # Initialize the database
    from app.database import init_db
    with app.app_context():
        init_db() # Create tables if they don't exist

    # Register blueprints (routes)
    from . import routes
    app.register_blueprint(routes.bp)

    # Optional: Add error handles, context processors, etc. here
    return app
