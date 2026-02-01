"""
Database configuration and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
import os

# Import settings
from app.core.settings import settings

# Create base class for models
Base = declarative_base()

# Create database engine
# NullPool prevents connection pooling issues in serverless/container environments
engine = create_engine(
    settings.get_database_url,
    poolclass=NullPool if settings.ENVIRONMENT == "production" else None,
    echo=settings.DEBUG,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for getting database session in FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database (create tables)"""
    Base.metadata.create_all(bind=engine)


def migrate_db():
    """Run migration SQL file (alternative to SQLAlchemy migrations)"""
    migration_file = os.path.join(os.path.dirname(__file__), "../../migrations/001_init.sql")
    
    if not os.path.exists(migration_file):
        raise FileNotFoundError(f"Migration file not found: {migration_file}")
    
    with open(migration_file, "r") as f:
        sql = f.read()
    
    with engine.connect() as connection:
        # Split by semicolon and execute each statement
        for statement in sql.split(";"):
            if statement.strip():
                connection.execute(statement)
        connection.commit()
