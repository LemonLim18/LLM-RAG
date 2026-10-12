"""Admin-only environment selection shared by both application compositions."""
import os
from typing import Literal
from dotenv import dotenv_values, set_key
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from auth.rbac import require_admin
from lab_config import MODE, PROJECT_DIR

router = APIRouter(prefix='/api/v1/environment', tags=['environment'])

class EnvironmentSelection(BaseModel):
    mode: Literal['local_lab', 'normal']

@router.get('')
def environment():
    selected = dotenv_values(PROJECT_DIR / '.env').get('COGNISHIELD_MODE', MODE)
    return {'active_mode': MODE, 'selected_mode': selected,
            'automatic_restart': os.getenv('COGNISHIELD_SUPERVISED') == '1',
            'restart_required': selected != MODE}

@router.put('', dependencies=[Depends(require_admin)])
def select_environment(body: EnvironmentSelection):
    # dotenv changes only this key; credentials and remote settings stay intact.
    set_key(str(PROJECT_DIR / '.env'), 'COGNISHIELD_MODE', body.mode)
    return environment()
