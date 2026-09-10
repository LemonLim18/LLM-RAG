# Chunking Strategy
from langchain_experimental.text_splitter import SemanticChunker
# LangChain Integration with Ollama Embeddings 
from langchain_ollama import OllamaEmbeddings
# LangChain Integration with Chroma Vector Store
from langchain_chroma import Chroma
# LangChain Integration with Ollama LLM
from langchain_ollama import ChatOllama

# GLOBAL VARIABLES
OLLAMA_URL = "http://192.168.1.8:11434"

# Document Reading
with open("original.txt", "r") as f:
    text = f.read()

# Specify Embedding Model
embeddings = OllamaEmbeddings(
    model = "nomic-embed-text",
    base_url = OLLAMA_URL
)

# Creation of Semantic Splitter using the specified embedding model
semantic_splitter = SemanticChunker(
    embeddings
)

# Creation of LLM using specified model
llm = ChatOllama(
    model = "qwen2.5:1.5b",
    base_url = OLLAMA_URL
)

# Creation of Chroma Vector Store
vectorstore = Chroma(
    collection_name = "network_docs",
    embedding_function = embeddings,
    persist_directory = "./chroma_db"
)


# Result of the documents generated from semantic splitting
documents = semantic_splitter.create_documents(
    [text]
)

# Storing of documents in Chroma Vector Store with embedding models
vectorstore.add_documents(documents)

for i, document in enumerate(documents):
    print(f"\n--- CHUNK {i+1} ---\n")
    print(f"Characters: {len(document.page_content)}\n")
    print(document.page_content)
