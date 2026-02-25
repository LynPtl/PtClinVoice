import pytest
import time
from fastapi.testclient import TestClient
from unittest.mock import patch

from main import app
from database import TaskStatus, create_db_and_tables

create_db_and_tables()
client = TestClient(app)

def test_worker_oom_handling():
    """
    Verifies that if the underlying run_stt_isolated throws a MemoryError,
    the background worker catches it and safely transitions the task to FAILED
    without crashing the main FastAPI process.
    """
    with patch("worker.run_stt_isolated") as mock_stt:
        # Simulate an OOM kill inside the strictly isolated whisper process
        mock_stt.side_effect = MemoryError("STT Process killed violently (possible OOM). Exit code: -9")
        
        # Dispatch
        payload = {"audio_path": "tests/fixtures/standard_accent.mp3"}
        resp = client.post("/api/v1/transcribe/mock", json=payload)
        
        assert resp.status_code == 200
        task_id = resp.json()["task_id"]
        
        # Poll
        final_state = None
        for _ in range(10):
            status_resp = client.get(f"/tasks/{task_id}")
            state = status_resp.json()
            if state["status"] in ["COMPLETED", "FAILED"]:
                final_state = state
                break
            time.sleep(0.5)
            
        assert final_state is not None, "Task did not resolve."
        assert final_state["status"] == "FAILED"
        assert "STT Process killed violently" in final_state["error_message"]
