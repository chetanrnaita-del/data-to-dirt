import json

scanned_items = [
    {"file_id": "1", "name": "A.pdf", "md5": "abc", "size_bytes": 100, "size_formatted": "100B", "last_modified_epoch_s": 0},
    {"file_id": "2", "name": "A.pdf", "md5": "abc", "size_bytes": 100, "size_formatted": "100B", "last_modified_epoch_s": 0}
]

files_by_md5 = {}
for item in scanned_items:
    if item["md5"]:
        files_by_md5.setdefault(item["md5"], []).append(item)

for item in scanned_items:
    reasons = []
    if item["md5"] and len(files_by_md5[item["md5"]]) > 1:
        if item["file_id"] != files_by_md5[item["md5"]][0]["file_id"]:
            reasons.append("Potential duplicate (md5 match)")
    
    if reasons:
        item["is_dark_data_candidate"] = True
        item["dark_data_reason"] = " | ".join(reasons)
    else:
        item["is_dark_data_candidate"] = False
        item["dark_data_reason"] = ""

dark = [f for f in scanned_items if f["is_dark_data_candidate"]]
print(json.dumps(dark, indent=2))
