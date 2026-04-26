from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from llm_router import LLMRouter
import os

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY")
)

vectorstore = Chroma(
    persist_directory="chroma_db",
    embedding_function=embeddings
)
...

retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

prompt_template = ChatPromptTemplate.from_template("""
أنت مساعد رسمي للشركة السورية للبترول - فرع محروقات اللاذقية.
استخدم المعلومات الموجودة فقط للإجابة.
جاوب بلباقة وبأسلوب سوري طبيعي.

المعلومات المتوفرة:
{context}

السؤال: {question}

الجواب:
""")

llm_router = LLMRouter()

def get_answer(question: str) -> str:
    try:
        docs = retriever.invoke(question)
        context = "\n\n".join([doc.page_content for doc in docs])

        prompt = prompt_template.format(context=context, question=question)
        response = llm_router.get_response(prompt)

        return response if response else "عذراً، ما قدرت أجاوبك حالياً. جرب مرة ثانية."

    except Exception as e:
        print(f"خطأ في RAG: {e}")
        return "عذراً، النظام مشغول حالياً. جرب بعد شوي."
