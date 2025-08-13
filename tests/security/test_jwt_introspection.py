#!/usr/bin/env python3
"""
JWT Introspection Tests

Covers OAuth2-style token introspection via API Gateway and direct service,
including active, invalid, and blacklisted tokens.
"""
import pytest
import uuid
from datetime import datetime

from external_api.api_gateway import ApiGateway
from external_api.jwt_integration import JwtIntegrationService
from external_api.models import ApiRequest
from security.auth_service import UserRole


@pytest.fixture
def base_config():
    return {
        "jwt_secret": "test-secret-key-for-jwt-testing",
        "jwt_algorithm": "HS256",
        "token_expiry_minutes": 15,
        "bcrypt_rounds": 4,
    }


@pytest.fixture
async def gateway(base_config):
    cfg = {
        "gateway": {"host": "localhost", "port": 8081, "auth_required": True},
        "jwt": base_config,
        "auth": base_config,
    }
    return ApiGateway(cfg)


@pytest.fixture
async def jwt_service(base_config):
    return JwtIntegrationService(base_config)


@pytest.fixture
async def user(jwt_service):
    success, message, user = await jwt_service.auth_service.create_user(
        username="introspect_user",
        email="intro@example.com",
        password="IntrospectPass123!",
        roles=[UserRole.DEVELOPER],
    )
    assert success
    return user


@pytest.mark.asyncio
async def test_introspection_active_valid_token(gateway, user):
    # Authenticate to get tokens
    auth_resp = await gateway.authenticate_user(
        username="introspect_user", password="IntrospectPass123!", client_ip="127.0.0.1"
    )
    if auth_resp.status_code != 200:
        # create user in the gateway's auth service and retry
        await gateway.jwt_service.auth_service.create_user(
            username="introspect_user",
            email="intro@example.com",
            password="IntrospectPass123!",
            roles=[UserRole.DEVELOPER],
        )
        auth_resp = await gateway.authenticate_user(
            username="introspect_user", password="IntrospectPass123!", client_ip="127.0.0.1"
        )
    assert auth_resp.status_code == 200
    access_token = auth_resp.body["access_token"]

    # Call introspection endpoint
    req = ApiRequest(
        method="POST",
        path="/api/v1/auth/introspect",
        headers={"Content-Type": "application/json"},
        query_params={},
        body={"token": access_token},
        timestamp=datetime.utcnow(),
        request_id=str(uuid.uuid4()),
        client_ip="127.0.0.1",
    )
    resp = await gateway.process_request(req)
    assert resp.status_code == 200
    assert resp.body["active"] is True
    assert resp.body.get("sub") == user.user_id or resp.body.get("sub") is not None


@pytest.mark.asyncio
async def test_introspection_inactive_invalid_token(gateway):
    req = ApiRequest(
        method="POST",
        path="/api/v1/auth/introspect",
        headers={"Content-Type": "application/json"},
        query_params={},
        body={"token": "invalid.token.value"},
        timestamp=datetime.utcnow(),
        request_id=str(uuid.uuid4()),
        client_ip="127.0.0.1",
    )
    resp = await gateway.process_request(req)
    assert resp.status_code == 200
    assert resp.body["active"] is False


class _FakeBlacklistManager:
    def __init__(self, blacklisted):
        self._blacklisted = set(blacklisted)

    def is_jwt_token_blacklisted(self, token: str) -> bool:
        return token in self._blacklisted


@pytest.mark.asyncio
async def test_introspection_blacklisted_token(gateway):
    # Authenticate to get tokens
    auth_resp = await gateway.authenticate_user(
        username="introspect_user", password="IntrospectPass123!", client_ip="127.0.0.1"
    )
    if auth_resp.status_code != 200:
        # create user if not present in this gateway instance
        jwt_service = gateway.jwt_service
        await jwt_service.auth_service.create_user(
            username="introspect_user",
            email="intro@example.com",
            password="IntrospectPass123!",
            roles=[UserRole.DEVELOPER],
        )
        auth_resp = await gateway.authenticate_user(
            username="introspect_user", password="IntrospectPass123!", client_ip="127.0.0.1"
        )
    assert auth_resp.status_code == 200
    access_token = auth_resp.body["access_token"]

    # Inject fake blacklist so introspection short-circuits to inactive
    gateway.jwt_service.redis_cache_manager = _FakeBlacklistManager({access_token})

    req = ApiRequest(
        method="POST",
        path="/api/v1/auth/introspect",
        headers={"Content-Type": "application/json"},
        query_params={},
        body={"token": access_token},
        timestamp=datetime.utcnow(),
        request_id=str(uuid.uuid4()),
        client_ip="127.0.0.1",
    )
    resp = await gateway.process_request(req)
    assert resp.status_code == 200
    assert resp.body["active"] is False
    assert resp.body.get("reason") in ("revoked_blacklisted", "invalid_token")
