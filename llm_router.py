from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
import os

class LLMRouter:
    def __init__(self):
        self.models = []
        
        # === Groq - الأساسي ===
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            self.models.append(
                ChatGroq(
                    model="llama3-8b-8192",
                    temperature=0.7,
                    max_tokens=600,
                    api_key=groq_key
                )
            )
        
        # === Gemini - احتياطي ===
        gemini_key = os.getenv("GOOGLE_API_KEY")
        if gemini_key:
            self.models.append(
                ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash",
                    temperature=0.7,
                    max_tokens=600,
                    google_api_key=gemini_key
                )
            )
    
    def get_llm(self):
        """ترجع أول موديل شغال"""
        if self.models:
            return self.models[0]
        else:
            raise ValueError("ما في أي API Key تم تفعيله!")
    
    def get_response(self, prompt):
        """تجرب كل الموديلات بالترتيب لحد ما يشتغل واحد"""
        for model in self.models:
            try:
                response = model.invoke(prompt)
                return response.content
            except Exception:
                continue
        
        return "عذراً، النظام مشغول حالياً. جرب مرة ثانية بعد دقائق."
