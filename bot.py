import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters
)
from config import Config
from database import Database
from gemini_ai import GeminiAI
from admin_panel import AdminPanel

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States
WAITING_COMPLAINT, WAITING_PHONE, WAITING_PRICE_USD, WAITING_PRICE_SYP, WAITING_EXCHANGE = range(5)

# Initialize
db = Database()
ai = GeminiAI()
admin = AdminPanel(db)

# Keyboards
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("⛽ أسعار المحروقات", callback_data='menu_prices')],
        [InlineKeyboardButton("📝 تقديم شكوى", callback_data='menu_complaint')],
        [InlineKeyboardButton("🤖 محادثة مع الذكاء الاصطناعي", callback_data='menu_ai')],
        [InlineKeyboardButton("📞 معلومات التواصل", callback_data='menu_contact')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_fuel_keyboard():
    keyboard = [
        [InlineKeyboardButton("⛽ بنزين", callback_data='fuel_بنزين'),
         InlineKeyboardButton("🛢️ مازوت", callback_data='fuel_مازوت')],
        [InlineKeyboardButton("🔥 غاز منزلي", callback_data='fuel_غاز منزلي'),
         InlineKeyboardButton("🏭 غاز صناعي", callback_data='fuel_غاز صناعي')],
        [InlineKeyboardButton("💱 سعر الصرف الحالي", callback_data='exchange_rate')],
        [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data='back_to_main')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Store user info
    context.user_data['user_id'] = user.id
    context.user_data['username'] = user.username
    context.user_data['full_name'] = user.full_name
    
    # Check if admin
    is_admin = user.id == Config.ADMIN_ID
    
    keyboard = get_main_keyboard()
    
    # Add admin button if admin
    if is_admin:
        keyboard.inline_keyboard.append([InlineKeyboardButton("🔧 لوحة تحكم الأدمن", callback_data='admin_menu')])
    
    await update.message.reply_text(
        f"{Config.WELCOME_MESSAGE}\n\n🆔 *معرفك:* `{user.id}`",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🤖 *أوامر البوت:*

/start - بدء البوت والقائمة الرئيسية
/help - عرض هذه المساعدة
/prices - عرض أسعار المحروقات
/complaint - تقديم شكوى جديدة
/admin - لوحة تحكم الأدمن (للمدراء فقط)

💡 يمكنك التحدث معي مباشرة للإجابة على استفساراتك!
    """
    await update.message.reply_text(text, parse_mode='Markdown')

# Callback Handlers
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'menu_prices':
        await query.edit_message_text(
            Config.PRICE_MENU,
            reply_markup=get_fuel_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data.startswith('fuel_'):
        fuel_type = data.replace('fuel_', '')
        price = db.get_fuel_price(fuel_type)
        ex_rate = db.get_exchange_rate()
        
        if price:
            text = f"""
⛽ *{fuel_type}*

💵 *السعر بالدولار:* `{price.price_usd} $`
🇸🇾 *السعر بالليرة:* `{price.price_syp} ل.س`

💱 *سعر الصرف المستخدم:* `{ex_rate.usd_to_syp}`

📅 *آخر تحديث:* `{price.updated_at.strftime('%Y-%m-%d %H:%M')}`
            """
        else:
            text = "❌ لم يتم العثور على السعر!"
        
        await query.edit_message_text(
            text,
            reply_markup=get_fuel_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data == 'exchange_rate':
        ex = db.get_exchange_rate()
        await query.edit_message_text(
            f"💱 *سعر الصرف الحالي:*\n\n1 دولار = `{ex.usd_to_syp}` ليرة سورية\n\n📅 آخر تحديث: {ex.updated_at.strftime('%Y-%m-%d %H:%M')}",
            reply_markup=get_fuel_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data == 'menu_complaint':
        await query.edit_message_text(
            Config.COMPLAINT_PROMPT,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إلغاء", callback_data='back_to_main')]])
        )
        context.user_data['awaiting_complaint'] = True
    
    elif data == 'menu_ai':
        await query.edit_message_text(
            "🤖 *الذكاء الاصطناعي*\n\nيمكنك الآن إرسال أي سؤال وسأقوم بالرد عليك مباشرة!\n\nللخروج من وضع الذكاء الاصطناعي، اضغط رجوع.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data='back_to_main')]]),
            parse_mode='Markdown'
        )
        context.user_data['ai_mode'] = True
    
    elif data == 'menu_contact':
        text = """
📞 *معلومات التواصل:*

🏢 الشركة السورية للبترول
📍 اللاذقية - سوريا
📱 للشكاوى والاستفسارات عبر البوت

🤖 البوت يعمل 24/7 للرد على استفساراتكم
        """
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]]),
            parse_mode='Markdown'
        )
    
    elif data == 'back_to_main':
        context.user_data.clear()
        keyboard = get_main_keyboard()
        if update.effective_user.id == Config.ADMIN_ID:
            keyboard.inline_keyboard.append([InlineKeyboardButton("🔧 لوحة تحكم الأدمن", callback_data='admin_menu')])
        
        await query.edit_message_text(
            f"{Config.WELCOME_MESSAGE}\n\nاختر خدمة:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    # Admin callbacks
    elif data == 'admin_menu':
        await admin.show_admin_menu(update, context)
    
    elif data == 'admin_prices':
        await admin.show_prices_editor(update, context)
    
    elif data == 'admin_exchange':
        await query.edit_message_text(
            "💱 أرسل سعر الصرف الجديد (الدولار مقابل الليرة السورية):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إلغاء", callback_data='admin_menu')]])
        )
        context.user_data['awaiting_exchange'] = True
    
    elif data == 'admin_complaints':
        await admin.show_complaints(update, context)
    
    elif data == 'admin_stats':
        prices = db.get_all_prices()
        complaints_count = len(db.get_all_complaints())
        text = f"""
📊 *إحصائيات البوت:*

⛽ أنواع الوقود: {len(prices)}
📝 إجمالي الشكاوى: {complaints_count}
💱 سعر الصرف الحالي: {db.get_exchange_rate().usd_to_syp}

✅ البوت يعمل بشكل طبيعي
        """
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')]]),
            parse_mode='Markdown'
        )
    
    elif data.startswith('edit_price_'):
        await admin.handle_price_edit(update, context)
    
    elif data.startswith('comp_status_'):
        parts = data.split('_')
        comp_id = int(parts[2])
        status = parts[3]
        db.update_complaint_status(comp_id, status)
        await query.answer(f"✅ تم تحديث حالة الشكوى إلى: {status}")
        await admin.show_complaints(update, context)

# Message Handlers
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    
    # Handle complaint flow
    if context.user_data.get('awaiting_complaint'):
        context.user_data['complaint_text'] = text
        context.user_data['awaiting_complaint'] = False
        context.user_data['awaiting_phone'] = True
        
        await update.message.reply_text(
            "📱 يرجى إرسال رقم هاتفك للتواصل:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 تخطي", callback_data='skip_phone')]])
        )
        return
    
    if context.user_data.get('awaiting_phone'):
        context.user_data['phone'] = text
        context.user_data['awaiting_phone'] = False
        
        # Save complaint
        complaint = db.add_complaint(
            user_id=user.id,
            username=user.username,
            full_name=context.user_data.get('full_name', user.full_name),
            phone=context.user_data.get('phone'),
            complaint_text=context.user_data.get('complaint_text')
        )
        
        # Notify admin
        try:
            admin_text = f"""
🆕 *شكوى جديدة!*

🆔 *الرقم:* #{complaint.id}
👤 *الاسم:* {complaint.full_name}
📱 *الهاتف:* {complaint.phone}
📝 *النص:* {complaint.complaint_text}
            """
            await context.bot.send_message(
                chat_id=Config.ADMIN_ID,
                text=admin_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
        
        await update.message.reply_text(
            Config.COMPLAINT_SUCCESS,
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return
    
    # Handle price editing (admin)
    if context.user_data.get('awaiting_price') and user.id == Config.ADMIN_ID:
        try:
            price_syp = float(text)
            price_id = context.user_data.get('editing_price_id')
            fuel = db.session.query(db.session.query(db.database.FuelPrice).filter_by(id=price_id).first().__class__).get(price_id)
            # Get fuel type from ID
            fuel_types = db.get_all_prices()
            selected_fuel = next((f for f in fuel_types if f.id == price_id), None)
            
            if selected_fuel:
                # Calculate USD price based on exchange rate
                ex_rate = db.get_exchange_rate().usd_to_syp
                price_usd = round(price_syp / ex_rate, 2) if ex_rate > 0 else 0
                
                db.update_fuel_price(selected_fuel.fuel_type, price_usd=price_usd, price_syp=price_syp)
                
                await update.message.reply_text(
                    f"✅ تم تحديث سعر {selected_fuel.fuel_type} بنجاح!\n\n💵 دولار: {price_usd}\n🇸🇾 ليرة: {price_syp}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة التحكم", callback_data='admin_menu')]])
                )
        except ValueError:
            await update.message.reply_text("❌ يرجى إدخال رقم صحيح!")
        
        context.user_data.pop('awaiting_price', None)
        context.user_data.pop('editing_price_id', None)
        return
    
    # Handle exchange rate editing (admin)
    if context.user_data.get('awaiting_exchange') and user.id == Config.ADMIN_ID:
        try:
            rate = float(text)
            db.update_exchange_rate(rate)
            await update.message.reply_text(
                f"✅ تم تحديث سعر الصرف بنجاح!\n\n1 دولار = {rate} ليرة سورية",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة التحكم", callback_data='admin_menu')]])
            )
        except ValueError:
            await update.message.reply_text("❌ يرجى إدخال رقم صحيح!")
        
        context.user_data.pop('awaiting_exchange', None)
        return
    
    # AI Mode
    if context.user_data.get('ai_mode'):
        # Typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        # Get prices for context
        prices = db.get_all_prices()
        
        # Get AI response
        response = await ai.get_response(text, prices)
        
        await update.message.reply_text(
            response,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 إنهاء المحادثة", callback_data='back_to_main')]
            ])
        )
        return
    
    # Default: AI response
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    prices = db.get_all_prices()
    response = await ai.get_response(text, prices)
    
    await update.message.reply_text(
        response,
        reply_markup=get_main_keyboard()
    )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_ID:
        await update.message.reply_text("⛔ غير مصرح!")
        return
    
    await admin.show_admin_menu(update, context)

def main():
    # Create application
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("prices", lambda u, c: u.message.reply_text(Config.PRICE_MENU, reply_markup=get_fuel_keyboard(), parse_mode='Markdown')))
    application.add_handler(CommandHandler("complaint", lambda u, c: u.message.reply_text(Config.COMPLAINT_PROMPT)))
    
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Run
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
