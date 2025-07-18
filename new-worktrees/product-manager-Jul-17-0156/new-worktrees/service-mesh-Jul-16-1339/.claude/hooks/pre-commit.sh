#!/bin/bash
set -e

python hooks/ensure_tests.py || exit 1
bash hooks/gemini_review.sh "$file" || true  # Assume file from git
python hooks/quality_gate.py || exit 1
echo "Pre-commit OK"  # Testable
