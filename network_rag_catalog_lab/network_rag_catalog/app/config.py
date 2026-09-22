from pathlib import Path

# Path(__file__).resolve() returns the absolute path of the current file (config.py).
# BASE_DIR = /network_rag_catalog/
BASE_DIR=Path(__file__).resolve().parents[1] 

# DATA_DIR = BASE_DIR/'data'
DATA_DIR=BASE_DIR/'data'; 
CATALOG_FILE=DATA_DIR/'catalog/operations.json'; 
CATEGORIES_FILE=DATA_DIR/'catalog/categories.json'; 
INVENTORY_FILE=DATA_DIR/'inventory/devices.json'
TEMPLATES_DIR=DATA_DIR/'templates'; 
CHROMA_DIR=BASE_DIR/'storage/chroma'
OLLAMA_LLM_MODEL='qwen2.5:1.5b'; 
OLLAMA_EMBED_MODEL='nomic-embed-text'; 
CHROMA_COLLECTION='network_operation_catalog'
