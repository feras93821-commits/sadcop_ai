from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import os
import shutil
import logging

logger = logging.getLogger(__name__)

# المسارات
DATA_PATH = "/app/data"
PERSIST_DIR = "/app/data/chroma_db"

os.makedirs(DATA_PATH, exist_ok=True)
os.makedirs(PERSIST_DIR, exist_ok=True)

# نموذج embedding محلي خفيف ويدعم العربية
embeddings = HuggingFaceEmbeddings(
    model_name="paraphrase-multilingual-MiniLM-L12-v2",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

def rebuild_chroma():
    print("🔄 جاري إعادة بناء قاعدة البيانات RAG...")

    # التحقق من وجود ملفات .md
    md_files = [f for f in os.listdir(DATA_PATH) if f.endswith('.md')]
    print(f"📄 عدد ملفات .md المكتشفة: {len(md_files)} → {md_files}")

    if not md_files:
        print("⚠️ لا توجد ملفات .md في مجلد data/")
        print("   تأكد من رفع ملفاتك داخل مجلد data/ على GitHub")
        # إنشاء vectorstore فارغ
        Chroma(persist_directory=PERSIST_DIR, embedding_function=embeddings)
        print("✅ تم إنشاء chroma_db فارغة")
        return

    # تحميل المستندات
    loader = DirectoryLoader(
        DATA_PATH,
        glob="*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    documents = loader.load()
    print(f"📚 تم تحميل {len(documents)} وثيقة")

    # تقسيم النصوص
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100
    )
    chunks = text_splitter.split_documents(documents)
    print(f"✂️ تم تقسيم إلى {len(chunks)} قطعة")

    # بناء قاعدة البيانات
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIR
    )
    print(f"✅ تم بناء chroma_db بنجاح مع {len(chunks)} قطعة!")

if __name__ == "__main__":
    rebuild_chroma()
