---
category: orchestration
description: Orchestrate a workflow with validation and XP practices
---

**Canonical script:** scripts/agent_manager.py, orchestrator

/orchestrate --workflow "feature-dev" --validate

1. Analyze requirements with evidence (cite metrics/docs).
2. Estimate complexity for adaptive depth (simple: think, complex: ultrathink).
3. Compress prompt if >10k tokens.
4. Distribute to agents via capabilities.
5. Monitor progress with auto-checkpoints.
6. Validate outputs via Gemini.

**Note:** For health checks, debugging, and optimization, use `/monitor` with the appropriate options.

$ARGUMENTS

