import pytest
from datetime import datetime, timedelta
import jwt

from external_api.api_gateway import ApiGateway
from external_api.models import ApiGatewayConfig, ApiRequest


@pytest.fixture
def api_gateway():
    cfg = ApiGatewayConfig(host="localhost", port=8081, api_prefix="/api/v1", auth_required=False)
    return ApiGateway(cfg)


@pytest.mark.asyncio
async def test_refresh_token_rotation_invalidates_old_token(api_gateway: ApiGateway):
    # Stub refresh_session to enforce one-time use refresh tokens
    used = set()

    class _Session:
        def __init__(self, user_id, access_token, refresh_token):
            self.user_id = user_id
            self.access_token = access_token
            self.refresh_token = refresh_token
            self.expires_at = datetime.utcnow() + timedelta(hours=1)

    async def refresh_session(refresh_token: str, client_ip: str):
        if refresh_token in used:
            return False, "refresh_token_used", None
        used.add(refresh_token)
        return True, "ok", _Session("u1", "acc-new", "ref-new")

    api_gateway.jwt_service.auth_service.refresh_session = refresh_session  # type: ignore

    # First refresh succeeds
    req1 = ApiRequest(
        method="POST",
        path="/api/v1/auth/refresh",
        headers={"Content-Type": "application/json"},
        query_params={},
        body={"refresh_token": "ref-old"},
        timestamp=datetime.utcnow(),
        request_id="r1",
        client_ip="127.0.0.1",
    )
    resp1 = await api_gateway.handle_request(req1)
    assert resp1.status_code == 200
    assert resp1.body["access_token"] == "acc-new"
    assert resp1.body["refresh_token"] == "ref-new"

    # Second refresh with old token fails
    req2 = ApiRequest(
        method="POST",
        path="/api/v1/auth/refresh",
        headers={"Content-Type": "application/json"},
        query_params={},
        body={"refresh_token": "ref-old"},
        timestamp=datetime.utcnow(),
        request_id="r2",
        client_ip="127.0.0.1",
    )
    resp2 = await api_gateway.handle_request(req2)
    assert resp2.status_code == 401
    assert "Token refresh failed" in resp2.body["error"]


@pytest.mark.asyncio
async def test_blacklisted_token_blocks_authentication(api_gateway: ApiGateway):
    # Prepare a token with token_id and exp
    payload = {"token_id": "tid-1", "sub": "u1", "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())}
    token = jwt.encode(payload, "secret", algorithm="HS256")

    # Stub redis manager
    class _RedisStub:
        def __init__(self):
            self.blacklisted = set()
        def blacklist_jwt_token(self, token: str, expires_at: datetime):
            self.blacklisted.add(token)
        def is_jwt_token_blacklisted(self, token: str) -> bool:
            return token in self.blacklisted

    api_gateway.jwt_service.redis_cache_manager = _RedisStub()  # type: ignore

    # Revoke the token (adds to blacklist)
    ok = await api_gateway.jwt_service.revoke_token(token, reason="test")
    assert ok is True

    # Now authenticate a request with this token
    req = ApiRequest(
        method="GET",
        path="/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"},
        query_params={},
        body=None,
        timestamp=datetime.utcnow(),
        request_id="r3",
        client_ip="127.0.0.1",
    )
    success, meta, error_resp = await api_gateway.jwt_service.authenticate_request(req)
    assert success is False
    assert error_resp is not None and error_resp.status_code == 401


@pytest.mark.asyncio
async def test_api_key_issue_rotate_revoke_analytics(api_gateway: ApiGateway):
    # Issue
    issue_req = ApiRequest(
        method="POST",
        path="/api/v1/keys",
        headers={"Content-Type": "application/json"},
        query_params={},
        body={"owner": "svc", "scopes": ["read"]},
        timestamp=datetime.utcnow(),
        request_id="k1",
        client_ip="127.0.0.1",
    )
    issue_resp = await api_gateway.handle_request(issue_req)
    assert issue_resp.status_code in (200, 201)
    api_key = issue_resp.body["api_key"]

    # Rotate
    rotate_req = ApiRequest(
        method="POST",
        path="/api/v1/keys/rotate",
        headers={"Content-Type": "application/json"},
        query_params={},
        body={"api_key": api_key},
        timestamp=datetime.utcnow(),
        request_id="k2",
        client_ip="127.0.0.1",
    )
    rotate_resp = await api_gateway.handle_request(rotate_req)
    assert rotate_resp.status_code == 200
    new_key = rotate_resp.body["new_api_key"]
    assert new_key != api_key

    # Analytics
    analytics_req = ApiRequest(
        method="GET",
        path="/api/v1/keys/analytics",
        headers={},
        query_params={},
        body=None,
        timestamp=datetime.utcnow(),
        request_id="k3",
        client_ip="127.0.0.1",
    )
    analytics_resp = await api_gateway.handle_request(analytics_req)
    assert analytics_resp.status_code == 200

    # Revoke
    revoke_req = ApiRequest(
        method="POST",
        path="/api/v1/keys/revoke",
        headers={"Content-Type": "application/json"},
        query_params={},
        body={"api_key": new_key},
        timestamp=datetime.utcnow(),
        request_id="k4",
        client_ip="127.0.0.1",
    )
    revoke_resp = await api_gateway.handle_request(revoke_req)
    assert revoke_resp.status_code == 200
