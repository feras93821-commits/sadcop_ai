import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackQueryHandler
)
from config import Config
from database import Database
from admin_panel import AdminPanel
from rag_chain import get_answer   # ← هذا الجديد
from llm_router import LLMRouter

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print("Initializing database...")
db = Database()
print("Initializing admin panel...")
admin_panel = AdminPanel(db)

# إعداد النظام الجديد
router = LLMRouter()

STATE_NORMAL = "normal"
STATE_AWAITING_COMPLAINT = "awaiting_complaint"
STATE_AWAITING_PHONE = "awaiting_phone"
STATE_EDITING_PRICE = "editing_price"
STATE_EDITING_EXCHANGE = "editing_exchange"

COMPLAINT_KEYWORDS = ['شكوى', 'شكوة', 'شكوي', 'complaint', 'تقديم شكوى', 'أشكو', 'بدي اشتكي']

def is_complaint_request(text):
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in COMPLAINT_KEYWORDS)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً بك 👋\n"
        "أنا مساعد الشركة السورية للبترول - فرع محروقات اللاذقية\n"
        "كيف أقدر أساعدك اليوم؟"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    current_state = context.user_data.get('state', STATE_NORMAL)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    # حالات الأدمن
    if current_state in (STATE_EDITING_PRICE, STATE_EDITING_EXCHANGE) and user.id == Config.ADMIN_ID:
        # (نبقي الكود القديم هنا كما هو)
        pass

    # حالات الشكاوى
    if current_state == STATE_AWAITING_COMPLAINT:
        # (نبقي كود الشكوى كما هو)
        pass

    if current_state == STATE_AWAITING_PHONE:
        # (نبقي كود الشكوى كما هو)
        pass

    if is_complaint_request(text):
        context.user_data['state'] = STATE_AWAITING_COMPLAINT
        msg = "بالطبع، يمكنني مساعدتك في تقديم شكوى.\n\nرقم الشكاوى: 0933145808\n\nيرجى كتابة تفاصيل الشكوى:"
        await update.message.reply_text(msg)
        return

    # ←←←← هنا الجزء الجديد (الأهم) ←←←←
    try:
        response = get_answer(text)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"RAG Error: {e}")
        await update.message.reply_text("عذراً، حدث خطأ في النظام. جرب مرة ثانية.")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_ID:
        await update.message.reply_text("هذا الأمر مخصص للمدير فقط.")
        return
    await admin_panel.show_admin_menu(update, context)


def main():
    application = Application.builder().token(Config.BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & \~filters.COMMAND, handle_message))

    logger.info("✅ البوت شغال مع نظام RAG الجديد")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
