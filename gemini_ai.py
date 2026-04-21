import google.generativeai as genai
from config import Config

class GeminiAI:
    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.base_context = '''أنت مساعد ذكي للشركة السورية للبترول - محروقات اللاذقية.
قواعد العمل:
- تحدث بالعربية الطبيعية.
- كن مختصراً ومفيداً.
- إذا سأل المستخدم عن الأسعار استخدم البيانات المرسلة فقط.
- إذا كان السؤال خارج اختصاص الشركة أجب بلطف ثم وجّه للخدمات المتاحة.
- افهم اللهجة السورية والعربية العامة.
- لا تستخدم JSON.
'''

    async def ask(self, prompt):
        try:
            r = self.model.generate_content(prompt)
            txt = getattr(r, 'text', '') or ''
            return txt.strip() if txt.strip() else 'يمكنني مساعدتك في الأسعار والشكاوى والاستفسارات العامة.'
        except Exception:
            return 'تعذر الاتصال بالخدمة الذكية حالياً، حاول بعد قليل.'

    async def get_response(self, user_message, prices=None):
        prices_text = self._prices_text(prices)
        prompt = f"{self.base_context}\n{prices_text}\nالمستخدم: {user_message}\nالرد:" 
        return await self.ask(prompt)

    async def generate_general_prices_response(self, prices, exchange_rate):
        prices_text = self._prices_text(prices)
        rate = getattr(exchange_rate, 'usd_to_syp', 0)
        prompt = f"{self.base_context}\nهذه أسعار المحروقات الحالية:\n{prices_text}\nسعر الصرف: {rate}\nقدّم جواباً واضحاً ومنسقاً." 
        return await self.ask(prompt)

    async def generate_complaint_confirmation(self, complaint_text, phone):
        prompt = f"أكد استلام شكوى المستخدم باحتراف. نص الشكوى: {complaint_text}. الهاتف: {phone}" 
        return await self.ask(prompt)

    def _prices_text(self, prices):
        if not prices:
            return 'لا توجد أسعار متاحة حالياً.'
        lines = []
        for p in prices:
            lines.append(f"- {p.fuel_type}: {p.price_syp:,.0f} ل.س قديم / {p.price_syp_new:,.0f} جديد / {p.price_usd}$")
        return '\n'.join(lines)
