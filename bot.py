import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from config import Config
from database import Database
from gemini_ai import GeminiAI

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()
ai = GeminiAI()

# حالات المحادثة
STATE_NORMAL = "normal"
STATE_AWAITING_COMPLAINT = "awaiting_complaint"
STATE_AWAITING_PHONE = "awaiting_phone"

FUEL_KEYWORDS = {
    'بنزين': 'بنزين',
    'مازوت': 'مازوت', 
    'غاز منزلي': 'غاز منزلي',
    'غاز صناعي': 'غاز صناعي',
    'بنزين': 'بنزين',
    'مازوت': 'مازوت',
    'غاز': 'غاز منزلي',
    'غاز البيت': 'غاز منزلي',
    'غاز المنزل': 'غاز منزلي',
    'غاز المصنع': 'غاز صناعي',
    'الغاز': 'غاز منزلي',
    'fuel': 'بنزين',
    'diesel': 'مازوت',
    'gas': 'غاز منزلي'
}

def detect_fuel_type(text):
    """اكتشاف نوع الوقود من النص"""
    text_lower = text.lower()
    for keyword, fuel in FUEL_KEYWORDS.items():
        if keyword in text_lower:
            return fuel
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء المحادثة"""
    user = update.effective_user
    
    # حفظ معلومات المستخدم
    context.user_data['user_id'] = user.id
    context.user_data['username'] = user.username
    context.user_data['full_name'] = user.full_name
    context.user_data['state'] = STATE_NORMAL
    
    welcome = Config.WELCOME_MESSAGE.format(company_name=Config.COMPANY_NAME)
    
    await update.message.reply_text(welcome)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل الواردة"""
    user = update.effective_user
    text = update.message.text
    current_state = context.user_data.get('state', STATE_NORMAL)
    
    # إظهار indicator الكتابة
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    # === معالجة حالة تقديم الشكوى ===
    if current_state == STATE_AWAITING_COMPLAINT:
        # حفظ نص الشكوى
        context.user_data['complaint_text'] = text
        context.user_data['state'] = STATE_AWAITING_PHONE
        
        await update.message.reply_text(
            "شكراً لك على توضيح الشكوى 📋\n\n"
            "الآن يرجى إرسال رقم هاتفك للتواصل معك (أو اكتب 'تخطي' إذا لا تريد):"
        )
        return
    
    if current_state == STATE_AWAITING_PHONE:
        phone = text if text != 'تخطي' else 'غير متوفر'
        context.user_data['phone'] = phone
        context.user_data['state'] = STATE_NORMAL
        
        # حفظ الشكوى في قاعدة البيانات
        complaint = db.add_complaint(
            user_id=user.id,
            username=user.username,
            full_name=context.user_data.get('full_name', user.full_name),
            phone=phone,
            complaint_text=context.user_data.get('complaint_text', '')
        )
        
        # إرسال إشعار للأدمن
        try:
            admin_msg = f"""🆕 *شكوى جديدة #{complaint.id}*

👤 *المرسل:* {complaint.full_name}
📱 *الهاتف:* {complaint.phone}
📝 *الشكوى:* {complaint.complaint_text}
📅 *التاريخ:* {complaint.created_at.strftime('%Y-%m-%d %H:%M')}"""
            
            await context.bot.send_message(
                chat_id=Config.ADMIN_ID,
                text=admin_msg,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
        
        # رد تأكيد للمستخدم
        confirmation = await ai.generate_complaint_confirmation(
            context.user_data.get('complaint_text', ''),
            phone
        )
        
        await update.message.reply_text(confirmation)
        return
    
    # === معالجة الرسائل العادية ===
    
    # 1. التحقق من طلب سعر وقود
    fuel_type = detect_fuel_type(text)
    if fuel_type and any(word in text.lower() for word in ['سعر', 'كم', 'price', 'cost', 'قيمة', 'ثمن', 'بكام', 'بدفع']):
        price = db.get_fuel_price(fuel_type)
        ex_rate = db.get_exchange_rate()
        
        if price:
            response = await ai.generate_price_response(fuel_type, price, ex_rate)
            await update.message.reply_text(response)
            return
    
    # 2. التحقق من طلب تقديم شكوى
    complaint_keywords = ['شكوى', 'شكوة', 'شكوي', 'complaint', 'تقديم شكوى', 'أشكو', 'أريد أشتكي', 'مشكلة', 'مشكلتي']
    if any(keyword in text.lower() for keyword in complaint_keywords):
        context.user_data['state'] = STATE_AWAITING_COMPLAINT
        
        await update.message.reply_text(
            "بالطبع، يمكنني مساعدتك في تقديم شكوى 📝\n\n"
            "يرجى كتابة تفاصيل الشكوى التي تريد تقديمها:"
        )
        return
    
    # 3. الرد العادي بالذكاء الاصطناعي
    try:
        prices = db.get_all_prices()
        response = await ai.get_response(text, prices)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"AI Error: {e}")
        await update.message.reply_text(
            "عذراً، لم أفهم طلبك تماماً. يمكنك:\n"
            "• سؤالي عن أسعار المحروقات (مثال: كم سعر البنزين؟)\n"
            "• طلب تقديم شكوى (مثال: أريد تقديم شكوى)\n"
            "• أو أي استفسار آخر"
        )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر الأدمن للإحصائيات"""
    if update.effective_user.id != Config.ADMIN_ID:
        await update.message.reply_text("⛔ هذا الأمر مخصص للمدير فقط.")
        return
    
    prices = db.get_all_prices()
    complaints = db.get_all_complaints()
    pending = len([c for c in complaints if c.status == 'pending'])
    
    stats = f"""📊 *إحصائيات البوت*

⛽ أنواع الوقود: {len(prices)}
📝 إجمالي الشكاوى: {len(complaints)}
🟡 قيد الانتظار: {pending}
💱 سعر الصرف: {db.get_exchange_rate().usd_to_syp}

*الأسعار الحالية:*
"""
    for p in prices:
        stats += f"\n• {p.fuel_type}: {p.price_syp} ل.س / {p.price_usd} $"
    
    await update.message.reply_text(stats, parse_mode='Markdown')

async def admin_update_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر الأدمن لتحديث السعر"""
    if update.effective_user.id != Config.ADMIN_ID:
        return
    
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "الاستخدام: /setprice [نوع الوقود] [السعر بالليرة]\n"
                "مثال: /setprice بنزين 8000"
            )
            return
        
        fuel_type = args[0]
        price_syp = float(args[1])
        
        # حساب السعر بالدولار
        ex_rate = db.get_exchange_rate().usd_to_syp
        price_usd = round(price_syp / ex_rate, 2) if ex_rate > 0 else 0
        
        if db.update_fuel_price(fuel_type, price_usd=price_usd, price_syp=price_syp):
            await update.message.reply_text(
                f"✅ تم تحديث سعر {fuel_type}:\n"
                f"🇸🇾 {price_syp} ليرة\n"
                f"💵 {price_usd} دولار"
            )
        else:
            await update.message.reply_text("❌ نوع الوقود غير موجود!")
            
    except ValueError:
        await update.message.reply_text("❌ يرجى إدخال رقم صحيح للسعر!")

async def admin_update_exchange(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر الأدمن لتحديث سعر الصرف"""
    if update.effective_user.id != Config.ADMIN_ID:
        return
    
    try:
        rate = float(context.args[0])
        db.update_exchange_rate(rate)
        await update.message.reply_text(f"✅ تم تحديث سعر الصرف: 1$ = {rate} ل.س")
    except (ValueError, IndexError):
        await update.message.reply_text("الاستخدام: /setexchange [السعر]\nمثال: /setexchange 14500")

async def admin_complaints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الشكاوى للأدمن"""
    if update.effective_user.id != Config.ADMIN_ID:
        return
    
    complaints = db.get_all_complaints()
    
    if not complaints:
        await update.message.reply_text("📭 لا توجد شكاوى حالياً.")
        return
    
    for c in complaints[:5]:
        status = {"pending": "🟡", "reviewed": "🔵", "resolved": "🟢"}.get(c.status, "⚪")
        msg = f"""{status} *شكوى #{c.id}*

👤 {c.full_name or 'غير معروف'}
📱 {c.phone or 'غير متوفر'}
📅 {c.created_at.strftime('%Y-%m-%d %H:%M')}
📝 {c.complaint_text}

لتحديث الحالة: /resolve {c.id}"""
        
        await update.message.reply_text(msg, parse_mode='Markdown')

async def admin_resolve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حل شكوى"""
    if update.effective_user.id != Config.ADMIN_ID:
        return
    
    try:
        comp_id = int(context.args[0])
        db.update_complaint_status(comp_id, 'resolved')
        await update.message.reply_text(f"✅ تم تحديث شكوى #{comp_id} إلى 'تم الحل'")
    except (ValueError, IndexError):
        await update.message.reply_text("الاستخدام: /resolve [رقم الشكوى]")

def main():
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_stats))
    application.add_handler(CommandHandler("setprice", admin_update_price))
    application.add_handler(CommandHandler("setexchange", admin_update_exchange))
    application.add_handler(CommandHandler("complaints", admin_complaints))
    application.add_handler(CommandHandler("resolve", admin_resolve))
    
    # الرسائل النصية
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
