from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import FastEmbedEmbeddings
import os

DATA_PATH = "data"

if not os.path.exists(DATA_PATH):
    os.makedirs(DATA_PATH)
    print(f"⚠️ مجلد {DATA_PATH}/ غير موجود، تم إنشاؤه فارغاً")

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

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100
)

chunks = text_splitter.split_documents(documents) if documents else []

embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

if chunks:
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="chroma_db"
    )
    print(f"✅ تم تحميل {len(chunks)} قطعة من المعلومات بنجاح")
else:
    vectorstore = Chroma(
        persist_directory="chroma_db",
        embedding_function=embeddings
    )
    print("⚠️ قاعدة بيانات RAG فارغة - أضف ملفات .md في data/")
