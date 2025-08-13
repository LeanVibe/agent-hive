from datetime import datetime

from external_api.api_gateway import ApiGateway
from external_api.models import ApiRequest


async def _ok_handler(request):
    return {"status_code": 200, "body": {"ok": True}}


def _mk_req(path: str, headers: dict) -> ApiRequest:
    return ApiRequest(
        method="GET",
        path=path,
        headers=headers,
        query_params={},
        body=None,
        timestamp=datetime.utcnow(),
        request_id="rid-1",
        client_ip="127.0.0.1",
    )


async def test_traceparent_incoming_is_propagated_and_returned():
    config = {"observability": {"tracing_enabled": True, "service_name": "gw"}}
    gw = ApiGateway(config)
    gw.register_route("/tp", "GET", _ok_handler)

    incoming_trace_id = "0123456789abcdef0123456789abcdef"
    incoming_span_id = "89abcdef01234567"
    incoming_tp = f"00-{incoming_trace_id}-{incoming_span_id}-01"

    req = _mk_req("/api/v1/tp", {"traceparent": incoming_tp})
    res = await gw.handle_request(req)

    assert res.status_code == 200
    # X-Trace-Id should match incoming trace id
    assert res.headers.get("X-Trace-Id") == incoming_trace_id
    # traceparent should be present and contain the same trace id
    tp = res.headers.get("traceparent")
    assert isinstance(tp, str) and tp.startswith(f"00-{incoming_trace_id}-")
    assert len(tp.split("-")) == 4


async def test_traceparent_is_generated_when_missing():
    config = {"observability": {"tracing_enabled": True, "service_name": "gw"}}
    gw = ApiGateway(config)
    gw.register_route("/tp2", "GET", _ok_handler)

    req = _mk_req("/api/v1/tp2", {})
    res = await gw.handle_request(req)

    assert res.status_code == 200
    trace_id = res.headers.get("X-Trace-Id")
    assert isinstance(trace_id, str) and len(trace_id) == 32
    tp = res.headers.get("traceparent")
    assert isinstance(tp, str)
    parts = tp.split("-")
    assert parts[0] == "00"
    assert parts[1] == trace_id
    assert len(parts[2]) == 16
    assert parts[3] in {"00", "01"}
