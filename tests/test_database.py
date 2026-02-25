import asyncio
import uuid
import os
import pytest
from sqlmodel import Session, select
from app.database import create_db_and_tables, TranscriptionTask, TaskStatus, User, SQLModel, sqlite_file_name as app_sqlite_file_name
from sqlmodel import create_engine, Session, select
from sqlalchemy import event
import sqlite3

sqlite_file_name = "test_concurrent.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
connect_args = {"check_same_thread": False, "timeout": 15}
engine = create_engine(sqlite_url, echo=False, connect_args=connect_args)

@event.listens_for(engine, "connect")
def pragma_on_connect(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA cache_size=-64000;")
        cursor.close()


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    # SRE Ensure clean slate
    if os.path.exists(sqlite_file_name):
        os.remove(sqlite_file_name)
    create_db_and_tables() # Create default one if needed by other tests
    SQLModel.metadata.create_all(engine) # Create tables on the isolated engine
    with Session(engine) as session:
        user = User(username="test_db_user", hashed_password="hashed_password")
        session.add(user)
        session.commit()
    yield
    # Teardown
    if os.path.exists(sqlite_file_name):
        os.remove(sqlite_file_name)

async def worker_update_task(task_id: str):
    """
    Simulates a background worker violently attempting to update the DB status
    """
    # Simulate a micro-delay as if it's doing network I/O
    await asyncio.sleep(0.01)
    
    # This block must not throw `OperationalError: database is locked`
    # if WAL is correctly configured.
    with Session(engine) as session:
        # Step 1: Create
        user = session.exec(select(User).where(User.username == "test_db_user")).first()
        task = TranscriptionTask(id=task_id, status=TaskStatus.PENDING, owner_id=user.id)
        session.add(task)
        session.commit()
        
        # Step 2: Read & Update
        task = session.get(TranscriptionTask, task_id)
        task.status = TaskStatus.TRANSCRIBING
        session.add(task)
        session.commit()

        # Step 3: Final Update
        task = session.get(TranscriptionTask, task_id)
        task.status = TaskStatus.COMPLETED
        session.add(task)
        session.commit()

@pytest.mark.asyncio
async def test_concurrent_sqlite_wal_resilience():
    """
    SRE Chaos Test: Can the system survive 100 simultaneous concurrent writes
    without database locking up? This proves WAL mode is strictly active.
    """
    num_concurrent_tasks = 100
    task_ids = [str(uuid.uuid4()) for _ in range(num_concurrent_tasks)]
    
    # Fire all 100 tasks simultaneously
    tasks = [worker_update_task(tid) for tid in task_ids]
    
    # If WAL is not set, this asyncio.gather will explode with OperationalError.
    await asyncio.gather(*tasks)
    
    # Verify all 100 finished properly.
    with Session(engine) as session:
        statement = select(TranscriptionTask).where(TranscriptionTask.status == TaskStatus.COMPLETED)
        completed_tasks = session.exec(statement).all()
        assert len(completed_tasks) == num_concurrent_tasks, "Not all tasks reached COMPLETED status. Did DB lock?"
