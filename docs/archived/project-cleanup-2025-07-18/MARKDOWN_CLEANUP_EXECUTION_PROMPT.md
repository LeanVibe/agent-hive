# 📋 Markdown File Cleanup Execution Prompt - Systematic Processing

## 🎯 EXECUTION FRAMEWORK

You are a pragmatic senior software engineer with excellent taste. Your mission is to systematically process **44 markdown files** in the project root and transform documentation chaos into a clean, maintainable architecture.

### Core Principles
- **Single Source of Truth**: BACKLOG.md for all priorities
- **Zero Information Loss**: Archive, don't delete valuable content
- **Action-Oriented**: Extract actionable items to BACKLOG.md
- **Clean Architecture**: ≤5 files in project root

## 📋 FILE-BY-FILE PROCESSING TEMPLATE

For each markdown file, follow this systematic evaluation:

### STEP 1: CONTENT ANALYSIS
```markdown
**File**: [filename.md]
**Size**: [file size]
**Last Modified**: [date]

**Content Summary**: [1-2 sentences describing main content]

**Content Type** (select one):
- [ ] Operational (daily use: BACKLOG.md, CLAUDE.md, README.md)
- [ ] Reference (stable docs: API, Architecture, Troubleshooting)
- [ ] Completion Report (historical: *_COMPLETE.md, *_STATUS.md)
- [ ] Planning/Strategy (may contain actionable items)
- [ ] Agent-Specific (requirements, protocols, coordination)
- [ ] Temporary/Generated (reports, sync files)
```

### STEP 2: ACTIONABLE ITEM EXTRACTION
```markdown
**Scan for Actionable Items**:
- [ ] TODO items found: [list 3-5 key todos]
- [ ] Incomplete tasks: [list unfinished work]
- [ ] Missing integrations: [list pending integrations]
- [ ] Outstanding bugs: [list known issues]
- [ ] Documentation gaps: [list missing docs]

**Items to Add to BACKLOG.md**:
Priority | Item | Estimate | Notes
P0 | [critical item] | [time] | [context]
P1 | [high priority] | [time] | [context]
P2 | [medium priority] | [time] | [context]
P3 | [future item] | [time] | [context]
```

### STEP 3: DECISION MATRIX
```markdown
**DECISION** (select one and provide reasoning):

**KEEP IN ROOT** ✅
- Reason: [why essential for daily operations]
- Action: None or [minor updates needed]

**MOVE TO docs/** 📚
- Reason: [why belongs in docs/ directory]
- Target: docs/[specific location]
- Action: Move file, update any references

**EXTRACT + ARCHIVE** 🔄
- Reason: [why contains actionable items]
- Extract: [what to extract to BACKLOG.md or CLAUDE.md]
- Archive to: docs/archived/project-cleanup-2025-07-18/
- Action: Extract → Update BACKLOG.md → Archive original

**ARCHIVE ONLY** 📦
- Reason: [why historical value but not operational]
- Archive to: docs/archived/project-cleanup-2025-07-18/
- Action: Direct move to archive

**DELETE** 🗑️
- Reason: [why no longer needed]
- Action: Delete (with confirmation)
```

### STEP 4: EXECUTION COMMANDS
```bash
# Provide exact bash commands to execute the decision
# Example:
mv FILENAME.md docs/archived/project-cleanup-2025-07-18/
# or
mv FILENAME.md docs/
# or specific extraction commands
```

## 📊 BATCH PROCESSING CATEGORIES

### Category A: Completion Reports (ARCHIVE ALL)
Process together for efficiency:
```
*_COMPLETE.md, *_STATUS.md, *_REPORT.md, *_SUMMARY.md
```

### Category B: Reference Docs (MOVE TO docs/)
```
API_REFERENCE.md, ARCHITECTURE.md, TROUBLESHOOTING.md, DEVELOPMENT.md, DEPLOYMENT.md
```

### Category C: Planning Docs (EXTRACT + ARCHIVE)  
```
*_STRATEGY.md, *_PLAN.md, *_PROTOCOL.md, IMPLEMENTATION_*.md
```

## 🎯 QUALITY GATES

Before processing each file:
- [ ] **Read the file**: Understand content and purpose
- [ ] **Check dependencies**: Look for references from other files
- [ ] **Verify value**: Confirm historical vs operational importance
- [ ] **Extract actionables**: Don't lose incomplete work

After processing each file:
- [ ] **Verify links**: Update any broken references
- [ ] **Test access**: Ensure moved files are accessible where needed
- [ ] **Update BACKLOG.md**: Add extracted items with proper priority
- [ ] **Document decision**: Log reasoning for future reference

## 📋 SYSTEMATIC EXECUTION PLAN

### Files to Process (Priority Order)

**Round 1: Easy Decisions (20 files)**
```
backlog_sync_report.md              → DELETE (auto-generated)
*_COMPLETE.md (8 files)             → ARCHIVE ALL
*_STATUS.md (4 files)               → ARCHIVE ALL  
*_REPORT.md (7 files)               → ARCHIVE ALL
```

**Round 2: Reference Documentation (6 files)**
```
API_REFERENCE.md                    → MOVE to docs/
ARCHITECTURE.md                     → MOVE to docs/
TROUBLESHOOTING.md                  → MOVE to docs/
DEVELOPMENT.md                      → MOVE to docs/
DEPLOYMENT.md                       → MOVE to docs/
WORKTREE_GUIDELINES.md              → MOVE to docs/
```

**Round 3: Extract + Archive (15 files)**
```
AGENT_COMMUNICATION_PROTOCOL.md     → EXTRACT + ARCHIVE
AGENT_COORDINATION_DASHBOARD.md     → EXTRACT + ARCHIVE
AGENT_DELEGATION_STRATEGY.md        → EXTRACT + ARCHIVE
AGENT_REQUIREMENTS.md               → EXTRACT + ARCHIVE
IMPLEMENTATION_STRATEGY.md          → EXTRACT + ARCHIVE
MULTI_AGENT_DELEGATION_STRATEGY.md  → EXTRACT + ARCHIVE
MULTI_AGENT_WORKFLOW_PROTOCOLS.md   → EXTRACT + ARCHIVE
... [continue for all strategy/planning docs]
```

**Round 4: Final Review (3 files)**
```
BACKLOG.md                          → KEEP (verify current)
CLAUDE.md                           → KEEP (verify current)
README.md                           → KEEP (update if needed)
```

## 🚀 SUCCESS VERIFICATION

After processing all files:
```bash
# Verify clean project root
ls -la *.md | wc -l  # Should be ≤ 5

# Verify BACKLOG.md updated with extracted items
grep -c "P[0-3]" BACKLOG.md  # Should be increased

# Verify archive organization
ls docs/archived/project-cleanup-2025-07-18/ | wc -l  # Should be ~35-40

# Verify docs organization  
ls docs/*.md | wc -l  # Should be ~6-8
```

## 🎯 EXECUTION COMMAND

To execute this plan systematically:

```
Process each file using the template above, starting with the easy decisions (completion reports) and working through to the complex extractions (planning documents). Document all decisions and extracted items for transparency and future reference.
```

This framework ensures every file gets proper consideration while maintaining efficiency and preventing information loss.