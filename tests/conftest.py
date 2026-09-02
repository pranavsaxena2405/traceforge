import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project paths to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SDK_DIR = os.path.join(BASE_DIR, "sdk")
COLLECTOR_DIR = os.path.join(BASE_DIR, "collector")

if SDK_DIR not in sys.path:
    sys.path.insert(0, SDK_DIR)
if COLLECTOR_DIR not in sys.path:
    sys.path.insert(0, COLLECTOR_DIR)

from collector.app.config import settings
from collector.app.db import get_db, Base
from collector.app.main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", settings.DATABASE_URL)


def is_postgres_available(url: str) -> bool:
    """Check if target PostgreSQL server is listening."""
    import socket
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 5432
        s = socket.create_connection((host, port), timeout=0.5)
        s.close()
        return True
    except Exception:
        return False



@pytest.fixture(scope="session")
def engine():
    if not is_postgres_available(TEST_DATABASE_URL):
        pytest.skip(
            f"PostgreSQL server not available at {TEST_DATABASE_URL}. "
            "Start PostgreSQL (e.g. `docker compose up -d postgres`) to run DB tests."
        )
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    def _get_test_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def app_client_no_db():
    """Client for testing non-DB endpoints like health when DB is offline."""
    with TestClient(app) as test_client:
        yield test_client
