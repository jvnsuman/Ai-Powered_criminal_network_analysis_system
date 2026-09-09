"""
db/connection.py

SQLAlchemy engine/session setup, built from config.get_settings().
This is the one place that knows how to connect to the database —
everything else (db/repository.py, api/main.py) gets a Session
through get_db() rather than touching the engine directly.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import get_settings

settings = get_settings()

# SQLite needs check_same_thread=False to be usable across the
# request-handling threads FastAPI may use; PostgreSQL (the default)
# doesn't need or want this.
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency — yields a Session for the duration of one
    request, then always closes it. Use as
    `db: Session = Depends(get_db)` in a route handler.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create any tables that don't exist yet, based on db.models.Base's
    metadata. Safe to call repeatedly (no-op for tables that already
    exist). Called from api/main.py's startup lifespan handler.
    """
    from db.models import Base

    Base.metadata.create_all(bind=engine)
