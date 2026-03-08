import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.stt import run_stt_isolated

# Provide a sample Arabic audio file path if available, or just describe the test
def test_arabic_translation():
    print("This script is a placeholder to verify the integration of whisper_task='translate'.")
    print("In production/CI, we would pass a real Arabic medical audio file to `run_stt_isolated`")
    print("with whisper_task='translate' and whisper_language='ar'.")

    # Example:
    # try:
    #     result = run_stt_isolated(
    #         "tests/fixtures/sample_arabic.wav",
    #         model_size="tiny",
    #         whisper_task="translate",
    #         whisper_language="ar"
    #     )
    #     print("Translation Output:", result)
    #     assert "pain" in result.lower() or "medical" in result.lower()
    # except Exception as e:
    #     print(f"Translation test failed: {e}")

if __name__ == "__main__":
    test_arabic_translation()
