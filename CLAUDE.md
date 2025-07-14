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

# For agents: Use agent_CLAUDE_template.md in each worktree, replacing with specific persona.
