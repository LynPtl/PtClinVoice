from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status, UploadFile, File, Query, Form
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from fastapi.security import OAuth2PasswordRequestForm
import os
import shutil
from pydantic import BaseModel
import uuid
import json
import asyncio
from sqlmodel import Session, select
from app.database import engine, create_db_and_tables, TranscriptionTask, TaskStatus, User
from app.worker import process_audio_task
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user, SECRET_KEY, ALGORITHM
import jwt

@asynccontextmanager
async def lifespan(app: FastAPI):
    # SRE Note: In a true multi-worker production environment, migrations 
    # should be handled via Alembic prior to app startup. For this single-node
    # SQLite appliance, auto-creation is acceptable.
    create_db_and_tables()
    yield

app = FastAPI(
    title="PtClinVoice Core API",
    description="SRE-grade Local Transcription & Privacy Filter Backend",
    version="3.0.0",
    lifespan=lifespan,
)

# SRE Note: Fallback to local ./uploads if the Docker-mounted ./data directory
# is owned by root and we are running tests in a local user environment.
UPLOAD_DIR = "data/uploads"
try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    test_file = os.path.join(UPLOAD_DIR, ".test_write")
    with open(test_file, "w") as f:
        f.write("test")
    os.remove(test_file)
except (PermissionError, OSError):
    UPLOAD_DIR = "uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)



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

class RegisterRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest):
    """
    Phase 5.2: Open User Self-Registration.
    """
    if not req.username or len(req.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if not req.password or len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == req.username)).first()
        if existing:
            raise HTTPException(status_code=409, detail="Username already exists.")
        
        new_user = User(username=req.username, hashed_password=get_password_hash(req.password))
        session.add(new_user)
        session.commit()
    
    return {"message": "Registration successful. Please log in."}

@app.get("/api/tasks/{task_id}", response_model=TranscriptionTask)
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

@app.delete("/api/tasks/{task_id}", status_code=status.HTTP_200_OK)
def delete_task(task_id: str, current_user: User = Depends(get_current_user)):
    """
    Phase 5.2: Hard-delete a task. Only the task owner can delete.
    """
    with Session(engine) as session:
        task = session.get(TranscriptionTask, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this task")
        session.delete(task)
        session.commit()
    return {"message": "Task deleted successfully."}

@app.get("/api/tasks")
def list_tasks(current_user: User = Depends(get_current_user)):
    """
    List all tasks owned by the current user.
    """
    with Session(engine) as session:
        # Order by created_at DESC ideally, assuming default sqlite ROWID order for now
        tasks = session.exec(select(TranscriptionTask).where(TranscriptionTask.owner_id == current_user.id)).all()
        return tasks

@app.get("/api/stream/{task_id}")
async def stream_task_status(task_id: str, token: str = Query(...)):
    """
    Phase 4.4: SSE Endpoint for Real-time Task Updates.
    Since EventSource cannot send Authorization headers, we use a query param token.
    """
    credentials_exception = HTTPException(status_code=401, detail="Invalid token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username: raise credentials_exception
    except Exception:
        raise credentials_exception
        
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user: raise credentials_exception
        task = session.get(TranscriptionTask, task_id)
        if not task or task.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Task not found or forbidden")

    async def event_generator():
        last_status = None
        while True:
            with Session(engine) as session:
                task = session.get(TranscriptionTask, task_id)
            if not task:
                break
            if task.status != last_status:
                last_status = task.status
                yield f"data: {json.dumps({'task_id': task.id, 'status': task.status})}\n\n"
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                break
            await asyncio.sleep(1) # SSE poll interval

    return StreamingResponse(event_generator(), media_type="text/event-stream")

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
            owner_id=current_user.id,
            filename=os.path.basename(req.audio_path)
        )
        session.add(new_task)
        session.commit()
        
    background_tasks.add_task(process_audio_task, task_id, req.audio_path)
    return {"task_id": task_id, "status": TaskStatus.PENDING}
    
@app.post("/api/upload")
def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form("auto"),
    patient_name: str = Form(""),
    current_user: User = Depends(get_current_user)
):
    """
    Phase 3: Secure Audio Upload with Burn-After-Reading lifecycle.
    """
    if not file.filename.endswith(('.wav', '.mp3', '.m4a', '.webm', '.ogg')):
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
            owner_id=current_user.id,
            filename=file.filename,
            patient_name=patient_name if patient_name else None,
            language=language
        )
        session.add(new_task)
        session.commit()
        
    # 3. Offload via Worker
    background_tasks.add_task(process_audio_task, task_id, file_path)
    
    return {"task_id": task_id, "status": TaskStatus.PENDING, "message": "File received. Processing in background."}
