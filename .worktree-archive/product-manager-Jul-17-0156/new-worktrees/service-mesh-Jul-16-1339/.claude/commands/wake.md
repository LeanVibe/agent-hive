# /wake - Memory Restoration Command

Restores essential knowledge and project state from persistent memory after context reset or session restart.

## Usage
```
/wake
```

**No parameters required** - automatically restores from latest memory consolidation.

## What It Does

### 1. **Essential Knowledge Restoration**
- **Immediately loads** `.claude/memory/ESSENTIAL_WORKFLOW_KNOWLEDGE.md`
- **Restores critical tools**: Communication scripts, quality gates, working systems
- **Updates context** with latest project discoveries and protocols
- **Provides summary** of preserved knowledge (first 500 chars)

### 2. **Project State Recovery**
- **Loads memory snapshot** from latest consolidation
- **Restores agent status**: Current coordination state and active agents
- **Recovers project status**: Git state, open PRs, recent commits
- **Identifies active work**: Worktrees, ongoing tasks, priorities

### 3. **Current State Verification**
- **Captures fresh state**: Validates what changed during memory gap
- **Compares timestamps**: Shows time since last consolidation
- **Verifies integrity**: Ensures memory files are intact and valid
- **Provides recommendations**: Next steps for resuming work

### 4. **Coordination Resume**
- **Agent communication ready**: Scripts and protocols immediately available
- **Quality gates active**: Evidence-based validation requirements restored
- **Git workflow known**: Commit and push requirements preserved
- **Tools accessible**: All working scripts and commands available

## When to Use

### **After Context Reset**
- **First command** to run after Claude Code session restart
- **Before any new work** to understand current project state
- **When unsure** about current progress or available tools

### **Session Restoration**
- Start new work sessions with full knowledge context
- Resume coordination with other agents seamlessly  
- Access all previously discovered working solutions
- Understand current sprint status and priorities

### **Knowledge Recovery**
- When you can't remember the working communication scripts
- To access quality gate requirements and protocols
- For current project status and recent work summary
- To restore agent coordination state and active tasks

## Output Example
```
🌅 Wake Protocol Results:
  essential_knowledge_restored: True
  memory_snapshot_restored: True  
  current_state_verified: True
  last_consolidation: 2025-07-16T08:58:32.389200
  consolidation_level: critical
  current_timestamp: 2025-07-16T09:15:42.123456
  recommendations: [
    'Review essential workflow knowledge',
    'Check agent status and coordination', 
    'Verify current work and priorities',
    'Use proper communication scripts for agent coordination'
  ]
  wake_instructions: [
    'Read .claude/memory/ESSENTIAL_WORKFLOW_KNOWLEDGE.md immediately',
    'Check agent status with scripts/check_agent_status.py',
    'Verify current work with git status and PR status', 
    'Resume coordination using proper communication scripts'
  ]

✅ Essential workflow knowledge restored
✅ Memory snapshot restored  
🎯 Wake protocol completed successfully

💡 Critical tools available:
   - scripts/fixed_agent_communication.py (agent messaging)
   - Quality gates: commit + push mandatory
   - Evidence-based validation required
```

## Knowledge Immediately Available

After `/wake`, you have instant access to:

### **🔧 Working Tools**
- `scripts/fixed_agent_communication.py` - Reliable agent messaging (no manual Enter)
- `scripts/check_agent_status.py --format json` - Agent coordination status
- Quality gate commands and evidence-based validation protocols

### **📋 Current Status** 
- Recent commits and project progress
- Open PRs and active work streams
- Agent worktrees and coordination state
- Sprint priorities and next steps

### **🚨 Critical Protocols**
- Git workflow requirements (commit + push mandatory)
- Evidence-based validation (never trust without verification)  
- Agent communication standards and window naming
- Quality gates and integration requirements

## Automatic Workflow Integration

The wake command integrates with:
- **Automatic consolidation** at 70% context usage
- **Essential knowledge auto-updates** during consolidation
- **Memory backup system** with checksums and atomic writes
- **Project status tracking** across all work sessions

## Recovery Verification

Wake protocol includes verification steps:
- ✅ **Essential knowledge file exists and is readable**
- ✅ **Memory snapshot loaded successfully**  
- ✅ **Current state captured and compared**
- ✅ **File integrity verified with checksums**
- ✅ **Recommendations generated based on state**

## Files Accessed
- `.claude/memory/ESSENTIAL_WORKFLOW_KNOWLEDGE.md` - Critical knowledge (always read first)
- `.claude/memory/LATEST_MEMORY_SNAPSHOT.json` - Complete state restoration
- `.claude/memory/DEEP_CONSOLIDATION_*.md` - Historical backups if needed
- Current project files for state verification

## Integration with Sleep
- **Sleep** preserves knowledge → **Wake** restores knowledge
- **Consolidation levels** (normal/critical/emergency) → **Full restoration**
- **Automatic thresholds** → **Manual control when needed**
- **Seamless continuation** across any context boundary

---
**🎯 Purpose**: Instantly restore all critical workflow knowledge, ensuring you never lose time rediscovering tools, protocols, or project state.