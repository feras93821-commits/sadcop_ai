from langchain_groq import ChatGroq
import os

class LLMRouter:
    def __init__(self):
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise ValueError("GROQ_API_KEY is required")

        self.llm = ChatGroq(
            model="llama-3.1-70b-versatile",
            temperature=0.6,
            max_tokens=700,
            api_key=groq_key
        )
        print("✅ Groq LLM (Llama 3.1 70B) جاهز")

    def get_response(self, prompt: str):
        try:
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            print(f"Groq Error: {e}")
            return "عذراً، حدث خطأ في معالجة الطلب. جرب مرة أخرى."
