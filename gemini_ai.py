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
            print("Google Gemini init failed: %s" % str(e))
            self.gemini_available = False
            self.gemini_model = None

        # Initialize Grok AI (xAI)
        self.grok_api_key = os.getenv("GROK_API_KEY", "")
        self.grok_available = bool(self.grok_api_key)
        if self.grok_available:
            print("Grok AI initialized successfully")
        else:
            print("Grok AI not configured (no GROK_API_KEY)")

        self.system_context = """انت مساعد ذكي ودي للشركة السورية للبترول - محروقات اللاذقية.

قواعد الرد:
- رد بشكل ودي ومفيد وقصير (1-3 جمل)
- اذا سأل عن موضوع خارج الشركة، رد بأدب انك تخصصك المحروقات والخدمات المتعلقة بها
- يمكنك التحادث بشكل عام لكن ارجع للموضوع بذكاء
- لا تستخدم JSON في الردود العادية
- استخدم الايموجي بشكل مناسب
- اذا سأل عن اسعار محددة، استخدم البيانات المقدمة فقط"""

    def _call_grok(self, prompt):
        """Call Grok AI API as fallback"""
        try:
            import requests
            import json

            headers = {
                "Authorization": "Bearer " + self.grok_api_key,
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
                print("Grok API error: %s - %s" % (str(response.status_code), response.text))
                return None

        except Exception as e:
            print("Grok call error: %s" % str(e))
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
                print("Gemini failed: %s" % str(e))

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
                prices_text = "\n\nالاسعار الحالية المتاحة:\n"
                for price in db_prices:
                    prices_text += "- " + price.fuel_type + ":\n"
                    prices_text += "  القديم: " + f"{price.price_syp:,.0f}" + " ل.س\n"
                    prices_text += "  الجديد: " + f"{price.price_syp_new:,.2f}" + " ل.س\n"
                    prices_text += "  دولار: " + str(price.price_usd) + " $\n"
                context += prices_text

            prompt = context + "\n\nالمستخدم: \"" + user_message + "\"\n\nقدم ردا طبيعيا ووديا بالعربية (فقرة قصيرة):"

            response = await self._generate_with_fallback(prompt)

            if response:
                return response
            else:
                raise Exception("Both AI models failed")

        except Exception as e:
            print("AI Response error: %s" % str(e))
            return "عذراً، حدث خطأ في معالجة طلبك. يمكنك سؤالي عن اسعار المحروقات او تقديم شكوى."

    async def generate_price_response(self, fuel_type, price, exchange_rate):
        """توليد رد طبيعي عن السعر المحدد"""
        try:
            ex_rate_value = exchange_rate.usd_to_syp if exchange_rate else 15000

            prompt = (
                "اخبر المستخدم عن سعر " + fuel_type + ":\n"
                "- السعر بالدولار: " + str(price.price_usd) + " $\n"
                "- السعر بالليرة السورية (القديمة): " + f"{price.price_syp:,.0f}" + " ل.س\n"
                "- السعر بالليرة السورية (الجديدة): " + f"{price.price_syp_new:,.2f}" + " ل.س\n"
                "- سعر الصرف: " + str(ex_rate_value) + "\n\n"
                "رد طبيعي ودي بالعربية (جملة او جملتين):"
            )

            response = await self._generate_with_fallback(prompt)

            if response:
                return response
            else:
                raise Exception("Both AI models failed")

        except Exception as e:
            print("Price response error: %s" % str(e))
            return (
                "سعر " + fuel_type + " حالياً:\n"
                "دولار: " + str(price.price_usd) + "\n"
                "ل.س (قديم): " + f"{price.price_syp:,.0f}" + "\n"
                "ل.س (جديد): " + f"{price.price_syp_new:,.2f}"
            )

    async def generate_general_prices_response(self, prices, exchange_rate):
        """توليد رد عن جميع الاسعار عند السؤال العام"""
        try:
            ex_rate_value = exchange_rate.usd_to_syp if exchange_rate else 15000

            prices_list = "\n".join([
                "- " + p.fuel_type + ": " + f"{p.price_syp:,.0f}" + " ل.س (قديم) / " + f"{p.price_syp_new:,.2f}" + " ل.س (جديد) / " + str(p.price_usd) + " $"
                for p in prices
            ])

            prompt = (
                "المستخدم يسأل عن اسعار المحروقات بشكل عام.\n"
                "الاسعار الحالية:\n" + prices_list + "\n\n"
                "سعر الصرف: 1 دولار = " + str(ex_rate_value) + " ليرة سورية (القديمة)\n\n"
                "قدم جواباً ودياً يوضح جميع الاسعار المتاحة (فقرة قصيرة بالعربية):"
            )

            response = await self._generate_with_fallback(prompt)

            if response:
                return response
            else:
                raise Exception("Both AI models failed")

        except Exception as e:
            print("General prices error: %s" % str(e))
            ex_rate_value = exchange_rate.usd_to_syp if exchange_rate else 15000
            prices_text = "\n".join([
                "- " + p.fuel_type + ": " + f"{p.price_syp:,.0f}" + " ل.س (قديم) / " + f"{p.price_syp_new:,.2f}" + " ل.س (جديد) / " + str(p.price_usd) + " $"
                for p in prices
            ])
            return (
                "الاسعار الحالية:\n" + prices_text + "\n\n"
                "سعر الصرف: 1 دولار = " + str(ex_rate_value) + " ليرة سورية"
            )

    async def generate_complaint_confirmation(self, complaint_text, phone):
        """توليد رسالة تأكيد للشكوى"""
        try:
            prompt = (
                "اكد استلام الشكوى بشكل ودي.\n"
                "نص الشكوى: \"" + complaint_text + "\"\n"
                "رقم الهاتف: " + phone + "\n\n"
                "رسالة قصيرة بالعربية شكر العميل على الشكوى:"
            )

            response = await self._generate_with_fallback(prompt)

            if response:
                return response
            else:
                raise Exception("Both AI models failed")

        except Exception as e:
            print("Complaint confirmation error: %s" % str(e))
            return (
                "تم استلام شكواك بنجاح!\n\n"
                "سيتم مراجعتها والتواصل معك على الرقم: " + phone + "\n\n"
                "شكراً لتواصلك معنا"
            )
