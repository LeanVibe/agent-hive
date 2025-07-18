---
category: orchestration  
description: Spawn specialized agent with reliable initialization
---

# Enhanced Agent Spawning System

## Usage
```bash
/spawn --agent integration-specialist --priority 1.1 --task "api-gateway-repair" --timeline "3-days"
/spawn --agent service-mesh --priority 1.2 --task "service-discovery-integration" --timeline "2-days"  
/spawn --agent frontend --priority 1.3 --task "dashboard-integration-repair" --timeline "2-days"
```

## Automated Process
1. **Worktree Creation**: Create isolated Git worktree with quality gates
2. **Tmux Session**: Start named tmux window with Claude Code (--dangerously-skip-permissions)
3. **Instruction Delivery**: Reliable delivery of specialized CLAUDE.md instructions
4. **Agent Activation**: Automatic activation ensuring agents work without manual intervention
5. **Initialization Verification**: Confirm agent received instructions and is active
6. **Status Tracking**: Register agent in orchestrator tracking system
7. **Progress Monitoring**: Setup automated progress reporting every 2 hours

## Agent Types Available
- **integration-specialist**: API Gateway, HTTP servers, service integration
- **service-mesh**: Service discovery, health checks, distributed systems
- **frontend**: UI/UX, dashboard integration, WebSocket connections
- **security**: Authentication, authorization, encryption, compliance
- **infrastructure**: Redis, monitoring, scaling, high availability
- **performance**: Optimization, load testing, benchmarking
- **monitoring**: Observability, metrics, alerting, conflict resolution

## Implementation Script
```bash
python scripts/enhanced_agent_spawner.py \
    --agent-type integration-specialist \
    --priority 1.1 \
    --task "Fix API Gateway foundation - replace simulation with real FastAPI server" \
    --timeline "3 days" \
    --human-decision-points "Day 2: Architecture review, Day 3: Production config" \
    --success-criteria "Real HTTP server,All tests passing,Service discovery integration" \
    --escalation-triggers "Test failures after 4h,Integration issues,Architecture decisions"
```

## Quality Gates
- **Agent Verification**: Confirm Claude Code running with correct instructions
- **Communication Test**: Verify agent can send/receive messages via pm-agent
- **Task Understanding**: Agent acknowledges specific objectives and timeline
- **Progress Setup**: Automated 2-hour progress reporting configured
- **Human Decision Points**: Clear escalation matrix established

## Reliability Features
- **Retry Logic**: Automatic retry if agent initialization fails
- **Instruction Verification**: Confirm agent received and understood instructions
- **Status Monitoring**: Real-time agent lifecycle state tracking
- **Cleanup Protocol**: Automatic cleanup if spawning fails
- **Recovery Mechanism**: Re-spawn capability if agent becomes unresponsive

## Human Agency Integration
- **Decision Authority Matrix**: Clear escalation protocols (autonomous vs human required)
- **Progress Checkpoints**: Scheduled human review points for critical decisions
- **Quality Review**: Human validation of agent work at completion milestones
- **Strategic Oversight**: Human control over architecture and business decisions

## Example Workflows

### Week 1 Sprint Foundation Fixes
```bash
# Results in agents like: integration-specialist-Jul-16-14:30, service-mesh-Jul-16-14:32
/spawn --agent integration-specialist --priority 1.1 --task "api-gateway-foundation-repair"
/spawn --agent service-mesh --priority 1.2 --task "service-discovery-integration"  
/spawn --agent frontend --priority 1.3 --task "dashboard-integration-repair"
```

### Security Hardening Phase
```bash
/spawn --agent security --priority 2.1 --task "authentication-authorization-system"
/spawn --agent infrastructure --priority 2.2 --task "distributed-rate-limiting"
```

### Production Infrastructure
```bash
/spawn --agent infrastructure --priority 3.1 --task "distributed-storage-backend"
/spawn --agent monitoring --priority 3.2 --task "comprehensive-monitoring-system"
```

## Success Metrics
- **100% Agent Initialization Success**: All spawned agents receive instructions reliably
- **< 2 minute spawn time**: From command to active agent working on task
- **Real-time status tracking**: Always know agent status and progress
- **Automated progress reporting**: Every 2 hours without human intervention
- **Automated completion detection**: Agents automatically report when tasks complete
- **Quality validation**: Completion handler validates work before marking complete
- **Clear escalation protocols**: Human decisions only when needed

This enhanced spawn system ensures consistent, reliable agent initialization with clear communication protocols and human agency integration points.

$ARGUMENTS