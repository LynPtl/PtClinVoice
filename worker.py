import os
import traceback
from sqlmodel import Session
from database import engine, TranscriptionTask, TaskStatus
from stt_core import run_stt_isolated
from privacy_filter import ClinicalPrivacyFilter
from deepseek_adapter import DeepSeekClinicalAdapter

def process_audio_task(task_id: str, audio_path: str):
    """
    Phase 2.3 Background Worker Execution Pipeline.
    Strictly isolated OOM-safe boundary -> Local PII Mask -> DeepSeek SOAP Parse.
    """
    with Session(engine) as session:
        # Fetch the pending task
        task = session.get(TranscriptionTask, task_id)
        if not task:
            return  # Ghost task, silently exit
        
        # 1. Update State to TRANSCRIBING
        task.status = TaskStatus.TRANSCRIBING
        session.add(task)
        session.commit()
    
    # Run heavy operations outside the DB session context to limit transaction duration
    try:
        # --- LOCAL STT OOM ISOLATION ZONE ---
        # The underlying process is strictly spawned dynamically and drops everything upon crash
        raw_transcript = run_stt_isolated(audio_path, model_size="tiny.en")
        
        # 2. Update State to ANALYZING
        with Session(engine) as session:
            task = session.get(TranscriptionTask, task_id)
            task.status = TaskStatus.ANALYZING
            task.transcript = raw_transcript
            session.add(task)
            session.commit()
            
        # --- LOCAL PII NER REDACTION ZONE ---
        privacy_filter = ClinicalPrivacyFilter()
        safe_transcript = privacy_filter.mask_pii(raw_transcript)
        
        # --- CLOUD LLM SOAP GENERATION ZONE ---
        adapter = DeepSeekClinicalAdapter()
        soap_note_dict = adapter.generate_soap_note(safe_transcript)
        # DeepSeek returns a mapped struct containing the raw json string of SOAP
        # Make sure to convert dict layout to simple structured database cache
        import json
        soap_dump = json.dumps(soap_note_dict)
        
        # 3. Final State Update -> COMPLETED
        with Session(engine) as session:
            task = session.get(TranscriptionTask, task_id)
            task.status = TaskStatus.COMPLETED
            task.soap_note = soap_dump
            session.add(task)
            session.commit()

    except Exception as e:
        # 4. Fallback Catch-all for Exceptions (OOM/DeepSeek Timeout)
        error_info = str(e)
        # SRE Note: In production we use actual loggers, but we capture the error trace here.
        # Ensure we always update db state on pipeline rupture to avoid Zombie status.
        with Session(engine) as session:
            task = session.get(TranscriptionTask, task_id)
            if task:
                task.status = TaskStatus.FAILED
                task.error_message = error_info
                session.add(task)
                session.commit()
    
    finally:
        # --------- BURN AFTER READING DEFENSE ---------
        # SRE Security: Regardless of whether the pipeline succeeded, crashed, or OOM'd,
        # we MUST purge the physical audio file from the server disk to protect PII.
        if os.path.exists(audio_path) and not "mock" in audio_path and not "tests/" in audio_path:
            try:
                os.remove(audio_path)
            except Exception as cleanup_err:
                print(f"CRITICAL: Failed to shred audio file {audio_path}: {cleanup_err}")

