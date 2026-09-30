import json

from ..vectorstore import get_vectorstore
from ..catalog import get_operation
from ..knowledge.runtime import current_snapshot, snapshot_request


@snapshot_request
def retrieve_operation_candidates(prompt: str, category: str, k: int = 3):
    snapshot = current_snapshot()
    vs = get_vectorstore()
    results = vs.similarity_search_with_score(prompt, k=k, filter={"category": category})
    candidates = []
    for document, score in results:
        try:
            operation = get_operation(document.metadata["operation_id"])
        except KeyError:
            # An administrator may have deactivated an operation before the
            # next ingestion run. Do not let stale vector data revive it.
            continue
        if snapshot and (document.metadata.get("release_id") != snapshot.release_id
                         or document.metadata.get("operation_version") != operation.get("version", 1)
                         or document.metadata.get("category") != operation["category_id"]):
            raise ValueError("Retrieval data belongs to a different knowledge contract.")
        if operation["category_id"] != category:
            continue
        candidates.append({
            "operation_id": operation["operation_id"],
            "category": category,
            "description": operation["description"],
            "vendor_support": json.loads(document.metadata.get("vendor_support", "{}")),
            # Chroma returns a distance here. Lower is better for the default metric.
            "distance": float(score),
        })
    return candidates
