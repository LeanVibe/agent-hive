#!/bin/bash
# Control script for real-time coordination event monitoring

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/../coordination_monitor.pid"
LOG_FILE="$SCRIPT_DIR/../coordination_monitor.log"
ALERTS_FILE="$SCRIPT_DIR/../coordination_alerts.json"

case "$1" in
    start)
        echo "🚀 Starting real-time coordination monitoring..."
        nohup python3 "$SCRIPT_DIR/realtime_coordination_monitor.py" \
            --alerts-file "$ALERTS_FILE" \
            > "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        echo "Started with PID $(cat $PID_FILE)"
        echo "📋 Monitor: $LOG_FILE"
        echo "📡 Events: $ALERTS_FILE"
        ;;
    stop)
        if [ -f "$PID_FILE" ]; then
            pid=$(cat "$PID_FILE")
            if kill -0 "$pid" 2>/dev/null; then
                echo "🛑 Stopping coordination monitoring (PID: $pid)..."
                kill "$pid"
                rm -f "$PID_FILE"
                echo "Stopped."
            else
                echo "❌ Process not running (stale PID file)"
                rm -f "$PID_FILE"
            fi
        else
            echo "❌ Not running"
        fi
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        if [ -f "$PID_FILE" ]; then
            pid=$(cat "$PID_FILE")
            if kill -0 "$pid" 2>/dev/null; then
                echo "✅ Running (PID: $pid)"
                echo "📊 Statistics:"
                python3 "$SCRIPT_DIR/realtime_coordination_monitor.py" --stats --alerts-file "$ALERTS_FILE"
                echo ""
                echo "📋 Recent activity:"
                tail -n 5 "$LOG_FILE" 2>/dev/null || echo "No log entries yet"
            else
                echo "❌ Not running (stale PID file)"
                rm -f "$PID_FILE"
            fi
        else
            echo "❌ Not running"
        fi
        ;;
    logs)
        echo "📋 Recent coordination monitoring logs:"
        tail -n "${2:-20}" "$LOG_FILE" 2>/dev/null || echo "No log file found"
        ;;
    events)
        echo "📨 Recent coordination events:"
        tail -n "${2:-10}" "$ALERTS_FILE" 2>/dev/null | while read -r line; do
            if [ -n "$line" ]; then
                echo "$line" | python3 -m json.tool 2>/dev/null || echo "$line"
                echo "---"
            fi
        done
        ;;
    test-event)
        echo "🧪 Generating test coordination event..."
        test_event="{\"type\": \"DEADLINE_WARNING\", \"task_id\": \"test-task-123\", \"agent_id\": \"test-agent\", \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)\", \"time_remaining\": \"30 minutes\"}"
        echo "$test_event" >> "$ALERTS_FILE"
        echo "Test event added to $ALERTS_FILE"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [lines]|events [count]|test-event}"
        echo ""
        echo "Commands:"
        echo "  start      - Start real-time coordination monitoring"
        echo "  stop       - Stop coordination monitoring"
        echo "  restart    - Restart coordination monitoring"
        echo "  status     - Check status and show statistics"
        echo "  logs       - Show recent monitoring logs (default: 20 lines)"
        echo "  events     - Show recent coordination events (default: 10 events)"
        echo "  test-event - Generate a test coordination event"
        echo ""
        echo "Real-time Event-Driven Coordination System"
        echo "Monitors: $ALERTS_FILE"
        echo "Triggers: PM agent notifications, agent reminders, emergency protocols"
        exit 1
        ;;
esac