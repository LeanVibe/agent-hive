# Custom Commands & Workflow Audit Task

## Mission
Comprehensive audit and streamlining of Agent Hive's custom commands, scripts, and workflow documentation to eliminate redundancy and improve efficiency.

## Core Task
Re-evaluate all custom commands from `.claude` code and documentation (@docs/INDEX.md @docs/archive/CLAUDE.md) to ensure supporting scripts, folders, and processes are still used as expected.

## Specific Deliverables

### 1. Command Inventory & Analysis
- **Audit all custom commands** in `.claude/` directory
- **Map command-to-script relationships** (which commands use which scripts)
- **Identify unused/deprecated commands** and scripts
- **Document command dependencies** and workflow integration points

### 2. Workflow Streamlining
- **Create Mermaid diagrams** showing:
  - Current command workflow
  - Proposed simplified workflow
  - Agent coordination patterns
- **Identify bottlenecks and redundancies**
- **Propose consolidation opportunities**

### 3. Documentation Updates
- **Update critical documentation** to reflect current state
- **Consolidate scattered command references**
- **Create unified command reference**
- **Update workflow documentation**

### 4. Compound Effect Analysis
- **Identify changes with highest impact-to-effort ratio**
- **Prioritize improvements that enable future efficiency gains**
- **Document self-improving system opportunities**

## Engineering Constraints

### Quality Standards
- **Test-driven approach**: Write tests for any new command functionality
- **YAGNI principle**: Only implement what's immediately needed
- **Simple over clever**: Favor straightforward solutions
- **Vertical slices**: Complete features over partial implementations

### Process Requirements
- **<500 line PRs**: Break work into small, reviewable chunks
- **Documentation-first**: Update docs before implementing changes
- **Backward compatibility**: Ensure existing workflows continue working
- **Version control**: Clear commit messages linking to requirements

## Success Criteria
- [ ] Complete command inventory with usage analysis
- [ ] Mermaid workflow diagrams (current vs proposed)
- [ ] Updated documentation reflecting current state
- [ ] Prioritized improvement roadmap
- [ ] At least 3 compound-effect improvements identified
- [ ] All deliverables in <500 line PRs

## Context
- We're using this development system to develop the tooling itself
- Focus on low-hanging fruit with compound benefits
- Self-improving system approach
- XP methodology adaptation where applicable

## Timeline
- **Analysis Phase**: 2-3 hours
- **Documentation Phase**: 1-2 hours  
- **Improvement Proposals**: 1 hour
- **Total**: 4-6 hours

## Agent Coordination Notes
This task requires:
- Deep system knowledge (Documentation/Architecture Agent)
- Script analysis capabilities (Infrastructure Agent)
- Workflow optimization skills (PM Agent)
- Cross-system integration understanding

**Recommendation**: Delegate to Documentation Agent with Infrastructure Agent support.