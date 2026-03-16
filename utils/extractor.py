from google import genai
from utils.config import Config
from utils.utils import setup_logger
import json
import time

logger = setup_logger(__name__)

class PrescriptionExtractor:
    def __init__(self):
        if not Config.GOOGLE_API_KEY:
            logger.warning("Google API Key not found")
            self.client = None
        else:
            self.client = genai.Client(api_key=Config.GOOGLE_API_KEY)

    def extract_data(self, file_input):
        prompt = """
        You are an expert medical assistant. Analyze this prescription and extract the following information in JSON format.
        Focus strictly on the medicine details and instructions.

        {
            "date": "Date of prescription",
            "medicines": [
                {
                    "name": "Exact name of the tablet/medicine",
                    "dosage": "Strength of the medicine (e.g., 500mg, 10ml)",
                    "timing": {
                        "morning": "Number of tablets/dose in morning (e.g. '1', '1/2', '0')",
                        "afternoon": "Number of tablets/dose in afternoon (e.g. '1', '1/2', '0')",
                        "night": "Number of tablets/dose in night (e.g. '1', '1/2', '0')",
                        "food_timing": "Before meal / After meal / With food / Empty stomach"
                    },
                    "frequency": "Raw frequency string (e.g., 1-0-1)",
                    "duration": "For how many days the medicine should be taken (e.g. '5 days')",
                    "caution": "Warning string if doctor consultation is needed for this specific medicine (e.g. 'Antibiotic', 'Schedule H'), else empty string"
                }
            ],
            "requires_doctor_consultation": true,
            "consultation_reason": "Provide a brief reason if true, e.g., 'Antibiotics require full course completion', 'Scheduled H drug', or 'High dosage'. If false, null.",
            "notes": "Any special instructions"
        }
        If a field is missing, use "-". For timing, use "0" if not applicable. Return ONLY the JSON.
        """

        if not self.client:
            logger.error("Gemini client not initialized.")
            return None

        try:
            content = [prompt]

            if isinstance(file_input, str):
                if file_input.lower().endswith(".pdf"):
                    uploaded = self.client.files.upload(file=file_input)
                    while uploaded.state.name == "PROCESSING":
                        time.sleep(2)
                        uploaded = self.client.files.get(name=uploaded.name)
                    content.append(uploaded)
                else:
                    import PIL.Image
                    img = PIL.Image.open(file_input)
                    content.append(img)
            elif hasattr(file_input, 'read'):
                import PIL.Image
                img = PIL.Image.open(file_input)
                content.append(img)
            elif isinstance(file_input, list):
                content.extend(file_input)
            else:
                content.append(file_input)

            response = self.client.models.generate_content(
                model=Config.GEMINI_MODEL_NAME,
                contents=content
            )
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            return json.loads(text.strip())

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return None
