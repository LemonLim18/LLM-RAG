from langchain_core.documents import Document
from langchain_chroma import Chroma
from .config import CHROMA_DIR, OLLAMA_EMBED_MODEL
from .embeddings import embeddings

def build_document(op):
    text=(
        f"Operation ID: {op['operation_id']}\n"
        f"Category: {op['category_id']}\n"
        f"Name: {op['display_name']}\n"
        f"Aliases: {', '.join(op.get('aliases', []))}\n"
        f"Description: {op['description']}\nUse cases:\n"
        + '\n'.join('- '+x for x in op.get('use_cases',[]))
    )
    return Document(page_content=text,metadata={'operation_id':op['operation_id'],'category':op['category_id']})

def ingest():
    from .config import runtime_mode
    if runtime_mode() == "files":
        return ingest_files()
    from .knowledge.publication import publish
    snapshot = publish()
    print(f"Published and indexed knowledge release {snapshot.release_id}")


def ingest_files():
    from .config import CHROMA_COLLECTION
    from .file_runtime import catalog_revision, file_documents
    revision = catalog_revision()
    documents = file_documents(revision)
    vs = Chroma(collection_name=CHROMA_COLLECTION, persist_directory=str(CHROMA_DIR), embedding_function=embeddings)
    vs.add_documents([Document(page_content=row["page_content"], metadata=row["metadata"]) for row in documents],
                     ids=[row["id"] for row in documents])
    stored = vs.get(include=["metadatas", "documents"])
    expected = {row["id"]: row for row in documents}
    stale = set(stored["ids"]) - set(expected)
    if stale:
        vs.delete(ids=sorted(stale))
    seen = set()
    for identity, metadata, content in zip(stored["ids"], stored["metadatas"], stored["documents"]):
        if identity in expected:
            if metadata != expected[identity]["metadata"] or content != expected[identity]["page_content"]:
                raise ValueError("File catalog index verification failed; rerun python -m app.ingest.")
            seen.add(identity)
    if seen != set(expected) or catalog_revision() != revision:
        raise ValueError("Catalog changed or indexing is incomplete; rerun python -m app.ingest.")
    print(f"Indexed {len(seen)} operations directly from data/ into {CHROMA_COLLECTION}.")
    return {"ids": sorted(seen), "catalog_revision": revision, "collection": CHROMA_COLLECTION}


def build_release_index(release_id, documents, *, chroma_dir=None):
    collection = "knowledge_" + release_id
    chroma_dir = CHROMA_DIR if chroma_dir is None else chroma_dir
    chroma_dir.mkdir(parents=True, exist_ok=True)
    vs = Chroma(collection_name=collection, persist_directory=str(chroma_dir), embedding_function=embeddings)
    if vs.get().get("ids"):
        raise ValueError("A release index cannot be overwritten.")
    docs = [Document(page_content=doc["page_content"], metadata=doc["metadata"]) for doc in documents]
    if docs:
        vs.add_documents(docs, ids=[doc["id"] for doc in documents])
    stored = vs.get(include=["metadatas", "documents"])
    expected = {doc["id"]: doc for doc in documents}
    if sorted(stored["ids"]) != sorted(expected):
        raise ValueError("Incomplete retrieval index.")
    for identity, metadata, content in zip(stored["ids"], stored["metadatas"], stored["documents"]):
        if metadata != expected[identity]["metadata"] or content != expected[identity]["page_content"]:
            raise ValueError("Retrieval index content mismatch.")
    return {"release_id": release_id, "collection": collection, "ids": sorted(expected),
            "embedding_model": OLLAMA_EMBED_MODEL}
if __name__=='__main__': ingest()
