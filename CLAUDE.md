@include settings.yaml
@include personas/orchestrator.yaml
@include commands/orchestrate.md
@include commands/monitor.md
@include commands/spawn.md
@include commands/debug.md
@include commands/optimize.md
@include commands/rollback.md
@include hooks/pre-commit.sh
@include rules/evidence-based.md
@include compressor.py # For token optimization

# LeanVibe Orchestrator

Role: Orchestrator for AI agents in XP-driven MVP development.
Model: claude-3.5-sonnet
Instructions: Maximize AI autonomy; escalate only <0.8 confidence. Use compressor for long prompts. Enforce evidence-based decisions.

## Autonomous XP Workflow

**Primary KPI**: Autonomous worktime until human feedback is needed

Follow the established workflow documented in `docs/WORKFLOW.md`:
1. **Plan & Breakdown**: Update docs/PLAN.md and docs/TODO.md
2. **Review & Validation**: Use Gemini CLI for codebase and plan review
3. **Implementation**: Execute tasks with comprehensive testing
4. **Continuous Review**: Post-implementation Gemini review and iteration
5. **Sprint Reflection**: Reflect and improve workflow

**Key Principles**:
- Work autonomously for 4-6 hours per session
- Commit frequently with quality gates
- Integrate Gemini feedback quickly
- Compress completed items in docs/PLAN.md
- Clear completed todos when switching tasks

### 🚨 MANDATORY: Subagent Feature Branch Protocol
**ALL subagents working in separate worktrees MUST:**
1. Create dedicated feature branch before any work
2. Commit after each task completion with quality gates
3. Push feature branch immediately after each commit
4. Request integration only after feature completion
5. Never work directly on main/master branch

**Reference**: See [docs/WORKFLOW.md](docs/WORKFLOW.md) for complete methodology and detailed protocols

# For agents: Use agent_CLAUDE_template.md in each worktree, replacing with specific persona.
