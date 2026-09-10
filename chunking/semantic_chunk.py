import os
from dotenv import load_dotenv
from langchain_experimental.text_splitter import SemanticChunker
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

# FILE READING
with open("original.txt", "r", encoding="utf-8") as file:
    text = file.read()


# CREATE GEMINI EMBEDDING MODEL
embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001"
)


# CREATE SEMANTIC CHUNKER
semantic_splitter = SemanticChunker(
    embeddings
)


# CREATE DOCUMENTS
documents = semantic_splitter.create_documents(
    [text]
)


# PRINT RESULTS
for i, document in enumerate(documents):
    print(f"\n--- CHUNK {i + 1} ---")
    print(f"Characters: {len(document.page_content)}")
    print(document.page_content)