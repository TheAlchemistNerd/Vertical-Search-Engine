from flask import Blueprint, render_template, request, current_app
from sqlalchemy import func
from app.models import Publication, PublicationFTS, Author
from app.database import get_db

bp = Blueprint('main', __name__)

@bp .route('/', methods=['GET'])
def index():
    """
    Render the homepage with a search bar and displays intial or search results.
    """
    query = request.args.get('quey', '').strip()
    publications = []
    error_message = None

    if query:
        # Perform FTS search
        db_session = next(get_db()) # get a session
        try:
           # Query FTS5 table for matching rowids
            # Use MATCH operator for FTS5 queries
            # For simplicity, we directly query PublicationFTS.
            # For more advanced scenarios, consider a join or subquery.
            fts_results = db_session.query(PublicationFTS.rowid)\
                                    .filter(PublicationFTS.match(query))\
                                    .limit(50)\
                                    .all() # Limit results to prevent overwhelming display.
            
            # Extract publication IDs for FTS results
            publication_ids 
            