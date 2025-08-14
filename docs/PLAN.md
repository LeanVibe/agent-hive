# Foundation Epic Phase 2 – Advanced Systems & Security: Execution Plan

Last updated: 2025-08-13 • Owner: Foundation Epic Phase 2 • Scope: external_api, security, performance, orchestrator shims

## Current status
- external_api test suite green and stable locally
- GitHub Actions shows failures driven by global workflows (XP gate) executing full repo tests. Root causes identified and planned for remediation.
- Recent security work: JWT introspection/blacklisting tests added and passing; auth endpoints exempted from pre-auth; shared SecureTokenManager instance across services.
- Orchestrator and state shims under `.claude/*` caused import errors in full-suite runs; compatibility shims introduced, additional adapters planned below.
  - Full repo test collection now succeeds after adding `sitecustomize.py`, enforcing local `config` package, and adding `config/config_loader.py` shim.
  - `.claude/logs/` added to `.gitignore` with `.gitkeep`; tracked logs removed.
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
   - Implement missing `metrics_collector` lifecycle helpers `start_metrics_collection`, `stop_metrics_collection`, `print_live_dashboard` exports [done]
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

---

# Next 4 Epics – Pragmatic Roadmap (80/20 focus)

All epics follow the same rules: prioritize must-haves, add tests first, ship vertical slices, keep repo test collection clean.

## Epic 2 – Security & Identity Hardening (Phase 2 core)

Objectives
- Production-grade token and key lifecycle; RBAC consistency; tenant isolation hooks

Must-haves
- JWT refresh rotation with jti tracking and invalidation
- Blacklist provider interface with in-memory default; optional Redis provider (behind feature flag)
- Introspection endpoint hardening (issuer/audience/expiry/permissions validation); error shaping parity
- API key lifecycle: issue/rotate/revoke; hash at rest; per-key rate limits; minimal analytics (usage count, last used)
- Scope→RBAC mapping utilities; permission checks centralized
- Tenant propagation via `X-Tenant-ID`; per-tenant rate-limit quotas (config-driven)

Tests
- Extend `tests/security/test_jwt_auth.py` and `test_auth_security_integration.py` for refresh rotation, introspection, and revocation
- Add focused tests for API key rotation/revocation and per-key limits
- Add tenant header propagation and quota checks in gateway middleware tests

Deliverables
- `security/token_manager.py`: jti store and rotation semantics
- `external_api/auth_middleware.py`: tenant header handling; introspection checks
- `security/api_key_manager.py`: rotate/revoke APIs; hashed storage
- Config toggles in `config/security_config.py`

Acceptance
- All security tests pass; new tests added for rotation/introspection/keys/tenant quotas

Non-goals
- Full OAuth2 auth code + PKCE (moved to next epic)

Milestone slices
1) jti + refresh rotation + tests
2) blacklist provider interface + in-memory implementation + tests
3) introspection hardening + tests
4) API key rotation/revocation + per-key limits + tests
5) tenant header propagation + quota checks + tests

Detailed Sprint Plan (Epic 2 • Sprint 1)
- Scope: Complete 1–3, start 4 (rotation, blacklist, introspection)

Tasks
- T2.1 Rotation/jti
  - Add in-memory jti blacklist and enforce in `SecureTokenManager.validate_token_secure` [done]
  - Revoke + blacklist old refresh on session refresh in `AuthenticationService.refresh_session` [done]
  - Add unit/integration tests:
    - Extend `tests/security/test_jwt_auth.py::TestTokenRefresh::test_successful_token_refresh` to assert old refresh is invalid
    - Add test for `JwtIntegrationService.refresh_token` failure on invalid refresh
- T2.2 Blacklist provider
  - Define `BlacklistProvider` proto with `blacklist(token|id, ttl)`/`is_blacklisted(token|id)`
  - Wire: default in-memory provider; optional Redis-backed (existing redis_cache_integration)
  - Tests: simulate blacklisting access token id; validation must fail
- T2.3 Introspection hardening
  - In `JwtIntegrationService.introspect_token` add `iss`/`aud` checks when provided in config; return reason on mismatch
  - Ensure signature verification path respects algorithm from config
  - Tests: positive/negative cases for issuer/audience
- T2.4 API keys (begin)
  - Add rotate API: returns new key, disables old; persist hashed value only
  - Per-key rate limit (in-memory counters) and usage metrics (count, last_used)
  - Tests in `tests/security` for rotate, revoke, per-key limit

Deliverables & Exit
- Tests added and green locally for T2.1–T2.3; coverage maintained for touched code
- Feature flags documented in config

## Epic 3 – Mesh & Observability (Envoy exporter + tracing)

Objectives
- Strengthen Envoy/xDS export; consistent tracing and metrics across gateway/discovery/lb

Must-haves
- Envoy exporter enhancements: per-method route duplication; weighted clusters for multiple backends; retries/timeouts mapping; headers match parity
- Golden tests for exporter based on sample routing DSL
- End-to-end tracing: ensure traceparent propagation already implemented is covered; add spans in service discovery and load balancer critical paths
- Minimal metrics: expose Prometheus-style endpoint for gateway (if already present, extend with key counters)

Tests
- Add/extend `tests/external_api/test_envoy_exporter.py` with golden cases (methods, weights, retries)
- Extend tracing tests (`tests/external_api/test_traceparent_propagation.py`, `test_tracing_basic.py`) to include discovery/lb spans assertions (mocked)

Deliverables
- `external_api/envoy_exporter.py` upgrades
- Tracing hooks in `external_api/service_discovery.py`, `external_api/load_balancer.py`
- Optional lightweight `/metrics` JSON/Prometheus mapping in `external_api/monitoring_system.py`

Acceptance
- Exporter tests green; tracing tests extended and passing

Non-goals
- Full dynamic xDS control plane; stick to static export for now

Milestone slices
1) Per-method route split + tests
2) Weighted clusters + tests
3) Retry/timeout/header mapping + tests
4) Tracing spans in discovery/lb + tests

## Epic 4 – Developer Experience & SDKs

Objectives
- Faster integration for users: OpenAPI→routes and SDKs that are practically useful

Must-haves
- Minimal operation parsing from OpenAPI to generate per-verb client methods (Python/JS)
- CLI or function to write generated clients to disk under `clients/{lang}/{service}`
- Improve docs and examples to wire gateway+discovery and export SDKs
- CI for SDK generation smoke tests

Tests
- Add unit tests for SDK factory that assert method names and basic request composition per path/verb

Deliverables
- `external_api/client_generators.py`: extend `generate_*_from_openapi`
- Small CLI entry or helper in `cli.py`
- Docs samples under `docs/`

Acceptance
- SDK unit tests pass; example generation outputs expected files

Non-goals
- Full schema-driven models; keep payloads typed loosely for now

Milestone slices
1) Parse operations → in-memory client methods + tests
2) Emit to disk + simple importable package structure + tests
3) Docs/examples + CI smoke

## Epic 5 – Production Readiness & Reliability

Objectives
- Harden gateway and services for production basics: limits, headers, graceful lifecycle, and packaging

Must-haves
- Request size/time limits, HSTS and security headers (verify in middleware)
- Backpressure and graceful shutdown hooks exposed in gateway
- Health/readiness endpoints consistency across gateway/discovery
- Build pipeline: reproducible Docker image, GH Actions build workflow, release artifact

Tests
- Extend existing webhook/gateway tests for payload limits/timeouts
- Add health/readiness endpoint tests

Deliverables
- `external_api/api_gateway.py` and middleware: limits/headers/shutdown
- Dockerfile tweaks if needed; GH Actions build workflow(s)

Acceptance
- New tests pass; image builds in CI

Non-goals
- Full Terraform/Helm stack (documented stubs only if required)
