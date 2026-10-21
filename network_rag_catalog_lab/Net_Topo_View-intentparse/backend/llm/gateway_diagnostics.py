"""Passive diagnostics: no installs, service starts, DB migrations or publication."""
import importlib.util
import os
import shutil
import sys
from pathlib import Path


async def diagnose():
    from lab_config import DB_PATH, LOCAL_OLLAMA_URL, PROJECT_DIR, MODE
    from local_providers.chat import runtime
    from llm.gateway_knowledge import release_assessment
    state = await runtime()
    from llm.orchestration.model import RoutingModel
    budgets=RoutingModel()
    python = Path(os.getenv('COGNISHIELD_V9_PYTHON', str(PROJECT_DIR.parents[1] / '.venv/Scripts/python.exe')))
    return {'mode': MODE, 'database_exists': DB_PATH.is_file(), 'database': str(DB_PATH),
        'backend_python': sys.executable, 'ollama_url': LOCAL_OLLAMA_URL, 'model_runtime': state,
        'v9_python_available': python.is_file(), 'knowledge': release_assessment(),
        'validation': {'runtime': 'wsl', 'launcher_available': shutil.which('wsl') is not None,
            'status': 'unavailable_until_containment_verified', 'device_testing': 'not_run', 'deployment': 'disabled'},
        'pdf_extraction': {'backend_pypdf_installed':bool(importlib.util.find_spec('pypdf')),
            'configured_interpreter':os.getenv('COGNISHIELD_DOCUMENT_PYTHON',sys.executable),
            'configured_interpreter_exists':Path(os.getenv('COGNISHIELD_DOCUMENT_PYTHON',sys.executable)).is_file()},
        'document_understanding': {'ocr':'Windows.Media.Ocr', 'renderer':os.getenv('COGNISHIELD_PDF_RENDERER') or shutil.which('pdftoppm'), 'ocr_host_available':os.name=='nt' and shutil.which('powershell.exe') is not None, 'vision_model':os.getenv('COGNISHIELD_VISION_MODEL'), 'vision_requires_advertised_capability':True, 'limits':{'ocr_pages':24,'ocr_seconds':90,'image_pixels':16000000,'context_characters':10000}},
        'optional_ocr_model':os.getenv('COGNISHIELD_OCR_MODEL'),
        'agent_engine':{'planning_enabled':os.getenv('COGNISHIELD_AI_PLANNING','0')=='1','synthesis_enabled':os.getenv('COGNISHIELD_AI_SYNTHESIS','0')=='1','configured':os.getenv('COGNISHIELD_AI_ENGINE','legacy'),
            'langgraph_installed':bool(importlib.util.find_spec('langgraph')),
            'scope':'Shared Floating/Studio orchestration with existing V9/proposal boundaries' if os.getenv('COGNISHIELD_AI_ENGINE')=='langgraph_b3' else 'Floating read-only; Studio engineering retains existing paths',
            'checkpointing':os.getenv('COGNISHIELD_AI_ENGINE') in {'langgraph_b2','langgraph_b3'},'max_read_rounds':3 if os.getenv('COGNISHIELD_AI_ENGINE') in {'langgraph_b2','langgraph_b3'} else 2,'max_tool_calls':8,'max_model_calls':budgets.max_calls,'model_stage_limits':budgets.stage_limits,'max_input_characters':budgets.max_input_characters,'max_seconds':120,
            'studio_max_seconds':210,'studio_proposal_calls':1,'proposal_model_attempts':2},
        'semantic_routing':{'embedding_model':os.getenv('COGNISHIELD_ROUTING_EMBED_MODEL','nomic-embed-text:latest'),'fallback':'structured_chat_classification','operation_authority':'V9'},
        'network_context': {'readers':['inventory','planned_topology','telemetry','syslog','incidents','configuration_history','documentation'], 'live_reads_enabled':os.getenv('COGNISHIELD_AI_LIVE_READS')=='1', 'collection_triggered':False},
        'deferred': ['multi_file_engineering','F6','A6'], 'execution_available': False}
