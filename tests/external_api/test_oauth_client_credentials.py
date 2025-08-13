import pytest
from datetime import datetime

from external_api.api_gateway import ApiGateway
from external_api.models import ApiRequest


@pytest.fixture
def api_gateway_with_client():
    cfg = {
        "host": "localhost",
        "port": 8081,
        "api_prefix": "/api/v1",
        "auth_required": False,
        # minimal oauth client registry for tests
        "oauth_clients": {
            "client-1": {"secret": "s3cr3t", "permissions": ["read"], "scopes": ["read"]}
        },
        # ensure deterministic token algo
        "jwt_secret": "secret",
        "jwt_algorithm": "HS256",
    }
    return ApiGateway(cfg)


@pytest.mark.asyncio
async def test_client_credentials_success(api_gateway_with_client: ApiGateway):
    req = ApiRequest(
        method="POST",
        path="/api/v1/auth/token",
        headers={"Content-Type": "application/json"},
        query_params={},
        body={
            "grant_type": "client_credentials",
            "client_id": "client-1",
            "client_secret": "s3cr3t",
            "scope": "read"
        },
        timestamp=datetime.utcnow(),
        request_id="oauth1",
        client_ip="127.0.0.1",
    )
    resp = await api_gateway_with_client.handle_request(req)
    assert resp.status_code == 200
    assert resp.body.get("token_type") == "bearer"
    assert isinstance(resp.body.get("access_token"), str) and len(resp.body.get("access_token")) > 10
    assert resp.body.get("scope") == "read"


@pytest.mark.asyncio
async def test_client_credentials_invalid_secret(api_gateway_with_client: ApiGateway):
    req = ApiRequest(
        method="POST",
        path="/api/v1/auth/token",
        headers={"Content-Type": "application/json"},
        query_params={},
        body={
            "grant_type": "client_credentials",
            "client_id": "client-1",
            "client_secret": "wrong",
        },
        timestamp=datetime.utcnow(),
        request_id="oauth2",
        client_ip="127.0.0.1",
    )
    resp = await api_gateway_with_client.handle_request(req)
    assert resp.status_code == 401
    assert "invalid_client" in resp.body.get("error", "")
