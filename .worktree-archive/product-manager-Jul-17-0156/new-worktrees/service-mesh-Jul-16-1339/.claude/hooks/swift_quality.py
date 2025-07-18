import sys
import subprocess
import json

data = json.load(sys.stdin)
path = data.get("file_path", "")
if path.endswith(".swift"):
    try:
        subprocess.check_call(["echo", "Swift OK"])  # Stub swiftlint
    except:
        print("Swift failed", file=sys.stderr)
        sys.exit(1)
print("OK")
