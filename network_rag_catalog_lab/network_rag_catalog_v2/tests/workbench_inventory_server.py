"""Isolated browser-test server: temporary inventory, no production write path."""
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn
from app.devices import inventory
from app.workbench.api import create_app


if __name__ == '__main__':
    source = inventory.INVENTORY_FILE
    original = source.read_bytes()
    modified = source.stat().st_mtime_ns
    with TemporaryDirectory(prefix='inventory-browser-') as directory:
        isolated = Path(directory) / 'devices.json'
        isolated.write_bytes(original)
        inventory.INVENTORY_FILE = isolated
        try:
            uvicorn.run(create_app(), host='127.0.0.1', port=8000)
        finally:
            assert source.read_bytes() == original and source.stat().st_mtime_ns == modified
