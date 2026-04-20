import google.generativeai as genai
from config import Config

class GeminiAI:
    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # System prompt for context
        self.system_context = """
        أنت مساعد ذكي للشركة السورية للبترول - محروقات اللاذقية.
        تساعد العملاء في:
        - الاستفسار عن أسعار المحروقات (بنزين، مازوت، غاز منزلي، غاز صناعي)
        - تقديم الشكاوى والاقتراحات
        - المعلومات العامة عن الشركة
        
        قدم إجابات ودية ومفيدة باللغة العربية.
        """
    
    async def get_response(self, user_message, db_prices=None):
        try:
            # Add prices context if available
            context = self.system_context
            if db_prices:
                prices_text = "\nالأسعار الحالية:\n"
                for price in db_prices:
                    prices_text += f"- {price.fuel_type}: {price.price_syp} ل.س / {price.price_usd} $\n"
                context += prices_text
            
            prompt = f"{context}\n\nالمستخدم: {user_message}\n\nالرد:"
            
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            return f"عذراً، حدث خطأ في معالجة طلبك. يرجى المحاولة مرة أخرى. (Error: {str(e)})"
