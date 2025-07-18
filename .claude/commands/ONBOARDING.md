# Agent Hive Onboarding Checklist

Welcome to the LeanVibe Agent Hive! This checklist will help you get started quickly and ensure you are using the most reliable workflows and tools.

## 1. Environment Setup
- [ ] Clone the repository
- [ ] Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- [ ] (Optional) Set up pre-commit hooks:
  ```bash
  pre-commit install
  ```

## 2. Core Workflows & Scripts
- [ ] Review the [scripts/README.md](../scripts/README.md) for canonical scripts and usage
- [ ] Use only scripts marked as **Canonical** for new workflows
- [ ] All scripts support `--help` for usage instructions

## 3. Protocols & Commands
- [ ] Review [commands/README.md](README.md) for protocol-to-script mapping and CLI usage
- [ ] Use these protocols for all agentic workflows:
  - `/sleep` – Memory consolidation
  - `/wake` – Memory restoration
  - `/spawn` – Agent initialization (with persona/task)
  - `/monitor` – Health, metrics, debug, optimize
  - `/rollback` – Emergency recovery
  - `/orchestrate` – Complex/multi-agent workflows

## 4. Quality & Testing
- [ ] Run all tests before pushing:
  ```bash
  pytest
  ```
- [ ] Run linting and formatting:
  ```bash
  ruff .
  black .
  isort . --profile black --line-length 100
  mypy .
  ```
- [ ] Run pre-commit checks:
  ```bash
  pre-commit run --all-files
  ```

## 5. Contribution & Coordination
- [ ] Use `/monitor` and `monitor_agents.py` to check agent status and progress
- [ ] Use `/spawn` and `agent_manager.py` for agent lifecycle management
- [ ] Use `/orchestrate` and `agent_manager.py` for complex workflows
- [ ] Use `/rollback` and `state_manager.py` for emergency recovery
- [ ] Use `/sleep` and `/wake` to preserve and restore knowledge across sessions

## 6. Support & Documentation
- [ ] For detailed usage, see each protocol file in `.claude/commands/`
- [ ] For advanced workflows, see `ARCHITECTURE.md` and `AGENTS.md`
- [ ] For troubleshooting, see `TROUBLESHOOTING.md`

---

**You are now ready to contribute and coordinate in the Agent Hive!**
