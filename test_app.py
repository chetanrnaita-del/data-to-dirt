import sys
import os
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from src.app.server import create_flask_app

app = create_flask_app()
app.testing = True
client = app.test_client()

data = {
    "scan_type": "browser_files",
    "folder_path": None,
    "files": [
        {"name": "test.txt", "size": None, "lastModified": None}
    ]
}

response = client.post('/api/scan/request', json=data)
print(f"Status: {response.status_code}")
print(f"Data: {response.data.decode('utf-8')}")
