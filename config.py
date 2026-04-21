import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN', '')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
    COMPLAINT_PHONE = os.getenv('COMPLAINT_PHONE', '+963000000000')
