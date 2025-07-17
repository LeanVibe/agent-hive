# Worktree Consolidation Plan

## Current Status: 14 worktrees remaining (Target: <15 ✅)

### CONSOLIDATION OPPORTUNITIES:

#### 1. Infrastructure branches (CONSOLIDATE)
- `infrastructure-Jul-17-1349`: Critical import fixes (2 commits ahead) - KEEP
- `infrastructure-Jul-17-1444`: Similar critical fixes (1 commit ahead) - MERGE INTO 1349

#### 2. Integration Specialist branches (CONSOLIDATE)
- `integration-specialist-Jul-17-1349`: FastAPI HTTP server (2 commits ahead) - KEEP
- `integration-specialist-Jul-17-1438`: API Gateway implementation (2 commits ahead) - MERGE INTO 1349
- `integration-specialist-Jul-17-0156`: Sync changes only (2 commits ahead) - ARCHIVE
- `integration-specialist-Jul-17-0824`: Sync changes only (4 commits ahead) - ARCHIVE

#### 3. Performance branches (CONSOLIDATE)
- `performance-Jul-17-1349`: PM coordination system (4 commits ahead) - KEEP
- `performance-Jul-17-0823`: Technical debt reduction (6 commits ahead) - EVALUATE FOR MERGE

#### 4. Frontend branches (CONSOLIDATE)
- `frontend-Jul-17-1438`: WebSocket metrics (1 commit ahead) - KEEP
- `frontend-Jul-17-0824`: General changes (5 commits ahead) - EVALUATE FOR MERGE

#### 5. Standalone branches (KEEP)
- `monitoring-Jul-17-1349`: Unique monitoring features - KEEP
- `security-Jul-17-0944`: Security improvements - KEEP
- `pm-agent-new`: Foundation epic consolidation - KEEP

## TARGET FINAL STATE: 10 worktrees
1. Main integration branch
2. `infrastructure-Jul-17-1349` (consolidated)
3. `integration-specialist-Jul-17-1349` (consolidated)
4. `performance-Jul-17-1349` (consolidated)
5. `frontend-Jul-17-1438` (active development)
6. `monitoring-Jul-17-1349` (unique features)
7. `security-Jul-17-0944` (security improvements)
8. `pm-agent-new` (foundation epic)
9. `frontend-Jul-17-0824` (evaluate for merge)
10. `performance-Jul-17-0823` (evaluate for merge)

## CONSOLIDATION ACTIONS:
1. Merge `infrastructure-Jul-17-1444` into `infrastructure-Jul-17-1349`
2. Merge `integration-specialist-Jul-17-1438` into `integration-specialist-Jul-17-1349`
3. Archive `integration-specialist-Jul-17-0156` (sync only)
4. Archive `integration-specialist-Jul-17-0824` (sync only)