import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackQueryHandler
)
from config import Config
from database import Database
from admin_panel import AdminPanel
from rag_chain import get_answer

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

STATE_NORMAL = "normal"
STATE_AWAITING_COMPLAINT = "awaiting_complaint"
STATE_AWAITING_PHONE = "awaiting_phone"
STATE_EDITING_PRICE = "editing_price"
STATE_EDITING_EXCHANGE = "editing_exchange"

COMPLAINT_KEYWORDS = ['شكوى', 'شكوة', 'شكوي', 'complaint', 'تقديم شكوى', 'أشكو', 'بدي اشتكي']
FUEL_KEYWORDS = ['بنزين', 'مازوت', 'غاز', 'سعر', 'أسعار', 'price', 'fuel']

def is_complaint_request(text):
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in COMPLAINT_KEYWORDS)

def is_fuel_question(text):
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in FUEL_KEYWORDS)

def get_fuel_prices_text():
    """يرجع نص بأسعار المحروقات من قاعدة البيانات"""
    try:
        prices = db.get_all_prices()
        if not prices:
            return None
        lines = ["📋 أسعار المحروقات الحالية:"]
        for p in prices:
            lines.append(f"\n⛽ *{p.fuel_type}*")
            if p.price_usd and p.price_usd > 0:
                lines.append(f"   💵 دولار: `{p.price_usd}`")
            if p.price_syp and p.price_syp > 0:
                lines.append(f"   💷 قديم: `{int(p.price_syp):,}` ل.س")
            if p.price_syp_new and p.price_syp_new > 0:
                lines.append(f"   💶 جديد: `{p.price_syp_new:,.2f}` ل.س")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error getting prices: {e}")
        return None

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

    if current_state == STATE_AWAITING_COMPLAINT:
        context.user_data['complaint_text'] = text
        context.user_data['state'] = STATE_AWAITING_PHONE
        msg = f"شكراً لك على توضيح الشكوى\n\nرقم الشكاوى: {Config.COMPLAINT_PHONE}\n\nالآن يرجى إرسال رقم هاتفك (أو اكتب 'تخطي'):"
        await update.message.reply_text(msg)
        return

    if current_state == STATE_AWAITING_PHONE:
        phone = text if text != 'تخطي' else Config.COMPLAINT_PHONE
        context.user_data['phone'] = phone

        try:
            db.add_complaint(
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
                phone=phone,
                complaint_text=context.user_data.get('complaint_text', '')
            )
        except Exception as e:
            logger.error(f"Error saving complaint: {e}")
            await update.message.reply_text("عذراً، حدث خطأ أثناء حفظ الشكوى. جرب مرة ثانية.")
            context.user_data['state'] = STATE_NORMAL
            context.user_data.pop('complaint_text', None)
            context.user_data.pop('phone', None)
            return

        context.user_data['state'] = STATE_NORMAL
        context.user_data.pop('complaint_text', None)
        context.user_data.pop('phone', None)
        await update.message.reply_text("شكراً، تم تسجيل شكواك وسيتم التواصل معك.")
        return

    if is_complaint_request(text):
        context.user_data['state'] = STATE_AWAITING_COMPLAINT
        msg = f"بالطبع، يمكنني مساعدتك في تقديم شكوى.\n\nرقم الشكاوى: {Config.COMPLAINT_PHONE}\n\nيرجى كتابة تفاصيل الشكوى:"
        await update.message.reply_text(msg)
        return

    # محاولة RAG أولاً
    try:
        response = get_answer(text)
        if response:
            await update.message.reply_text(response)
            return
    except Exception as e:
        logger.error(f"RAG Error: {e}")

    # Fallback: إذا كان السؤال عن أسعار المحروقات
    if is_fuel_question(text):
        prices_text = get_fuel_prices_text()
        if prices_text:
            await update.message.reply_text(prices_text, parse_mode='Markdown')
            return

    # Fallback نهائي
    await update.message.reply_text(
        "عذراً، النظام مشغول حالياً أو لا أملك إجابة لهذا السؤال.\n"
        "يمكنك سؤالي عن:\n"
        "• أسعار المحروقات (بنزين، مازوت، غاز...)\n"
        "• تقديم شكوى\n"
        "• معلومات عامة عن الشركة"
    )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_ID:
        await update.message.reply_text("هذا الأمر مخصص للمدير فقط.")
        return
    await admin_panel.show_admin_menu(update, context)

async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر للمدير لمعرفة حالة النظام"""
    if update.effective_user.id != Config.ADMIN_ID:
        return

    prices = db.get_all_prices()
    complaints_count = len(db.get_all_complaints())

    msg = (
        "🔧 حالة النظام:\n\n"
        f"🛢️ أنواع الوقود: {len(prices)}\n"
        f"📨 عدد الشكاوى: {complaints_count}\n"
        f"🤖 BOT_TOKEN: {'✅ موجود' if Config.BOT_TOKEN else '❌ غير موجود'}\n"
        f"🔑 GROQ_API_KEY: {'✅ موجود' if Config.GROQ_API_KEY else '❌ غير موجود'}\n"
        f"🔑 GEMINI_API_KEY: {'✅ موجود' if Config.GEMINI_API_KEY else '❌ غير موجود'}\n"
        f"👤 ADMIN_ID: {Config.ADMIN_ID}"
    )
    await update.message.reply_text(msg)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'admin_menu':
        await admin_panel.show_admin_menu(update, context)
    elif data == 'admin_prices':
        await admin_panel.show_prices_editor(update, context)
    elif data.startswith('edit_price_'):
        await admin_panel.handle_price_edit(update, context)
    elif data == 'admin_complaints':
        await admin_panel.show_complaints(update, context)
    elif data == 'admin_exchange':
        await query.edit_message_text("تعديل سعر الصرف - قريباً")
    elif data == 'admin_stats':
        await query.edit_message_text("الإحصائيات - قريباً")
    elif data == 'close_menu':
        await query.delete_message()
    elif data.startswith('comp_status_'):
        parts = data.split('_')
        if len(parts) >= 4:
            comp_id = int(parts[2])
            new_status = parts[3]
            try:
                db.update_complaint_status(comp_id, new_status)
                await query.answer(f"تم تحديث الحالة إلى: {new_status}", show_alert=True)
            except Exception as e:
                logger.error(f"Error updating complaint status: {e}")
                await query.answer("حدث خطأ أثناء التحديث", show_alert=True)
    else:
        await query.edit_message_text("أمر غير معروف.")


def main():
    application = Application.builder().token(Config.BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("debug", debug_command))
    application.add_handler(CallbackQueryHandler(button_callback))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("✅ البوت شغال مع نظام RAG الجديد")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
