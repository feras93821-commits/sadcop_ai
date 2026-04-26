from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from llm_router import LLMRouter
import os
import shutil

embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

PERSIST_DIR = "chroma_db"

# إذا كانت قاعدة البيانات معطوبة (مثلاً من embedding قديم)، احذفها وأعد البناء
def _init_vectorstore():
    try:
        vs = Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=embeddings
        )
        # اختبار سريع
        vs.similarity_search("test", k=1)
        return vs
    except Exception as e:
        print(f"⚠️ chroma_db corrupted or incompatible: {e}")
        print("🗑️ Deleting and rebuilding chroma_db...")
        if os.path.exists(PERSIST_DIR):
            shutil.rmtree(PERSIST_DIR)
        return Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=embeddings
        )

vectorstore = _init_vectorstore()
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

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

        if response:
            return response
        else:
            print("⚠️ All LLMs failed, returning fallback")
            return None  # Signal to bot.py to use fallback

    except Exception as e:
        print(f"❌ خطأ في RAG: {e}")
        return None  # Signal to bot.py to use fallback
