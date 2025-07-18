"""
Database models for authentication and user management.

Provides SQLAlchemy models for persistent storage of users, API keys, and JWT tokens.
"""

from datetime import datetime
from typing import Optional, Dict, Any
import uuid

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, JSON, 
    ForeignKey, Table, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from enum import Enum

Base = declarative_base()


# RBAC Enums - imported from Infrastructure Agent's framework
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


# Association table for user roles
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True)
)


# Association table for role permissions
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id'), primary_key=True)
)


class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Authentication stats
    login_count = Column(Integer, default=0)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Profile information
    profile_data = Column(JSON, nullable=True)  # Store additional profile data
    
    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    jwt_tokens = relationship("JWTToken", back_populates="user", cascade="all, delete-orphan")
    login_sessions = relationship("LoginSession", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_username', 'username'),
        Index('idx_users_active', 'is_active'),
        Index('idx_users_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            'id': str(self.id),
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'is_superuser': self.is_superuser,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'login_count': self.login_count,
            'roles': [role.name for role in self.roles],
            'profile_data': self.profile_data or {}
        }


class Role(Base):
    """Role model for hierarchical role-based access control."""
    
    __tablename__ = 'roles'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Role status
    is_active = Column(Boolean, default=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)  # System roles cannot be deleted
    
    # Hierarchical role support
    parent_role_names = Column(JSON, nullable=True)  # List of parent role names
    child_role_names = Column(JSON, nullable=True)   # List of child role names
    
    # Role metadata for RBAC integration
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("PermissionModel", secondary=role_permissions, back_populates="roles")
    
    # Indexes
    __table_args__ = (
        Index('idx_roles_name', 'name'),
        Index('idx_roles_active', 'is_active'),
        Index('idx_roles_system', 'is_system'),
    )
    
    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"
    
    def to_rbac_role(self):
        """Convert to RBAC framework Role object."""
        # Import here to avoid circular imports
        # Note: In production, import from shared RBAC framework module
        # from rbac_framework import Role as RBACRole
        
        rbac_permissions = [perm.to_rbac_permission() for perm in self.permissions]
        
        return RBACRole(
            name=self.name,
            description=self.description or "",
            permissions=rbac_permissions,
            parent_roles=self.parent_role_names or [],
            child_roles=self.child_role_names or [],
            metadata=self.metadata or {},
            created_at=self.created_at,
            updated_at=self.updated_at,
            is_active=self.is_active
        )
    
    def add_parent_role(self, parent_role_name: str) -> None:
        """Add a parent role."""
        if self.parent_role_names is None:
            self.parent_role_names = []
        if parent_role_name not in self.parent_role_names:
            self.parent_role_names.append(parent_role_name)
            self.updated_at = datetime.utcnow()
    
    def remove_parent_role(self, parent_role_name: str) -> None:
        """Remove a parent role."""
        if self.parent_role_names and parent_role_name in self.parent_role_names:
            self.parent_role_names.remove(parent_role_name)
            self.updated_at = datetime.utcnow()
    
    def add_child_role(self, child_role_name: str) -> None:
        """Add a child role."""
        if self.child_role_names is None:
            self.child_role_names = []
        if child_role_name not in self.child_role_names:
            self.child_role_names.append(child_role_name)
            self.updated_at = datetime.utcnow()
    
    def remove_child_role(self, child_role_name: str) -> None:
        """Remove a child role."""
        if self.child_role_names and child_role_name in self.child_role_names:
            self.child_role_names.remove(child_role_name)
            self.updated_at = datetime.utcnow()


class PermissionModel(Base):
    """Permission model for granular access control with RBAC integration."""
    
    __tablename__ = 'permissions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # RBAC Framework Integration
    resource_type = Column(String(50), nullable=False)  # ResourceType enum value
    action_type = Column(String(50), nullable=False)    # ActionType enum value
    scope = Column(String(50), nullable=False)          # PermissionScope enum value
    resource_id = Column(String(255), nullable=True)    # Specific resource ID or wildcard
    
    # Conditional permissions - JSON field for dynamic conditions
    conditions = Column(JSON, nullable=True)
    
    # Permission lifecycle
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
    
    # Indexes
    __table_args__ = (
        Index('idx_permissions_resource_type', 'resource_type'),
        Index('idx_permissions_action_type', 'action_type'),
        Index('idx_permissions_scope', 'scope'),
        Index('idx_permissions_resource_id', 'resource_id'),
        Index('idx_permissions_active', 'is_active'),
        Index('idx_permissions_expires_at', 'expires_at'),
        UniqueConstraint('resource_type', 'action_type', 'scope', 'resource_id', name='unique_permission')
    )
    
    def __repr__(self):
        return f"<Permission(id={self.id}, name='{self.name}', resource_type='{self.resource_type}', action_type='{self.action_type}')>"
    
    def to_rbac_permission(self):
        """Convert to RBAC framework Permission object."""
        # Import here to avoid circular imports
        # Note: In production, import from shared RBAC framework module
        # from rbac_framework import Permission as RBACPermission, ResourceType, ActionType, PermissionScope
        
        # TODO: Implement when RBAC framework is properly integrated
        # return RBACPermission(
        #     resource_type=ResourceType(self.resource_type),
        #     action=ActionType(self.action_type),
        #     scope=PermissionScope(self.scope),
        #     resource_id=self.resource_id,
        #     conditions=self.conditions or {},
        #     created_at=self.created_at,
        #     expires_at=self.expires_at
        # )
        pass
    
    def is_valid(self) -> bool:
        """Check if permission is still valid."""
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
    
    def matches_request(self, resource_type: ResourceType, action: ActionType, 
                       resource_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if this permission matches a request."""
        if not self.is_valid():
            return False
        
        # Check resource type
        if self.resource_type != resource_type.value:
            return False
        
        # Check action
        if self.action_type != action.value:
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


class APIKey(Base):
    """API key model for API authentication."""
    
    __tablename__ = 'api_keys'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)  # Human-readable name for the key
    description = Column(Text, nullable=True)
    
    # Key metadata
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    prefix = Column(String(10), nullable=False)  # First few characters for identification
    
    # Key status and permissions
    is_active = Column(Boolean, default=True, nullable=False)
    permissions = Column(JSON, nullable=True)  # Store specific permissions for this key
    
    # Usage tracking
    last_used = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    # Indexes
    __table_args__ = (
        Index('idx_api_keys_hash', 'key_hash'),
        Index('idx_api_keys_user_id', 'user_id'),
        Index('idx_api_keys_active', 'is_active'),
        Index('idx_api_keys_expires_at', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', prefix='{self.prefix}')>"
    
    def is_expired(self) -> bool:
        """Check if the API key is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class JWTToken(Base):
    """JWT token model for token blacklisting and tracking."""
    
    __tablename__ = 'jwt_tokens'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    jti = Column(String(100), unique=True, nullable=False, index=True)  # JWT ID
    token_type = Column(String(20), nullable=False)  # 'access' or 'refresh'
    
    # Token metadata
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Token status
    is_blacklisted = Column(Boolean, default=False, nullable=False)
    blacklisted_at = Column(DateTime(timezone=True), nullable=True)
    blacklist_reason = Column(String(255), nullable=True)
    
    # Token lifecycle
    issued_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Usage tracking
    last_used = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Client information
    client_ip = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="jwt_tokens")
    
    # Indexes
    __table_args__ = (
        Index('idx_jwt_tokens_hash', 'token_hash'),
        Index('idx_jwt_tokens_jti', 'jti'),
        Index('idx_jwt_tokens_user_id', 'user_id'),
        Index('idx_jwt_tokens_blacklisted', 'is_blacklisted'),
        Index('idx_jwt_tokens_expires_at', 'expires_at'),
        Index('idx_jwt_tokens_type', 'token_type'),
    )
    
    def __repr__(self):
        return f"<JWTToken(id={self.id}, jti='{self.jti}', type='{self.token_type}')>"
    
    def is_expired(self) -> bool:
        """Check if the JWT token is expired."""
        return datetime.utcnow() > self.expires_at
    
    def blacklist(self, reason: str = None) -> None:
        """Blacklist this token."""
        self.is_blacklisted = True
        self.blacklisted_at = datetime.utcnow()
        self.blacklist_reason = reason or "Manually blacklisted"


class LoginSession(Base):
    """Login session model for session management."""
    
    __tablename__ = 'login_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Session metadata
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Session status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Session lifecycle
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="login_sessions")
    
    # Indexes
    __table_args__ = (
        Index('idx_login_sessions_token', 'session_token'),
        Index('idx_login_sessions_user_id', 'user_id'),
        Index('idx_login_sessions_active', 'is_active'),
        Index('idx_login_sessions_expires_at', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<LoginSession(id={self.id}, user_id={self.user_id})>"
    
    def is_expired(self) -> bool:
        """Check if the session is expired."""
        return datetime.utcnow() > self.expires_at
    
    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = datetime.utcnow()


# Database utility functions
def create_default_roles(session: Session) -> None:
    """Create default system roles."""
    default_roles = [
        {"name": "admin", "display_name": "Administrator", "description": "Full system access", "is_system": True},
        {"name": "user", "display_name": "User", "description": "Standard user access", "is_system": True},
        {"name": "readonly", "display_name": "Read Only", "description": "Read-only access", "is_system": True},
    ]
    
    for role_data in default_roles:
        existing_role = session.query(Role).filter_by(name=role_data["name"]).first()
        if not existing_role:
            role = Role(**role_data)
            session.add(role)
    
    session.commit()


def create_default_permissions(session: Session) -> None:
    """Create default system permissions."""
    default_permissions = [
        {"name": "read", "display_name": "Read", "description": "Read access to resources"},
        {"name": "write", "display_name": "Write", "description": "Write access to resources"},
        {"name": "admin", "display_name": "Admin", "description": "Administrative access"},
        {"name": "execute", "display_name": "Execute", "description": "Execute operations"},
    ]
    
    for perm_data in default_permissions:
        existing_perm = session.query(PermissionModel).filter_by(name=perm_data["name"]).first()
        if not existing_perm:
            permission = PermissionModel(**perm_data)
            session.add(permission)
    
    session.commit()


def setup_default_rbac(session: Session) -> None:
    """Set up default role-based access control with RBAC framework integration."""
    create_default_permissions(session)
    create_default_roles(session)
    
    # Create RBAC-specific permissions
    rbac_permissions = []
    
    # Create comprehensive permissions for all resource types and actions
    for resource_type in ResourceType:
        for action_type in ActionType:
            for scope in PermissionScope:
                permission_name = f"{resource_type.value}_{action_type.value}_{scope.value}"
                
                # Check if permission already exists
                existing_perm = session.query(PermissionModel).filter_by(name=permission_name).first()
                if not existing_perm:
                    perm = PermissionModel(
                        name=permission_name,
                        display_name=f"{action_type.value.title()} {resource_type.value.replace('_', ' ').title()} ({scope.value})",
                        description=f"Permission to {action_type.value} {resource_type.value} resources at {scope.value} scope",
                        resource_type=resource_type.value,
                        action_type=action_type.value,
                        scope=scope.value,
                        resource_id="*"  # Wildcard for default permissions
                    )
                    session.add(perm)
                    rbac_permissions.append(perm)
    
    session.commit()
    
    # Set up hierarchical roles matching Infrastructure Agent's framework
    setup_hierarchical_roles(session)


def setup_hierarchical_roles(session: Session) -> None:
    """Set up hierarchical roles matching Infrastructure Agent's RBAC framework."""
    
    # Define role hierarchy and permissions
    role_definitions = {
        "super_admin": {
            "description": "Super administrator with all permissions",
            "parent_roles": [],
            "permissions": [
                ("API_ENDPOINT", "ADMIN", "GLOBAL"),
                ("DATABASE", "ADMIN", "GLOBAL"),
                ("FILE_SYSTEM", "ADMIN", "GLOBAL"),
                ("SERVICE", "ADMIN", "GLOBAL"),
                ("AGENT", "ADMIN", "GLOBAL"),
                ("WORKFLOW", "ADMIN", "GLOBAL"),
                ("MONITORING", "ADMIN", "GLOBAL"),
                ("CONFIGURATION", "ADMIN", "GLOBAL"),
            ]
        },
        "admin": {
            "description": "Administrator with most permissions",
            "parent_roles": ["super_admin"],
            "permissions": [
                ("API_ENDPOINT", "READ", "GLOBAL"),
                ("API_ENDPOINT", "UPDATE", "GLOBAL"),
                ("API_ENDPOINT", "CREATE", "GLOBAL"),
                ("DATABASE", "READ", "GLOBAL"),
                ("DATABASE", "UPDATE", "GLOBAL"),
                ("SERVICE", "READ", "GLOBAL"),
                ("SERVICE", "CONFIGURE", "GLOBAL"),
                ("AGENT", "READ", "GLOBAL"),
                ("AGENT", "EXECUTE", "GLOBAL"),
                ("MONITORING", "READ", "GLOBAL"),
            ]
        },
        "developer": {
            "description": "Developer with development permissions",
            "parent_roles": ["admin"],
            "permissions": [
                ("API_ENDPOINT", "READ", "PROJECT"),
                ("API_ENDPOINT", "UPDATE", "PROJECT"),
                ("DATABASE", "READ", "PROJECT"),
                ("SERVICE", "READ", "PROJECT"),
                ("AGENT", "READ", "PROJECT"),
                ("AGENT", "EXECUTE", "PROJECT"),
                ("WORKFLOW", "READ", "PROJECT"),
                ("WORKFLOW", "UPDATE", "PROJECT"),
            ]
        },
        "operator": {
            "description": "Operations team with deployment and monitoring permissions",
            "parent_roles": ["admin"],
            "permissions": [
                ("SERVICE", "DEPLOY", "GLOBAL"),
                ("SERVICE", "SCALE", "GLOBAL"),
                ("MONITORING", "READ", "GLOBAL"),
                ("MONITORING", "CONFIGURE", "GLOBAL"),
                ("CONFIGURATION", "READ", "GLOBAL"),
                ("CONFIGURATION", "UPDATE", "GLOBAL"),
            ]
        },
        "viewer": {
            "description": "Read-only access to most resources",
            "parent_roles": ["developer", "operator"],
            "permissions": [
                ("API_ENDPOINT", "READ", "PROJECT"),
                ("DATABASE", "READ", "PROJECT"),
                ("SERVICE", "READ", "PROJECT"),
                ("AGENT", "READ", "PROJECT"),
                ("WORKFLOW", "READ", "PROJECT"),
                ("MONITORING", "READ", "PROJECT"),
            ]
        }
    }
    
    # Create or update roles
    for role_name, role_def in role_definitions.items():
        role = session.query(Role).filter_by(name=role_name).first()
        if not role:
            role = Role(
                name=role_name,
                display_name=role_name.replace("_", " ").title(),
                description=role_def["description"],
                is_system=True
            )
            session.add(role)
        
        # Set parent roles
        role.parent_role_names = role_def["parent_roles"]
        
        # Set child roles for parents
        for parent_role_name in role_def["parent_roles"]:
            parent_role = session.query(Role).filter_by(name=parent_role_name).first()
            if parent_role:
                if parent_role.child_role_names is None:
                    parent_role.child_role_names = []
                if role_name not in parent_role.child_role_names:
                    parent_role.child_role_names.append(role_name)
    
    session.commit()
    
    # Assign permissions to roles
    for role_name, role_def in role_definitions.items():
        role = session.query(Role).filter_by(name=role_name).first()
        if role:
            # Clear existing permissions
            role.permissions = []
            
            # Add new permissions
            for resource_type, action_type, scope in role_def["permissions"]:
                permission_name = f"{resource_type.lower()}_{action_type.lower()}_{scope.lower()}"
                permission = session.query(PermissionModel).filter_by(name=permission_name).first()
                if permission:
                    role.permissions.append(permission)
    
    session.commit()
    logger.info("Set up hierarchical roles with RBAC framework integration")


def create_rbac_user_from_auth_user(session: Session, auth_user: User) -> Optional[Any]:
    """Create an RBAC framework User from database User model."""
    try:
        # Import here to avoid circular imports
        # Note: In production, import from shared RBAC framework module
        # from rbac_framework import User as RBACUser, Permission as RBACPermission
        
        # Get user roles
        role_names = [role.name for role in auth_user.roles]
        
        # Get direct permissions (if any)
        direct_permissions = []
        # Convert database permissions to RBAC permissions if needed
        
        rbac_user = RBACUser(
            user_id=str(auth_user.id),
            roles=role_names,
            direct_permissions=direct_permissions,
            metadata={
                "username": auth_user.username,
                "email": auth_user.email,
                "is_active": auth_user.is_active,
                "is_verified": auth_user.is_verified,
                "is_superuser": auth_user.is_superuser
            },
            created_at=auth_user.created_at,
            updated_at=auth_user.updated_at,
            is_active=auth_user.is_active
        )
        
        return rbac_user
        
    except Exception as e:
        logger.error(f"Failed to create RBAC user from auth user: {e}")
        return None


def sync_database_with_rbac_framework(session: Session, rbac_manager: Any) -> bool:
    """Synchronize database models with RBAC framework."""
    try:
        # Sync users
        db_users = session.query(User).all()
        for db_user in db_users:
            rbac_user = create_rbac_user_from_auth_user(session, db_user)
            if rbac_user:
                rbac_manager.users[rbac_user.user_id] = rbac_user
        
        # Sync roles
        db_roles = session.query(Role).all()
        for db_role in db_roles:
            rbac_role = db_role.to_rbac_role()
            rbac_manager.roles[rbac_role.name] = rbac_role
        
        logger.info(f"Synchronized {len(db_users)} users and {len(db_roles)} roles with RBAC framework")
        return True
        
    except Exception as e:
        logger.error(f"Failed to sync database with RBAC framework: {e}")
        return False