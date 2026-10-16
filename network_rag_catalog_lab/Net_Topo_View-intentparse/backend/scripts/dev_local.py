"""One ordinary workspace, fixed frontend/backend ports, no installation or port hopping."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def port_in_use(port):
    with socket.socket() as sock:
        sock.settimeout(.3)
        return sock.connect_ex(('127.0.0.1', port)) == 0


def main():
    for port in (5173, 8000, 5174, 5175, 5176, 8001, 8002):
        if port_in_use(port):
            raise SystemExit(f'Port {port} already has a listener. Reuse the standard app or stop the old CogniShield server first. No alternate port was opened.')
    node = shutil.which('node')
    vite = ROOT / 'frontend/node_modules/vite/bin/vite.js'
    if not node or not vite.is_file():
        raise SystemExit('The existing Node/Vite runtime is missing. No dependencies were installed.')
    # Ordinary configuration comes from .env, never inherited acceptance-workspace overrides.
    env = {k:v for k,v in os.environ.items() if not k.startswith(('COGNISHIELD_', 'VITE_API_URL', 'VITE_WS_URL'))}
    env.update(VITE_API_URL='http://127.0.0.1:8000', VITE_WS_URL='ws://127.0.0.1:8000/ws', PYTHONDONTWRITEBYTECODE='1')
    processes = []
    try:
        processes.append(subprocess.Popen([sys.executable, '-B', str(ROOT/'backend/run_environment.py')], cwd=ROOT, env=env))
        processes.append(subprocess.Popen([node, str(vite), '--host', '127.0.0.1', '--port', '5173', '--strictPort'], cwd=ROOT/'frontend', env=env))
        print('CogniShield: http://127.0.0.1:5173 | API: http://127.0.0.1:8000 | Ctrl+C stops both.', flush=True)
        while all(p.poll() is None for p in processes):
            time.sleep(.5)
        raise SystemExit('A development server exited; both servers are being stopped.')
    except KeyboardInterrupt:
        pass
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
                else:
                    process.terminate()
                process.wait(timeout=30)


if __name__ == '__main__':
    main()
