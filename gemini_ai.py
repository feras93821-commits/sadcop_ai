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
        """توليد رد طبيعي عن السعر المحدد"""
        try:
            prompt = f"""أخبر المستخدم عن سعر {fuel_type}:
- السعر بالدولار: {price.price_usd} $
- السعر بالليرة: {price.price_syp} ل.س
- سعر الصرف: {exchange_rate.usd_to_syp}

رد طبيعي ودي بالعربية (جملة أو جملتين):"""
            
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except:
            return f"⛽ سعر {fuel_type} حالياً:\n💵 {price.price_usd} دولار\n🇸🇾 {price.price_syp} ليرة سورية"
    
    async def generate_general_prices_response(self, prices, exchange_rate):
        """توليد رد عن جميع الأسعار عند السؤال العام"""
        try:
            prices_list = "\n".join([f"- {p.fuel_type}: {p.price_syp} ل.س / {p.price_usd} $" for p in prices])
            
            prompt = f"""المستخدم يسأل عن أسعار المحروقات بشكل عام.
الأسعار الحالية:
{prices_list}

سعر الصرف: 1 دولار = {exchange_rate.usd_to_syp} ليرة سورية

قدم جواباً ودياً يوضح جميع الأسعار المتاحة (فقرة قصيرة بالعربية):"""
            
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except:
            prices_text = "\n".join([f"• {p.fuel_type}: {p.price_syp} ل.س / {p.price_usd} $" for p in prices])
            return f"💰 *الأسعار الحالية:*\n{prices_text}\n\n💱 سعر الصرف: 1 دولار = {exchange_rate.usd_to_syp} ليرة سورية"
    
    async def generate_complaint_confirmation(self, complaint_text, phone):
        """توليد رسالة تأكيد للشكوى"""
        try:
            prompt = f"""أكد استلام الشكوى بشكل ودي.
نص الشكوى: "{complaint_text}"
رقم الهاتف: {phone}

رسالة قصيرة بالعربية شكر العميل على الشكوى:"""
            
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except:
            return f"✅ تم استلام شكواك بنجاح! 📝\n\nسيتم مراجعتها والتواصل معك على الرقم: {phone}\n\nشكراً لتواصلك معنا 🙏"
