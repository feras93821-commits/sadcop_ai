from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import os

# إعداد المجلد
DATA_PATH = "data"

# 1. تحميل كل الملفات من مجلد data
loader = DirectoryLoader(
    DATA_PATH,
    glob="*.md",
    loader_cls=TextLoader,
    loader_kwargs={"encoding": "utf-8"}
)

documents = loader.load()

# 2. تقسيم النصوص لقطع صغيرة
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100
)

chunks = text_splitter.split_documents(documents)

# 3. إعداد نظام البحث (Vector Store)
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="chroma_db"
)

print(f"✅ تم تحميل {len(chunks)} قطعة من المعلومات بنجاح")
print("✅ تم إنشاء قاعدة بيانات الـ RAG")
