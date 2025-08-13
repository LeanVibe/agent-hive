# External API Focused Tests (Phase 2)

For Phase 2 sprint, limit CI to the `external_api` suite to avoid repo-level coverage gates affecting results (`.claude/*`).

- Run tests:

```bash
pytest -q tests/external_api
```

- Run with coverage on `external_api` only:

```bash
pytest -q tests/external_api --cov=external_api --cov-report=term-missing
```

- Example GitHub Actions job (do not commit unless requested):

```yaml
jobs:
  external-api-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest -q tests/external_api --cov=external_api --cov-report=xml
```
