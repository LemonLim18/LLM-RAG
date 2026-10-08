from ..config import BASE_DIR, CATALOG_RELEASES_DIR, OLLAMA_EMBED_MODEL, OLLAMA_LLM_MODEL, runtime_mode
from ..knowledge.authority import authority
from ..knowledge.runtime import active_pointer
from .models import KnowledgeAuthority, PassiveCheck, RuntimeStatusResponse


def _knowledge_authority() -> KnowledgeAuthority:
    try:
        mode = runtime_mode()
        authoring = authority(BASE_DIR)
        if mode == "files":
            return KnowledgeAuthority(
                status="ready",
                configured_runtime_mode="files",
                effective_runtime_authority="direct_files",
                authoring_authority=authoring,
                active_release_id=None,
            )

        pointer = active_pointer(CATALOG_RELEASES_DIR)
        if pointer is None:
            return KnowledgeAuthority(
                status="unavailable",
                configured_runtime_mode="published",
                effective_runtime_authority=None,
                authoring_authority=authoring,
                active_release_id=None,
                error_code="MISSING_ACTIVE_RELEASE",
            )
        return KnowledgeAuthority(
            status="ready",
            configured_runtime_mode="published",
            effective_runtime_authority="published_release",
            authoring_authority=authoring,
            active_release_id=pointer["release_id"],
        )
    except ValueError:
        return KnowledgeAuthority(
            status="unavailable",
            configured_runtime_mode=None,
            effective_runtime_authority=None,
            authoring_authority=None,
            active_release_id=None,
            error_code="INVALID_RUNTIME_CONFIGURATION",
        )
    except (OSError, KeyError, TypeError):
        return KnowledgeAuthority(
            status="unavailable",
            configured_runtime_mode=None,
            effective_runtime_authority=None,
            authoring_authority=None,
            active_release_id=None,
            error_code="RUNTIME_AUTHORITY_UNREADABLE",
        )


def runtime_status() -> RuntimeStatusResponse:
    return RuntimeStatusResponse(
        knowledge=_knowledge_authority(),
        llm=PassiveCheck(
            configured_model=OLLAMA_LLM_MODEL,
            reason="No model or network probe is performed by this read-only endpoint.",
        ),
        embeddings=PassiveCheck(
            configured_model=OLLAMA_EMBED_MODEL,
            reason="No model or network probe is performed by this read-only endpoint.",
        ),
        retrieval=PassiveCheck(
            reason="Chroma and index freshness are not opened or evaluated by this endpoint.",
        ),
    )
