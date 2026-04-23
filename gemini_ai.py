import logging
import time
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackQueryHandler
)
from config import Config
from database import Database
from admin_panel import AdminPanel

# إعداد السجلات
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تهيئة المكونات
print("Initializing database...")
db = Database()
print("Initializing admin panel...")
admin_panel = AdminPanel(db)

# حالات المستخدم (لأغراض الشكاوى والإدارة)
STATE_NORMAL = "normal"
STATE_AWAITING_COMPLAINT = "awaiting_complaint"
STATE_AWAITING_PHONE = "awaiting_phone"

# --- نظام إدارة سياق المحادثة (10 دقائق) ---
user_context = {}
user_states = {}

def update_context(user_id, intent, data=None):
    user_context[user_id] = {
        'intent': intent,
        'data': data,
        'timestamp': time.time()
    }

def get_context(user_id):
    if user_id in user_context:
        ctx = user_context[user_id]
        if time.time() - ctx['timestamp'] < 600:
            return ctx
        else:
            del user_context[user_id]
    return None

# --- قاعدة بيانات الردود المحلية (الاجتماعية والمهنية) ---
LOCAL_KNOWLEDGE = {
    "social": {
        # التحيات والترحيب
        r"(السلام عليكم|سلام|سلامات|مرحبا|هلو|هايو|أهلاً|هلا والله|يسعد مساك|يسعد صباحك)": 
            "وعليكم السلام ورحمة الله وبركاته. أهلاً بك في بوت محروقات اللاذقية الرسمي. كيف يمكنني خدمتك اليوم؟",
        r"(صباح الخير|صباحو|يسعد صباحك|صباح النور)": 
            "صباح النور والسرور. نرجو لك يوماً سعيداً ومليئاً بالإنجاز. كيف نساعدك؟",
        r"(مساء الخير|مسا الخير|يسعد مساك)": 
            "مساء النور والعافية. أهلاً بك، نحن في خدمتك دائماً.",
        
        # السؤال عن الحال والدردشة
        r"(كيف حالك|شلونك|كيفك|شخبارك|شو الأخبار|كيف الصحة|أحوالك|عساك بخير|تمام)": 
            "أنا بخير وأعمل بكامل طاقتي لخدمتكم، شكراً جزيلاً لسؤالك اللطيف! كيف يمكنني مساعدتك اليوم؟",
        r"(الحمد لله|بخير|تمام|ماشي الحال)": 
            "دامت أيامكم بخير وعافية. هل هناك أي استفسار حول خدماتنا تود معرفته؟",
        
        # الهوية والتعريف
        r"(من أنت|مين أنت|شو أنت|شو بتشتغل|شو وظيفتك|عرفني عن حالك|شو اسمك)": 
            "أنا المساعد الرقمي لشركة محروقات اللاذقية. مهمتي توفير معلومات الأسعار، مواقع المحطات، واستقبال الشكاوى بشكل آلي وسريع.",
        r"(من صنعك|مين برمجك|مين طورك|مين صاحبك|مين سوّاك)": 
            "تم تطويري وبرمجتي بواسطة الفريق التقني المختص لخدمة المواطنين وتسهيل الوصول لمعلومات شركة المحروقات في محافظة اللاذقية.",
        r"(هل أنت روبوت|أنت بشر|أنت ذكاء اصطناعي|أنت بوت|حقيقة)": 
            "نعم، أنا مساعد ذكي (روبوت برمجي) مخصص لخدمتكم على مدار الساعة والإجابة على استفساراتكم.",
        
        # الشكر والتقدير
        r"(شكراً|تسلم|مشكور|شكرا جزيلا|ممنونك|يعطيك العافية|عافاك الله|قصرت|ما قصرت|كفو|بطل|شاطر|ممتاز)": 
            "على الرحب والسعة! هذا واجبي. نحن دائماً هنا لضمان تقديم أفضل خدمة لكم في محافظة اللاذقية.",
        
        # الفكاهة والأسئلة العامة
        r"(اشتقتلك|وينك|وين غايب|ليش تأخرت|وين كنت)": 
            "أنا هنا دائماً! لا أغيب عنكم أبداً، بمجرد إرسال رسالة سأكون في خدمتك فوراً.",
        r"(بتحبني|بتحب سوريا|بتحب اللاذقية|شو رأيك فيني)": 
            "بالتأكيد! أنا مبرمج لخدمة هذا الوطن وأهله الكرام في محافظة اللاذقية بكل إخلاص واحترام.",
        r"(شو عم تعمل|شو بتساوي|فاضي|عم تسمعني)": 
            "أنا دائماً بانتظار استفساراتكم للإجابة عليها. هل تريد معرفة أسعار اليوم أو مواقع المحطات؟",
        
        # الوداع
        r"(باي|مع السلامة|بامان الله|تصبح على خير|خاطرك|بشوفك)": 
            "في أمان الله وحفظه. يسعدنا تواصلك معنا في أي وقت. طاب يومك!"
    },
    "fuel_inquiry": {
        r"(بنزين|أوكتان|اوكتان|قديش البنزين|سعر البنزين|بدي بنزين|شقد البنزين)": "بنزين",
        r"(مازوت|ديزل|قديش المازوت|سعر المازوت|بدي مازوت|شقد المازوت)": "مازوت",
        r"(غاز|جرة|قنينة|غاز منزلي|غاز صناعي|تبديل غاز|بدنا غاز)": "غاز"
    },
    "services": {
        r"(شكوى|بدي اشتكي|تظلم|مشكلة|سرقة|غش|معاملة سيئة|تقديم شكوى|بدي ارفع شكوى)": "complaint",
        r"(وين|مكان|عنوان|محطة|كازية|قريب|وين في كازية|أقرب محطة|موقع|اريد كازية)": "station_search",
        r"(تواصل|رقم|تلفون|اتصال|حاكيكم|كلمكم|واتساب|ارقام التواصل)": "contact",
        r"(دوام|أوقات|ساعات العمل|متى بتفتحوا|إيمت بتفتحوا|وقت العمل)": "work_hours"
    }
}

# --- معالجة منطق الرسائل ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    text_lower = text.lower()

    # إدارة الحالة (لتقديم الشكاوى)
    current_state = user_states.get(user_id, STATE_NORMAL)
    
    if current_state == STATE_AWAITING_COMPLAINT:
        context.user_data['complaint_text'] = text
        user_states[user_id] = STATE_AWAITING_PHONE
        await update.message.reply_text("تم تسجيل نص الشكوى. يرجى تزويدنا برقم الهاتف لنتواصل معك ومتابعة الحالة:")
        return
    
    if current_state == STATE_AWAITING_PHONE:
        complaint_text = context.user_data.get('complaint_text')
        phone = text
        try:
            db.add_complaint(user_id, update.effective_user.username, update.effective_user.full_name, phone, complaint_text)
            await update.message.reply_text("✅ تم تقديم شكواك بنجاح للقسم المختص. سيتم التواصل معك قريباً. شكراً لتعاونكم.")
        except Exception as e:
            logger.error(f"Error adding complaint: {e}")
            await update.message.reply_text("عذراً، حدث خطأ أثناء حفظ الشكوى. يرجى المحاولة لاحقاً.")
        user_states[user_id] = STATE_NORMAL
        return

    # 1. الردود الاجتماعية
    for pattern, response in LOCAL_KNOWLEDGE["social"].items():
        if re.search(pattern, text_lower):
            await update.message.reply_text(response)
            return

    # 2. التحقق من السياق (Context)
    prev_ctx = get_context(user_id)

    # 3. معالجة طلبات المحروقات والأسعار
    found_fuel = None
    for pattern, fuel_type in LOCAL_KNOWLEDGE["fuel_inquiry"].items():
        if re.search(pattern, text_lower):
            found_fuel = fuel_type
            break
            
    # دعم السياق المتصل (مثال: سأل عن البنزين ثم قال "والمازوت؟")
    if not found_fuel and prev_ctx and prev_ctx['intent'] == 'price_inquiry':
        if any(word in text_lower for word in ["مازوت", "بنزين", "غاز"]):
            found_fuel = "مازوت" if "مازوت" in text_lower else ("بنزين" if "بنزين" in text_lower else "غاز")

    if found_fuel:
        prices = db.get_fuel_price(found_fuel)
        if prices:
            msg = f"الأسعار الرسمية لـ *{found_fuel}* حالياً في محافظة اللاذقية:\n\n💰 السعر المحلي: {prices.price_syp_new:,.0f} ل.س\n💵 السعر الدولي: {prices.price_usd} $\n\nعلماً أن هذه الأسعار هي المعتمدة رسمياً حتى تاريخ اليوم."
            update_context(user_id, 'price_inquiry', found_fuel)
            await update.message.reply_text(msg, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"عذراً، لم أتمكن من العثور على سعر {found_fuel} في قاعدة البيانات.")
        return

    # 4. البحث عن المحطات في قاعدة البيانات الجديدة
    if re.search(r"(وين|محطة|كازية|أقرب|موقع|عنوان)", text_lower):
        # استخراج كلمات البحث وتنظيف النص
        search_query = re.sub(r"(وين|كازية|محطة|موقع|عنوان|أقرب|بدي|اريد|في)", "", text_lower).strip()
        
        # إذا لم يكتب المستخدم منطقة محددة، نطلب منه التوضيح
        if not search_query or len(search_query) < 2:
            await update.message.reply_text("يرجى كتابة اسم المنطقة أو المحطة التي تبحث عنها (مثال: محطات جبلة، أو كازية حورية).")
            return
            
        results = db.search_stations(search_query)
        if results:
            response = "إليك المحطات التي عثرت عليها بناءً على طلبك:\n\n"
            for s in results[:6]: # عرض أول 6 نتائج
                response += f"📍 *{s.name}*\n- الموقع: {s.location}\n- المنطقة: {s.area}\n- الحالة: {s.status}\n\n"
            update_context(user_id, 'station_search')
            await update.message.reply_text(response, parse_mode='Markdown')
        else:
            await update.message.reply_text("عذراً، لم أجد محطة بهذا الاسم أو المنطقة تحديداً. تتوفر لدينا محطات في (جبلة، الحفة، القرداحة، واللاذقية المدينة). ما هي المنطقة التي تبحث فيها؟")
        return

    # 5. معلومات التواصل وأوقات العمل
    if re.search(r"(تواصل|رقم|تلفون|اتصال|واتساب|ارقام التواصل)", text_lower):
        msg = "يمكنكم التواصل مع الإدارة العامة لشركة المحروقات باللاذقية عبر:\n📞 الهاتف الأرضي: 041-2553151\n📍 العنوان: المنطقة الصناعية - اللاذقية."
        await update.message.reply_text(msg)
        return
    
    if re.search(r"(دوام|أوقات|ساعات العمل|وقت العمل|إيمت بتفتحوا|متى بتفتحوا)", text_lower):
        await update.message.reply_text("الإدارة العامة تعمل من الساعة 8:30 صباحاً حتى 3:30 مساءً. أما المحطات الرئيسية (مثل محطة حورية، شركة سادكوب، محطة الشاطئ) فتعمل على مدار 24 ساعة.")
        return

    # 6. الشكاوى
    if re.search(r"(شكوى|اشتكي|مشكلة|غش|سرقة|معاملة سيئة|تقديم شكوى|بدي ارفع شكوى)", text_lower):
        await update.message.reply_text("نحن هنا لخدمتكم. يرجى كتابة تفاصيل شكواك بدقة (نوع المخالفة واسم المحطة إن وجد):")
        user_states[user_id] = STATE_AWAITING_COMPLAINT
        return

    # 7. الرد الافتراضي الاحترافي
    await update.message.reply_text("عذراً، لم أستطع فهم طلبك بدقة. هل تود الاستفسار عن أسعار المحروقات، مواقع المحطات، أم تقديم شكوى؟ أنا هنا لمساعدتك.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = Config.WELCOME_MESSAGE.format(company_name=Config.COMPANY_NAME)
    keyboard = [
        [InlineKeyboardButton("⛽ أسعار المحروقات", callback_data='prices')],
        [InlineKeyboardButton("📍 مواقع المحطات", callback_data='stations')],
        [InlineKeyboardButton("📝 تقديم شكوى", callback_data='complaint')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome, reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'prices':
        prices = db.get_all_prices()
        if prices:
            text = "قائمة الأسعار الرسمية:\n\n"
            for p in prices:
                text += f"• {p.fuel_type}: {p.price_syp_new:,.0f} ل.س\n"
            await query.edit_message_text(text)
        else:
            await query.edit_message_text("لا توجد أسعار مسجلة حالياً.")
    elif query.data == 'stations':
        await query.edit_message_text("يرجى إرسال اسم المنطقة أو المحطة التي تبحث عنها (مثال: محطات جبلة، أو كازية حورية).")
    elif query.data == 'complaint':
        user_states[update.effective_user.id] = STATE_AWAITING_COMPLAINT
        await query.edit_message_text("يرجى كتابة نص الشكوى وسأقوم برفعه للإدارة فوراً:")
    
    # تفويض الطلبات الأخرى إلى لوحة التحكم
    elif query.data.startswith('admin_') or query.data == 'close_menu' or query.data.startswith('comp_status_'):
        if admin_panel.is_admin(update.effective_user.id):
             await admin_panel.handle_callback(update, context)
        else:
             await query.answer("ليس لديك صلاحية!", show_alert=True)


# --- أوامر الأدمن ---
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await admin_panel.show_admin_menu(update, context)

def main():
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Local Agent Bot started successfully!")
    application.run_polling()

if __name__ == '__main__':
    main()
