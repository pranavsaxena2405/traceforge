from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from collector.app.config import settings
from collector.app.models import Base

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    connect_args={"connect_timeout": 3},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_health() -> bool:
    """Check database connectivity using fast socket ping followed by query."""
    import socket
    from urllib.parse import urlparse

    try:
        parsed = urlparse(settings.DATABASE_URL)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 5432
        s = socket.create_connection((host, port), timeout=0.5)
        s.close()
    except Exception:
        return False

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

