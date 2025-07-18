## Quick Start Commands for Personas

```bash
# .claude/commands/persona.md
---
category: system
description: Switch or configure personas
---

Switch to a specific persona or configure persona behavior:

Usage:
- `/persona orchestrator` - Switch to orchestrator role
- `/persona developer --lang python` - Developer focusing on Python
- `/persona reviewer --strict` - Strict code review mode
- `/persona optimizer --focus frontend` - Optimize frontend performance
- `/persona debugger --issue "error message"` - Debug specific issue

Options:
- `--auto` - Automatically select best persona for current task
- `--combine persona1,persona2` - Combine multiple personas
- `--reset` - Return to default persona

The system learns which personas work best for different tasks and can automatically switch when `--auto` is enabled.

$ARGUMENTS
```
