from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
CATALOG_DIR = DATA_DIR / "catalog"
CATALOG_FILE = CATALOG_DIR / "operations.json"
CATEGORIES_FILE = CATALOG_DIR / "categories.json"
PARAMETERS_FILE = CATALOG_DIR / "parameters.json"
CATEGORY_PARAMETERS_FILE = CATALOG_DIR / "category_parameters.json"
OPERATION_PARAMETERS_FILE = CATALOG_DIR / "operation_parameters.json"
OPERATION_RULES_FILE = CATALOG_DIR / "operation_rules.json"
INVENTORY_FILE = DATA_DIR / "inventory" / "devices.json"
TEMPLATES_DIR = DATA_DIR / "templates"
STORAGE_DIR = BASE_DIR / "storage"
CHROMA_DIR = STORAGE_DIR / "chroma"
SESSIONS_DIR = STORAGE_DIR / "sessions"
CATALOG_RELEASES_DIR = STORAGE_DIR / "catalog_releases"
TEMPLATE_BINDINGS_FILE = CATALOG_DIR / "template_bindings.json"

OLLAMA_LLM_MODEL = "qwen2.5:1.5b"
OLLAMA_EMBED_MODEL = "nomic-embed-text"
CHROMA_COLLECTION = "network_operation_catalog"

# Terminal prompt testing reads data/ directly. The existing backend is retained.
def runtime_mode():
    mode = os.environ.get("NETWORK_RAG_RUNTIME", "files")
    if mode not in {"files", "published"}:
        raise ValueError("NETWORK_RAG_RUNTIME must be files or published.")
    return mode
