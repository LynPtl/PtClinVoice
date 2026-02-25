import pytest
from app.core.privacy import ClinicalPrivacyFilter

@pytest.fixture(scope="module")
def privacy_filter():
    """
    Intialize the filter once for the test module since loading SpaCy models
    takes measurable time (a few hundred milliseconds).
    """
    return ClinicalPrivacyFilter()

def test_privacy_filter_person_redaction(privacy_filter):
    """
    1.3 Require: 输入包含 PII 假名组合的文本，断言被准确标记为 [REDACTED]。
    """
    raw_text = "Hello, my name is Emily Chen and my doctor is Dr. James Wilson."
    safe_text = privacy_filter.mask_pii(raw_text)
    
    assert "Emily" not in safe_text, "Patient first name leaked!"
    assert "Chen" not in safe_text, "Patient last name leaked!"
    assert "James" not in safe_text, "Doctor first name leaked!"
    assert "Wilson" not in safe_text, "Doctor last name leaked!"
    
    # Assert structural integrity 
    assert "[REDACTED]" in safe_text, "Entities were not replaced with the correct mask."

def test_privacy_filter_ssn_and_phone(privacy_filter):
    """
    Ensure critical identifiers like SSN and Phone Numbers are caught.
    """
    raw_text = "You can reach me at 555-019-8372. My SSN is 012-34-5678."
    safe_text = privacy_filter.mask_pii(raw_text)
    
    assert "555-019-8372" not in safe_text, "Phone number leaked!"
    assert "012-34-5678" not in safe_text, "SSN leaked!"
    assert safe_text.count("[REDACTED]") >= 2, "Failed to redact both identifiers."

def test_privacy_filter_empty_string(privacy_filter):
    """
    Edge case: Empty or whitespace-only strings should not crash the engine.
    """
    assert privacy_filter.mask_pii("") == ""
    assert privacy_filter.mask_pii("   ") == "   "
