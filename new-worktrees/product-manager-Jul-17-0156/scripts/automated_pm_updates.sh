#!/bin/bash
# Automated PM Status Updates
# Runs every 3 minutes to get status from PM agent via fixed communication system
# Includes kill switch and comprehensive logging

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/../coordination_pm_updates.log"
PID_FILE="$SCRIPT_DIR/../automated_pm_updates.pid"
KILL_FILE="$SCRIPT_DIR/../KILL_PM_UPDATES"
UPDATE_INTERVAL=180  # 3 minutes in seconds

# Initialize log
echo "=== Automated PM Updates Started: $(date) ===" >> "$LOG_FILE"

# Function to log with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Function to send status request to PM agent
send_pm_status_request() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    log_message "Sending status request to PM agent..."
    
    # Use fixed agent communication system
    local response=$(python3 "$SCRIPT_DIR/fixed_agent_communication.py" \
        --agent pm-agent \
        --message "AUTOMATED STATUS UPDATE: Please provide current coordination status, active agents, PR status, and any urgent issues. Time: $timestamp" \
        2>&1)
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_message "✅ PM STATUS REQUEST SENT - Response: $response"
    else
        log_message "❌ PM STATUS REQUEST FAILED - Error: $response"
    fi
    
    return $exit_code
}

# Function to check for kill switch
check_kill_switch() {
    if [ -f "$KILL_FILE" ]; then
        log_message "🛑 KILL SWITCH ACTIVATED - Stopping automated PM updates"
        echo "Automated PM updates stopped by kill switch at $(date)" >> "$LOG_FILE"
        rm -f "$PID_FILE" "$KILL_FILE"
        exit 0
    fi
}

# Function to handle cleanup on exit
cleanup() {
    log_message "🏁 Automated PM updates stopping (cleanup signal received)"
    rm -f "$PID_FILE"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT SIGQUIT

# Check if already running
if [ -f "$PID_FILE" ]; then
    old_pid=$(cat "$PID_FILE")
    if kill -0 "$old_pid" 2>/dev/null; then
        echo "Automated PM updates already running (PID: $old_pid)"
        echo "To stop: touch $KILL_FILE or kill $old_pid"
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

# Store current PID
echo $$ > "$PID_FILE"

log_message "🚀 Automated PM updates started (PID: $$)"
log_message "📝 Kill switch file: $KILL_FILE"
log_message "⏰ Update interval: $UPDATE_INTERVAL seconds"

# Main monitoring loop
while true; do
    # Check kill switch
    check_kill_switch
    
    # Send status request
    send_pm_status_request
    
    # Log next update time
    next_update=$(date -d "+$UPDATE_INTERVAL seconds" '+%Y-%m-%d %H:%M:%S')
    log_message "⏳ Next update scheduled for: $next_update"
    
    # Wait for next interval
    sleep $UPDATE_INTERVAL
done