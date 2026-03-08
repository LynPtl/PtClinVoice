import os
import traceback
from sqlmodel import Session
from app.database import engine, TranscriptionTask, TaskStatus
from app.core.stt import run_stt_isolated
from app.core.privacy import ClinicalPrivacyFilter
from app.core.deepseek import DeepSeekClinicalAdapter
import subprocess
import tempfile

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
        
        # Read metadata for Translation pipeline
        language = task.language or "auto"
        # Option A strategy: Always translate if Arabic or Auto, otherwise transcribe
        whisper_task = "translate" if language in ["ar", "auto"] else "transcribe"
        whisper_language = language if language != "auto" else None
        
        session.add(task)
        session.commit()
    
    # Run heavy operations outside the DB session context to limit transaction duration
    enhanced_audio_path = audio_path
    try:
        # --- AUDIO PREPROCESSING (NOISE REDUCTION) ---
        # SRE Note: Apply Fast Fourier Transform Denoise (afftdn) and Volume Normalization (loudnorm)
        # before passing to Whisper. This significantly improves RTF and accuracy on noisy clinical recordings.
        try:
            temp_clean_fd, temp_clean_path = tempfile.mkstemp(suffix=".wav")
            os.close(temp_clean_fd)
            subprocess.run([
                "ffmpeg", "-y", "-i", audio_path,
                "-af", "afftdn=nf=-25,loudnorm=I=-16:TP=-1.5:LRA=11",
                "-ar", "16000", "-ac", "1",
                temp_clean_path
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            enhanced_audio_path = temp_clean_path
        except Exception as ffmpeg_err:
            print(f"Warning: FFmpeg noise reduction failed, falling back to raw audio: {ffmpeg_err}")
            enhanced_audio_path = audio_path

        # --- LOCAL STT OOM ISOLATION ZONE ---
        # The underlying process is strictly spawned dynamically and drops everything upon crash
        raw_transcript = run_stt_isolated(
            enhanced_audio_path, 
            model_size="small",
            whisper_task=whisper_task,
            whisper_language=whisper_language
        )
        
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
        for path_to_clean in [audio_path, enhanced_audio_path]:
            if os.path.exists(path_to_clean) and not "mock" in path_to_clean and not "tests/" in path_to_clean:
                try:
                    os.remove(path_to_clean)
                except Exception as cleanup_err:
                    print(f"CRITICAL: Failed to shred audio file {path_to_clean}: {cleanup_err}")

