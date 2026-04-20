import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackQueryHandler
)
from config import Config
from database import Database
from gemini_ai import GeminiAI
from admin_panel import AdminPanel

# ✅ تقليل رسائل httpx
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()
ai = GeminiAI()
admin_panel = AdminPanel(db)

STATE_NORMAL = "normal"
STATE_AWAITING_COMPLAINT = "awaiting_complaint"
STATE_AWAITING_PHONE = "awaiting_phone"
STATE_EDITING_PRICE = "editing_price"
STATE_EDITING_EXCHANGE = "editing_exchange"

FUEL_KEYWORDS = {
    'بنزين': 'بنزين',
    'مازوت': 'مازوت', 
    'غاز منزلي': 'غاز منزلي',
    'غاز صناعي': 'غاز صناعي',
    'غاز': 'غاز منزلي',
    'غاز البيت': 'غاز منزلي',
    'غاز المنزل': 'غاز منزلي',
    'غاز المصنع': 'غاز صناعي',
    'الغاز': 'غاز منزلي',
    'fuel': 'بنزين',
    'diesel': 'مازوت',
    'gas': 'غاز منزلي',
    'petrol': 'بنزين',
}

COMPLAINT_KEYWORDS = ['شكوى', 'شكوة', 'شكوي', 'complaint', 'تقديم شكوى', 'أشكو', 
                      'أريد أشتكي', 'مشكلة', 'مشكلتي', 'اعتراض', 'تظلم', 'شاكي', 
                      'نشكو', 'نشكي', 'تذمر']

PRICE_KEYWORDS = ['سعر', 'كم', 'price', 'cost', 'قيمة', 'ثمن', 'بكام', 'بدفع', 
                  'بكم', 'السعر', 'كام', 'أسعار', 'اسعار']

def detect_fuel_type(text):
    text_lower = text.lower()
    sorted_keywords = sorted(FUEL_KEYWORDS.keys(), key=len, reverse=True)
    for keyword in sorted_keywords:
        if keyword in text_lower:
            return FUEL_KEYWORDS[keyword]
    return None

def is_price_query(text):
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in PRICE_KEYWORDS)

def is_complaint_request(text):
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in COMPLAINT_KEYWORDS)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    context.user_data['user_id'] = user.id
    context.user_data['username'] = user.username
    context.user_data['full_name'] = user.full_name
    context.user_data['state'] = STATE_NORMAL
    
    welcome = Config.WELCOME_MESSAGE.format(company_name=Config.COMPANY_NAME)
    await update.message.reply_text(welcome)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    current_state = context.user_data.get('state', STATE_NORMAL)
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    # ================== حالة تعديل السعر ==================
    if current_state == STATE_EDITING_PRICE and user.id == Config.ADMIN_ID:
        try:
            price_syp = float(text)
            price_id = context.user_data.get('editing_price_id')
            
            prices = db.get_all_prices()
            fuel = next((p for p in prices if p.id == price_id), None)
            
            if fuel:
                ex_rate = db.get_exchange_rate().usd_to_syp
                price_usd = round(price_syp / ex_rate, 2) if ex_rate > 0 else 0
                price_syp_new = round(price_syp / 100, 2)
                
                db.update_fuel_price(fuel.fuel_type, price_usd=price_usd, price_syp=price_syp, price_syp_new=price_syp_new)
                
                await update.message.reply_text(
                    f"✅ تم تحديث سعر *{fuel.fuel_type}*:\n"
                    f"🇸🇾 `{price_syp:,.0f}` ليرة (قديم)\n"
                    f"🇸🇾 `{price_syp_new:,.0f}` ليرة (جديد)\n"
                    f"💵 `{price_usd}` دولار",
                    parse_mode='Markdown'
                )
                
                context.user_data['state'] = STATE_NORMAL
                keyboard = [[InlineKeyboardButton("↩️ العودة للقائمة الرئيسية", callback_data='admin_menu')]]
                await update.message.reply_text(
                    "اختر إجراء آخر:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text("❌ حدث خطأ في تحديث السعر!")
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إدخال رقم صحيح! مثال: `8500`", parse_mode='Markdown')
        return
    
    # ================== حالة تعديل سعر الصرف ==================
    if current_state == STATE_EDITING_EXCHANGE and user.id == Config.ADMIN_ID:
        try:
            rate = float(text)
            db.update_exchange_rate(rate)
            
            await update.message.reply_text(
                f"✅ تم تحديث سعر الصرف:\n"
                f"1 دولار = `{rate}` ليرة سورية",
                parse_mode='Markdown'
            )
            
            context.user_data['state'] = STATE_NORMAL
            keyboard = [[InlineKeyboardButton("↩️ العودة للقائمة الرئيسية", callback_data='admin_menu')]]
            await update.message.reply_text(
                "اختر إجراء آخر:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except ValueError:
            await update.message.reply_text("❌ يرجى إدخال رقم صحيح! مثال: `15000`", parse_mode='Markdown')
        return
    
    # ================== حالة انتظار الشكوى ==================
    if current_state == STATE_AWAITING_COMPLAINT:
        context.user_data['complaint_text'] = text
        context.user_data['state'] = STATE_AWAITING_PHONE
        
        await update.message.reply_text(
            f"شكراً لك على توضيح الشكوى 📋\n\n"
            f"📞 *رقم الشكاوى:* {Config.COMPLAINT_PHONE}\n\n"
            f"الآن يرجى إرسال رقم هاتفك للتواصل معك (أو اكتب 'تخطي'):",
            parse_mode='Markdown'
        )
        return
    
    # ================== حالة انتظار الهاتف ==================
    if current_state == STATE_AWAITING_PHONE:
        phone = text if text != 'تخطي' else Config.COMPLAINT_PHONE
        context.user_data['phone'] = phone
        context.user_data['state'] = STATE_NORMAL
        
        complaint = db.add_complaint(
            user_id=user.id,
            username=user.username,
            full_name=context.user_data.get('full_name', user.full_name),
            phone=phone,
            complaint_text=context.user_data.get('complaint_text', '')
        )
        
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
        
        confirmation = await ai.generate_complaint_confirmation(
            context.user_data.get('complaint_text', ''),
            phone
        )
        
        await update.message.reply_text(confirmation)
        return
    
    # ================== معالجة طلب الشكوى (قبل الأسعار) ==================
    if is_complaint_request(text):
        context.user_data['state'] = STATE_AWAITING_COMPLAINT
        
        await update.message.reply_text(
            f"بالطبع، يمكنني مساعدتك في تقديم شكوى 📝\n\n"
            f"📞 *رقم الشكاوى:* {Config.COMPLAINT_PHONE}\n\n"
            f"يرجى كتابة تفاصيل الشكوى:",
            parse_mode='Markdown'
        )
        return
    
    # ================== معالجة أسئلة الأسعار ==================
    fuel_type = detect_fuel_type(text)
    
    if is_price_query(text):
        if fuel_type:
            # سؤال عن سعر معين
            price = db.get_fuel_price(fuel_type)
            ex_rate = db.get_exchange_rate()
            
            if price:
                response = await ai.generate_price_response(fuel_type, price, ex_rate)
                await update.message.reply_text(response)
                return
        else:
            # سؤال عام عن الأسعار
            prices = db.get_all_prices()
            ex_rate = db.get_exchange_rate()
            response = await ai.generate_general_prices_response(prices, ex_rate)
            await update.message.reply_text(response)
            return
    
    # ================== الاستجابة العامة (الخيار الأخير) ==================
    try:
        print(f"📝 User message: {text}")
        print(f"🤖 Calling AI...")
        prices = db.get_all_prices()
        response = await ai.get_response(text, prices)
        print(f"✅ AI Response: {response[:50]}...")
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"AI Error: {e}")
        print(f"❌ Error: {e}")
        await update.message.reply_text(
            "مرحباً! 👋\n\n"
            "يمكنني مساعدتك في:\n"
            "• 💰 معرفة أسعار المحروقات (بنزين، مازوت، غاز...)\n"
            "• 📝 تقديم شكوى أو اقتراح\n"
            "• ❓ الرد على استفساراتك العامة\n\n"
            "كيف يمكنني مساعدتك؟"
        )

# ==================== معالجات الأدمن ====================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_ID:
        await update.message.reply_text("⛔ هذا الأمر مخصص للمدير فقط.")
        return
    
    context.user_data['state'] = STATE_NORMAL
    await admin_panel.show_admin_menu(update, context)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_ID:
        await update.callback_query.answer("⛔ ليس لديك صلاحية!", show_alert=True)
        return
    
    query = update.callback_query
    data = query.data
    
    try:
        if data == 'admin_menu':
            context.user_data['state'] = STATE_NORMAL
            await admin_panel.show_admin_menu(update, context)
        
        elif data == 'admin_prices':
            await admin_panel.show_prices_editor(update, context)
        
        elif data == 'admin_exchange':
            await query.answer()
            await query.edit_message_text(
                "💱 *تعديل سعر الصرف*\n\n"
                "أرسل السعر الجديد (1 دولار = كم ليرة؟)\n"
                "مثال: `15000`",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data='admin_menu')]])
            )
            context.user_data['state'] = STATE_EDITING_EXCHANGE
        
        elif data == 'admin_complaints':
            await admin_panel.show_complaints(update, context)
        
        elif data == 'admin_stats':
            await query.answer()
            prices = db.get_all_prices()
            complaints = db.get_all_complaints()
            pending = len([c for c in complaints if c.status == 'pending'])
            
            stats = f"""📊 *إحصائيات البوت*

⛽ أنواع الوقود: {len(prices)}
📝 إجمالي الشكاوى: {len(complaints)}
🟡 قيد الانتظار: {pending}
💱 سعر الصرف: `{db.get_exchange_rate().usd_to_syp}`

*الأسعار الحالية:*
"""
            for p in prices:
                stats += f"\n• {p.fuel_type}: {p.price_syp:,.0f} ل.س (قديم) / {p.price_syp_new:,.0f} ل.س (جديد) / {p.price_usd} $"
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')]]
            await query.edit_message_text(stats, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        elif data.startswith('comp_status_'):
            parts = data.split('_')
            comp_id = int(parts[2])
            status = parts[3]
            db.update_complaint_status(comp_id, status)
            await query.answer(f"✅ تم تحديث الشكوى!", show_alert=False)
        
        elif data.startswith('edit_price_'):
            await admin_panel.handle_price_edit(update, context)
            context.user_data['state'] = STATE_EDITING_PRICE
        
        elif data == 'close_menu':
            await query.delete_message()
            context.user_data['state'] = STATE_NORMAL
            
    except Exception as e:
        logger.error(f"Callback error: {e}")
        await query.answer("حدث خطأ!", show_alert=True)

async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_ID:
        await update.message.reply_text("⛔ هذا الأمر مخصص للمدير فقط.")
        return
    
    help_text = """🔧 *أوامر لوحة تحكم الأدمن:*

📊 `/admin` - فتح لوحة التحكم التفاعلية

💰 `/setprice [الوقود] [السعر]`
   مثال: `/setprice بنزين 8500`

💱 `/setexchange [السعر]`
   مثال: `/setexchange 15000`

📋 `/complaints` - عرض آخر 5 شكاوى

✅ `/resolve [رقم]` - تحديد شكوى كمحلولة
   مثال: `/resolve 3`"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def admin_update_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_ID:
        return
    
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "❌ الاستخدام: `/setprice [نوع الوقود] [السعر بالليرة]`\n"
                "مثال: `/setprice بنزين 8500`",
                parse_mode='Markdown'
            )
            return
        
        fuel_type = args[0]
        price_syp = float(args[1])
        
        ex_rate = db.get_exchange_rate().usd_to_syp
        price_usd = round(price_syp / ex_rate, 2) if ex_rate > 0 else 0
        
        if db.update_fuel_price(fuel_type, price_usd=price_usd, price_syp=price_syp):
            await update.message.reply_text(
                f"✅ تم تحديث سعر *{fuel_type}*:\n"
                f"🇸🇾 `{price_syp:,.0f}` ليرة\n"
                f"💵 `{price_usd}` دولار",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ نوع الوقود غير موجود! الأنواع المتاحة: بنزين، مازوت، غاز منزلي، غاز صناعي")
            
    except ValueError:
        await update.message.reply_text("❌ يرجى إدخال رقم صحيح للسعر!")

async def admin_update_exchange(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_ID:
        return
    
    try:
        if not context.args:
            await update.message.reply_text("❌ الاستخدام: `/setexchange [السعر]`\nمثال: `/setexchange 15000`", parse_mode='Markdown')
            return
            
        rate = float(context.args[0])
        db.update_exchange_rate(rate)
        await update.message.reply_text(f"✅ تم تحديث سعر الصرف:\n1 دولار = `{rate}` ليرة سورية", parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ يرجى إدخال رقم صحيح!")

async def admin_complaints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_ID:
        return
    
    complaints = db.get_all_complaints()
    
    if not complaints:
        await update.message.reply_text("📭 لا توجد شكاوى حالياً.")
        return
    
    for c in complaints[:5]:
        status = {"pending": "🟡 قيد الانتظار", "reviewed": "🔵 قيد المراجعة", "resolved": "🟢 تم الحل"}.get(c.status, "⚪")
        msg = f"""🆔 *شكوى #{c.id}*

👤 *الاسم:* {c.full_name or 'غير معروف'}
📱 *الهاتف:* {c.phone or 'غير متوفر'}
📅 *التاريخ:* {c.created_at.strftime('%Y-%m-%d %H:%M')}
📊 *الحالة:* {status}
📝 *النص:* {c.complaint_text}

للتحديث: `/resolve {c.id}`"""
        
        await update.message.reply_text(msg, parse_mode='Markdown')

async def admin_resolve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_ID:
        return
    
    try:
        if not context.args:
            await update.message.reply_text("❌ الاستخدام: `/resolve [رقم الشكوى]`", parse_mode='Markdown')
            return
            
        comp_id = int(context.args[0])
        db.update_complaint_status(comp_id, 'resolved')
        await update.message.reply_text(f"✅ تم تحديث شكوى #{comp_id} إلى *تم الحل*", parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ يرجى إدخال رقم صحيح!")

def main():
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # =============== أوامر عادية ===============
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("helpadmin", admin_help))
    application.add_handler(CommandHandler("setprice", admin_update_price))
    application.add_handler(CommandHandler("setexchange", admin_update_exchange))
    application.add_handler(CommandHandler("complaints", admin_complaints))
    application.add_handler(CommandHandler("resolve", admin_resolve))
    
    # =============== معالجات الأزرار ===============
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # =============== معالجة الرسائل (يجب أن تكون الأخيرة) ===============
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    logger.info("🚀 Bot started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
