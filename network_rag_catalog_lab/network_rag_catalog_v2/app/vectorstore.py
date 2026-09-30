from langchain_chroma import Chroma
from .config import CHROMA_DIR, CHROMA_COLLECTION, OLLAMA_EMBED_MODEL
from .embeddings import embeddings
from .knowledge.runtime import current_snapshot

def get_vectorstore():
    snapshot = current_snapshot()
    if snapshot:
        retrieval = snapshot.manifest["retrieval"]
        if not retrieval["ready"] or retrieval["mode"] != "chroma":
            raise ValueError("This release is offline; choose a literal catalog operation or publish with embeddings.")
        if retrieval["embedding_model"] != OLLAMA_EMBED_MODEL:
            raise ValueError("Embedding model changed; publish a new matching retrieval release.")
        return Chroma(collection_name=retrieval["collection"], persist_directory=retrieval["index_path"],
                      embedding_function=embeddings, create_collection_if_not_exists=False)
    from .config import runtime_mode
    if runtime_mode() == "files":
        from .file_runtime import catalog_revision
        from .catalog import load_operations
        vs = Chroma(collection_name=CHROMA_COLLECTION, persist_directory=str(CHROMA_DIR),
                    embedding_function=embeddings, create_collection_if_not_exists=False)
        stored = vs.get(include=["metadatas"])
        revision = catalog_revision()
        expected = {row["operation_id"] for row in load_operations()}
        if (set(stored["ids"]) != expected or any(metadata.get("catalog_revision") != revision
                or metadata.get("embedding_model") != OLLAMA_EMBED_MODEL for metadata in stored["metadatas"])):
            raise ValueError("RAG index does not match data/. Run python -m app.ingest.")
        return vs
    from .catalog import load_operations
    if any(operation.get("schema_source") == "registry" for operation in load_operations()):
        raise ValueError("Publish a knowledge release before semantic retrieval; a legacy index cannot serve registry contracts.")
    return Chroma(collection_name=CHROMA_COLLECTION,persist_directory=str(CHROMA_DIR),embedding_function=embeddings)
