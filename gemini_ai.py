import requests
from config import Config

class GeminiAI:
    def __init__(self):
        self.key = Config.GROQ_API_KEY

    async def get_response(self, text, prices=None):
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "llama3-8b-8192",
                "messages": [
                    {"role":"system","content":"أجب بالعربية بشكل مفيد ومختصر."},
                    {"role":"user","content":text}
                ]
            }

            r = requests.post(url, headers=headers, json=data, timeout=30)
            js = r.json()

            return js["choices"][0]["message"]["content"]

       except Exception as e:
    print("Gemini Error:", repr(e))
    return "الخدمة الذكية غير متاحة حالياً."
