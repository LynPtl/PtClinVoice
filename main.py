from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
import os
import shutil
from pydantic import BaseModel
import uuid
from sqlmodel import Session, select
from database import engine, create_db_and_tables, TranscriptionTask, TaskStatus, User
from worker import process_audio_task
from auth import get_password_hash, verify_password, create_access_token, get_current_user

app = FastAPI(
    title="PtClinVoice Core API",
    description="SRE-grade Local Transcription & Privacy Filter Backend",
    version="3.0.0",
)

# SRE Note: Fallback to local ./uploads if the Docker-mounted ./data directory
# is owned by root and we are running tests in a local user environment.
UPLOAD_DIR = "data/uploads"
try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
except PermissionError:
    UPLOAD_DIR = "uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.on_event("startup")
def on_startup():
    # SRE Note: In a true multi-worker production environment, migrations 
    # should be handled via Alembic prior to app startup. For this single-node
    # SQLite appliance, auto-creation is acceptable.
    create_db_and_tables()

@app.get("/health")
def health_check():
    """
    Standard Liveness Probe
    """
    return {"status": "ok", "service": "PtClinVoice API"}

@app.post("/api/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Phase 3: Zero-Trust JWT Issuer
    """
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == form_data.username)).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        access_token = create_access_token(data={"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer"}

@app.get("/tasks/{task_id}", response_model=TranscriptionTask)
def get_task_status(task_id: str, current_user: User = Depends(get_current_user)):
    """
    Retrieve task status. Protected by JWT.
    Users can only retrieve tasks they own.
    """
    with Session(engine) as session:
        task = session.get(TranscriptionTask, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        # Privilege Separation
        if task.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this task")
            
        return task

class MockTranscribeRequest(BaseModel):
    audio_path: str

@app.post("/api/v1/transcribe/mock")
def create_mock_transcription(
    req: MockTranscribeRequest, 
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Phase 2.3/3.1 Mock Transcribe. Now JWT Protected.
    """
    task_id = str(uuid.uuid4())
    
    with Session(engine) as session:
        new_task = TranscriptionTask(
            id=task_id, 
            status=TaskStatus.PENDING,
            owner_id=current_user.id  # Bind task to user
        )
        session.add(new_task)
        session.commit()
        
    background_tasks.add_task(process_audio_task, task_id, req.audio_path)
    return {"task_id": task_id, "status": TaskStatus.PENDING}
    
@app.post("/api/upload")
def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Phase 3: Secure Audio Upload with Burn-After-Reading lifecycle.
    """
    if not file.filename.endswith(('.wav', '.mp3', '.m4a')):
        raise HTTPException(status_code=400, detail="Invalid audio format")
        
    task_id = str(uuid.uuid4())
    # Generate unique secure filename to prevent traversal attacks
    secure_filename = f"{task_id}_{file.filename.replace('/', '_')}"
    file_path = os.path.join(UPLOAD_DIR, secure_filename)
    
    # 1. Spool to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 2. Register State
    with Session(engine) as session:
        new_task = TranscriptionTask(
            id=task_id, 
            status=TaskStatus.PENDING,
            owner_id=current_user.id
        )
        session.add(new_task)
        session.commit()
        
    # 3. Offload via Worker
    background_tasks.add_task(process_audio_task, task_id, file_path)
    
    return {"task_id": task_id, "status": TaskStatus.PENDING, "message": "File received. Processing in background."}
