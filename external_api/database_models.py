"""
Database models for RBAC framework - compatibility alias.

This module provides a compatibility layer for the enhanced RBAC database models.
It re-exports the models from rbac_database_models to maintain backward compatibility.
"""

# Re-export all models from rbac_database_models
from .rbac_database_models import (
    Base,
    User,
    Role,
    PermissionModel,
    ResourceType,
    ActionType,
    PermissionScope,
    setup_default_rbac,
    create_default_roles,
    create_default_permissions,
    
    # Enhanced models
    EnhancedRole,
    EnhancedPermission,
    PermissionCache,
    AuditLog,
    
    # Enum classes
    ResourceTypeEnum,
    ActionTypeEnum,
    PermissionScopeEnum,
    
    # Setup functions
    create_enhanced_system_roles,
    create_enhanced_system_permissions,
    setup_enhanced_rbac,
    cleanup_expired_cache,
    cleanup_old_audit_logs
)

# Backward compatibility aliases
SecurityUser = User
SecurityRole = Role

# Export the main setup function as both names
create_default_rbac = setup_default_rbac
setup_default_rbac = setup_enhanced_rbac