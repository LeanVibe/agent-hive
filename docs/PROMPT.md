LeanVibe Agent Hive – Handoff Prompt for Next Cursor Agent

Context
- Repo: LeanVibe Agent Hive – multi-agent orchestration with external_api, security, performance, orchestrator shims
- Branch: feature/phase2-epic-planning+gateway-lifecycle
- Goal of Epic 1 (current): Full-repo CI Stabilization & Adapter Shims (test collection passes across repo; import hygiene fixed)
- Status: pytest --collect-only is clean across the entire repo. Import errors fixed via sitecustomize and config shim. Next: continue Phase 2 tasks while maintaining green collection and scoped CI.

What was just completed
- Import hygiene and test collection stabilization:
  - Added sitecustomize.py to enforce project root and .claude on sys.path and ensure local config package wins over any installed package named config
  - Added config/config_loader.py shim mirroring .claude/config/config_loader.py API
  - Hardened tests/conftest.py and tests/security/conftest.py to ensure local package resolution
  - Registered pytest marker security; added .claude/logs to .gitignore with .gitkeep; untracked logs
- Validation: pytest --collect-only now succeeds, listing 1157 tests; no collection errors

Key files touched
- sitecustomize.py
- config/config_loader.py
- tests/conftest.py
- tests/security/conftest.py
- pytest.ini (marker added)
- .gitignore (+ .claude/logs/.gitkeep)
- docs/PLAN.md updated with import/CI stabilization notes

Active constraints
- Keep external_api suites green and fast
- XP full-repo workflow should collect successfully (no ImportError) while we iterate
- Coverage gate in pytest.ini currently targets external_api; do not break it

Your immediate objectives (Epic 2 • Sprint 1)
1) Rotation & jti blacklist (T2.1)
   - Ensure in-memory jti blacklist enforced in SecureTokenManager.validate_token_secure [done]
   - Revoke + blacklist old refresh on session refresh [done]
   - Add tests: old refresh invalid after rotation; JwtIntegrationService.refresh_token fails for invalid refresh
2) Blacklist provider (T2.2)
   - Introduce interface and wire default in-memory + optional Redis provider
   - Add tests to assert blacklisted access token id is rejected
3) Introspection hardening (T2.3)
   - Add issuer/audience checks in JwtIntegrationService.introspect_token when configured; return reason on mismatch
   - Tests for positive/negative iss/aud cases
4) API key lifecycle (start T2.4)
   - Add rotate API (disable old, return new); store hashed value; per-key rate limits and usage metrics
   - Add tests for rotate/revoke/per-key-limits

Non-goals for this pass
- Terraform infrastructure (out of scope)
- Broad architecture docs rewrite (add only surgical notes/examples needed for new features)

Quality and methodology guardrails
- Use small vertical slices: add a focused failing test, implement minimal code to pass, refactor
- Maintain or improve coverage for external_api and security changes
- Keep import hygiene intact (no reintroducing sys.path churn); prefer adapters/shims

Execution plan (pragmatic sequence)
A) Add tests for T2.1 rotation invalidation and invalid refresh
B) Implement blacklist provider abstraction; wire Redis option; write tests
C) Harden introspection (iss/aud); write tests
D) Begin API key rotate/revoke/per-key limits; write tests
E) Run focused security tests and keep repo collection clean

How to validate
- pytest --collect-only must remain clean
- pytest -q tests/external_api should pass locally
- Focused tests you add for exporter/SDK/security should pass

Commits and PRs
- Use descriptive commit messages, eg: “ci(imports): enforce local config resolution with sitecustomize”
- Keep changes scoped; prefer separate commits per vertical slice
- Open PRs against the current feature branch; include short test plan and risks

If blocked
- When imports fail: print sys.path and module __file__ in failing context; check sitecustomize and conftest guards
- When exporter conflicts with tests: preserve old behavior by default; guard new features behind presence checks in routing_config

Reference
- docs/PLAN.md tracks all tasks and statuses; update it when advancing milestones
- external_api/envoy_exporter.py – exporter surface
- external_api/client_generators.py – SDK factory
- security/token_manager.py – JWT/refresh handling
- performance/metrics_collector.py – lifecycle helpers

Good luck. Keep collection green, iterate in vertical slices, and commit frequently with clear messages. 