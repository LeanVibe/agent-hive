"""
Test suite for RBAC PostgreSQL integration

Tests the integration between the RBAC framework and PostgreSQL database models
with Redis caching, ensuring seamless coordination between components.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import redis
import tempfile
import os

# Import Security Agent's database models
import sys
sys.path.append('../security-Jul-17-0944')
from external_api.rbac_database_models import (
    Base, User, Role, PermissionModel, ResourceType, ActionType, PermissionScope,
    setup_default_rbac, create_default_roles, create_default_permissions
)

# Import our RBAC components
from external_api.rbac_postgres_manager import PostgreSQLRBACManager
from external_api.rbac_postgres_middleware import PostgreSQLRBACMiddleware
from external_api.rbac_framework import Permission as RBACPermission, Role as RBACRole
from external_api.models import ApiRequest
from external_api.auth_middleware import AuthenticationMiddleware, AuthResult


@pytest.fixture(scope="function")
def db_session():
    """Create test database session."""
    # Create in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Set up default RBAC
    setup_default_rbac(session)
    
    yield session
    
    session.close()


@pytest.fixture(scope="function")
def session_factory(db_session):
    """Create session factory for testing."""
    def _session_factory():
        return db_session
    return _session_factory


@pytest.fixture(scope="function")
def mock_redis():
    """Mock Redis client."""
    redis_mock = Mock(spec=redis.Redis)
    redis_mock.get.return_value = None
    redis_mock.setex.return_value = True
    redis_mock.keys.return_value = []
    redis_mock.delete.return_value = True
    redis_mock.ping.return_value = True
    return redis_mock


@pytest.fixture(scope="function")
def rbac_manager(session_factory, mock_redis):
    """Create PostgreSQL RBAC manager."""
    return PostgreSQLRBACManager(session_factory, mock_redis)


@pytest.fixture(scope="function")
def auth_middleware():
    """Mock authentication middleware."""
    mock_auth = Mock(spec=AuthenticationMiddleware)
    return mock_auth


@pytest.fixture(scope="function")
def rbac_middleware(session_factory, auth_middleware, mock_redis):
    """Create PostgreSQL RBAC middleware."""
    return PostgreSQLRBACMiddleware(session_factory, auth_middleware, mock_redis)


class TestPostgreSQLRBACManager:
    """Test PostgreSQL RBAC manager functionality."""
    
    def test_manager_initialization(self, rbac_manager):
        """Test RBAC manager initialization."""
        assert rbac_manager is not None
        assert rbac_manager.session_factory is not None
        assert rbac_manager.redis_client is not None
        assert rbac_manager.evaluator is not None
    
    def test_create_role_with_database_persistence(self, rbac_manager, db_session):
        """Test role creation with database persistence."""
        # Create permissions for the role
        permissions = [
            RBACPermission(
                resource_type=ResourceType.API_ENDPOINT,
                action=ActionType.READ,
                scope=PermissionScope.PROJECT
            ),
            RBACPermission(
                resource_type=ResourceType.SERVICE,
                action=ActionType.DEPLOY,
                scope=PermissionScope.GLOBAL
            )
        ]
        
        # Create role
        role = rbac_manager.create_role(
            name="test_role",
            description="Test role",
            permissions=permissions,
            parent_roles=["admin"]
        )
        
        assert role.name == "test_role"
        assert role.description == "Test role"
        assert len(role.permissions) == 2
        assert "admin" in role.parent_roles
        
        # Verify in database
        db_role = db_session.query(Role).filter_by(name="test_role").first()
        assert db_role is not None
        assert db_role.name == "test_role"
        assert db_role.description == "Test role"
        assert "admin" in db_role.parent_role_names
    
    def test_create_user_with_database_persistence(self, rbac_manager, db_session):
        """Test user creation with database persistence."""
        # Create user
        user = rbac_manager.create_user(
            user_id="test_user",
            roles=["admin", "developer"],
            email="test@example.com",
            full_name="Test User"
        )
        
        assert user.user_id == "test_user"
        assert "admin" in user.roles
        assert "developer" in user.roles
        assert user.metadata["email"] == "test@example.com"
        assert user.metadata["full_name"] == "Test User"
        
        # Verify in database
        db_user = db_session.query(User).filter_by(username="test_user").first()
        assert db_user is not None
        assert db_user.username == "test_user"
        assert db_user.email == "test@example.com"
        assert db_user.full_name == "Test User"
        assert len(db_user.roles) == 2
    
    def test_role_hierarchy_persistence(self, rbac_manager, db_session):
        """Test role hierarchy persistence."""
        # Create parent role
        parent_role = rbac_manager.create_role(
            name="parent_role",
            description="Parent role"
        )
        
        # Create child role
        child_role = rbac_manager.create_role(
            name="child_role",
            description="Child role",
            parent_roles=["parent_role"]
        )
        
        # Verify hierarchy in database
        db_parent = db_session.query(Role).filter_by(name="parent_role").first()
        db_child = db_session.query(Role).filter_by(name="child_role").first()
        
        assert db_parent is not None
        assert db_child is not None
        assert "parent_role" in db_child.parent_role_names
        assert "child_role" in db_parent.child_role_names
    
    def test_permission_checking_with_hierarchy(self, rbac_manager, db_session):
        """Test permission checking with role hierarchy."""
        # Create user with child role
        user = rbac_manager.create_user(
            user_id="hierarchy_user",
            roles=["developer"],  # developer inherits from admin
            email="hierarchy@example.com"
        )
        
        # Check if user has admin permissions through hierarchy
        has_admin_permission = rbac_manager.check_permission(
            "hierarchy_user",
            ResourceType.API_ENDPOINT,
            ActionType.READ
        )
        
        # Should have permission through hierarchy
        assert has_admin_permission is True
    
    def test_bulk_operations(self, rbac_manager):
        """Test bulk operations."""
        # Create multiple users
        for i in range(3):
            rbac_manager.create_user(
                user_id=f"bulk_user_{i}",
                roles=["admin"],
                email=f"bulk{i}@example.com"
            )
        
        # Bulk check permissions
        requests = [
            {
                "user_id": "bulk_user_0",
                "resource_type": "api_endpoint",
                "action": "read"
            },
            {
                "user_id": "bulk_user_1",
                "resource_type": "service",
                "action": "deploy"
            },
            {
                "user_id": "bulk_user_2",
                "resource_type": "database",
                "action": "read"
            }
        ]
        
        results = rbac_manager.bulk_check_permissions(requests)
        
        assert len(results) == 3
        assert all(isinstance(v, bool) for v in results.values())
    
    def test_role_management_operations(self, rbac_manager, db_session):
        """Test role management operations."""
        # Create role
        role = rbac_manager.create_role(
            name="management_role",
            description="Management role"
        )
        
        # Update role
        success = rbac_manager.update_role(
            name="management_role",
            description="Updated management role"
        )
        
        assert success is True
        
        # Verify update in database
        db_role = db_session.query(Role).filter_by(name="management_role").first()
        assert db_role.description == "Updated management role"
        
        # Delete role
        success = rbac_manager.delete_role("management_role")
        assert success is True
        
        # Verify deletion in database
        db_role = db_session.query(Role).filter_by(name="management_role").first()
        assert db_role is None
    
    def test_caching_behavior(self, rbac_manager, mock_redis):
        """Test caching behavior."""
        # Create user
        user = rbac_manager.create_user(
            user_id="cache_user",
            roles=["admin"],
            email="cache@example.com"
        )
        
        # First permission check (should cache result)
        result1 = rbac_manager.check_permission(
            "cache_user",
            ResourceType.API_ENDPOINT,
            ActionType.READ
        )
        
        # Second permission check (should use cache)
        result2 = rbac_manager.check_permission(
            "cache_user",
            ResourceType.API_ENDPOINT,
            ActionType.READ
        )
        
        assert result1 == result2
        assert result1 is True
    
    def test_stats_collection(self, rbac_manager):
        """Test statistics collection."""
        # Create some data
        rbac_manager.create_user(
            user_id="stats_user",
            roles=["admin"],
            email="stats@example.com"
        )
        
        rbac_manager.create_role(
            name="stats_role",
            description="Stats role"
        )
        
        # Get stats
        stats = rbac_manager.get_stats()
        
        assert "total_users" in stats
        assert "total_roles" in stats
        assert "total_permissions" in stats
        assert stats["total_users"] > 0
        assert stats["total_roles"] > 0


@pytest.mark.asyncio
class TestPostgreSQLRBACMiddleware:
    """Test PostgreSQL RBAC middleware functionality."""
    
    async def test_middleware_initialization(self, rbac_middleware):
        """Test middleware initialization."""
        assert rbac_middleware is not None
        assert rbac_middleware.session_factory is not None
        assert rbac_middleware.rbac_manager is not None
        assert rbac_middleware.resource_mapper is not None
        assert rbac_middleware.audit_logger is not None
    
    async def test_successful_authorization_flow(self, rbac_middleware, auth_middleware, db_session):
        """Test successful authorization flow."""
        # Create test user
        user = User(
            username="auth_user",
            email="auth@example.com",
            password_hash="hashed_password"
        )
        db_session.add(user)
        
        # Assign admin role
        admin_role = db_session.query(Role).filter_by(name="admin").first()
        if admin_role:
            user.roles.append(admin_role)
        
        db_session.commit()
        
        # Mock authentication success
        auth_result = AuthResult(
            success=True,
            user_id="auth_user",
            permissions=[],
            metadata={"auth_method": "api_key"}
        )
        auth_middleware.authenticate_request = AsyncMock(return_value=auth_result)
        
        # Create request
        request = Mock()
        request.path = "/api/v1/services"
        request.method = "GET"
        request.client_ip = "127.0.0.1"
        request.headers = {"User-Agent": "test"}
        request.body = None
        
        # Authorize request
        result = await rbac_middleware.authorize_request(request)
        
        assert result.authorized is True
        assert result.user_id == "auth_user"
        assert result.context.resource_type == ResourceType.SERVICE
        assert result.context.action == ActionType.READ
    
    async def test_failed_authentication(self, rbac_middleware, auth_middleware):
        """Test failed authentication."""
        # Mock authentication failure
        auth_result = AuthResult(
            success=False,
            error="Invalid credentials"
        )
        auth_middleware.authenticate_request = AsyncMock(return_value=auth_result)
        
        # Create request
        request = Mock()
        request.path = "/api/v1/services"
        request.method = "GET"
        request.client_ip = "127.0.0.1"
        request.headers = {"User-Agent": "test"}
        
        # Authorize request
        result = await rbac_middleware.authorize_request(request)
        
        assert result.authorized is False
        assert "Authentication failed" in result.reason
    
    async def test_insufficient_permissions(self, rbac_middleware, auth_middleware, db_session):
        """Test insufficient permissions."""
        # Create test user with limited permissions
        user = User(
            username="limited_user",
            email="limited@example.com",
            password_hash="hashed_password"
        )
        db_session.add(user)
        
        # Assign viewer role (read-only)
        viewer_role = db_session.query(Role).filter_by(name="readonly").first()
        if viewer_role:
            user.roles.append(viewer_role)
        
        db_session.commit()
        
        # Mock authentication success
        auth_result = AuthResult(
            success=True,
            user_id="limited_user",
            permissions=[],
            metadata={"auth_method": "api_key"}
        )
        auth_middleware.authenticate_request = AsyncMock(return_value=auth_result)
        
        # Create request requiring write permissions
        request = Mock()
        request.path = "/api/v1/services"
        request.method = "POST"  # Create operation
        request.client_ip = "127.0.0.1"
        request.headers = {"User-Agent": "test"}
        request.body = None
        
        # Authorize request
        result = await rbac_middleware.authorize_request(request)
        
        assert result.authorized is False
        assert "Insufficient permissions" in result.reason
    
    async def test_bypass_authentication(self, rbac_middleware):
        """Test bypassing authentication for certain paths."""
        # Create request to bypass path
        request = Mock()
        request.path = "/health"
        request.method = "GET"
        request.client_ip = "127.0.0.1"
        request.headers = {"User-Agent": "test"}
        
        # Authorize request
        result = await rbac_middleware.authorize_request(request)
        
        assert result.authorized is True
        assert result.user_id == "anonymous"
        assert "Bypassed authentication" in result.reason
    
    async def test_cache_invalidation(self, rbac_middleware, db_session):
        """Test cache invalidation."""
        # Create test user
        user = User(
            username="cache_test_user",
            email="cache_test@example.com",
            password_hash="hashed_password"
        )
        db_session.add(user)
        db_session.commit()
        
        # Invalidate user cache
        await rbac_middleware.invalidate_user_cache("cache_test_user")
        
        # Should not raise any exceptions
        assert True
    
    async def test_bulk_operations(self, rbac_middleware, auth_middleware, db_session):
        """Test bulk operations."""
        # Create test user
        user = User(
            username="bulk_test_user",
            email="bulk@example.com",
            password_hash="hashed_password"
        )
        db_session.add(user)
        
        # Assign admin role
        admin_role = db_session.query(Role).filter_by(name="admin").first()
        if admin_role:
            user.roles.append(admin_role)
        
        db_session.commit()
        
        # Test bulk permission checking
        permission_requests = [
            (ResourceType.API_ENDPOINT, ActionType.READ, None),
            (ResourceType.SERVICE, ActionType.DEPLOY, "test-service"),
            (ResourceType.DATABASE, ActionType.READ, "test-db")
        ]
        
        results = await rbac_middleware.bulk_check_permissions(
            "bulk_test_user",
            permission_requests
        )
        
        assert len(results) == 3
        assert all(isinstance(v, bool) for v in results.values())
    
    async def test_metrics_collection(self, rbac_middleware, auth_middleware, db_session):
        """Test metrics collection."""
        # Create test user
        user = User(
            username="metrics_user",
            email="metrics@example.com",
            password_hash="hashed_password"
        )
        db_session.add(user)
        
        # Assign admin role
        admin_role = db_session.query(Role).filter_by(name="admin").first()
        if admin_role:
            user.roles.append(admin_role)
        
        db_session.commit()
        
        # Mock authentication success
        auth_result = AuthResult(
            success=True,
            user_id="metrics_user",
            permissions=[],
            metadata={"auth_method": "api_key"}
        )
        auth_middleware.authenticate_request = AsyncMock(return_value=auth_result)
        
        # Create request
        request = Mock()
        request.path = "/api/v1/services"
        request.method = "GET"
        request.client_ip = "127.0.0.1"
        request.headers = {"User-Agent": "test"}
        request.body = None
        
        # Authorize request
        initial_requests = rbac_middleware.metrics["total_requests"]
        await rbac_middleware.authorize_request(request)
        
        # Check metrics
        metrics = rbac_middleware.get_metrics()
        
        assert metrics["total_requests"] > initial_requests
        assert "authorization_rate" in metrics
        assert "denial_rate" in metrics
        assert "cache_hit_rate" in metrics
    
    async def test_audit_logging(self, rbac_middleware, auth_middleware, db_session):
        """Test audit logging."""
        # Create test user
        user = User(
            username="audit_user",
            email="audit@example.com",
            password_hash="hashed_password"
        )
        db_session.add(user)
        
        # Assign admin role
        admin_role = db_session.query(Role).filter_by(name="admin").first()
        if admin_role:
            user.roles.append(admin_role)
        
        db_session.commit()
        
        # Mock authentication success
        auth_result = AuthResult(
            success=True,
            user_id="audit_user",
            permissions=[],
            metadata={"auth_method": "api_key"}
        )
        auth_middleware.authenticate_request = AsyncMock(return_value=auth_result)
        
        # Create request
        request = Mock()
        request.path = "/api/v1/services"
        request.method = "GET"
        request.client_ip = "127.0.0.1"
        request.headers = {"User-Agent": "test"}
        request.body = None
        
        # Authorize request
        await rbac_middleware.authorize_request(request)
        
        # Check audit summary
        audit_summary = await rbac_middleware.get_audit_summary()
        
        assert "database_analytics" in audit_summary
        assert "redis_analytics" in audit_summary
        assert "middleware_metrics" in audit_summary
        assert "rbac_stats" in audit_summary
    
    async def test_health_check(self, rbac_middleware):
        """Test health check functionality."""
        health = await rbac_middleware.health_check()
        
        assert "status" in health
        assert "components" in health
        assert "postgresql" in health["components"]
        assert "rbac_manager" in health["components"]


class TestIntegrationScenarios:
    """Test integration scenarios between components."""
    
    def test_database_to_rbac_framework_conversion(self, db_session):
        """Test conversion from database models to RBAC framework objects."""
        # Create database user
        db_user = User(
            username="conversion_user",
            email="conversion@example.com",
            password_hash="hashed_password"
        )
        db_session.add(db_user)
        
        # Create database role
        db_role = Role(
            name="conversion_role",
            description="Conversion role"
        )
        db_session.add(db_role)
        
        # Create database permission
        db_permission = PermissionModel(
            name="conversion_permission",
            resource_type=ResourceType.API_ENDPOINT.value,
            action_type=ActionType.READ.value,
            scope=PermissionScope.PROJECT.value
        )
        db_session.add(db_permission)
        
        # Link them
        db_user.roles.append(db_role)
        db_role.permissions.append(db_permission)
        
        db_session.commit()
        
        # Test conversion
        rbac_permission = db_permission.to_rbac_permission()
        assert rbac_permission.resource_type == ResourceType.API_ENDPOINT
        assert rbac_permission.action == ActionType.READ
        assert rbac_permission.scope == PermissionScope.PROJECT
    
    def test_full_integration_flow(self, rbac_manager, db_session):
        """Test full integration flow from database to RBAC operations."""
        # Create user through RBAC manager
        rbac_user = rbac_manager.create_user(
            user_id="integration_user",
            roles=["admin"],
            email="integration@example.com"
        )
        
        # Check permission through RBAC manager
        has_permission = rbac_manager.check_permission(
            "integration_user",
            ResourceType.API_ENDPOINT,
            ActionType.READ
        )
        
        assert has_permission is True
        
        # Verify user exists in database
        db_user = db_session.query(User).filter_by(username="integration_user").first()
        assert db_user is not None
        assert db_user.email == "integration@example.com"
        
        # Verify user has admin role
        admin_role = db_session.query(Role).filter_by(name="admin").first()
        assert admin_role in db_user.roles
    
    def test_performance_with_large_dataset(self, rbac_manager):
        """Test performance with larger dataset."""
        # Create multiple users and roles
        for i in range(50):
            rbac_manager.create_user(
                user_id=f"perf_user_{i}",
                roles=["admin"] if i % 2 == 0 else ["readonly"],
                email=f"perf{i}@example.com"
            )
        
        # Test bulk permission checking
        import time
        start_time = time.time()
        
        requests = [
            {
                "user_id": f"perf_user_{i}",
                "resource_type": "api_endpoint",
                "action": "read"
            }
            for i in range(20)
        ]
        
        results = rbac_manager.bulk_check_permissions(requests)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within reasonable time
        assert execution_time < 5.0  # 5 seconds
        assert len(results) == 20
    
    def test_concurrent_operations(self, rbac_manager):
        """Test concurrent operations."""
        import threading
        import time
        
        results = []
        errors = []
        
        def create_user_worker(user_id):
            try:
                user = rbac_manager.create_user(
                    user_id=f"concurrent_{user_id}",
                    roles=["admin"],
                    email=f"concurrent{user_id}@example.com"
                )
                results.append(user)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_user_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(results) == 10
        assert len(errors) == 0  # No errors should occur


if __name__ == "__main__":
    pytest.main([__file__, "-v"])