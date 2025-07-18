#!/bin/bash
set -euo pipefail

trap " ./shutdown.sh " INT TERM

python scripts/orchestrator.py & 
ORCH_PID=$!

for agent in backend frontend ios infra; do
  cd ../wt-$agent
  # Stub claude start; for test, echo
  echo "Starting $agent agent"
  cd -
done

while true; do
  python scripts/health_check.py
  sleep 60
done
