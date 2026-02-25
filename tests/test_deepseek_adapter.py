import os
import json
import pytest
from unittest.mock import patch, MagicMock
from app.core.deepseek import DeepSeekClinicalAdapter

# Sample transcript without PII (Phase 1.3 will redact the names before this stage)
MOCK_TRANSCRIPT = (
    "Good morning. I am the doctor. Are you the [REDACTED] from [REDACTED]? "
    "Yes, doctor. I have been taking [REDACTED] and [REDACTED], but my blood pressure is still high."
)

MOCK_DEEPSEEK_RESPONSE_JSON = json.dumps({
    "dialogue": "[Doctor]: Good morning. I am the doctor. Are you the [REDACTED] from [REDACTED]?\n[Patient]: Yes, doctor. I have been taking [REDACTED] and [REDACTED], but my blood pressure is still high.",
    "soap": {
        "subjective": "Patient reports that blood pressure remains high despite taking [REDACTED] and [REDACTED].",
        "objective": "No specific objective vitals recorded in this brief snippet.",
        "assessment": "Uncontrolled hypertension.",
        "plan": "Review current medication efficacy and adjust dosage as needed."
    }
})

@pytest.fixture
def mock_openai_client():
    with patch("app.core.deepseek.OpenAI") as mock_openai:
        # Construct the deeply nested mock chain: client.chat.completions.create().choices[0].message.content
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        
        mock_choice.message.content = MOCK_DEEPSEEK_RESPONSE_JSON
        mock_response.choices = [mock_choice]
        
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client_instance
        yield mock_openai

def test_deepseek_adapter_json_structure(mock_openai_client):
    """
    1.2 Require: 设计 Prompt 模板测试基于语义的角色分离与 SOAP 生成。
    验证返回的 JSON / Markdown 解析出 SOAP 格式的稳定性。
    """
    adapter = DeepSeekClinicalAdapter(api_key="TEST_KEY")
    result = adapter.generate_soap_note(MOCK_TRANSCRIPT)
    
    # Assert JSON was properly parsed back into a dictionary
    assert isinstance(result, dict)
    
    # Assert root keys
    assert "dialogue" in result
    assert "soap" in result
    
    # Assert SOAP sub-keys
    soap = result["soap"]
    assert "subjective" in soap
    assert "objective" in soap
    assert "assessment" in soap
    assert "plan" in soap
    
    # Assert the mock data flowed correctly
    assert "[Doctor]" in result["dialogue"]
    assert "[Patient]" in result["dialogue"]
    assert "hypertension" in soap["assessment"]

def test_deepseek_adapter_empty_transcript():
    """Edge case: Providing an empty transcript should raise ValueError early."""
    adapter = DeepSeekClinicalAdapter(api_key="TEST_KEY")
    with pytest.raises(ValueError, match="Transcript cannot be empty"):
        adapter.generate_soap_note("   \n  ")
