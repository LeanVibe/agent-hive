#!/bin/bash
agent=$1
killall -9 claude_$agent  # Stub
python scripts/state_manager.py checkpoint "emergency-$agent"
echo "Emergency OK"
