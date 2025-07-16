#!/bin/bash
#
# PM Agent Status Updater - Automated Coordination Monitoring
# 
# Specification:
# - Runs every 3 minutes
# - Sends status requests to pm-agent-new
# - Logs responses with timestamps and update counter
# - Background daemon with easy kill mechanism
# - Critical phase coordination automation
#
# Usage:
#   ./scripts/pm_status_updater.sh start    # Start background monitoring
#   ./scripts/pm_status_updater.sh stop     # Stop monitoring
#   ./scripts/pm_status_updater.sh status   # Check if running
#   ./scripts/pm_status_updater.sh logs     # View recent logs
#

set -euo pipefail

# Configuration
SCRIPT_NAME="pm_status_updater"
PID_FILE="/tmp/${SCRIPT_NAME}.pid"
LOG_FILE=".claude/logs/pm_coordination.log"
UPDATE_INTERVAL=180  # 3 minutes in seconds
PM_AGENT_TARGET="pm-agent-new"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function with timestamp
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

# Status request function
send_status_request() {
    local update_count="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    log_message "INFO" "Update #$update_count - Sending status request to $PM_AGENT_TARGET"
    
    # Try multiple communication methods
    local response=""
    local method_used=""
    
    # Method 1: Fixed agent communication script
    if [[ -f "scripts/fixed_agent_communication.py" ]]; then
        response=$(python3 scripts/fixed_agent_communication.py \
            --agent "$PM_AGENT_TARGET" \
            --message "STATUS REQUEST #$update_count: Foundation Epic coordination status. PR #69 merged, monitoring PR #70 conflicts. Automated update at $timestamp" \
            2>&1 || echo "COMMUNICATION_FAILED")
        method_used="fixed_agent_communication"
    
    # Method 2: Standard agent communication
    elif [[ -f "scripts/send_agent_message.py" ]]; then
        response=$(python3 scripts/send_agent_message.py \
            --agent "$PM_AGENT_TARGET" \
            --message "STATUS REQUEST #$update_count: Foundation Epic coordination status. PR #69 merged, monitoring PR #70 conflicts. Automated update at $timestamp" \
            2>&1 || echo "COMMUNICATION_FAILED")
        method_used="send_agent_message"
    
    # Method 3: Direct tmux communication
    else
        response=$(tmux send-keys -t "agent-hive:agent-$PM_AGENT_TARGET" \
            "STATUS REQUEST #$update_count: Foundation Epic coordination status. PR #69 merged, monitoring PR #70 conflicts. Automated update at $timestamp" Enter \
            2>&1 || echo "TMUX_COMMUNICATION_FAILED")
        method_used="direct_tmux"
    fi
    
    # Log response
    if [[ "$response" == *"FAILED"* ]]; then
        log_message "ERROR" "Update #$update_count failed via $method_used: $response"
    else
        log_message "SUCCESS" "Update #$update_count sent via $method_used"
        log_message "RESPONSE" "Agent response: $response"
    fi
    
    # Log system status
    log_message "SYSTEM" "Update #$update_count complete - next update in $UPDATE_INTERVAL seconds"
}

# Main monitoring loop
run_monitoring() {
    local update_count=0
    
    log_message "START" "PM Agent Status Updater started - PID: $$"
    log_message "CONFIG" "Target: $PM_AGENT_TARGET, Interval: ${UPDATE_INTERVAL}s, Log: $LOG_FILE"
    
    # Save PID for stop functionality
    echo $$ > "$PID_FILE"
    
    while true; do
        ((update_count++))
        
        # Send status request
        send_status_request "$update_count"
        
        # Wait for next interval
        sleep "$UPDATE_INTERVAL"
    done
}

# Start monitoring in background
start_monitoring() {
    if is_running; then
        echo "❌ PM Status Updater is already running (PID: $(cat "$PID_FILE"))"
        exit 1
    fi
    
    echo "🚀 Starting PM Agent Status Updater..."
    echo "📁 Log file: $LOG_FILE"
    echo "⏱️  Update interval: ${UPDATE_INTERVAL}s (3 minutes)"
    echo "🎯 Target agent: $PM_AGENT_TARGET"
    
    # Start in background
    nohup bash "$0" _internal_run > /dev/null 2>&1 &
    local pid=$!
    
    # Verify it started
    sleep 1
    if kill -0 "$pid" 2>/dev/null; then
        echo "✅ PM Status Updater started successfully (PID: $pid)"
        echo "💡 Use: $0 stop    # To stop monitoring"
        echo "💡 Use: $0 logs    # To view logs"
    else
        echo "❌ Failed to start PM Status Updater"
        exit 1
    fi
}

# Stop monitoring
stop_monitoring() {
    if ! is_running; then
        echo "⚠️  PM Status Updater is not running"
        return 0
    fi
    
    local pid=$(cat "$PID_FILE")
    echo "🛑 Stopping PM Status Updater (PID: $pid)..."
    
    if kill "$pid" 2>/dev/null; then
        # Wait for graceful shutdown
        local count=0
        while kill -0 "$pid" 2>/dev/null && [[ $count -lt 10 ]]; do
            sleep 0.5
            ((count++))
        done
        
        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null || true
        fi
        
        rm -f "$PID_FILE"
        log_message "STOP" "PM Status Updater stopped"
        echo "✅ PM Status Updater stopped successfully"
    else
        echo "❌ Failed to stop PM Status Updater"
        rm -f "$PID_FILE"  # Clean up stale PID file
        exit 1
    fi
}

# Check if monitoring is running
is_running() {
    [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

# Show status
show_status() {
    if is_running; then
        local pid=$(cat "$PID_FILE")
        echo "✅ PM Status Updater is running (PID: $pid)"
        echo "📁 Log file: $LOG_FILE"
        echo "⏱️  Update interval: ${UPDATE_INTERVAL}s"
        echo "🎯 Target agent: $PM_AGENT_TARGET"
        
        # Show recent activity
        if [[ -f "$LOG_FILE" ]]; then
            echo ""
            echo "📋 Recent activity (last 5 lines):"
            tail -5 "$LOG_FILE" | sed 's/^/   /'
        fi
    else
        echo "❌ PM Status Updater is not running"
        echo "💡 Use: $0 start    # To start monitoring"
    fi
}

# Show logs
show_logs() {
    if [[ -f "$LOG_FILE" ]]; then
        echo "📋 PM Agent Coordination Logs:"
        echo "======================================"
        tail -20 "$LOG_FILE"
        echo ""
        echo "💡 Use: tail -f $LOG_FILE    # To follow logs in real-time"
    else
        echo "⚠️  No log file found: $LOG_FILE"
    fi
}

# Signal handlers for graceful shutdown
trap 'log_message "SIGNAL" "Received SIGTERM, shutting down..."; exit 0' TERM
trap 'log_message "SIGNAL" "Received SIGINT, shutting down..."; exit 0' INT

# Main command handling
case "${1:-}" in
    start)
        start_monitoring
        ;;
    stop)
        stop_monitoring
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    restart)
        stop_monitoring
        sleep 1
        start_monitoring
        ;;
    _internal_run)
        # Internal command for background execution
        run_monitoring
        ;;
    *)
        echo "PM Agent Status Updater - Automated Coordination Monitoring"
        echo ""
        echo "Usage: $0 {start|stop|status|logs|restart}"
        echo ""
        echo "Commands:"
        echo "  start    Start background monitoring (3-minute intervals)"
        echo "  stop     Stop monitoring daemon"
        echo "  status   Check if monitoring is running"
        echo "  logs     Show recent coordination logs"
        echo "  restart  Stop and start monitoring"
        echo ""
        echo "Configuration:"
        echo "  Target: $PM_AGENT_TARGET"
        echo "  Interval: ${UPDATE_INTERVAL}s (3 minutes)"
        echo "  Log file: $LOG_FILE"
        echo ""
        echo "Foundation Epic Phase 1 - Critical coordination automation"
        exit 1
        ;;
esac