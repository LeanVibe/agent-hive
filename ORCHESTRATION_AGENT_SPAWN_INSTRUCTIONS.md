# Orchestration Agent Spawn Instructions

## Agent Overview
- **Agent Type**: Orchestration Agent
- **GitHub Issue**: https://github.com/LeanVibe/agent-hive/issues/26
- **Worktree**: `/Users/bogdan/work/leanvibe-dev/agent-hive/worktrees/orchestration-agent`
- **Duration**: 6-8 hours
- **Position**: Agent 5 of 6 specialized agents

## Spawn Command
```bash
# Navigate to orchestration agent worktree
cd /Users/bogdan/work/leanvibe-dev/agent-hive/worktrees/orchestration-agent

# Spawn the Orchestration Agent
claude --agent-file agent_CLAUDE_template.md --session-id orchestration-agent-001
```

## Pre-Spawn Validation
1. **Worktree Status**: ✅ Created at `/Users/bogdan/work/leanvibe-dev/agent-hive/worktrees/orchestration-agent`
2. **Agent Instructions**: ✅ Available in `agent_CLAUDE_template.md`
3. **GitHub Issue**: ✅ Created as Issue #26
4. **Coordination Setup**: ✅ Protocols established with other 4 agents

## Agent Coordination Context
The Orchestration Agent will coordinate with:
- **Production Agent** (Issue #21) - Deployment orchestration
- **Documentation Agent** (Issue #22) - System documentation
- **Integration Agent** (Issue #23) - System integration
- **Intelligence Agent** (Issue #24) - AI optimization insights

## Initial Agent Tasks
1. **Setup Feature Branch** - Create `feature/orchestration-coordination-sprint`
2. **O.1 Implementation** - Dynamic agent management (3-4 hours)
3. **O.2 Implementation** - Advanced coordination (3-4 hours)
4. **Quality Gates** - Maintain 100% test coverage
5. **Documentation** - Real-time documentation updates

## Success Validation
- [ ] Dynamic agent scaling operational
- [ ] Intelligent load balancing active
- [ ] Resource optimization achieved (30% improvement)
- [ ] Multi-agent coordination enhanced
- [ ] Performance monitoring operational
- [ ] Cross-agent communication protocols established

## Autonomous Operation
- **Duration**: 6-8 hours autonomous operation
- **Confidence Threshold**: Escalate at <0.8 confidence
- **Progress Updates**: Every 2 hours to GitHub issue #26
- **Quality Gates**: All tests pass before completion

## Post-Spawn Integration
After successful spawn, the agent will:
1. Automatically create and push feature branch
2. Begin O.1 dynamic agent management implementation
3. Coordinate with other 4 agents for integration planning
4. Maintain quality gates and documentation standards
5. Progress through O.2 advanced coordination systems

---

**Status**: ✅ Ready for spawn  
**Agent Count**: 5/6 specialized agents  
**Coordination**: Multi-agent orchestration protocols active  
**Quality Gates**: 100% test coverage, <200ms response times  

## Next Agent
After Orchestration Agent completion, spawn **Quality Agent** (6th/6th) for final sprint coordination.