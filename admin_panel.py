async def show_prices_editor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة تعديل الأسعار"""
    query = update.callback_query
    await query.answer()
    
    prices = self.db.get_all_prices()
    text = "💰 *تعديل أسعار المحروقات:*\n\n"
    keyboard = []
    
    for price in prices:
        text += f"*{price.fuel_type}*\n"
        text += f"  💵 دولار: `{price.price_usd}`\n"
        text += f"  🇸🇾 قديم: `{price.price_syp:,.0f}` ل.س\n"  # ✅ العملة القديمة
        text += f"  🇸🇾 جديد: `{price.price_syp_new:,.0f}` ل.س\n\n"  # ✅ العملة الجديدة
        keyboard.append([
            InlineKeyboardButton(f"✏️ تعديل {price.fuel_type}", callback_data=f'edit_price_{price.id}')
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
