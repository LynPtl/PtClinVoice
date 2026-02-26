import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
import os

from app.main import app
from app.database import engine, User, create_db_and_tables
from app.auth import get_password_hash

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    create_db_and_tables()
    with Session(engine) as session:
        # Create test user A
        user_a = User(username="dr_alice", hashed_password=get_password_hash("password123"))
        # Create test user B
        user_b = User(username="dr_bob", hashed_password=get_password_hash("password123"))
        
        # Clean existing test users if they exist
        existing = session.exec(select(User).where(User.username.in_(["dr_alice", "dr_bob"]))).all()
        for e in existing:
            session.delete(e)
        session.commit()
            
        session.add(user_a)
        session.add(user_b)
        session.commit()

def get_token(username, password):
    resp = client.post("/api/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]

def test_unauthorized_access_rejected():
    """Ensure endpoints reject requests without tokens"""
    resp = client.post("/api/v1/transcribe/mock", json={"audio_path": "test.mp3"})
    assert resp.status_code == 401

def test_jwt_auth_success():
    """Verify legitimate users can authenticate and dispatch tasks"""
    token = get_token("dr_alice", "password123")
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = client.post(
        "/api/v1/transcribe/mock", 
        json={"audio_path": "tests/fixtures/standard_accent.mp3"},
        headers=headers
    )
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]
    
    # Verify owner can fetch status
    status_resp = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert status_resp.status_code == 200

def test_horizontal_privilege_escalation_blocked():
    """Verify User B cannot access User A's task (403 Forbidden)"""
    # 1. User A creates task
    token_a = get_token("dr_alice", "password123")
    resp_a = client.post(
        "/api/v1/transcribe/mock", 
        json={"audio_path": "tests/fixtures/standard_accent.mp3"},
        headers={"Authorization": f"Bearer {token_a}"}
    )
    task_id = resp_a.json()["task_id"]
    
    # 2. User B tries to read it
    token_b = get_token("dr_bob", "password123")
    resp_b = client.get(
        f"/api/tasks/{task_id}", 
        headers={"Authorization": f"Bearer {token_b}"}
    )
    
    # 3. Assert blocked
    assert resp_b.status_code == 403
    assert "Not authorized" in resp_b.json()["detail"]
