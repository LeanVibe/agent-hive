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

Your immediate objectives (pick up from here)
1) Finalize XP Workflow Stabilization (Docs task H in docs/PLAN.md)
   - Implement import fallback to .claude/state/git_milestone_manager.py if state/git_milestone_manager is missing
   - Re-validate pytest --collect-only and run a light subset to ensure no regressions
2) Performance lifecycle helpers (confirm done)
   - performance/metrics_collector.py must export: start_metrics_collection, stop_metrics_collection, print_live_dashboard; verify presence and import usage in tests
3) Envoy/xDS Exporter enhancements (Docs task J)
   - Add method-aware route duplication when match.methods is an array (create one route per method)
   - Add weighted clusters when multiple backends provided
   - Add unit tests under tests/external_api/test_envoy_exporter.py (or extend existing)
4) SDK generation from OpenAPI
   - Extend ClientLibraryFactory.generate_*_from_openapi to parse operations minimally and expose one representative method per path/verb to increase utility; add focused tests
5) Security & Identity (Docs task I)
   - JWT refresh rotation hardening with jti tracking; keep in-memory provider as default; make Redis provider pluggable but optional
   - Add introspection hardening and audience verification toggles
   - Keep tests passing; write or extend targeted tests in tests/security

Non-goals for this pass
- Terraform infrastructure (out of scope)
- Broad architecture docs rewrite (add only surgical notes/examples needed for new features)

Quality and methodology guardrails
- Use small vertical slices: add a focused failing test, implement minimal code to pass, refactor
- Maintain or improve coverage for external_api and security changes
- Keep import hygiene intact (no reintroducing sys.path churn); prefer adapters/shims

Execution plan (pragmatic sequence)
A) XP import adapter: implement .claude/state/git_milestone_manager.py fallback import in .claude/orchestrator.py if necessary; verify collection
B) Envoy exporter: implement method split + weighted clusters; add unit tests; keep the function export_envoy_virtual_host backwards compatible
C) Client SDKs: minimal endpoint method generation (e.g., GET returns fetch wrapper, POST returns post wrapper) with simple naming convention; tests
D) Security: implement jti rotation tracking in token manager; add introspection checks; update tests
E) Run external_api tests and targeted security tests locally; ensure pytest -q tests/external_api passes; ensure pytest --collect-only remains clean

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