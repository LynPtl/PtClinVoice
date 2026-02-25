import os
import pytest
import numpy as np
import wave
from app.core.stt import run_stt_isolated

# To prevent multiprocessing pickle error, keep top-level
def malicious_oom_worker(audio_path, model_size, conn):
    import signal
    import os
    # Mock OOM: Kill itself with SIGKILL immediately (exit code -9)
    os.kill(os.getpid(), signal.SIGKILL)

# Test paths
AUDIO_STANDARD = "tests/fixtures/standard_accent.mp3"
AUDIO_NON_STANDARD = "tests/fixtures/heavy_accent.mp3"

def test_stt_standard_audio_handling():
    """
    1.1 Require: 输入标准和非标准口音的音频文件，Assert 识别文字是否合规生成。
    If the text string forms, we check whether "initial_prompt" worked correctly (capitalization and punctuation).
    We assert the real content from standard_accent test file.
    """
    try:
        # base.en for testing specific clinical words accurately
        text = run_stt_isolated(AUDIO_STANDARD, model_size="base.en")
        
        # We assert it returns a valid string.
        assert isinstance(text, str), "The process must return a valid string."
        
        # Assert content and prompt conditioning
        assert text[0].isupper(), f"Returned text should be capitalized. Got: {text}"
        assert text[-1] in [".", "?", "!"], f"Returned text should have punct. Got: {text}"
        assert "patient" in text.lower(), "Should detect 'patient'"
        assert "abdominal pain" in text.lower(), "Should accurately transcribe 'abdominal pain'"
            
    except RuntimeError as e:
         pytest.fail(f"Faster-whisper engine failed: {e}")

def test_stt_oom_isolation_survival():
    """
    1.1 & Core constraints Require: 
    针对 Whisper 极高的内存消耗，实施进程隔离，如果发生 OOM，必须确保只 kill 子进程，主进程绝对不能崩溃。
    Here we mock the isolation worker to die violently (SIGKILL) pretending it ran out of memory.
    """
    import multiprocessing
    from app.core import stt

    original_worker = stt._stt_worker
    stt._stt_worker = malicious_oom_worker

    try:
        with pytest.raises(MemoryError, match="STT Process killed violently"):
            stt.run_stt_isolated(AUDIO_STANDARD, model_size="tiny.en")
            
        # The fact we reach here after raising MemoryError proves the main thread survived.
        assert True
    finally:
        stt._stt_worker = original_worker
