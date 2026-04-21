import google.generativeai as genai
from config import Config

class GeminiAI:
    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def get_response(self, text, prices=None):
        try:
            prompt = f"رد بالعربية بشكل مفيد ومختصر: {text}"
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print("Gemini Error:", e)
            return "حالياً الخدمة الذكية غير متاحة، حاول بعد قليل."
