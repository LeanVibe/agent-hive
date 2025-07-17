#!/bin/bash
# Enhanced Agent Spawner with Hybrid Communication Protocol
# 
# This script automatically includes the hybrid communication protocol
# in all newly spawned agents.

set -e

# Default values
SESSION="agent-hive"
SPAWN_TMUX=true
SEND_PROMPT=true

# Help function
show_help() {
    echo "Enhanced Agent Spawner with Hybrid Communication Protocol"
    echo ""
    echo "Usage: $0 --type AGENT_TYPE [OPTIONS]"
    echo ""
    echo "Required:"
    echo "  --type TYPE        Agent type to spawn"
    echo ""
    echo "Options:"
    echo "  --task TASK        Specific task description"
    echo "  --priority NUM     Priority level (lower = higher priority)"
    echo "  --session NAME     Tmux session name (default: agent-hive)"
    echo "  --no-spawn         Create worktree only, don't spawn in tmux"
    echo "  --no-prompt        Don't send starting prompt"
    echo "  --list             List available agent types"
    echo "  --help             Show this help"
    echo ""
    echo "Available Agent Types:"
    echo "  integration-specialist     API Gateway and Service Integration"
    echo "  frontend-dashboard        Frontend Dashboard and UI"
    echo "  service-mesh              Service Mesh and Infrastructure"
    echo "  monitoring-system         Monitoring and Observability"
    echo "  security-hardening        Security and Authentication"
    echo "  documentation-agent       Documentation and Knowledge Management"
    echo "  quality-assurance         Quality Assurance and Testing"
    echo "  performance-optimization  Performance and Scalability"
    echo ""
    echo "Examples:"
    echo "  $0 --type integration-specialist --task 'Fix API Gateway tests'"
    echo "  $0 --type frontend-dashboard --priority 1.2"
    echo "  $0 --type monitoring-system --no-spawn"
    echo ""
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --type)
            AGENT_TYPE="$2"
            shift 2
            ;;
        --task)
            TASK="$2"
            shift 2
            ;;
        --priority)
            PRIORITY="$2"
            shift 2
            ;;
        --session)
            SESSION="$2"
            shift 2
            ;;
        --no-spawn)
            SPAWN_TMUX=false
            shift
            ;;
        --no-prompt)
            SEND_PROMPT=false
            shift
            ;;
        --list)
            python3 scripts/enhanced_agent_spawner.py --list-types
            exit 0
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$AGENT_TYPE" ]; then
    echo "❌ Error: --type is required"
    echo "Use --list to see available agent types"
    echo "Use --help for usage information"
    exit 1
fi

echo "🚀 ENHANCED AGENT SPAWNER - Protocol Integration"
echo "================================================="
echo "Agent Type: $AGENT_TYPE"
echo "Session: $SESSION"
echo "Spawn in tmux: $SPAWN_TMUX"
echo "Send prompt: $SEND_PROMPT"
if [ -n "$TASK" ]; then
    echo "Task: $TASK"
fi
if [ -n "$PRIORITY" ]; then
    echo "Priority: $PRIORITY"
fi
echo ""

# Build command
CMD="python3 scripts/enhanced_agent_spawner.py --agent-type $AGENT_TYPE --session $SESSION"

if [ -n "$TASK" ]; then
    CMD="$CMD --task '$TASK'"
fi

if [ -n "$PRIORITY" ]; then
    CMD="$CMD --priority $PRIORITY"
fi

if [ "$SPAWN_TMUX" = false ]; then
    CMD="$CMD --no-spawn"
fi

if [ "$SEND_PROMPT" = false ]; then
    CMD="$CMD --no-prompt"
fi

# Execute command
echo "🔄 Executing: $CMD"
echo ""
eval $CMD

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ PROTOCOL INTEGRATION COMPLETE"
    echo "🔗 Hybrid communication protocol automatically enabled"
    echo "📋 Agent will receive protocol instructions on spawn"
    echo "🚨 Protocol compliance monitoring: ACTIVE"
    echo ""
    if [ "$SPAWN_TMUX" = true ]; then
        echo "💡 To attach to agent: tmux attach-session -t $SESSION"
        echo "💡 To view all agents: python3 scripts/agent_manager.py --status"
    fi
else
    echo ""
    echo "❌ AGENT SPAWN FAILED"
    echo "Check error messages above for details"
    exit 1
fi