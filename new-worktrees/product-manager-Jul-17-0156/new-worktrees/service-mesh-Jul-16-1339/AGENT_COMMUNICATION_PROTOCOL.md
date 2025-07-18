# 🤖 Agent-to-Agent Communication Protocol

## 🎯 **Purpose**
This document establishes clear communication pathways for agents to request help, coordinate work, and escalate to humans when needed.

## 📞 **Basic Agent Communication**

### **How to Send Messages Between Agents**
```bash
# Basic syntax
python scripts/send_agent_message.py --agent <target-agent-name> --message "<your-message>"

# Examples
python scripts/send_agent_message.py --agent pm-agent --message "I need help with PR conflicts"
python scripts/send_agent_message.py --agent documentation-agent --message "Can you review my changes?"
```

### **Available Agents**
- `pm-agent` - Project management and coordination
- `documentation-agent` - Documentation and writing
- `integration-agent` - System integration
- `quality-agent` - Quality assurance and testing
- `intelligence-agent` - AI and ML components
- `orchestration-agent` - Multi-agent coordination

## 🆘 **When to Ask for Help**

### **Request Help from PM-Agent When:**
- ❌ Stuck on PR conflicts for >15 minutes
- ❌ Unclear about task requirements
- ❌ Need coordination with other agents
- ❌ Facing technical blockers
- ❌ Unsure about merge priorities

### **Example Help Requests:**
```bash
# Conflict Resolution Help
python scripts/send_agent_message.py --agent pm-agent --message "🆘 HELP NEEDED: Stuck on PR conflicts

I'm documentation-agent working on PR #38 (Monitoring System).

🚨 CURRENT ISSUE:
- Rebase conflicts in multiple files
- Unsure which changes to keep vs main branch
- Been stuck for 20 minutes

🔧 SPECIFIC CONFLICTS:
- observability/__init__.py 
- dashboard/enhanced_server.py
- Multiple logging files

❓ QUESTIONS:
1. Should I accept main branch changes for infrastructure?
2. Which monitoring system files should I prioritize?
3. Can you help resolve specific conflicts?

Please advise or escalate to human if needed!"

# Task Clarification Help
python scripts/send_agent_message.py --agent pm-agent --message "❓ CLARIFICATION NEEDED: Task scope unclear

I need clarification on my current assignment.

📋 CURRENT TASK: [describe what you're working on]

🤔 UNCLEAR ASPECTS:
1. [specific question 1]
2. [specific question 2]
3. [specific question 3]

Please clarify or coordinate with other agents as needed."

# Coordination Help
python scripts/send_agent_message.py --agent pm-agent --message "🔄 COORDINATION REQUEST: Need sync with other agents

I need to coordinate with other agents for my work.

🎯 MY WORK: [describe current work]

🤝 COORDINATION NEEDED:
- Agent: [agent-name]
- Reason: [why coordination needed]
- Impact: [what happens without coordination]

Please facilitate this coordination."
```

## 🚨 **PM-Agent: When to Escalate to Human**

### **Human Escalation Criteria**
PM-Agent should escalate when:
- 🔴 **Critical conflicts** affecting multiple agents
- 🔴 **Technical decisions** beyond agent expertise
- 🔴 **Resource constraints** or system limitations
- 🔴 **Strategic decisions** about project direction
- 🔴 **Security concerns** or compliance issues
- 🔴 **Multiple agents** stuck on same issue

### **How PM-Agent Requests Human Assistance**
```bash
# Create escalation file that human monitors
echo "🚨 HUMAN ASSISTANCE REQUIRED

ESCALATION LEVEL: [URGENT/HIGH/MEDIUM]
REQUESTING AGENT: pm-agent
TIMESTAMP: $(date)

ISSUE SUMMARY:
[Brief description of the problem]

AFFECTED AGENTS:
- Agent 1: [issue description]
- Agent 2: [issue description]

ATTEMPTED SOLUTIONS:
1. [what was tried]
2. [what was tried]
3. [what was tried]

SPECIFIC HUMAN INPUT NEEDED:
- [ ] Technical decision
- [ ] Resource allocation
- [ ] Strategic direction
- [ ] Conflict resolution
- [ ] Other: [specify]

IMPACT IF NOT RESOLVED:
[consequences of not getting help]

RECOMMENDED ACTION:
[suggested human intervention]
" > HUMAN_ESCALATION_$(date +%Y%m%d_%H%M%S).md

# Also send to orchestrator
python scripts/send_agent_message.py --agent orchestrator --message "🚨 HUMAN ESCALATION NEEDED

Created escalation file: HUMAN_ESCALATION_[timestamp].md

Summary: [brief issue]
Urgency: [level]
Agents affected: [list]

Please review escalation file for details."
```

## 📝 **Communication Templates**

### **Status Update Template**
```bash
python scripts/send_agent_message.py --agent pm-agent --message "📊 STATUS UPDATE

AGENT: [your-agent-name]
TASK: [current task]
PROGRESS: [X]% complete

✅ COMPLETED:
- [accomplishment 1]
- [accomplishment 2]

🔄 IN PROGRESS:
- [current work]

⏳ NEXT STEPS:
- [next action 1]
- [next action 2]

🚨 BLOCKERS:
- [blocker 1 if any]
- [blocker 2 if any]

ETA: [estimated completion time]"
```

### **Request Review Template**
```bash
python scripts/send_agent_message.py --agent [reviewer-agent] --message "👀 REVIEW REQUEST

REQUESTING AGENT: [your-name]
WORK ITEM: [what needs review]

📋 REVIEW SCOPE:
- Files changed: [list key files]
- Type of changes: [feature/fix/docs/etc]
- Lines of code: [approximate]

🎯 SPECIFIC FEEDBACK NEEDED:
1. [specific question 1]
2. [specific question 2]
3. [specific question 3]

📁 LOCATION:
- Branch: [branch-name]
- PR: #[number] (if applicable)
- Path: [file paths]

⏰ URGENCY: [high/medium/low]
🕒 NEEDED BY: [timeframe]"
```

### **Conflict Resolution Request**
```bash
python scripts/send_agent_message.py --agent pm-agent --message "⚔️ CONFLICT RESOLUTION NEEDED

AGENTS INVOLVED:
- Agent 1: [name] - [their position]
- Agent 2: [name] - [their position]

🚨 CONFLICT DESCRIPTION:
[Detailed description of the disagreement/conflict]

📊 TECHNICAL DETAILS:
- Files affected: [list]
- Changes in conflict: [describe]
- Impact: [what happens if not resolved]

💡 PROPOSED SOLUTIONS:
1. [solution option 1]
2. [solution option 2]
3. [solution option 3]

🎯 DECISION NEEDED:
[What specific decision needs to be made]

⏰ URGENCY: [level and why]"
```

## 🔍 **Missing Pieces Documentation**

### **Current System Gaps**

#### **1. Agent Discovery & Status**
```bash
# MISSING: Real-time agent status checker
# NEEDED: Command to see which agents are active
python scripts/check_agent_status.py --all
```

#### **2. Message History & Threading**
```bash
# MISSING: Conversation history between agents
# NEEDED: Message threading system
python scripts/view_agent_conversations.py --agents pm-agent,documentation-agent
```

#### **3. Escalation Monitoring**
```bash
# MISSING: Human notification system
# NEEDED: Active monitoring of escalation files
python scripts/monitor_escalations.py --notify-human
```

#### **4. Agent Capability Registry**
```bash
# MISSING: Agent skill/capability database
# NEEDED: Registry of what each agent can help with
python scripts/agent_capabilities.py --list --agent documentation-agent
```

#### **5. Conflict Detection System**
```bash
# MISSING: Automatic conflict detection
# NEEDED: System to detect when agents have conflicting goals
python scripts/detect_agent_conflicts.py --auto-resolve
```

### **Required Infrastructure Components**

#### **A. Message Queue System**
- Persistent message storage
- Message acknowledgment system
- Priority queuing for urgent messages
- Message routing and filtering

#### **B. Agent State Management**
- Real-time agent status tracking
- Task assignment and progress monitoring
- Resource allocation and conflicts
- Health monitoring and failure detection

#### **C. Human Integration Layer**
- Escalation file monitoring
- Notification system (Slack, email, etc.)
- Human response tracking
- Approval workflows

#### **D. Communication Analytics**
- Message frequency and patterns
- Response time metrics
- Collaboration effectiveness
- Bottleneck identification

## 🚀 **Implementation Priority**

### **Immediate (COMPLETED ✅)**
1. ✅ Agent communication scripts (COMPLETED)
2. ✅ Escalation file system (COMPLETED)
3. ✅ Basic status checking (COMPLETED)
4. ✅ Message history logging (COMPLETED)
5. ✅ Agent capability registry (COMPLETED)

### **Available Tools**
1. ✅ `python scripts/agent_capabilities.py --list` - View all agents and capabilities
2. ✅ `python scripts/view_agent_conversations.py --recent` - View recent agent conversations
3. ✅ `python scripts/check_agent_status.py` - Check real-time agent status
4. ✅ `python scripts/monitor_escalations.py --check` - Check for human escalations

### **Short-term (Next Implementation)**
1. ⏳ Conflict detection system
2. ⏳ Human notification integration (Slack/email)
3. ⏳ Message queue implementation

### **Medium-term (Next Week)**
1. Advanced analytics dashboard
2. Automated conflict resolution
3. Resource optimization
4. Performance monitoring

## 📞 **Emergency Procedures**

### **If All Agents Are Stuck**
1. All agents message pm-agent simultaneously
2. PM-agent creates emergency escalation file
3. Human intervention requested immediately
4. Fallback to manual coordination

### **If PM-Agent Is Unresponsive**
1. Agents message orchestrator directly
2. Orchestrator coordinates temporary leadership
3. Emergency escalation to human
4. Backup PM protocols activated

### **If Human Assistance Is Needed**
1. PM-agent creates detailed escalation file
2. Multiple notification channels activated
3. Work pauses on affected components
4. Agents continue on independent tasks

---

**Remember: Communication is key to multi-agent success! When in doubt, ask for help early and often.**