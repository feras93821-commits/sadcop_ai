import logging
import asyncio
from telegram import Update
from telegram.error import Conflict, NetworkError, TimedOut
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    CommandHandler,
    filters,
)

from config import Config
from database import Database
from gemini_ai import GeminiAI
from admin_panel import AdminPanel


# ==================================
# LOGGING
# ==================================
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# ==================================
# INIT
# ==================================
DB = Database(Config.DATABASE_URL)
AI = GeminiAI()
ADMIN = AdminPanel(DB)


# ==================================
# STATES
# ==================================
STATE_NORMAL = "normal"
STATE_WAIT_COMPLAINT = "wait_complaint"
STATE_WAIT_PHONE = "wait_phone"


# ==================================
# HELPERS
# ==================================
def is_admin(user_id):
    return user_id == Config.ADMIN_ID


def contains_any(text, words):
    t = text.lower()
    return any(w in t for w in words)


def is_complaint(text):
    return contains_any(
        text,
        ["شكوى", "اعتراض", "بلاغ", "اقتراح", "مشكلة"]
    )


# ==================================
# ERROR HANDLER
# ==================================
async def error_handler(update, context):
    err = context.error

    if isinstance(err, Conflict):
        logger.warning("نسخة أخرى تعمل بنفس التوكن.")
        return

    logger.error("Unhandled error: %s", err)


# ==================================
# ADMIN
# ==================================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user:
        if is_admin(update.effective_user.id):
            await ADMIN.show_admin_menu(update, context)


# ==================================
# MESSAGE HANDLER
# ==================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message:
            return

        text = update.message.text.strip()
        user = update.effective_user

        if not user:
            return

        state = context.user_data.get(
            "state",
            STATE_NORMAL
        )

        # لوحة الأدمن
        if is_admin(user.id) and text == "لوحة الادمن":
            await ADMIN.show_admin_menu(update, context)
            return

        # بدء شكوى
        if is_complaint(text):
            context.user_data["state"] = STATE_WAIT_COMPLAINT

            await update.message.reply_text(
                "يرجى إرسال تفاصيل الشكوى."
            )
            return

        # استقبال نص الشكوى
        if state == STATE_WAIT_COMPLAINT:
            context.user_data["complaint"] = text
            context.user_data["state"] = STATE_WAIT_PHONE

            await update.message.reply_text(
                "أرسل رقم الهاتف أو اكتب تخطي"
            )
            return

        # حفظ الشكوى
        if state == STATE_WAIT_PHONE:
            phone = (
                text
                if text != "تخطي"
                else Config.COMPLAINT_PHONE
            )

            row = DB.add_complaint(
                user.id,
                user.username,
                user.full_name,
                phone,
                context.user_data.get(
                    "complaint",
                    ""
                )
            )

            context.user_data["state"] = STATE_NORMAL

            await update.message.reply_text(
                f"تم استلام الشكوى رقم #{row.id}"
            )
            return

        # رد الذكاء الاصطناعي
        response = await AI.get_response(text)

        if not response:
            response = "يرجى إعادة صياغة السؤال."

        await update.message.reply_text(response)

    except Exception as e:
        logger.error("Message error: %s", e)

        try:
            await update.message.reply_text(
                "حدث خطأ مؤقت."
            )
        except Exception:
            pass


# ==================================
# CALLBACKS
# ==================================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await ADMIN.route_callback(update, context)

    except Exception as e:
        logger.error("Callback error: %s", e)


# ==================================
# RUN BOT
# ==================================
def run_bot():
    app = Application.builder().token(
        Config.BOT_TOKEN
    ).build()

    app.add_error_handler(error_handler)

    app.add_handler(
        CommandHandler("admin", admin_command)
    )

    app.add_handler(
        CallbackQueryHandler(callback_handler)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    logger.info("Bot started (Polling Stable Mode)")

    app.run_polling(
        drop_pending_updates=True,
        poll_interval=1.5,
        timeout=30,
        bootstrap_retries=10,
        close_loop=False
    )


# ==================================
# MAIN LOOP
# ==================================
def main():
    while True:
        try:
            run_bot()

        except Conflict:
            logger.warning(
                "تم اكتشاف نسخة أخرى للبوت."
            )
            asyncio.sleep(10)

        except (NetworkError, TimedOut):
            logger.warning(
                "انقطاع اتصال... إعادة المحاولة"
            )
            asyncio.sleep(5)

        except Exception as e:
            logger.error(
                "Crash Restart: %s",
                e
            )
            asyncio.sleep(10)


if __name__ == "__main__":
    main()
