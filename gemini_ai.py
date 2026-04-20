import google.generativeai as genai
import json
import re
from config import Config

class GeminiAI:
    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
        
        self.system_context = """أنت مساعد ذكي للشركة السورية للبترول - محروقات اللاذقية.
        
قواعد مهمة:
1. إذا سأل المستخدم عن سعر وقود محدد، رد ب JSON فقط: {"intent": "price_query", "fuel_type": "اسم الوقود"}
2. إذا أراد تقديم شكوى، رد ب JSON فقط: {"intent": "complaint_start"}
3. إذا كان يكمل شكوى، رد ب JSON فقط: {"intent": "complaint_text", "text": "نص الشكوى"}
4. إذا أرسل رقم هاتف، رد ب JSON فقط: {"intent": "phone_number", "phone": "الرقم"}
5. لأي استفسار آخر، رد بشكل طبيعي وودي.

أنواع الوقود المتاحة: بنزين، مازوت، غاز منزلي، غاز صناعي"""

    async def analyze_intent(self, user_message, conversation_context=None):
        """تحليل نية المستخدم وإرجاع JSON"""
        try:
            context = self.system_context
            if conversation_context:
                context += f"\n\nسياق المحادثة الحالي: {conversation_context}"
            
            prompt = f"""{context}

رسالة المستخدم: "{user_message}"

حدد النية ورد ب JSON فقط بدون أي نص إضافي:"""
            
            response = await self.model.generate_content_async(prompt)
            text = response.text.strip()
            
            # استخراج JSON من الرد
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            # إذا لم يكن JSON، فهو رد عادي
            return {"intent": "general", "response": text}
            
        except Exception as e:
            return {"intent": "general", "response": user_message}
    
    async def get_response(self, user_message, db_prices=None, conversation_context=None):
        """الحصول على رد عادي من الذكاء الاصطناعي"""
        try:
            context = self.system_context
            
            if db_prices:
                prices_text = "\n\nالأسعار الحالية:\n"
                for price in db_prices:
                    prices_text += f"- {price.fuel_type}: {price.price_syp} ل.س / {price.price_usd} $\n"
                context += prices_text
            
            if conversation_context:
                context += f"\n\nسياق المحادثة: {conversation_context}"
            
            prompt = f"""{context}

المستخدم: "{user_message}"

قدم رداً ودياً ومفيداً بالعربية (بدون JSON):"""
            
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
            
        except Exception as e:
            return "عذراً، حدث خطأ في معالجة طلبك. يرجى المحاولة مرة أخرى."
    
    async def generate_price_response(self, fuel_type, price, exchange_rate):
        """توليد رد طبيعي عن السعر"""
        try:
            prompt = f"""أنت مساعد ودي. أخبر المستخدم عن سعر {fuel_type}:
- السعر بالدولار: {price.price_usd} $
- السعر بالليرة: {price.price_syp} ل.س
- سعر الصرف: {exchange_rate.usd_to_syp}

قدم رداً طبيعياً وودياً بالعربية (جملة أو جملتين فقط):"""
            
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except:
            return f"سعر {fuel_type} حالياً:\n💵 {price.price_usd} دولار\n🇸🇾 {price.price_syp} ليرة سورية"
    
    async def generate_complaint_confirmation(self, complaint_text, phone):
        """توليد رسالة تأكيد للشكوى"""
        try:
            prompt = f"""أكد للمستخدم استلام شكواه. نص الشكوى: "{complaint_text}"
رقم الهاتف: {phone}
اكتب رسالة ودية قصيرة بالعربية تؤكد استلام الشكوى وتخبره بأن الإدارة ستتواصل معه."""
            
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except:
            return "✅ تم استلام شكواك بنجاح! سيتم مراجعتها والتواصل معك في أقرب وقت."
