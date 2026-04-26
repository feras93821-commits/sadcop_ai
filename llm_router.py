from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
import os

class LLMRouter:
    def __init__(self):
        self.models = []

        # === Groq - الأساسي ===
        groq_key = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")
        if groq_key:
            try:
                self.models.append(
                    ChatGroq(
                        model="llama-3.1-8b-instant",
                        temperature=0.7,
                        max_tokens=600,
                        api_key=groq_key
                    )
                )
                print("✅ Groq model loaded")
            except Exception as e:
                print("❌ Groq init error:", e)
        else:
            print("⚠️ GROQ_API_KEY not found")

        # === Gemini - احتياطي ===
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key:
            try:
                self.models.append(
                    ChatGoogleGenerativeAI(
                        model="gemini-1.5-flash",
                        temperature=0.7,
                        max_tokens=600,
                        google_api_key=gemini_key
                    )
                )
                print("✅ Gemini model loaded")
            except Exception as e:
                print("❌ Gemini init error:", e)
        else:
            print("⚠️ GEMINI_API_KEY not found")

        if not self.models:
            print("❌ لا يوجد أي موديل شغال! تحقق من مفاتيح API في إعدادات Railway.")

    def get_llm(self):
        if self.models:
            return self.models[0]
        else:
            raise ValueError("ما في أي API Key تم تفعيله!")

    def get_response(self, prompt):
        for i, model in enumerate(self.models):
            try:
                response = model.invoke(prompt)
                return response.content
            except Exception as e:
                print(f"❌ Model {i} failed: {e}")
                continue

        return None  # Return None so caller can detect failure
