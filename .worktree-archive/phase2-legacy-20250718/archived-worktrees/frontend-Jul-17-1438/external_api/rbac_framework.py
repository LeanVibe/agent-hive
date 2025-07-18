"""
RBAC Framework with Hierarchical Roles and Dynamic Authorization

Provides comprehensive Role-Based Access Control (RBAC) system with:
- Hierarchical role inheritance
- Granular permission matrix
- Dynamic authorization evaluation
- Resource-based access control
- Performance-optimized caching
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
import hashlib

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of resources that can be protected."""
    API_ENDPOINT = "api_endpoint"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    SERVICE = "service"
    AGENT = "agent"
    WORKFLOW = "workflow"
    MONITORING = "monitoring"
    CONFIGURATION = "configuration"


class ActionType(Enum):
    """Types of actions that can be performed on resources."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"
    CONFIGURE = "configure"
    MONITOR = "monitor"
    DEPLOY = "deploy"
    SCALE = "scale"


class PermissionScope(Enum):
    """Scope of permission application."""
    GLOBAL = "global"
    ORGANIZATION = "organization"
    PROJECT = "project"
    RESOURCE = "resource"
    INSTANCE = "instance"


@dataclass
class Permission:
    """Represents a specific permission with scope and constraints."""
    
    resource_type: ResourceType
    action: ActionType
    scope: PermissionScope
    resource_id: Optional[str] = None
    conditions: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        self.id = f"{self.resource_type.value}:{self.action.value}:{self.scope.value}:{self.resource_id or '*'}"
    
    def is_valid(self) -> bool:
        """Check if permission is still valid."""
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True
    
    def matches_request(self, resource_type: ResourceType, action: ActionType, 
                       resource_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if this permission matches a request."""
        if not self.is_valid():
            return False
        
        # Check resource type
        if self.resource_type != resource_type:
            return False
        
        # Check action
        if self.action != action:
            return False
        
        # Check resource ID (wildcard or exact match)
        if self.resource_id and self.resource_id != "*" and self.resource_id != resource_id:
            return False
        
        # Check conditions
        if context and self.conditions:
            for condition_key, condition_value in self.conditions.items():
                if condition_key not in context or context[condition_key] != condition_value:
                    return False
        
        return True


@dataclass
class Role:
    """Represents a role with hierarchical inheritance."""
    
    name: str
    description: str
    permissions: List[Permission] = field(default_factory=list)
    parent_roles: List[str] = field(default_factory=list)
    child_roles: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    
    def __post_init__(self):
        self.id = f"role:{self.name}"
    
    def add_permission(self, permission: Permission) -> None:
        """Add a permission to this role."""
        if permission not in self.permissions:
            self.permissions.append(permission)
            self.updated_at = datetime.now()
    
    def remove_permission(self, permission: Permission) -> None:
        """Remove a permission from this role."""
        if permission in self.permissions:
            self.permissions.remove(permission)
            self.updated_at = datetime.now()
    
    def has_permission(self, resource_type: ResourceType, action: ActionType, 
                      resource_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if role has a specific permission."""
        for permission in self.permissions:
            if permission.matches_request(resource_type, action, resource_id, context):
                return True
        return False


@dataclass
class User:
    """Represents a user with assigned roles."""
    
    user_id: str
    roles: List[str] = field(default_factory=list)
    direct_permissions: List[Permission] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    
    def assign_role(self, role_name: str) -> None:
        """Assign a role to this user."""
        if role_name not in self.roles:
            self.roles.append(role_name)
            self.updated_at = datetime.now()
    
    def remove_role(self, role_name: str) -> None:
        """Remove a role from this user."""
        if role_name in self.roles:
            self.roles.remove(role_name)
            self.updated_at = datetime.now()
    
    def add_direct_permission(self, permission: Permission) -> None:
        """Add a direct permission to this user."""
        if permission not in self.direct_permissions:
            self.direct_permissions.append(permission)
            self.updated_at = datetime.now()


class AuthorizationEvaluator:
    """Evaluates authorization requests with caching and performance optimization."""
    
    def __init__(self, cache_ttl: int = 300):
        self.cache_ttl = cache_ttl
        self.permission_cache: Dict[str, Tuple[bool, float]] = {}
        self.role_hierarchy_cache: Dict[str, Set[str]] = {}
        
    def evaluate_permission(self, user: User, roles: Dict[str, Role], 
                           resource_type: ResourceType, action: ActionType,
                           resource_id: Optional[str] = None, 
                           context: Optional[Dict[str, Any]] = None) -> bool:
        """Evaluate if user has permission for the requested action."""
        
        # Generate cache key
        cache_key = self._generate_cache_key(user.user_id, resource_type, action, resource_id, context)
        
        # Check cache
        if cache_key in self.permission_cache:
            result, timestamp = self.permission_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return result
        
        # Evaluate permission
        result = self._evaluate_permission_uncached(user, roles, resource_type, action, resource_id, context)
        
        # Cache result
        self.permission_cache[cache_key] = (result, time.time())
        
        return result
    
    def _evaluate_permission_uncached(self, user: User, roles: Dict[str, Role], 
                                     resource_type: ResourceType, action: ActionType,
                                     resource_id: Optional[str] = None, 
                                     context: Optional[Dict[str, Any]] = None) -> bool:
        """Evaluate permission without caching."""
        
        if not user.is_active:
            return False
        
        # Check direct permissions first
        for permission in user.direct_permissions:
            if permission.matches_request(resource_type, action, resource_id, context):
                return True
        
        # Check role-based permissions with hierarchy
        all_roles = self._get_all_user_roles(user, roles)
        
        for role_name in all_roles:
            if role_name not in roles:
                continue
                
            role = roles[role_name]
            if not role.is_active:
                continue
                
            if role.has_permission(resource_type, action, resource_id, context):
                return True
        
        return False
    
    def _get_all_user_roles(self, user: User, roles: Dict[str, Role]) -> Set[str]:
        """Get all roles for a user including inherited roles."""
        all_roles = set()
        
        for role_name in user.roles:
            all_roles.update(self._get_role_hierarchy(role_name, roles))
        
        return all_roles
    
    def _get_role_hierarchy(self, role_name: str, roles: Dict[str, Role]) -> Set[str]:
        """Get all roles in the hierarchy for a given role."""
        if role_name in self.role_hierarchy_cache:
            return self.role_hierarchy_cache[role_name]
        
        hierarchy = set()
        visited = set()
        
        def traverse(current_role: str):
            if current_role in visited or current_role not in roles:
                return
            
            visited.add(current_role)
            hierarchy.add(current_role)
            
            role = roles[current_role]
            for parent_role in role.parent_roles:
                traverse(parent_role)
        
        traverse(role_name)
        self.role_hierarchy_cache[role_name] = hierarchy
        return hierarchy
    
    def _generate_cache_key(self, user_id: str, resource_type: ResourceType, 
                           action: ActionType, resource_id: Optional[str] = None,
                           context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a cache key for permission evaluation."""
        key_parts = [user_id, resource_type.value, action.value, resource_id or ""]
        if context:
            context_str = json.dumps(context, sort_keys=True)
            key_parts.append(hashlib.md5(context_str.encode()).hexdigest())
        return ":".join(key_parts)
    
    def clear_cache(self) -> None:
        """Clear all caches."""
        self.permission_cache.clear()
        self.role_hierarchy_cache.clear()
    
    def clear_user_cache(self, user_id: str) -> None:
        """Clear cache for a specific user."""
        keys_to_remove = [key for key in self.permission_cache.keys() if key.startswith(user_id)]
        for key in keys_to_remove:
            del self.permission_cache[key]


class RBACManager:
    """Main RBAC manager with comprehensive role and permission management."""
    
    def __init__(self, redis_client=None):
        self.users: Dict[str, User] = {}
        self.roles: Dict[str, Role] = {}
        self.evaluator = AuthorizationEvaluator()
        self.redis_client = redis_client
        self.audit_log: List[Dict[str, Any]] = []
        
        # Initialize system roles
        self._initialize_system_roles()
    
    def _initialize_system_roles(self) -> None:
        """Initialize default system roles."""
        
        # Super Admin Role
        super_admin = Role(
            name="super_admin",
            description="Super administrator with all permissions",
            permissions=[
                Permission(ResourceType.API_ENDPOINT, ActionType.ADMIN, PermissionScope.GLOBAL),
                Permission(ResourceType.DATABASE, ActionType.ADMIN, PermissionScope.GLOBAL),
                Permission(ResourceType.FILE_SYSTEM, ActionType.ADMIN, PermissionScope.GLOBAL),
                Permission(ResourceType.SERVICE, ActionType.ADMIN, PermissionScope.GLOBAL),
                Permission(ResourceType.AGENT, ActionType.ADMIN, PermissionScope.GLOBAL),
                Permission(ResourceType.WORKFLOW, ActionType.ADMIN, PermissionScope.GLOBAL),
                Permission(ResourceType.MONITORING, ActionType.ADMIN, PermissionScope.GLOBAL),
                Permission(ResourceType.CONFIGURATION, ActionType.ADMIN, PermissionScope.GLOBAL),
            ]
        )
        
        # Admin Role
        admin = Role(
            name="admin",
            description="Administrator with most permissions",
            permissions=[
                Permission(ResourceType.API_ENDPOINT, ActionType.READ, PermissionScope.GLOBAL),
                Permission(ResourceType.API_ENDPOINT, ActionType.UPDATE, PermissionScope.GLOBAL),
                Permission(ResourceType.API_ENDPOINT, ActionType.CREATE, PermissionScope.GLOBAL),
                Permission(ResourceType.DATABASE, ActionType.READ, PermissionScope.GLOBAL),
                Permission(ResourceType.DATABASE, ActionType.UPDATE, PermissionScope.GLOBAL),
                Permission(ResourceType.SERVICE, ActionType.READ, PermissionScope.GLOBAL),
                Permission(ResourceType.SERVICE, ActionType.CONFIGURE, PermissionScope.GLOBAL),
                Permission(ResourceType.AGENT, ActionType.READ, PermissionScope.GLOBAL),
                Permission(ResourceType.AGENT, ActionType.EXECUTE, PermissionScope.GLOBAL),
                Permission(ResourceType.MONITORING, ActionType.READ, PermissionScope.GLOBAL),
            ]
        )
        
        # Developer Role
        developer = Role(
            name="developer",
            description="Developer with development permissions",
            permissions=[
                Permission(ResourceType.API_ENDPOINT, ActionType.READ, PermissionScope.PROJECT),
                Permission(ResourceType.API_ENDPOINT, ActionType.UPDATE, PermissionScope.PROJECT),
                Permission(ResourceType.DATABASE, ActionType.READ, PermissionScope.PROJECT),
                Permission(ResourceType.SERVICE, ActionType.READ, PermissionScope.PROJECT),
                Permission(ResourceType.AGENT, ActionType.READ, PermissionScope.PROJECT),
                Permission(ResourceType.AGENT, ActionType.EXECUTE, PermissionScope.PROJECT),
                Permission(ResourceType.WORKFLOW, ActionType.READ, PermissionScope.PROJECT),
                Permission(ResourceType.WORKFLOW, ActionType.UPDATE, PermissionScope.PROJECT),
            ]
        )
        
        # Operator Role
        operator = Role(
            name="operator",
            description="Operations team with deployment and monitoring permissions",
            permissions=[
                Permission(ResourceType.SERVICE, ActionType.DEPLOY, PermissionScope.GLOBAL),
                Permission(ResourceType.SERVICE, ActionType.SCALE, PermissionScope.GLOBAL),
                Permission(ResourceType.MONITORING, ActionType.READ, PermissionScope.GLOBAL),
                Permission(ResourceType.MONITORING, ActionType.CONFIGURE, PermissionScope.GLOBAL),
                Permission(ResourceType.CONFIGURATION, ActionType.READ, PermissionScope.GLOBAL),
                Permission(ResourceType.CONFIGURATION, ActionType.UPDATE, PermissionScope.GLOBAL),
            ]
        )
        
        # Viewer Role
        viewer = Role(
            name="viewer",
            description="Read-only access to most resources",
            permissions=[
                Permission(ResourceType.API_ENDPOINT, ActionType.READ, PermissionScope.PROJECT),
                Permission(ResourceType.DATABASE, ActionType.READ, PermissionScope.PROJECT),
                Permission(ResourceType.SERVICE, ActionType.READ, PermissionScope.PROJECT),
                Permission(ResourceType.AGENT, ActionType.READ, PermissionScope.PROJECT),
                Permission(ResourceType.WORKFLOW, ActionType.READ, PermissionScope.PROJECT),
                Permission(ResourceType.MONITORING, ActionType.READ, PermissionScope.PROJECT),
            ]
        )
        
        # Set up role hierarchy
        admin.parent_roles = ["super_admin"]
        developer.parent_roles = ["admin"]
        operator.parent_roles = ["admin"]
        viewer.parent_roles = ["developer", "operator"]
        
        # Store roles
        self.roles = {
            "super_admin": super_admin,
            "admin": admin,
            "developer": developer,
            "operator": operator,
            "viewer": viewer
        }
        
        logger.info("Initialized system roles with hierarchy")
    
    # Role Management
    
    def create_role(self, name: str, description: str, permissions: List[Permission] = None,
                   parent_roles: List[str] = None) -> Role:
        """Create a new role."""
        if name in self.roles:
            raise ValueError(f"Role '{name}' already exists")
        
        role = Role(
            name=name,
            description=description,
            permissions=permissions or [],
            parent_roles=parent_roles or []
        )
        
        self.roles[name] = role
        
        # Update child roles
        for parent_name in parent_roles or []:
            if parent_name in self.roles:
                if name not in self.roles[parent_name].child_roles:
                    self.roles[parent_name].child_roles.append(name)
        
        self._clear_hierarchy_cache()
        self._audit_log("create_role", {"role_name": name, "parent_roles": parent_roles})
        
        logger.info(f"Created role: {name}")
        return role
    
    def update_role(self, name: str, description: str = None, 
                   permissions: List[Permission] = None,
                   parent_roles: List[str] = None) -> bool:
        """Update an existing role."""
        if name not in self.roles:
            return False
        
        role = self.roles[name]
        
        if description is not None:
            role.description = description
        
        if permissions is not None:
            role.permissions = permissions
        
        if parent_roles is not None:
            # Remove from old parents
            for old_parent in role.parent_roles:
                if old_parent in self.roles and name in self.roles[old_parent].child_roles:
                    self.roles[old_parent].child_roles.remove(name)
            
            # Add to new parents
            for new_parent in parent_roles:
                if new_parent in self.roles and name not in self.roles[new_parent].child_roles:
                    self.roles[new_parent].child_roles.append(name)
            
            role.parent_roles = parent_roles
        
        role.updated_at = datetime.now()
        self._clear_hierarchy_cache()
        self._audit_log("update_role", {"role_name": name})
        
        logger.info(f"Updated role: {name}")
        return True
    
    def delete_role(self, name: str) -> bool:
        """Delete a role."""
        if name not in self.roles:
            return False
        
        role = self.roles[name]
        
        # Remove from parent roles
        for parent_name in role.parent_roles:
            if parent_name in self.roles and name in self.roles[parent_name].child_roles:
                self.roles[parent_name].child_roles.remove(name)
        
        # Update child roles
        for child_name in role.child_roles:
            if child_name in self.roles:
                self.roles[child_name].parent_roles.remove(name)
        
        # Remove from users
        for user in self.users.values():
            if name in user.roles:
                user.remove_role(name)
        
        del self.roles[name]
        self._clear_hierarchy_cache()
        self._audit_log("delete_role", {"role_name": name})
        
        logger.info(f"Deleted role: {name}")
        return True
    
    def get_role(self, name: str) -> Optional[Role]:
        """Get a role by name."""
        return self.roles.get(name)
    
    def list_roles(self) -> List[Role]:
        """List all roles."""
        return list(self.roles.values())
    
    # User Management
    
    def create_user(self, user_id: str, roles: List[str] = None,
                   direct_permissions: List[Permission] = None) -> User:
        """Create a new user."""
        if user_id in self.users:
            raise ValueError(f"User '{user_id}' already exists")
        
        user = User(
            user_id=user_id,
            roles=roles or [],
            direct_permissions=direct_permissions or []
        )
        
        self.users[user_id] = user
        self.evaluator.clear_user_cache(user_id)
        self._audit_log("create_user", {"user_id": user_id, "roles": roles})
        
        logger.info(f"Created user: {user_id}")
        return user
    
    def update_user(self, user_id: str, roles: List[str] = None,
                   direct_permissions: List[Permission] = None,
                   is_active: bool = None) -> bool:
        """Update an existing user."""
        if user_id not in self.users:
            return False
        
        user = self.users[user_id]
        
        if roles is not None:
            user.roles = roles
        
        if direct_permissions is not None:
            user.direct_permissions = direct_permissions
        
        if is_active is not None:
            user.is_active = is_active
        
        user.updated_at = datetime.now()
        self.evaluator.clear_user_cache(user_id)
        self._audit_log("update_user", {"user_id": user_id})
        
        logger.info(f"Updated user: {user_id}")
        return True
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        if user_id not in self.users:
            return False
        
        del self.users[user_id]
        self.evaluator.clear_user_cache(user_id)
        self._audit_log("delete_user", {"user_id": user_id})
        
        logger.info(f"Deleted user: {user_id}")
        return True
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        return self.users.get(user_id)
    
    def list_users(self) -> List[User]:
        """List all users."""
        return list(self.users.values())
    
    # Authorization
    
    def check_permission(self, user_id: str, resource_type: ResourceType, 
                        action: ActionType, resource_id: Optional[str] = None,
                        context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if a user has permission for a specific action."""
        user = self.get_user(user_id)
        if not user:
            return False
        
        return self.evaluator.evaluate_permission(
            user, self.roles, resource_type, action, resource_id, context
        )
    
    def get_user_permissions(self, user_id: str) -> List[Permission]:
        """Get all effective permissions for a user."""
        user = self.get_user(user_id)
        if not user:
            return []
        
        permissions = list(user.direct_permissions)
        
        # Add role-based permissions
        all_roles = self.evaluator._get_all_user_roles(user, self.roles)
        for role_name in all_roles:
            if role_name in self.roles:
                permissions.extend(self.roles[role_name].permissions)
        
        return permissions
    
    def _clear_hierarchy_cache(self) -> None:
        """Clear role hierarchy cache."""
        self.evaluator.role_hierarchy_cache.clear()
    
    def _audit_log(self, action: str, details: Dict[str, Any]) -> None:
        """Log audit events."""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details
        }
        self.audit_log.append(audit_entry)
        
        # Keep only last 1000 entries
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit log entries."""
        return self.audit_log[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get RBAC system statistics."""
        return {
            "total_users": len(self.users),
            "active_users": len([u for u in self.users.values() if u.is_active]),
            "total_roles": len(self.roles),
            "active_roles": len([r for r in self.roles.values() if r.is_active]),
            "cache_size": len(self.evaluator.permission_cache),
            "audit_log_size": len(self.audit_log)
        }