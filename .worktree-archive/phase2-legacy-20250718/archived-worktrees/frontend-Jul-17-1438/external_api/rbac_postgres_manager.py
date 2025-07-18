"""
PostgreSQL-backed RBAC Manager

Integrates with Security Agent's database models to provide persistent RBAC functionality
with hierarchical roles, granular permissions, and high-performance caching.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set, Tuple
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, text
import redis
import hashlib
import json

# Import Security Agent's database models
import sys
sys.path.append('../security-Jul-17-0944')
from external_api.database_models import (
    User, Role, PermissionModel, ResourceType, ActionType, PermissionScope
)

# Import our RBAC framework
from .rbac_framework import (
    RBACManager as BaseRBACManager,
    Permission as RBACPermission,
    Role as RBACRole,
    User as RBACUser,
    AuthorizationEvaluator
)
from .permission_manager import PermissionManager, PermissionCacheManager

logger = logging.getLogger(__name__)


class PostgreSQLRBACManager(BaseRBACManager):
    """PostgreSQL-backed RBAC manager with persistent storage."""
    
    def __init__(self, session_factory: sessionmaker, redis_client: redis.Redis = None):
        """Initialize PostgreSQL RBAC manager."""
        self.session_factory = session_factory
        self.redis_client = redis_client
        self.evaluator = AuthorizationEvaluator()
        
        # Cache for database objects
        self._user_cache: Dict[str, User] = {}
        self._role_cache: Dict[str, Role] = {}
        self._permission_cache: Dict[str, PermissionModel] = {}
        
        # Audit log
        self.audit_log: List[Dict[str, Any]] = []
        
        # Initialize permission manager if Redis is available
        if redis_client:
            self.permission_manager = PermissionManager(self, redis_client)
    
    def _get_session(self) -> Session:
        """Get database session."""
        return self.session_factory()
    
    def _to_rbac_permission(self, db_permission: PermissionModel) -> RBACPermission:
        """Convert database permission to RBAC framework permission."""
        return RBACPermission(
            resource_type=ResourceType(db_permission.resource_type),
            action=ActionType(db_permission.action_type),
            scope=PermissionScope(db_permission.scope),
            resource_id=db_permission.resource_id,
            conditions=db_permission.conditions or {},
            created_at=db_permission.created_at,
            expires_at=db_permission.expires_at
        )
    
    def _to_rbac_role(self, db_role: Role) -> RBACRole:
        """Convert database role to RBAC framework role."""
        permissions = [self._to_rbac_permission(perm) for perm in db_role.permissions]
        
        return RBACRole(
            name=db_role.name,
            description=db_role.description or "",
            permissions=permissions,
            parent_roles=db_role.parent_role_names or [],
            child_roles=db_role.child_role_names or [],
            metadata=db_role.metadata or {},
            created_at=db_role.created_at,
            updated_at=db_role.updated_at,
            is_active=db_role.is_active
        )
    
    def _to_rbac_user(self, db_user: User) -> RBACUser:
        """Convert database user to RBAC framework user."""
        roles = [role.name for role in db_user.roles]
        
        return RBACUser(
            user_id=db_user.username,  # Use username as user_id
            roles=roles,
            direct_permissions=[],  # TODO: Implement direct permissions
            metadata={
                'id': str(db_user.id),
                'email': db_user.email,
                'full_name': db_user.full_name,
                'profile_data': db_user.profile_data or {}
            },
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
            is_active=db_user.is_active
        )
    
    # Role Management
    
    def create_role(self, name: str, description: str, permissions: List[RBACPermission] = None,
                   parent_roles: List[str] = None, **kwargs) -> RBACRole:
        """Create a new role with database persistence."""
        with self._get_session() as session:
            try:
                # Check if role already exists
                existing_role = session.query(Role).filter_by(name=name).first()
                if existing_role:
                    raise ValueError(f"Role '{name}' already exists")
                
                # Create database role
                db_role = Role(
                    name=name,
                    display_name=kwargs.get('display_name', name),
                    description=description,
                    parent_role_names=parent_roles or [],
                    child_role_names=[],
                    metadata=kwargs.get('metadata', {}),
                    is_system=kwargs.get('is_system', False)
                )
                
                session.add(db_role)
                session.flush()  # Get the ID
                
                # Add permissions if provided
                if permissions:
                    for perm in permissions:
                        db_perm = self._get_or_create_permission(session, perm)
                        if db_perm:
                            db_role.permissions.append(db_perm)
                
                # Update parent roles' child_roles
                if parent_roles:
                    for parent_name in parent_roles:
                        parent_role = session.query(Role).filter_by(name=parent_name).first()
                        if parent_role:
                            parent_role.add_child_role(name)
                
                session.commit()
                
                # Clear cache
                self._clear_role_cache()
                
                # Audit log
                self._audit_log("create_role", {"role_name": name, "parent_roles": parent_roles})
                
                logger.info(f"Created role: {name}")
                return self._to_rbac_role(db_role)
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Error creating role {name}: {e}")
                raise
    
    def update_role(self, name: str, description: str = None, 
                   permissions: List[RBACPermission] = None,
                   parent_roles: List[str] = None, **kwargs) -> bool:
        """Update an existing role."""
        with self._get_session() as session:
            try:
                db_role = session.query(Role).filter_by(name=name).first()
                if not db_role:
                    return False
                
                # Update basic fields
                if description is not None:
                    db_role.description = description
                
                if 'display_name' in kwargs:
                    db_role.display_name = kwargs['display_name']
                
                if 'metadata' in kwargs:
                    db_role.metadata = kwargs['metadata']
                
                # Update permissions
                if permissions is not None:
                    db_role.permissions.clear()
                    for perm in permissions:
                        db_perm = self._get_or_create_permission(session, perm)
                        if db_perm:
                            db_role.permissions.append(db_perm)
                
                # Update parent roles
                if parent_roles is not None:
                    # Remove from old parents
                    if db_role.parent_role_names:
                        for old_parent in db_role.parent_role_names:
                            parent_role = session.query(Role).filter_by(name=old_parent).first()
                            if parent_role:
                                parent_role.remove_child_role(name)
                    
                    # Add to new parents
                    for new_parent in parent_roles:
                        parent_role = session.query(Role).filter_by(name=new_parent).first()
                        if parent_role:
                            parent_role.add_child_role(name)
                    
                    db_role.parent_role_names = parent_roles
                
                db_role.updated_at = datetime.utcnow()
                session.commit()
                
                # Clear cache
                self._clear_role_cache()
                
                # Audit log
                self._audit_log("update_role", {"role_name": name})
                
                logger.info(f"Updated role: {name}")
                return True
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Error updating role {name}: {e}")
                return False
    
    def delete_role(self, name: str) -> bool:
        """Delete a role."""
        with self._get_session() as session:
            try:
                db_role = session.query(Role).filter_by(name=name).first()
                if not db_role:
                    return False
                
                # Don't delete system roles
                if db_role.is_system:
                    logger.warning(f"Cannot delete system role: {name}")
                    return False
                
                # Update parent roles
                if db_role.parent_role_names:
                    for parent_name in db_role.parent_role_names:
                        parent_role = session.query(Role).filter_by(name=parent_name).first()
                        if parent_role:
                            parent_role.remove_child_role(name)
                
                # Update child roles
                if db_role.child_role_names:
                    for child_name in db_role.child_role_names:
                        child_role = session.query(Role).filter_by(name=child_name).first()
                        if child_role:
                            child_role.remove_parent_role(name)
                
                session.delete(db_role)
                session.commit()
                
                # Clear cache
                self._clear_role_cache()
                
                # Audit log
                self._audit_log("delete_role", {"role_name": name})
                
                logger.info(f"Deleted role: {name}")
                return True
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Error deleting role {name}: {e}")
                return False
    
    def get_role(self, name: str) -> Optional[RBACRole]:
        """Get a role by name."""
        # Check cache first
        if name in self._role_cache:
            return self._to_rbac_role(self._role_cache[name])
        
        with self._get_session() as session:
            try:
                db_role = session.query(Role).filter_by(name=name).first()
                if db_role:
                    self._role_cache[name] = db_role
                    return self._to_rbac_role(db_role)
                return None
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting role {name}: {e}")
                return None
    
    def list_roles(self, active_only: bool = True) -> List[RBACRole]:
        """List all roles."""
        with self._get_session() as session:
            try:
                query = session.query(Role)
                if active_only:
                    query = query.filter(Role.is_active == True)
                
                db_roles = query.all()
                return [self._to_rbac_role(role) for role in db_roles]
                
            except SQLAlchemyError as e:
                logger.error(f"Error listing roles: {e}")
                return []
    
    # User Management
    
    def create_user(self, user_id: str, roles: List[str] = None, 
                   direct_permissions: List[RBACPermission] = None, **kwargs) -> RBACUser:
        """Create a new user with database persistence."""
        with self._get_session() as session:
            try:
                # Check if user already exists
                existing_user = session.query(User).filter_by(username=user_id).first()
                if existing_user:
                    raise ValueError(f"User '{user_id}' already exists")
                
                # Create database user
                db_user = User(
                    username=user_id,
                    email=kwargs.get('email', f"{user_id}@example.com"),
                    password_hash=kwargs.get('password_hash', 'placeholder'),
                    full_name=kwargs.get('full_name'),
                    profile_data=kwargs.get('profile_data', {}),
                    is_active=kwargs.get('is_active', True)
                )
                
                session.add(db_user)
                session.flush()  # Get the ID
                
                # Add roles if provided
                if roles:
                    for role_name in roles:
                        db_role = session.query(Role).filter_by(name=role_name).first()
                        if db_role:
                            db_user.roles.append(db_role)
                
                # TODO: Add direct permissions support
                
                session.commit()
                
                # Clear cache
                self._clear_user_cache()
                
                # Audit log
                self._audit_log("create_user", {"user_id": user_id, "roles": roles})
                
                logger.info(f"Created user: {user_id}")
                return self._to_rbac_user(db_user)
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Error creating user {user_id}: {e}")
                raise
    
    def update_user(self, user_id: str, roles: List[str] = None,
                   direct_permissions: List[RBACPermission] = None,
                   is_active: bool = None, **kwargs) -> bool:
        """Update an existing user."""
        with self._get_session() as session:
            try:
                db_user = session.query(User).filter_by(username=user_id).first()
                if not db_user:
                    return False
                
                # Update basic fields
                if is_active is not None:
                    db_user.is_active = is_active
                
                if 'email' in kwargs:
                    db_user.email = kwargs['email']
                
                if 'full_name' in kwargs:
                    db_user.full_name = kwargs['full_name']
                
                if 'profile_data' in kwargs:
                    db_user.profile_data = kwargs['profile_data']
                
                # Update roles
                if roles is not None:
                    db_user.roles.clear()
                    for role_name in roles:
                        db_role = session.query(Role).filter_by(name=role_name).first()
                        if db_role:
                            db_user.roles.append(db_role)
                
                # TODO: Update direct permissions
                
                db_user.updated_at = datetime.utcnow()
                session.commit()
                
                # Clear cache
                self._clear_user_cache()
                
                # Audit log
                self._audit_log("update_user", {"user_id": user_id})
                
                logger.info(f"Updated user: {user_id}")
                return True
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Error updating user {user_id}: {e}")
                return False
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        with self._get_session() as session:
            try:
                db_user = session.query(User).filter_by(username=user_id).first()
                if not db_user:
                    return False
                
                session.delete(db_user)
                session.commit()
                
                # Clear cache
                self._clear_user_cache()
                
                # Audit log
                self._audit_log("delete_user", {"user_id": user_id})
                
                logger.info(f"Deleted user: {user_id}")
                return True
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Error deleting user {user_id}: {e}")
                return False
    
    def get_user(self, user_id: str) -> Optional[RBACUser]:
        """Get a user by ID."""
        # Check cache first
        if user_id in self._user_cache:
            return self._to_rbac_user(self._user_cache[user_id])
        
        with self._get_session() as session:
            try:
                db_user = session.query(User).filter_by(username=user_id).first()
                if db_user:
                    self._user_cache[user_id] = db_user
                    return self._to_rbac_user(db_user)
                return None
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting user {user_id}: {e}")
                return None
    
    def list_users(self, active_only: bool = True) -> List[RBACUser]:
        """List all users."""
        with self._get_session() as session:
            try:
                query = session.query(User)
                if active_only:
                    query = query.filter(User.is_active == True)
                
                db_users = query.all()
                return [self._to_rbac_user(user) for user in db_users]
                
            except SQLAlchemyError as e:
                logger.error(f"Error listing users: {e}")
                return []
    
    # Permission Management
    
    def _get_or_create_permission(self, session: Session, perm: RBACPermission) -> Optional[PermissionModel]:
        """Get or create a permission in the database."""
        try:
            # Generate permission name
            name = f"{perm.resource_type.value}:{perm.action.value}:{perm.scope.value}"
            if perm.resource_id:
                name += f":{perm.resource_id}"
            
            # Check if permission exists
            db_perm = session.query(PermissionModel).filter_by(name=name).first()
            
            if not db_perm:
                # Create new permission
                db_perm = PermissionModel(
                    name=name,
                    display_name=f"{perm.action.value.title()} {perm.resource_type.value}",
                    description=f"Permission to {perm.action.value} {perm.resource_type.value} resources",
                    resource_type=perm.resource_type.value,
                    action_type=perm.action.value,
                    scope=perm.scope.value,
                    resource_id=perm.resource_id,
                    conditions=perm.conditions,
                    expires_at=perm.expires_at
                )
                session.add(db_perm)
                session.flush()
            
            return db_perm
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting/creating permission: {e}")
            return None
    
    def check_permission(self, user_id: str, resource_type: ResourceType, 
                        action: ActionType, resource_id: Optional[str] = None,
                        context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if a user has permission for a specific action."""
        with self._get_session() as session:
            try:
                # Get user
                db_user = session.query(User).filter_by(username=user_id).first()
                if not db_user or not db_user.is_active:
                    return False
                
                # Check direct permissions first (TODO: implement)
                
                # Check role-based permissions with hierarchy
                all_roles = self._get_all_user_roles(session, db_user)
                
                for role in all_roles:
                    if not role.is_active:
                        continue
                    
                    for perm in role.permissions:
                        if perm.matches_request(resource_type, action, resource_id, context):
                            return True
                
                return False
                
            except SQLAlchemyError as e:
                logger.error(f"Error checking permission for user {user_id}: {e}")
                return False
    
    def get_user_permissions(self, user_id: str) -> List[RBACPermission]:
        """Get all effective permissions for a user."""
        with self._get_session() as session:
            try:
                db_user = session.query(User).filter_by(username=user_id).first()
                if not db_user:
                    return []
                
                permissions = []
                
                # Get permissions from roles
                all_roles = self._get_all_user_roles(session, db_user)
                for role in all_roles:
                    if role.is_active:
                        permissions.extend([self._to_rbac_permission(perm) for perm in role.permissions])
                
                # TODO: Add direct permissions
                
                return permissions
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting user permissions for {user_id}: {e}")
                return []
    
    def _get_all_user_roles(self, session: Session, user: User) -> List[Role]:
        """Get all roles for a user including inherited roles."""
        all_roles = []
        visited = set()
        
        def traverse_roles(role_names: List[str]):
            for role_name in role_names:
                if role_name in visited:
                    continue
                
                visited.add(role_name)
                role = session.query(Role).filter_by(name=role_name).first()
                if role and role.is_active:
                    all_roles.append(role)
                    if role.parent_role_names:
                        traverse_roles(role.parent_role_names)
        
        # Start with user's direct roles
        user_role_names = [role.name for role in user.roles]
        traverse_roles(user_role_names)
        
        return all_roles
    
    # Cache Management
    
    def _clear_user_cache(self):
        """Clear user cache."""
        self._user_cache.clear()
    
    def _clear_role_cache(self):
        """Clear role cache."""
        self._role_cache.clear()
    
    def _clear_permission_cache(self):
        """Clear permission cache."""
        self._permission_cache.clear()
    
    def clear_all_caches(self):
        """Clear all caches."""
        self._clear_user_cache()
        self._clear_role_cache()
        self._clear_permission_cache()
        
        if hasattr(self, 'permission_manager'):
            asyncio.create_task(self.permission_manager.clear_cache())
    
    # Audit and Statistics
    
    def _audit_log(self, action: str, details: Dict[str, Any]) -> None:
        """Log audit events."""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
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
        with self._get_session() as session:
            try:
                total_users = session.query(User).count()
                active_users = session.query(User).filter(User.is_active == True).count()
                total_roles = session.query(Role).count()
                active_roles = session.query(Role).filter(Role.is_active == True).count()
                total_permissions = session.query(PermissionModel).count()
                
                return {
                    "total_users": total_users,
                    "active_users": active_users,
                    "total_roles": total_roles,
                    "active_roles": active_roles,
                    "total_permissions": total_permissions,
                    "audit_log_size": len(self.audit_log),
                    "cache_sizes": {
                        "users": len(self._user_cache),
                        "roles": len(self._role_cache),
                        "permissions": len(self._permission_cache)
                    }
                }
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting stats: {e}")
                return {"error": str(e)}
    
    # Bulk Operations
    
    def bulk_check_permissions(self, requests: List[Dict[str, Any]]) -> Dict[str, bool]:
        """Check multiple permissions efficiently."""
        results = {}
        
        with self._get_session() as session:
            for i, req in enumerate(requests):
                user_id = req["user_id"]
                resource_type = ResourceType(req["resource_type"])
                action = ActionType(req["action"])
                resource_id = req.get("resource_id")
                context = req.get("context")
                
                result = self.check_permission(user_id, resource_type, action, resource_id, context)
                results[f"req_{i}"] = result
        
        return results
    
    def get_users_with_role(self, role_name: str) -> List[RBACUser]:
        """Get all users with a specific role."""
        with self._get_session() as session:
            try:
                db_role = session.query(Role).filter_by(name=role_name).first()
                if not db_role:
                    return []
                
                return [self._to_rbac_user(user) for user in db_role.users if user.is_active]
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting users with role {role_name}: {e}")
                return []
    
    def get_roles_with_permission(self, resource_type: ResourceType, 
                                 action: ActionType) -> List[RBACRole]:
        """Get all roles with a specific permission."""
        with self._get_session() as session:
            try:
                db_permissions = session.query(PermissionModel).filter(
                    PermissionModel.resource_type == resource_type.value,
                    PermissionModel.action_type == action.value
                ).all()
                
                roles = set()
                for perm in db_permissions:
                    roles.update(perm.roles)
                
                return [self._to_rbac_role(role) for role in roles if role.is_active]
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting roles with permission: {e}")
                return []