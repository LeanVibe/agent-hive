# /sleep - Memory Consolidation Command

**Canonical system:** Automatic/manual memory system (see scripts/memory_*, .claude/memory/)

Consolidates current context into persistent memory for knowledge preservation across context boundaries.

## Usage
```
/sleep [level]
```

**Parameters:**
- `level` (optional): Consolidation level - `normal`, `critical`, or `emergency`
  - Default: `critical` (recommended for manual triggers)

## What It Does

### 1. **Context Assessment**
- Analyzes current context usage
- Determines appropriate consolidation level
- Reports memory efficiency status

### 2. **Memory Consolidation**
- **Captures Current State**: Agent status, project status, active work
- **Updates Essential Knowledge**: Latest tools, discoveries, and working systems
- **Creates Memory Snapshot**: Complete state preservation for wake protocol
- **Saves Deep Memory**: Comprehensive backup with timestamps

### 3. **Knowledge Preservation**
- Updates `.claude/memory/ESSENTIAL_WORKFLOW_KNOWLEDGE.md` with latest discoveries
- Preserves critical tools and scripts that must never be forgotten
- Documents current project status and priorities
- Saves agent coordination state and active work

### 4. **Reliability Features**
- **SHA-256 Checksums**: Ensures data integrity during preservation
- **Atomic Writes**: Prevents corruption during save operations
- **Backup Storage**: Redundant copies in `.claude/memory_backup/`
- **Verification**: Confirms successful consolidation

## When to Use

### **Manual Triggers**
- Before ending work sessions to preserve progress
- When approaching context limits (>70% usage)
- Before major task transitions or sprint changes
- After completing critical discoveries or fixes

### **Preparation for Context Reset**
- Save current state before Claude Code session limits
- Preserve ongoing work and coordination state
- Ensure critical knowledge survives context boundaries

## Output Example
```
🧠 Starting memory consolidation (level: critical)
✅ Essential knowledge updated
✅ Memory snapshot saved for wake protocol
✅ Deep consolidation saved: .claude/memory/DEEP_CONSOLIDATION_20250716_0900.md
✅ Memory consolidation completed (level: critical)

📊 Context Usage: 85.2%
🎯 Memory preserved for wake protocol
💡 Use '/wake' to restore after context reset
```

## Files Created/Updated
- `.claude/memory/ESSENTIAL_WORKFLOW_KNOWLEDGE.md` - Critical tools (auto-updated)
- `.claude/memory/LATEST_MEMORY_SNAPSHOT.json` - Complete state for wake protocol
- `.claude/memory/DEEP_CONSOLIDATION_*.md` - Timestamped comprehensive backup
- `.claude/memory_backup/` - Redundant backup copies

## Integration with Automatic System
This command uses the same memory consolidation system that runs automatically at 70% context usage. Manual triggers allow you to:
- Force consolidation before automatic thresholds
- Create checkpoints at strategic moments
- Prepare for planned context resets

## See Also
- `/wake` - Restore memory after context reset
- Context monitoring runs automatically at 70% usage
- Memory files persist across all Claude Code sessions

---
**🎯 Purpose**: Ensure critical workflow knowledge NEVER gets lost, enabling seamless work continuation across any context boundary.