# LeanVibe Agent Hive Demo Developer Guide

## 1. Prerequisites & Environment Setup

- macOS 10.15+, Python 3.12+, Git, UV (recommended), Bun (optional)
- Install dependencies and verify with `uv sync`, `uv run pytest`, and `python cli.py --help`
- No custom config required for demo; advanced config in `.claude/config/config.yaml` (future)

## 2. Autonomous CLI Workflow & Agentic Prompts

- Use `python cli.py orchestrate --workflow feature-dev --project medium-clone --validate` to start agentic orchestration
- Spawn tasks for backend, frontend, database, etc. using `python cli.py spawn --task "..." --agent ... --depth ultrathink`
- Monitor progress with `python cli.py monitor --metrics --real-time`
- Checkpoint milestones with `python cli.py checkpoint --name ... --validate`
- Use multi-agent PR review: `python cli.py pr create --title ... --auto-review`
- Run tests: `uv run pytest --cov=app --cov-report=html`, `bun test`, `bun run test:e2e`
- Use detailed agentic prompts from the tutorial for each major feature

## 3. Coverage & Readiness Validation

- All CLI commands, agent personas, hooks, and documentation are present and robust
- Pre-commit hook enforces code quality, documentation sync, and project structure
- No major implementation gaps detected

## 4. Remediation Prerequisites Checklist

- [ ] Ensure PLAN.md, README.md, API_REFERENCE.md exist and are current
- [ ] Update documentation if any core features or tests change
- [ ] Ensure all core tests pass before committing
- [ ] Validate CLI help system and import paths
- [ ] Remove debug prints and TODO markers from Python files
- [ ] Ensure required files (cli.py, advanced_orchestration, requirements.txt) exist
- [ ] If any of the above checks fail, address before proceeding with demo

---

This guide enables a developer to set up, run, and demo LeanVibe Agent Hive autonomously for the Medium clone project, with all critical commands, prompts, and quality gates enforced.