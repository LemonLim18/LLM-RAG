"""Restart the existing backend composition when the .env mode changes.

No provider fallback: failed normal-mode startup stays failed until the operator
repairs its prerequisites or selects local_lab in .env.
"""
import os
from pathlib import Path
import subprocess
import sys
import time
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent

def selected_mode():
    value = dotenv_values(ROOT.parent / '.env').get('COGNISHIELD_MODE', 'local_lab')
    if value not in {'local_lab', 'normal'}:
        raise ValueError('COGNISHIELD_MODE must be local_lab or normal')
    return value

def stop_worker(worker):
    if worker and worker.poll() is None:
        if os.name == 'nt':
            # Windows venv launchers create an interpreter child. Stop only our
            # owned worker tree, otherwise its child would retain port 8000.
            subprocess.run(['taskkill', '/PID', str(worker.pid), '/T', '/F'], check=True, capture_output=True)
        else:
            worker.terminate()
        worker.wait(timeout=30)

def main():
    worker = None
    mode = None
    try:
        while True:
            desired = selected_mode()
            if desired != mode:
                stop_worker(worker)
                mode = desired
                env = dict(os.environ, COGNISHIELD_MODE=mode, COGNISHIELD_SUPERVISED='1')
                worker = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend:app', '--host', '127.0.0.1', '--port', '8000'], cwd=ROOT, env=env)
            time.sleep(1)
    finally:
        stop_worker(worker)

if __name__ == '__main__':
    main()
