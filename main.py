from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uuid
from sqlmodel import Session, select
from database import engine, create_db_and_tables, TranscriptionTask, TaskStatus
from worker import process_audio_task

app = FastAPI(
    title="PtClinVoice Core API",
    description="SRE-grade Local Transcription & Privacy Filter Backend",
    version="2.1.0",
)

@app.on_event("startup")
def on_startup():
    # SRE Note: In a true multi-worker production environment, migrations 
    # should be handled via Alembic prior to app startup. For this single-node
    # SQLite appliance, auto-creation is acceptable.
    create_db_and_tables()

@app.get("/health")
def health_check():
    """
    Standard Liveness Probe for Kubernetes / Docker Swarm
    """
    return {"status": "ok", "service": "PtClinVoice API"}

@app.get("/tasks/{task_id}", response_model=TranscriptionTask)
def get_task_status(task_id: str):
    """
    Retrieve the status of a specific transcription task.
    """
    with Session(engine) as session:
        task = session.get(TranscriptionTask, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

class MockTranscribeRequest(BaseModel):
    audio_path: str

@app.post("/api/v1/transcribe/mock")
def create_mock_transcription(req: MockTranscribeRequest, background_tasks: BackgroundTasks):
    """
    Phase 2.3: Ingest a mock file path and dispatch to the background STT/NLP worker pool.
    Returns immediately with a UUID task ID for polling.
    """
    task_id = str(uuid.uuid4())
    
    # 1. State Machine Initialization
    with Session(engine) as session:
        new_task = TranscriptionTask(id=task_id, status=TaskStatus.PENDING)
        session.add(new_task)
        session.commit()
        
    # 2. Dispatch the actual heavy-lifting to the isolated worker queue
    background_tasks.add_task(process_audio_task, task_id, req.audio_path)
    
    # 3. Non-blocking return
    return {"task_id": task_id, "status": TaskStatus.PENDING}
