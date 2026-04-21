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

            payload = {
                "model": "llama3-8b-8192",
                "messages": [
                    {
                        "role": "system",
                        "content": "أجب بالعربية بشكل بسيط ومفيد."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ]
            }

            r = requests.post(url, headers=headers, json=payload, timeout=20)

            # 🔴 أهم سطر للتشخيص
            print("AI STATUS:", r.status_code)
            print("AI RESPONSE:", r.text)

            data = r.json()

            return data["choices"][0]["message"]["content"]

        except Exception as e:
            # 🔴 لا تخفي الخطأ أبداً الآن
            print("REAL AI ERROR:", repr(e))
            return f"AI ERROR: {str(e)}"
