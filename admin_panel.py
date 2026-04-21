from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import Config

class AdminPanel:
    def __init__(self, database):
        self.db = database
    
    def is_admin(self, user_id):
        return user_id == Config.ADMIN_ID
    
    async def show_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة الأدمن الرئيسية"""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ ليس لديك صلاحية الوصول!")
            return
        
        keyboard = [
            [InlineKeyboardButton("💰 تعديل الأسعار", callback_data='admin_prices')],
            [InlineKeyboardButton("💱 تعديل سعر الصرف", callback_data='admin_exchange')],
            [InlineKeyboardButton("📋 عرض الشكاوى", callback_data='admin_complaints')],
            [InlineKeyboardButton("📊 إحصائيات", callback_data='admin_stats')],
            [InlineKeyboardButton("❌ إغلاق", callback_data='close_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_text = """🔧 *لوحة تحكم الأدمن*

اختر الإجراء المطلوب:"""

        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    admin_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    admin_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        except Exception as e:
            print(f"show_admin_menu error: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=admin_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    async def show_complaints(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض كافة الشكاوى في قاعدة البيانات"""
        if not self.is_admin(update.effective_user.id):
            return

        try:
            complaints = self.db.get_all_complaints()
            if not complaints:
                await update.callback_query.edit_message_text(
                    "📭 لا يوجد شكاوى حالياً.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')]])
                )
                return

            await update.callback_query.answer()
            
            for c in complaints:
                status = "🔴 معلقة" if c.status == 'pending' else "🟢 تم الحل" if c.status == 'resolved' else "🔵 قيد المراجعة"
                
                keyboard = [
                    [
                        InlineKeyboardButton("🟢 تم الحل", callback_data=f'comp_status_{c.id}_resolved'),
                        InlineKeyboardButton("🔵 مراجعة", callback_data=f'comp_status_{c.id}_reviewed'),
                        InlineKeyboardButton("🟡 انتظار", callback_data=f'comp_status_{c.id}_pending')
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                msg = f"""🆔 *شكوى #{c.id}*

👤 *الاسم:* {c.full_name or 'غير معروف'}
📱 *الهاتف:* {c.phone or 'غير متوفر'}
📅 *التاريخ:* {c.created_at.strftime('%Y-%m-%d %H:%M')}
📊 *الحالة:* {status}
📝 *النص:* {c.complaint_text}"""
                
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=msg,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )

            # Send back button separately
            keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data='admin_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="👆 انقر على زر لتحديث حالة أي شكوى",
                reply_markup=reply_markup
            )

        except Exception as e:
            print(f"show_complaints error: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ حدث خطأ أثناء جلب الشكاوى."
            )
