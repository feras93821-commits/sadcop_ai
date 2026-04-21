import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "sqlite:///bot.db"
    )

    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

    COMPLAINT_PHONE = os.getenv(
        "COMPLAINT_PHONE",
        ""
    )

    APP_URL = os.getenv("APP_URL", "")
    PORT = int(os.getenv("PORT", "8080"))
