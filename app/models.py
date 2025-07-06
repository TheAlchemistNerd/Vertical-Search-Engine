# app/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from app.database import Base

# Many-to-many association table for Publications and Authors
publication_authors_association = Table(
    'publication_authors_association',
    Base.metadata,
    Column('publication_id', Integer, ForeignKey('publications.id')),
    Column('author_id', Integer, ForeignKey('authors.id'))
)

class Publication(Base):
    """
    Represents a research publication.
    """
    __tablename__ = 'publications'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    publication_link = Column(String, unique=True, nullable=False)
    publication_year = Column(Integer)
    abstract = Column(Text) # Storing abstract if available

    # Many-to-many relationship with Author
    authors = relationship(
        'Author',
        secondary=publication_authors_association,
        back_populates='publications'
    )

    def __repr__(self):
        return f"<Publication(id={self.id}, title='{self.title}')>"

class Author(Base):
    """
    Represents an author of a research publication.
    """
    __tablename__ = 'authors'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True) # Assuming author names are unique enough
    author_link = Column(String, unique=True) # Link to author's profile on PurePortal

    # Many-to-many relationship with Publication
    publications = relationship(
        'Publication',
        secondary=publication_authors_association,
        back_populates='authors'
    )

    def __repr__(self):
        return f"<Author(id={self.id}, name='{self.name}')>"

# --- FTS5 Table for Full-Text Search ---
# Note: We remove 'sqlite_fts': True from __table_args__ here.
# The FTS table will be created via raw SQL in app/database.py.
class PublicationFTS(Base):
    """
    Dedicated FTS5 table for full-text search on publication titles and abstracts.
    The 'content' column will hold the searchable text.
    The 'rowid' maps directly to the 'id' of the Publication table.
    """
    __tablename__ = 'publications_fts'
    # 'sqlite_autoincrement': True is still valid for rowid if it's a primary key
    # in an FTS table, but we'll manage the FTS creation explicitly.
    # We define the columns that will be indexed.
    rowid = Column(Integer, primary_key=True) # rowid maps to Publication.id
    title = Column(Text)
    abstract = Column(Text)

    def __repr__(self):
        return f"<PublicationFTS(rowid={self.rowid}, title='{self.title[:30]}...')>"
