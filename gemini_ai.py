import google.generativeai as genai
import json
import re
from config import Config

class GeminiAI:
    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
        
        self.system_context = """أنت مساعد ذكي ودي للشركة السورية للبترول - محروقات اللاذقية.
        
قواعد الرد:
- رد بشكل ودي ومفيد وقصير
- إذا سأل عن موضوع خارج الشركة، رد بأدب أنك تخصصك المحروقات والخدمات المتعلقة بها
- يمكنك التحادث بشكل عام لكن ارجع للموضوع بذكاء
- لا تستخدم JSON في الردود العادية
- استخدم الإيموجي بشكل مناسب"""

    async def analyze_intent(self, user_message):
        """تحليل نية المستخدم فقط - لا توليد رد"""
        try:
            prompt = f"""حدد نية المستخدم من الرسالة التالية. رد بـ JSON فقط:
{{
    "intent": "price_query" أو "complaint_start" أو "general",
    "fuel_type": "اسم الوقود إذا كان intent=price_query" أو null,
    "confidence": رقم بين 0 و 1
}}

الرسالة: "{user_message}"

JSON فقط:"""
            
            response = await self.model.generate_content_async(prompt)
            text = response.text.strip()
            
            json_match = re.search(r'\{{.*\}}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            return {"intent": "general", "fuel_type": None, "confidence": 0.5}
            
        except Exception as e:
            print(f"Intent analysis error: {e}")
            return {"intent": "general", "fuel_type": None, "confidence": 0.5}
    
    async def get_response(self, user_message, db_prices=None):
        """الحصول على رد عادي من الذكاء الاصطناعي"""
        try:
            context = self.system_context
            
            if db_prices:
                prices_text = "\n\nالأسعار الحالية المتاحة:\n"
                for price in db_prices:
                    prices_text += f"- {price.fuel_type}: {price.price_syp} ل.س / {price.price_usd} $\n"
                context += prices_text
            
            prompt = f"""{context}

المستخدم: "{user_message}"

قدم رداً طبيعياً وودياً بالعربية (فقرة قصيرة):"""
            
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
            
        except Exception as e:
            print(f"AI Response error: {e}")
            return "عذراً، حدث خطأ في معالجة طلبك. يمكنك سؤالي عن أسعار المحروقات أو تقديم شكوى."
    
    async def generate_price_response(self, fuel_type, price, exchange_rate):
        """توليد رد طبيعي عن السعر"""
        try:
            prompt = f"""أخبر المستخدم عن سعر {fuel_type}:
- السعر بالدولار: {price.price_usd} $
- السعر بالليرة: {price.price_syp} ل.س
- سعر الصرف: {exchange_rate.usd_to_syp}

رد طبيعي ودي بالعربية (جملة أو جملتين):"""
            
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except:
            return f"⛽ سعر {fuel_type} حالياً:\n💵 {price.price_usd} دولار\n🇸🇾 {price.price_syp} ليرة سورية\n\n💱 سعر الصرف: {exchange_rate.usd_to_syp}"
    
    async def generate_complaint_confirmation(self, complaint_text, phone):
        """توليد رسالة تأكيد للشكوى"""
        try:
            prompt = f"""أكد استلام الشكوى بشكل ودي. نص الشكوى: "{complaint_text}"
رقم الهاتف: {phone}
رسالة قصيرة بالعربية:"""
            
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except:
            return "✅ تم استلام شكواك بنجاح! سيتم مراجعتها والتواصل معك قريباً."
