import os
import google.generativeai as genai
from config import Config

class GeminiAI:
    def __init__(self):
        # Initialize Google Gemini
        try:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            self.gemini_available = True
            print("Google Gemini initialized successfully")
        except Exception as e:
            print("Google Gemini init failed: " + str(e))
            self.gemini_available = False
            self.gemini_model = None

        # Initialize Grok AI (xAI)
        self.grok_api_key = os.getenv("GROK_API_KEY", "")
        self.grok_available = bool(self.grok_api_key)
        if self.grok_available:
            print("Grok AI initialized successfully")
        else:
            print("Grok AI not configured (no GROK_API_KEY)")

        self.system_context = """أنت مساعد ذكي ودي للشركة السورية للبترول - محروقات اللاذقية.

قواعد الرد:
- رد بشكل ودي ومفيد وقصير (1-3 جمل)
- إذا سأل عن موضوع خارج الشركة، رد بأدب أنك تخصصك المحروقات والخدمات المتعلقة بها
- يمكنك التحادث بشكل عام لكن ارجع للموضوع بذكاء
- لا تستخدم JSON في الردود العادية
- استخدم الإيموجي بشكل مناسب
- إذا سأل عن أسعار محددة، استخدم البيانات المقدمة فقط"""

    def _call_grok(self, prompt):
        """Call Grok AI API as fallback"""
        try:
            import requests
            import json

            headers = {
                "Authorization": f"Bearer {self.grok_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "grok-2-latest",
                "messages": [
                    {"role": "system", "content": self.system_context},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }

            response = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                print(f"Grok API error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"Grok call error: {e}")
            return None

    async def _generate_with_fallback(self, prompt):
        """Generate response using Gemini first, fallback to Grok"""

        # Try Google Gemini first
        if self.gemini_available:
            try:
                response = self.gemini_model.generate_content(prompt)
                if response and response.text:
                    print("Response from: Google Gemini")
                    return response.text.strip()
            except Exception as e:
                print(f"Gemini failed: {e}")

        # Fallback to Grok AI
        if self.grok_available:
            print("Falling back to Grok AI...")
            grok_response = self._call_grok(prompt)
            if grok_response:
                print("Response from: Grok AI")
                return grok_response

        # Both failed
        return None

    async def get_response(self, user_message, db_prices=None):
        """الحصول على رد عادي من الذكاء الاصطناعي"""
        try:
            context = self.system_context

            if db_prices:
                prices_text = "

الأسعار الحالية المتاحة:
"
                for price in db_prices:
                    prices_text += f"- {price.fuel_type}:
"
                    prices_text += f"  القديم: {price.price_syp:,.0f} ل.س
"
                    prices_text += f"  الجديد: {price.price_syp_new:,.2f} ل.س
"
                    prices_text += f"  دولار: {price.price_usd} $
"
                context += prices_text

            prompt = f"""{context}

المستخدم: "{user_message}"

قدم رداً طبيعياً وودياً بالعربية (فقرة قصيرة):"""

            response = await self._generate_with_fallback(prompt)

            if response:
                return response
            else:
                raise Exception("Both AI models failed")

        except Exception as e:
            print("AI Response error: " + str(e))
            return "عذراً، حدث خطأ في معالجة طلبك. يمكنك سؤالي عن أسعار المحروقات أو تقديم شكوى."

    async def generate_price_response(self, fuel_type, price, exchange_rate):
        """توليد رد طبيعي عن السعر المحدد"""
        try:
            ex_rate_value = exchange_rate.usd_to_syp if exchange_rate else 15000

            prompt = f"""أخبر المستخدم عن سعر {fuel_type}:
- السعر بالدولار: {price.price_usd} $
- السعر بالليرة السورية (القديمة): {price.price_syp:,.0f} ل.س
- السعر بالليرة السورية (الجديدة): {price.price_syp_new:,.2f} ل.س
- سعر الصرف: {ex_rate_value}

رد طبيعي ودي بالعربية (جملة أو جملتين):"""

            response = await self._generate_with_fallback(prompt)

            if response:
                return response
            else:
                raise Exception("Both AI models failed")

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

            prices_list = "
".join([
                f"- {p.fuel_type}: {p.price_syp:,.0f} ل.س (قديم) / {p.price_syp_new:,.2f} ل.س (جديد) / {p.price_usd} $"
                for p in prices
            ])

            prompt = f"""المستخدم يسأل عن أسعار المحروقات بشكل عام.
الأسعار الحالية:
{prices_list}

سعر الصرف: 1 دولار = {ex_rate_value} ليرة سورية (القديمة)

قدم جواباً ودياً يوضح جميع الأسعار المتاحة (فقرة قصيرة بالعربية):"""

            response = await self._generate_with_fallback(prompt)

            if response:
                return response
            else:
                raise Exception("Both AI models failed")

        except Exception as e:
            print("General prices error: " + str(e))
            ex_rate_value = exchange_rate.usd_to_syp if exchange_rate else 15000
            prices_text = "
".join([
                f"• {p.fuel_type}: {p.price_syp:,.0f} ل.س (قديم) / {p.price_syp_new:,.2f} ل.س (جديد) / {p.price_usd} $"
                for p in prices
            ])
            return f"""الأسعار الحالية:
{prices_text}

💱 سعر الصرف: 1 دولار = {ex_rate_value} ليرة سورية"""

    async def generate_complaint_confirmation(self, complaint_text, phone):
        """توليد رسالة تأكيد للشكوى"""
        try:
            prompt = f"""أكد استلام الشكوى بشكل ودي.
نص الشكوى: "{complaint_text}"
رقم الهاتف: {phone}

رسالة قصيرة بالعربية شكر العميل على الشكوى:"""

            response = await self._generate_with_fallback(prompt)

            if response:
                return response
            else:
                raise Exception("Both AI models failed")

        except Exception as e:
            print("Complaint confirmation error: " + str(e))
            return f"تم استلام شكواك بنجاح!

سيتم مراجعتها والتواصل معك على الرقم: {phone}

شكراً لتواصلك معنا"
