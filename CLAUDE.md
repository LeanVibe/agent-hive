# LeanVibe Agent Hive - Main Coordination Hub

## 🏗️ ARCHITECTURE OVERVIEW
This project uses **Convention over Configuration** for CLAUDE.md files:
- **Main CLAUDE.md**: Core project knowledge (THIS FILE)
- **Worktree Extensions**: `worktrees/{name}/CLAUDE_EXTENSIONS.md`
- **Worktree Overrides**: `worktrees/{name}/CLAUDE_OVERRIDES.md` (USE SPARINGLY)

## 🚨 OVERRIDE POLICY
`CLAUDE_OVERRIDES.md` should only be used when:
1. Worktree requires different quality gates
2. Agent needs different communication protocols  
3. Justified with comment explaining why override is necessary

**Rule**: Extensions extend, overrides replace. Use overrides sparingly.

## 📋 CURRENT PROJECT STATUS

### **Project Overview**
Multi-agent orchestration system for autonomous software development with human agency integration.

### **Current State**
- **Branch**: `integration/phase3-advanced-features`
- **Communication**: ✅ **FIXED** (`scripts/fixed_agent_communication.py`)
- **Crisis Response**: ✅ **ACTIVE** (evidence-based workflow)
- **Quality Gates**: ✅ **OPERATIONAL** (evidence-based validation)
- **Agent Coordination**: ✅ **FUNCTIONAL** (window mapping updated)

### **Recent Achievements**
- **Communication System Repaired**: Fixed window mapping for agent message delivery
- **Evidence-Based Workflow**: Implemented Definition of Done with deliverable validation
- **Crisis Response**: Developed systematic crisis management with agent accountability
- **Quality Gates**: Established mandatory validation before task completion

## 🧠 CRITICAL MEMORY MANAGEMENT

### **Essential Knowledge Files (READ FIRST)**
```bash
# ALWAYS read these after any context reset or memory loss
cat .claude/memory/ESSENTIAL_WORKFLOW_KNOWLEDGE.md
cat COMMUNICATION_SYSTEM_FIX.md
cat NEW_WORKFLOW_DESIGN.md
cat AGENT_FEEDBACK_ANALYSIS.md
```

### **Context Management Commands**
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
- `COMMUNICATION_SYSTEM_FIX.md` - Fixed agent communication protocols
- `NEW_WORKFLOW_DESIGN.md` - Evidence-based workflow design
- `AGENT_FEEDBACK_ANALYSIS.md` - Crisis response lessons learned

## 🔧 ESSENTIAL TOOLS (ALWAYS USE THESE)

### **Agent Communication (FIXED)**
```bash
# PRIMARY: Fixed communication system (window mapping updated)
python scripts/fixed_agent_communication.py --agent security --message "TASK"
python scripts/fixed_agent_communication.py --agent performance --message "TASK"
python scripts/fixed_agent_communication.py --agent frontend --message "TASK"
python scripts/fixed_agent_communication.py --agent pm-agent-new --message "TASK"

# FALLBACK: Standard communication (expects agent- prefix)
python scripts/send_agent_message.py --agent security --message "TASK"
```

### **Agent Management**
```bash
# Check agent status
python scripts/check_agent_status.py --format json

# Monitor agent progress
python scripts/monitor_agents.py --real-time

# Spawn new agents (if needed)
python scripts/enhanced_agent_spawner.py --agent-type [type] --priority 1.0 --task "TASK"
```

### **Quality Gates (MANDATORY)**
```bash
# Before ANY completion claims - EVIDENCE-BASED VALIDATION
pytest tests/ -x --tb=short
python -m py_compile **/*.py
git status && git log --oneline -3
git push origin branch-name  # MANDATORY
```

## 🤖 AGENT COORDINATION PROTOCOL

### **Communication Standards**
- **Window Mapping**: `SEC-Input-⏳`, `PERF-Input-⏳`, `FE-Input-⏳`, `PM-Input-⏳`
- **Message Delivery**: Automatic submission via buffer method
- **Verification**: Always verify agent receives and acknowledges messages

### **Evidence-Based Workflow**
- **Definition of Done**: Deliverables must exist and be validated
- **Validation Mechanisms**: File existence, content, quality gates, commits
- **Accountability**: No completion without git evidence
- **Success Criteria**: Task complete only after commit hash generated

### **Human Agency Integration**
- **Architecture Decisions**: Always escalate to human
- **Security Changes**: Human review required
- **Performance Issues**: Immediate escalation
- **Business Logic**: Human guidance needed
- **Confidence Threshold**: Escalate when confidence < 80%

## 🚨 CRISIS RESPONSE PROTOCOLS

### **Communication System Status**
- **Status**: ✅ **OPERATIONAL**
- **Fixed Script**: `scripts/fixed_agent_communication.py`
- **Window Mapping**: Updated for current agent windows
- **Test Command**: `python scripts/fixed_agent_communication.py --agent security --message "TEST"`

### **Crisis Management Approach**
- **Prevention First**: Proactive monitoring and quality gates
- **Evidence-Based**: All claims must be verified with deliverables
- **Systematic Response**: Structured crisis response with clear escalation
- **Agent Accountability**: Deliverables required for completion claims

### **Escalation Triggers**
- Agent coordination failures
- Communication system issues
- Quality gate failures (tests, builds, security)
- Security vulnerabilities
- Performance degradation >10%

## 🚨 CRITICAL REMINDERS

### **NEVER FORGET**
- ❌ Don't use `tmux send-keys` directly
- ❌ Don't trust agent self-reports without verification
- ❌ Don't skip quality gates
- ❌ Don't forget to push commits to remote
- ❌ Don't mark tasks complete without deliverables

### **ALWAYS REMEMBER**
- ✅ Use `scripts/fixed_agent_communication.py` for messaging
- ✅ Verify git commits and pushes before claiming completion
- ✅ Evidence-based validation required for all tasks
- ✅ Read essential knowledge after context reset
- ✅ Validate deliverables exist before marking complete

## 🔄 WAKE PROTOCOL (AFTER CONTEXT RESET)

### **Immediate Actions**
1. **Read Essential Knowledge**: `cat .claude/memory/ESSENTIAL_WORKFLOW_KNOWLEDGE.md`
2. **Check Communication**: `python scripts/fixed_agent_communication.py --agent security --message "STATUS CHECK"`
3. **Restore Memory**: `python scripts/context_memory_manager.py --wake`
4. **Verify Current Work**: `git status && gh pr list --state open`
5. **Check Crisis State**: Review `COMMUNICATION_SYSTEM_FIX.md` and `NEW_WORKFLOW_DESIGN.md`

### **Memory Restoration Commands**
```bash
# Full wake protocol
python scripts/context_memory_manager.py --wake

# Check what was preserved
ls -la .claude/memory/

# Verify working systems
python scripts/fixed_agent_communication.py --agent performance --message "Status check"
```

## 🔄 WORKTREE INTEGRATION

### **Current Worktree Detection**
```bash
# Detect current worktree
CURRENT_WORKTREE=$(git rev-parse --show-toplevel | xargs basename)
echo "Current worktree: $CURRENT_WORKTREE"
```

### **Worktree-Specific Instructions**
**IMPORTANT**: After reading this main CLAUDE.md file, also read:

1. **Worktree Extensions** (if exists):
   - `worktrees/frontend-Jul-17-0824/CLAUDE_EXTENSIONS.md` - Frontend specialist context
   - `worktrees/performance-Jul-17-0823/CLAUDE_EXTENSIONS.md` - Performance optimization context
   - `worktrees/pm-agent-new/CLAUDE_EXTENSIONS.md` - PM coordination context
   - `worktrees/security-Jul-17-0944/CLAUDE_EXTENSIONS.md` - Security specialist context

2. **Worktree Overrides** (if exists and justified):
   - `worktrees/{current_worktree}/CLAUDE_OVERRIDES.md`

### **Available Worktrees**
- **frontend-Jul-17-0824**: Frontend specialist - dashboard integration and UI components
- **performance-Jul-17-0823**: Performance specialist - optimization and technical debt reduction
- **pm-agent-new**: PM coordination - sprint planning and agent coordination
- **security-Jul-17-0944**: Security specialist - auditing and vulnerability management

## 📚 DOCUMENTATION REFERENCES

### **Key Documentation Files**
- `COMMUNICATION_SYSTEM_FIX.md` - Fixed agent communication protocols
- `NEW_WORKFLOW_DESIGN.md` - Evidence-based workflow with Definition of Done
- `AGENT_FEEDBACK_ANALYSIS.md` - Crisis response lessons and workflow improvements
- `CLAUDE_MD_RECREATION_PLAN_REFINED.md` - This file's creation plan and architecture

### **Working Scripts**
- `scripts/fixed_agent_communication.py` - Reliable agent messaging (FIXED)
- `scripts/context_memory_manager.py` - Memory management system
- `scripts/enhanced_agent_spawner.py` - Proper agent creation
- `scripts/check_agent_status.py` - Agent status monitoring

### **Quality & Validation**
- `scripts/run_quality_gates.py` - Comprehensive quality validation
- `scripts/validate_claude_structure.py` - CLAUDE.md structure validation
- `pytest.ini` - Test configuration
- `mypy.ini` - Type checking configuration

---

**🎯 MEMORY COMMITMENT**: This knowledge MUST persist across all context boundaries. If context is lost, immediately run the wake protocol and restore essential knowledge.

**📝 CONVENTION**: This main CLAUDE.md provides core project context. Worktree-specific files extend this context for specialized roles without conflicts.

**🔄 USAGE**: Read this file first, then read worktree-specific extensions for your current role and context.