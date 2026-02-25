import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class DeepSeekClinicalAdapter:
    def __init__(self, api_key: str = None):
        """
        Initializes the OpenAI client pointing to DeepSeek's base URL.
        As per the architecture constraints, all complex NLP relies on the high-cost-performance DeepSeek API.
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        
        # DeepSeek implements an OpenAI-compatible API
        self.client = OpenAI(
            api_key=self.api_key or "DUMMY_KEY_FOR_TESTS", 
            base_url="https://api.deepseek.com"
        )
        # Using deepseek-chat for parsing efficiency, can be changed to deepseek-reasoner for harder cases
        self.model = "deepseek-chat"
        
    def generate_soap_note(self, transcript: str) -> dict:
        """
        Phase 1.2: Takes a privacy-hardened raw STT transcript, separates the speaker roles by semantic analysis, 
        and extracts clinical entities into a structured SOAP note JSON format.
        
        Args:
            transcript (str): The raw text (e.g. from Whisper), strictly after local PII redaction.
            
        Returns:
            dict: Parsed JSON with keys "dialogue" and "soap".
        """
        
        if not transcript.strip():
             raise ValueError("Transcript cannot be empty.")
             
        prompt = (
            "You are a highly skilled SRE and Clinical AI Assistant. "
            "You are provided with a continuous, undifferentiated raw transcript from a medical consultation. "
            "Your task is to:\n"
            "1. Diarize the text by separating the roles logically (e.g., [Doctor]: <text> \\n [Patient]: <text>).\n"
            "2. Extract and format the information into a strict SOAP note format (Subjective, Objective, Assessment, Plan).\n\n"
            "IMPORTANT: Your output MUST be strictly valid JSON without markdown code blocks, using exactly this structure:\n"
            "{\n"
            "  \"dialogue\": \"string with reconstructed speaker roles\",\n"
            "  \"soap\": {\n"
            "    \"subjective\": \"string\",\n"
            "    \"objective\": \"string\",\n"
            "    \"assessment\": \"string\",\n"
            "    \"plan\": \"string\"\n"
            "  }\n"
            "}\n\n"
            f"Transcript:\n{transcript}"
        )

        # deepseek-chat supports JSON response formatting natively
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a specialized medical documentation system. Always respond in strictly formatted JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,  # Low temperature for highly deterministic clinical text
            max_tokens=2048
        )
        
        raw_output = response.choices[0].message.content
        
        try:
            return json.loads(raw_output)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse DeepSeek response as JSON: {raw_output}") from e
