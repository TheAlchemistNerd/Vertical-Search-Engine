from flask import Blueprint, render_template, request, current_app
from sqlalchemy import func
from app.models import Publication, PublicationFTS, Author
from app.database import get_db

bp = Blueprint('main', __name__)

@bp.route('/', methods=['GET'])
def index():
    """
    Renders the homepage with a search bar and displays initial or search results.
    """
    query = request.args.get('query', '').strip()
    publications = []
    error_message = None

    db_session = None # Initialize db_session to ensure it's closed in finally block

    try:
        db_session = next(get_db()) # Get a database session

        if query:
            # Perform FTS search
            # The 'MATCH' operator in SQLite FTS5 requires the FTS table name followed by the query.
            # SQLAlchemy's .matches() method simplifies this.
            fts_results = db_session.query(PublicationFTS.rowid).filter(PublicationFTS.matches(query)).limit(50).all()

            # Extract publication IDs from FTS results
            publication_ids = [r.rowid for r in fts_results]

            if publication_ids:
                # Fetch full publication details from the main publications table
                # Ensure publications are ordered for consistent display, e.g., by year and title
                publications = db_session.query(Publication)\
                                         .filter(Publication.id.in_(publication_ids))\
                                         .order_by(Publication.publication_year.desc().nulls_last(), Publication.title.asc())\
                                         .all()
            else:
                error_message = "No publications found matching your query."

        else:
            # If no query, display some recent publications or a welcome message
            publications = db_session.query(Publication)\
                                     .order_by(Publication.publication_year.desc().nulls_last(), Publication.id.desc())\
                                     .limit(10).all() # Show a few recent ones
    except Exception as e:
        current_app.logger.error(f"Database error in index route: {e}")
        error_message = "An error occurred while retrieving publications. Please try again later."
    finally:
        if db_session:
            db_session.close()

    return render_template('index.html', publications=publications, query=query, error_message=error_message)
