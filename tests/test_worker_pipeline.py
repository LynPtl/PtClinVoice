import pytest
import time
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlmodel import Session, select
import json

from app.main import app
from app.database import engine, User, TranscriptionTask, TaskStatus, create_db_and_tables
from app.core.deepseek import DeepSeekClinicalAdapter
from app.auth import get_password_hash

create_db_and_tables()
client = TestClient(app)

AUDIO_STANDARD = "tests/fixtures/standard_accent.mp3"

MOCK_DEEPSEEK_RESPONSE_JSON = json.dumps({
    "dialogue": "[Patient]: My name is [REDACTED]. I have abdominal pain.\n[Doctor]: Let's run some tests.",
    "soap": {
        "subjective": "Patient [REDACTED] reports abdominal pain.",
        "objective": "Pending tests.",
        "assessment": "Abdominal pain of unknown etiology.",
        "plan": "Run diagnostic panels."
    }
})

@pytest.fixture
def mock_openai_client():
    """Mock the external cloud API to prevent bandwidth and token usage during CI/CD"""
    with patch("app.core.deepseek.OpenAI") as mock_openai:
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        
        mock_choice.message.content = MOCK_DEEPSEEK_RESPONSE_JSON
        mock_response.choices = [mock_choice]
        
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client_instance
        yield mock_openai

@pytest.fixture(autouse=True)
def setup_db():
    create_db_and_tables()
    with Session(engine) as session:
        session.exec(User.__table__.delete())
        session.exec(TranscriptionTask.__table__.delete())
        session.commit()
    yield

def test_background_worker_pipeline(mock_openai_client):
    """
    Simulates a client submitting a MockTranscribeRequest to the FastAPI background queue.
    The client then polls the /tasks/{task_id} endpoint until the status reaches COMPLETED.
    """
    # Create test user
    with Session(engine) as session:
        user = User(username="worker_user", hashed_password=get_password_hash("password123"))
        session.add(user)
        session.commit()
    
    # Get token
    resp = client.post("/api/auth/login", data={"username": "worker_user", "password": "password123"})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Dispatch Task
    payload = {"audio_path": AUDIO_STANDARD}
    resp = client.post("/api/v1/transcribe/mock", json=payload, headers=headers)
    
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data
    assert data["status"] == "PENDING"
    
    task_id = data["task_id"]
    
    # 2. Poll the Database via the API
    max_retries = 30 # Up to 30 seconds wait
    final_state = None
    
    for _ in range(max_retries):
        status_resp = client.get(f"/tasks/{task_id}", headers=headers)
        assert status_resp.status_code == 200
        state = status_resp.json()
        
        if state["status"] in ["COMPLETED", "FAILED"]:
            final_state = state
            break
            
        time.sleep(1)
        
    # 3. Assertions
    assert final_state is not None, "Worker pipeline timed out."
    assert final_state["status"] == "COMPLETED", f"Task failed: {final_state.get('error_message')}"
    
    assert final_state["transcript"] is not None
    assert "abdominal pain" in final_state["transcript"].lower()
    
    # Verify PII masking on the final output
    assert final_state["soap_note"] is not None
    soap_dict = json.loads(final_state["soap_note"])
    assert "[REDACTED]" in soap_dict["dialogue"]
    assert "[REDACTED]" in soap_dict["soap"]["subjective"]
