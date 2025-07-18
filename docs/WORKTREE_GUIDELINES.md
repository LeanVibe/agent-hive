# 📁 Git Worktree Guidelines - LeanVibe Agent Hive

## 🎯 Worktree Structure Standard

**MANDATORY**: All new git worktrees MUST be created in the `worktrees/` directory structure.

### Standard Structure
```
agent-hive/                    # Main repository
├── worktrees/                 # All worktrees go here
│   ├── feature-branch-name/   # Feature worktrees
│   ├── agent-work-name/       # Agent worktrees
│   └── hotfix-branch-name/    # Hotfix worktrees
├── README.md
├── cli.py
└── ...
```

### ✅ Correct Worktree Creation
```bash
# Create new worktree in correct location
git worktree add worktrees/feature-auth-system

# Create agent worktree
git worktree add worktrees/performance-agent-Jul-19

# Create hotfix worktree  
git worktree add worktrees/hotfix-critical-bug
```

### ❌ Incorrect Worktree Creation (DO NOT DO)
```bash
# WRONG - Don't create in project root
git worktree add new-feature-branch

# WRONG - Don't create in subdirectories
git worktree add features/new-feature

# WRONG - Don't create in nested paths
git worktree add deep/nested/path/feature
```

## 🛠️ Worktree Management Commands

### Create New Worktree
```bash
# Standard pattern
git worktree add worktrees/[branch-name]

# With specific branch
git worktree add worktrees/feature-name -b new-feature-branch
```

### List Worktrees
```bash
git worktree list
```

### Remove Worktree
```bash
# Remove worktree and clean up
git worktree remove worktrees/feature-name

# Force remove if needed
git worktree remove --force worktrees/feature-name
```

### Cleanup Stale Worktrees
```bash
# Remove stale worktree references
git worktree prune
```

## 📋 Naming Conventions

### Feature Worktrees
- `worktrees/feature-description`
- `worktrees/fix-bug-description`
- `worktrees/refactor-component-name`

### Agent Worktrees
- `worktrees/agent-type-date` (e.g., `worktrees/performance-Jul-19`)
- `worktrees/agent-type-task` (e.g., `worktrees/security-auth-system`)

### Hotfix Worktrees
- `worktrees/hotfix-description`
- `worktrees/emergency-fix-issue`

## 🔄 Lifecycle Management

### During Development
1. **Create**: `git worktree add worktrees/feature-name`
2. **Work**: Make changes in the worktree
3. **Commit**: Regular commits in the worktree
4. **Push**: Push branch to remote
5. **PR**: Create pull request
6. **Review**: Code review process
7. **Merge**: Merge PR to main
8. **Clean**: Remove worktree after merge

### Cleanup Process
```bash
# After successful PR merge
git worktree remove worktrees/feature-name
git branch -D feature-name  # Remove local branch
git remote prune origin     # Clean remote references
```

## 🚨 Important Notes

### Why This Structure?
- **Organization**: All worktrees in one place
- **Clarity**: Easy to find and manage
- **Automation**: Scripts can reliably find worktrees
- **Cleanup**: Simplified cleanup procedures

### Agent Coordination
- Each agent gets its own worktree in `worktrees/`
- No conflicts between agent working directories
- Easy to track agent work progress
- Clean separation of concerns

### Repository Health
- Main repository stays clean
- No worktree pollution in project root
- Consistent structure across all development
- Easy automation and tooling

## 📊 Compliance

**MANDATORY RULE**: All team members and agents must follow this structure.

**Enforcement**: Any worktrees created outside `worktrees/` directory will be flagged for cleanup.

**Migration**: Existing worktrees will be migrated to this structure during next cleanup cycle.

---

**Last Updated**: July 18, 2025  
**Applies To**: All future development work  
**Enforcement**: Immediate