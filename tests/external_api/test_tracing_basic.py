import asyncio
from datetime import datetime

from external_api.api_gateway import ApiGateway
from external_api.models import ApiRequest


async def _simple_handler(request):
    return {"status_code": 200, "body": {"ok": True}}


async def test_tracing_header_attached_when_enabled():
    # Configure gateway with tracing enabled (no OpenTelemetry dependency required)
    config = {
        "gateway": {},
        "observability": {"tracing_enabled": True, "service_name": "test-gateway"},
    }
    gw = ApiGateway(config)
    gw.register_route("/trace", "GET", _simple_handler)

    req = ApiRequest(
        method="GET",
        path="/api/v1/trace",
        headers={"Content-Type": "application/json"},
        query_params={},
        body=None,
        timestamp=datetime.utcnow(),
        request_id="trace-123",
        client_ip="127.0.0.1",
    )

    res = await gw.handle_request(req)
    assert res.status_code == 200
    # Minimal contract: response carries a trace id header when tracing is enabled
    assert "X-Trace-Id" in res.headers and isinstance(res.headers["X-Trace-Id"], str)
