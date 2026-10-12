"""Local equivalents of credential and service checks; never opens a device socket."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from auth.rbac import require_any, require_admin
from auth.credentials import CredentialVault
from common_services.service import get_effective_profile
from lab_config import DB_PATH

router = APIRouter(prefix='/api/v1')

class CredentialBody(BaseModel):
    username: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=4096)
    label: str = Field(default='ZTP_SERVER_SSH', min_length=1, max_length=100)
    device_id: int | None = Field(default=None, gt=0)

class ConnectionBody(BaseModel):
    target_server_ip: str | None = None
    target_server_port: int = Field(default=22, ge=1, le=65535)
    credential_label: str = 'ZTP_SERVER_SSH'
    credential_device_id: int | None = None

@router.get('/onboarding/ztp/server-credential', dependencies=[Depends(require_admin)])
def credential_status(label: str = 'ZTP_SERVER_SSH', device_id: int | None = None):
    credential = CredentialVault().get(device_id, label)
    return {'configured': bool(credential), 'username': credential['username'] if credential else '', 'label': label, 'device_id': device_id, 'source': 'stored'}

@router.post('/onboarding/ztp/server-credential', dependencies=[Depends(require_admin)])
def save_credential(body: CredentialBody):
    if not body.username.strip():
        raise HTTPException(422, 'SSH username must not be blank')
    row_id = CredentialVault().store(body.label, body.device_id, body.username.strip(), body.password)
    return {'id': row_id, 'stored': True, 'label': body.label, 'device_id': body.device_id, 'source': 'stored'}

@router.post('/onboarding/ztp/server-credential/test', dependencies=[Depends(require_admin)])
def test_connection(body: ConnectionBody):
    credential = CredentialVault().get(body.credential_device_id, body.credential_label)
    ok = bool(credential)
    return {'ok': ok, 'duration_ms': 0, 'credential_label': body.credential_label,
            'message': 'Simulated connection successful; stored credential validated. No SSH connection made.' if ok else 'Save a server credential first.',
            'stderr': '' if ok else 'Credential missing', 'source': 'simulated'}

@router.post('/common-services/test-{service}', dependencies=[Depends(require_any)])
def test_service(service: str, site: str | None = None, role: str | None = None, device_id: int | None = None):
    if service not in {'ntp', 'syslog'}:
        raise HTTPException(404, 'Unknown service test')
    profile = get_effective_profile(str(DB_PATH), site=site, role=role, device_id=device_id)
    host = profile.get('ntp_server_ip' if service == 'ntp' else 'syslog_host_ip')
    if not host:
        raise HTTPException(422, f'{service} server is not configured in the saved effective profile')
    return {'ok': True, 'host': host, 'server': host, 'port': profile.get('syslog_port') or 6514,
            'transmit_time': 1791673200, 'offset_seconds': 0,
            'source': 'simulated', 'message': f'Simulated {service} test successful. Saved profile validated; no packet sent.'}
