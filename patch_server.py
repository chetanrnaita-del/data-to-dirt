import re

with open('src/app/server.py', 'r') as f:
    content = f.read()

# We need a global scanner instance
content = content.replace("from src.services.analytics import AnalyticsService\n", 
"""from src.services.analytics import AnalyticsService
from src.services.scanner import FileScanner

global_scanner = FileScanner()
""")

# Rewrite api_scan_request
new_scan_request = """    @app.route("/api/scan/request", methods=["POST"])
    def api_scan_request():
        data = request.get_json() or {}
        folder_path = data.get("folder_path", "").strip()
        session_only = data.get("session_only", True)

        state = load_state()
        state["scanner"]["state"] = "SCANNING"
        
        target_path = folder_path or str(Path.home() / "Desktop")
        state["scanner"]["current_folder"] = target_path

        try:
            global_scanner.request_access(target_path, session_only)
            scanned_items = global_scanner.scan()
            
            files = [item.to_dict() for item in scanned_items]
            # Map dark data reasoning
            for f in files:
                f["size_formatted"] = format_bytes(f["size_bytes"])
                f["category"] = "dark_data" if f["is_dark_data_candidate"] else "normal"
                f["dark_data_tag"] = f["dark_data_reason"] or "Normal"
                
            state["scanner"]["files"] = files
            state["scanner"]["state"] = "COMPLETED"
        except Exception as e:
            state["scanner"]["state"] = "ERROR"
            print(f"Error scanning: {e}")
            
        save_state(state)

        return jsonify({
            "status": "completed",
            "folder": state["scanner"]["current_folder"],
            "files_found": len(state["scanner"]["files"]),
            "files": state["scanner"]["files"],
            "session_only": session_only
        })"""

content = re.sub(r'    @app\.route\("/api/scan/request", methods=\["POST"\]\).*?(?=    @app\.route\("/api/scan/revoke", methods=\["POST"\]\))', new_scan_request + "\n", content, flags=re.DOTALL)

with open('src/app/server.py', 'w') as f:
    f.write(content)

