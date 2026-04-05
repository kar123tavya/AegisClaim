import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

logger = logging.getLogger("aegisclaim.database")

# Create engine
engine = create_engine(
    settings.sqlite_db_url, 
    connect_args={"check_same_thread": False} # Needed for SQLite with FastAPI
)

# Session maker factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base
Base = declarative_base()

def init_db():
    from app.modules.analytics import models
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized at {settings.sqlite_db_url}")

def get_db():
    """Dependency to get DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
