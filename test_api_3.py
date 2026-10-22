import urllib.request
import json

url = "http://localhost:8088/api/scan/request"
payload = json.dumps({"folder_path": "/Users/narayan/Desktop", "session_only": True}).encode('utf-8')
req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req) as response:
        print("STATUS:", response.status)
        data = response.read().decode('utf-8')
        print("RESPONSE:", data)
except Exception as e:
    print("ERROR:", e)
    if hasattr(e, 'read'):
        print("BODY:", e.read().decode('utf-8'))
