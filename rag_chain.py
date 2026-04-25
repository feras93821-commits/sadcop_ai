from rag import vectorstore
from llm_router import LLMRouter
from langchain_core.prompts import ChatPromptTemplate

# تحميل الـ Router
router = LLMRouter()

# إعداد الـ Retriever (البحث في المعلومات)
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

# قالب الـ Prompt
prompt_template = ChatPromptTemplate.from_template("""
أنت مساعد رسمي للشركة السورية للبترول - فرع محروقات اللاذقية.
استخدم فقط المعلومات الموجودة أدناه للإجابة.
جاوب بلباقة وبلهجة سورية طبيعية.

المعلومات المتوفرة:
{context}

السؤال: {question}

الجواب:
""")

# دالة الإجابة النهائية
def get_answer(question: str) -> str:
    # أولاً نبحث في قاعدة المعلومات
    docs = retriever.invoke(question)
    context = "\n\n".join( )
    
    # نركب الـ Prompt كامل
    prompt = prompt_template.format(context=context, question=question)
    
    # نطلب الجواب من الراوتر
    answer = router.get_response(prompt)
    
    return answer
