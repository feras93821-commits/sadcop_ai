from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from config import Config

class AdminPanel:
    def __init__(self, db):
        self.db = db

    def is_admin(self, user_id):
        return user_id == Config.ADMIN_ID

    async def show_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            return
        kb = [
            [InlineKeyboardButton('💰 الأسعار', callback_data='prices')],
            [InlineKeyboardButton('💱 الصرف', callback_data='exchange')],
            [InlineKeyboardButton('📋 الشكاوى', callback_data='complaints')],
            [InlineKeyboardButton('📊 الإحصائيات', callback_data='stats')],
            [InlineKeyboardButton('❌ إغلاق', callback_data='close')],
        ]
        text = 'لوحة تحكم الأدمن'
        if getattr(update, 'callback_query', None):
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.effective_chat.send_message(text, reply_markup=InlineKeyboardMarkup(kb))

    async def route_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        if not self.is_admin(update.effective_user.id):
            return
        data = q.data
        if data == 'prices':
            await self.show_prices(q)
        elif data == 'exchange':
            rate = self.db.get_exchange_rate()
            await q.edit_message_text(f'سعر الصرف الحالي: {rate.usd_to_syp}')
        elif data == 'complaints':
            await self.show_complaints(q)
        elif data == 'stats':
            await self.show_stats(q)
        elif data == 'close':
            await q.delete_message()

    async def show_prices(self, q):
        prices = self.db.get_all_prices()
        text = 'الأسعار الحالية:\n\n'
        for p in prices:
            text += f"{p.fuel_type}: {p.price_syp:,.0f} ل.س\n"
        await q.edit_message_text(text)

    async def show_complaints(self, q):
        rows = self.db.get_all_complaints()[:10]
        if not rows:
            await q.edit_message_text('لا توجد شكاوى.')
            return
        text='آخر الشكاوى:\n\n'
        for r in rows:
            text += f"#{r.id} | {r.full_name or 'بدون اسم'} | {r.status}\n{r.complaint_text[:80]}\n\n"
        await q.edit_message_text(text)

    async def show_stats(self, q):
        prices = len(self.db.get_all_prices())
        complaints = len(self.db.get_all_complaints())
        await q.edit_message_text(f'أنواع الوقود: {prices}\nإجمالي الشكاوى: {complaints}')
