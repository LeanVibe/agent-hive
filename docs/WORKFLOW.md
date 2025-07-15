# LeanVibe Agent Hive - Autonomous XP Workflow

## Overview

This document defines the autonomous working methodology for the LeanVibe Agent Hive project, inspired by Extreme Programming (XP) principles. The primary goal is to maximize autonomous work time until human feedback is needed.

## Key Performance Indicator (KPI)

**Primary KPI**: Autonomous worktime until human feedback is needed
- Sessions for clarifying details are acceptable
- Once details are clear, Claude + Gemini should work autonomously until entire plan is implemented
- Minimize human intervention during implementation phases

## 🚨 MANDATORY: Subagent Feature Branch Protocol

### For ALL Subagents Working in Separate Worktrees

**CRITICAL REQUIREMENT**: Every subagent MUST follow this protocol without exception.

#### 1. Create Dedicated Feature Branch
- **NEVER work directly on main/master branch**
- **Create feature branch** before any work begins
- **Name format**: `feature/{subagent-purpose}-{component}`
- **Examples**: 
  - `feature/docs-update-comprehensive`
  - `feature/tutorial-medium-clone`
  - `feature/tech-debt-analysis`
  - `feature/phase2-ml-components`

#### 2. Commit Protocol (MANDATORY)
- **Frequency**: After each individual task completion
- **Quality Gates**: All tests MUST pass before commit
- **Message Format**: Descriptive with component and achievement
- **Template**:
```
feat(component): Brief description

✅ Completed: Specific achievements
✅ Tests passed ✅ Build successful

Technical details and metrics

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### 3. Automatic Branch Pushing
- **Automated**: Post-commit hook automatically pushes feature branches
- **Manual backup**: `git push origin feature/branch-name` if hook fails
- **Purpose**: Maintain visibility and backup of work
- **Coverage**: Applies to feature/*, fix/*, hotfix/* branches only

#### 4. Integration Request Protocol
- **Only after feature completion**: Request integration when entire feature is done
- **Include**: Test results, quality metrics, completion summary
- **Never**: Partial or incomplete work integration

#### 5. Branch Lifecycle Management
- **Duration**: Keep branch active only during active development
- **Cleanup**: Delete after successful integration
- **No persistence**: Feature branches are temporary working branches

### Worktree Integration and Cleanup Protocol

#### When Work is Complete
1. **Notify Integration Agent**: Signal that feature branch work is complete
2. **Provide Integration Summary**: Include test results, achievements, changes
3. **Wait for Integration**: Do not delete worktree until integration is confirmed
4. **Verify Integration**: Confirm work appears in main branch

#### Worktree Cleanup (Integration Agent Only)
1. **Validate Completion**: Ensure all work is properly integrated into main
2. **Remove Worktree**: `git worktree remove /path/to/worktree`
3. **Delete Feature Branch**: `git branch -d feature/branch-name`
4. **Clean Remote**: `git push origin --delete feature/branch-name`

## Workflow Phases

### Phase 1: Planning & Breakdown

1. **Update docs/PLAN.md**
   - Plan tasks in advance following XP principles
   - Keep plan up to date with current progress
   - Compress completed items that are no longer relevant
   - Focus on current and next immediate priorities

2. **Update docs/TODO.md**
   - Break down current task into immediate priorities
   - Evaluate all implementation details
   - Clear completed todos when switching to new tasks
   - Maintain only actionable, current items

### Phase 2: Review & Validation

3. **Gemini CLI Review**
   - Use `gemini cli` to review codebase
   - Evaluate plan and todo breakdowns
   - Validate implementation details
   - Get feedback on approach before implementation

4. **Incorporate Feedback**
   - Update docs/PLAN.md with Gemini feedback
   - Adjust docs/TODO.md based on review
   - Refine implementation approach

### Phase 3: Implementation

5. **Execute Tasks**
   - Create feature branch for each task
   - Implement tasks following the refined plan
   - Maintain focus on current TODO items
   - Write comprehensive tests for all components
   - Ensure quality gates are met

6. **Commit & Push**
   - Commit each completed task on feature branch
   - Include test results and quality metrics
   - Push feature branch to origin
   - Merge to main after task completion
   - Delete feature branch after merge

### Phase 4: Continuous Review

7. **Post-Implementation Review**
   - Ask Gemini to review completed work
   - Identify areas for improvement
   - Validate that requirements are met

8. **Iterate & Improve**
   - Implement Gemini feedback
   - Update documentation based on learnings
   - Commit improvements
   - Proceed to next task

### Phase 5: Sprint Reflection

9. **Sprint Completion**
   - Reflect on what went well
   - Identify workflow improvements
   - Document lessons learned
   - Plan next sprint/week

## Documentation Standards

### docs/PLAN.md
- **Current Status**: Always up to date with progress
- **Task Hierarchy**: Clear priority levels (PRIORITY X.Y format)
- **Completion Tracking**: Mark completed items, compress old details
- **Forward Looking**: Focus on current and next phases

### docs/TODO.md
- **Immediate Actions**: Only current, actionable items
- **Clean Slate**: Clear completed todos when switching tasks
- **Detailed Breakdown**: Sufficient detail for autonomous execution
- **Priority Ordered**: Most important tasks first

## Autonomous Work Principles

### 1. Self-Directed Execution
- Follow the plan without waiting for permission
- Make implementation decisions based on established patterns
- Use test-driven development for validation

### 2. Continuous Integration
- Commit frequently with quality gates
- Push changes to maintain visibility
- Never break existing functionality

### 3. Feedback Integration
- Actively seek Gemini review at key checkpoints
- Implement feedback quickly and thoroughly
- Document decisions and rationale

### 4. Quality Assurance
- Write comprehensive tests for all components
- Maintain code quality standards
- Ensure all quality gates pass before commits

## Tools & Commands

### Gemini CLI Integration
```bash
# Review codebase and plan
gemini cli review-plan --file docs/PLAN.md

# Review implementation
gemini cli review-code --changes "describe changes"

# Evaluate approach
gemini cli evaluate-approach --context "current context"
```

### Git Workflow
```bash
# Feature branch workflow
git checkout -b feature/phase-X-task-description
git add -A
git commit -m "Brief description

✅ Completed: Specific achievements
✅ Tests passed ✅ Build successful

Technical details and metrics

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin feature/phase-X-task-description

# After task completion, merge to main
git checkout main
git merge feature/phase-X-task-description
git push origin main
git branch -d feature/phase-X-task-description
```

### Worktree Management
```bash
# Create worktree for new phase
git worktree add ../agent-hive-phase2 -b phase2/main

# Switch between worktrees
cd ../agent-hive-phase2

# List all worktrees
git worktree list

# Remove worktree when done
git worktree remove ../agent-hive-phase2
```

## Success Metrics

### Autonomous Work Sessions
- **Target**: 4-6 hours of autonomous work per session
- **Measurement**: Time between human interventions
- **Quality**: No regression in code quality or test coverage

### Implementation Velocity
- **Target**: Complete planned tasks within estimated timeframes
- **Measurement**: Tasks completed per sprint/week
- **Quality**: All quality gates passed, comprehensive tests

### Feedback Cycles
- **Target**: Quick incorporation of Gemini feedback
- **Measurement**: Time from feedback to implementation
- **Quality**: Improved code quality after feedback

## Workflow Improvements

### Iteration 1 (Current)
- Established basic XP workflow
- Implemented Gemini review integration
- Created comprehensive documentation

### Future Improvements
- [ ] Automated quality gate integration
- [ ] Enhanced Gemini feedback processing
- [ ] Improved autonomous decision making
- [ ] Better progress tracking and metrics

## References

- **CLAUDE.md**: Project-specific configuration and guidelines
- **docs/PLAN.md**: Current development plan and priorities
- **docs/TODO.md**: Immediate actionable tasks
- **Extreme Programming**: Methodology inspiration and principles