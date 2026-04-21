import google.generativeai as genai
from config import Config

class GeminiAI:
    def __init__(self):
        # تهيئة مكتبة جوجل وتحديد النموذج
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # السياق العام للبوت لضمان شخصية المساعد
        self.system_context = """أنت مساعد ذكي ودي للشركة السورية للبترول - محروقات اللاذقية.
        
قواعد الرد الصارمة:
- رد بشكل ودي ومفيد وقصير جداً (1-3 جمل فقط).
- تخصصك هو المحروقات والخدمات المتعلقة بشركة محروقات فقط.
- لا تخرج عن السياق، واستخدم الإيموجي المناسب.
- استخدم بيانات الأسعار المزودة لك بدقة."""

    async def get_response(self, user_message, db_prices=None):
        """الحصول على رد من الذكاء الاصطناعي بناءً على رسالة المستخدم وأسعار قاعدة البيانات"""
        try:
            context = self.system_context
            
            # إضافة بيانات الأسعار الحالية للسياق إذا توفرت
            if db_prices:
                prices_text = "\n\nالأسعار الحالية المتاحة في قاعدة البيانات:\n"
                for p in db_prices:
                    prices_text += f"- {p.fuel_type}: {p.price_syp:,.0f} ل.س (قديم) | {p.price_syp_new:,.2f} ل.س (جديد)\n"
                context += prices_text

            prompt = f"{context}\n\nرسالة المستخدم: {user_message}\nالرد العربي الودي:"
            
            # طلب التوليد من Gemini
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                return response.text.strip()
            return None
            
        except Exception as e:
            print(f"❌ Gemini Error: {str(e)}")
            return None

    async def generate_complaint_confirmation(self, complaint_text, phone):
        """توليد رسالة تأكيد استلام الشكوى"""
        try:
            prompt = f"قم بتأكيد استلام شكوى العميل صاحب الرقم {phone} التي مضمونها: {complaint_text}. الرد يجب أن يكون قصيراً ومهنياً."
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except:
            return f"✅ تم استلام شكواك بنجاح. سيتم التواصل معك على الرقم {phone} قريباً."
