from ..vectorstore import get_vectorstore
from ..catalog import get_operation


def retrieve_operation_candidates(prompt: str, category: str, k: int = 3):
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
        candidates.append({
            "operation_id": operation["operation_id"],
            "category": category,
            "description": operation["description"],
            # Chroma returns a distance here. Lower is better for the default metric.
            "distance": float(score),
        })
    return candidates
