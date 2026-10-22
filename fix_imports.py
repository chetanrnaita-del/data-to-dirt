import os
import re

dirs_to_process = ['src/analyzer', 'src/fileclean_core', 'src/security']

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Replace from core... with from src.fileclean_core...
    content = re.sub(r'^from core\b', 'from src.fileclean_core', content, flags=re.MULTILINE)
    content = re.sub(r'^import core\b', 'import src.fileclean_core', content, flags=re.MULTILINE)
    
    # Replace from analyzer... with from src.analyzer...
    content = re.sub(r'^from analyzer\b', 'from src.analyzer', content, flags=re.MULTILINE)
    content = re.sub(r'^import analyzer\b', 'import src.analyzer', content, flags=re.MULTILINE)
    
    # Replace from security... with from src.security...
    content = re.sub(r'^from security\b', 'from src.security', content, flags=re.MULTILINE)
    content = re.sub(r'^import security\b', 'import src.security', content, flags=re.MULTILINE)

    # Some imports might be like: from core.config import Config
    # The above re.sub covers it because \b matches the dot or space after "core"
    
    with open(filepath, 'w') as f:
        f.write(content)

for d in dirs_to_process:
    for root, dirs, files in os.walk(d):
        for file in files:
            if file.endswith('.py'):
                process_file(os.path.join(root, file))

print("Imports fixed.")
