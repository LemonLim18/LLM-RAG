"""Single mode/path authority. Local lab is the safe default; normal is opt-in."""
import os
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
# Process settings take precedence; old VM settings never override explicit mode.
load_dotenv(PROJECT_DIR / '.env', override=False)
load_dotenv(BACKEND_DIR / '.env', override=False)
MODE = os.getenv('COGNISHIELD_MODE', 'local_lab').strip().lower()
if MODE not in {'local_lab', 'normal'}:
    raise ValueError('COGNISHIELD_MODE must be local_lab or normal')
LOCAL_LAB = MODE == 'local_lab'
DB_PATH = Path(os.getenv('COGNISHIELD_DB_PATH', str(BACKEND_DIR / 'db' / 'netauto.db')))
if not DB_PATH.is_absolute():
    DB_PATH = BACKEND_DIR / DB_PATH
DB_PATH = DB_PATH.resolve()
OBSERVATION_PROVIDER = os.getenv('COGNISHIELD_OBSERVATION_PROVIDER', 'json_fixture')
LOCAL_OLLAMA_URL = os.getenv('COGNISHIELD_LOCAL_OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')
LOCAL_OLLAMA_MODEL = os.getenv('COGNISHIELD_LOCAL_OLLAMA_MODEL', 'auto')
FIXTURE_DIR = Path(os.getenv('COGNISHIELD_FIXTURE_DIR', str(BACKEND_DIR / 'simulation')))
if not FIXTURE_DIR.is_absolute():
    FIXTURE_DIR = BACKEND_DIR / FIXTURE_DIR
if LOCAL_LAB and OBSERVATION_PROVIDER != 'json_fixture':
    raise ValueError('Local lab supports only json_fixture observations; remote providers remain disabled')

def require_remote():
    if LOCAL_LAB:
        from fastapi import HTTPException
        raise HTTPException(503, 'Unavailable in local lab: remote integration and execution are disabled.')
