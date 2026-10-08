import os
import tempfile

# These must be set BEFORE the app is imported, so config.py picks them up.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_tmp, 'test.db')}"
os.environ["OUTPUT_DIR"] = os.path.join(_tmp, "generated")

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    """Give every test an empty database."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def valid_payload():
    return {
        "event_name": "Python Workshop 2026",
        "issued_by": "Tech Club",
        "issue_date": "7 October 2026",
        "recipients": [
            {"name": "Asha Rao", "email": "asha@example.com"},
            {"name": "Ravi Kumar", "email": "ravi@example.com"},
        ],
    }