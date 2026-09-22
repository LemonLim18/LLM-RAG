from langchain_chroma import Chroma
from .config import CHROMA_DIR,CHROMA_COLLECTION
from .embeddings import embeddings

def get_vectorstore():
    return Chroma(collection_name=CHROMA_COLLECTION,persist_directory=str(CHROMA_DIR),embedding_function=embeddings)
