import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters, CallbackQueryHandler, CommandHandler
from config import Config
from database import Database
from gemini_ai import GeminiAI
from admin_panel import AdminPanel

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

DB = Database(Config.DATABASE_URL)
AI = GeminiAI()
ADMIN = AdminPanel(DB)

STATE_NORMAL='normal'
STATE_AWAITING_COMPLAINT='awaiting_complaint'
STATE_AWAITING_PHONE='awaiting_phone'

PRICE_WORDS = ['سعر','اسعار','أسعار','كم']
COMPLAINT_WORDS = ['شكوى','اعتراض','مشكلة','اقتراح']


def looks_like_price(text:str)->bool:
    t=text.lower()
    return any(w in t for w in PRICE_WORDS)


def looks_like_complaint(text:str)->bool:
    t=text.lower()
    return any(w in t for w in COMPLAINT_WORDS)


async def private_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == Config.ADMIN_ID:
        await ADMIN.show_admin_menu(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user = update.effective_user
    text = update.message.text.strip()
    state = context.user_data.get('state', STATE_NORMAL)

    if user.id == Config.ADMIN_ID and text == 'لوحة الادمن':
        await ADMIN.show_admin_menu(update, context)
        return

    if state == STATE_AWAITING_COMPLAINT:
        context.user_data['complaint_text'] = text
        context.user_data['state'] = STATE_AWAITING_PHONE
        await update.message.reply_text('أرسل رقم هاتفك للتواصل أو اكتب تخطي')
        return

    if state == STATE_AWAITING_PHONE:
        phone = text if text != 'تخطي' else Config.COMPLAINT_PHONE
        c = DB.add_complaint(user.id, user.username, user.full_name, phone, context.user_data.get('complaint_text',''))
        context.user_data['state'] = STATE_NORMAL
        msg = await AI.generate_complaint_confirmation(c.complaint_text, phone)
        await update.message.reply_text(msg)
        return

    if looks_like_complaint(text):
        context.user_data['state'] = STATE_AWAITING_COMPLAINT
        await update.message.reply_text('يرجى كتابة تفاصيل الشكوى وسأقوم بتسجيلها.')
        return

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    except Exception:
        pass

    prices = DB.get_all_prices()
    if looks_like_price(text):
        response = await AI.generate_general_prices_response(prices, DB.get_exchange_rate())
    else:
        response = await AI.get_response(text, prices)

    await update.message.reply_text(response)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ADMIN.route_callback(update, context)


def main():
    app = Application.builder().token(Config.BOT_TOKEN).build()
    app.add_handler(CommandHandler('admin', private_admin))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info('Bot started')
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
