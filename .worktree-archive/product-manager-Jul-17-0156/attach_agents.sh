#!/bin/bash
# LeanVibe Agent Hive - Attach to Agent Windows
# Session: agent-hive
# Generated: 2025-07-15 13:57:45

echo 'Available agents:'
echo '1. documentation-agent (agent-documentation-agent)'
echo '2. orchestration-agent (agent-orchestration-agent)'
echo '3. intelligence-agent (agent-intelligence-agent)'

echo 'Commands:'
echo 'tmux attach-session -t agent-hive  # Attach to session'
echo 'tmux list-windows -t agent-hive    # List windows'
echo 'tmux select-window -t agent-hive:agent-documentation-agent && tmux attach-session -t agent-hive  # Attach to documentation-agent'
echo 'tmux select-window -t agent-hive:agent-orchestration-agent && tmux attach-session -t agent-hive  # Attach to orchestration-agent'
echo 'tmux select-window -t agent-hive:agent-intelligence-agent && tmux attach-session -t agent-hive  # Attach to intelligence-agent'
