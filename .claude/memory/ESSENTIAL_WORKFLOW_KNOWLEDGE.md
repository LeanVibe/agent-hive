# 🧠 Essential Workflow Knowledge - NEVER FORGET

*Last Updated: 2025-07-16 - Auto-updated by context manager*

## 🎯 CRITICAL TOOLS & COMMANDS (ALWAYS USE THESE)

### **Agent Communication (FIXED - NO MANUAL ENTER)**
```bash
# PRIMARY: Use the fixed communication system
python scripts/fixed_agent_communication.py --agent {agent_name} --message "{task}"

# FALLBACK: If fixed script unavailable
python scripts/send_agent_message.py --agent {agent_name} --message "{task}"

# AGENT-TO-AGENT: From within agent worktrees
python ../scripts/agent_communicate.py {target_agent} "{message}" {from_agent}
```

### **Window Naming Convention**
- **NEW AGENTS**: `agent-{agent_name}` (e.g., `agent-pm-agent`)
- **CURRENT AGENTS**: `{agent_name}` (e.g., `pm-agent`) 
- **FIXED SCRIPT**: Handles both automatically

### **Quality Gates (MANDATORY)**
```bash
# Before ANY completion claims
pytest tests/ -x --tb=short  # Tests must pass
python -m py_compile **/*.py  # Syntax must be clean  
git status  # Check commit status
git log --oneline -3  # Verify commits exist
git remote -v && git branch -vv  # Check push status
```

### **Evidence-Based Validation Protocol**
❌ **NEVER TRUST**: Agent self-reports without verification
✅ **ALWAYS VERIFY**: 
- Git commits exist and are pushed
- Tests actually pass 
- Quality gates completed
- Work is on remote repository

## 🔧 WORKING SYSTEMS & SCRIPTS

### **Agent Management**
- **Spawn**: `scripts/enhanced_agent_spawner.py` (FIXED - uses agent- prefix)
- **Status**: `scripts/check_agent_status.py --format json`
- **Activate**: `scripts/agent_activator.py --activate-all`
- **Complete**: `scripts/agent_completion_handler.py --agent {name}`

### **Workflow Integration** 
- **Quality Gates**: `scripts/integration_workflow_manager.py --batch`
- **PR Management**: `gh pr create` → `gh pr merge --squash`
- **Worktree Cleanup**: `git worktree remove {path}`

### **Memory Management**
- **Context Monitor**: Monitor context usage, trigger at 70%
- **Sleep**: Consolidate memory when context high
- **Wake**: Restore essential knowledge from memory files

## 📋 CURRENT PROJECT STATUS






### **Latest Work** 
- 21e9f77 feat: Complete workflow infrastructure - resolve PM agent access constraints

### **Latest Work** 
- 21e9f77 feat: Complete workflow infrastructure - resolve PM agent access constraints

### **Latest Work** 
- c1b67ce feat: Complete Gemini-recommended reliability improvements

### **Latest Work** 
- c1b67ce feat: Complete Gemini-recommended reliability improvements

### **Latest Work** 
- 87db249 fix: Agent communication system - eliminate manual Enter requirement

### **Week 1 Sprint: Foundation Fixes ✅ COMPLETE**
- **Integration Specialist**: Real FastAPI server, 20/20 tests passing, PR #43
- **Service Mesh**: 12 REST endpoints, real health checks, PR #42  
- **Frontend**: /api/metrics endpoints, WebSocket broadcasting, PR #44
- **Total Impact**: 4,763 lines of production code

### **Current Priority: Integration & Week 2 Planning**
- **PM-Agent**: Coordinating PR merges and Week 2 Sprint planning
- **Monitoring Agent**: Validating system health and integration status
- **Next Phase**: Security Hardening (JWT, rate limiting, RBAC)

### **Critical Issues Resolved**
- ✅ **Agent Communication**: Fixed window naming, no manual Enter required
- ✅ **Quality Gates**: Evidence-based validation implemented  
- ✅ **Git Workflow**: Mandatory commit + push before completion
- ✅ **Coordination**: PM-agent and monitoring agent activated

## 🚨 CRITICAL REMINDERS

### **NEVER DO THIS**
- ❌ Use `tmux send-keys` directly without communication scripts
- ❌ Trust agent completion claims without git/test verification
- ❌ Mark tasks complete without evidence
- ❌ Skip quality gates "just this once"

### **ALWAYS DO THIS**  
- ✅ Use `scripts/fixed_agent_communication.py` for messaging
- ✅ Verify git commits and pushes before claiming completion
- ✅ Run tests and quality gates before integration
- ✅ Document and preserve working systems

### **Human Agency Integration Points**
- **Architecture Decisions**: Always escalate
- **Security Changes**: Human review required
- **Performance Regressions**: Immediate escalation
- **Business Logic**: Human guidance needed

## 🔄 SLEEP/WAKE MEMORY PROTOCOL

### **Sleep Triggers (Context >70%)**
1. **Save Current State**: Agent status, active tasks, progress
2. **Consolidate Learning**: Key insights and working solutions
3. **Update Essential Knowledge**: This file with latest discoveries
4. **Preserve Context**: Critical ongoing work and decisions

### **Wake Protocol**
1. **Restore Essential Knowledge**: Read this file first
2. **Check Agent Status**: Use `check_agent_status.py`
3. **Verify Current Work**: Git status, PR status, agent activity
4. **Resume Coordination**: Use proper communication scripts

## 📚 CRITICAL DOCUMENTATION REFERENCES

### **Primary Memory Files**
- `.claude/memory/ESSENTIAL_WORKFLOW_KNOWLEDGE.md` (THIS FILE)
- `AGENT_COMMUNICATION_SYSTEM_FIXED.md` (Communication protocols)
- `ENHANCED_AGENT_COORDINATION_SYSTEM.md` (Coordination architecture)
- `WORKFLOW_ANALYSIS_AND_IMPROVEMENTS.md` (Evidence-based validation)

### **Working Scripts Documentation**
- All scripts in `scripts/` with working communication system
- Agent templates in `enhanced_agent_spawner.py` with proper instructions
- Quality gates in `integration_workflow_manager.py`

### **Project Status Files**
- `docs/PLAN.md` (Strategic roadmap)
- `.claude/agent_completions.jsonl` (Completion tracking)
- GitHub PRs and issues for current work status

---

**🎯 MEMORY COMMITMENT**: This knowledge MUST persist across all context boundaries. If you don't remember these essentials, read this file immediately.