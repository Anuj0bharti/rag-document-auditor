import os
from pathlib import Path
import tempfile
os.environ["DATABASE_URL"] = f"sqlite:///{Path(tempfile.gettempdir()) / 'rda-test.db'}"
os.environ["EMBEDDING_PROVIDER"] = "hashing"
os.environ["LLM_MODE"] = "mock"
os.environ["UPLOAD_DIR"] = str(Path(tempfile.gettempdir()) / "rda-test-uploads")
import pytest
from fastapi.testclient import TestClient
from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def auth_headers(client):
    response = client.post("/api/auth/register", json={"email": "test@example.com", "password": "correct-horse-battery"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}

