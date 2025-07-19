#!/usr/bin/env python3
"""
Simplified RBAC API Endpoints for Testing

Basic REST API endpoints for role-based access control management.
This is a simplified version for testing and validation purposes.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from security.rbac_manager import RBACManager, PermissionType, RoleType
from security.permission_middleware import PermissionMiddleware
from security.auth_service import AuthenticationService


logger = logging.getLogger(__name__)


class SimpleRBACEndpoints:
    """
    Simplified RBAC API endpoints for testing and validation.
    """
    
    def __init__(self, rbac_manager: RBACManager, 
                 permission_middleware: PermissionMiddleware,
                 auth_service: AuthenticationService):
        """Initialize RBAC endpoints."""
        self.rbac_manager = rbac_manager
        self.permission_middleware = permission_middleware
        self.auth_service = auth_service
        
        logger.info("SimpleRBACEndpoints initialized")
    
    async def create_role(self, role_type: str, name: str, description: str,
                         permissions: List[str]) -> Dict[str, Any]:
        """Create a new role."""
        try:
            # Convert string types to enums
            role_type_enum = RoleType(role_type)
            permission_enums = [PermissionType(p) for p in permissions]
            
            success, message, role = await self.rbac_manager.create_role(
                role_type=role_type_enum,
                name=name,
                description=description,
                permissions=permission_enums,
                created_by="api_user"
            )
            
            if not success:
                return {"success": False, "error": message}
            
            return {
                "success": True,
                "role": {
                    "role_id": role.role_id,
                    "name": role.name,
                    "type": role.role_type.value,
                    "description": role.description,
                    "permissions": [p.value for p in role.permissions],
                    "created_at": role.created_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create role: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_roles(self, active_only: bool = True) -> Dict[str, Any]:
        """List all roles."""
        try:
            roles = await self.rbac_manager.list_roles(active_only=active_only)
            
            return {
                "success": True,
                "roles": [
                    {
                        "role_id": role.role_id,
                        "name": role.name,
                        "type": role.role_type.value,
                        "description": role.description,
                        "permissions": [p.value for p in role.permissions],
                        "active": role.active
                    }
                    for role in roles
                ],
                "total": len(roles)
            }
            
        except Exception as e:
            logger.error(f"Failed to list roles: {e}")
            return {"success": False, "error": str(e)}
    
    async def assign_role(self, user_id: str, role_id: str) -> Dict[str, Any]:
        """Assign role to user."""
        try:
            success, message = await self.rbac_manager.assign_role_to_user(
                user_id=user_id,
                role_id=role_id,
                assigned_by="api_user"
            )
            
            return {
                "success": success,
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Failed to assign role: {e}")
            return {"success": False, "error": str(e)}
    
    async def revoke_role(self, user_id: str, role_id: str) -> Dict[str, Any]:
        """Revoke role from user."""
        try:
            success, message = await self.rbac_manager.revoke_role_from_user(
                user_id=user_id,
                role_id=role_id,
                revoked_by="api_user"
            )
            
            return {
                "success": success,
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Failed to revoke role: {e}")
            return {"success": False, "error": str(e)}
    
    async def check_permission(self, user_id: str, permission: str) -> Dict[str, Any]:
        """Check if user has specific permission."""
        try:
            permission_enum = PermissionType(permission)
            result = await self.rbac_manager.check_permission(user_id, permission_enum)
            
            return {
                "success": True,
                "permission_check": {
                    "user_id": result.user_id,
                    "permission": result.permission.value,
                    "granted": result.granted,
                    "reason": result.reason,
                    "role_sources": result.role_sources,
                    "checked_at": result.checked_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to check permission: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_user_roles(self, user_id: str) -> Dict[str, Any]:
        """Get roles assigned to user."""
        try:
            roles = await self.rbac_manager.get_user_roles(user_id)
            
            return {
                "success": True,
                "user_id": user_id,
                "roles": [
                    {
                        "role_id": role.role_id,
                        "name": role.name,
                        "type": role.role_type.value,
                        "description": role.description
                    }
                    for role in roles
                ],
                "total_roles": len(roles)
            }
            
        except Exception as e:
            logger.error(f"Failed to get user roles: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """Get all effective permissions for user."""
        try:
            permissions = await self.rbac_manager.get_user_permissions(user_id)
            
            return {
                "success": True,
                "user_id": user_id,
                "permissions": [p.value for p in permissions],
                "total_permissions": len(permissions),
                "retrieved_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get user permissions: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_rbac_analytics(self) -> Dict[str, Any]:
        """Get RBAC analytics and statistics."""
        try:
            analytics = await self.rbac_manager.get_rbac_analytics()
            return {
                "success": True,
                "analytics": analytics,
                "retrieved_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get RBAC analytics: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_permission_analytics(self) -> Dict[str, Any]:
        """Get permission enforcement analytics."""
        try:
            analytics = await self.permission_middleware.get_permission_analytics()
            return {
                "success": True,
                "analytics": analytics,
                "retrieved_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get permission analytics: {e}")
            return {"success": False, "error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """RBAC system health check."""
        try:
            total_roles = len(self.rbac_manager.roles)
            active_roles = sum(1 for role in self.rbac_manager.roles.values() if role.active)
            total_assignments = sum(len(assignments) for assignments in self.rbac_manager.user_assignments.values())
            
            return {
                "success": True,
                "status": "healthy",
                "rbac_manager": {
                    "total_roles": total_roles,
                    "active_roles": active_roles,
                    "total_assignments": total_assignments
                },
                "permission_middleware": {
                    "registered_endpoints": len(self.permission_middleware.endpoint_permissions),
                    "cache_enabled": self.permission_middleware.cache_enabled
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "success": False,
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }