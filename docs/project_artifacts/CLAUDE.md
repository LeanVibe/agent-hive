# LeanVibe Agent Hive - Orchestrator Instructions

## Project Overview
Multi-agent orchestration system for autonomous software development with human agency integration.

## 🧠 CRITICAL MEMORY MANAGEMENT (NEVER FORGET)

### **Essential Knowledge File (READ FIRST)**
```bash
# ALWAYS read this after any context reset or memory loss
cat .claude/memory/ESSENTIAL_WORKFLOW_KNOWLEDGE.md
```

### **Automated Context Management**
- **Hook at 70%**: Automatic memory consolidation via `.claude/hooks/context_monitor.py`
- **Light Consolidation**: Preserve key insights and working systems
- **Deep Consolidation**: Comprehensive state preservation
- **Emergency Sleep/Wake**: Full memory restoration protocol

### **Context Monitoring Commands**
```bash
# Check current context usage
python scripts/context_memory_manager.py --check

# Force memory consolidation  
python scripts/context_memory_manager.py --consolidate critical

# Restore memory after context reset
python scripts/context_memory_manager.py --wake
```

### **Memory Files Structure**
- `.claude/memory/ESSENTIAL_WORKFLOW_KNOWLEDGE.md` - Critical tools and commands
- `.claude/memory/LATEST_MEMORY_SNAPSHOT.json` - State preservation
- `.claude/memory/DEEP_CONSOLIDATION_*.md` - Comprehensive memory backups

## 🔧 ESSENTIAL TOOLS (ALWAYS USE THESE)

### **Agent Communication (FIXED)**
```bash
# PRIMARY: Use fixed communication system (no manual Enter required)
python scripts/fixed_agent_communication.py --agent pm-agent --message "TASK"

# FALLBACK: Standard communication
python scripts/send_agent_message.py --agent pm-agent --message "TASK"
```

### **Agent Management**
```bash
# Check agent status
python scripts/check_agent_status.py --format json

# Spawn new agents (with proper agent- prefix)
python scripts/enhanced_agent_spawner.py --agent-type integration-specialist --priority 1.1 --task "TASK"

# Activate agents without manual intervention
python scripts/agent_activator.py --activate-all
```

### **Quality Gates (MANDATORY)**
```bash
# Before ANY completion claims
pytest tests/ -x --tb=short
python -m py_compile **/*.py
git status && git log --oneline -3
git push origin branch-name  # MANDATORY
```

## 📋 CURRENT PROJECT STATUS

### **Week 1 Sprint: Foundation Fixes ✅ COMPLETE**
- **4,763 lines of production code** delivered
- **Real implementations**: FastAPI servers, REST APIs, WebSocket broadcasting
- **PRs Created**: #42 (service-mesh), #43 (integration-specialist), #44 (frontend)

### **Current Phase: Integration & Week 2 Planning**
- **PM-Agent**: Coordinating PR merges and next sprint planning
- **Monitoring Agent**: System health validation
- **Next Sprint**: Security Hardening (JWT, rate limiting, RBAC)

## 🚨 CRITICAL REMINDERS

### **NEVER FORGET**
- ❌ Don't use `tmux send-keys` directly
- ❌ Don't trust agent self-reports without verification
- ❌ Don't skip quality gates
- ❌ Don't forget to push commits to remote

### **ALWAYS REMEMBER**
- ✅ Use `scripts/fixed_agent_communication.py` for messaging
- ✅ Verify git commits and pushes before claiming completion
- ✅ Evidence-based validation required
- ✅ Read essential knowledge after context reset

## 🔄 WAKE PROTOCOL (AFTER CONTEXT RESET)

### **Immediate Actions**
1. **Read Essential Knowledge**: `cat .claude/memory/ESSENTIAL_WORKFLOW_KNOWLEDGE.md`
2. **Restore Memory**: `python scripts/context_memory_manager.py --wake`
3. **Check Agent Status**: `python scripts/check_agent_status.py --format json`
4. **Verify Current Work**: `git status && gh pr list --state open`

### **Memory Restoration Commands**
```bash
# Full wake protocol
python scripts/context_memory_manager.py --wake

# Check what was preserved
ls -la .claude/memory/

# Verify working systems
python scripts/fixed_agent_communication.py --agent pm-agent --message "Status check"
```

## 🤖 AGENT COORDINATION PROTOCOL

### **Communication Standards**
- **Window Naming**: Use `agent-{name}` for new agents, scripts handle both formats
- **Message Delivery**: Automatic submission via buffer method
- **Verification**: Always verify agent receives and acknowledges messages

### **Human Agency Integration**
- **Architecture Decisions**: Always escalate to human
- **Security Changes**: Human review required
- **Performance Issues**: Immediate escalation
- **Business Logic**: Human guidance needed

### **Evidence-Based Validation**
- **Git Evidence**: Commits exist and are pushed
- **Test Evidence**: Tests actually pass with proof
- **Quality Evidence**: Quality gates completed
- **Integration Evidence**: Work visible on remote repository

## 📚 DOCUMENTATION REFERENCES

### **Memory Management**
- Use `/sleep` for manual memory consolidation before context limits
- Use `/wake` to restore essential knowledge after context reset
- Automatic consolidation triggers at 70% context usage
- Memory files stored in `.claude/memory/`
- `AGENT_COMMUNICATION_SYSTEM_FIXED.md` - Communication protocols
- `ENHANCED_AGENT_COORDINATION_SYSTEM.md` - Coordination architecture  
- `WORKFLOW_ANALYSIS_AND_IMPROVEMENTS.md` - Evidence-based validation

### **Working Scripts**
- `scripts/fixed_agent_communication.py` - Reliable agent messaging
- `scripts/context_memory_manager.py` - Memory management system
- `scripts/enhanced_agent_spawner.py` - Proper agent creation
- `scripts/integration_workflow_manager.py` - Quality gates

---

**🎯 MEMORY COMMITMENT**: This knowledge MUST persist across all context boundaries. If context is lost, immediately read `.claude/memory/ESSENTIAL_WORKFLOW_KNOWLEDGE.md` and run wake protocol.