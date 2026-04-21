import logging
import asyncio
from telegram import Update
from telegram.constants import ChatAction
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


# ===============================
# LOGGING (clean)
# ===============================
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# ===============================
# INIT
# ===============================
DB = Database(Config.DATABASE_URL)
AI = GeminiAI()
ADMIN = AdminPanel(DB)


# ===============================
# STATES
# ===============================
STATE_NORMAL = "normal"
STATE_WAIT_COMPLAINT = "wait_complaint"
STATE_WAIT_PHONE = "wait_phone"


# ===============================
# HELPERS
# ===============================
def is_admin(user_id: int) -> bool:
    return user_id == Config.ADMIN_ID


def contains_any(text: str, words: list) -> bool:
    t = text.lower()
    return any(word in t for word in words)


def is_complaint(text: str) -> bool:
    return contains_any(
        text,
        [
            "شكوى",
            "اعتراض",
            "مشكلة",
            "اقتراح",
            "بلاغ",
            "تظلم",
        ],
    )


def is_price_question(text: str) -> bool:
    return contains_any(
        text,
        [
            "سعر",
            "أسعار",
            "كم",
            "بنزين",
            "مازوت",
            "غاز",
        ],
    )


# ===============================
# ERROR HANDLER
# ===============================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled error: %s", context.error)


# ===============================
# ADMIN COMMAND
# ===============================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return

    if is_admin(update.effective_user.id):
        await ADMIN.show_admin_menu(update, context)


# ===============================
# MAIN MESSAGE HANDLER
# ===============================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.text:
            return

        user = update.effective_user
        chat_id = update.effective_chat.id
        text = update.message.text.strip()

        if not user:
            return

        state = context.user_data.get("state", STATE_NORMAL)

        # =======================
        # ADMIN TEXT SHORTCUT
        # =======================
        if is_admin(user.id) and text == "لوحة الادمن":
            await ADMIN.show_admin_menu(update, context)
            return

        # =======================
        # COMPLAINT FLOW
        # =======================
        if state == STATE_WAIT_COMPLAINT:
            context.user_data["complaint_text"] = text
            context.user_data["state"] = STATE_WAIT_PHONE

            await update.message.reply_text(
                "أرسل رقم الهاتف للتواصل أو اكتب: تخطي"
            )
            return

        if state == STATE_WAIT_PHONE:
            phone = text

            if text == "تخطي":
                phone = Config.COMPLAINT_PHONE

            complaint = DB.add_complaint(
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
                phone=phone,
                complaint_text=context.user_data.get(
                    "complaint_text", ""
                ),
            )

            context.user_data["state"] = STATE_NORMAL

            await update.message.reply_text(
                f"تم استلام شكواك بنجاح رقم #{complaint.id}"
            )
            return

        # Start complaint
        if is_complaint(text):
            context.user_data["state"] = STATE_WAIT_COMPLAINT

            await update.message.reply_text(
                "يرجى إرسال تفاصيل الشكوى."
            )
            return

        # =======================
        # TYPING ACTION
        # =======================
        try:
            await context.bot.send_chat_action(
                chat_id=chat_id,
                action=ChatAction.TYPING
            )
        except Exception:
            pass

        # =======================
        # PRICE QUESTIONS
        # =======================
        if is_price_question(text):
            prices = DB.get_all_prices()
            response = await AI.get_response(text, prices)

        else:
            response = await AI.get_response(text)

        if not response:
            response = "لم أتمكن من فهم الطلب، حاول بصياغة أخرى."

        await update.message.reply_text(response)

    except Exception as e:
        logger.error("handle_message error: %s", e)

        try:
            await update.message.reply_text(
                "حدث خطأ مؤقت، حاول مرة أخرى."
            )
        except Exception:
            pass


# ===============================
# CALLBACK BUTTONS
# ===============================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await ADMIN.route_callback(update, context)
    except Exception as e:
        logger.error("callback error: %s", e)


# ===============================
# STARTUP
# ===============================
async def post_init(app: Application):
    try:
        await app.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook removed")
    except Exception as e:
        logger.warning("Webhook cleanup skipped: %s", e)


# ===============================
# MAIN
# ===============================
def main():
    app = (
        Application.builder()
        .token(Config.BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_error_handler(error_handler)

    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    logger.info("Bot started")

    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        close_loop=False,
    )


if __name__ == "__main__":
    main()
