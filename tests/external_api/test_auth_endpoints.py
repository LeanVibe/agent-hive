import pytest
from datetime import datetime, timedelta

from external_api.api_gateway import ApiGateway
from external_api.models import ApiGatewayConfig, ApiRequest


class DummySession:
    def __init__(self, user_id: str, access_token: str, refresh_token: str, expires_at: datetime):
        self.user_id = user_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at


@pytest.fixture
def gateway_config():
    return ApiGatewayConfig(
        host="localhost",
        port=8081,
        api_prefix="/api/v1",
        auth_required=False,
        request_timeout=10,
    )


@pytest.fixture
def api_gateway(gateway_config):
    return ApiGateway(gateway_config)


@pytest.mark.asyncio
async def test_auth_login_refresh_logout_introspect_flow(api_gateway: ApiGateway):
    # Monkeypatch auth_service.authenticate_user to return a session
    async def mock_authenticate_user(username: str, password: str, client_ip: str = None, user_agent: str = None):
        return True, "ok", DummySession(
            user_id="user-123",
            access_token="access-abc",
            refresh_token="refresh-xyz",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )

    api_gateway.jwt_service.auth_service.authenticate_user = mock_authenticate_user  # type: ignore

    # 1) Login
    login_req = ApiRequest(
        method="POST",
        path="/api/v1/auth/login",
        headers={"Content-Type": "application/json"},
        query_params={},
        body={"username": "john", "password": "secret"},
        timestamp=datetime.utcnow(),
        request_id="req-login",
        client_ip="127.0.0.1",
    )
    login_resp = await api_gateway.handle_request(login_req)
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.body
    assert "refresh_token" in login_resp.body

    access_token = login_resp.body["access_token"]
    refresh_token = login_resp.body["refresh_token"]

    # Monkeypatch refresh_session for refresh flow
    async def mock_refresh_session(refresh_token: str, client_ip: str):
        return True, "ok", DummySession(
            user_id="user-123",
            access_token="new-access",
            refresh_token="new-refresh",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )

    api_gateway.jwt_service.auth_service.refresh_session = mock_refresh_session  # type: ignore

    # 2) Refresh
    refresh_req = ApiRequest(
        method="POST",
        path="/api/v1/auth/refresh",
        headers={"Content-Type": "application/json"},
        query_params={},
        body={"refresh_token": refresh_token},
        timestamp=datetime.utcnow(),
        request_id="req-refresh",
        client_ip="127.0.0.1",
    )
    refresh_resp = await api_gateway.handle_request(refresh_req)
    assert refresh_resp.status_code == 200
    assert refresh_resp.body["access_token"] == "new-access"
    assert refresh_resp.body["refresh_token"] == "new-refresh"

    # 3) Introspect active token: monkeypatch token_manager.validate_token_secure -> success
    class _ValidateResult:
        def __init__(self, success: bool, user_id: str = None, permissions=None, metadata=None, error: str = None):
            self.success = success
            self.user_id = user_id
            self.permissions = permissions or []
            self.metadata = metadata or {}
            self.error = error

    async def mock_validate_token_secure(token: str, *args, **kwargs):
        return _ValidateResult(success=True, user_id="user-123", permissions=["read"], metadata={})

    api_gateway.jwt_service.token_manager.validate_token_secure = mock_validate_token_secure  # type: ignore

    introspect_req = ApiRequest(
        method="POST",
        path="/api/v1/auth/introspect",
        headers={"Content-Type": "application/json"},
        query_params={},
        body={"token": access_token},
        timestamp=datetime.utcnow(),
        request_id="req-introspect-active",
        client_ip="127.0.0.1",
    )
    introspect_resp = await api_gateway.handle_request(introspect_req)
    assert introspect_resp.status_code == 200
    assert introspect_resp.body.get("active") is True

    # 4) Introspect blacklisted token path: stub redis blacklist
    class _RedisStub:
        def __init__(self, blacklisted):
            self.blacklisted = blacklisted
        def is_jwt_token_blacklisted(self, token: str) -> bool:
            return token in self.blacklisted

    api_gateway.jwt_service.redis_cache_manager = _RedisStub({"bad-token"})  # type: ignore

    introspect_bad_req = ApiRequest(
        method="POST",
        path="/api/v1/auth/introspect",
        headers={"Content-Type": "application/json"},
        query_params={},
        body={"token": "bad-token"},
        timestamp=datetime.utcnow(),
        request_id="req-introspect-bad",
        client_ip="127.0.0.1",
    )
    introspect_bad_resp = await api_gateway.handle_request(introspect_bad_req)
    assert introspect_bad_resp.status_code == 200
    assert introspect_bad_resp.body.get("active") is False

    # 5) Logout (revoke)
    async def mock_revoke_token(token: str, reason: str = "user_logout"):
        return True
    api_gateway.jwt_service.revoke_token = mock_revoke_token  # type: ignore

    logout_req = ApiRequest(
        method="POST",
        path="/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        query_params={},
        body=None,
        timestamp=datetime.utcnow(),
        request_id="req-logout",
        client_ip="127.0.0.1",
    )
    logout_resp = await api_gateway.handle_request(logout_req)
    assert logout_resp.status_code == 200
    assert logout_resp.body.get("message") == "Logout successful"
