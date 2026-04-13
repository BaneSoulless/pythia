import os
import sys
from pathlib import Path

import pytest

# main.py lives at backend/main.py, outside the pythia package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pythia.core.structured_logging import setup_structured_logging  # noqa: E402

setup_structured_logging("ERROR", "test.log")

pytest_plugins = ("pytest_asyncio",)

from collections.abc import Generator  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402
from pythia.infrastructure.persistence.database import get_db  # noqa: E402
from pythia.infrastructure.persistence.models import Base  # noqa: F401
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function", autouse=True)
def setup_test_db():
    """Create and drop tables for every test to guarantee perfect isolation."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Provide a pristine database session."""
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session) -> Generator[TestClient, None, None]:

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
