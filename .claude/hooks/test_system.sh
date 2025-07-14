#!/bin/bash
./setup.sh
./start_orchestrator.sh &
sleep 10
# Simulate command (stub; assume claude /orchestrate via echo)
echo "/orchestrate --workflow test"
python scripts/monitor.py
python scripts/health_check.py
./shutdown.sh

# Verify
if [ -f ".claude/state.db" ] && [ -s ".claude/logs/app.log" ]; then
  echo "Test passed"
else
  echo "Test failed"
fi
