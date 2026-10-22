import requests
import json
import sys

# Create some test files
import os
os.makedirs("test_scan_folder", exist_ok=True)
with open("test_scan_folder/stale.txt", "w") as f:
    f.write("test")
# Make it stale (200 days old)
import time
t = time.time() - 200 * 86400
os.utime("test_scan_folder/stale.txt", (t, t))

url = "http://127.0.0.1:8088/api/scan/request"
payload = {"folder_path": os.path.abspath("test_scan_folder"), "session_only": True}
headers = {"Content-Type": "application/json"}

try:
    response = requests.post(url, json=payload, headers=headers)
    print("STATUS:", response.status_code)
    print("RESPONSE:", json.dumps(response.json(), indent=2))
except Exception as e:
    print("ERROR:", e)
