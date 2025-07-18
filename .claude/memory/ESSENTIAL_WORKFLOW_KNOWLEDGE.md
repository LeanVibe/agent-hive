# 🧠 ESSENTIAL WORKFLOW KNOWLEDGE - READ FIRST AFTER WAKE

## 🎯 IMMEDIATE PRIORITIES - CHECK BACKLOG.md FIRST
- **SINGLE SOURCE OF TRUTH**: `BACKLOG.md` contains ALL current priorities
- **MAIN AGENT ROLE**: Coordination and delegation only, not direct implementation  
- **DOCUMENTATION COMPLETE**: ✅ Single source of truth operational with automation

## 🔧 WORKING TOOLS (VERIFIED SCRIPTS)

### Core Commands
```bash
# Priority and Planning (ALWAYS CHECK FIRST)
cat BACKLOG.md                                    # Master priority list
python scripts/backlog_sync.py --action=report   # GitHub sync status

# Agent Communication and Lifecycle  
python scripts/agent_manager.py --status          # Agent status
python scripts/fixed_agent_communication.py --agent "NAME" --message "MSG"
tmux list-windows -t agent-hive                   # Check active agents

# Quality Gates (MANDATORY)
python scripts/run_quality_gates.py
python scripts/quality_gate_validation.py

# Automation Tools
/autoflow --title "TITLE" --description "DESC" --branch "BRANCH"  # Complete workflow
python scripts/backlog_sync.py --action=sync      # Manual GitHub sync

# Memory Management
/sleep critical    # Context preservation  
/wake             # Restore after reset
```

## 📊 CURRENT STATUS - ALWAYS VERIFY WITH BACKLOG.md

### ✅ DOCUMENTATION CONSOLIDATION COMPLETE (July 18, 2025)
- **Single Source of Truth**: BACKLOG.md operational with GitHub sync
- **Automation**: Git hooks, backlog sync, priority management active
- **Agent Integration**: Sleep/wake/spawn cycles preserve documentation rules
- **Quality Gates**: Pre-commit validation, post-commit sync operational

### 🎯 CURRENT PRIORITIES (Check BACKLOG.md for Latest)
- **P0 Items**: Check `## 🔥 P0 - Critical (This Week)` in BACKLOG.md
- **Active Sprint**: Foundation Epic Phase 2 Preparation
- **Next Review**: July 25, 2025 (per BACKLOG.md header)

## 🔄 WAKE PROTOCOL CHECKLIST

After reading this file:
1. **Check BACKLOG.md**: Read current P0/P1 priorities (5 seconds)
2. **Verify git status**: `git status && git log --oneline -3`
3. **Check agent status**: `python scripts/agent_manager.py --status`
4. **Review current work**: Match with BACKLOG.md priorities
5. **Test automation**: `python scripts/backlog_sync.py --action=report`

## 📋 DOCUMENTATION RULES (EMBEDDED IN ALL AGENTS)

### Single Source of Truth (MANDATORY)
- **BACKLOG.md**: Master priority list - check FIRST for all work
- **GitHub Issues**: Auto-synced execution tracking  
- **docs/archived/**: Historical reference (read-only)

### Automation Active
- **Git hooks**: Pre-commit validation, post-commit GitHub sync
- **scripts/backlog_sync.py**: Manual sync and reporting
- **Priority system**: P0 (48hr), P1 (1wk), P2 (1mo), P3 (future)

## 🚨 CRITICAL SUCCESS FACTORS
- **Evidence over claims**: Verify completion vs reported
- **BACKLOG.md first**: Always check priorities here before planning
- **Quality gates**: Never skip validation before completion
- **Documentation rules**: Embedded in sleep/wake/spawn cycles

---
**🎯 MEMORY COMMITMENT**: This knowledge persists across context boundaries. 
**📋 CURRENT STATUS**: Documentation consolidation complete, automation operational, BACKLOG.md is single source of truth.