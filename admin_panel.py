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
            if update.message:
                await update.message.reply_text("ليس لديك صلاحية الوصول!")
            return

        keyboard = [
            [InlineKeyboardButton("تعديل الأسعار", callback_data='admin_prices')],
            [InlineKeyboardButton("تعديل سعر الصرف", callback_data='admin_exchange')],
            [InlineKeyboardButton("عرض الشكاوى", callback_data='admin_complaints')],
            [InlineKeyboardButton("إحصائيات", callback_data='admin_stats')],
            [InlineKeyboardButton("إغلاق", callback_data='close_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    "لوحة تحكم الأدمن

اختر الإجراء المطلوب:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            elif update.message:
                await update.message.reply_text(
                    "لوحة تحكم الأدمن

اختر الإجراء المطلوب:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        except Exception as e:
            print(f"show_admin_menu error: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="لوحة تحكم الأدمن

اختر الإجراء المطلوب:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    async def show_prices_editor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة تعديل الأسعار"""
        query = update.callback_query if update else None

        if query:
            try:
                await query.answer()
            except Exception as e:
                print(f"query.answer() error: {e}")

        try:
            prices = self.db.get_all_prices() or []
            if not prices:
                text = "لا توجد أسعار متاحة حالياً."
                keyboard = [[InlineKeyboardButton("رجوع", callback_data='admin_menu')]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                if query:
                    try:
                        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                    except:
                        await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                else:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup, parse_mode='Markdown')
                return

            text_lines = ["تعديل أسعار المحروقات:
"]
            keyboard = []

            for price in prices:
                price_usd = getattr(price, "price_usd", 0) or 0
                price_syp = getattr(price, "price_syp", 0) or 0
                price_syp_new = getattr(price, "price_syp_new", 0) or 0

                text_lines.append(f"*{price.fuel_type}*")
                text_lines.append(f"  دولار: `{price_usd}`")
                text_lines.append(f"  قديم: `{int(price_syp):,}` ل.س")
                text_lines.append(f"  جديد: `{price_syp_new:,.2f}` ل.س")
                text_lines.append("")

                keyboard.append([
                    InlineKeyboardButton(f"تعديل {price.fuel_type}", callback_data=f'edit_price_{price.id}')
                ])

            keyboard.append([InlineKeyboardButton("رجوع", callback_data='admin_menu')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = "
".join(text_lines)

            if query:
                try:
                    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                except Exception as e:
                    print(f"edit_message_text error: {e}")
                    await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup, parse_mode='Markdown')

        except Exception as e:
            print(f"show_prices_editor fatal error: {e}")
            target = update.effective_chat.id if getattr(update, "effective_chat", None) else Config.ADMIN_ID
            await context.bot.send_message(
                chat_id=target,
                text="حدث خطأ أثناء تحميل قائمة الأسعار."
            )

    async def handle_price_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة اختيار تعديل سعر"""
        query = update.callback_query if update else None

        if query:
            try:
                await query.answer()
            except Exception as e:
                print(f"handle_price_edit query.answer error: {e}")

        try:
            data = query.data if query else ""
            parts = data.split('_')
            price_id = int(parts[-1]) if parts and parts[-1].isdigit() else None

            if not price_id:
                if query:
                    await query.answer("لا أستطيع قراءة معرف السعر.", show_alert=True)
                return

            context.user_data['editing_price_id'] = price_id
            prices = self.db.get_all_prices() or []
            fuel_name = next((p.fuel_type for p in prices if p.id == price_id), "الوقود")

            prompt_text = (
                f"تعديل سعر {fuel_name}

"
                f"أرسل السعر بالليرة السورية (القديمة).
"
                f"سيتم حساب السعر الجديد تلقائياً (قسمة على 100).
"
                f"مثال: `8500`"
            )

            cancel_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("إلغاء", callback_data='admin_menu')]])

            if query:
                try:
                    await query.edit_message_text(prompt_text, parse_mode='Markdown', reply_markup=cancel_keyboard)
                except Exception as e:
                    print(f"handle_price_edit edit_message_text error: {e}")
                    await query.message.reply_text(prompt_text, parse_mode='Markdown', reply_markup=cancel_keyboard)
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=prompt_text, parse_mode='Markdown', reply_markup=cancel_keyboard)

        except Exception as e:
            print(f"handle_price_edit error: {e}")
            await context.bot.send_message(chat_id=Config.ADMIN_ID, text="حدث خطأ أثناء بدء تعديل السعر.")

    async def show_complaints(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة الشكاوى للأدمن"""
        query = update.callback_query if update else None

        if query:
            try:
                await query.answer()
            except Exception as e:
                print(f"show_complaints query.answer error: {e}")

        try:
            complaints = self.db.get_all_complaints()

            if not complaints:
                text = "لا توجد شكاوى حالياً."
                keyboard = [[InlineKeyboardButton("رجوع", callback_data='admin_menu')]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                if query:
                    try:
                        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                    except:
                        await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                else:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup, parse_mode='Markdown')
                return

            for c in complaints[:5]:
                status = {"pending": "قيد الانتظار", "reviewed": "قيد المراجعة", "resolved": "تم الحل"}.get(c.status, "غير معروف")

                keyboard = [
                    [
                        InlineKeyboardButton("حل", callback_data=f'comp_status_{c.id}_resolved'),
                        InlineKeyboardButton("مراجعة", callback_data=f'comp_status_{c.id}_reviewed'),
                        InlineKeyboardButton("انتظار", callback_data=f'comp_status_{c.id}_pending')
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                msg = f"""شكوى #{c.id}

الاسم: {c.full_name or 'غير معروف'}
الهاتف: {c.phone or 'غير متوفر'}
التاريخ: {c.created_at.strftime('%Y-%m-%d %H:%M')}
الحالة: {status}
النص: {c.complaint_text}"""

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=msg,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )

            keyboard = [[InlineKeyboardButton("رجوع للقائمة", callback_data='admin_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="انقر على زر لتحديث حالة أي شكوى",
                reply_markup=reply_markup
            )

        except Exception as e:
            print(f"show_complaints error: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="حدث خطأ أثناء تحميل الشكاوى."
            )
