import pytest
import json
from unittest.mock import patch, MagicMock

from stt_core import run_stt_isolated
from privacy_filter import ClinicalPrivacyFilter
from deepseek_adapter import DeepSeekClinicalAdapter

AUDIO_STANDARD = "tests/fixtures/standard_accent.mp3"

MOCK_DEEPSEEK_RESPONSE_JSON = json.dumps({
    "dialogue": "[Patient]: My name is [REDACTED]. I have abdominal pain.\n[Doctor]: Let's run some tests.",
    "soap": {
        "subjective": "Patient [REDACTED] reports abdominal pain.",
        "objective": "Pending tests.",
        "assessment": "Abdominal pain of unknown etiology.",
        "plan": "Run diagnostic panels."
    }
})

@pytest.fixture(scope="module")
def privacy_filter():
    """Load SpaCy en_core_web_sm once for the integration module."""
    return ClinicalPrivacyFilter()

@pytest.fixture
def mock_openai_client():
    """Mock the external cloud API to prevent bandwidth and token usage during CI/CD integration testing."""
    with patch("deepseek_adapter.OpenAI") as mock_openai:
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        
        mock_choice.message.content = MOCK_DEEPSEEK_RESPONSE_JSON
        mock_response.choices = [mock_choice]
        
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client_instance
        yield mock_openai

def test_phase_1_end_to_end_pipeline(privacy_filter, mock_openai_client):
    """
    E2E Integration Test for Phase 1 Black-Box Prototype.
    Flow: Local STT (Faster-Whisper) -> Local NER (Presidio) -> Cloud LLM Adapter (DeepSeek)
    """
    
    # ---------------------------------------------------------
    # STEP 1: STT Engine (Audio to Text)
    # Perform actual inference on the generated test audio.
    # ---------------------------------------------------------
    raw_transcript = run_stt_isolated(AUDIO_STANDARD, model_size="tiny.en")
    
    assert isinstance(raw_transcript, str), "STT pipeline failed to output string."
    assert len(raw_transcript) > 10, "STT transcript too short or silent."
    assert "abdominal pain" in raw_transcript.lower(), "STT failed to transcribe crucial medical context."
    
    # We deliberately inject highly sensitive PII into the STT output to stress-test the pipeline link
    transcript_with_pii = raw_transcript + " Oh by the way, my name is Robert Oppenheimer and my SSN is 999-88-7777."
    
    # ---------------------------------------------------------
    # STEP 2: Privacy Filter (Local Anonymization)
    # Ensure STT output doesn't leak directly to the cloud.
    # ---------------------------------------------------------
    safe_transcript = privacy_filter.mask_pii(transcript_with_pii)
    
    # Assert STT core logic was preserved
    assert "abdominal pain" in safe_transcript.lower(), "Privacy filter destroyed non-PII medical context."
    
    # Assert PII was destroyed
    assert "Robert" not in safe_transcript, "PII Leak: First Name breached!"
    assert "Oppenheimer" not in safe_transcript, "PII Leak: Last Name breached!"
    assert "999-88-7777" not in safe_transcript, "PII Leak: SSN breached!"
    assert "[REDACTED]" in safe_transcript, "Privacy filter failed to insert security mask."

    # ---------------------------------------------------------
    # STEP 3: DeepSeek Adapter (Structured SOAP Extraction)
    # Pass the sanitized text to the LLM for dialogue formatting.
    # ---------------------------------------------------------
    adapter = DeepSeekClinicalAdapter(api_key="TEST_DUMMY_KEY")
    final_soap_note = adapter.generate_soap_note(safe_transcript)
    
    # Assert Dict Structure
    assert "dialogue" in final_soap_note, "DeepSeek missed dialogue key."
    assert "soap" in final_soap_note, "DeepSeek missed soap root key."
    
    # Assert SOAP parsing
    soap = final_soap_note["soap"]
    assert "subjective" in soap
    assert "objective" in soap
    assert "assessment" in soap
    assert "plan" in soap
    
    # Assert that the DeepSeek LLM was fed and returned the masked text, proving the integrity of the chain
    assert "[REDACTED]" in final_soap_note["dialogue"], "LLM pipeline lost the REDACTED mask constraint."
    assert "[REDACTED]" in final_soap_note["soap"]["subjective"], "LLM subjective text lost privacy constraints."
