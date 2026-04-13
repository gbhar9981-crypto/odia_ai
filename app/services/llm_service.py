import os
import httpx
import json
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Using the user's specifically requested model: gemini-2.5-flash
GEMINI_MODEL = "gemini-2.5-flash" 

class LLMService:
    def __init__(self):
        # The system prompt enforcing the "Odia by Default" rule
        self.system_instruction = '''
You are "Odia AI", the intelligent AI assistant in the Odia AI application.
Your core directive is multilingual understanding with strictly Odia language output.
The user may ask you questions in Hindi, English, Hinglish, Odia, or a mix of any languages.
NO MATTER what language the user speaks to you in, you MUST ALWAYS respond natively in the Odia language.
Do NOT respond in English, Hindi, or Hinglish unless the user explicitly asks for "Translate to English" via a system action.
Keep your responses helpful, polite, and properly formatted in markdown.
'''

    def _get_url(self):
        # Using v1beta for newest models (2.5) if they are in preview
        return f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    async def generate_response(self, user_query: str, context: str = "") -> str:
        """
        Generates a standard RAG or zero-shot response fully in Odia via REST.
        """
        if not GEMINI_API_KEY or "AIza" not in GEMINI_API_KEY:
            return "Error: Gemini API Key is missing or invalid. Please check your .env file."

        payload = {
            "contents": [{
                "parts": [{"text": f"Context from user documents: {context}\n\nUser Question: {user_query}" if context else user_query}]
            }],
            "systemInstruction": {
                "parts": [{"text": self.system_instruction}]
            },
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048,
            }
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self._get_url(), json=payload, timeout=30.0)
                if response.status_code != 200:
                    return f"Gemini API Error {response.status_code}: {response.text}"
                
                data = response.json()
                if "candidates" in data and data["candidates"]:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                return "AI logic error: No response candidates found."
            except Exception as e:
                return f"Error connecting to Gemini API: {str(e)}"

    async def generate_translation(self, ai_odia_response: str) -> str:
        """
        Translates a previous Odia AI response into English via REST.
        """
        if not GEMINI_API_KEY or "AIza" not in GEMINI_API_KEY:
            return "Error: API Key missing or invalid."

        prompt = f"Translate the following Odia text into fluent English closely maintaining the original tone:\n\n{ai_odia_response}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3}
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self._get_url(), json=payload, timeout=30.0)
                if response.status_code != 200:
                    return f"Translation Error {response.status_code}: {response.text}"
                    
                data = response.json()
                if "candidates" in data and data["candidates"]:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                return "Translation failed."
            except Exception as e:
                return f"Error: {str(e)}"

# Singleton instance
llm_service = LLMService()
