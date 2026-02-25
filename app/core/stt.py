import multiprocessing
import multiprocessing.connection
import os
import time
from typing import Optional, Dict, Any

def _stt_worker(audio_path: str, model_size: str, child_conn: multiprocessing.connection.Connection):
    """
    Subprocess execution context for Faster-Whisper.
    Imports are isolated here to ensure all large objects belong solely to the child process memory space.
    If this process is killed via OOM by the kernel, the main process remains completely unaware and unharmed.
    """
    try:
        from faster_whisper import WhisperModel
        
        try:
            model = WhisperModel(model_size, device="auto", compute_type="default")
            initial_prompt = "Hello, this is a standard medical transcription. Please use proper capitalization and punctuation."
            segments, info = model.transcribe(
                audio_path, 
                beam_size=5,
                initial_prompt=initial_prompt
            )
            # Exhaust generator
            text = " ".join([seg.text.strip() for seg in segments]).strip()
        except Exception as e:
            if "libcublas" in str(e) or "cudnn" in str(e) or "cublas" in str(e).lower():
                # fallback to CPU if missing libcublas or other CUDA/GPU dependencies
                model = WhisperModel(model_size, device="cpu", compute_type="default")
                initial_prompt = "Hello, this is a standard medical transcription. Please use proper capitalization and punctuation."
                segments, info = model.transcribe(
                    audio_path, 
                    beam_size=5,
                    initial_prompt=initial_prompt
                )
                text = " ".join([seg.text.strip() for seg in segments]).strip()
            else:
                raise e
        
        child_conn.send({"status": "success", "text": text})
    except Exception as e:
        # Catch normal Python exceptions and return them gracefully
        child_conn.send({"status": "error", "error": str(e)})
    finally:
        child_conn.close()

def run_stt_isolated(audio_path: str, model_size: str = "base.en", timeout: int = 300) -> str:
    """
    Runs the Speech-to-Text inference in an isolated process.
    If an Out-Of-Memory (OOM) error occurs, the child process is killed, and an exception is raised in the parent process.
    
    Args:
        audio_path (str): The absolute path to the audio file.
        model_size (str): The Whisper model size (default: "base.en").
        timeout (int): The maximum duration (in seconds) to allow the STT job to run.
        
    Returns:
        str: Transcribed text.
        
    Raises:
        MemoryError: If the internal process exits with a non-zero exit code due to a system kill (e.g., OOM).
        TimeoutError: If the process takes longer than the timeout period.
        RuntimeError: If Faster-Whisper inherently fails.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    parent_conn, child_conn = multiprocessing.Pipe()
    
    # Must use 'spawn' to guarantee a fresh memory snapshot instead of 'fork' (which duplicates the parent's memory usage).
    ctx = multiprocessing.get_context('spawn')
    p = ctx.Process(target=_stt_worker, args=(audio_path, model_size, child_conn))
    
    p.start()
    
    start_time = time.time()
    result: Optional[Dict[str, Any]] = None
    
    # Wait loop
    while p.is_alive():
        # Check timeout
        if time.time() - start_time > timeout:
            p.terminate()
            p.join()
            raise TimeoutError(f"STT Process timed out after {timeout} seconds")
            
        # Check if data is available in the pipe (non-blocking for 0.1s)
        if parent_conn.poll(0.1):
            try:
                result = parent_conn.recv()
                break
            except EOFError:
                break
            
    # Wait for the process to actually terminate
    p.join()

    # If the process was killed violently by the kernel (e.g., SIGKILL due to OOM), the exitcode will be negative (e.g., -9)
    if p.exitcode is not None and p.exitcode != 0:
        raise MemoryError(f"STT Process killed violently (possible OOM or Segmentation Fault). Exit code: {p.exitcode}")

    if result is None:
         raise RuntimeError("Process finished but no result was returned via pipe.")
         
    if result.get("status") == "error":
        raise RuntimeError(f"STT Internal Error: {result.get('error')}")
        
    return result.get("text", "")
