# app/database.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Get database URL from environment variable
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///vertical_search.db')

# Create a SQLAlchemy engine
# connect_args={'check_same_thread': False} is necessary for SQLite in Flask
# when multiple threads access the same connection, which can happen with default Flask setup.
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()

def init_db():
    """
    Initializes the database by creating all tables defined in models
    and ensuring the FTS5 table is created as a virtual table.
    """
    import app.models # Import models to ensure Base knows about them

    # Create standard tables if they don't exist
    Base.metadata.create_all(bind=engine)
    print("Standard database tables created or already exist.")

    # Explicitly create the FTS5 virtual table if it doesn't exist
    # This is necessary because SQLAlchemy's declarative base doesn't
    # directly support CREATE VIRTUAL TABLE syntax via __table_args__.
    with engine.connect() as connection:
        # Check if the FTS table already exists
        result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='publications_fts';")).fetchone()
        if result is None:
            # If not, create the virtual FTS5 table
            # The columns here must match the ones defined in PublicationFTS model
            # that you want to be indexed for full-text search.
            create_fts_table_sql = """
            CREATE VIRTUAL TABLE publications_fts USING fts5(title, abstract);
            """
            connection.execute(text(create_fts_table_sql))
            connection.commit() # Commit the DDL operation
            print("FTS5 virtual table 'publications_fts' created.")
        else:
            print("FTS5 virtual table 'publications_fts' already exists.")

def get_db():
    """Dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
