from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import Config

class AdminPanel:
    def __init__(self, database):
        self.db = database
    
    def is_admin(self, user_id):
        return user_id == Config.ADMIN_ID
    
    async def show_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ ليس لديك صلاحية الوصول!")
            return
        
        keyboard = [
            [InlineKeyboardButton("💰 تعديل الأسعار", callback_data='admin_prices')],
            [InlineKeyboardButton("💱 تعديل سعر الصرف", callback_data='admin_exchange')],
            [InlineKeyboardButton("📋 عرض الشكاوى", callback_data='admin_complaints')],
            [InlineKeyboardButton("📊 إحصائيات", callback_data='admin_stats')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔧 *لوحة تحكم الأدمن*\nاختر الإجراء المطلوب:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_prices_editor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        prices = self.db.get_all_prices()
        text = "💰 *تعديل أسعار المحروقات:*\n\n"
        keyboard = []
        
        for price in prices:
            text += f"*{price.fuel_type}*\n"
            text += f"  💵 دولار: `{price.price_usd}`\n"
            text += f"  🇸🇾 ليرة: `{price.price_syp}`\n\n"
            keyboard.append([
                InlineKeyboardButton(f"تعديل {price.fuel_type}", callback_data=f'edit_price_{price.id}')
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_price_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        price_id = int(query.data.split('_')[-1])
        context.user_data['editing_price_id'] = price_id
        
        await query.edit_message_text(
            "✏️ أرسل السعر الجديد بالليرة السورية:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إلغاء", callback_data='admin_prices')]])
        )
        context.user_data['awaiting_price'] = True
    
    async def show_complaints(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        complaints = self.db.get_all_complaints()
        
        if not complaints:
            await query.edit_message_text(
                "📭 لا توجد شكاوى حالياً.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')]])
            )
            return
        
        for complaint in complaints[:5]:  # Show last 5
            status_emoji = "🟡" if complaint.status == 'pending' else "🟢" if complaint.status == 'resolved' else "🔵"
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
            
            if update.callback_query:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
        
        await query.edit_message_text(
            "📋 *قائمة الشكاوى* (تم إرسال آخر 5 شكاوى في الدردشة)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')]]),
            parse_mode='Markdown'
        )
