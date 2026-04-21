import google.generativeai as genai
from config import Config

class GeminiAI:
    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

        self.system_context = """أنت مساعد ذكي ودي للشركة السورية للبترول - محروقات اللاذقية.

قواعد الرد:
- رد بشكل ودي ومفيد وقصير (1-3 جمل).
- إذا سأل عن موضوع خارج الشركة، رد بأدب أن تخصصك هو المحروقات والخدمات المتعلقة بها.
- يمكنك التحادث بشكل عام لكن ارجع للموضوع بذكاء.
- لا تستخدم JSON في الردود العادية.
- استخدم الإيموجي بشكل مناسب.
- إذا سأل عن أسعار محددة، استخدم البيانات المقدمة فقط.
- عند عرض الأسعار: السعر الجديد = السعر القديم / 100 (حذف صفرين تلقائياً)."""

    async def get_response(self, user_message, db_prices=None):
        """الحصول على رد عادي من الذكاء الاصطناعي"""
        try:
            context = self.system_context

            if db_prices:
                prices_text = "\n\nالأسعار الحالية المتاحة:\n"
                for price in db_prices:
                    prices_text += f"- {price.fuel_type}:\n"
                    prices_text += f"  🇸🇾 قديم: {price.price_syp:,.0f} ل.س\n"
                    prices_text += f"  🇸🇾 جديد: {price.price_syp_new:,.2f} ل.س\n"
                    prices_text += f"  💵 دولار: {price.price_usd} $\n"
                context += prices_text 

            prompt = f"""{context}

المستخدم: "{user_message}"

قدم رداً طبيعياً وودياً بالعربية (فقرة قصيرة):"""

            response = self.model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            print("AI Response error: " + str(e))
            return "عذراً، حدث خطأ في معالجة طلبك. يمكنك سؤالي عن أسعار المحروقات أو تقديم شكوى."

    async def generate_price_response(self, fuel_type, price, exchange_rate):
        """توليد رد طبيعي عن السعر المحدد"""
        try:
            ex_rate_text = f"{exchange_rate.usd_to_syp}" if exchange_rate else "غير متوفر"

            prompt = f"""أخبر المستخدم عن سعر {fuel_type}:
- السعر بالدولار: {price.price_usd} $
- السعر بالليرة السورية (القديمة): {price.price_syp:,.0f} ل.س
- السعر بالليرة السورية (الجديدة): {price.price_syp_new:,.2f} ل.س
- سعر الصرف: {ex_rate_text}

رد طبيعي ودي بالعربية (جملة أو جملتين):"""

            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print("Price response error: " + str(e))
            return f"""سعر {fuel_type} حالياً:
💵 {price.price_usd} دولار
🇸🇾 {price.price_syp:,.0f} ل.س (قديم)
🇸🇾 {price.price_syp_new:,.2f} ل.س (جديد)"""

    async def generate_general_prices_response(self, prices, exchange_rate):
        """توليد رد عن جميع الأسعار عند السؤال العام"""
        try:
            ex_rate_value = exchange_rate.usd_to_syp if exchange_rate else 15000

            prices_list = "\n".join([
                f"- {p.fuel_type}: {p.price_syp:,.0f} ل.س (قديم) / {p.price_syp_new:,.2f} ل.س (جديد) / {p.price_usd} $" 
                for p in prices
            ])

            prompt = f"""المستخدم يسأل عن أسعار المحروقات بشكل عام.
الأسعار الحالية:
{prices_list}

سعر الصرف: 1 دولار = {ex_rate_value} ليرة سورية (القديمة)

قدم جواباً ودياً يوضح جميع الأسعار المتاحة (فقرة قصيرة بالعربية):"""

            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print("General prices error: " + str(e))
            ex_rate_value = exchange_rate.usd_to_syp if exchange_rate else 15000
            prices_text = "\n".join([
                f"• {p.fuel_type}: {p.price_syp:,.0f} ل.س (قديم) / {p.price_syp_new:,.2f} ل.س (جديد) / {p.price_usd} $" 
                for p in prices
            ])
            return f"""الأسعار الحالية:
{prices_text}

سعر الصرف: 1 دولار = {ex_rate_value} ليرة سورية"""

    async def generate_complaint_confirmation(self, complaint_text, phone):
        """توليد رسالة تأكيد للشكوى"""
        try:
            prompt = f"""أكد استلام الشكوى بشكل ودي.
نص الشكوى: "{complaint_text}"
رقم الهاتف: {phone}

رسالة قصيرة بالعربية لشكر العميل على الشكوى:"""

            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print("Complaint confirmation error: " + str(e))
            return f"تم استلام شكواك بنجاح!\n\nسيتم مراجعتها والتواصل معك على الرقم: {phone}\n\nشكراً لتواصلك معنا"
