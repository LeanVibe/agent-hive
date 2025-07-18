#!/bin/bash
# Control script for automated PM updates

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/../automated_pm_updates.pid"
KILL_FILE="$SCRIPT_DIR/../KILL_PM_UPDATES"
LOG_FILE="$SCRIPT_DIR/../coordination_pm_updates.log"

case "$1" in
    start)
        echo "🚀 Starting automated PM updates..."
        nohup "$SCRIPT_DIR/automated_pm_updates.sh" > /dev/null 2>&1 &
        echo "Started in background. Check status with: $0 status"
        ;;
    stop)
        echo "🛑 Stopping automated PM updates..."
        touch "$KILL_FILE"
        sleep 2
        if [ -f "$PID_FILE" ]; then
            pid=$(cat "$PID_FILE")
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid"
                echo "Force stopped PID $pid"
            fi
            rm -f "$PID_FILE"
        fi
        rm -f "$KILL_FILE"
        echo "Stopped."
        ;;
    status)
        if [ -f "$PID_FILE" ]; then
            pid=$(cat "$PID_FILE")
            if kill -0 "$pid" 2>/dev/null; then
                echo "✅ Running (PID: $pid)"
                echo "📊 Recent activity:"
                tail -n 5 "$LOG_FILE" 2>/dev/null || echo "No log entries yet"
            else
                echo "❌ Not running (stale PID file)"
                rm -f "$PID_FILE"
            fi
        else
            echo "❌ Not running"
        fi
        ;;
    log)
        echo "📋 Recent PM update log:"
        tail -n "${2:-20}" "$LOG_FILE" 2>/dev/null || echo "No log file found"
        ;;
    *)
        echo "Usage: $0 {start|stop|status|log [lines]}"
        echo "  start  - Start automated PM updates in background"
        echo "  stop   - Stop automated PM updates"
        echo "  status - Check if running and show recent activity"
        echo "  log    - Show recent log entries (default: 20 lines)"
        exit 1
        ;;
esac