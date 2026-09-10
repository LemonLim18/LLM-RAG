"""
adaptive_rag.py

ADAPTIVE RAG SYSTEM

Pipeline:

    Document
        ↓
    Clean / Normalize
        ↓
    Structure Detection
        ↓
    Adaptive Chunking
        ↓
    Chunk Validation
        ↓
    Metadata
        ↓
    Ollama Embeddings
        ↓
    ChromaDB
        ↓
    Retrieval
        ↓
    Ollama LLM
        ↓
    Answer

Chunking strategy:

1. Structure-aware
   Used when reliable headings/sections are detected.

2. Paragraph-aware
   Used when the document has meaningful paragraphs but
   weak or missing heading structure.

3. Semantic refinement
   Used when paragraphs/sections are too large or contain
   multiple semantic topics.

4. Recursive size fallback
   Used when semantic splitting still produces chunks
   that are too large.

Important:

This is an adaptive baseline, not a claim that one algorithm
is universally optimal for every document.
"""

from pathlib import Path
import re
from typing import List, Dict

from httpx2 import query
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter


# ============================================================
# 1. CONFIGURATION
# ============================================================

OLLAMA_URL = "http://192.168.1.8:11434"

EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "qwen2.5:1.5b"

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"

CHROMA_DIR = BASE_DIR / "chroma_db"

COLLECTION_NAME = "adaptive_rag"

RELEVANCE_THRESHOLD = 0.9

# Approximate maximum character size.
#
# This is deliberately conservative because characters are
# not exactly equivalent to tokens.
MAX_CHUNK_CHARS = 1800

# Minimum useful chunk size.
MIN_CHUNK_CHARS = 150

# Overlap for the final size-based fallback.
CHUNK_OVERLAP = 200

TOP_K = 4


# ============================================================
# 2. LOAD MODELS
# ============================================================

print("=" * 70)
print("ADAPTIVE RAG SYSTEM")
print("=" * 70)

print(f"\nOllama server    : {OLLAMA_URL}")
print(f"Embedding model  : {EMBEDDING_MODEL}")
print(f"LLM model        : {LLM_MODEL}")


embeddings = OllamaEmbeddings(
    model=EMBEDDING_MODEL,
    base_url=OLLAMA_URL
)

llm = ChatOllama(
    model=LLM_MODEL,
    base_url=OLLAMA_URL,
    temperature=0
)


# ============================================================
# 3. DOCUMENT CLEANING
# ============================================================

def clean_text(text: str) -> str:
    """
    Basic document normalization.

    This intentionally does NOT aggressively rewrite the
    document because we want to preserve meaning and structure.
    """

    # Normalize line endings.
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Replace tabs with spaces.
    text = text.replace("\t", " ")

    # Remove excessive spaces.
    text = re.sub(r"[ ]{2,}", " ", text)

    # Reduce excessive blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ============================================================
# 4. STRUCTURE DETECTION
# ============================================================

def detect_headings(text: str) -> List[Dict]:
    """
    Detect common heading patterns.

    Supports examples such as:

        # Introduction

        ## Background

        1. Introduction

        1.1 System Design

        CHAPTER 1

        INTRODUCTION

    This is intentionally heuristic.
    """

    headings = []

    lines = text.splitlines()

    for index, line in enumerate(lines):

        stripped = line.strip()

        if not stripped:
            continue

        # ----------------------------------------------------
        # Markdown heading
        # ----------------------------------------------------

        if re.match(r"^#{1,6}\s+\S+", stripped):

            headings.append(
                {
                    "line_index": index,
                    "text": stripped,
                    "type": "markdown"
                }
            )

            continue

        # ----------------------------------------------------
        # Numbered heading
        #
        # Examples:
        #
        # 1. Introduction
        # 2. Methodology
        # 2.1 Experimental Setup
        # ----------------------------------------------------

        if re.match(
            r"^\d+(?:\.\d+)*\.\s+\S+",
            stripped
        ):

            headings.append(
                {
                    "line_index": index,
                    "text": stripped,
                    "type": "numbered"
                }
            )

            continue

        # ----------------------------------------------------
        # Chapter heading
        # ----------------------------------------------------

        if re.match(
            r"^(CHAPTER|SECTION)\s+\d+",
            stripped,
            re.IGNORECASE
        ):

            headings.append(
                {
                    "line_index": index,
                    "text": stripped,
                    "type": "chapter"
                }
            )

            continue

        # ----------------------------------------------------
        # ALL CAPS heading
        #
        # Avoid treating long paragraphs as headings.
        # ----------------------------------------------------

        if (
            stripped.isupper()
            and len(stripped.split()) <= 12
            and len(stripped) <= 120
        ):

            headings.append(
                {
                    "line_index": index,
                    "text": stripped,
                    "type": "uppercase"
                }
            )

    return headings


# ============================================================
# 5. STRUCTURE QUALITY SCORE
# ============================================================

def calculate_structure_score(
    text: str,
    headings: List[Dict]
) -> float:
    """
    Estimate how trustworthy the document structure is.

    This is not machine learning.

    It is a practical heuristic used to decide which
    chunking strategy should be attempted.
    """

    lines = text.splitlines()

    if not lines:
        return 0.0

    non_empty_lines = [
        line.strip()
        for line in lines
        if line.strip()
    ]

    if not non_empty_lines:
        return 0.0

    score = 0.0

    # --------------------------------------------------------
    # Heading presence
    # --------------------------------------------------------

    heading_ratio = (
        len(headings)
        / max(len(non_empty_lines), 1)
    )

    if len(headings) >= 3:
        score += 0.45

    elif len(headings) >= 1:
        score += 0.25

    # --------------------------------------------------------
    # Paragraph quality
    # --------------------------------------------------------

    paragraphs = re.split(
        r"\n\s*\n",
        text
    )

    paragraphs = [
        p.strip()
        for p in paragraphs
        if p.strip()
    ]

    if len(paragraphs) >= 3:
        score += 0.25

    # --------------------------------------------------------
    # Excessively long lines can indicate poor extraction.
    # --------------------------------------------------------

    long_lines = sum(
        1
        for line in non_empty_lines
        if len(line) > 1000
    )

    if long_lines == 0:
        score += 0.20

    # --------------------------------------------------------
    # Reasonable heading density
    # --------------------------------------------------------

    if 0 < heading_ratio < 0.20:
        score += 0.10

    return min(score, 1.0)


# ============================================================
# 6. STRUCTURE-AWARE CHUNKING
# ============================================================

def structure_aware_chunk(
    text: str,
    headings: List[Dict]
) -> List[Document]:
    """
    Split document according to detected headings.

    Each heading becomes the beginning of a structural chunk.
    """

    lines = text.splitlines()

    chunks = []

    for i, heading in enumerate(headings):

        start_line = heading["line_index"]

        if i + 1 < len(headings):

            end_line = headings[
                i + 1
            ]["line_index"]

        else:

            end_line = len(lines)

        section_text = "\n".join(
            lines[start_line:end_line]
        ).strip()

        if not section_text:
            continue

        chunks.append(
            Document(
                page_content=section_text,
                metadata={
                    "chunk_method": "structure",
                    "heading": heading["text"],
                    "heading_type": heading["type"],
                    "section_index": i + 1
                }
            )
        )

    return chunks


# ============================================================
# 7. PARAGRAPH-AWARE CHUNKING
# ============================================================

def paragraph_chunk(
    text: str
) -> List[Document]:
    """
    Use blank-line-separated paragraphs as the primary units.
    """

    paragraphs = re.split(
        r"\n\s*\n",
        text
    )

    paragraphs = [
        p.strip()
        for p in paragraphs
        if p.strip()
    ]

    documents = []

    for index, paragraph in enumerate(paragraphs):

        documents.append(
            Document(
                page_content=paragraph,
                metadata={
                    "chunk_method": "paragraph",
                    "paragraph_index": index
                }
            )
        )

    return documents


# ============================================================
# 8. SEMANTIC REFINEMENT
# ============================================================

def semantic_refine(
    documents: List[Document],
    embeddings
) -> List[Document]:
    """
    Apply SemanticChunker only to documents that are too large.

    Small chunks are preserved.

    This is the key difference from simply running
    SemanticChunker over the entire document.
    """

    semantic_splitter = SemanticChunker(
        embeddings,
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=90
    )

    final_documents = []

    for doc in documents:

        if len(doc.page_content) <= MAX_CHUNK_CHARS:

            final_documents.append(doc)

            continue

        # ----------------------------------------------------
        # Only large documents get semantic refinement.
        # ----------------------------------------------------

        semantic_chunks = semantic_splitter.create_documents(
            [doc.page_content]
        )

        for index, chunk in enumerate(
            semantic_chunks
        ):

            metadata = dict(
                doc.metadata
            )

            metadata.update(
                {
                    "chunk_method":
                        "semantic_refinement",
                    "semantic_index":
                        index
                }
            )

            final_documents.append(
                Document(
                    page_content=chunk.page_content,
                    metadata=metadata
                )
            )

    return final_documents


# ============================================================
# 9. SIZE FALLBACK
# ============================================================

def size_fallback(
    documents: List[Document]
) -> List[Document]:
    """
    Ensure no chunk remains excessively large.

    RecursiveCharacterTextSplitter is used only as the
    final safety mechanism.
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=MAX_CHUNK_CHARS,
        chunk_overlap=CHUNK_OVERLAP,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
            ""
        ]
    )

    final_documents = []

    for doc in documents:

        if len(doc.page_content) <= MAX_CHUNK_CHARS:

            final_documents.append(doc)

            continue

        smaller_chunks = splitter.split_documents(
            [doc]
        )

        for index, chunk in enumerate(
            smaller_chunks
        ):

            metadata = dict(
                doc.metadata
            )

            metadata.update(
                {
                    "chunk_method":
                        "recursive_fallback",
                    "fallback_index":
                        index
                }
            )

            final_documents.append(
                Document(
                    page_content=chunk.page_content,
                    metadata=metadata
                )
            )

    return final_documents


# ============================================================
# 10. REMOVE TINY / BAD CHUNKS
# ============================================================

def validate_chunks(
    documents: List[Document]
) -> List[Document]:
    """
    Remove extremely small chunks.

    Very tiny chunks often contain headings or extraction
    artifacts without enough semantic context.
    """

    validated = []

    for doc in documents:

        text = doc.page_content.strip()

        if len(text) < MIN_CHUNK_CHARS:

            continue

        validated.append(
            doc
        )

    return validated


# ============================================================
# 11. ADD FINAL METADATA
# ============================================================

def add_final_metadata(
    documents: List[Document],
    source_name: str
) -> List[Document]:
    """
    Add consistent metadata to every final chunk.
    """

    final_documents = []

    for index, doc in enumerate(
        documents
    ):

        metadata = dict(
            doc.metadata
        )

        metadata.update(
            {
                "source": source_name,
                "chunk_id": index,
                "chunk_size":
                    len(doc.page_content)
            }
        )

        final_documents.append(
            Document(
                page_content=doc.page_content,
                metadata=metadata
            )
        )

    return final_documents


# ============================================================
# 12. ADAPTIVE CHUNKING ENGINE
# ============================================================

def adaptive_chunk_document(
    text: str,
    source_name: str
) -> List[Document]:
    """
    Main adaptive chunking controller.
    """

    print("\n" + "=" * 70)
    print("ADAPTIVE CHUNKING")
    print("=" * 70)

    # --------------------------------------------------------
    # Clean
    # --------------------------------------------------------

    text = clean_text(text)

    # --------------------------------------------------------
    # Analyze structure
    # --------------------------------------------------------

    headings = detect_headings(
        text
    )

    structure_score = (
        calculate_structure_score(
            text,
            headings
        )
    )

    print(
        f"\nDetected headings : "
        f"{len(headings)}"
    )

    print(
        f"Structure score    : "
        f"{structure_score:.2f}"
    )

    # --------------------------------------------------------
    # Choose initial strategy
    # --------------------------------------------------------

    if structure_score >= 0.65:

        strategy = "structure"

        print(
            "Selected strategy : "
            "STRUCTURE-AWARE"
        )

        documents = structure_aware_chunk(
            text,
            headings
        )

    else:

        paragraphs = paragraph_chunk(
            text
        )

        # ----------------------------------------------------
        # Determine paragraph quality.
        # ----------------------------------------------------

        useful_paragraphs = [
            doc
            for doc in paragraphs
            if len(doc.page_content)
            >= MIN_CHUNK_CHARS
        ]

        if len(useful_paragraphs) >= 3:

            strategy = "paragraph"

            print(
                "Selected strategy : "
                "PARAGRAPH-AWARE"
            )

            documents = paragraphs

        else:

            strategy = "semantic"

            print(
                "Selected strategy : "
                "SEMANTIC"
            )

            semantic_splitter = SemanticChunker(
                embeddings,
                breakpoint_threshold_type="percentile",
                breakpoint_threshold_amount=90
            )

            documents = (
                semantic_splitter
                .create_documents(
                    [text]
                )
            )

            for doc in documents:

                doc.metadata[
                    "chunk_method"
                ] = "semantic"

    # --------------------------------------------------------
    # Semantic refinement
    # --------------------------------------------------------

    print(
        f"\nInitial chunks: "
        f"{len(documents)}"
    )

    documents = semantic_refine(
        documents,
        embeddings
    )

    print(
        f"After semantic refinement: "
        f"{len(documents)}"
    )

    # --------------------------------------------------------
    # Size fallback
    # --------------------------------------------------------

    documents = size_fallback(
        documents
    )

    print(
        f"After size fallback: "
        f"{len(documents)}"
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    documents = validate_chunks(
        documents
    )

    print(
        f"After validation: "
        f"{len(documents)}"
    )

    # --------------------------------------------------------
    # Final metadata
    # --------------------------------------------------------

    documents = add_final_metadata(
        documents,
        source_name
    )

    return documents


# ============================================================
# 13. PRINT CHUNK INFORMATION
# ============================================================

def print_chunks(
    documents: List[Document]
):
    """
    Display final chunks for debugging.
    """

    print("\n" + "=" * 70)
    print("FINAL CHUNKS")
    print("=" * 70)

    for index, doc in enumerate(
        documents
    ):

        method = doc.metadata.get(
            "chunk_method",
            "unknown"
        )

        heading = doc.metadata.get(
            "heading",
            "-"
        )

        print(
            f"\nChunk {index + 1:02d}"
        )

        print(
            f"Method  : {method}"
        )

        print(
            f"Size    : "
            f"{len(doc.page_content)} chars"
        )

        print(
            f"Heading : {heading}"
        )

        print(
            f"Preview : "
            f"{' '.join(doc.page_content.split())[:250]}..."
        )


# ============================================================
# 14. BUILD VECTOR DATABASE
# ============================================================

def build_vectorstore(
    documents: List[Document]
):
    """
    Create a clean Chroma collection and store the chunks.
    """

    print("\n" + "=" * 70)
    print("BUILDING CHROMA DATABASE")
    print("=" * 70)

    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(
            CHROMA_DIR
        )
    )

    # --------------------------------------------------------
    # Clean previous experimental collection.
    # --------------------------------------------------------

    try:

        vectorstore.delete_collection()

    except Exception:

        pass

    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(
            CHROMA_DIR
        )
    )

    # --------------------------------------------------------
    # Store documents.
    # --------------------------------------------------------

    vectorstore.add_documents(
        documents
    )

    print(
        f"\nStored chunks: "
        f"{len(documents)}"
    )

    print(
        f"Chroma directory: "
        f"{CHROMA_DIR}"
    )

    return vectorstore


# ============================================================
# 15. RETRIEVAL
# ============================================================

def retrieve(
    vectorstore,
    query: str,
    k: int = TOP_K
):
    """
    Retrieve the most relevant chunks.
    """

    results = (
        vectorstore
        .similarity_search_with_score(
            query,
            k=k
        )
    )

    relevant_results = [
        (doc, distance)
        for doc, distance in results
        if distance <= RELEVANCE_THRESHOLD
    ]

    return relevant_results


# ============================================================
# 16. DISPLAY RETRIEVAL
# ============================================================

def display_retrieval(
    query: str,
    results
):
    """
    Display retrieved chunks.
    """

    print("\n" + "=" * 70)
    print("RETRIEVAL")
    print("=" * 70)

    print(
        f"\nQuery:\n{query}"
    )

    for rank, (
        doc,
        distance
    ) in enumerate(
        results,
        start=1
    ):

        print(
            f"\nRank {rank}"
        )

        print(
            f"Distance : "
            f"{distance:.4f}"
        )

        print(
            f"Method   : "
            f"{doc.metadata.get('chunk_method')}"
        )

        print(
            f"Source   : "
            f"{doc.metadata.get('source')}"
        )

        print(
            f"Chunk ID : "
            f"{doc.metadata.get('chunk_id')}"
        )

        print(
            f"Heading  : "
            f"{doc.metadata.get('heading', '-')}"
        )

        print(
            "Text     : "
            f"{' '.join(doc.page_content.split())[:500]}..."
        )


# ============================================================
# 17. GENERATE ANSWER
# ============================================================

def generate_answer(
    query: str,
    results
):
    """
    Generate an answer only from relevant retrieved context.
    """

    # Safety check:
    # Never allow the LLM to answer without retrieved context.

    if not results:

        return (
            "I cannot find this information "
            "in the existing document."
        )

    context_parts = []

    for rank, (
        doc,
        distance
    ) in enumerate(
        results,
        start=1
    ):

        context_parts.append(
            f"""
--- CONTEXT {rank} ---
Source: {doc.metadata.get('source')}
Chunk: {doc.metadata.get('chunk_id')}
Heading: {doc.metadata.get('heading', '-')}
Content:
{doc.page_content}
"""
        )

    context = "\n".join(
        context_parts
    )

    prompt = f"""
You are a closed-book Retrieval-Augmented Generation (RAG) assistant.

IMPORTANT RULES:

1. You MUST answer using ONLY the information in the
   retrieved context below.

2. You MUST NOT use your own pretrained knowledge.

3. If the answer is not explicitly supported by the
   retrieved context, say:

   "I cannot find this information in the existing document."

4. Do NOT guess.

5. Do NOT provide an answer just because you know it
   from general knowledge.

User question:
{query}

Retrieved context:
{context}

Answer only from the retrieved context.
"""

    response = llm.invoke(
        prompt
    )

    return response.content


# ============================================================
# 18. MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # Select input document
    # --------------------------------------------------------

    document_path = (
        DATA_DIR
        / "network_test_document.txt"
    )

    if not document_path.exists():

        raise FileNotFoundError(
            f"\nDocument not found:\n"
            f"{document_path}"
        )

    # --------------------------------------------------------
    # Load document
    # --------------------------------------------------------

    text = document_path.read_text(
        encoding="utf-8"
    )

    print(
        f"\nDocument: "
        f"{document_path}"
    )

    print(
        f"Characters: "
        f"{len(text):,}"
    )

    # --------------------------------------------------------
    # Adaptive chunking
    # --------------------------------------------------------

    documents = adaptive_chunk_document(
        text,
        document_path.name
    )

    # --------------------------------------------------------
    # Inspect chunks
    # --------------------------------------------------------

    print_chunks(
        documents
    )

    # --------------------------------------------------------
    # Build vector DB
    # --------------------------------------------------------

    vectorstore = build_vectorstore(
        documents
    )

    # --------------------------------------------------------
    # Interactive question loop
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("RAG READY")
    print("=" * 70)

    print(
        "\nType a question."
        "\nType 'exit' to stop."
    )

    while True:

        query = input(
            "\nQuestion: "
        ).strip()

        if not query:

            continue

        if query.lower() == "exit":

            break

        # ----------------------------------------------------
        # Retrieve
        # ----------------------------------------------------

        results = retrieve(
            vectorstore,
            query,
            TOP_K
        )

        # ----------------------------------------------------
        # Display retrieved chunks
        # ----------------------------------------------------

        display_retrieval(
            query,
            results
        )

        # ----------------------------------------------------
        # Generate answer
        # ----------------------------------------------------

        print(
            "\n" + "=" * 70
        )

        print(
            "GENERATED ANSWER"
        )

        print(
            "=" * 70
        )

        if not results:

            answer = (
                "I cannot find this information "
                "in the existing document."
            )

        else:
        
            answer = generate_answer(
                query,
                results
            )

        print(
            f"\n{answer}"
        )


# ============================================================
# 19. RUN
# ============================================================

if __name__ == "__main__":

    main()