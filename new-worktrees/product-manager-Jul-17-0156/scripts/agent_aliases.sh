#!/bin/bash
# LeanVibe Agent Hive - Convenient Agent Management Aliases

# Session management
alias agent-session="tmux attach-session -t agent-hive"
alias agent-list="tmux list-windows -t agent-hive"
alias agent-status="python scripts/agent_manager.py --status"

# Agent spawning
alias spawn-all="python scripts/agent_manager.py --spawn-all --force"
alias spawn-doc="python scripts/agent_manager.py --spawn documentation-agent --force"
alias spawn-intel="python scripts/agent_manager.py --spawn intelligence-agent --force"
alias spawn-orch="python scripts/agent_manager.py --spawn orchestration-agent --force"

# Agent attachment
alias attach-doc="tmux select-window -t agent-hive:agent-documentation-agent && tmux attach-session -t agent-hive"
alias attach-intel="tmux select-window -t agent-hive:agent-intelligence-agent && tmux attach-session -t agent-hive"
alias attach-orch="tmux select-window -t agent-hive:agent-orchestration-agent && tmux attach-session -t agent-hive"

# Agent management
alias kill-agents="python scripts/agent_manager.py --kill-all"
alias restart-doc="python scripts/agent_manager.py --restart documentation-agent"
alias restart-intel="python scripts/agent_manager.py --restart intelligence-agent"
alias restart-orch="python scripts/agent_manager.py --restart orchestration-agent"

# Quick access functions
agent-attach() {
    case $1 in
        doc|documentation)
            attach-doc
            ;;
        intel|intelligence)
            attach-intel
            ;;
        orch|orchestration)
            attach-orch
            ;;
        *)
            echo "Usage: agent-attach [doc|intel|orch]"
            echo "Available agents:"
            echo "  doc  - documentation-agent"
            echo "  intel - intelligence-agent"
            echo "  orch - orchestration-agent"
            ;;
    esac
}

agent-spawn() {
    case $1 in
        doc|documentation)
            python scripts/agent_manager.py --spawn documentation-agent --force
            ;;
        intel|intelligence)
            python scripts/agent_manager.py --spawn intelligence-agent --force
            ;;
        orch|orchestration)
            python scripts/agent_manager.py --spawn orchestration-agent --force
            ;;
        all)
            python scripts/agent_manager.py --spawn-all --force
            ;;
        *)
            echo "Usage: agent-spawn [doc|intel|orch|all]"
            echo "Available agents:"
            echo "  doc  - documentation-agent"
            echo "  intel - intelligence-agent"
            echo "  orch - orchestration-agent"
            echo "  all  - spawn all agents"
            ;;
    esac
}

agent-restart() {
    case $1 in
        doc|documentation)
            restart-doc
            ;;
        intel|intelligence)
            restart-intel
            ;;
        orch|orchestration)
            restart-orch
            ;;
        *)
            echo "Usage: agent-restart [doc|intel|orch]"
            echo "Available agents:"
            echo "  doc  - documentation-agent"
            echo "  intel - intelligence-agent"
            echo "  orch - orchestration-agent"
            ;;
    esac
}

# Show help
agent-help() {
    echo "🤖 LeanVibe Agent Hive - Management Commands"
    echo "============================================"
    echo ""
    echo "📊 Status & Monitoring:"
    echo "  agent-status          - Show current agent status"
    echo "  agent-list           - List tmux windows"
    echo "  agent-session        - Attach to main session"
    echo ""
    echo "🚀 Spawning:"
    echo "  agent-spawn <agent>  - Spawn specific agent"
    echo "  spawn-all            - Spawn all agents"
    echo "  spawn-doc            - Spawn documentation agent"
    echo "  spawn-intel          - Spawn intelligence agent"
    echo "  spawn-orch           - Spawn orchestration agent"
    echo ""
    echo "🔗 Attachment:"
    echo "  agent-attach <agent> - Attach to specific agent"
    echo "  attach-doc           - Attach to documentation agent"
    echo "  attach-intel         - Attach to intelligence agent"
    echo "  attach-orch          - Attach to orchestration agent"
    echo ""
    echo "🔄 Management:"
    echo "  agent-restart <agent> - Restart specific agent"
    echo "  kill-agents          - Kill all agents"
    echo ""
    echo "💡 Tips:"
    echo "  - Use Ctrl+B then D to detach from tmux"
    echo "  - Use Ctrl+B then W to list windows"
    echo "  - Use Ctrl+B then C to create new window"
    echo ""
    echo "📖 Examples:"
    echo "  agent-spawn all      # Spawn all agents"
    echo "  agent-attach doc     # Attach to documentation agent"
    echo "  agent-restart intel  # Restart intelligence agent"
}

echo "🤖 LeanVibe Agent Hive aliases loaded!"
echo "💡 Run 'agent-help' for available commands"