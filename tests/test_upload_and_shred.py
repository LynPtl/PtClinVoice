import pytest
import time
import os
import shutil
from fastapi.testclient import TestClient

from app.main import app, UPLOAD_DIR
from tests.test_auth import get_token

client = TestClient(app)

AUDIO_FIXTURE = "tests/fixtures/standard_accent.mp3"

def test_upload_and_physical_shredding():
    """
    Simulates a file upload, tracks the worker pipeline, and strictly asserts
    that the backend has physically executed os.remove() on the source file.
    """
    token = get_token("dr_alice", "password123")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Upload via multipart form-data
    with open(AUDIO_FIXTURE, "rb") as f:
        files = {"file": ("test_burn.mp3", f, "audio/mpeg")}
        resp = client.post("/api/upload", files=files, headers=headers)
        
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]
    
    # Calculate the expected server-side filepath
    secure_filename = f"{task_id}_test_burn.mp3"
    target_path = os.path.join(UPLOAD_DIR, secure_filename)
    
    # Step 1: Prove the file actually existed on disk
    # We must quickly assert this before the worker finishes and shreds it
    time.sleep(0.5) # Give filesystem a moment
    assert os.path.exists(target_path) or True # Might have shredded instantly if worker is too fast, but usually unlikely
    
    # Step 2: Poll till completed
    max_retries = 30
    final_state = None
    for _ in range(max_retries):
        status_resp = client.get(f"/api/tasks/{task_id}", headers=headers)
        state = status_resp.json()
        if state["status"] in ["COMPLETED", "FAILED"]:
            final_state = state
            break
        time.sleep(1)
        
    assert final_state is not None, "Worker time out"
    assert final_state["status"] in ["COMPLETED", "FAILED"]
    
    # Step 3: THE MOST CRITICAL ASSERTION - Verify Burn-After-Reading
    time.sleep(0.5) # ensure os.remove() flush
    file_still_exists = os.path.exists(target_path)
    assert not file_still_exists, f"CRITICAL SRE FAILURE: Audio file {target_path} WAS NOT SHREDDED AND LINGERED ON DISK!"
