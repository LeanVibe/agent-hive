---
category: automation
description: Automated workflow for PR creation, review, feedback implementation, and cleanup
---

# AutoFlow - Complete Development Workflow Automation

## Usage
```bash
/autoflow --title "Feature: New authentication system" --description "Implement JWT auth" --branch "feat/auth-system"
/autoflow --title "Fix: Dashboard metrics bug" --description "Fix missing metrics endpoint" --branch "fix/dashboard-metrics" --quick
/autoflow --title "Chore: Code cleanup" --description "Remove unused imports" --branch "chore/cleanup" --skip-review
```

## Automated Workflow Process

### 1. **PR Creation** (5-10 seconds)
- Validate current branch has changes
- Create pull request with comprehensive description
- Add appropriate labels and metadata
- Link to related issues if detected

### 2. **Gemini CLI Review** (30-60 seconds)
- Attempt review with Gemini CLI
- Handle quota limits gracefully
- Fallback to manual review template
- Generate structured feedback report

### 3. **Think & Implement Feedback** (2-15 minutes)
- Analyze review feedback comprehensively
- Categorize feedback by priority and type
- Implement critical and important changes
- Document implementation decisions
- Update PR with feedback responses

### 4. **Git Worktree Cleanup** (10-30 seconds)
- Remove current worktree safely
- Delete local branch after merge
- Clean up temporary files
- Update remote references

### 5. **De-spawn Process** (5-10 seconds)
- Gracefully terminate agent processes
- Clean up tmux sessions
- Remove agent tracking files
- Update orchestrator state

### 6. **Strategic Thinking** (30-60 seconds)
- Analyze workflow efficiency
- Identify improvement opportunities
- Generate next steps recommendations
- Update development metrics

## Command Options

### Required
- `--title`: PR title (following conventional commits)
- `--description`: PR description
- `--branch`: Target branch name (auto-create if needed)

### Optional
- `--quick`: Skip detailed review analysis (5x faster)
- `--skip-review`: Skip Gemini review entirely
- `--no-feedback`: Skip feedback implementation
- `--keep-branch`: Don't delete branch after merge
- `--draft`: Create draft PR
- `--reviewers`: Comma-separated list of reviewers
- `--labels`: Comma-separated list of labels
- `--milestone`: Milestone to assign

## Safety Features

### Pre-flight Checks
- Verify git repository is clean
- Check for uncommitted changes
- Validate branch naming conventions
- Ensure no merge conflicts exist

### Error Handling
- Graceful fallbacks for quota limits
- Automatic retry logic for network issues
- Rollback capabilities for failed operations
- Comprehensive error logging

### Quality Gates
- Minimum change threshold (prevent empty PRs)
- Code quality validation
- Test coverage requirements
- Documentation completeness check

## Integration Points

### Gemini CLI Integration
```bash
# Primary review attempt
gemini -p "Review PR: $PR_URL. Focus on code quality, security, and architectural decisions."

# Quota limit fallback
gemini -m "gemini-1.5-flash" -p "Quick review: $PR_URL"

# Manual review template generation
```

### GitHub CLI Integration
```bash
# PR creation
gh pr create --title "$TITLE" --body "$DESCRIPTION" --label "$LABELS"

# Review management
gh pr review $PR_NUMBER --approve --body "$REVIEW_COMMENT"
```

### Worktree Management
```bash
# Safe worktree removal
git worktree remove --force worktrees/$BRANCH_NAME
git branch -D $BRANCH_NAME
git remote prune origin
```

## Workflow Templates

### Feature Development
```bash
/autoflow --title "feat: User authentication system" \
          --description "Implement JWT-based authentication with role-based access control" \
          --branch "feat/auth-system" \
          --reviewers "security-team,backend-team" \
          --labels "feature,security,high-priority"
```

### Bug Fixes
```bash
/autoflow --title "fix: Dashboard metrics endpoint" \
          --description "Fix missing /api/metrics endpoint causing dashboard errors" \
          --branch "fix/dashboard-metrics" \
          --quick \
          --labels "bug,dashboard,p1"
```

### Maintenance
```bash
/autoflow --title "chore: Code cleanup and optimization" \
          --description "Remove unused imports, optimize imports, fix linting issues" \
          --branch "chore/cleanup" \
          --skip-review \
          --labels "maintenance,cleanup"
```

## Performance Metrics

### Speed Targets
- **Total Workflow**: < 5 minutes for typical changes
- **PR Creation**: < 10 seconds
- **Review Process**: < 60 seconds (with Gemini)
- **Feedback Implementation**: < 2 minutes for minor changes
- **Cleanup**: < 30 seconds

### Success Rates
- **PR Creation**: 99%+ success rate
- **Review Completion**: 95%+ (accounting for quota limits)
- **Feedback Implementation**: 90%+ for automated changes
- **Cleanup Completion**: 99%+ success rate

## Error Recovery

### Common Issues
1. **Quota Limits**: Fallback to manual review
2. **Network Issues**: Retry with exponential backoff
3. **Merge Conflicts**: Guidance for manual resolution
4. **Test Failures**: Automatic fix attempts for common issues

### Rollback Scenarios
- Failed PR creation: Clean up branch and worktree
- Review failure: Continue with manual review
- Feedback implementation failure: Preserve changes, create issue
- Cleanup failure: Mark for manual cleanup

## Implementation Script

The autoflow command executes: `python scripts/autoflow_orchestrator.py` with comprehensive error handling and logging.

## Human Decision Points

### Automatic Decisions
- Code formatting fixes
- Import optimization
- Simple bug fixes
- Documentation updates

### Human Review Required
- Architecture changes
- Security modifications
- Breaking changes
- Complex business logic

### Escalation Triggers
- Test failures after 3 attempts
- Merge conflicts requiring manual resolution
- Security vulnerabilities detected
- Performance regression > 20%

## Success Criteria

- **Zero Manual Steps**: Complete workflow automation
- **High Success Rate**: 95%+ successful completions
- **Fast Execution**: < 5 minutes typical workflow
- **Quality Maintenance**: No reduction in code quality
- **Error Resilience**: Graceful handling of all failure modes

This autoflow system provides a complete development workflow automation while maintaining quality standards and providing appropriate human oversight points.

$ARGUMENTS