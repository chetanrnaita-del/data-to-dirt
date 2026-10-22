import json
from src.app.server import create_flask_app

app = create_flask_app()
client = app.test_client()

response = client.post('/api/scan/request', 
    json={"scan_type": "browser_files", "files": [{"name": "test.jpg", "size": 1000, "lastModified": 1600000000}]}
)
print("Status:", response.status_code)
print("Data:", response.get_data(as_text=True))
