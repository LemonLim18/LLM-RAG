import os
from pathlib import Path
root=Path(__file__).resolve().parents[1]
folder=root/'tmp/v9-browser';folder.mkdir(parents=True,exist_ok=True)
os.environ['COGNISHIELD_DB_PATH']=str(folder/'browser.db')
os.environ['COGNISHIELD_MODE']='local_lab'
os.environ['COGNISHIELD_STUDIO_ENGINE']='v9'
from db.manager import DatabaseManager
from db.models import Device
from auth.auth import seed_default_admin
manager=DatabaseManager();manager.initialize();seed_default_admin()
with manager._connect() as c: found=c.execute("SELECT id FROM devices WHERE hostname='V9-SW1'").fetchone()
if not found:
 manager.upsert_device(Device(hostname='V9-SW1',management_ip='192.0.2.80',management_subnet_mask='24',vendor='cisco_ios',os_version='IOS-XE 17.9',status='planned',role='access'))
import uvicorn
uvicorn.run('backend:app',host='127.0.0.1',port=8000)
