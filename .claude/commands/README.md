# Agent Command Protocols – Directory Summary

This directory contains the canonical protocols for agentic workflows. Each protocol maps to a real-world script or system, ensuring reliability and clarity for all agent operations.

| Protocol         | Purpose/Use-case                                 | Canonical Script(s)                        |
|------------------|--------------------------------------------------|--------------------------------------------|
| sleep.md         | Memory consolidation before context reset         | (auto/manual) memory system                |
| wake.md          | Restore knowledge/project state after reset       | (auto/manual) memory system                |
| spawn.md         | Spawn/init new agent with persona/task           | scripts/enhanced_agent_spawner.py          |
| monitor.md       | System/agent health, metrics, debug, optimize    | scripts/monitoring_core.py, monitoring_*    |
| rollback.md      | Emergency rollback to checkpoint                  | state_manager.py                           |
| orchestrate.md   | Orchestrate complex workflows (feature/dev)      | scripts/agent_manager.py, orchestrator      |
| persona.md (DEPRECATED) | Persona switching (now in spawn.md)        | See spawn.md                               |
| debug.md (DEPRECATED)   | Debugging (now in monitor.md)              | See monitor.md                             |
| optimize.md (DEPRECATED)| Optimization (now in monitor.md)           | See monitor.md                             |
| health-check.md (DEPRECATED)| Health check (now in monitor.md)        | See monitor.md                             |

**Quick Start:**
- Use `/sleep` before ending a session or at context limits.
- Use `/wake` after session reset to restore all knowledge and state.
- Use `/spawn` to initialize new agents with specific personas and tasks.
- Use `/monitor` for health, metrics, debugging, and optimization.
- Use `/rollback` for emergency recovery.
- Use `/orchestrate` for complex, multi-agent workflows.

**Deprecated protocols** are retained for reference but point to their new consolidated locations.

---

## CLI Usage Examples

- **/sleep**: Consolidate memory before ending session or at context limits
  ```bash
  /sleep [level]
  # level: normal | critical | emergency (default: critical)
  ```

- **/wake**: Restore knowledge and project state after context reset
  ```bash
  /wake
  # No parameters required
  ```

- **/spawn**: Initialize new agent with persona/task
  ```bash
  /spawn --agent integration-specialist --priority 1.1 --task "api-gateway-repair" --timeline "3-days"
  /spawn --agent developer --persona reviewer --lang python --strict
  # See spawn.md for all persona/task options
  ```

- **/monitor**: System/agent health, metrics, debug, optimize
  ```bash
  /monitor --metrics --real-time
  /monitor --health
  /monitor --debug "error message"
  /monitor --optimize --threshold 95%
  # See monitor.md for all options
  ```

- **/rollback**: Emergency rollback to checkpoint
  ```bash
  /rollback checkpoint-id
  # See rollback.md for details
  ```

- **/orchestrate**: Orchestrate complex workflows (feature/dev)
  ```bash
  /orchestrate --workflow "feature-dev" --validate
  # See orchestrate.md for advanced options
  ```

For detailed usage and examples, see each protocol file.
