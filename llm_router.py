from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os

load_dotenv()

class LLMRouter:
    def __init__(self):
        self.models = []
        
        # Groq (الأول والأسرع)
        if os.getenv("GROQ_API_KEY"):
            self.models.append(ChatGroq(
                model="llama3-8b-8192",
                temperature=0.7,
                max_tokens=500
            ))
        
        # Gemini كاحتياطي
        if os.getenv("GOOGLE_API_KEY"):
            self.models.append(ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                temperature=0.7,
                max_tokens=500
            ))
    
    def get_response(self, prompt):
        for model in self.models:
            try:
                response = model.invoke(prompt)
                return response.content
            except Exception as e:
                print(f"⚠️ فشل الموديل، جاري تجربة التالي...")
                continue
        
        return "عذراً، فيه مشكلة بالاتصال بالنظام. جرب مرة ثانية بعد شوي."

# إنشاء نسخة واحدة من الراوتر
llm_router = LLMRouter()
