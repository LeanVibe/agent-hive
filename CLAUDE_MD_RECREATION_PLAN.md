# 🔄 CLAUDE.md Recreation Plan - Convention Over Configuration

**Generated**: July 18, 2025 1:30 PM  
**Status**: 🎯 **COMPREHENSIVE PLAN** - Main CLAUDE.md + worktree-specific includes  
**Problem**: Lost main CLAUDE.md file with comprehensive project context

## 📊 **ANALYSIS FINDINGS**

### **Historical CLAUDE.md Evolution**
1. **Initial (528d86f)**: Configuration-based with includes (`@include settings.yaml`)
2. **Comprehensive (712205e)**: Best version with project context, tools, workflows
3. **Agent-specific (1ede091)**: Individual agent instructions (Intelligence Agent)
4. **Phase-specific (2db366d)**: Foundation Epic Phase 1 focus
5. **Current**: Missing main CLAUDE.md, only worktree-specific files exist

### **Current Worktree Structure Analysis**
```
worktrees/
├── frontend-Jul-17-0824/CLAUDE.md     # Frontend specialist instructions
├── performance-Jul-17-0823/CLAUDE.md  # Performance specialist template
├── pm-agent-new/CLAUDE.md            # Main coordination agent (phase-specific)
└── security-Jul-17-0944/CLAUDE.md    # Main coordination agent (duplicate)
```

### **Key Issues Identified**
1. **No Main CLAUDE.md**: Missing comprehensive project context
2. **Inconsistent Worktree CLAUDE.md**: Some specific, some duplicated
3. **Phase-specific Context**: Current files focused on old "Foundation Epic Phase 1"
4. **Missing Modern Context**: No memory management, communication fixes, crisis response

## 🎯 **CONVENTION OVER CONFIGURATION APPROACH**

### **Main CLAUDE.md Structure**
```
CLAUDE.md (main project context)
├── Core Project Information
├── Essential Tools & Commands
├── Memory Management & Context
├── Agent Communication System
├── Quality Gates & Workflow
├── Crisis Response & Escalation
└── @include worktree-specific context
```

### **Worktree-Specific Context**
```
worktrees/{worktree-name}/
├── CLAUDE.md (worktree-specific instructions)
├── CLAUDE_EXTENSIONS.md (additional context)
└── CLAUDE_OVERRIDES.md (override main context)
```

### **Convention Rules**
1. **Main CLAUDE.md**: Always read first, contains core project knowledge
2. **Worktree CLAUDE.md**: Extends main context with specific instructions
3. **No Conflicts**: Worktree files extend, never override core context
4. **Automatic Detection**: Claude detects current worktree and includes relevant files

## 🚀 **IMPLEMENTATION PLAN**

### **Phase 1: Main CLAUDE.md Recreation (30 minutes)**
**Based on Best Historical Version (712205e) + Current Context**

#### **Core Sections**
1. **Project Overview**: Multi-agent orchestration system
2. **Memory Management**: Essential knowledge, wake/sleep protocols
3. **Essential Tools**: Fixed agent communication, quality gates
4. **Agent Coordination**: Communication standards, evidence-based validation
5. **Crisis Management**: Current crisis response knowledge
6. **Worktree Integration**: Convention over configuration includes

#### **Modern Updates**
- **Communication System**: Updated with fixed scripts and window mapping
- **Crisis Response**: Include current crisis management approaches
- **Quality Gates**: Evidence-based workflow with Definition of Done
- **Context Management**: Memory consolidation and wake protocols

### **Phase 2: Worktree-Specific Files (45 minutes)**
**Clean up and standardize existing worktree CLAUDE.md files**

#### **Frontend Worktree**
- Keep specific: Frontend specialist instructions
- Add: Dashboard integration context
- Remove: Generic coordination content

#### **Performance Worktree**
- Keep specific: Performance optimization focus
- Add: Technical debt reduction context
- Remove: Duplicate coordination content

#### **PM Agent Worktree**
- Keep specific: PM coordination role
- Add: Sprint planning and delegation context
- Remove: Outdated "Foundation Epic Phase 1" content

#### **Security Worktree**
- Keep specific: Security audit and vulnerability management
- Add: Security monitoring and threat response
- Remove: Duplicate coordination content

### **Phase 3: Convention Implementation (15 minutes)**
**Create automatic worktree detection and include mechanism**

#### **Detection Logic**
```bash
# Detect current worktree
CURRENT_WORKTREE=$(git rev-parse --show-toplevel | xargs basename)

# Check for worktree-specific context
if [[ -f "worktrees/${CURRENT_WORKTREE}/CLAUDE_EXTENSIONS.md" ]]; then
    echo "Including worktree-specific context: ${CURRENT_WORKTREE}"
fi
```

#### **Include Mechanism**
```markdown
<!-- Main CLAUDE.md -->
## Worktree-Specific Context
@include worktrees/{{current_worktree}}/CLAUDE_EXTENSIONS.md
@include worktrees/{{current_worktree}}/CLAUDE_OVERRIDES.md
```

## 📋 **DETAILED MAIN CLAUDE.MD STRUCTURE**

### **1. Project Overview (Based on 712205e)**
```markdown
# LeanVibe Agent Hive - Main Coordination Hub

## Project Overview
Multi-agent orchestration system for autonomous software development with human agency integration.

## Current Status
- **Integration Branch**: integration/phase3-advanced-features
- **Crisis Response**: Active (communication system repaired)
- **Quality Gates**: Evidence-based workflow implemented
- **Agent Communication**: Fixed scripts operational
```

### **2. Memory Management (Enhanced)**
```markdown
## 🧠 CRITICAL MEMORY MANAGEMENT

### Essential Knowledge Files
- `.claude/memory/ESSENTIAL_WORKFLOW_KNOWLEDGE.md`
- `COMMUNICATION_SYSTEM_FIX.md`
- `NEW_WORKFLOW_DESIGN.md`
- `AGENT_FEEDBACK_ANALYSIS.md`

### Wake Protocol (Enhanced)
1. Read essential knowledge files
2. Check agent communication system status
3. Verify crisis response state
4. Restore context from memory consolidation
```

### **3. Essential Tools (Updated)**
```markdown
## 🔧 ESSENTIAL TOOLS

### Agent Communication (FIXED)
```bash
# PRIMARY: Fixed communication with window mapping
python scripts/fixed_agent_communication.py --agent security --message "TASK"

# CANONICAL: Standard communication
python scripts/send_agent_message.py --agent security --message "TASK"
```

### Quality Gates (Evidence-Based)
```bash
# MANDATORY: Evidence-based validation
pytest tests/ -x --tb=short
python -m py_compile **/*.py
git status && git commit -m "feat: description"
git push origin branch-name
```
```

### **4. Crisis Management (Current)**
```markdown
## 🚨 CRISIS RESPONSE PROTOCOLS

### Communication System Status
- **Status**: ✅ OPERATIONAL
- **Fixed Script**: `scripts/fixed_agent_communication.py`
- **Window Mapping**: Updated for current agent windows

### Evidence-Based Workflow
- **Definition of Done**: Deliverables must exist and be validated
- **Validation Mechanisms**: File existence, content, quality gates, commits
- **Accountability**: No completion without git evidence

### Escalation Triggers
- Agent coordination failures
- Quality gate failures
- Communication system issues
- Security vulnerabilities
```

### **5. Worktree Integration (Convention)**
```markdown
## 🔄 WORKTREE-SPECIFIC CONTEXT

### Current Worktree Detection
Auto-detected worktree: {{current_worktree}}

### Worktree-Specific Instructions
@include worktrees/{{current_worktree}}/CLAUDE_EXTENSIONS.md

### Worktree-Specific Overrides
@include worktrees/{{current_worktree}}/CLAUDE_OVERRIDES.md

### Available Worktrees
- **frontend-Jul-17-0824**: Frontend specialist context
- **performance-Jul-17-0823**: Performance optimization context
- **pm-agent-new**: PM coordination and sprint planning
- **security-Jul-17-0944**: Security audit and monitoring
```

## 🎯 **SUCCESS CRITERIA**

### **Main CLAUDE.md Quality Gates**
- [ ] Contains all essential project context
- [ ] Includes modern communication system knowledge
- [ ] Has crisis response and escalation procedures
- [ ] Implements convention over configuration
- [ ] Automatically detects and includes worktree context

### **Worktree Files Quality Gates**
- [ ] Each worktree has specific, non-duplicate content
- [ ] No conflicts with main CLAUDE.md
- [ ] Extends main context appropriately
- [ ] Removes outdated phase-specific content

### **Integration Quality Gates**
- [ ] Automatic worktree detection works
- [ ] Include mechanism functions correctly
- [ ] No duplicate information across files
- [ ] Comprehensive coverage of project knowledge

## 🔍 **GEMINI CLI EVALUATION QUESTIONS**

### **Architecture Questions**
1. **Is the convention over configuration approach optimal for this multi-worktree project?**
2. **Does the main CLAUDE.md + worktree-specific approach prevent conflicts?**
3. **Are there better alternatives to the include mechanism?**

### **Content Questions**
1. **Does the main CLAUDE.md capture all essential project knowledge?**
2. **Are the worktree-specific files properly scoped and focused?**
3. **Is the historical knowledge integration comprehensive?**

### **Implementation Questions**
1. **Is the 90-minute implementation timeline realistic?**
2. **Are there potential issues with the automatic detection logic?**
3. **Does this approach scale to additional worktrees?**

---

**Status**: 🎯 **COMPREHENSIVE PLAN READY** - Main CLAUDE.md + worktree convention  
**Next Action**: Evaluate plan with Gemini CLI, then implement  
**Timeline**: 90 minutes for complete implementation  
**Key Innovation**: Convention over configuration with automatic worktree detection