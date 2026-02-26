import pytest
import time
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.database import engine, User, TranscriptionTask, TaskStatus, create_db_and_tables
from app.auth import get_password_hash
from sqlmodel import Session

create_db_and_tables()
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    create_db_and_tables()
    with Session(engine) as session:
        session.exec(User.__table__.delete())
        session.exec(TranscriptionTask.__table__.delete())
        session.commit()
    yield

def test_worker_oom_handling():
    """
    Verifies that if the underlying run_stt_isolated throws a MemoryError,
    the background worker catches it and safely transitions the task to FAILED
    without crashing the main FastAPI process.
    """
    # Create test user
    with Session(engine) as session:
        user = User(username="oom_user", hashed_password=get_password_hash("password123"))
        session.add(user)
        session.commit()
    
    # Get token
    resp = client.post("/api/auth/login", data={"username": "oom_user", "password": "password123"})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    with patch("app.worker.run_stt_isolated") as mock_stt:
        # Simulate an OOM kill inside the strictly isolated whisper process
        mock_stt.side_effect = MemoryError("STT Process killed violently (possible OOM). Exit code: -9")
        
        # Dispatch
        payload = {"audio_path": "tests/fixtures/standard_accent.mp3"}
        resp = client.post("/api/v1/transcribe/mock", json=payload, headers=headers)
        
        assert resp.status_code == 200
        task_id = resp.json()["task_id"]
        
        # Poll
        final_state = None
        for _ in range(10):
            status_resp = client.get(f"/api/tasks/{task_id}", headers=headers)
            state = status_resp.json()
            if state["status"] in ["COMPLETED", "FAILED"]:
                final_state = state
                break
            time.sleep(0.5)
            
        assert final_state is not None, "Task did not resolve."
        assert final_state["status"] == "FAILED"
        assert "STT Process killed violently" in final_state["error_message"]
