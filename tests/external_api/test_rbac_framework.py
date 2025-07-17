"""
Comprehensive test suite for RBAC framework

Tests cover:
- Role hierarchy and inheritance
- Permission evaluation
- User management
- Dynamic authorization
- Cache performance
- Edge cases and security
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import redis

from external_api.rbac_framework import (
    RBACManager, User, Role, Permission, ResourceType, ActionType,
    PermissionScope, AuthorizationEvaluator
)
from external_api.permission_manager import PermissionManager, PermissionCacheManager
from external_api.rbac_middleware import RBACMiddleware, AuthorizationContext, ResourceMapper
from external_api.models import ApiRequest, ApiResponse
from external_api.auth_middleware import AuthenticationMiddleware, AuthResult


class TestPermission:
    """Test Permission class functionality."""
    
    def test_permission_creation(self):
        """Test permission creation and basic properties."""
        perm = Permission(
            resource_type=ResourceType.API_ENDPOINT,
            action=ActionType.READ,
            scope=PermissionScope.PROJECT,
            resource_id="test-resource"
        )
        
        assert perm.resource_type == ResourceType.API_ENDPOINT
        assert perm.action == ActionType.READ
        assert perm.scope == PermissionScope.PROJECT
        assert perm.resource_id == "test-resource"
        assert perm.is_valid() is True
    
    def test_permission_expiration(self):
        """Test permission expiration functionality."""
        # Create expired permission
        expired_perm = Permission(
            resource_type=ResourceType.API_ENDPOINT,
            action=ActionType.READ,
            scope=PermissionScope.PROJECT,
            expires_at=datetime.now() - timedelta(hours=1)
        )
        
        assert expired_perm.is_valid() is False
        
        # Create valid permission
        valid_perm = Permission(
            resource_type=ResourceType.API_ENDPOINT,
            action=ActionType.READ,
            scope=PermissionScope.PROJECT,
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        assert valid_perm.is_valid() is True
    
    def test_permission_matching(self):
        """Test permission matching logic."""
        perm = Permission(
            resource_type=ResourceType.API_ENDPOINT,
            action=ActionType.READ,
            scope=PermissionScope.PROJECT,
            resource_id="test-resource"
        )
        
        # Exact match
        assert perm.matches_request(
            ResourceType.API_ENDPOINT, 
            ActionType.READ, 
            "test-resource"
        ) is True
        
        # Different resource type
        assert perm.matches_request(
            ResourceType.SERVICE, 
            ActionType.READ, 
            "test-resource"
        ) is False
        
        # Different action
        assert perm.matches_request(
            ResourceType.API_ENDPOINT, 
            ActionType.UPDATE, 
            "test-resource"
        ) is False
        
        # Different resource ID
        assert perm.matches_request(
            ResourceType.API_ENDPOINT, 
            ActionType.READ, 
            "different-resource"
        ) is False
    
    def test_permission_wildcard_matching(self):
        """Test permission wildcard matching."""
        wildcard_perm = Permission(
            resource_type=ResourceType.API_ENDPOINT,
            action=ActionType.READ,
            scope=PermissionScope.PROJECT,
            resource_id="*"
        )
        
        # Should match any resource
        assert wildcard_perm.matches_request(
            ResourceType.API_ENDPOINT, 
            ActionType.READ, 
            "any-resource"
        ) is True
        
        assert wildcard_perm.matches_request(
            ResourceType.API_ENDPOINT, 
            ActionType.READ, 
            "another-resource"
        ) is True
    
    def test_permission_conditions(self):
        """Test permission conditions."""
        perm = Permission(
            resource_type=ResourceType.API_ENDPOINT,
            action=ActionType.READ,
            scope=PermissionScope.PROJECT,
            conditions={"environment": "production"}
        )
        
        # Matching conditions
        assert perm.matches_request(
            ResourceType.API_ENDPOINT,
            ActionType.READ,
            None,
            {"environment": "production"}
        ) is True
        
        # Non-matching conditions
        assert perm.matches_request(
            ResourceType.API_ENDPOINT,
            ActionType.READ,
            None,
            {"environment": "staging"}
        ) is False
        
        # Missing conditions
        assert perm.matches_request(
            ResourceType.API_ENDPOINT,
            ActionType.READ,
            None,
            {}
        ) is False


class TestRole:
    """Test Role class functionality."""
    
    def test_role_creation(self):
        """Test role creation and basic properties."""
        role = Role(
            name="test-role",
            description="Test role",
            permissions=[],
            parent_roles=["parent-role"]
        )
        
        assert role.name == "test-role"
        assert role.description == "Test role"
        assert role.parent_roles == ["parent-role"]
        assert role.is_active is True
    
    def test_role_permission_management(self):
        """Test adding and removing permissions from roles."""
        role = Role(name="test-role", description="Test role")
        
        perm = Permission(
            resource_type=ResourceType.API_ENDPOINT,
            action=ActionType.READ,
            scope=PermissionScope.PROJECT
        )
        
        # Add permission
        role.add_permission(perm)
        assert perm in role.permissions
        
        # Remove permission
        role.remove_permission(perm)
        assert perm not in role.permissions
    
    def test_role_has_permission(self):
        """Test role permission checking."""
        role = Role(name="test-role", description="Test role")
        
        perm = Permission(
            resource_type=ResourceType.API_ENDPOINT,
            action=ActionType.READ,
            scope=PermissionScope.PROJECT
        )
        
        role.add_permission(perm)
        
        # Should have permission
        assert role.has_permission(
            ResourceType.API_ENDPOINT,
            ActionType.READ
        ) is True
        
        # Should not have different permission
        assert role.has_permission(
            ResourceType.API_ENDPOINT,
            ActionType.UPDATE
        ) is False


class TestUser:
    """Test User class functionality."""
    
    def test_user_creation(self):
        """Test user creation and basic properties."""
        user = User(
            user_id="test-user",
            roles=["role1", "role2"],
            is_active=True
        )
        
        assert user.user_id == "test-user"
        assert user.roles == ["role1", "role2"]
        assert user.is_active is True
    
    def test_user_role_management(self):
        """Test assigning and removing roles from users."""
        user = User(user_id="test-user")
        
        # Assign role
        user.assign_role("test-role")
        assert "test-role" in user.roles
        
        # Remove role
        user.remove_role("test-role")
        assert "test-role" not in user.roles
    
    def test_user_direct_permissions(self):
        """Test direct permission management."""
        user = User(user_id="test-user")
        
        perm = Permission(
            resource_type=ResourceType.API_ENDPOINT,
            action=ActionType.READ,
            scope=PermissionScope.PROJECT
        )
        
        # Add direct permission
        user.add_direct_permission(perm)
        assert perm in user.direct_permissions


class TestAuthorizationEvaluator:
    """Test AuthorizationEvaluator functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.evaluator = AuthorizationEvaluator()
        
        # Create test roles
        self.admin_role = Role(
            name="admin",
            description="Administrator role",
            permissions=[
                Permission(ResourceType.API_ENDPOINT, ActionType.ADMIN, PermissionScope.GLOBAL),
                Permission(ResourceType.SERVICE, ActionType.ADMIN, PermissionScope.GLOBAL)
            ]
        )
        
        self.user_role = Role(
            name="user",
            description="User role",
            permissions=[
                Permission(ResourceType.API_ENDPOINT, ActionType.READ, PermissionScope.PROJECT),
                Permission(ResourceType.SERVICE, ActionType.READ, PermissionScope.PROJECT)
            ]
        )
        
        self.viewer_role = Role(
            name="viewer",
            description="Viewer role",
            parent_roles=["user"],
            permissions=[
                Permission(ResourceType.API_ENDPOINT, ActionType.READ, PermissionScope.PROJECT)
            ]
        )
        
        self.roles = {
            "admin": self.admin_role,
            "user": self.user_role,
            "viewer": self.viewer_role
        }
    
    def test_direct_permission_evaluation(self):
        """Test evaluation of direct permissions."""
        self.setUp()
        
        # Create user with direct permission
        user = User(user_id="test-user")
        user.add_direct_permission(
            Permission(ResourceType.API_ENDPOINT, ActionType.READ, PermissionScope.PROJECT)
        )
        
        # Should have permission
        result = self.evaluator.evaluate_permission(
            user, self.roles, ResourceType.API_ENDPOINT, ActionType.READ
        )
        assert result is True
        
        # Should not have different permission
        result = self.evaluator.evaluate_permission(
            user, self.roles, ResourceType.API_ENDPOINT, ActionType.UPDATE
        )
        assert result is False
    
    def test_role_based_permission_evaluation(self):
        """Test evaluation of role-based permissions."""
        self.setUp()
        
        # Create user with admin role
        user = User(user_id="test-user", roles=["admin"])
        
        # Should have admin permission
        result = self.evaluator.evaluate_permission(
            user, self.roles, ResourceType.API_ENDPOINT, ActionType.ADMIN
        )
        assert result is True
        
        # Create user with user role
        user = User(user_id="test-user", roles=["user"])
        
        # Should have read permission
        result = self.evaluator.evaluate_permission(
            user, self.roles, ResourceType.API_ENDPOINT, ActionType.READ
        )
        assert result is True
        
        # Should not have admin permission
        result = self.evaluator.evaluate_permission(
            user, self.roles, ResourceType.API_ENDPOINT, ActionType.ADMIN
        )
        assert result is False
    
    def test_role_hierarchy_evaluation(self):
        """Test evaluation with role hierarchy."""
        self.setUp()
        
        # Create user with viewer role (inherits from user)
        user = User(user_id="test-user", roles=["viewer"])
        
        # Should have permissions from both viewer and user roles
        result = self.evaluator.evaluate_permission(
            user, self.roles, ResourceType.API_ENDPOINT, ActionType.READ
        )
        assert result is True
        
        # Test hierarchy caching
        hierarchy = self.evaluator._get_role_hierarchy("viewer", self.roles)
        assert "viewer" in hierarchy
        assert "user" in hierarchy
    
    def test_inactive_user_evaluation(self):
        """Test evaluation for inactive users."""
        self.setUp()
        
        # Create inactive user
        user = User(user_id="test-user", roles=["admin"], is_active=False)
        
        # Should not have permission even with admin role
        result = self.evaluator.evaluate_permission(
            user, self.roles, ResourceType.API_ENDPOINT, ActionType.ADMIN
        )
        assert result is False
    
    def test_cache_functionality(self):
        """Test permission evaluation caching."""
        self.setUp()
        
        user = User(user_id="test-user", roles=["admin"])
        
        # First evaluation should be cached
        result1 = self.evaluator.evaluate_permission(
            user, self.roles, ResourceType.API_ENDPOINT, ActionType.READ
        )
        
        # Second evaluation should use cache
        result2 = self.evaluator.evaluate_permission(
            user, self.roles, ResourceType.API_ENDPOINT, ActionType.READ
        )
        
        assert result1 == result2
        assert len(self.evaluator.permission_cache) > 0
        
        # Clear cache
        self.evaluator.clear_cache()
        assert len(self.evaluator.permission_cache) == 0


class TestRBACManager:
    """Test RBACManager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.rbac = RBACManager()
    
    def test_rbac_initialization(self):
        """Test RBAC manager initialization."""
        self.setUp()
        
        # Should have system roles
        assert "super_admin" in self.rbac.roles
        assert "admin" in self.rbac.roles
        assert "developer" in self.rbac.roles
        assert "viewer" in self.rbac.roles
        
        # Check role hierarchy
        admin_role = self.rbac.roles["admin"]
        assert "super_admin" in admin_role.parent_roles
    
    def test_role_management(self):
        """Test role creation, update, and deletion."""
        self.setUp()
        
        # Create role
        role = self.rbac.create_role(
            name="test-role",
            description="Test role",
            permissions=[
                Permission(ResourceType.API_ENDPOINT, ActionType.READ, PermissionScope.PROJECT)
            ]
        )
        
        assert role.name == "test-role"
        assert "test-role" in self.rbac.roles
        
        # Update role
        success = self.rbac.update_role(
            name="test-role",
            description="Updated test role"
        )
        assert success is True
        assert self.rbac.roles["test-role"].description == "Updated test role"
        
        # Delete role
        success = self.rbac.delete_role("test-role")
        assert success is True
        assert "test-role" not in self.rbac.roles
    
    def test_user_management(self):
        """Test user creation, update, and deletion."""
        self.setUp()
        
        # Create user
        user = self.rbac.create_user(
            user_id="test-user",
            roles=["admin"]
        )
        
        assert user.user_id == "test-user"
        assert "test-user" in self.rbac.users
        
        # Update user
        success = self.rbac.update_user(
            user_id="test-user",
            roles=["developer"]
        )
        assert success is True
        assert self.rbac.users["test-user"].roles == ["developer"]
        
        # Delete user
        success = self.rbac.delete_user("test-user")
        assert success is True
        assert "test-user" not in self.rbac.users
    
    def test_permission_checking(self):
        """Test permission checking functionality."""
        self.setUp()
        
        # Create user with admin role
        self.rbac.create_user(user_id="test-user", roles=["admin"])
        
        # Should have permission
        result = self.rbac.check_permission(
            "test-user",
            ResourceType.API_ENDPOINT,
            ActionType.READ
        )
        assert result is True
        
        # Non-existent user should not have permission
        result = self.rbac.check_permission(
            "non-existent",
            ResourceType.API_ENDPOINT,
            ActionType.READ
        )
        assert result is False
    
    def test_role_hierarchy_management(self):
        """Test role hierarchy creation and management."""
        self.setUp()
        
        # Create parent role
        parent_role = self.rbac.create_role(
            name="parent-role",
            description="Parent role",
            permissions=[
                Permission(ResourceType.API_ENDPOINT, ActionType.READ, PermissionScope.PROJECT)
            ]
        )
        
        # Create child role
        child_role = self.rbac.create_role(
            name="child-role",
            description="Child role",
            parent_roles=["parent-role"],
            permissions=[
                Permission(ResourceType.API_ENDPOINT, ActionType.UPDATE, PermissionScope.PROJECT)
            ]
        )
        
        # Check hierarchy
        assert "parent-role" in child_role.parent_roles
        assert "child-role" in parent_role.child_roles
        
        # Create user with child role
        self.rbac.create_user(user_id="test-user", roles=["child-role"])
        
        # Should have permissions from both parent and child
        assert self.rbac.check_permission(
            "test-user", ResourceType.API_ENDPOINT, ActionType.READ
        ) is True
        assert self.rbac.check_permission(
            "test-user", ResourceType.API_ENDPOINT, ActionType.UPDATE
        ) is True
    
    def test_audit_logging(self):
        """Test audit logging functionality."""
        self.setUp()
        
        # Create user (should be logged)
        self.rbac.create_user(user_id="test-user", roles=["admin"])
        
        # Check audit log
        audit_log = self.rbac.get_audit_log()
        assert len(audit_log) > 0
        
        # Find the create_user entry
        create_user_entry = None
        for entry in audit_log:
            if entry["action"] == "create_user":
                create_user_entry = entry
                break
        
        assert create_user_entry is not None
        assert create_user_entry["details"]["user_id"] == "test-user"
    
    def test_stats_collection(self):
        """Test statistics collection."""
        self.setUp()
        
        # Create some users and roles
        self.rbac.create_user(user_id="user1", roles=["admin"])
        self.rbac.create_user(user_id="user2", roles=["developer"])
        self.rbac.create_role(name="custom-role", description="Custom role")
        
        # Get stats
        stats = self.rbac.get_stats()
        
        assert stats["total_users"] >= 2
        assert stats["total_roles"] >= 6  # System roles + custom role
        assert "cache_size" in stats
        assert "audit_log_size" in stats


@pytest.mark.asyncio
class TestPermissionManager:
    """Test PermissionManager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.rbac = RBACManager()
        self.mock_redis = Mock(spec=redis.Redis)
        self.pm = PermissionManager(self.rbac, self.mock_redis)
    
    async def test_permission_checking_with_cache(self):
        """Test permission checking with caching."""
        self.setUp()
        
        # Create user
        self.rbac.create_user(user_id="test-user", roles=["admin"])
        
        # Mock Redis get (cache miss)
        self.mock_redis.get.return_value = None
        
        # Check permission
        result = await self.pm.check_permission(
            "test-user",
            ResourceType.API_ENDPOINT,
            ActionType.READ
        )
        
        assert result is True
        assert self.pm.metrics["permission_checks"] > 0
        assert self.pm.metrics["cache_misses"] > 0
    
    async def test_bulk_permission_checking(self):
        """Test bulk permission checking."""
        self.setUp()
        
        # Create users
        self.rbac.create_user(user_id="user1", roles=["admin"])
        self.rbac.create_user(user_id="user2", roles=["developer"])
        
        # Bulk check requests
        requests = [
            {
                "user_id": "user1",
                "resource_type": "api_endpoint",
                "action": "read"
            },
            {
                "user_id": "user2",
                "resource_type": "api_endpoint",
                "action": "read"
            }
        ]
        
        results = await self.pm.bulk_check_permissions(requests)
        
        assert len(results) == 2
        assert self.pm.metrics["bulk_operations"] > 0
    
    async def test_user_permission_caching(self):
        """Test user permission caching."""
        self.setUp()
        
        # Create user
        self.rbac.create_user(user_id="test-user", roles=["admin"])
        
        # Mock Redis responses
        self.mock_redis.get.return_value = None
        
        # Get user permissions
        permissions = await self.pm.get_user_permissions("test-user")
        
        assert len(permissions) > 0
        assert self.pm.metrics["cache_misses"] > 0
    
    async def test_permission_matrix_generation(self):
        """Test permission matrix generation."""
        self.setUp()
        
        # Create users
        self.rbac.create_user(user_id="user1", roles=["admin"])
        self.rbac.create_user(user_id="user2", roles=["developer"])
        
        # Define permissions to check
        permissions = [
            (ResourceType.API_ENDPOINT, ActionType.READ, None),
            (ResourceType.API_ENDPOINT, ActionType.UPDATE, None),
            (ResourceType.SERVICE, ActionType.ADMIN, None)
        ]
        
        # Generate matrix
        matrix = await self.pm.get_permission_matrix(["user1", "user2"], permissions)
        
        assert "user1" in matrix
        assert "user2" in matrix
        assert len(matrix["user1"]) == 3
        assert len(matrix["user2"]) == 3
    
    async def test_analytics_collection(self):
        """Test analytics collection."""
        self.setUp()
        
        # Create some data
        self.rbac.create_user(user_id="test-user", roles=["admin"])
        
        # Perform some operations
        await self.pm.check_permission(
            "test-user",
            ResourceType.API_ENDPOINT,
            ActionType.READ
        )
        
        # Get analytics
        analytics = await self.pm.get_permission_analytics()
        
        assert "total_users" in analytics
        assert "total_roles" in analytics
        assert "cache_performance" in analytics
        assert "operation_counts" in analytics


class TestResourceMapper:
    """Test ResourceMapper functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mapper = ResourceMapper()
    
    def test_endpoint_mapping(self):
        """Test endpoint to resource mapping."""
        self.setUp()
        
        # Create mock request
        request = Mock()
        request.path = "/api/v1/services"
        request.method = "GET"
        
        # Map request
        resource_type, action, resource_id = self.mapper.map_request_to_resource(request)
        
        assert resource_type == ResourceType.SERVICE
        assert action == ActionType.READ
        assert resource_id is None
    
    def test_pattern_matching(self):
        """Test pattern matching for parameterized endpoints."""
        self.setUp()
        
        # Create mock request with parameter
        request = Mock()
        request.path = "/api/v1/services/service-123"
        request.method = "GET"
        
        # Map request
        resource_type, action, resource_id = self.mapper.map_request_to_resource(request)
        
        assert resource_type == ResourceType.SERVICE
        assert action == ActionType.READ
        assert resource_id == "service-123"
    
    def test_method_to_action_mapping(self):
        """Test HTTP method to action mapping."""
        self.setUp()
        
        # Test different methods
        methods_actions = [
            ("GET", ActionType.READ),
            ("POST", ActionType.CREATE),
            ("PUT", ActionType.UPDATE),
            ("DELETE", ActionType.DELETE)
        ]
        
        for method, expected_action in methods_actions:
            request = Mock()
            request.path = "/api/v1/services"
            request.method = method
            
            _, action, _ = self.mapper.map_request_to_resource(request)
            assert action == expected_action
    
    def test_custom_endpoint_mapping(self):
        """Test adding custom endpoint mappings."""
        self.setUp()
        
        # Add custom mapping for special endpoint
        self.mapper.add_endpoint_mapping(
            "/api/v1/custom/execute",
            ResourceType.CONFIGURATION,
            ActionType.EXECUTE
        )
        
        # Test custom mapping
        request = Mock()
        request.path = "/api/v1/custom/execute"
        request.method = "POST"
        
        resource_type, action, _ = self.mapper.map_request_to_resource(request)
        assert resource_type == ResourceType.CONFIGURATION
        assert action == ActionType.EXECUTE  # Should use custom action for special endpoint


@pytest.mark.asyncio
class TestRBACMiddleware:
    """Test RBACMiddleware functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.rbac = RBACManager()
        self.mock_redis = Mock(spec=redis.Redis)
        self.pm = PermissionManager(self.rbac, self.mock_redis)
        self.auth_middleware = Mock(spec=AuthenticationMiddleware)
        self.middleware = RBACMiddleware(
            self.rbac, self.pm, self.auth_middleware, self.mock_redis
        )
    
    async def test_successful_authorization(self):
        """Test successful authorization flow."""
        self.setUp()
        
        # Create user
        self.rbac.create_user(user_id="test-user", roles=["admin"])
        
        # Mock authentication success
        auth_result = AuthResult(
            success=True,
            user_id="test-user",
            permissions=[],
            metadata={"auth_method": "api_key"}
        )
        self.auth_middleware.authenticate_request = AsyncMock(return_value=auth_result)
        
        # Create request
        request = Mock()
        request.path = "/api/v1/services"
        request.method = "GET"
        request.client_ip = "127.0.0.1"
        request.headers = {"User-Agent": "test"}
        request.body = None
        
        # Authorize request
        result = await self.middleware.authorize_request(request)
        
        assert result.authorized is True
        assert result.user_id == "test-user"
        assert result.context.resource_type == ResourceType.SERVICE
        assert result.context.action == ActionType.READ
    
    async def test_failed_authentication(self):
        """Test authorization with failed authentication."""
        self.setUp()
        
        # Mock authentication failure
        auth_result = AuthResult(
            success=False,
            error="Invalid credentials"
        )
        self.auth_middleware.authenticate_request = AsyncMock(return_value=auth_result)
        
        # Create request
        request = Mock()
        request.path = "/api/v1/services"
        request.method = "GET"
        request.client_ip = "127.0.0.1"
        request.headers = {"User-Agent": "test"}
        
        # Authorize request
        result = await self.middleware.authorize_request(request)
        
        assert result.authorized is False
        assert "Authentication failed" in result.reason
    
    async def test_insufficient_permissions(self):
        """Test authorization with insufficient permissions."""
        self.setUp()
        
        # Create user with limited permissions
        self.rbac.create_user(user_id="test-user", roles=["viewer"])
        
        # Mock authentication success
        auth_result = AuthResult(
            success=True,
            user_id="test-user",
            permissions=[],
            metadata={"auth_method": "api_key"}
        )
        self.auth_middleware.authenticate_request = AsyncMock(return_value=auth_result)
        
        # Create request requiring admin permissions
        request = Mock()
        request.path = "/api/v1/services/service-123/deploy"
        request.method = "POST"
        request.client_ip = "127.0.0.1"
        request.headers = {"User-Agent": "test"}
        request.body = None
        
        # Authorize request
        result = await self.middleware.authorize_request(request)
        
        assert result.authorized is False
        assert "Insufficient permissions" in result.reason
    
    async def test_bypass_authentication(self):
        """Test bypassing authentication for certain paths."""
        self.setUp()
        
        # Create request to bypass path
        request = Mock()
        request.path = "/health"
        request.method = "GET"
        request.client_ip = "127.0.0.1"
        request.headers = {"User-Agent": "test"}
        
        # Authorize request
        result = await self.middleware.authorize_request(request)
        
        assert result.authorized is True
        assert result.user_id == "anonymous"
        assert "Bypassed authentication" in result.reason
    
    async def test_metrics_collection(self):
        """Test metrics collection during authorization."""
        self.setUp()
        
        # Create user
        self.rbac.create_user(user_id="test-user", roles=["admin"])
        
        # Mock authentication success
        auth_result = AuthResult(
            success=True,
            user_id="test-user",
            permissions=[],
            metadata={"auth_method": "api_key"}
        )
        self.auth_middleware.authenticate_request = AsyncMock(return_value=auth_result)
        
        # Create request
        request = Mock()
        request.path = "/api/v1/services"
        request.method = "GET"
        request.client_ip = "127.0.0.1"
        request.headers = {"User-Agent": "test"}
        request.body = None
        
        # Authorize request
        initial_requests = self.middleware.metrics["total_requests"]
        await self.middleware.authorize_request(request)
        
        # Check metrics
        assert self.middleware.metrics["total_requests"] > initial_requests
        assert self.middleware.metrics["authorized_requests"] > 0
    
    async def test_audit_logging(self):
        """Test audit logging during authorization."""
        self.setUp()
        
        # Create user
        self.rbac.create_user(user_id="test-user", roles=["admin"])
        
        # Mock authentication success
        auth_result = AuthResult(
            success=True,
            user_id="test-user",
            permissions=[],
            metadata={"auth_method": "api_key"}
        )
        self.auth_middleware.authenticate_request = AsyncMock(return_value=auth_result)
        
        # Create request
        request = Mock()
        request.path = "/api/v1/services"
        request.method = "GET"
        request.client_ip = "127.0.0.1"
        request.headers = {"User-Agent": "test"}
        request.body = None
        
        # Authorize request
        await self.middleware.authorize_request(request)
        
        # Check audit log
        audit_summary = await self.middleware.get_audit_summary()
        assert "total_requests" in audit_summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])