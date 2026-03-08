import sqlite3
from typing import Optional
from enum import Enum
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, create_engine
from sqlalchemy import event
import os

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    TRANSCRIBING = "TRANSCRIBING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str

class TranscriptionTask(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Metadata
    filename: Optional[str] = None
    language: str = Field(default="auto")
    
    # Store the actual results
    transcript: Optional[str] = None
    soap_note: Optional[str] = None
    error_message: Optional[str] = None
    
    # Phase 3 Security: Zero-Trust mapping
    owner_id: int = Field(foreign_key="user.id", index=True)

# SRE Note: For a local appliance storing PII, we use a local SQLite file.
# The critical SRE aspect here is the WAL (Write-Ahead Logging) mode.
# Read from DB_PATH env variable for Docker volume mapping, default to local directory.
sqlite_file_name = os.getenv("DB_PATH", "ptclinvoice_sre.db")
sqlite_url = f"sqlite:///{sqlite_file_name}"

# By default, SQLite blocks concurrent writes. We must configure timeout and WAL
connect_args = {"check_same_thread": False, "timeout": 15}
engine = create_engine(sqlite_url, echo=False, connect_args=connect_args)

# Force WAL mode upon any new connection
@event.listens_for(engine, "connect")
def pragma_on_connect(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA cache_size=-64000;") # 64MB cache
        cursor.close()

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
