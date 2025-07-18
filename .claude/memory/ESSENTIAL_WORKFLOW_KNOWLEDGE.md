# 🧠 ESSENTIAL WORKFLOW KNOWLEDGE - ALWAYS READ FIRST AFTER WAKE

## 🚨 CRITICAL REMINDERS - NEVER FORGET
- **YOU ARE THE MAIN AGENT** - Coordination and delegation only, not direct implementation
- **STRATEGIC SHIFT ACTIVE**: Prevention-first approach implemented (Days 1-2)
- **Current Status**: Phase 1 prevention system implementation in progress
- **🎯 TOP PRIORITY**: Coordinate prevention systems before resuming feature work
- **PM Agent**: Leading prevention rollout, all agents briefed on strategic shift

## 🔧 WORKING TOOLS (CANONICAL SCRIPTS)
```bash
# Agent Communication (RELIABLE)
python scripts/fixed_agent_communication.py --agent AGENT_NAME --message "MESSAGE"

# Agent Lifecycle Management
python scripts/agent_manager.py --spawn AGENT_NAME
python scripts/agent_manager.py --status

# Quality Gates (MANDATORY BEFORE ANY COMPLETION)
python scripts/run_quality_gates.py
python scripts/quality_gate_validation.py

# PR/CI Automation
python scripts/pr_manager.py
python scripts/pr_merge_coordinator.py PR_NUMBER
python scripts/pr_resolution_monitor.py

# Emergency/Crisis
python scripts/emergency_cli.py --task "Task Name"

# Agent Status Check
python scripts/check_agent_status.py --format json

# Gemini CLI Strategic Analysis
gemini -p "STRATEGIC_QUESTION"
```

## 📊 CURRENT PROJECT STATUS (Jul 18, 2025)

### 🎯 STRATEGIC SHIFT: Prevention-First Approach Active
**Days 1-2: PREVENTION PHASE** (Critical Foundation)
- **Pre-commit hooks**: PR size validation before creation
- **Agent requirements docs**: Single source of truth for workflow rules
- **Automated PM monitoring**: Health checks and auto-respawn
- **GitHub Actions**: Basic PR validation

### 🚨 CRISIS RESOLVED: Week 2 Workflow Discipline
- **Root Cause**: Agents created 16K+ line PRs violating <500 line limits
- **Response**: New PM Agent deployed, enforced compliance within 30 minutes
- **Outcome**: All oversized PRs closed, Issue #92 created for Security Agent
- **Learning**: Prevention systems needed to avoid future crises

### 🧠 GEMINI CLI STRATEGIC GUIDANCE (IMPLEMENTED)
1. **Prevention over reaction**: "Cost of another crisis higher than 1-2 day pause"
2. **Phase 1 implementation**: Pre-commit hooks, agent requirements, monitoring
3. **Automation balance**: Hard rules (enforcement) + soft rules (learning)
4. **Resource allocation**: 60% prevention, 30% coordination, 10% monitoring

## 🤖 ACTIVE AGENT COORDINATION

### All Agents Briefed on Strategic Shift
- **PM Agent**: Leading prevention rollout coordination
- **Frontend Agent**: Creating agent requirements documentation
- **Performance Agent**: Implementing infrastructure (pre-commit hooks, GitHub Actions)
- **Security Agent**: System testing and validation

### Agent Status (Last Known)
- **PM Agent**: ✅ Active - Coordinating prevention implementation
- **Frontend Agent**: ✅ Active - Commands audit completed, now on requirements docs
- **Performance Agent**: ✅ Active - Working on infrastructure implementation
- **Security Agent**: ⚠️ Compliance required - Issue #92 active

## 📋 GITHUB ISSUE TRACKING (YOUR PRIMARY ROLE)

### Active Issues
- **Issue #92**: Security Agent workflow discipline enforcement (URGENT)
- **Issue #80**: Strategic integration plan (Updated with prevention-first approach)

### Your Responsibilities as Main Agent
1. **🎯 TOP PRIORITY: Coordinate prevention system implementation**
2. **Monitor Phase 1 progress** (Days 1-2 critical foundation)
3. **Validate prevention systems** before resuming feature work
4. **Update GitHub issues** with prevention implementation progress
5. **Maintain strategic oversight** - delegate but don't implement directly
6. **Escalate to human** only for strategic decisions or major issues

## 🎯 PREVENTION-FIRST SUCCESS METRICS

### Phase 1 Success (Days 1-2)
- [ ] Pre-commit hooks operational and tested
- [ ] All agents acknowledge workflow requirements
- [ ] PM Agent automated monitoring active
- [ ] GitHub Actions validation working

### Prevention Effectiveness
- [ ] Zero PR size violations for 48+ hours
- [ ] 90% reduction in manual intervention
- [ ] Agent coordination time <30 minutes per issue

## 🔄 WAKE PROTOCOL CHECKLIST

After reading this file, immediately:
1. **🎯 Check prevention implementation progress**: Are Phase 1 systems operational?
2. **Check agent status**: `python scripts/agent_manager.py --status`
3. **Verify current work**: `git status && git log --oneline -3`
4. **Review active issues**: `gh issue list --state open --limit 5`
5. **Coordinate prevention validation**: Ensure systems working before feature resumption
6. **Update todos**: Based on prevention implementation progress

## 🚨 CRITICAL SUCCESS FACTORS
- **Prevention over reaction**: Proactive systems prevent crises
- **Phase 1 completion**: All prevention systems must be operational
- **Agent coordination**: PM Agent leads, you coordinate strategically
- **Quality gates**: Never skip validation before completion claims
- **Strategic oversight**: Delegate implementation, maintain coordination

## 💡 STRATEGIC PRINCIPLES
- **Prevention-first approach**: Better to prevent than react to crises
- **Automated guardrails**: Hard rules prevent violations, soft rules enable learning
- **Strategic delegation**: PM Agent executes, you coordinate and validate
- **Continuous monitoring**: Real-time validation of systems and agents

## 📊 CURRENT WORK STATUS
- **Phase 1 Prevention**: In progress (Days 1-2)
- **Feature work**: Paused until prevention systems operational
- **Agent coordination**: All agents briefed and executing prevention tasks
- **Quality gates**: Being enhanced with automated validation

---
**🎯 MEMORY COMMITMENT**: This knowledge MUST persist across all context boundaries. Always read this file first after /wake command.

**STATUS**: Strategic shift to prevention-first approach successfully implemented, Phase 1 prevention system implementation in progress.