"""Adapters that preserve original CogniShield business rules in local mode."""
import json
from datetime import datetime, timezone
from db.models import ConfigSnapshot
from common_services.service import get_effective_profile
from onboarding.config_generator import OnboardingConfigGenerator
from .templates import LocalTemplateRenderer
from .authoring import AuthoringStore

def day0_parameters(db, device, db_path):
    profile=get_effective_profile(str(db_path), role=device.role, device_id=device.id)
    interfaces=db.get_interfaces_for_device(device.id)
    discovery=[i.name for i in interfaces if i.name and i.name != device.management_interface and str(i.status or '').lower() not in {'down','disabled','shutdown','admin-down'}]
    vendor=(device.vendor or 'cisco_ios').lower()
    interface=device.management_interface or ({'huawei_vrp':'MEth0/0/0','juniper_junos':'fxp0'}.get(vendor,'GigabitEthernet0/0'))
    return {
        'hostname':device.hostname,'mgmt_ip':device.management_ip or '0.0.0.0',
        'subnet_mask':device.management_subnet_mask or '255.255.255.0','gateway':device.oob_gateway_ip or '',
        'mgmt_interface':interface,'discovery_interfaces':discovery,'vendor':vendor,'role':device.role or 'network-device',
        'ssh_user':device.ssh_user or 'admin','ssh_password':device.ssh_password or 'CHANGE_ME','port':device.ssh_port or 22,
        'snmp_community':profile.get('snmp_community'),'snmp_huawei_community':profile.get('snmp_huawei_community'),
        'snmp_location':profile.get('snmp_location'),'snmp_contact':profile.get('snmp_contact'),
        'snmp_host_ip':profile.get('snmp_host_ip'),'syslog_host_ip':profile.get('syslog_host_ip'),'ntp_server_ip':profile.get('ntp_server_ip'),
    }

def generate_day0(db, device, db_path):
    override=db.get_onboarding_day0_override(device.id)
    if override and str(override.get('config_text') or '').strip():
        return str(override['config_text']), str(override.get('filename') or f'{device.hostname}_day0_config.txt'), True
    params=day0_parameters(db,device,db_path)
    try:
        # Uses M0.1's effective SQLite revision when a day-0 template is locally edited.
        config=LocalTemplateRenderer(AuthoringStore(db)).render(params['vendor'],'day-0',params)
    except Exception:
        config=OnboardingConfigGenerator().generate(params)
    return config, f'{device.hostname}_day0_config.txt', False

def save_capture(db, device, config_text, description, user, fixture_config_hash=None):
    snapshot_id=db.save_config_snapshot(ConfigSnapshot(device_id=device.id,config_text=config_text,description=description or 'Simulated running-config capture',source_type='simulated_capture',owner_username=user))
    with db._connect() as c:
        c.execute('INSERT INTO simulated_device_configs(device_id,config_text,source_snapshot_id,source) VALUES (?,?,?,?) ON CONFLICT(device_id) DO UPDATE SET config_text=excluded.config_text,source_snapshot_id=excluded.source_snapshot_id,source=excluded.source,updated_at=datetime(\'now\')',(device.id,config_text,snapshot_id,'simulated'))
        c.execute('INSERT INTO local_workflow_attempts(workflow,device_id,status,details_json) VALUES (?,?,?,?)',('config_capture',device.id,'success',json.dumps({'snapshot_id':snapshot_id,'source':'simulated','fixture_config_hash':fixture_config_hash})))
    return snapshot_id

def restore_snapshot(db, snapshot, status, message, user):
    outcome=status.lower()
    success=outcome in {'success','succeeded','ok'}
    with db._connect() as c:
        if success:
            c.execute('INSERT INTO simulated_device_configs(device_id,config_text,source_snapshot_id,source) VALUES (?,?,?,?) ON CONFLICT(device_id) DO UPDATE SET config_text=excluded.config_text,source_snapshot_id=excluded.source_snapshot_id,source=excluded.source,updated_at=datetime(\'now\')',(snapshot.device_id,snapshot.config_text,snapshot.id,'simulated_restore'))
        c.execute('INSERT INTO local_workflow_attempts(workflow,device_id,status,details_json) VALUES (?,?,?,?)',('config_restore',snapshot.device_id,'success' if success else 'failed',json.dumps({'snapshot_id':snapshot.id,'message':message,'actor':user,'source':'simulated'})))
        c.execute('INSERT INTO audit_log(user_id,action,target,details) VALUES (?,?,?,?)',(user,'config_restore_simulated',str(snapshot.device_id),json.dumps({'snapshot_id':snapshot.id,'status':'success' if success else 'failed','source':'simulated'})))
    return success
