# 📋 Documentation Single Source of Truth Rules

## MANDATORY: Check BACKLOG.md FIRST
- **BACKLOG.md**: Master priority list - ALL work priorities are here
- **GitHub Issues**: Auto-synced execution tracking only
- **docs/archived/**: Historical reference (read-only)

## Documentation Workflow
1. **Check BACKLOG.md** before planning any new work
2. **Update BACKLOG.md** for priority changes (auto-syncs to GitHub)
3. **Archive scattered plans** to docs/archived/ (preserve, don't delete)
4. **Use priority system**: P0 (48hr), P1 (1wk), P2 (1mo), P3 (future)

## Automation Available
- `scripts/backlog_sync.py`: GitHub Issues ↔ BACKLOG.md sync
- Git hooks: Pre-commit validation, post-commit auto-sync
- Priority labels: P0-P3 with automatic GitHub issue creation

## Anti-Patterns (AVOID)
- Creating new planning documents (use BACKLOG.md)
- Updating GitHub issues directly (update BACKLOG.md instead)
- Deleting old plans (archive to docs/archived/)
- Multiple competing roadmaps (single source of truth only)

**Result**: 90% less documentation maintenance, 5-second priority decisions