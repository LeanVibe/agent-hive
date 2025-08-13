You are taking over Phase 2 sprint work for LeanVibe Agent Hive focusing on the external_api stack (API Gateway, Service Discovery, Registry, Load Balancer, Event Streaming, Auth Middleware). Continue from the current branch `feature/phase2-epic-planning+gateway-lifecycle`.
Title: Continue Foundation Epic Phase 2 – Stabilize Full CI and Advance Security/Envoy

Context
- Repo: leanvibe/agent-hive
- Branch: feature/phase2-epic-planning+gateway-lifecycle
- Goal: Keep external_api green and stabilize full GitHub Actions XP workflow by fixing test collection/import issues and providing missing adapters. Then advance Security (JWT/OAuth2) and Envoy exporter features.

What’s already done
- external_api suite passes locally; CI workflow .github/workflows/external_api_tests.yml runs it.
- Envoy exporter module created: external_api/envoy_exporter.py
- Client SDK generation from OpenAPI added in external_api/client_generators.py
- JWT introspection/blacklisting tests created and passing; auth endpoints exempted from pre-auth; shared SecureTokenManager across services.
- Performance monitor exposes decorators track_* now (performance_monitor.py), used by performance tests.
- Orchestrator/state compatibility: .claude/state/state_manager.py shim re-exports real state/state_manager.py; .claude/orchestrator.py has TriggerManager fallback.
- PLAN updated with next steps (docs/PLAN.md).

Primary problems to fix next (CI blockers)
1) Orchestrator imports during full-suite tests
   - tests import from .claude/orchestrator.py which expects state/trigger/git managers under state/.
   - We added shim for state_manager and TriggerManager fallback, but imports for state.git_milestone_manager still fail.

2) Performance tests expect helpers from performance/metrics_collector.py
   - tests import start_metrics_collection, stop_metrics_collection, print_live_dashboard, and a global metrics_collector.
   - File defines metrics_collector = None but does not export lifecycle helpers.

3) Ensure security imports resolve in CI
   - config/auth_models.py and config/security_config.py exist; ensure package works without PYTHONPATH issues. Tests already insert project root; no changes expected.

Deliverables for you
- Implement the missing shims/exports and re-run full tests locally.
- Keep changes minimal, additive, and safe; do not refactor unrelated code.

Detailed tasks
Task A: Orchestrator shims
- In .claude/orchestrator.py import, add safe fallback for GitMilestoneManager:
  - Try import from state.git_milestone_manager; on ImportError, import from .claude/state/git_milestone_manager.
- Verify LeanVibeOrchestrator.__init__ matches tests’ usage. Do not change public API.

Task B: Metrics collector lifecycle exports
- In performance/metrics_collector.py implement and export:
  - metrics_collector: a singleton initialized on-demand with performance_monitor.
  - async def start_metrics_collection(): instantiate if needed and await start().
  - async def stop_metrics_collection(): await stop() if started.
  - def print_live_dashboard(hours: int = 1): produce console output using monitor.get_performance_summary and/or collector dashboard snapshot.
- Ensure these names match tests/performance/test_system_performance.py imports.

Task C: State manager parity check
- Confirm state/state_manager.py exposes AgentState, TaskState, SystemState (it does) and signatures used by tests: get_next_priority_task() (no args) and should_create_checkpoint(agent_id: str) are present; adjust if needed.

Task D: Envoy exporter improvements (after CI green)
- Add support for multiple HTTP methods by duplicating routes with header match.
- Add weighted backend clusters when DSL provides multiple backends with weight.
- Include minimal unit tests for envoy_exporter using a sample routing config.

Task E: Security enhancements (Epic Phase 2)
- JWT refresh rotation and jti tracking; optional Redis-backed blacklist provider behind clean interface with in-memory default.
- OAuth2 scaffolds: auth code and client credentials minimal flows; scope→RBAC mapping and state/nonce checks.
- Introspection hardening: audience verification toggle; consistent 200 with active:false when failing.

Task F: Documentation
- Add docs/api examples: gateway+discovery wiring and Envoy export usage.
- Update docs/PLAN.md upon completion of each logical group.

Quality gates
- Keep external_api tests passing: pytest -q tests/external_api
- Full-suite collection must not error; remaining failures should not be due to imports.
- Prefer surgical changes; avoid changing test interfaces.

How to run
- Scoped: pytest -q tests/external_api
- Full: pytest -q
- CI: gh run list and gh run view to inspect workflow logs.

Commit and branch
- Continue on feature/phase2-epic-planning+gateway-lifecycle
- Group coherent changes; reference “XP gate stabilization” or “Epic 2 security” in commit titles.

Checklist
- [ ] Add GitMilestoneManager import fallback in .claude/orchestrator.py
- [ ] Add lifecycle helpers to performance/metrics_collector.py and wire singleton
- [ ] Verify state signatures; adjust if tests require
- [ ] Re-run full tests locally; fix any remaining import or name errors
- [ ] Enhance Envoy exporter (methods, weighted clusters); add unit tests
- [ ] Start JWT refresh+jti + optional Redis provider scaffolding
- [ ] Update docs/PLAN.md with progress
- [ ] Commit and push when a logical epic slice completes

Notes
- Do not alter pytest.ini global coverage gates yet; focus on adapters to pass collection.
- Keep security changes behind interfaces so in-memory defaults work without Redis.

Context you must know (already implemented/fixed):
- ApiGateway
  - Accepts injected `service_discovery` in __init__(config, service_discovery)
  - Service-route helpers: `register_service_route(path_prefix, service_name)`, `unregister_service_route`, `_find_service_route(path)`, `get_service_instance(name)`, and `proxy_to_service(request, service_name)` (aiohttp-based)
  - `health_check()` reports unhealthy when server not running
- ServiceDiscovery
  - Health check `_perform_health_check` works with aiohttp and also with the AsyncMock patterns in tests (supports awaited response and context-managed forms)
- Load Balancer
  - `LoadBalancingMetrics` has `successful_requests`, `failed_requests`; circuit breaker opens after N recent failures and auto-recovers after timeout; unknown instances considered available after recovery
- Event Streaming
  - When compressed, `_flush_events` wraps with visible `event_count` and `events` fields for consumers
- Auth Middleware
  - API key/basic/JWT/OAuth2/signature supported; in-memory stores and helpers exist; rate limiting applies only to failed attempts

What still blocks a full green run:
- The repo-level coverage gate in pytest.ini measures `.claude/*` and fails the job even when external_api passes. For this sprint we limit scope to external_api tests; CI should use a job that runs `pytest -q tests/external_api` and/or a coverage source override for this job.

Your goals
1) Stabilize and harden external_api behaviors per docs/PLAN.md and add missing developer examples and docstrings.
2) Provide small integration examples and docs for registering services, mapping routes, and proxying via gateway.
3) Add minimal CI job files or notes that run external_api tests and do not fail due to .claude coverage (do not change global coverage policy unless explicitly asked; prefer job-specific coverage source override).
4) Keep making targeted, minimal edits; do not refactor unrelated code.

High-level tasks (do these next)
- API Gateway
  - Re-check `proxy_to_service` error shaping: ensure when exceptions occur it returns a deterministic `{status_code: 502, body: {error, details}}` and headers field exists (possibly empty dict) for consistency.
  - Add examples under docs/api: how to register service routes and proxy a request (simple snippet).
- Service Discovery
  - Add unit-level utility for mocking aiohttp health checks (docs comment or small test helper under tests/external_api if allowed).
  - Ensure `get_healthy_instance` falls back correctly when only STARTING instances exist (expectations currently satisfied, but add a brief docstring and comment).
- Load Balancer
  - Verify legibility: add concise docstrings and type hints where missing in public APIs; avoid altering behavior.
  - Consider exposing a method to manually mark instance health for demos (optional; do not break tests).
- Event Streaming
  - Confirm compression and wrapping update `events_delivered` counters appropriately; adjust if needed.
- Auth Middleware
  - Add small docstrings describing method behavior; add note on failure-count-based rate-limiting.

Testing/Validation
- Run: `pytest -q tests/external_api` locally; resolve any regressions introduced by doc/typing edits.
- Do not try to make repo-wide coverage pass. Instead, prepare a CI job definition or a dev README snippet showing how to run the focused suite and measure coverage for external_api only (e.g., `--cov=external_api`).

Guardrails
- Do not start long-lived processes.
- Do not modify git config.
- Prefer ApplyPatch/Write tools for changes; always read files before editing.
- Keep messages concise for the user; code verbose and clear.

Output requirements for this session
- Update docs: `docs/PLAN.md` (already updated) and add `docs/api/gateway_service_routing_examples.md` with quick samples.
- If you add any new example files under docs, keep them minimal and directly runnable (pseudo or brief code ok).
- If you choose to add a CI snippet, place it under `docs/DEVELOPMENT.md` section or a `docs/ci/external_api_tests.md` note rather than committing CI config unless requested.

Reference commands
- Focused tests: `pytest -q tests/external_api`
- Selective tests while iterating:
  - `pytest -q tests/external_api/test_service_discovery_integration.py::TestServiceDiscoveryIntegration::test_api_gateway_service_proxying`
  - `pytest -q tests/external_api/test_event_streaming.py::TestEventStreaming::test_flush_events_to_consumers`

Definition of done (for handoff)
- External API suite green locally
- Docs with concrete example snippets for service registration and gateway proxying
- Clear note for CI about scoping coverage to external_api for this phase
