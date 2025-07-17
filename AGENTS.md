# AGENTS.md — Coding Agent Guidelines

## Build, Lint, and Test Commands
- **Install dependencies:** `pip install -r requirements.txt`
- **Run all tests:** `pytest`
- **Run a single test:** `pytest path/to/test_file.py::test_function`
- **Lint (ruff):** `ruff .`
- **Format (black):** `black .`
- **Sort imports:** `isort . --profile black --line-length 100`
- **Type check:** `mypy .`
- **Pre-commit (all checks):** `pre-commit run --all-files`
- **Test coverage:** `pytest --cov=.claude --cov-report=term-missing`

## Code Style Guidelines
- **Imports:** PEP8 order; use isort with black profile, line length 100.
- **Formatting:** Use black (line length 100).
- **Linting:** Use ruff for static analysis and auto-fixes.
- **Type hints:** Required for all public functions; mypy strict mode.
- **Naming:** snake_case for functions/variables, PascalCase for classes.
- **Error handling:** Use try/except, log errors, avoid bare excepts.
- **Docstrings:** Google style, required for public APIs (pydocstyle, D100/D104 ignored).
- **Pre-commit:** All code must pass pre-commit hooks (format, lint, type, security, doc).
- **Tests:** All in `tests/`, named `test_*.py`, functions/classes prefixed with `test_`.
- **Coverage:** Minimum 80% for `.claude` package.
