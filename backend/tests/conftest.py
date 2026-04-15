import os
import sys
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend root is in path for main.py import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Grouping delayed imports after sys.path modification
from main import app  # noqa: E402
from pythia.core.structured_logging import setup_structured_logging  # noqa: E402
from pythia.infrastructure.persistence.database import get_db  # noqa: E402
from pythia.infrastructure.persistence.models import Base  # noqa: E402

setup_structured_logging("ERROR", "test.log")

pytest_plugins = ("pytest_asyncio",)

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function", autouse=True)
def setup_test_db():
    """Create and drop tables for every test to guarantee perfect isolation."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function", name="db_session")
def db_session_fixture() -> Generator[Session, None, None]:
    """Provide a pristine database session."""
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide a TestClient with a session-overridden database."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
