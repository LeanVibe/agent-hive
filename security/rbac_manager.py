#!/usr/bin/env python3
"""
Role-Based Access Control (RBAC) Manager

Enterprise-grade RBAC system with hierarchical roles, permission inheritance,
dynamic permission calculation, and comprehensive audit capabilities.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

from config.auth_models import Permission, AuthResult
# Import will be handled in the auth integration methods


logger = logging.getLogger(__name__)


class PermissionType(Enum):
    """System permission types with hierarchical structure."""
    # System Administration (highest level)
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITORING = "system:monitoring"
    
    # User Management
    USER_MANAGEMENT = "user:management"
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # Agent Management
    AGENT_MANAGEMENT = "agent:management"
    AGENT_SPAWN = "agent:spawn"
    AGENT_CONTROL = "agent:control"
    AGENT_MONITOR = "agent:monitor"
    AGENT_TERMINATE = "agent:terminate"
    
    # Task Execution
    TASK_EXECUTION = "task:execution"
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    
    # API Access
    API_GATEWAY = "api:gateway"
    API_ADMIN = "api:admin"
    API_READ = "api:read"
    API_WRITE = "api:write"
    
    # Public Access
    PUBLIC_ACCESS = "public:access"
    READ_ONLY = "read:only"


class RoleType(Enum):
    """Enhanced role types with clear hierarchy."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    AGENT = "agent"
    USER = "user"
    GUEST = "guest"


@dataclass
class RoleDefinition:
    """Comprehensive role definition with inheritance."""
    role_id: str
    role_type: RoleType
    name: str
    description: str
    permissions: Set[PermissionType]
    inherits_from: Optional[List[str]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.inherits_from is None:
            self.inherits_from = []


@dataclass
class UserRoleAssignment:
    """User role assignment with context and constraints."""
    assignment_id: str
    user_id: str
    role_id: str
    assigned_by: str
    assigned_at: datetime
    expires_at: Optional[datetime] = None
    context_constraints: Dict[str, Any] = field(default_factory=dict)
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PermissionCheck:
    """Permission check result with detailed context."""
    user_id: str
    permission: PermissionType
    granted: bool
    reason: str
    role_sources: List[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RBACManager:
    """
    Enterprise-grade Role-Based Access Control Manager.
    
    Features:
    - Hierarchical role inheritance
    - Dynamic permission calculation
    - Context-aware permission evaluation
    - Comprehensive audit logging
    - Permission caching for performance
    - Role lifecycle management
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize RBAC Manager."""
        self.config = config or {}
        
        # Storage for roles and assignments
        self.roles: Dict[str, RoleDefinition] = {}
        self.user_assignments: Dict[str, List[UserRoleAssignment]] = defaultdict(list)
        self.permission_cache: Dict[str, Dict[PermissionType, bool]] = {}
        self.audit_log: List[Dict[str, Any]] = []
        
        # Performance settings
        self.cache_ttl = self.config.get("cache_ttl_seconds", 300)  # 5 minutes
        self.cache_timestamps: Dict[str, datetime] = {}
        
        # Initialize default roles
        self._initialize_default_roles()
        
        logger.info("RBACManager initialized with hierarchical permissions")
    
    def _initialize_default_roles(self) -> None:
        """Initialize default system roles with proper hierarchy."""
        # Super Admin - Full system access
        super_admin_role = RoleDefinition(
            role_id="super_admin",
            role_type=RoleType.SUPER_ADMIN,
            name="Super Administrator",
            description="Full system access with all permissions",
            permissions={
                PermissionType.SYSTEM_ADMIN,
                PermissionType.SYSTEM_CONFIG,
                PermissionType.SYSTEM_MONITORING,
                PermissionType.USER_MANAGEMENT,
                PermissionType.AGENT_MANAGEMENT,
                PermissionType.TASK_EXECUTION,
                PermissionType.API_ADMIN,
                PermissionType.API_GATEWAY
            }
        )
        
        # Admin - System management without config changes
        admin_role = RoleDefinition(
            role_id="admin",
            role_type=RoleType.ADMIN,
            name="Administrator",
            description="System administration with user and agent management",
            permissions={
                PermissionType.USER_MANAGEMENT,
                PermissionType.USER_CREATE,
                PermissionType.USER_READ,
                PermissionType.USER_UPDATE,
                PermissionType.AGENT_MANAGEMENT,
                PermissionType.AGENT_SPAWN,
                PermissionType.AGENT_CONTROL,
                PermissionType.AGENT_MONITOR,
                PermissionType.TASK_EXECUTION,
                PermissionType.API_WRITE,
                PermissionType.API_READ
            }
        )
        
        # Agent - Task execution and limited system access
        agent_role = RoleDefinition(
            role_id="agent",
            role_type=RoleType.AGENT,
            name="Agent",
            description="Autonomous agent with task execution capabilities",
            permissions={
                PermissionType.TASK_EXECUTION,
                PermissionType.TASK_CREATE,
                PermissionType.TASK_READ,
                PermissionType.TASK_UPDATE,
                PermissionType.AGENT_MONITOR,
                PermissionType.API_WRITE,
                PermissionType.API_READ
            }
        )
        
        # User - Basic access with read/write permissions
        user_role = RoleDefinition(
            role_id="user",
            role_type=RoleType.USER,
            name="User",
            description="Standard user with basic access permissions",
            permissions={
                PermissionType.TASK_READ,
                PermissionType.TASK_CREATE,
                PermissionType.API_READ,
                PermissionType.READ_ONLY,
                PermissionType.PUBLIC_ACCESS
            }
        )
        
        # Guest - Minimal read-only access
        guest_role = RoleDefinition(
            role_id="guest",
            role_type=RoleType.GUEST,
            name="Guest",
            description="Limited read-only access to public resources",
            permissions={
                PermissionType.PUBLIC_ACCESS,
                PermissionType.READ_ONLY
            }
        )
        
        # Store default roles
        for role in [super_admin_role, admin_role, agent_role, user_role, guest_role]:
            self.roles[role.role_id] = role
        
        logger.info(f"Initialized {len(self.roles)} default roles")
    
    async def create_role(self, role_type: RoleType, name: str, description: str,
                         permissions: List[PermissionType], 
                         inherits_from: Optional[List[str]] = None,
                         created_by: str = "system") -> Tuple[bool, str, Optional[RoleDefinition]]:
        """
        Create a new role with permissions and inheritance.
        
        Returns:
            Tuple of (success, message, role_object)
        """
        try:
            # Validate inputs
            if not name or not description:
                return False, "Role name and description are required", None
            
            # Check for duplicate names
            for role in self.roles.values():
                if role.name == name and role.active:
                    return False, f"Role with name '{name}' already exists", None
            
            # Validate inheritance
            if inherits_from:
                for parent_role_id in inherits_from:
                    if parent_role_id not in self.roles:
                        return False, f"Parent role '{parent_role_id}' does not exist", None
            
            # Validate permissions
            for permission in permissions:
                if not isinstance(permission, PermissionType):
                    return False, f"Invalid permission type: {permission}", None
            
            # Create role
            role_id = str(uuid.uuid4())
            role = RoleDefinition(
                role_id=role_id,
                role_type=role_type,
                name=name,
                description=description,
                permissions=set(permissions),
                inherits_from=inherits_from or [],
                created_by=created_by
            )
            
            # Store role
            self.roles[role_id] = role
            
            # Clear permission cache since role structure changed
            await self._clear_permission_cache()
            
            # Log audit event
            await self._log_audit_event({
                "action": "role_created",
                "role_id": role_id,
                "role_name": name,
                "role_type": role_type.value,
                "permissions_count": len(permissions),
                "created_by": created_by,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Created role: {name} ({role_id})")
            return True, "Role created successfully", role
            
        except Exception as e:
            logger.error(f"Failed to create role {name}: {e}")
            return False, f"Failed to create role: {e}", None
    
    async def assign_role_to_user(self, user_id: str, role_id: str, assigned_by: str,
                                 expires_at: Optional[datetime] = None,
                                 context_constraints: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        Assign role to user with optional constraints and expiration.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate role exists
            if role_id not in self.roles:
                return False, f"Role '{role_id}' does not exist"
            
            role = self.roles[role_id]
            if not role.active:
                return False, f"Role '{role_id}' is not active"
            
            # Check if user already has this role
            for assignment in self.user_assignments[user_id]:
                if (assignment.role_id == role_id and 
                    assignment.active and
                    (not assignment.expires_at or assignment.expires_at > datetime.utcnow())):
                    return False, f"User already has active role '{role.name}'"
            
            # Create assignment
            assignment_id = str(uuid.uuid4())
            assignment = UserRoleAssignment(
                assignment_id=assignment_id,
                user_id=user_id,
                role_id=role_id,
                assigned_by=assigned_by,
                assigned_at=datetime.utcnow(),
                expires_at=expires_at,
                context_constraints=context_constraints or {}
            )
            
            # Store assignment
            self.user_assignments[user_id].append(assignment)
            
            # Clear user's permission cache
            await self._clear_user_permission_cache(user_id)
            
            # Log audit event
            await self._log_audit_event({
                "action": "role_assigned",
                "user_id": user_id,
                "role_id": role_id,
                "role_name": role.name,
                "assigned_by": assigned_by,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Assigned role '{role.name}' to user {user_id}")
            return True, f"Role '{role.name}' assigned successfully"
            
        except Exception as e:
            logger.error(f"Failed to assign role {role_id} to user {user_id}: {e}")
            return False, f"Failed to assign role: {e}"
    
    async def revoke_role_from_user(self, user_id: str, role_id: str, revoked_by: str) -> Tuple[bool, str]:
        """
        Revoke role from user.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Find active assignment
            assignment_found = False
            for assignment in self.user_assignments[user_id]:
                if (assignment.role_id == role_id and 
                    assignment.active and
                    (not assignment.expires_at or assignment.expires_at > datetime.utcnow())):
                    
                    assignment.active = False
                    assignment_found = True
                    break
            
            if not assignment_found:
                return False, f"User does not have active role '{role_id}'"
            
            role = self.roles.get(role_id)
            role_name = role.name if role else role_id
            
            # Clear user's permission cache
            await self._clear_user_permission_cache(user_id)
            
            # Log audit event
            await self._log_audit_event({
                "action": "role_revoked",
                "user_id": user_id,
                "role_id": role_id,
                "role_name": role_name,
                "revoked_by": revoked_by,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Revoked role '{role_name}' from user {user_id}")
            return True, f"Role '{role_name}' revoked successfully"
            
        except Exception as e:
            logger.error(f"Failed to revoke role {role_id} from user {user_id}: {e}")
            return False, f"Failed to revoke role: {e}"
    
    async def check_permission(self, user_id: str, permission: PermissionType,
                              context: Optional[Dict[str, Any]] = None) -> PermissionCheck:
        """
        Check if user has specific permission with detailed result.
        
        Args:
            user_id: User identifier
            permission: Permission to check
            context: Optional context for context-aware permissions
            
        Returns:
            PermissionCheck object with detailed result
        """
        try:
            # Check cache first
            if await self._is_permission_cached(user_id, permission):
                cached_result = self.permission_cache[user_id][permission]
                return PermissionCheck(
                    user_id=user_id,
                    permission=permission,
                    granted=cached_result,
                    reason="cached_result",
                    metadata={"source": "cache"}
                )
            
            # Get user's effective permissions
            effective_permissions, role_sources = await self._get_user_effective_permissions(user_id)
            
            # Check if user has the specific permission
            has_permission = permission in effective_permissions
            
            # Determine reason
            if has_permission:
                reason = f"granted_via_roles: {', '.join(role_sources)}"
            else:
                reason = "permission_not_found_in_user_roles"
            
            # Create result
            result = PermissionCheck(
                user_id=user_id,
                permission=permission,
                granted=has_permission,
                reason=reason,
                role_sources=role_sources,
                metadata={
                    "total_permissions": len(effective_permissions),
                    "total_roles": len(role_sources),
                    "context_applied": context is not None
                }
            )
            
            # Cache result
            await self._cache_permission_result(user_id, permission, has_permission)
            
            return result
            
        except Exception as e:
            logger.error(f"Permission check failed for user {user_id}, permission {permission}: {e}")
            return PermissionCheck(
                user_id=user_id,
                permission=permission,
                granted=False,
                reason=f"error: {e}",
                metadata={"error": str(e)}
            )
    
    async def get_user_roles(self, user_id: str, include_expired: bool = False) -> List[RoleDefinition]:
        """Get all roles assigned to a user."""
        user_roles = []
        current_time = datetime.utcnow()
        
        for assignment in self.user_assignments[user_id]:
            if not assignment.active:
                continue
                
            # Check expiration
            if (not include_expired and 
                assignment.expires_at and 
                assignment.expires_at <= current_time):
                continue
            
            role = self.roles.get(assignment.role_id)
            if role and role.active:
                user_roles.append(role)
        
        return user_roles
    
    async def get_user_permissions(self, user_id: str) -> Set[PermissionType]:
        """Get all effective permissions for a user."""
        effective_permissions, _ = await self._get_user_effective_permissions(user_id)
        return effective_permissions
    
    async def list_roles(self, active_only: bool = True) -> List[RoleDefinition]:
        """List all roles in the system."""
        if active_only:
            return [role for role in self.roles.values() if role.active]
        return list(self.roles.values())
    
    async def get_role(self, role_id: str) -> Optional[RoleDefinition]:
        """Get role by ID."""
        return self.roles.get(role_id)
    
    async def update_role(self, role_id: str, updates: Dict[str, Any], updated_by: str) -> Tuple[bool, str]:
        """
        Update role definition.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            if role_id not in self.roles:
                return False, f"Role '{role_id}' does not exist"
            
            role = self.roles[role_id]
            old_data = {
                "name": role.name,
                "description": role.description,
                "permissions": list(role.permissions)
            }
            
            # Update fields
            if "name" in updates:
                role.name = updates["name"]
            if "description" in updates:
                role.description = updates["description"]
            if "permissions" in updates:
                role.permissions = set(updates["permissions"])
            if "active" in updates:
                role.active = updates["active"]
            
            role.updated_at = datetime.utcnow()
            
            # Clear permission cache since role changed
            await self._clear_permission_cache()
            
            # Log audit event
            await self._log_audit_event({
                "action": "role_updated",
                "role_id": role_id,
                "role_name": role.name,
                "old_data": old_data,
                "updates": updates,
                "updated_by": updated_by,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Updated role: {role.name} ({role_id})")
            return True, "Role updated successfully"
            
        except Exception as e:
            logger.error(f"Failed to update role {role_id}: {e}")
            return False, f"Failed to update role: {e}"
    
    async def delete_role(self, role_id: str, deleted_by: str, force: bool = False) -> Tuple[bool, str]:
        """
        Delete role (soft delete by default).
        
        Returns:
            Tuple of (success, message)
        """
        try:
            if role_id not in self.roles:
                return False, f"Role '{role_id}' does not exist"
            
            role = self.roles[role_id]
            
            # Check if role is in use
            users_with_role = []
            for user_id, assignments in self.user_assignments.items():
                for assignment in assignments:
                    if (assignment.role_id == role_id and 
                        assignment.active and
                        (not assignment.expires_at or assignment.expires_at > datetime.utcnow())):
                        users_with_role.append(user_id)
                        break
            
            if users_with_role and not force:
                return False, f"Role is assigned to {len(users_with_role)} users. Use force=True to delete anyway."
            
            if force:
                # Revoke role from all users
                for user_id in users_with_role:
                    await self.revoke_role_from_user(user_id, role_id, deleted_by)
            
            # Soft delete
            role.active = False
            role.updated_at = datetime.utcnow()
            
            # Clear permission cache
            await self._clear_permission_cache()
            
            # Log audit event
            await self._log_audit_event({
                "action": "role_deleted",
                "role_id": role_id,
                "role_name": role.name,
                "users_affected": len(users_with_role),
                "force_delete": force,
                "deleted_by": deleted_by,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Deleted role: {role.name} ({role_id})")
            return True, "Role deleted successfully"
            
        except Exception as e:
            logger.error(f"Failed to delete role {role_id}: {e}")
            return False, f"Failed to delete role: {e}"
    
    async def get_rbac_analytics(self) -> Dict[str, Any]:
        """Get comprehensive RBAC analytics."""
        total_roles = len(self.roles)
        active_roles = sum(1 for role in self.roles.values() if role.active)
        total_assignments = sum(len(assignments) for assignments in self.user_assignments.values())
        active_assignments = 0
        current_time = datetime.utcnow()
        
        # Count active assignments
        for assignments in self.user_assignments.values():
            for assignment in assignments:
                if (assignment.active and
                    (not assignment.expires_at or assignment.expires_at > current_time)):
                    active_assignments += 1
        
        # Role distribution
        role_distribution = defaultdict(int)
        for role in self.roles.values():
            if role.active:
                role_distribution[role.role_type.value] += 1
        
        # Permission distribution
        permission_usage = defaultdict(int)
        for role in self.roles.values():
            if role.active:
                for permission in role.permissions:
                    permission_usage[permission.value] += 1
        
        # User distribution
        users_with_roles = len([user_id for user_id, assignments in self.user_assignments.items() 
                               if any(a.active for a in assignments)])
        
        return {
            "roles": {
                "total": total_roles,
                "active": active_roles,
                "by_type": dict(role_distribution)
            },
            "assignments": {
                "total": total_assignments,
                "active": active_assignments,
                "users_with_roles": users_with_roles
            },
            "permissions": {
                "total_unique": len(PermissionType),
                "usage_by_permission": dict(permission_usage)
            },
            "cache": {
                "cached_users": len(self.permission_cache),
                "cache_hit_potential": f"{len(self.permission_cache) * len(PermissionType)} checks"
            },
            "audit": {
                "total_events": len(self.audit_log)
            }
        }
    
    # Private helper methods
    
    async def _get_user_effective_permissions(self, user_id: str) -> Tuple[Set[PermissionType], List[str]]:
        """Get all effective permissions for user with role sources."""
        effective_permissions = set()
        role_sources = []
        current_time = datetime.utcnow()
        
        # Get user's active role assignments
        for assignment in self.user_assignments[user_id]:
            if not assignment.active:
                continue
                
            # Check expiration
            if assignment.expires_at and assignment.expires_at <= current_time:
                continue
            
            role = self.roles.get(assignment.role_id)
            if not role or not role.active:
                continue
            
            # Add role permissions
            role_permissions = await self._get_role_effective_permissions(role.role_id)
            effective_permissions.update(role_permissions)
            role_sources.append(role.name)
        
        return effective_permissions, role_sources
    
    async def _get_role_effective_permissions(self, role_id: str) -> Set[PermissionType]:
        """Get effective permissions for role including inherited permissions."""
        if role_id not in self.roles:
            return set()
        
        role = self.roles[role_id]
        effective_permissions = set(role.permissions)
        
        # Add inherited permissions
        for parent_role_id in role.inherits_from:
            parent_permissions = await self._get_role_effective_permissions(parent_role_id)
            effective_permissions.update(parent_permissions)
        
        return effective_permissions
    
    async def _is_permission_cached(self, user_id: str, permission: PermissionType) -> bool:
        """Check if permission result is cached and valid."""
        if user_id not in self.permission_cache:
            return False
        
        if permission not in self.permission_cache[user_id]:
            return False
        
        # Check cache expiration
        cache_time = self.cache_timestamps.get(f"{user_id}:{permission.value}")
        if not cache_time:
            return False
        
        return (datetime.utcnow() - cache_time).total_seconds() < self.cache_ttl
    
    async def _cache_permission_result(self, user_id: str, permission: PermissionType, result: bool) -> None:
        """Cache permission check result."""
        if user_id not in self.permission_cache:
            self.permission_cache[user_id] = {}
        
        self.permission_cache[user_id][permission] = result
        self.cache_timestamps[f"{user_id}:{permission.value}"] = datetime.utcnow()
    
    async def _clear_permission_cache(self) -> None:
        """Clear all permission cache."""
        self.permission_cache.clear()
        self.cache_timestamps.clear()
        logger.debug("Cleared all permission cache")
    
    async def _clear_user_permission_cache(self, user_id: str) -> None:
        """Clear permission cache for specific user."""
        if user_id in self.permission_cache:
            del self.permission_cache[user_id]
        
        # Clear timestamp cache for user
        keys_to_remove = [key for key in self.cache_timestamps.keys() if key.startswith(f"{user_id}:")]
        for key in keys_to_remove:
            del self.cache_timestamps[key]
        
        logger.debug(f"Cleared permission cache for user {user_id}")
    
    async def _log_audit_event(self, event: Dict[str, Any]) -> None:
        """Log RBAC audit event."""
        event["event_id"] = str(uuid.uuid4())
        event["component"] = "rbac_manager"
        self.audit_log.append(event)
        
        # Keep only last 10000 events to prevent memory issues
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-5000:]
        
        logger.debug(f"RBAC audit event: {event['action']}")