import logging
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
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
    text = text.lower()
    return any(w in text for w in words)


def is_complaint(text):
    return contains_any(
        text,
        ["شكوى", "اعتراض", "اقتراح", "مشكلة", "بلاغ"]
    )


def is_price(text):
    return contains_any(
        text,
        ["سعر", "أسعار", "بنزين", "مازوت", "غاز", "كم"]
    )


# ==================================
# ERROR HANDLER
# ==================================
async def error_handler(update, context):
    logger.error("Error: %s", context.error)


# ==================================
# ADMIN
# ==================================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user and is_admin(update.effective_user.id):
        await ADMIN.show_admin_menu(update, context)


# ==================================
# MAIN MESSAGE HANDLER
# ==================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.text:
            return

        text = update.message.text.strip()
        user = update.effective_user

        if not user:
            return

        state = context.user_data.get("state", STATE_NORMAL)

        # admin text
        if is_admin(user.id) and text == "لوحة الادمن":
            await ADMIN.show_admin_menu(update, context)
            return

        # complaint flow
        if state == STATE_WAIT_COMPLAINT:
            context.user_data["complaint"] = text
            context.user_data["state"] = STATE_WAIT_PHONE

            await update.message.reply_text(
                "أرسل رقم الهاتف أو اكتب تخطي"
            )
            return

        if state == STATE_WAIT_PHONE:
            phone = text if text != "تخطي" else Config.COMPLAINT_PHONE

            row = DB.add_complaint(
                user.id,
                user.username,
                user.full_name,
                phone,
                context.user_data.get("complaint", "")
            )

            context.user_data["state"] = STATE_NORMAL

            await update.message.reply_text(
                f"تم استلام الشكوى رقم #{row.id}"
            )
            return

        if is_complaint(text):
            context.user_data["state"] = STATE_WAIT_COMPLAINT

            await update.message.reply_text(
                "أرسل تفاصيل الشكوى."
            )
            return

        # AI response
        prices = DB.get_all_prices() if is_price(text) else None

        response = await AI.get_response(text, prices)

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
# MAIN
# ==================================
def main():
    app = Application.builder().token(
        Config.BOT_TOKEN
    ).build()

    app.add_error_handler(error_handler)

    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    logger.info("Bot started in WEBHOOK mode")

    app.run_webhook(
        listen="0.0.0.0",
        port=8080,
        webhook_url=f"{Config.APP_URL}/{Config.BOT_TOKEN}",
        secret_token="securetoken123",
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
