# COMMUNICATION ARCHITECTURE PLAN

## CRITICAL ISSUES IDENTIFIED

### 1. NO EFFECTIVE PM AGENT
- integration-specialist-Jul-17-1331 is TMUX_ONLY (no worktree)
- Cannot function as proper PM without codebase access
- Agents have no clear chain of command

### 2. BROKEN COMMUNICATION FLOWS
- Agents don't know who to report to
- No standardized reporting protocols
- No clear task assignment mechanism
- No progress tracking visibility

### 3. RESOURCE WASTE
- Multiple agents doing overlapping work
- Stale agents consuming resources
- No clear role definitions

## PROPOSED SOLUTION ARCHITECTURE

### A. SPAWN PROPER PM AGENT
```
NEW PM AGENT: pm-coordinator-Jul-17-[TIME]
- Full worktree access
- Coordination authority
- Communication hub role
- Window name: agent-pm-coordinator-Jul-17-[TIME]
```

### B. COMMUNICATION PROTOCOLS

#### 1-to-1 (Agent → PM)
```bash
# Standardized reporting format
python scripts/report_to_pm.py --agent AGENT_ID --status STATUS --task TASK --result RESULT
```

#### 1-to-Many (PM → All Agents)
```bash
# Broadcast to all active agents
python scripts/pm_broadcast.py --message MESSAGE --priority PRIORITY
```

#### Many-to-1 (All Agents → PM)
```bash
# Automatic status collection
python scripts/collect_agent_status.py --output pm_dashboard.json
```

### C. AGENT CLEANUP STRATEGY

#### DESPAWN CANDIDATES:
1. **integration-specialist-Jul-17-1331** → Replace with proper PM
2. **frontend-Jul-17-1438** → 3+ hours stale, not responding
3. **integration-specialist-Jul-17-1438** → Duplicate role with 1349
4. **infrastructure-Jul-17-1349** → Keep as backup only

#### KEEP & OPTIMIZE:
1. **infrastructure-Jul-17-1444** → Primary import fixes (rename window)
2. **integration-specialist-Jul-17-1349** → Keep as coordination specialist
3. **monitoring-Jul-17-1349** → System monitoring
4. **performance-Jul-17-1349** → Performance tracking

### D. CLEAR ROLE DEFINITIONS

```
PM AGENT (NEW):
- Coordinates all agents
- Assigns tasks and priorities  
- Collects status reports
- Escalates to human for strategic decisions
- Maintains progress dashboard

INFRASTRUCTURE AGENT:
- Fixes technical issues (import errors)
- Reports progress every 15 minutes
- Escalates blockers to PM

INTEGRATION SPECIALIST:
- Manages code integration workflows
- Coordinates between technical agents
- Reports integration status to PM

MONITORING AGENT:
- Tracks system health
- Monitors agent performance
- Reports issues to PM

PERFORMANCE AGENT:
- Optimizes system performance
- Tracks performance metrics
- Reports bottlenecks to PM
```

## IMPLEMENTATION SEQUENCE

### Phase 1: PM Agent Setup (5 minutes)
1. Spawn proper PM agent with worktree
2. Create communication scripts
3. Test PM agent responsiveness

### Phase 2: Agent Cleanup (10 minutes)  
1. Despawn stale/duplicate agents
2. Rename remaining agent windows for clarity
3. Reassign clear roles

### Phase 3: Communication Deployment (15 minutes)
1. Deploy reporting protocols
2. Test 1-to-1 and 1-to-many communication
3. Establish regular status update cycles

### Phase 4: Workflow Integration (10 minutes)
1. Integrate with existing progress monitoring
2. Test end-to-end communication flow
3. Validate PM agent coordination effectiveness

## SUCCESS CRITERIA

- [ ] PM agent responsive and coordinating
- [ ] All agents know their roles and reporting structure
- [ ] Regular status updates flowing to PM
- [ ] PM can assign tasks and get results
- [ ] Clean agent roster with no duplicates/stale agents
- [ ] Import errors resolved through proper coordination

## ESCALATION PROTOCOL

PM Agent → Human escalation triggers:
1. Strategic decisions beyond PM authority
2. Resource constraints requiring human input
3. Blockers that cannot be resolved with current agents
4. User requirement clarifications needed