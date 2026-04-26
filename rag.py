from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import os

# إعداد المجلد
DATA_PATH = "data"

# تأكد من وجود المجلد
if not os.path.exists(DATA_PATH):
    os.makedirs(DATA_PATH)
    print(f"⚠️ مجلد {DATA_PATH}/ غير موجود، تم إنشاؤه فارغاً")
    print("   أضف ملفات .md داخله ثم شغّل هذا الملف مرة أخرى.")
    # لا نوقف التشغيل، لكن vectorstore سيكون فارغاً

# 1. تحميل كل الملفات من مجلد data
if os.path.exists(DATA_PATH) and any(f.endswith('.md') for f in os.listdir(DATA_PATH)):
    loader = DirectoryLoader(
        DATA_PATH,
        glob="*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    documents = loader.load()
else:
    documents = []
    print("⚠️ لا توجد ملفات .md في مجلد data/")

# 2. تقسيم النصوص لقطع صغيرة
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100
)

chunks = text_splitter.split_documents(documents) if documents else []

# 3. إعداد نظام البحث (Vector Store)
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

if chunks:
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="chroma_db"
    )
    print(f"✅ تم تحميل {len(chunks)} قطعة من المعلومات بنجاح")
    print("✅ تم إنشاء قاعدة بيانات الـ RAG")
else:
    # إنشاء vectorstore فارغ
    vectorstore = Chroma(
        persist_directory="chroma_db",
        embedding_function=embeddings
    )
    print("⚠️ قاعدة بيانات RAG فارغة - أضف ملفات .md في data/")
