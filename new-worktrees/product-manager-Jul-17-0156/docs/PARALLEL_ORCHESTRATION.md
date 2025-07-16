# Parallel Work Orchestration System

## Overview

This document defines the parallel work orchestration system for LeanVibe Agent Hive, inspired by Extreme Programming (XP) methodology. The system coordinates multiple subagents working simultaneously on separate worktrees with feature branches.

## Orchestration Architecture

### 1. GitHub Issues as Coordination Hub

Each major task is tracked via GitHub issues with the following structure:

```
Title: [AGENT-TYPE] Task Description
Labels: agent:type, priority:high/medium/low, status:assigned/in-progress/review/complete
Assignee: @orchestrator-agent (for coordination)

Body:
## Task Description
Clear, specific description of what needs to be accomplished

## Acceptance Criteria
- [ ] Specific, measurable criteria
- [ ] Test coverage requirements
- [ ] Documentation requirements
- [ ] Quality gates

## Agent Assignment
- Worktree: /path/to/worktree
- Branch: feature/task-name
- Agent Persona: backend/frontend/docs/analysis

## Progress Tracking
Agent updates every 2 hours via comments:
- Current status
- Completed items
- Blockers/questions
- Next steps

## Completion Checklist
- [ ] All acceptance criteria met
- [ ] Tests passing
- [ ] Code quality gates passed
- [ ] Documentation updated
- [ ] Ready for PR creation
```

### 2. Worktree-Agent Mapping

Current active assignments:

| Worktree | Path | Branch | Agent Type | Current Focus |
|----------|------|--------|------------|---------------|
| **docs-tutorial** | `/agent-hive-docs-tutorial` | `feature/docs-tutorial-implementation` | Documentation Agent | Tutorial development |
| **tech-debt** | `/agent-hive-tech-debt` | `feature/tech-debt-analysis-and-review` | Analysis Agent | Code quality review |
| **main** | `/agent-hive` | `main` | Orchestrator | Coordination & integration |

### 3. XP-Inspired Practices

#### Small, Frequent Commits
- Commit after each completed sub-task (max 2 hours work)
- Descriptive commit messages with achievements
- Automatic push via post-commit hooks

#### Continuous Integration
- All commits must pass quality gates
- Tests must pass before commit
- Build validation on every change

#### Agent Collaboration
- Cross-agent reviews via GitHub PR system
- Knowledge sharing through issue comments
- Pair programming through coordinated tasks

#### Test-Driven Development
- Write tests first for new functionality
- Maintain >90% test coverage
- Include test results in progress updates

#### Simple Design
- YAGNI principle - implement only what's needed
- Refactor continuously to reduce technical debt
- Clear, readable code over clever solutions

#### Regular Retrospectives
- Daily agent status updates
- Weekly retrospective via GitHub discussion
- Continuous process improvement

## Coordination Commands

### Issue Management
```bash
# Create task issue for agent
python cli.py orchestrate issue create \
  --title "[DOCS] Complete comprehensive tutorial system" \
  --agent-type docs \
  --worktree docs-tutorial \
  --priority high

# Update progress on issue
python cli.py orchestrate issue update \
  --issue 123 \
  --status "50% complete - finished authentication section" \
  --next-steps "Starting article management system"

# List active agent tasks
python cli.py orchestrate issue list --status in-progress

# Close completed task
python cli.py orchestrate issue close \
  --issue 123 \
  --pr-url "https://github.com/org/repo/pull/456"
```

### Agent Coordination
```bash
# Spawn agent on specific worktree
python cli.py orchestrate spawn \
  --worktree docs-tutorial \
  --agent-type documentation \
  --task-issue 123 \
  --depth ultrathink

# Monitor all agent progress
python cli.py orchestrate monitor --real-time

# Request status update from all agents
python cli.py orchestrate status --all-agents

# Coordinate cross-agent collaboration
python cli.py orchestrate collaborate \
  --primary-agent docs \
  --supporting-agent tech-debt \
  --shared-task "API documentation review"
```

### Progress Tracking
```bash
# Generate daily status report
python cli.py orchestrate report --daily

# Check blockers across all agents
python cli.py orchestrate blockers --list

# Update sprint progress
python cli.py orchestrate sprint --update
```

## Agent Instructions Template

### For Junior-Mid Level Developer Agents

```markdown
# Agent Assignment: [TASK-NAME]

## Your Role
You are a [AGENT-TYPE] working on [SPECIFIC-COMPONENT]. You have mid-level development skills and can achieve excellent results with clear guidance.

## Working Environment
- **Worktree**: /path/to/your/worktree
- **Branch**: feature/your-task-name
- **Base Branch**: main
- **Issue**: #123 (track progress here)

## Task Breakdown
1. **Immediate Task**: [First specific task]
   - Expected time: 2 hours
   - Acceptance criteria: [specific criteria]
   - Tests required: [specific tests]

2. **Next Task**: [Second specific task]
   - Expected time: 1.5 hours
   - Dependencies: Complete task 1
   - Integration points: [other components]

## Work Protocol
1. **Before Starting**: Comment on issue #123 with start time
2. **Every 2 Hours**: Update issue with progress
3. **After Each Task**: Commit changes with descriptive message
4. **When Stuck**: Comment on issue asking for help
5. **When Complete**: Request PR creation

## Quality Standards
- All tests must pass before commit
- Code coverage >90% for new code
- Follow existing patterns and conventions
- Update documentation for any new features
- Use descriptive variable and function names

## Communication
- **Progress Updates**: Every 2 hours on issue #123
- **Questions**: Tag @orchestrator-agent on issue
- **Blockers**: Immediate comment on issue
- **Completion**: Comment with summary and request PR

## Success Criteria
- [ ] All acceptance criteria met
- [ ] Tests passing (include test results)
- [ ] Documentation updated
- [ ] Code review ready
- [ ] Integration tested

Remember: You're capable of excellent work. When in doubt, ask questions early rather than guessing.
```

## Current Sprint Planning

### Active Tasks (Sprint 1)

#### Issue #1: Documentation & Tutorial System
- **Agent**: Documentation Agent
- **Worktree**: docs-tutorial
- **Priority**: High
- **Estimate**: 1 week
- **Status**: Ready to start

**Acceptance Criteria**:
- [ ] Complete Medium clone tutorial
- [ ] API documentation for all endpoints
- [ ] Component documentation for frontend
- [ ] Deployment guides
- [ ] Testing documentation

#### Issue #2: Technical Debt Analysis & Refactoring
- **Agent**: Analysis Agent  
- **Worktree**: tech-debt
- **Priority**: High
- **Estimate**: 1 week
- **Status**: Ready to start

**Acceptance Criteria**:
- [ ] Comprehensive code quality analysis
- [ ] Refactoring recommendations
- [ ] Performance optimization opportunities
- [ ] Security audit results
- [ ] Dependency update plan

### Future Sprints

#### Sprint 2: Feature Development
- New API features based on analysis
- Frontend enhancements
- Performance optimizations

#### Sprint 3: Production Readiness
- Deployment automation
- Monitoring and observability
- Security hardening

## Monitoring and Metrics

### Daily Metrics
- Commits per agent
- Test coverage trends
- Issue completion rate
- Blocker resolution time

### Weekly Metrics
- Sprint velocity
- Quality gate failures
- Cross-agent collaboration instances
- Technical debt reduction

### Quality Gates
- All tests pass
- Code coverage >90%
- No security vulnerabilities
- Performance benchmarks met
- Documentation complete

## Escalation Procedures

### When Agent is Stuck (>30 minutes)
1. Agent comments on issue with specific question
2. Orchestrator provides guidance within 15 minutes
3. If complex, spawn supporting agent for collaboration

### When Quality Gates Fail
1. Agent reverts to last working commit
2. Analysis of failure cause
3. Specific guidance provided
4. Re-attempt with clearer instructions

### When Deadlines at Risk
1. Task breakdown into smaller pieces
2. Parallel work assignment
3. Scope reduction if necessary
4. Additional agent support

This orchestration system ensures efficient parallel development while maintaining code quality and clear communication.