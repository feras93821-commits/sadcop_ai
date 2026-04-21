import requests
from config import Config


class GeminiAI:
    def __init__(self):
        self.api_key = Config.GROQ_API_KEY

    async def get_response(self, text, prices=None):
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "llama3-8b-8192",
                "messages": [
                    {
                        "role": "system",
                        "content": "أجب بالعربية بشكل واضح ومفيد."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ]
            }

            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=30
            )

            result = response.json()

            return result["choices"][0]["message"]["content"]

        except Exception as e:
            print("AI ERROR:", repr(e))
            return "الخدمة الذكية متوقفة مؤقتاً."
