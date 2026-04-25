from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from llm_router import llm_router

# تحميل قاعدة البيانات
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vectorstore = Chroma(
    persist_directory="chroma_db",
    embedding_function=embeddings
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

# Prompt للبوت
prompt_template = ChatPromptTemplate.from_template(
    """أنت مساعد رسمي مهذب للشركة السورية للبترول - فرع محروقات اللاذقية.

استخدم المعلومات التالية فقط للإجابة:
{context}

السؤال: {question}

جاوب باللهجة السورية الطبيعية، بلباقة واختصار، وكن مفيداً.
إذا ما كان عندك معلومة دقيقة، قول إنك راح تشيك أحدث المعلومات.
"""
)

def get_answer(question: str) -> str:
    try:
        # استرجاع المعلومات المتعلقة
        docs = retriever.invoke(question)
        context = "\n\n".join([doc.page_content for doc in docs])

        # إعداد الـ prompt الكامل
        prompt = prompt_template.format(context=context, question=question)

        # الحصول على الرد من الـ Router
        response = llm_router.get_response(prompt)
        
        return response

    except Exception as e:
        print(f"RAG Error: {e}")
        return "عذراً، فيه مشكلة بالنظام حالياً. جرب مرة ثانية بعد شوي."
