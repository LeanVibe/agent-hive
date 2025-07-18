# Scripts Directory Index – Agent Hive

This directory contains all automation, orchestration, and monitoring scripts for the LeanVibe Agent Hive. **Canonical scripts** are marked and should be used for all new workflows. Deprecated/legacy scripts are noted with recommended alternatives.

| Script                        | Canonical | Description                                                                                 | Notes/Alternatives                        |
|-------------------------------|-----------|---------------------------------------------------------------------------------------------|-------------------------------------------|
| agent_manager.py              | ✅        | Agent lifecycle: spawn, monitor, manage, resume agents (tmux-based)                         | Use for all agent lifecycle ops           |
| enhanced_agent_spawner.py     |           | Reliable agent initialization, solves spawn/instruction delivery issues                      | Use agent_manager.py instead              |
| pr_manager.py                 | ✅        | PR review, merge, and integration automation (XP/PM/quality gates)                          | Use for all PR review/merge workflows     |
| pr_merge_coordinator.py       | ✅        | PR merge automation and coordination                                                        | Use for merge/post-review workflows       |
| monitor_agents.py             | ✅        | Monitors agent activity, status, and resumption                                             |                                           |
| send_agent_message.py         | ✅        | Agent-to-agent communication (auto-submit)                                                  | Use for all agent messaging               |
| fixed_agent_communication.py  |           | Agent messaging (legacy, for window naming issues)                                          | Use send_agent_message.py                 |
| check_agent_status.py         |           | Check status of a single agent                                                              | Use monitor_agents.py                     |
| check_agent_progress.py       |           | Check progress of agents                                                                    | Use monitor_agents.py                     |
| integration_workflow_manager.py|           | Integration workflow automation (legacy)                                                    | Use agent_manager.py, pr_manager.py       |
| dashboard_integration_micro.py|           | Micro dashboard integration (specialized)                                                   |                                           |
| ...                           |           | ...                                                                                         |                                           |

**Legend:**
- ✅ = Canonical (use for all new workflows)
- (blank) = Legacy, specialized, or superseded

## Usage
- All canonical scripts support `--help` for usage instructions.
- For agent lifecycle: `python agent_manager.py --help`
- For PR review/merge: `python pr_manager.py --help`
- For agent monitoring: `python monitor_agents.py --help`
- For agent messaging: `python send_agent_message.py --help`

## Deprecation Policy
- Deprecated scripts are retained for reference but will be removed after the next major release.
- Always prefer canonical scripts for reliability and support.

---

For protocol mapping, see `.claude/commands/README.md`.
