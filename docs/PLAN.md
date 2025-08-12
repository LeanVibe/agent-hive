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
- Tasks:
  - Add gateway health/metrics JSON to CLI status output.
  - Expand tests: gateway lifecycle, route registration, health/metrics shape.
  - Docs: guides/api-gateway-guide.md verify code parity.
  - Add example service registration in `docs/guides/deployment.md`.
- Success metrics:
  - <200ms gateway health endpoint p95, <1% error rate during smoke tests.

## Epic 2: Security & Authentication Enhancements
- Goal: Consolidate and validate security subsystems for production.
- Deliverables:
  - JWT/RBAC flow validations through gateway endpoints.
  - Audit logging roll-up, summarized dashboards.
  - Pre-commit/CI checks ensure critical docs present and current.
- Tasks:
  - Add integration tests through `external_api` auth endpoints using `tests/external_api` fixtures.
  - Wire `security/security_manager.py` summaries into dashboard surface.
  - Ensure README/test counts reflect reality; align with hooks expectations.
  - Pen-test checklist doc; add quick OWASP ZAP how-to.
- Success metrics:
  - 100% auth paths covered by tests; 0 critical findings in quick scan.

## Epic 3: Real-Time Observability
- Goal: Ship end-to-end Hooks -> Stream -> Dashboard visibility.
- Deliverables:
  - `observability/hook_manager.py` already implements core. Verify start/stop from CLI/dash.
  - SSE/WS live stream with lightweight client sample.
  - Docs and a 2-minute verification script.
- Tasks:
  - Add CLI glue: simple test that generates events and prints received counts.
  - Write docs/README_MONITORING.md cross-link and quick start.
  - Tests for event serialization and broadcast.
- Success metrics:
  - <100ms event fan-out to local WS, stable under 500 events/min.

## Epic 4: Persona-driven Coordination UX
- Goal: Expose persona selection in CLI and coordinator flows.
- Deliverables:
  - Leverage `personas/persona_manager.py` to pick personas based on capabilities.
  - CLI flags for persona and capability hints in `spawn`/`review` flows.
  - Minimal docs and example.
- Tasks:
  - Add `--persona` and `--capabilities` flags; print resolved persona.
  - Unit test persona selection + context compression stats.
  - Doc section in CLI reference.
- Success metrics:
  - Persona chosen deterministically for given capabilities; smoke test passing.

## Cross-cutting
- Docs parity: ensure `README.md`, `docs/CLI_COMMANDS*.md`, gateway and security guides align.
- Tests: green run locally; CI readiness.

## Immediate Next Work (this branch)
- Implement Epic 1 minimal code: gateway lifecycle + route registration compatibility. [Done]
- Add targeted tests next commit.
- Update docs with plan and next steps. [Done]

