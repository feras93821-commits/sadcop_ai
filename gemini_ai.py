import os
import asyncio
from google import genai
from config import Config

class GeminiAI:
    def __init__(self):
        try:
            # تهيئة المكتبة الجديدة
            self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
            self.gemini_available = True
            print("Google Gemini (New SDK) initialized successfully")
        except Exception as e:
            print(f"Google Gemini init failed: {e}")
            self.gemini_available = False
            self.client = None

        self.grok_api_key = os.getenv("GROK_API_KEY", "")
        self.grok_available = bool(self.grok_api_key)

        self.system_context = """انت مساعد ذكي ودي للشركة السورية للبترول - محروقات اللاذقية.

قواعد الرد:
- رد بشكل ودي ومفيد وقصير (1-3 جمل).
- تخصصك هو المحروقات والخدمات المتعلقة بها.
- استخدم الايموجي بشكل مناسب."""

    async def _generate_with_fallback(self, prompt):
        """دالة داخلية للتعامل مع طلبات الذكاء الاصطناعي"""
        if self.gemini_available and self.client:
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model='gemini-1.5-flash',
                    config={
                        'system_instruction': self.system_context,
                        'temperature': 0.7,
                    },
                    contents=prompt
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                print(f"Gemini AI error: {e}")

        return None

    async def get_response(self, user_text, *args, **kwargs):
        """الدالة الأساسية التي يستدعيها البوت"""
        result = await self._generate_with_fallback(user_text)
        return result or "عذراً، واجهت مشكلة في معالجة طلبك حالياً."

    async def generate_price_response(self, fuel_type, price_data, exchange_rate):
        try:
            prompt = (
                f"اشرح سعر {fuel_type} للعميل.\n"
                f"السعر القديم: {price_data.price_syp:,.0f} ل.س\n"
                f"السعر الجديد: {price_data.price_syp_new:,.0f} ل.س\n"
                f"السعر بالدولار: {price_data.price_usd} $\n"
                f"سعر الصرف: 1 دولار = {exchange_rate.usd_to_syp} ل.س\n"
                "اجعل الرد ودياً ومختصراً."
            )
            return await self._generate_with_fallback(prompt)
        except Exception as e:
            print(f"Price response error: {e}")
            return None

    async def generate_general_prices_response(self, prices, exchange_rate):
        try:
            prices_text = "\n".join([
                f"- {p.fuel_type}: {p.price_syp_new:,.0f} ل.س / {p.price_usd} $"
                for p in prices
            ])
            prompt = (
                f"اعرض قائمة الأسعار التالية للعميل بوضوح:\n{prices_text}\n"
                f"سعر الصرف الحالي: {exchange_rate.usd_to_syp} ل.س."
            )
            return await self._generate_with_fallback(prompt)
        except Exception as e:
            print(f"General prices error: {e}")
            return None

    async def generate_complaint_confirmation(self, complaint_text, phone):
        try:
            prompt = (
                "اكد استلام الشكوى بشكل ودي.\n"
                f"نص الشكوى: \"{complaint_text}\"\n"
                f"رقم الهاتف: {phone}\n"
                "رسالة قصيرة بالعربية شكر العميل على الشكوى."
            )
            return await self._generate_with_fallback(prompt)
        except Exception as e:
            print(f"Complaint confirmation error: {e}")
            return None
