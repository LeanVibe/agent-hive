import json
import pathlib
import sys


def find_test_files(source_path):
    path = pathlib.Path(source_path)
    stem = path.stem
    patterns = [f"tests/test_{stem}.py"]
    for p in patterns:
        if pathlib.Path(p).exists():
            return True
    return False


data = json.load(sys.stdin)
path = data.get("file_path", "")
if path.endswith(".py") and not find_test_files(path):
    print("No tests!", file=sys.stderr)
    sys.exit(1)
print("Tests OK")
