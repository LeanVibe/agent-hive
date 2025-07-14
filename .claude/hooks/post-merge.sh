#!/bin/bash
set -e

# Spawn documenter
python scripts/spawn.py "Generate docs" "think"
mv generated.md docs/updated.md
echo "Post-merge docs OK"
