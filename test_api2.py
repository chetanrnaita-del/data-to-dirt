import urllib.request
import json
import os
import time

os.makedirs("test_scan_folder", exist_ok=True)
with open("test_scan_folder/stale.txt", "w") as f:
    f.write("test")
t = time.time() - 200 * 86400
os.utime("test_scan_folder/stale.txt", (t, t))

url = "http://127.0.0.1:8088/api/scan/request"
payload = json.dumps({"folder_path": os.path.abspath("test_scan_folder"), "session_only": True}).encode('utf-8')
req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req) as response:
        print("STATUS:", response.status)
        data = json.loads(response.read().decode('utf-8'))
        print("RESPONSE:", json.dumps(data, indent=2))
except Exception as e:
    print("ERROR:", e)
