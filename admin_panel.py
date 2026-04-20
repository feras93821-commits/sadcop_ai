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
        
        try:
            await update.callback_query.edit_message_text(
                "🔧 *لوحة تحكم الأدمن*\n\n"
                "اختر الإجراء المطلوب:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except:
            await update.message.reply_text(
                "🔧 *لوحة تحكم الأدمن*\n\n"
                "اختر الإجراء المطلوب:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    async def show_prices_editor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة تعديل الأسعار (محمية من الأخطاء)."""
        query = getattr(update, "callback_query", None)
        if query:
            try:
                await query.answer()
            except Exception:
                pass

        try:
            prices = self.db.get_all_prices() or []
            text_lines = ["💰 *تعديل أسعار المحروقات:*\n"]
            keyboard = []

            for price in prices:
                price_usd = getattr(price, "price_usd", 0) or 0
                price_syp = getattr(price, "price_syp", 0) or 0
                price_syp_new = getattr(price, "price_syp_new", None)
                
                if price_syp_new is None and price_syp:
                    try:
                        price_syp_new = round(float(price_syp) / 100.0, 2)
                    except Exception:
                        price_syp_new = None

                text_lines.append(f"*{price.fuel_type}*")
                text_lines.append(f"  💵 دولار: `{price_usd}`")
                try:
                    text_lines.append(f"  🇸🇾 قديم: `{int(price_syp):,}` ل.س")
                except Exception:
                    text_lines.append(f"  🇸🇾 قديم: `{price_syp}` ل.س")
                if price_syp_new is not None:
                    try:
                        display_new = int(price_syp_new) if float(price_syp_new).is_integer() else price_syp_new
                        text_lines.append(f"  🇸🇾 جديد: `{display_new:,}` ل.س")
                    except Exception:
                        text_lines.append(f"  🇸🇾 جديد: `{price_syp_new}` ل.س")
                else:
                    text_lines.append(f"  🇸🇾 جديد: غير متوفر")
                text_lines.append("")

                keyboard.append([
                    InlineKeyboardButton(f"✏️ تعديل {price.fuel_type}", callback_data=f'edit_price_{price.id}')
                ])

            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = "\n".join(text_lines)

            if query:
                try:
                    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                    return
                except Exception as e:
                    print(f"show_prices_editor edit_message_text error: {e}")

            if query and getattr(query, "message", None):
                await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup, parse_mode='Markdown')

        except Exception as e:
            print(f"show_prices_editor fatal error: {e}")
            target = update.effective_chat.id if getattr(update, "effective_chat", None) else Config.ADMIN_ID
            await context.bot.send_message(
                chat_id=target,
                text="❌ حدث خطأ أثناء تحميل قائمة الأسعار. الرجاء التحقق من السجلات."
            )

    async def handle_price_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة اختيار تعديل سعر — تحفظ id وتطلب من الأدمن إدخال السعر."""
        query = getattr(update, "callback_query", None)
        if query:
            try:
                await query.answer()
            except Exception:
                pass
        try:
            data = query.data if query else (update.message.text if update.message else "")
            parts = (data or "").split('_')
            price_id = int(parts[-1]) if parts and parts[-1].isdigit() else None
            if not price_id:
                if query:
                    await query.answer("❌ لا أستطيع قراءة معرّف السعر.", show_alert=True)
                return

            context.user_data['editing_price_id'] = price_id

            prices = self.db.get_all_prices() or []
            fuel_name = next((p.fuel_type for p in prices if p.id == price_id), "الوقود")

            prompt_text = (
                f"✏️ *تعديل سعر {fuel_name}*\n\n"
                f"أرسل السعر بالليرة السورية (القديمة).\n"
                f"سيتم حساب السعر الجديد تلقائياً (قسمة على 100).\n"
                f"مثال: `8500`"
            )
            if query:
                await query.edit_message_text(prompt_text, parse_mode='Markdown',
                                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data='admin_menu')]]))
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=prompt_text, parse_mode='Markdown')
        except Exception as e:
            print(f"handle_price_edit error: {e}")
            await context.bot.send_message(chat_id=Config.ADMIN_ID, text="❌ حدث خطأ أثناء بدء تعديل السعر.")

    async def show_complaints(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة الشكاوى للأدمن"""
        query = getattr(update, "callback_query", None)
        if query:
            try:
                await query.answer()
            except Exception:
                pass

        try:
            complaints = self.db.get_all_complaints()
            
            if not complaints:
                text = "📭 لا توجد شكاوى حالياً."
                keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if query:
                    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                else:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup, parse_mode='Markdown')
                return

            # Show first 5 complaints with pagination could be added later
            for c in complaints[:5]:
                status = {"pending": "🟡 قيد الانتظار", "reviewed": "🔵 قيد المراجعة", "resolved": "🟢 تم الحل"}.get(c.status, "⚪")
                
                keyboard = [
                    [
                        InlineKeyboardButton("🟢 حل", callback_data=f'comp_status_{c.id}_resolved'),
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
                text="❌ حدث خطأ أثناء تحميل الشكاوى."
            )
