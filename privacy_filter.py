from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

class ClinicalPrivacyFilter:
    def __init__(self):
        """
        Phase 1.3: Local Privacy Redaction Layer.
        Ensures that Personal Identifiable Information (PII) is structurally blocked from
        leaving the local hardware before sending the transcript to the DeepSeek cloud.
        """
        try:
            # We initialize with the lightweight SpaCy model en_core_web_sm
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
        except OSError as e:
            raise RuntimeError(
                "Failed to initialize Presidio. Did you install language models? "
                "Run: python -m spacy download en_core_web_sm"
            ) from e
            
        # We explicitly target the most sensitive medical identifiers
        self.target_entities = [
            "PERSON", 
            "PHONE_NUMBER", 
            "EMAIL_ADDRESS", 
            "US_SSN",
            "LOCATION",
            "CREDIT_CARD"
        ]

    def mask_pii(self, transcript: str) -> str:
        """
        Scans and redacts PII from the raw transcription.
        All detected entities are irreversibly replaced with [REDACTED].
        
        Args:
            transcript (str): Raw STT text.
            
        Returns:
            str: Privacy-hardened transcript safe for cloud API consumption.
        """
        if not transcript.strip():
            return transcript

        # 1. Analyze the text for specific PII entities
        results = self.analyzer.analyze(
            text=transcript,
            entities=self.target_entities,
            language="en"
        )
        
        # 2. Anonymize the detected entities with a static mask
        anonymized_result = self.anonymizer.anonymize(
            text=transcript,
            analyzer_results=results,
            operators={"DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"})}
        )
        
        return anonymized_result.text
