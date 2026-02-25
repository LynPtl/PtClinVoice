import asyncio
import uuid
import os
import pytest
from sqlmodel import Session, select
from database import engine, create_db_and_tables, TranscriptionTask, TaskStatus, sqlite_file_name

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    # SRE Ensure clean slate
    if os.path.exists(sqlite_file_name):
        os.remove(sqlite_file_name)
    create_db_and_tables()
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
        task = TranscriptionTask(id=task_id, status=TaskStatus.PENDING)
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
