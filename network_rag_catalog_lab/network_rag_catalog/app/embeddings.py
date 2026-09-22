# Embeddings configuration for the ChromaDB config
from langchain_ollama import OllamaEmbeddings
from .config import OLLAMA_EMBED_MODEL
embeddings=OllamaEmbeddings(model=OLLAMA_EMBED_MODEL)
