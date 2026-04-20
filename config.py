import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///spc_bot.db")
    
    # ✅ إضافة رقم الشكاوى
    COMPLAINT_PHONE = os.getenv("COMPLAINT_PHONE", "+963-123-456789")
    
    COMPANY_NAME = "الشركة السورية للبترول - محروقات اللاذقية"
    
    WELCOME_MESSAGE = """أهلاً وسهلاً بك في {company_name} 👋

أنا المساعد الذكي الخاص بكم، يمكنك التحدث معي بشكل طبيعي:

• 💰 اسألني عن أسعار المحروقات (بنزين، مازوت، غاز...)
• 📝 اطلب تقديم شكوى وسأساعدك في ذلك
• ❓ اسألني أي استفسار عن الشركة والخدمات

كيف يمكنني مساعدتك اليوم؟"""
