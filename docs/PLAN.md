# Foundation Epic Phase 2 – Advanced Systems & Security: Execution Plan

Last updated: 2025-08-13 • Owner: Foundation Epic Phase 2 • Scope: external_api, security, performance, orchestrator shims

## Current status
- external_api test suite green and stable locally
- GitHub Actions shows failures driven by global workflows (XP gate) executing full repo tests. Root causes identified and planned for remediation.
- Recent security work: JWT introspection/blacklisting tests added and passing; auth endpoints exempted from pre-auth; shared SecureTokenManager instance across services.
- Orchestrator and state shims under `.claude/*` caused import errors in full-suite runs; compatibility shims introduced, additional adapters planned below.
  - ApiGateway accepts injected `service_discovery` and exposes service route helpers
  - Load balancer metrics include successful/failed counters; circuit-breaker recovery semantics improved
  - Event streaming batch now always exposes `event_count` and `events` even when compressed
  - Auth middleware completed with API key/basic/JWT/OAuth2/signature; rate-limiting applies to failed attempts only
  - Service discovery health checks now compatible with `aiohttp` mocks used in tests
- Remaining global coverage gate fails due to `.claude/*` coverage settings (outside this sprint scope)

## Objectives (next 2 sprints)
- Sprint A: Stabilize full-repo CI by adding missing compatibility adapters, performance decorators, and metrics hooks required by XP workflow tests. Keep external_api green.
- Sprint B: Security & Identity hardening (refresh rotation, Redis blacklist optional, OAuth2 scaffolds), Envoy/xDS export validation, and SDK generation from OpenAPI polishing.

## Deliverables
- Api Gateway
  - Injectible `ServiceDiscovery`, service route table (`register_service_route`, `_find_service_route`, `proxy_to_service`)
  - Accurate health semantics when server not running
  - Request proxying via `aiohttp` respecting timeouts from `ApiGatewayConfig`
- Service Discovery / Registry
  - Health-check behavior handles mocked sessions and timeouts; watcher notifications are safe
  - Registry discovery filters: `include_unhealthy`, `tags` multiple-match semantics
- Load Balancer
  - Metrics parity: `total_requests`, `successful_requests`, `failed_requests`, moving average response time
  - Circuit-breaker: trip on N recent failures; recover after timeout; instance availability changes reflect recovery
- Event Streaming
  - Batch shape stable for consumers regardless of compression; report `event_count`, `stream_name`, `events`
  - Minimal in-memory stores for api-keys/users/tokens; complete method set used by tests
- Envoy/xDS Exporter
  - `external_api/envoy_exporter.py` produces `virtual_host` structures from routing DSL
- SDK Generation from OpenAPI
  - Client generators exposed via `ClientLibraryFactory.generate_*_from_openapi`
- Performance & XP Gate Compatibility
  - `performance_monitor.py` exposes `track_*` decorators used by tests
  - `performance/metrics_collector.py` export and lifecycle adapters
- Orchestrator/State Compatibility
  - `.claude/state/state_manager.py` compatibility shim re-exporting real `state/state_manager.py`
  - `.claude/orchestrator.py` TriggerManager fallback, GitMilestoneManager import stabilized

## Risks / Constraints
- XP workflow executes full test suite; missing adapters in legacy `.claude/*` paths will fail collection. We address via shims and selective delegation to real modules.
- Global coverage gate in pytest.ini targets `.claude/*`; interim mitigation: run scoped workflows (external_api) and keep XP gate non-blocking until full stabilization.
- `terraform/` currently empty; infra remains out-of-scope for now.

## Detailed task list (ready to pick up)

### A. API Gateway routing and discovery integration
1) Ensure `_find_service_route` does longest-prefix match and is resilient to trailing slashes [implemented]
2) `get_service_instance(service_name)` calls service discovery and returns `ServiceInstance` or None [implemented]
3) `proxy_to_service` builds URL by composing service host/port/path/query and returns `{status_code, headers, body}` [implemented], re-verify error shaping for 4xx/5xx
4) Add example wiring in docs/api to show registering routes and service mapping

### B. Service discovery health checks
1) Make `_perform_health_check` work with patched `aiohttp.ClientSession` and both context-managed and awaited responses [implemented]
2) Add short-circuit healthy when `health_check_url` missing [existing]
3) Add unit example doc for mocking `aiohttp`

### C. Load balancer semantics
1) Define `successful_requests`/`failed_requests` counters in `LoadBalancingMetrics` [implemented]
2) Recovery: when `circuit_breaker_open_until` has passed, mark instance available again (degraded/unknown allowed) [implemented]
3) Validate health-weighted selection biases to higher health score [tests pass]

### D. Event streaming stability
1) `_prepare_batch` includes `event_count`, `events` before compression [existing]
2) `_flush_events` wraps compressed payload with visible `event_count` and `events` keys [implemented]
3) Track `batches_sent`, `events_delivered` stats remain correct

### E. Auth middleware completeness
1) Implement in-memory stores for API keys, basic users, JWT/OAuth2 tokens, signing secrets [implemented]
2) `authenticate_request` tries methods in order; failed attempts accrue to rate limiter; success bypasses limiting [implemented]
3) Helpers to create tokens/keys and manage users [implemented]

### F. Integration tests and examples
1) Add docs snippet for: creating `ServiceInstance`s, registering with `ServiceDiscovery`, mapping routes in `ApiGateway`, and proxying
2) Provide example test flow that aligns with `tests/external_api/test_service_discovery_integration.py`

### G. CI/Test coverage strategy (outside immediate code changes)
- Keep `external_api_tests.yml` running the scoped suite to protect gateway stack.
- XP gate: remediate missing imports/decorators to allow collection; if still red, mark non-blocking until all adapters land.

### H. XP Workflow/Full-suite Stabilization (new)
1) Orchestrator imports
   - Provide `.claude/state/state_manager.py` shim that re-exports project `state/state_manager.py` [done]
   - Provide fallback `TriggerManager` minimal API in `.claude/orchestrator.py` when missing [done]
   - Provide import fallback to `.claude/state/git_milestone_manager.py` if `state/git_milestone_manager` missing [todo]
2) State module parity
   - Ensure `state/state_manager.py` exposes `AgentState`, `TaskState`, `SystemState` [done]
   - Align signatures expected by tests (e.g., `should_create_checkpoint(agent_id)` vs optional arg) [review]
3) Performance module decorators
   - Added `track_jwt_authentication`, `track_rbac_authorization`, `track_rate_limiting`, `track_service_discovery`, `track_load_balancing`, `track_api_gateway_request`, `track_end_to_end_request` [done]
   - Implement missing `metrics_collector` lifecycle helpers `start_metrics_collection`, `stop_metrics_collection`, `print_live_dashboard` exports [todo]
4) Security imports
   - Tests import `config.auth_models`, `config.security_config`; both exist under `config/` [verified]
   - Ensure package import works in CI PYTHONPATH; tests already insert project root [verified]

### I. Security & Identity Enhancements (next)
1) JWT refresh rotation hardening with jti tracking; optional Redis blacklist provider behind interface
2) OAuth2 scaffolds for auth code and client credentials; scope→RBAC mapping
3) Introspection endpoint hardening; error shaping parity; audience verification toggles

### J. Envoy/xDS Exporter Enhancements
1) Add header/method expansions into route duplication when methods array present
2) Add weighted clusters support when multiple backends in DSL
3) Unit tests for exporter from sample routing config

### K. Developer Experience
1) docs/api examples for gateway+discovery wiring and Envoy export usage
2) README/architecture notes after stabilization

## Acceptance criteria
- `pytest -q tests/external_api` stays green
- XP workflow collects tests without ImportError; remaining failures, if any, not due to import scaffolding
- `performance` tests consume provided decorators and metrics collector helpers successfully
- Docs updated showing end-to-end flow and Envoy export usage

## Out-of-scope for this sprint (tracked)
- Terraform infra definitions (stubs acceptable)
- Global coverage target across out-of-sprint directories
- Full JWT/RBAC production flows beyond test harness usage
