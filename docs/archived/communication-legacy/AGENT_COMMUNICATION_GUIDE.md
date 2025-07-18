# Agent Communication Guide

## 🚀 **Automatic Message Delivery Fixed**

The agent-to-agent communication system has been enhanced to eliminate manual Enter key requirements. All messages now submit automatically.

## 📡 **Communication Methods**

### 1. **Direct Agent-to-Agent Communication**

```bash
# From within any agent directory
python ../scripts/agent_communicate.py <target_agent> "<message>" [from_agent]

# Examples:
python ../scripts/agent_communicate.py documentation-agent "Please update API docs for new feature"
python ../scripts/agent_communicate.py pm-agent "Sprint planning needed" quality-agent
```

### 2. **Broadcast Messages to All Agents**

```bash
# Send message to all agents
python scripts/send_agent_message.py --ping-all

# Send custom message to specific agent
python scripts/send_agent_message.py --agent pm-agent --message "Custom message here"
```

### 3. **Testing Communication Methods**

```bash
# Test all methods for specific agent
python scripts/send_agent_message.py --test documentation-agent
```

## 🔧 **Technical Implementation**

### **Buffer-Based Reliable Delivery**
- Uses tmux `set-buffer` and `paste-buffer` for reliable message handling
- Clears existing input with `C-c` before sending
- Automatically submits with `Enter` after brief pause
- Handles long messages without truncation

### **Message Flow**
1. **Clear Input**: `tmux send-keys -t session:window "C-c"`
2. **Set Buffer**: `tmux set-buffer "message content"`
3. **Paste Content**: `tmux paste-buffer -t session:window`
4. **Auto-Submit**: `tmux send-keys -t session:window "Enter"`

## 📊 **Message Logging**

All communications are automatically logged to SQLite database:
- **Prompt Statistics**: Available at `http://localhost:8000/api/prompts/stats`
- **PM Review**: Use `python scripts/pm_review_prompts.py` for optimization
- **Success Tracking**: Currently 95.7% success rate across 23+ messages

## 🤖 **Available Agents**

| Agent | Window Name | Purpose |
|-------|-------------|---------|
| `documentation-agent` | `agent-documentation-agent` | Documentation and guides |
| `orchestration-agent` | `agent-orchestration-agent` | Multi-agent coordination |
| `pm-agent` | `agent-pm-agent` | Project management and XP |
| `intelligence-agent` | `agent-intelligence-agent` | AI and ML capabilities |
| `integration-agent` | `agent-integration-agent` | System integration |
| `quality-agent` | `agent-quality-agent` | Testing and quality |

## 🎯 **Best Practices**

### **Message Format**
- **Clear Subject**: Start with purpose
- **Actionable Content**: Specific requests
- **Context**: Provide necessary background
- **Courtesy**: Include "please" and "thank you"

### **Example Good Messages**
```bash
# Good: Specific and actionable
python ../scripts/agent_communicate.py documentation-agent "Please update the API reference for the new prompt_logger module. Include usage examples and parameter descriptions."

# Good: Coordination request
python ../scripts/agent_communicate.py pm-agent "Sprint review needed: All feature branches ready for integration. Please coordinate the merge process."
```

### **Example Poor Messages**
```bash
# Poor: Too vague
python ../scripts/agent_communicate.py documentation-agent "help with docs"

# Poor: No context
python ../scripts/agent_communicate.py pm-agent "something is wrong"
```

## 🔄 **Troubleshooting**

### **If Message Not Delivered**
1. Check tmux session exists: `tmux list-sessions`
2. Verify agent window: `tmux list-windows -t agent-hive`
3. Test with: `python scripts/send_agent_message.py --test <agent>`

### **If Agent Not Responding**
1. Check agent activity: `python scripts/check_agent_progress.py`
2. Attach to agent: `tmux attach-session -t agent-hive:agent-<name>`
3. Restart agent: `python scripts/agent_manager.py --restart <agent>`

## 📈 **Monitoring**

- **Real-time Dashboard**: `http://localhost:8000`
- **Agent Status**: `python scripts/agent_manager.py --status`
- **Communication Log**: `python scripts/pm_review_prompts.py`
- **Progress Check**: `python scripts/check_agent_progress.py`

## ✅ **Success Indicators**

- ✅ Messages submit automatically without manual Enter
- ✅ 95.7% success rate in message delivery
- ✅ All agent-to-agent communications logged
- ✅ PM review system for optimization
- ✅ Real-time monitoring dashboard

The communication system now provides reliable, automatic message delivery between all agents with comprehensive logging and monitoring capabilities.