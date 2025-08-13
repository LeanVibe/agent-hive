# API Gateway: Service Routing and Proxy Examples

Quick examples for registering services, mapping routes, and proxying via the gateway.

- Register a service instance:

```python
from external_api.service_discovery import ServiceInstance

svc = ServiceInstance(
    service_id="users-1",
    service_name="user-service",
    host="localhost",
    port=5001,
    metadata={"version": "1.0.0"},
    health_check_url="http://localhost:5001/health"
)
await gateway.register_service(svc)
```

- Map HTTP path prefix to service name:

```python
gateway.register_service_route("/api/v1/users", "user-service")
```

- Proxy an incoming request to the mapped service:

```python
from external_api.models import ApiRequest

req = ApiRequest(
    method="GET",
    path="/api/v1/users/42",
    headers={"X-API-Key": "test-key"},
    body=None,
    query_params={"expand": "profile"}
)

service_name = gateway._find_service_route(req.path)
if service_name:
    proxied = await gateway.proxy_to_service(req, service_name)
    # proxied is a dict with keys: status_code, headers, body
```

- End-to-end route handling with handler fallback:

```python
@gateway.register_route("/api/v1/health", "GET", handler=async lambda r: {"status_code": 200, "body": {"ok": True}})
```

Notes
- `proxy_to_service` returns a deterministic dict. On errors: `status_code=502`, an `error` object in `body`, and a `headers` field (possibly empty).
- For tests/CI focused on `external_api`, run: `pytest -q tests/external_api`.
