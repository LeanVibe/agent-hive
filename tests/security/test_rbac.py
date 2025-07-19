#!/usr/bin/env python3
"""
Comprehensive RBAC Testing Framework

Test suite for Role-Based Access Control system including:
- Role management and inheritance
- Permission checking and validation
- User role assignments
- Integration with authentication system
- Performance and security testing
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any

from security.rbac_manager import RBACManager, RoleType, PermissionType, RoleDefinition
from security.permission_middleware import PermissionMiddleware, PermissionContext, PermissionResult
from security.auth_service import AuthenticationService
from config.auth_models import Permission, AuthResult


class TestRBACManager:
    """Test suite for RBAC Manager functionality."""
    
    @pytest.fixture
    def rbac_manager(self):
        """Create RBAC manager instance for testing."""
        return RBACManager()
    
    @pytest.fixture
    def auth_service(self):
        """Create authentication service for testing."""
        config = {
            "bcrypt_rounds": 4,  # Lower for faster tests
            "jwt_secret": "test-secret",
            "jwt_algorithm": "HS256",
            "token_expiry_minutes": 15
        }
        return AuthenticationService(config)
    
    @pytest.mark.asyncio
    async def test_default_roles_initialization(self, rbac_manager):
        """Test that default roles are properly initialized."""
        roles = await rbac_manager.list_roles()
        
        # Check that default roles exist
        role_names = [role.name for role in roles]
        expected_roles = ["Super Administrator", "Administrator", "Agent", "User", "Guest"]
        
        for expected_role in expected_roles:
            assert expected_role in role_names
        
        # Check Super Admin has all permissions
        super_admin_role = next(role for role in roles if role.name == "Super Administrator")
        assert PermissionType.SYSTEM_ADMIN in super_admin_role.permissions
        assert PermissionType.USER_MANAGEMENT in super_admin_role.permissions
        assert PermissionType.AGENT_MANAGEMENT in super_admin_role.permissions
    
    @pytest.mark.asyncio
    async def test_create_custom_role(self, rbac_manager):
        """Test creating custom roles."""
        # Create a custom role
        success, message, role = await rbac_manager.create_role(
            role_type=RoleType.USER,
            name="Test Manager",
            description="Test role for managing specific resources",
            permissions=[PermissionType.TASK_CREATE, PermissionType.TASK_READ],
            created_by="test_user"
        )
        
        assert success
        assert role is not None
        assert role.name == "Test Manager"
        assert PermissionType.TASK_CREATE in role.permissions
        assert PermissionType.TASK_READ in role.permissions
        
        # Verify role is stored
        retrieved_role = await rbac_manager.get_role(role.role_id)
        assert retrieved_role is not None
        assert retrieved_role.name == "Test Manager"
    
    @pytest.mark.asyncio
    async def test_role_inheritance(self, rbac_manager):
        """Test role inheritance functionality."""
        # Create parent role
        success, message, parent_role = await rbac_manager.create_role(
            role_type=RoleType.USER,
            name="Base Role",
            description="Base role with basic permissions",
            permissions=[PermissionType.READ_ONLY, PermissionType.PUBLIC_ACCESS]
        )
        assert success
        
        # Create child role that inherits from parent
        success, message, child_role = await rbac_manager.create_role(
            role_type=RoleType.USER,
            name="Extended Role",
            description="Extended role with additional permissions",
            permissions=[PermissionType.TASK_CREATE],
            inherits_from=[parent_role.role_id]
        )
        assert success
        
        # Test effective permissions include inherited ones
        effective_permissions = await rbac_manager._get_role_effective_permissions(child_role.role_id)
        
        # Should have both own and inherited permissions
        assert PermissionType.TASK_CREATE in effective_permissions  # Own permission
        assert PermissionType.READ_ONLY in effective_permissions     # Inherited
        assert PermissionType.PUBLIC_ACCESS in effective_permissions # Inherited
    
    @pytest.mark.asyncio
    async def test_user_role_assignment(self, rbac_manager):
        """Test assigning and revoking roles to/from users."""
        user_id = str(uuid.uuid4())
        
        # Get a role to assign
        roles = await rbac_manager.list_roles()
        user_role = next(role for role in roles if role.name == "User")
        
        # Assign role to user
        success, message = await rbac_manager.assign_role_to_user(
            user_id=user_id,
            role_id=user_role.role_id,
            assigned_by="test_admin"
        )
        assert success
        
        # Verify user has the role
        user_roles = await rbac_manager.get_user_roles(user_id)
        assert len(user_roles) == 1
        assert user_roles[0].role_id == user_role.role_id
        
        # Test duplicate assignment fails
        success, message = await rbac_manager.assign_role_to_user(
            user_id=user_id,
            role_id=user_role.role_id,
            assigned_by="test_admin"
        )
        assert not success
        assert "already has active role" in message
        
        # Revoke role
        success, message = await rbac_manager.revoke_role_from_user(
            user_id=user_id,
            role_id=user_role.role_id,
            revoked_by="test_admin"
        )
        assert success
        
        # Verify role is revoked
        user_roles = await rbac_manager.get_user_roles(user_id)
        assert len(user_roles) == 0
    
    @pytest.mark.asyncio
    async def test_permission_checking(self, rbac_manager):
        """Test permission checking for users."""
        user_id = str(uuid.uuid4())
        
        # Assign admin role to user
        roles = await rbac_manager.list_roles()
        admin_role = next(role for role in roles if role.name == "Administrator")
        
        await rbac_manager.assign_role_to_user(
            user_id=user_id,
            role_id=admin_role.role_id,
            assigned_by="test_admin"
        )
        
        # Test permission that admin should have
        result = await rbac_manager.check_permission(
            user_id=user_id,
            permission=PermissionType.USER_MANAGEMENT
        )
        assert result.granted
        assert result.reason.startswith("granted_via_roles")
        
        # Test permission that admin should not have
        result = await rbac_manager.check_permission(
            user_id=user_id,
            permission=PermissionType.SYSTEM_ADMIN
        )
        assert not result.granted
        assert "not_found" in result.reason
    
    @pytest.mark.asyncio
    async def test_effective_permissions(self, rbac_manager):
        """Test getting all effective permissions for a user."""
        user_id = str(uuid.uuid4())
        
        # Assign multiple roles
        roles = await rbac_manager.list_roles()
        user_role = next(role for role in roles if role.name == "User")
        agent_role = next(role for role in roles if role.name == "Agent")
        
        await rbac_manager.assign_role_to_user(user_id, user_role.role_id, "test_admin")
        await rbac_manager.assign_role_to_user(user_id, agent_role.role_id, "test_admin")
        
        # Get effective permissions
        permissions = await rbac_manager.get_user_permissions(user_id)
        
        # Should have permissions from both roles
        assert PermissionType.PUBLIC_ACCESS in permissions  # From User role
        assert PermissionType.TASK_EXECUTION in permissions # From Agent role
        assert len(permissions) > 0
    
    @pytest.mark.asyncio
    async def test_role_update(self, rbac_manager):
        """Test updating role definitions."""
        # Create a role
        success, message, role = await rbac_manager.create_role(
            role_type=RoleType.USER,
            name="Updatable Role",
            description="Role for update testing",
            permissions=[PermissionType.READ_ONLY]
        )
        assert success
        
        # Update the role
        updates = {
            "description": "Updated description",
            "permissions": [PermissionType.READ_ONLY, PermissionType.TASK_READ]
        }
        
        success, message = await rbac_manager.update_role(
            role_id=role.role_id,
            updates=updates,
            updated_by="test_admin"
        )
        assert success
        
        # Verify updates
        updated_role = await rbac_manager.get_role(role.role_id)
        assert updated_role.description == "Updated description"
        assert PermissionType.TASK_READ in updated_role.permissions
    
    @pytest.mark.asyncio
    async def test_role_deletion(self, rbac_manager):
        """Test role deletion with and without force."""
        user_id = str(uuid.uuid4())
        
        # Create a role
        success, message, role = await rbac_manager.create_role(
            role_type=RoleType.USER,
            name="Deletable Role",
            description="Role for deletion testing",
            permissions=[PermissionType.READ_ONLY]
        )
        assert success
        
        # Assign role to user
        await rbac_manager.assign_role_to_user(user_id, role.role_id, "test_admin")
        
        # Try to delete without force - should fail
        success, message = await rbac_manager.delete_role(
            role_id=role.role_id,
            deleted_by="test_admin",
            force=False
        )
        assert not success
        assert "assigned to" in message
        
        # Delete with force - should succeed
        success, message = await rbac_manager.delete_role(
            role_id=role.role_id,
            deleted_by="test_admin",
            force=True
        )
        assert success
        
        # Verify role is deactivated
        deleted_role = await rbac_manager.get_role(role.role_id)
        assert not deleted_role.active
    
    @pytest.mark.asyncio
    async def test_permission_caching(self, rbac_manager):
        """Test permission result caching."""
        user_id = str(uuid.uuid4())
        
        # Assign role
        roles = await rbac_manager.list_roles()
        user_role = next(role for role in roles if role.name == "User")
        await rbac_manager.assign_role_to_user(user_id, user_role.role_id, "test_admin")
        
        # First permission check (should cache result)
        result1 = await rbac_manager.check_permission(user_id, PermissionType.PUBLIC_ACCESS)
        assert result1.granted
        
        # Second permission check (should use cache)
        result2 = await rbac_manager.check_permission(user_id, PermissionType.PUBLIC_ACCESS)
        assert result2.granted
        
        # Verify cache exists
        assert user_id in rbac_manager.permission_cache
        assert PermissionType.PUBLIC_ACCESS in rbac_manager.permission_cache[user_id]
    
    @pytest.mark.asyncio
    async def test_rbac_analytics(self, rbac_manager):
        """Test RBAC analytics functionality."""
        user_id = str(uuid.uuid4())
        
        # Assign some roles
        roles = await rbac_manager.list_roles()
        user_role = next(role for role in roles if role.name == "User")
        await rbac_manager.assign_role_to_user(user_id, user_role.role_id, "test_admin")
        
        # Get analytics
        analytics = await rbac_manager.get_rbac_analytics()
        
        # Verify analytics structure
        assert "roles" in analytics
        assert "assignments" in analytics
        assert "permissions" in analytics
        assert "cache" in analytics
        assert "audit" in analytics
        
        # Verify data
        assert analytics["roles"]["total"] > 0
        assert analytics["assignments"]["active"] > 0
        assert analytics["permissions"]["total_unique"] > 0


class TestPermissionMiddleware:
    """Test suite for Permission Middleware functionality."""
    
    @pytest.fixture
    def rbac_manager(self):
        """Create RBAC manager for middleware testing."""
        return RBACManager()
    
    @pytest.fixture
    def auth_service(self):
        """Create auth service for middleware testing."""
        config = {
            "bcrypt_rounds": 4,
            "jwt_secret": "test-secret",
            "jwt_algorithm": "HS256",
            "token_expiry_minutes": 15
        }
        return AuthenticationService(config)
    
    @pytest.fixture
    def permission_middleware(self, rbac_manager, auth_service):
        """Create permission middleware for testing."""
        return PermissionMiddleware(rbac_manager, auth_service)
    
    @pytest.mark.asyncio
    async def test_endpoint_permission_registration(self, permission_middleware):
        """Test registering endpoint permissions."""
        from security.permission_middleware import EndpointPermission
        
        endpoint_perm = EndpointPermission(
            endpoint="/api/test",
            method="GET",
            required_permissions=[PermissionType.READ_ONLY],
            description="Test endpoint"
        )
        
        success = permission_middleware.register_endpoint_permission(endpoint_perm)
        assert success
        
        # Verify registration
        key = "GET:/api/test"
        assert key in permission_middleware.endpoint_permissions
    
    @pytest.mark.asyncio
    async def test_permission_enforcement_success(self, permission_middleware, rbac_manager, auth_service):
        """Test successful permission enforcement."""
        # Create user and session
        user_id = str(uuid.uuid4())
        username = f"test_user_{user_id[:8]}"
        
        # Create user with proper role
        success, message, user = await auth_service.create_user(
            username=username,
            email=f"{username}@test.com",
            password="test_password",
            roles=[]
        )
        assert success
        
        # Assign public access role
        roles = await rbac_manager.list_roles()
        guest_role = next(role for role in roles if role.name == "Guest")
        await rbac_manager.assign_role_to_user(user.user_id, guest_role.role_id, "test_admin")
        
        # Create session
        session_success, session_message, session = await auth_service.authenticate_user(
            username=username,
            password="test_password",
            client_ip="127.0.0.1",
            user_agent="test_agent"
        )
        assert session_success
        
        # Create permission context for public endpoint
        context = PermissionContext(
            user_id=user.user_id,
            endpoint="/api/v1/health",
            method="GET",
            client_ip="127.0.0.1",
            user_agent="test_agent"
        )
        
        # Test permission enforcement
        result = await permission_middleware.enforce_permissions(context, session.access_token)
        
        assert result.allowed
        assert result.user_id == user.user_id
        assert result.response_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_permission_enforcement_denied(self, permission_middleware, rbac_manager, auth_service):
        """Test permission enforcement denial."""
        # Create user with limited role
        user_id = str(uuid.uuid4())
        username = f"test_user_{user_id[:8]}"
        
        success, message, user = await auth_service.create_user(
            username=username,
            email=f"{username}@test.com",
            password="test_password",
            roles=[]
        )
        assert success
        
        # Assign guest role (limited permissions)
        roles = await rbac_manager.list_roles()
        guest_role = next(role for role in roles if role.name == "Guest")
        await rbac_manager.assign_role_to_user(user.user_id, guest_role.role_id, "test_admin")
        
        # Create session
        session_success, session_message, session = await auth_service.authenticate_user(
            username=username,
            password="test_password",
            client_ip="127.0.0.1",
            user_agent="test_agent"
        )
        assert session_success
        
        # Create permission context for admin endpoint
        context = PermissionContext(
            user_id=user.user_id,
            endpoint="/api/v1/system/config",
            method="POST",
            client_ip="127.0.0.1",
            user_agent="test_agent"
        )
        
        # Test permission enforcement
        result = await permission_middleware.enforce_permissions(context, session.access_token)
        
        assert not result.allowed
        assert "insufficient_permissions" in result.reason.lower()
        assert len(result.permissions_denied) > 0
    
    @pytest.mark.asyncio
    async def test_bulk_permission_check(self, permission_middleware, rbac_manager):
        """Test bulk permission checking."""
        user_id = str(uuid.uuid4())
        
        # Assign admin role
        roles = await rbac_manager.list_roles()
        admin_role = next(role for role in roles if role.name == "Administrator")
        await rbac_manager.assign_role_to_user(user_id, admin_role.role_id, "test_admin")
        
        # Check multiple permissions
        permissions_to_check = [
            PermissionType.USER_MANAGEMENT,
            PermissionType.AGENT_MANAGEMENT,
            PermissionType.SYSTEM_ADMIN  # This should be denied
        ]
        
        results = await permission_middleware.check_bulk_permissions(user_id, permissions_to_check)
        
        assert results[PermissionType.USER_MANAGEMENT] == True
        assert results[PermissionType.AGENT_MANAGEMENT] == True
        assert results[PermissionType.SYSTEM_ADMIN] == False
    
    @pytest.mark.asyncio
    async def test_permission_analytics(self, permission_middleware):
        """Test permission analytics functionality."""
        # Simulate some permission checks by adding to the list
        from security.permission_middleware import PermissionResult
        
        # Add some mock results
        for i in range(5):
            result = PermissionResult(
                allowed=i % 2 == 0,  # Alternate allowed/denied
                user_id=f"user_{i}",
                endpoint=f"/api/test/{i}",
                method="GET",
                permissions_checked=[PermissionType.READ_ONLY],
                permissions_granted=[PermissionType.READ_ONLY] if i % 2 == 0 else [],
                permissions_denied=[] if i % 2 == 0 else [PermissionType.READ_ONLY],
                reason="test_reason",
                response_time_ms=10.5
            )
            permission_middleware.permission_checks.append(result)
        
        # Get analytics
        analytics = await permission_middleware.get_permission_analytics()
        
        # Verify analytics structure
        assert "total_checks" in analytics
        assert "access_stats" in analytics
        assert "performance" in analytics
        assert "endpoints" in analytics
        
        # Verify data
        assert analytics["access_stats"]["allowed"] > 0
        assert analytics["access_stats"]["denied"] > 0


class TestRBACIntegration:
    """Test suite for RBAC system integration."""
    
    @pytest.fixture
    def integrated_system(self):
        """Create integrated RBAC system for testing."""
        auth_config = {
            "bcrypt_rounds": 4,
            "jwt_secret": "test-secret",
            "jwt_algorithm": "HS256",
            "token_expiry_minutes": 15
        }
        
        rbac_manager = RBACManager()
        auth_service = AuthenticationService(auth_config)
        permission_middleware = PermissionMiddleware(rbac_manager, auth_service)
        
        return {
            "rbac_manager": rbac_manager,
            "auth_service": auth_service,
            "permission_middleware": permission_middleware
        }
    
    @pytest.mark.asyncio
    async def test_end_to_end_rbac_flow(self, integrated_system):
        """Test complete RBAC flow from user creation to permission checking."""
        rbac_manager = integrated_system["rbac_manager"]
        auth_service = integrated_system["auth_service"]
        permission_middleware = integrated_system["permission_middleware"]
        
        # 1. Create custom role
        success, message, custom_role = await rbac_manager.create_role(
            role_type=RoleType.USER,
            name="Test Manager",
            description="Custom role for testing",
            permissions=[PermissionType.TASK_CREATE, PermissionType.TASK_READ, PermissionType.API_READ]
        )
        assert success
        
        # 2. Create user with RBAC integration
        username = f"test_manager_{uuid.uuid4().hex[:8]}"
        success, message, user = await auth_service.create_user_with_rbac(
            username=username,
            email=f"{username}@test.com",
            password="secure_password",
            role_ids=[custom_role.role_id],
            rbac_manager=rbac_manager,
            created_by="system_admin"
        )
        assert success
        
        # 3. Authenticate with RBAC
        auth_success, auth_message, session, role_ids = await auth_service.authenticate_with_rbac(
            username=username,
            password="secure_password",
            client_ip="127.0.0.1",
            user_agent="test_browser",
            rbac_manager=rbac_manager
        )
        assert auth_success
        assert custom_role.role_id in role_ids
        
        # 4. Validate session with RBAC
        auth_result = await auth_service.validate_session_with_rbac(
            access_token=session.access_token,
            client_ip="127.0.0.1",
            rbac_manager=rbac_manager,
            required_permissions=[PermissionType.TASK_CREATE]
        )
        assert auth_result.success
        assert "rbac" in auth_result.metadata
        assert "Test Manager" in auth_result.metadata["rbac"]["roles"]
        
        # 5. Test permission enforcement
        context = PermissionContext(
            user_id=user.user_id,
            endpoint="/api/v1/tasks",
            method="POST",
            client_ip="127.0.0.1",
            user_agent="test_browser"
        )
        
        enforcement_result = await permission_middleware.enforce_permissions(
            context, session.access_token
        )
        assert enforcement_result.allowed
        
        # 6. Get comprehensive user summary
        user_summary = await auth_service.get_user_rbac_summary(
            user_id=user.user_id,
            rbac_manager=rbac_manager
        )
        assert "roles" in user_summary
        assert "permissions" in user_summary
        assert user_summary["rbac_summary"]["total_roles"] == 1
    
    @pytest.mark.asyncio
    async def test_role_assignment_performance(self, integrated_system):
        """Test performance of role assignments at scale."""
        rbac_manager = integrated_system["rbac_manager"]
        auth_service = integrated_system["auth_service"]
        
        # Create multiple users
        user_ids = []
        for i in range(10):
            username = f"perf_user_{i}_{uuid.uuid4().hex[:8]}"
            success, message, user = await auth_service.create_user(
                username=username,
                email=f"{username}@test.com",
                password="test_password",
                roles=[]
            )
            assert success
            user_ids.append(user.user_id)
        
        # Get available roles
        roles = await rbac_manager.list_roles()
        user_role = next(role for role in roles if role.name == "User")
        
        # Bulk assign roles
        user_role_mapping = {user_id: [user_role.role_id] for user_id in user_ids}
        
        start_time = datetime.utcnow()
        results = await auth_service.bulk_assign_roles(
            user_role_mapping=user_role_mapping,
            rbac_manager=rbac_manager,
            assigned_by="performance_test"
        )
        end_time = datetime.utcnow()
        
        # Verify performance
        duration = (end_time - start_time).total_seconds()
        assert duration < 1.0  # Should complete within 1 second
        assert results["successful_assignments"] == 10
        assert results["failed_assignments"] == 0
    
    @pytest.mark.asyncio
    async def test_permission_cache_performance(self, integrated_system):
        """Test permission checking performance with caching."""
        rbac_manager = integrated_system["rbac_manager"]
        auth_service = integrated_system["auth_service"]
        
        # Create user with role
        username = f"cache_user_{uuid.uuid4().hex[:8]}"
        success, message, user = await auth_service.create_user(
            username=username,
            email=f"{username}@test.com",
            password="test_password",
            roles=[]
        )
        assert success
        
        roles = await rbac_manager.list_roles()
        admin_role = next(role for role in roles if role.name == "Administrator")
        await rbac_manager.assign_role_to_user(user.user_id, admin_role.role_id, "test_admin")
        
        # First permission check (should be slower)
        start_time = datetime.utcnow()
        result1 = await rbac_manager.check_permission(user.user_id, PermissionType.USER_MANAGEMENT)
        first_duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Second permission check (should be faster due to caching)
        start_time = datetime.utcnow()
        result2 = await rbac_manager.check_permission(user.user_id, PermissionType.USER_MANAGEMENT)
        second_duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Both should succeed
        assert result1.granted
        assert result2.granted
        
        # Second check should be faster (cache hit)
        # Note: This test might be flaky on very fast systems
        assert second_duration <= first_duration or second_duration < 0.001


class TestRBACSecurityValidation:
    """Test suite for RBAC security validation."""
    
    @pytest.fixture
    def rbac_manager(self):
        """Create RBAC manager for security testing."""
        return RBACManager()
    
    @pytest.mark.asyncio
    async def test_privilege_escalation_prevention(self, rbac_manager):
        """Test that users cannot escalate their privileges."""
        user_id = str(uuid.uuid4())
        
        # Assign user role (low privilege)
        roles = await rbac_manager.list_roles()
        user_role = next(role for role in roles if role.name == "User")
        await rbac_manager.assign_role_to_user(user_id, user_role.role_id, "test_admin")
        
        # Verify user cannot get admin permissions
        admin_check = await rbac_manager.check_permission(user_id, PermissionType.SYSTEM_ADMIN)
        assert not admin_check.granted
        
        user_mgmt_check = await rbac_manager.check_permission(user_id, PermissionType.USER_MANAGEMENT)
        assert not user_mgmt_check.granted
        
        # Verify user only has their assigned permissions
        user_permissions = await rbac_manager.get_user_permissions(user_id)
        admin_permissions = [PermissionType.SYSTEM_ADMIN, PermissionType.USER_MANAGEMENT]
        
        for admin_perm in admin_permissions:
            assert admin_perm not in user_permissions
    
    @pytest.mark.asyncio
    async def test_role_assignment_authorization(self, rbac_manager):
        """Test that role assignments are properly authorized."""
        user_id = str(uuid.uuid4())
        
        # Test that non-existent role assignment fails
        success, message = await rbac_manager.assign_role_to_user(
            user_id=user_id,
            role_id="non_existent_role",
            assigned_by="test_admin"
        )
        assert not success
        assert "does not exist" in message
        
        # Test that duplicate assignment fails
        roles = await rbac_manager.list_roles()
        user_role = next(role for role in roles if role.name == "User")
        
        # First assignment should succeed
        success, message = await rbac_manager.assign_role_to_user(
            user_id=user_id,
            role_id=user_role.role_id,
            assigned_by="test_admin"
        )
        assert success
        
        # Duplicate assignment should fail
        success, message = await rbac_manager.assign_role_to_user(
            user_id=user_id,
            role_id=user_role.role_id,
            assigned_by="test_admin"
        )
        assert not success
    
    @pytest.mark.asyncio
    async def test_audit_trail_integrity(self, rbac_manager):
        """Test that audit trail is properly maintained."""
        initial_audit_count = len(rbac_manager.audit_log)
        
        # Perform auditable actions
        success, message, role = await rbac_manager.create_role(
            role_type=RoleType.USER,
            name="Audit Test Role",
            description="Role for audit testing",
            permissions=[PermissionType.READ_ONLY]
        )
        assert success
        
        user_id = str(uuid.uuid4())
        await rbac_manager.assign_role_to_user(user_id, role.role_id, "audit_test")
        await rbac_manager.revoke_role_from_user(user_id, role.role_id, "audit_test")
        
        # Verify audit events were logged
        final_audit_count = len(rbac_manager.audit_log)
        assert final_audit_count > initial_audit_count
        
        # Verify audit event structure
        recent_events = rbac_manager.audit_log[-3:]  # Last 3 events
        event_types = [event["action"] for event in recent_events]
        
        assert "role_created" in event_types
        assert "role_assigned" in event_types
        assert "role_revoked" in event_types
        
        # Verify audit events have required fields
        for event in recent_events:
            assert "event_id" in event
            assert "timestamp" in event
            assert "component" in event
            assert event["component"] == "rbac_manager"


if __name__ == "__main__":
    # Run specific test groups
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--durations=10"
    ])