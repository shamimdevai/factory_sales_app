import os
from contextlib import contextmanager
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
# CHANGE THIS LINE:
from src.database.base_class import Base

# 1. Explicitly load the .env file from your project root
load_dotenv()

# 2. Retrieve DATABASE_URL with a fallback for safety
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL not found in environment variables. "
        "Please ensure your .env file exists and contains a valid connection string."
    )

# 3. Initialize the SQLAlchemy engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# 4. Create a thread-safe scoped session factory
session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Session = scoped_session(session_factory)


def init_db():
    """
    Creates all database tables defined in the models schema
    if they do not already exist in PostgreSQL.
    """
    try:
        # Import models here locally to register them on the Base metadata before creation
        from src.database import models

        Base.metadata.create_all(bind=engine)
        print("[Database]: Tables checked/initialized successfully.")
    except Exception as e:
        print(f"[Database Error]: Table creation failed: {e}")
        raise e


@contextmanager
def get_db_session():
    """Context manager to guarantee clean transactional sessions and resource cleanup."""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()