# LeanVibe Agent Hive — Phase 2 Execution Plan (4 Epics)

Last updated: 2025-08-12 | Owner: Core Maintainers | Confidence: High

## Objectives
- Maintain Phase 1 quality gates while delivering Phase 2 advanced capabilities.
- Ship production-grade external integration, security, observability, and coordination UX.

## Epic 1: External API & Service Mesh Hardening
- Goal: Lock down and productionize the API gateway + service discovery + registry stack.
- Deliverables:
  - API Gateway runtime lifecycle for CLI control (start/stop/status), health + metrics. [Implemented]
  - Flexible route registration API for CLI compatibility. [Implemented]
  - Circuit breaker, load balancer, registry stats endpoints.
  - Service discovery routing smoke tests and docs.
- Tasks (Week 1-2):
  - Gateway lifecycle + routing
    - Ensure `start_server`, `stop_server`, `health_check`, `get_gateway_info` return consistent structures
    - Make `register_route` accept `(path, handler, methods)` and `(path, method, handler)` (done)
    - Add `_find_handler` and simple `handle_request` with timeout, CORS, and basic API-key support (done)
  - Discovery/registry/circuit breaker/load balancer
    - Add integration tests for discovery, registry stats, and circuit-breaker trips
    - Simulate two service instances and assert load balancer selection
  - API surface consistency and examples
    - Provide sample `/api/v1/services` and `/api/v1/auth/*` flows with smoke
  - Docs parity
    - Verify guides/api-gateway-guide.md and DEPLOYMENT.md reflect reality
  - Acceptance
    - CLI `gateway --action start|status|stop` shows `server_running`, `registered_routes`, <200ms p95
- Success metrics:
  - <200ms gateway health endpoint p95, <1% error rate during smoke tests.

## Epic 2: Security & Authentication Enhancements
- Goal: Consolidate and validate security subsystems for production.
- Deliverables:
  - JWT/RBAC flow validations through gateway endpoints.
  - Audit logging roll-up, summarized dashboards.
  - Pre-commit/CI checks ensure critical docs present and current.
- Tasks (Week 2-3):
  - JWT/RBAC coherency
    - Validate protected/public paths; add tests for valid/expired/invalid/revoked tokens
    - Verify permission gating on `agents` and `tasks` endpoints
  - Rate limiting
    - Ensure 429 includes retry headers; surface rate-limit stats in metrics
  - Audit + dashboard
    - Use `audit_logger` roll-ups; render to `security_dashboard`
  - Import shadowing
    - Resolve `.claude/config` name collision with `config/` (namespace or rename)
  - Pen-test checklist & script
    - Add OWASP ZAP quick-run and verify zero critical findings in smoke
  - Acceptance
    - 100% auth path test coverage; audit roll-up visible; 0 critical findings
- Success metrics:
  - 100% auth paths covered by tests; 0 critical findings in quick scan.

## Epic 3: Real-Time Observability
- Goal: Ship end-to-end Hooks -> Stream -> Dashboard visibility.
- Deliverables:
  - `observability/hook_manager.py` already implements core. Verify start/stop from CLI/dash.
  - SSE/WS live stream with lightweight client sample.
  - Docs and a 2-minute verification script.
- Tasks (Week 3-4):
  - CLI glue
    - Add `observability` command to start/stop/status (done)
    - Add optional demo emitter to generate events
  - Client view
    - Minimal CLI tail or simple dashboard client
  - Persistence and metrics
    - Keep small rolling event history; expose counters in `/metrics`
  - Docs
    - Quick start and verification script
  - Acceptance
    - <100ms fan-out to WS/SSE; stable under 500 events/min locally
- Success metrics:
  - <100ms event fan-out to local WS, stable under 500 events/min.

## Epic 4: Persona-driven Coordination UX
- Goal: Expose persona selection in CLI and coordinator flows.
- Deliverables:
  - Leverage `personas/persona_manager.py` to pick personas based on capabilities.
  - CLI flags for persona and capability hints in `spawn`/`review` flows.
  - Minimal docs and example.
- Tasks (Week 4-5):
  - CLI flags (spawn/review)
    - Add `--persona` and `--capabilities` (done)
    - Resolve persona with `persona_manager` and print selection and compression stats
  - Coordinator metadata (minimal)
    - Plumb persona metadata into task context (no behavior change)
  - Docs
    - Update CLI reference with examples
  - Acceptance
    - Deterministic persona chosen for provided capabilities; smoke test output validated
- Success metrics:
  - Persona chosen deterministically for given capabilities; smoke test passing.

## Cross-cutting
- Docs parity: ensure `README.md`, `docs/CLI_COMMANDS*.md`, gateway and security guides align.
- Tests: green run locally; CI readiness.
- Performance SLOs: Gateway p95 <200ms; Observability fan-out <100ms; <1% error-rate smoke
- CI: slim matrix for external_api/security/observability; no long-lived processes

## Immediate Next Work (this branch)
- Implement gateway lifecycle + route registration compatibility. [Done]
- Add persona flags in CLI and `observability` command. [Done]
- Add targeted tests next commit.
- Update docs with plan and next steps. [Done]

