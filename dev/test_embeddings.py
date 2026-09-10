"""
test_embeddings.py

CONTROLLED EMBEDDING EXPERIMENT

Purpose:
1. Load a networking document.
2. Split it using KNOWN section headings.
3. Generate embeddings using Ollama's nomic-embed-text over LAN.
4. Store the sections in Chroma.
5. Embed several test queries.
6. Compare query embeddings against section embeddings using cosine similarity.
7. Check whether the CORRECT section ranks #1 and appears in Top-3.
8. Measure the similarity margin between the correct result and runner-up.
9. Generate visualizations for inspection.

IMPORTANT:
This version intentionally does NOT use SemanticChunker.

The purpose is to isolate the embedding/retrieval factor.

If retrieval works well here but failed with SemanticChunker,
the likely problem is chunking rather than the embedding model.

No LLM is used in this script.
"""

from pathlib import Path
import re

import numpy as np
import matplotlib.pyplot as plt

from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document


# ============================================================
# 1. CONFIGURATION
# ============================================================

OLLAMA_URL = "http://192.168.1.8:11434"
EMBEDDING_MODEL = "nomic-embed-text"

BASE_DIR = Path(__file__).resolve().parent

DOCUMENT_PATH = (
    BASE_DIR
    / "data"
    / "network_test_document.txt"
)

CHROMA_DIR = BASE_DIR / "chroma_db"

ANALYSIS_PICTURE_PATH = (
    BASE_DIR
    / "analysis_pictures"
)

ANALYSIS_PICTURE_PATH.mkdir(
    parents=True,
    exist_ok=True
)

COLLECTION_NAME = "network_controlled_embedding_test"

TOP_K = 5


# ============================================================
# 2. TEST QUERIES
# ============================================================

# Each query has a known correct section.
#
# This is our ground truth for the controlled experiment.

TEST_QUERIES = {

    "DHCP": {
        "query":
            "Which protocol dynamically assigns IP addresses "
            "and network configuration to clients?",
        "expected_section": 6,
    },

    "ARP": {
        "query":
            "How does a host discover the MAC address "
            "associated with an IPv4 address?",
        "expected_section": 7,
    },

    "DNS": {
        "query":
            "How are human-readable domain names translated "
            "into IP address information?",
        "expected_section": 5,
    },

    "TCP": {
        "query":
            "How does TCP provide reliable and ordered "
            "delivery of data?",
        "expected_section": 1,
    },

    "VLAN": {
        "query":
            "How can a switched network be divided into "
            "separate logical broadcast domains?",
        "expected_section": 10,
    },

    "FIREWALL": {
        "query":
            "How does a firewall control network traffic "
            "according to a security policy?",
        "expected_section": 12,
    },

    "ROUTING": {
        "query":
            "What is the purpose of a default gateway "
            "and routing table?",
        "expected_section": 13,
    },
}


# ============================================================
# 3. HELPER FUNCTIONS
# ============================================================

def cosine_similarity(a, b):
    """
    Calculate cosine similarity between two vectors.
    Higher = more semantically similar.
    """

    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)

    denominator = (
        np.linalg.norm(a)
        * np.linalg.norm(b)
    )

    if denominator == 0:
        return 0.0

    return float(
        np.dot(a, b) / denominator
    )


def detect_section(doc):
    """
    Get section information from Document metadata.
    """

    return (
        f"{doc.metadata['section_number']}. "
        f"{doc.metadata['section_title']}"
    )


def shorten(text, length=220):
    """
    Shorten text for terminal output.
    """

    text = " ".join(text.split())

    if len(text) <= length:
        return text

    return text[:length] + "..."


# ============================================================
# 4. START
# ============================================================

print("=" * 70)
print("CONTROLLED EMBEDDING + RETRIEVAL EXPERIMENT")
print("=" * 70)

print(f"\nOllama server   : {OLLAMA_URL}")
print(f"Embedding model : {EMBEDDING_MODEL}")


# ============================================================
# 5. CONNECT TO OLLAMA EMBEDDING MODEL
# ============================================================

print("\nConnecting to Ollama...")

embeddings = OllamaEmbeddings(
    model=EMBEDDING_MODEL,
    base_url=OLLAMA_URL
)

print("Embedding model connection configured.")


# ============================================================
# 6. LOAD DOCUMENT
# ============================================================

if not DOCUMENT_PATH.exists():

    raise FileNotFoundError(
        f"\nDocument not found:\n"
        f"{DOCUMENT_PATH}\n\n"
        f"Expected structure:\n"
        f"dev/\n"
        f"├── test_embeddings.py\n"
        f"└── data/\n"
        f"    └── network_test_document.txt"
    )


text = DOCUMENT_PATH.read_text(
    encoding="utf-8"
)

print(f"\nDocument: {DOCUMENT_PATH}")
print(f"Characters: {len(text):,}")


# ============================================================
# 7. CONTROLLED SECTION-BASED CHUNKING
# ============================================================

print("\nCreating controlled section-based chunks...")

# Expected heading format:
#
# 1. TRANSMISSION CONTROL PROTOCOL (TCP)
# 2. USER DATAGRAM PROTOCOL (UDP)
# ...
# 14. HOW THESE PROTOCOLS WORK TOGETHER
#
# We deliberately use these headings as chunk boundaries.
#
# This gives us known ground truth:
#
# Section 1 -> TCP
# Section 5 -> DNS
# Section 6 -> DHCP
# Section 7 -> ARP
# Section 10 -> VLAN
# Section 12 -> Firewall
# Section 13 -> Routing

section_pattern = re.compile(
    r"(?m)^(\d+)\.\s+(.+?)\s*$"
)

matches = list(
    section_pattern.finditer(text)
)

documents = []

for i, match in enumerate(matches):

    section_number = int(
        match.group(1)
    )

    section_title = match.group(2).strip()

    # Ignore anything beyond section 14.
    if section_number > 14:
        continue

    # Start at the current heading.
    start = match.start()

    # End immediately before the next heading.
    if i + 1 < len(matches):

        end = matches[i + 1].start()

    else:

        end = len(text)

    section_text = text[
        start:end
    ].strip()

    documents.append(
        Document(
            page_content=section_text,
            metadata={
                "section_number": section_number,
                "section_title": section_title,
            }
        )
    )


# ============================================================
# 8. VALIDATE THE CONTROLLED CHUNKS
# ============================================================

print(
    f"\nNumber of controlled sections: "
    f"{len(documents)}"
)


# We EXPECT exactly 14 sections.

if len(documents) != 14:

    raise ValueError(
        f"\nERROR: Expected 14 sections "
        f"but found {len(documents)}."
    )


actual_section_numbers = [
    doc.metadata["section_number"]
    for doc in documents
]

expected_section_numbers = list(
    range(1, 15)
)

if actual_section_numbers != expected_section_numbers:

    raise ValueError(
        "\nERROR: Section numbering is incorrect.\n"
        f"Found   : {actual_section_numbers}\n"
        f"Expected: {expected_section_numbers}"
    )


print("\nControlled chunks:")

for i, doc in enumerate(documents):

    print(
        f"  Chunk {i + 1:02d} | "
        f"{len(doc.page_content):5d} chars | "
        f"{detect_section(doc)}"
    )


# ============================================================
# 9. CREATE CLEAN CHROMA COLLECTION
# ============================================================

print("\nCreating clean Chroma collection...")

vectorstore = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings,
    persist_directory=str(CHROMA_DIR)
)

# Remove old test collection so repeated runs
# do not accumulate duplicate documents.

try:

    vectorstore.delete_collection()

except Exception:

    pass


vectorstore = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings,
    persist_directory=str(CHROMA_DIR)
)


# ============================================================
# 10. STORE DOCUMENTS IN CHROMA
# ============================================================

print("\nAdding sections to Chroma...")

vectorstore.add_documents(
    documents
)

print(
    f"Stored {len(documents)} sections in Chroma."
)

print(
    f"Chroma directory: {CHROMA_DIR}"
)


# ============================================================
# 11. CREATE CHUNK EMBEDDINGS
# ============================================================

print("\nGenerating embeddings for sections...")

chunk_texts = [
    doc.page_content
    for doc in documents
]

chunk_vectors = (
    embeddings.embed_documents(
        chunk_texts
    )
)

chunk_matrix = np.asarray(
    chunk_vectors,
    dtype=np.float32
)


print(
    f"Embedding matrix shape: "
    f"{chunk_matrix.shape}"
)

print(
    f"This means: "
    f"{chunk_matrix.shape[0]} sections x "
    f"{chunk_matrix.shape[1]} dimensions"
)


# ============================================================
# 12. VALIDATE EMBEDDING MATRIX
# ============================================================

if chunk_matrix.shape[0] != len(documents):

    raise ValueError(
        "Number of embeddings does not match "
        "number of document sections."
    )


if chunk_matrix.shape[1] == 0:

    raise ValueError(
        "Embedding vectors have zero dimensions."
    )


# Check vector norms.

embedding_norms = np.linalg.norm(
    chunk_matrix,
    axis=1
)

print("\nEmbedding norm statistics:")

print(
    f"  Minimum : "
    f"{embedding_norms.min():.4f}"
)

print(
    f"  Maximum : "
    f"{embedding_norms.max():.4f}"
)

print(
    f"  Mean    : "
    f"{embedding_norms.mean():.4f}"
)


# ============================================================
# 13. MANUAL COSINE-SIMILARITY RETRIEVAL
# ============================================================

print("\n" + "=" * 70)
print("MANUAL COSINE-SIMILARITY RETRIEVAL")
print("=" * 70)

all_results = {}

passed_top1 = 0
passed_top3 = 0


for topic, test in TEST_QUERIES.items():

    query = test["query"]
    expected_section = test["expected_section"]

    print("\n" + "=" * 70)
    print(f"QUERY: {query}")
    print(f"Expected section: {expected_section}")
    print(f"Expected section title: {documents[expected_section - 1].metadata['section_title']}")
    print("=" * 70)

    # --------------------------------------------------------
    # Embed query
    # --------------------------------------------------------

    query_vector = embeddings.embed_query(
        query
    )

    # --------------------------------------------------------
    # Compare query against EVERY section
    # --------------------------------------------------------

    scores = []

    for chunk_index, chunk_vector in enumerate(
        chunk_matrix
    ):

        score = cosine_similarity(
            query_vector,
            chunk_vector
        )

        scores.append(
            {
                "chunk_index": chunk_index,
                "score": score,
                "section_number":
                    documents[chunk_index]
                    .metadata["section_number"],
                "section":
                    detect_section(
                        documents[chunk_index]
                    ),
                "text":
                    documents[chunk_index]
                    .page_content,
            }
        )

    # --------------------------------------------------------
    # Highest cosine similarity first
    # --------------------------------------------------------

    scores.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    all_results[topic] = scores

    # --------------------------------------------------------
    # Determine rankings
    # --------------------------------------------------------

    top1_section = (
        scores[0]["section_number"]
    )

    top3_sections = [
        result["section_number"]
        for result in scores[:3]
    ]

    top1_pass = (
        top1_section == expected_section
    )

    top3_pass = (
        expected_section in top3_sections
    )

    if top1_pass:
        passed_top1 += 1

    if top3_pass:
        passed_top3 += 1

    # --------------------------------------------------------
    # Similarity margin
    # --------------------------------------------------------

    best_score = scores[0]["score"]

    second_score = scores[1]["score"]

    margin = (
        best_score
        - second_score
    )

    # --------------------------------------------------------
    # Print top results
    # --------------------------------------------------------

    print("\nTop retrieved sections:")

    for rank, result in enumerate(
        scores[:TOP_K],
        start=1
    ):

        print(
            f"\nRank {rank}"
            f"\nSimilarity : "
            f"{result['score']:.4f}"
            f"\nSection    : "
            f"{result['section']}"
            f"\nText       : "
            f"{shorten(result['text'])}"
        )

    # --------------------------------------------------------
    # Print evaluation
    # --------------------------------------------------------

    print("\n--- Evaluation ---")

    print(
        f"Expected section : "
        f"{expected_section}"
    )

    print(
        f"Top-1 section    : "
        f"{top1_section}"
    )

    print(
        f"Top-3 sections   : "
        f"{top3_sections}"
    )

    print(
        f"Top-1 similarity : "
        f"{best_score:.4f}"
    )

    print(
        f"2nd similarity   : "
        f"{second_score:.4f}"
    )

    print(
        f"Similarity margin: "
        f"{margin:.4f}"
    )

    if top1_pass:

        print(
            "RESULT: PASS - "
            "correct section ranked #1"
        )

    else:

        print(
            "RESULT: CHECK - "
            "correct section did NOT rank #1"
        )

    if top3_pass:

        print(
            "Top-3: PASS - "
            "correct section is in Top-3"
        )

    else:

        print(
            "Top-3: FAIL - "
            "correct section is NOT in Top-3"
        )


# ============================================================
# 14. CHROMA CROSS-CHECK
# ============================================================

print("\n" + "=" * 70)
print("CHROMA RETRIEVAL CROSS-CHECK")
print("=" * 70)

for topic, test in TEST_QUERIES.items():

    query = test["query"]

    expected_section = (
        test["expected_section"]
    )

    results = (
        vectorstore
        .similarity_search_with_score(
            query,
            k=3
        )
    )

    print(
        f"\nQuery [{topic}]"
    )

    for rank, (
        doc,
        distance
    ) in enumerate(
        results,
        start=1
    ):

        print(
            f"  Rank {rank} | "
            f"Distance: {distance:.4f} | "
            f"{detect_section(doc)}"
        )

    chroma_top_section = (
        results[0][0]
        .metadata["section_number"]
    )

    if chroma_top_section == expected_section:

        print(
            "  Chroma Top-1: PASS"
        )

    else:

        print(
            "  Chroma Top-1: CHECK"
        )


print(
    "\nNOTE:"
    "\nManual cosine similarity:"
    "\n  Higher = more similar."
    "\n\nChroma's returned distance:"
    "\n  Lower generally means closer."
    "\n\nDo not compare the numerical values "
    "directly."
)


# ============================================================
# 15. VISUALIZATION: TOP-5 SIMILARITY
# ============================================================

print(
    "\nGenerating similarity charts..."
)

for topic, scores in all_results.items():

    top_results = scores[:TOP_K]

    labels = [
        f"#{i + 1} {r['section']}"
        for i, r in enumerate(
            top_results
        )
    ]

    values = [
        r["score"]
        for r in top_results
    ]

    fig, ax = plt.subplots(
        figsize=(10, 5)
    )

    ax.barh(
        labels[::-1],
        values[::-1]
    )

    ax.set_xlabel(
        "Cosine similarity"
    )

    ax.set_title(
        f"{topic}: "
        "Query-to-section similarity"
    )

    ax.set_xlim(
        min(
            0.0,
            min(values) - 0.05
        ),
        min(
            1.0,
            max(values) + 0.05
        )
    )

    for y, value in enumerate(
        values[::-1]
    ):

        ax.text(
            value,
            y,
            f" {value:.3f}",
            va="center"
        )

    plt.tight_layout()

    filename = (
        ANALYSIS_PICTURE_PATH
        / f"similarity_{topic.lower()}.png"
    )

    plt.savefig(
        filename,
        dpi=160
    )

    plt.close()

    print(
        f"Saved: {filename.name}"
    )


# ============================================================
# 16. HEATMAP
# ============================================================

print(
    "\nGenerating similarity heatmap..."
)

topics = list(
    TEST_QUERIES.keys()
)

similarity_matrix = []

for topic in topics:

    query_vector = (
        embeddings.embed_query(
            TEST_QUERIES[topic]["query"]
        )
    )

    row = [
        cosine_similarity(
            query_vector,
            chunk_vector
        )
        for chunk_vector in chunk_matrix
    ]

    similarity_matrix.append(row)


similarity_matrix = np.asarray(
    similarity_matrix,
    dtype=np.float32
)


fig, ax = plt.subplots(
    figsize=(
        max(
            10,
            len(documents) * 0.7
        ),
        6
    )
)

image = ax.imshow(
    similarity_matrix,
    aspect="auto"
)

ax.set_title(
    "Query-to-section cosine similarity"
)

ax.set_xlabel(
    "Document section"
)

ax.set_ylabel(
    "Test query"
)

ax.set_xticks(
    range(len(documents))
)

ax.set_xticklabels(
    [
        f"C{i + 1}"
        for i in range(len(documents))
    ]
)

ax.set_yticks(
    range(len(topics))
)

ax.set_yticklabels(
    topics
)

fig.colorbar(
    image,
    ax=ax,
    label="Cosine similarity"
)

plt.tight_layout()

heatmap_path = (
    ANALYSIS_PICTURE_PATH
    / "similarity_heatmap.png"
)

plt.savefig(
    heatmap_path,
    dpi=160
)

plt.close()

print(
    f"Saved: {heatmap_path}"
)


# ============================================================
# 17. PCA VISUALIZATION
# ============================================================

print(
    "\nGenerating PCA visualization..."
)

# PCA implemented using NumPy.

centered = (
    chunk_matrix
    - chunk_matrix.mean(axis=0)
)

covariance = np.cov(
    centered,
    rowvar=False
)

eigenvalues, eigenvectors = (
    np.linalg.eigh(covariance)
)

# Largest eigenvalues first.

order = np.argsort(
    eigenvalues
)[::-1]

components = (
    eigenvectors[
        :,
        order[:2]
    ]
)

chunk_2d = (
    centered
    @ components
)


fig, ax = plt.subplots(
    figsize=(11, 7)
)

ax.scatter(
    chunk_2d[:, 0],
    chunk_2d[:, 1],
    s=70
)


for i, doc in enumerate(
    documents
):

    ax.annotate(
        f"C{i + 1}\n"
        f"{detect_section(doc)}",
        (
            chunk_2d[i, 0],
            chunk_2d[i, 1]
        ),
        xytext=(5, 5),
        textcoords="offset points",
        fontsize=8
    )


ax.set_title(
    "2D PCA projection of section embeddings"
)

ax.set_xlabel(
    "Principal component 1"
)

ax.set_ylabel(
    "Principal component 2"
)

plt.tight_layout()

pca_path = (
    ANALYSIS_PICTURE_PATH
    / "embedding_pca.png"
)

plt.savefig(
    pca_path,
    dpi=160
)

plt.close()

print(
    f"Saved: {pca_path}"
)


# ============================================================
# 18. FINAL CONTROLLED EXPERIMENT RESULT
# ============================================================

print("\n" + "=" * 70)
print("FINAL CONTROLLED EMBEDDING DIAGNOSTIC")
print("=" * 70)


for topic, scores in all_results.items():

    expected_section = (
        TEST_QUERIES[topic]
        ["expected_section"]
    )

    top1_section = (
        scores[0]["section_number"]
    )

    top1_score = (
        scores[0]["score"]
    )

    second_score = (
        scores[1]["score"]
    )

    margin = (
        top1_score
        - second_score
    )

    if top1_section == expected_section:

        status = "PASS"

    else:

        status = "CHECK"

    print(
        f"{status:5s} | "
        f"{topic:10s} | "
        f"Expected C{expected_section:02d} | "
        f"Got C{top1_section:02d} | "
        f"Top = {top1_score:.4f} | "
        f"Margin = {margin:.4f}"
    )


print(
    "\n" + "-" * 70
)

print(
    f"TOP-1 ACCURACY: "
    f"{passed_top1}/{len(TEST_QUERIES)} "
    f"= "
    f"{passed_top1 / len(TEST_QUERIES) * 100:.1f}%"
)

print(
    f"TOP-3 ACCURACY: "
    f"{passed_top3}/{len(TEST_QUERIES)} "
    f"= "
    f"{passed_top3 / len(TEST_QUERIES) * 100:.1f}%"
)


print("\nGenerated files:")

print(
    "  similarity_<topic>.png"
)

print(
    "  similarity_heatmap.png"
)

print(
    "  embedding_pca.png"
)


# ============================================================
# 19. INTERPRETATION
# ============================================================

print("\n" + "=" * 70)
print("HOW TO INTERPRET THIS EXPERIMENT")
print("=" * 70)

print(
    """
This experiment intentionally uses clean, known section boundaries.

If most expected sections rank #1:
    -> Embedding + retrieval is working reasonably well.
    -> Previous failures may be related to chunking.

If many expected sections fail even here:
    -> Investigate the embedding/retrieval setup.
    -> Possible factors include:
       - embedding model
       - query wording
       - document content
       - similarity metric
       - embedding consistency

IMPORTANT:
A high cosine similarity alone does NOT prove that
an embedding model is good.

The important question is:

    Does the correct semantic section rank
    above unrelated sections?

This experiment is designed to answer exactly that.
"""
)