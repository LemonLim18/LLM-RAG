"""Local implementations of original workflows; JSON only supplies external outcomes."""
import hashlib
import json
import os
import tempfile
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from fastapi import HTTPException

class _Model(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Outcome(_Model):
    device_id: int = Field(gt=0)
    status: str
    message: str = Field(min_length=1, max_length=1000)

class ExternalAction(_Model):
    default_status: str
    message: str
    device_outcomes: list[Outcome] = Field(default_factory=list)

class Capture(_Model):
    default_config: str = Field(min_length=1, max_length=2_000_000)
    device_configs: list['CaptureConfig'] = Field(default_factory=list)

class CaptureConfig(_Model):
    device_id: int = Field(gt=0)
    config_text: str = Field(min_length=1, max_length=2_000_000)

class DeviceConfig(CaptureConfig):
    source: str = 'simulated'

class WorkflowFixture(_Model):
    version: int = 1
    capture: Capture
    ztp_publish: ExternalAction
    restore: ExternalAction
    deployment_history: list['DeploymentHistory'] = Field(default_factory=list)

class DeploymentHistory(_Model):
    label: str = Field(min_length=1,max_length=200)
    timestamp: str
    outcome: str = Field(pattern='^(success|failed)$')
    message: str = Field(min_length=1,max_length=1000)

class WorkflowFixtureError(ValueError):
    pass

class LocalWorkflowProvider:
    def __init__(self, directory): self.path = Path(directory) / 'workflow_outcomes.json'

    def read(self, db):
        try:
            raw=self.path.read_bytes()
            data=WorkflowFixture.model_validate_json(raw)
        except (OSError, ValidationError, ValueError) as exc:
            detail='; '.join('.'.join(map(str,e['loc']))+': '+e['type'] for e in exc.errors()) if isinstance(exc,ValidationError) else str(exc)
            raise WorkflowFixtureError('Invalid simulation workflow_outcomes.json: '+detail) from exc
        with db._connect() as c:
            known={r['id'] for r in c.execute('SELECT id FROM devices')}
        for action in (data.ztp_publish,data.restore):
            for outcome in action.device_outcomes:
                if outcome.device_id not in known: raise WorkflowFixtureError(f'unknown SQLite device_id {outcome.device_id}')
        for capture in data.capture.device_configs:
            if capture.device_id not in known: raise WorkflowFixtureError(f'unknown SQLite device_id {capture.device_id}')
        return data, hashlib.sha256(raw).hexdigest()

    @staticmethod
    def action(data, name, device_id):
        action=getattr(data,name)
        found=next((o for o in action.device_outcomes if o.device_id==device_id),None)
        return (found.status,found.message) if found else (action.default_status,action.message)

    def capture_config(self, data, device):
        path = self.path.parent / 'configurations' / f'device-{device.id}.json'
        if path.exists():
            try:
                record = DeviceConfig.model_validate_json(path.read_bytes())
                if record.device_id != device.id:
                    raise ValueError('device_id does not match filename')
                return record.config_text
            except (ValueError, OSError) as exc:
                raise WorkflowFixtureError(f'Invalid configurations/device-{device.id}.json; check schema and device_id') from exc
        selected=next((entry for entry in data.capture.device_configs if entry.device_id == device.id),None)
        template=selected.config_text if selected else data.capture.default_config
        config = template.replace('{hostname}', device.hostname).replace('{management_ip}', device.management_ip or '')
        self.write_config(device, config)
        return config

    def write_config(self, device, config):
        record = DeviceConfig(device_id=device.id, config_text=config)
        directory = self.path.parent / 'configurations'
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f'device-{device.id}.json'
        if target.is_symlink() or directory.is_symlink():
            raise WorkflowFixtureError('Configuration files must remain inside the simulation directory')
        fd, temporary = tempfile.mkstemp(prefix='.config-', suffix='.tmp', dir=directory)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                stream.write(record.model_dump_json(indent=2) + '\n')
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
