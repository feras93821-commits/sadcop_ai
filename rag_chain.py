from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from llm_router import LLMRouter
import os
import shutil
import logging

logger = logging.getLogger(__name__)

DATA_DIR = "/app/data"
PERSIST_DIR = f"{DATA_DIR}/chroma_db"
os.makedirs(PERSIST_DIR, exist_ok=True)

# نموذج محلي خفيف ويدعم العربية
embeddings = HuggingFaceEmbeddings(
    model_name="paraphrase-multilingual-MiniLM-L12-v2",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

vectorstore = Chroma(persist_directory=PERSIST_DIR, embedding_function=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

prompt_template = ChatPromptTemplate.from_template("""
أنت مساعد رسمي ودقيق لفرع محروقات اللاذقية - الشركة السورية للبترول.

- استخدم فقط المعلومات الموجودة في السياق.
- إذا لم تكن متأكد أو المعلومة غير موجودة، قل: "عذراً، ما عندي هالمعلومة حالياً."
- جاوب باختصار وبأسلوب سوري طبيعي ولطيف.

المعلومات المتوفرة:
{context}

السؤال: {question}

الجواب:
""")

llm_router = LLMRouter()

def get_answer(question: str) -> str | None:
    try:
        docs = retriever.invoke(question)
        context = "\n\n".join([doc.page_content for doc in docs])

        if not context.strip():
            return None

        prompt = prompt_template.format(context=context, question=question)
        response = llm_router.get_response(prompt)
        return response.strip() if response else None

    except Exception as e:
        logger.error(f"RAG Error: {e}")
        return None
