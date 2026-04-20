import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot Token
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    # Google Gemini API Key
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Admin Telegram ID
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///spc_bot.db")
    
    # Company Info
    COMPANY_NAME = "الشركة السورية للبترول - محروقات اللاذقية"
    
    # Messages
    WELCOME_MESSAGE = f"أهلاً وسهلاً 🌟\nأنا المساعد الذكي للشركة السورية للبترول - محروقات اللاذقية ⛽\nأنا جاهز للرد على جميع استفساراتكم حول أسعار المحروقات والخدمات."
    
    COMPLAINT_PROMPT = "يرجى كتابة شكواك بالتفصيل وسيتم إرسالها إلى الإدارة مباشرة:"
    COMPLAINT_SUCCESS = "✅ تم استلام شكواك بنجاح! سيتم مراجعتها والرد عليك في أقرب وقت."
    
    PRICE_MENU = """
💰 *أسعار المحروقات الحالية:*

اختر نوع الوقود لمعرفة السعر:
"""
