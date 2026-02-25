from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Session, select
from database import engine, create_db_and_tables, TranscriptionTask

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
