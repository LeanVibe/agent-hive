#!/bin/bash
killall -15 python claude 2>/dev/null
python scripts/state_manager.py check "shutdown"
echo "Shutdown OK"
