# Scratchpad Directory - Agent Guidelines

## Purpose
This directory serves as a temporary workspace for agents to store analysis files, scripts, and working documents during task execution. Think of it as a shared notepad for the agent team.

## Usage Instructions for All Agents

### 📁 **Mandatory Use Cases**
All agents MUST use this directory for:
- **Analysis documents** - Technical assessments, codebase evaluations, architecture reviews
- **Working scripts** - Temporary Python scripts, bash utilities, data processing tools
- **Strategic plans** - Task breakdowns, implementation strategies, project roadmaps
- **Investigation reports** - Bug analysis, performance evaluations, security audits
- **Coordination notes** - Inter-agent communication, handoff documentation

### 📝 **File Naming Conventions**
```
{task_type}_{topic}_{date}.{extension}

Examples:
- analysis_database_performance_20250718.md
- script_migration_helper_20250718.py
- plan_message_queue_implementation_20250718.md
- report_security_audit_20250718.md
- notes_agent_coordination_20250718.txt
```

### 🔧 **Recommended File Types**
- **`.md`** - Analysis documents, plans, reports (primary format)
- **`.py`** - Working scripts, utilities, data processing
- **`.sql`** - Database queries, migration scripts
- **`.json`** - Configuration examples, data samples
- **`.txt`** - Quick notes, logs, temporary findings
- **`.sh`** - Shell scripts for automation

### 📋 **Template Structure for Analysis Documents**
```markdown
# [Document Title]

## Executive Summary
Brief overview of findings/recommendations

## Context
Background information and scope

## Analysis/Implementation Details  
Main content with technical details

## Recommendations
Actionable next steps

## References
Links to relevant code, docs, or related files
```

### 🚫 **What NOT to Store Here**
- **Production code** - Use proper src directories
- **Permanent documentation** - Use docs/ directory  
- **Configuration files** - Use config/ directory
- **Test files** - Use tests/ directory
- **Large datasets** - Use appropriate data directories
- **Sensitive information** - Use secure storage

### 🧹 **Cleanup Policy**
- **Review files weekly** - Remove obsolete analysis
- **Archive important findings** to appropriate permanent locations
- **Keep working files** for current tasks only
- **Maximum retention**: 30 days for temporary files

### 🤝 **Collaboration Guidelines**
- **Reference other agents' work** - Check existing files before duplicating analysis
- **Use clear file names** - Other agents should understand purpose from filename
- **Add brief comments** - Include context for scripts and complex analysis
- **Update shared documents** - When building on another agent's work, update their file

### 🎯 **Current Priority Files**
Key analysis files for current Phase 3+ initiatives:

1. **`worktree_mission_analysis.md`** - Evaluation of archived worktree relevance
2. **`consolidated_strategic_plan.md`** - Pareto-optimized production readiness plan
3. **`message_queue_analysis.md`** - Comprehensive messaging systems evaluation
4. **`database_migration_strategy.md`** - SQLite to PostgreSQL transition plan

### 📊 **Integration with Main Project**
- **Link to scratchpad files** in commit messages when relevant
- **Reference analysis** in PR descriptions for context
- **Migrate findings** to permanent documentation when stabilized
- **Use for planning** before implementing changes in main codebase

## Example Workflow

```bash
# 1. Create analysis document
echo "# Database Performance Analysis" > scratchpad/analysis_db_perf_$(date +%Y%m%d).md

# 2. Work on temporary script
cat > scratchpad/script_migration_helper.py << 'EOF'
#!/usr/bin/env python3
"""Temporary script to analyze SQLite migration requirements"""
# Working code here...
EOF

# 3. Reference in commit
git commit -m "Implement database optimization

Based on analysis in scratchpad/analysis_db_perf_20250718.md"

# 4. Clean up when task complete
rm scratchpad/script_migration_helper.py
mv scratchpad/analysis_db_perf_20250718.md docs/architecture/
```

## Benefits of Consistent Scratchpad Usage

- **Improved Coordination** - Agents can see each other's thinking process
- **Reduced Duplication** - Avoid repeating analysis work
- **Better Context** - Understand reasoning behind decisions
- **Faster Onboarding** - New agents can quickly understand current state
- **Enhanced Quality** - Peer review of analysis before implementation
- **Audit Trail** - Track decision-making process

---

**Remember**: The scratchpad is a powerful tool for coordination and analysis. Use it consistently to maximize team effectiveness and code quality!