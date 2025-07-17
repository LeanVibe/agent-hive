---
category: monitoring
# Consolidated Monitoring, Debug, and Optimization Protocol

description: Aggregate metrics, health, debug, and optimize
---

/monitor [--metrics] [--real-time] [--debug "issue"] [--optimize --threshold 95%]

## Usage Examples
- `/monitor --metrics --real-time` - Aggregate metrics and health (default)
- `/monitor --health` or `/monitor --quick` - Basic health check (ping agents, DB, logs)
- `/monitor --debug "error message"` - Debug with trace, evidence, and checkpoint
- `/monitor --optimize --threshold 95%` - Optimize performance, auto-apply if above threshold

## Steps
1. Query state DB for confidence, tasks.
2. Check Git logs for recent commits.
3. Agent health: context usage, stuck detection.
4. Auto-redistribute if unhealthy.
5. Output summary (CLI table).

### Health Check Mode (`--health` or `--quick`)
- Ping agents
- Query DB status
- Check logs for errors
- Report: Healthy if no issues

### Debug Mode (`--debug`)
- Load Debugger persona
- Trace error with evidence (logs/cites)
- Checkpoint before fix
- Propose solution

### Optimize Mode (`--optimize`)
- Load Optimizer
- Benchmark current (cite metrics)
- Suggest improvements with evidence
- If >threshold, auto-apply

$ARGUMENTS

**Note:** This protocol now subsumes the previous `debug.md`, `optimize.md`, and `health-check.md` commands. Use the appropriate options for health, debugging, and optimization.
