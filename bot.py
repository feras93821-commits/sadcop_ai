import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
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

# Initialize
db = Database()
ai = GeminiAI()
admin = AdminPanel(db)

def get_main_keyboard(user_id=None):
    """إنشاء لوحة المفاتيح الرئيسية"""
    keyboard = [
        [InlineKeyboardButton("⛽ أسعار المحروقات", callback_data='menu_prices')],
        [InlineKeyboardButton("📝 تقديم شكوى", callback_data='menu_complaint')],
        [InlineKeyboardButton("🤖 محادثة مع الذكاء الاصطناعي", callback_data='menu_ai')],
        [InlineKeyboardButton("📞 معلومات التواصل", callback_data='menu_contact')]
    ]
    
    # إضافة زر الأدمن إذا كان المستخدم هو الأدمن
    if user_id and user_id == Config.ADMIN_ID:
        keyboard.append([InlineKeyboardButton("🔧 لوحة تحكم الأدمن", callback_data='admin_menu')])
    
    return InlineKeyboardMarkup(keyboard)

def get_fuel_keyboard():
    """لوحة مفاتيح أنواع الوقود"""
    keyboard = [
        [InlineKeyboardButton("⛽ بنزين", callback_data='fuel_بنزين'),
         InlineKeyboardButton("🛢️ مازوت", callback_data='fuel_مازوت')],
        [InlineKeyboardButton("🔥 غاز منزلي", callback_data='fuel_غاز منزلي'),
         InlineKeyboardButton("🏭 غاز صناعي", callback_data='fuel_غاز صناعي')],
        [InlineKeyboardButton("💱 سعر الصرف الحالي", callback_data='exchange_rate')],
        [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data='back_to_main')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_keyboard():
    """لوحة مفاتيح الأدمن"""
    keyboard = [
        [InlineKeyboardButton("💰 تعديل الأسعار", callback_data='admin_prices')],
        [InlineKeyboardButton("💱 تعديل سعر الصرف", callback_data='admin_exchange')],
        [InlineKeyboardButton("📋 عرض الشكاوى", callback_data='admin_complaints')],
        [InlineKeyboardButton("📊 إحصائيات", callback_data='admin_stats')],
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
    
    keyboard = get_main_keyboard(user.id)
    
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

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_ID:
        await update.message.reply_text("⛔ غير مصرح!")
        return
    
    await update.message.reply_text(
        "🔧 *لوحة تحكم الأدمن*\nاختر الإجراء المطلوب:",
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )

# Callback Handlers
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    
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
        keyboard = get_main_keyboard(user_id)
        await query.edit_message_text(
            f"{Config.WELCOME_MESSAGE}\n\nاختر خدمة:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    # Admin callbacks
    elif data == 'admin_menu':
        if user_id != Config.ADMIN_ID:
            await query.answer("⛔ ليس لديك صلاحية!", show_alert=True)
            return
        await query.edit_message_text(
            "🔧 *لوحة تحكم الأدمن*\nاختر الإجراء المطلوب:",
            reply_markup=get_admin_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data == 'admin_prices':
        if user_id != Config.ADMIN_ID:
            return
        
        prices = db.get_all_prices()
        text = "💰 *تعديل أسعار المحروقات:*\n\n"
        keyboard = []
        
        for price in prices:
            text += f"*{price.fuel_type}*\n"
            text += f"  💵 دولار: `{price.price_usd}`\n"
            text += f"  🇸🇾 ليرة: `{price.price_syp}`\n\n"
            keyboard.append([InlineKeyboardButton(f"تعديل {price.fuel_type}", callback_data=f'edit_price_{price.id}')])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == 'admin_exchange':
        if user_id != Config.ADMIN_ID:
            return
        
        await query.edit_message_text(
            "💱 أرسل سعر الصرف الجديد (الدولار مقابل الليرة السورية):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إلغاء", callback_data='admin_menu')]])
        )
        context.user_data['awaiting_exchange'] = True
    
    elif data == 'admin_complaints':
        if user_id != Config.ADMIN_ID:
            return
        
        complaints = db.get_all_complaints()
        
        if not complaints:
            await query.edit_message_text(
                "📭 لا توجد شكاوى حالياً.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')]])
            )
            return
        
        # إرسال كل شكوى كرسالة منفصلة
        await query.edit_message_text("📋 *جاري عرض الشكاوى...*", parse_mode='Markdown')
        
        for complaint in complaints[:10]:  # آخر 10 شكاوى
            status_emoji = {"pending": "🟡", "reviewed": "🔵", "resolved": "🟢"}.get(complaint.status, "⚪")
            text = f"""
{status_emoji} *شكوى #{complaint.id}*
👤 *الاسم:* {complaint.full_name or 'غير معروف'}
📱 *الهاتف:* {complaint.phone or 'غير متوفر'}
📅 *التاريخ:* {complaint.created_at.strftime('%Y-%m-%d %H:%M')}
📝 *النص:* {complaint.complaint_text}
            """
            
            keyboard = [
                [InlineKeyboardButton("✅ تم المراجعة", callback_data=f'comp_status_{complaint.id}_reviewed'),
                 InlineKeyboardButton("🟢 تم الحل", callback_data=f'comp_status_{complaint.id}_resolved')]
            ]
            
            await context.bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ تم عرض الشكاوى",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع للوحة التحكم", callback_data='admin_menu')]])
        )
    
    elif data == 'admin_stats':
        if user_id != Config.ADMIN_ID:
            return
        
        prices = db.get_all_prices()
        complaints = db.get_all_complaints()
        pending = len([c for c in complaints if c.status == 'pending'])
        
        text = f"""
📊 *إحصائيات البوت:*

⛽ أنواع الوقود: {len(prices)}
📝 إجمالي الشكاوى: {len(complaints)}
🟡 شكاوى قيد الانتظار: {pending}
💱 سعر الصرف: {db.get_exchange_rate().usd_to_syp}

✅ البوت يعمل بشكل طبيعي
        """
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')]]),
            parse_mode='Markdown'
        )
    
    elif data.startswith('edit_price_'):
        if user_id != Config.ADMIN_ID:
            return
        
        price_id = int(data.split('_')[-1])
        context.user_data['editing_price_id'] = price_id
        
        # الحصول على نوع الوقود
        prices = db.get_all_prices()
        selected = next((p for p in prices if p.id == price_id), None)
        
        if selected:
            await query.edit_message_text(
                f"✏️ تعديل سعر *{selected.fuel_type}*\n\nأرسل السعر الجديد بالليرة السورية:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إلغاء", callback_data='admin_prices')]]),
                parse_mode='Markdown'
            )
            context.user_data['awaiting_price'] = True
    
    elif data.startswith('comp_status_'):
        if user_id != Config.ADMIN_ID:
            return
        
        parts = data.split('_')
        comp_id = int(parts[2])
        status = parts[3]
        db.update_complaint_status(comp_id, status)
        await query.answer(f"✅ تم التحديث!")
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 عودة للشكاوى", callback_data='admin_complaints')]
        ]))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    
    # Handle complaint flow
    if context.user_data.get('awaiting_complaint'):
        context.user_data['complaint_text'] = text
        context.user_data['awaiting_complaint'] = False
        context.user_data['awaiting_phone'] = True
        
        await update.message.reply_text(
            "📱 يرجى إرسال رقم هاتفك للتواصل (أو اضغط تخطي):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭️ تخطي", callback_data='skip_phone')]
            ])
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
            reply_markup=get_main_keyboard(user.id)
        )
        context.user_data.clear()
        return
    
    # Handle price editing (admin)
    if context.user_data.get('awaiting_price') and user.id == Config.ADMIN_ID:
        try:
            price_syp = float(text)
            price_id = context.user_data.get('editing_price_id')
            
            prices = db.get_all_prices()
            selected = next((p for p in prices if p.id == price_id), None)
            
            if selected:
                ex_rate = db.get_exchange_rate().usd_to_syp
                price_usd = round(price_syp / ex_rate, 2) if ex_rate > 0 else 0
                
                db.update_fuel_price(selected.fuel_type, price_usd=price_usd, price_syp=price_syp)
                
                await update.message.reply_text(
                    f"✅ تم تحديث سعر *{selected.fuel_type}* بنجاح!\n\n💵 دولار: `{price_usd}`\n🇸🇾 ليرة: `{price_syp}`",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة التحكم", callback_data='admin_menu')]]),
                    parse_mode='Markdown'
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
                f"✅ تم تحديث سعر الصرف بنجاح!\n\n1 دولار = `{rate}` ليرة سورية",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة التحكم", callback_data='admin_menu')]]),
                parse_mode='Markdown'
            )
        except ValueError:
            await update.message.reply_text("❌ يرجى إدخال رقم صحيح!")
        
        context.user_data.pop('awaiting_exchange', None)
        return
    
    # AI Mode or Default AI response
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    try:
        prices = db.get_all_prices()
        response = await ai.get_response(text, prices)
    except Exception as e:
        logger.error(f"AI Error: {e}")
        response = "عذراً، حدث خطأ في الاتصال بالذكاء الاصطناعي. يرجى المحاولة لاحقاً."
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='back_to_main')]]) if context.user_data.get('ai_mode') else get_main_keyboard(user.id)
    
    await update.message.reply_text(
        response,
        reply_markup=keyboard
    )

def main():
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin_command))
    
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Run
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
