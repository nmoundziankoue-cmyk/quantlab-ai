"""SQLAlchemy engine, session factory, and FastAPI dependency."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from config import settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # reconnect on stale connections
    pool_size=10,
    max_overflow=20,
    echo=False,
)


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    """Yield a database session, committing on success and rolling back on error."""
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Health check helper
# ---------------------------------------------------------------------------
def check_db_connection() -> bool:
    """Return True if the database is reachable, False otherwise."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
