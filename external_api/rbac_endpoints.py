#!/usr/bin/env python3
"""
RBAC API Endpoints

REST API endpoints for role-based access control management including
role creation, assignment, permission management, and analytics.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import json
import uuid

from fastapi import FastAPI, HTTPException, Depends, Query, Path, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from enum import Enum

from security.rbac_manager import RBACManager, RoleType, PermissionType, RoleDefinition, UserRoleAssignment
from security.permission_middleware import PermissionMiddleware, PermissionContext
from security.auth_service import AuthenticationService
from config.auth_models import AuthResult


logger = logging.getLogger(__name__)


# Pydantic models for API requests/responses

class RoleTypeEnum(str, Enum):
    """Role type enumeration for API."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    AGENT = "agent"
    USER = "user"
    GUEST = "guest"


class PermissionTypeEnum(str, Enum):
    """Permission type enumeration for API."""
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITORING = "system:monitoring"
    USER_MANAGEMENT = "user:management"
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    AGENT_MANAGEMENT = "agent:management"
    AGENT_SPAWN = "agent:spawn"
    AGENT_CONTROL = "agent:control"
    AGENT_MONITOR = "agent:monitor"
    AGENT_TERMINATE = "agent:terminate"
    TASK_EXECUTION = "task:execution"
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    API_GATEWAY = "api:gateway"
    API_ADMIN = "api:admin"
    API_READ = "api:read"
    API_WRITE = "api:write"
    PUBLIC_ACCESS = "public:access"
    READ_ONLY = "read:only"


class CreateRoleRequest(BaseModel):
    """Request model for creating a role."""
    role_type: RoleTypeEnum
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    permissions: List[PermissionTypeEnum]
    inherits_from: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class UpdateRoleRequest(BaseModel):
    """Request model for updating a role."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    permissions: Optional[List[PermissionTypeEnum]] = None
    active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class AssignRoleRequest(BaseModel):
    """Request model for assigning role to user."""
    user_id: str = Field(..., min_length=1)
    role_id: str = Field(..., min_length=1)
    expires_at: Optional[datetime] = None
    context_constraints: Optional[Dict[str, Any]] = None


class RevokeRoleRequest(BaseModel):
    """Request model for revoking role from user."""
    user_id: str = Field(..., min_length=1)
    role_id: str = Field(..., min_length=1)


class CheckPermissionRequest(BaseModel):
    """Request model for checking user permission."""
    user_id: str = Field(..., min_length=1)
    permission: PermissionTypeEnum
    context: Optional[Dict[str, Any]] = None


class BulkPermissionCheckRequest(BaseModel):
    """Request model for bulk permission checking."""
    user_id: str = Field(..., min_length=1)
    permissions: List[PermissionTypeEnum]


class RoleResponse(BaseModel):
    """Response model for role information."""
    role_id: str
    role_type: RoleTypeEnum
    name: str
    description: str
    permissions: List[PermissionTypeEnum]
    inherits_from: List[str]
    created_at: datetime
    updated_at: datetime
    created_by: str
    active: bool
    metadata: Dict[str, Any]


class UserRoleResponse(BaseModel):
    """Response model for user role assignment."""
    assignment_id: str
    user_id: str
    role_id: str
    role_name: str
    assigned_by: str
    assigned_at: datetime
    expires_at: Optional[datetime]
    active: bool
    context_constraints: Dict[str, Any]


class PermissionCheckResponse(BaseModel):
    """Response model for permission check."""
    user_id: str
    permission: PermissionTypeEnum
    granted: bool
    reason: str
    role_sources: List[str]
    checked_at: datetime
    metadata: Dict[str, Any]


class RBACEndpoints:
    """
    RBAC API endpoints for role and permission management.
    
    Provides comprehensive REST API for:
    - Role lifecycle management (CRUD)
    - User role assignments
    - Permission checking and validation
    - RBAC analytics and reporting
    """
    
    def __init__(self, rbac_manager: RBACManager, 
                 permission_middleware: PermissionMiddleware,
                 auth_service: AuthenticationService):
        """Initialize RBAC endpoints."""
        self.rbac_manager = rbac_manager
        self.permission_middleware = permission_middleware
        self.auth_service = auth_service
        
        logger.info("RBACEndpoints initialized")
    
    def setup_routes(self, app: FastAPI) -> None:
        """Set up RBAC routes on FastAPI app."""
        
        # Role management endpoints
        app.post("/api/v1/rbac/roles", response_model=RoleResponse)(self.create_role)
        app.get("/api/v1/rbac/roles", response_model=List[RoleResponse])(self.list_roles)
        app.get("/api/v1/rbac/roles/{role_id}", response_model=RoleResponse)(self.get_role)
        app.put("/api/v1/rbac/roles/{role_id}", response_model=RoleResponse)(self.update_role)
        app.delete("/api/v1/rbac/roles/{role_id}")(self.delete_role)
        
        # User role assignment endpoints
        app.post("/api/v1/rbac/assign-role")(self.assign_role)
        app.post("/api/v1/rbac/revoke-role")(self.revoke_role)
        app.get("/api/v1/rbac/users/{user_id}/roles", response_model=List[UserRoleResponse])(self.get_user_roles)
        app.get("/api/v1/rbac/roles/{role_id}/users")(self.get_role_users)
        
        # Permission checking endpoints
        app.post("/api/v1/rbac/check-permission", response_model=PermissionCheckResponse)(self.check_permission)
        app.post("/api/v1/rbac/check-permissions-bulk")(self.check_permissions_bulk)
        app.get("/api/v1/rbac/users/{user_id}/permissions")(self.get_user_permissions)
        app.get("/api/v1/rbac/users/{user_id}/accessible-endpoints")(self.get_user_accessible_endpoints)
        
        # Analytics and reporting endpoints
        app.get("/api/v1/rbac/analytics")(self.get_rbac_analytics)
        app.get("/api/v1/rbac/audit-log")(self.get_audit_log)
        app.get("/api/v1/rbac/permission-analytics")(self.get_permission_analytics)
        
        # System endpoints
        app.get("/api/v1/rbac/system/health")(self.health_check)
        
        logger.info("RBAC routes registered")
    
    async def create_role(self, request: CreateRoleRequest) -> RoleResponse:
        """Create a new role."""
        try:
            # Convert enum types
            role_type = RoleType(request.role_type.value)
            permissions = [PermissionType(p.value) for p in request.permissions]
            
            # Create role
            success, message, role = await self.rbac_manager.create_role(
                role_type=role_type,
                name=request.name,
                description=request.description,
                permissions=permissions,
                inherits_from=request.inherits_from,
                created_by="api_user"  # Would be extracted from auth context
            )
            
            if not success:
                raise HTTPException(status_code=400, detail=message)
            
            # Convert response
            return RoleResponse(
                role_id=role.role_id,
                role_type=RoleTypeEnum(role.role_type.value),
                name=role.name,
                description=role.description,
                permissions=[PermissionTypeEnum(p.value) for p in role.permissions],
                inherits_from=role.inherits_from,
                created_at=role.created_at,
                updated_at=role.updated_at,
                created_by=role.created_by,
                active=role.active,
                metadata=role.metadata
            )
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid input: {e}")
        except Exception as e:
            logger.error(f"Failed to create role: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def list_roles(self, active_only: bool = True) -> List[RoleResponse]:
        """List all roles."""
        try:
            roles = await self.rbac_manager.list_roles(active_only=active_only)
            
            return [
                RoleResponse(
                    role_id=role.role_id,
                    role_type=RoleTypeEnum(role.role_type.value),
                    name=role.name,
                    description=role.description,
                    permissions=[PermissionTypeEnum(p.value) for p in role.permissions],
                    inherits_from=role.inherits_from,
                    created_at=role.created_at,
                    updated_at=role.updated_at,
                    created_by=role.created_by,
                    active=role.active,
                    metadata=role.metadata
                )
                for role in roles
            ]
            
        except Exception as e:
            logger.error(f"Failed to list roles: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_role(self, role_id: str = Path(..., description="Role ID"),
                      current_user: dict = Depends(self._get_current_user)) -> RoleResponse:
        """Get role by ID."""
        try:
            role = await self.rbac_manager.get_role(role_id)
            
            if not role:
                raise HTTPException(status_code=404, detail="Role not found")
            
            return RoleResponse(
                role_id=role.role_id,
                role_type=RoleTypeEnum(role.role_type.value),
                name=role.name,
                description=role.description,
                permissions=[PermissionTypeEnum(p.value) for p in role.permissions],
                inherits_from=role.inherits_from,
                created_at=role.created_at,
                updated_at=role.updated_at,
                created_by=role.created_by,
                active=role.active,
                metadata=role.metadata
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get role {role_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_role(self, role_id: str = Path(..., description="Role ID"),
                         request: UpdateRoleRequest = Body(...),
                         current_user: dict = Depends(self._get_current_user)) -> RoleResponse:
        """Update role."""
        try:
            # Prepare updates dictionary
            updates = {}
            if request.name is not None:
                updates["name"] = request.name
            if request.description is not None:
                updates["description"] = request.description
            if request.permissions is not None:
                updates["permissions"] = [PermissionType(p.value) for p in request.permissions]
            if request.active is not None:
                updates["active"] = request.active
            if request.metadata is not None:
                updates["metadata"] = request.metadata
            
            # Update role
            success, message = await self.rbac_manager.update_role(
                role_id=role_id,
                updates=updates,
                updated_by=current_user["user_id"]
            )
            
            if not success:
                raise HTTPException(status_code=400, detail=message)
            
            # Get updated role
            role = await self.rbac_manager.get_role(role_id)
            
            return RoleResponse(
                role_id=role.role_id,
                role_type=RoleTypeEnum(role.role_type.value),
                name=role.name,
                description=role.description,
                permissions=[PermissionTypeEnum(p.value) for p in role.permissions],
                inherits_from=role.inherits_from,
                created_at=role.created_at,
                updated_at=role.updated_at,
                created_by=role.created_by,
                active=role.active,
                metadata=role.metadata
            )
            
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid input: {e}")
        except Exception as e:
            logger.error(f"Failed to update role {role_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_role(self, role_id: str = Path(..., description="Role ID"),
                         force: bool = Query(False, description="Force delete even if assigned to users"),
                         current_user: dict = Depends(self._get_current_user)) -> dict:
        """Delete role."""
        try:
            success, message = await self.rbac_manager.delete_role(
                role_id=role_id,
                deleted_by=current_user["user_id"],
                force=force
            )
            
            if not success:
                raise HTTPException(status_code=400, detail=message)
            
            return {"message": "Role deleted successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete role {role_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def assign_role(self, request: AssignRoleRequest,
                         current_user: dict = Depends(self._get_current_user)) -> dict:
        """Assign role to user."""
        try:
            success, message = await self.rbac_manager.assign_role_to_user(
                user_id=request.user_id,
                role_id=request.role_id,
                assigned_by=current_user["user_id"],
                expires_at=request.expires_at,
                context_constraints=request.context_constraints
            )
            
            if not success:
                raise HTTPException(status_code=400, detail=message)
            
            return {"message": message}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to assign role: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def revoke_role(self, request: RevokeRoleRequest,
                         current_user: dict = Depends(self._get_current_user)) -> dict:
        """Revoke role from user."""
        try:
            success, message = await self.rbac_manager.revoke_role_from_user(
                user_id=request.user_id,
                role_id=request.role_id,
                revoked_by=current_user["user_id"]
            )
            
            if not success:
                raise HTTPException(status_code=400, detail=message)
            
            return {"message": message}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to revoke role: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_user_roles(self, user_id: str = Path(..., description="User ID"),
                            include_expired: bool = Query(False, description="Include expired roles"),
                            current_user: dict = Depends(self._get_current_user)) -> List[UserRoleResponse]:
        """Get roles assigned to user."""
        try:
            roles = await self.rbac_manager.get_user_roles(user_id, include_expired=include_expired)
            
            # Get assignments for detailed response
            assignments = self.rbac_manager.user_assignments.get(user_id, [])
            current_time = datetime.utcnow()
            
            result = []
            for role in roles:
                # Find corresponding assignment
                assignment = None
                for assign in assignments:
                    if (assign.role_id == role.role_id and 
                        assign.active and
                        (include_expired or not assign.expires_at or assign.expires_at > current_time)):
                        assignment = assign
                        break
                
                if assignment:
                    result.append(UserRoleResponse(
                        assignment_id=assignment.assignment_id,
                        user_id=assignment.user_id,
                        role_id=role.role_id,
                        role_name=role.name,
                        assigned_by=assignment.assigned_by,
                        assigned_at=assignment.assigned_at,
                        expires_at=assignment.expires_at,
                        active=assignment.active,
                        context_constraints=assignment.context_constraints
                    ))
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get user roles for {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def check_permission(self, request: CheckPermissionRequest,
                              current_user: dict = Depends(self._get_current_user)) -> PermissionCheckResponse:
        """Check if user has specific permission."""
        try:
            permission = PermissionType(request.permission.value)
            
            result = await self.rbac_manager.check_permission(
                user_id=request.user_id,
                permission=permission,
                context=request.context
            )
            
            return PermissionCheckResponse(
                user_id=result.user_id,
                permission=PermissionTypeEnum(result.permission.value),
                granted=result.granted,
                reason=result.reason,
                role_sources=result.role_sources,
                checked_at=result.checked_at,
                metadata=result.metadata
            )
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid permission: {e}")
        except Exception as e:
            logger.error(f"Failed to check permission: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def check_permissions_bulk(self, request: BulkPermissionCheckRequest,
                                    current_user: dict = Depends(self._get_current_user)) -> dict:
        """Check multiple permissions for user."""
        try:
            permissions = [PermissionType(p.value) for p in request.permissions]
            
            results = {}
            for permission in permissions:
                check_result = await self.rbac_manager.check_permission(
                    user_id=request.user_id,
                    permission=permission
                )
                results[permission.value] = {
                    "granted": check_result.granted,
                    "reason": check_result.reason,
                    "role_sources": check_result.role_sources
                }
            
            return {
                "user_id": request.user_id,
                "permissions": results,
                "checked_at": datetime.utcnow().isoformat()
            }
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid permissions: {e}")
        except Exception as e:
            logger.error(f"Failed bulk permission check: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_user_permissions(self, user_id: str = Path(..., description="User ID"),
                                  current_user: dict = Depends(self._get_current_user)) -> dict:
        """Get all effective permissions for user."""
        try:
            permissions = await self.rbac_manager.get_user_permissions(user_id)
            
            return {
                "user_id": user_id,
                "permissions": [p.value for p in permissions],
                "total_permissions": len(permissions),
                "retrieved_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get user permissions for {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_user_accessible_endpoints(self, user_id: str = Path(..., description="User ID"),
                                           current_user: dict = Depends(self._get_current_user)) -> dict:
        """Get endpoints accessible to user."""
        try:
            accessible_endpoints = await self.permission_middleware.get_user_accessible_endpoints(user_id)
            
            endpoints_data = []
            for endpoint in accessible_endpoints:
                endpoints_data.append({
                    "endpoint": endpoint.endpoint,
                    "method": endpoint.method,
                    "description": endpoint.description,
                    "required_permissions": [p.value for p in endpoint.required_permissions]
                })
            
            return {
                "user_id": user_id,
                "accessible_endpoints": endpoints_data,
                "total_endpoints": len(endpoints_data),
                "retrieved_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get accessible endpoints for {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_rbac_analytics(self, current_user: dict = Depends(self._get_current_user)) -> dict:
        """Get RBAC analytics and statistics."""
        try:
            analytics = await self.rbac_manager.get_rbac_analytics()
            return {
                **analytics,
                "retrieved_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get RBAC analytics: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_permission_analytics(self, current_user: dict = Depends(self._get_current_user)) -> dict:
        """Get permission enforcement analytics."""
        try:
            analytics = await self.permission_middleware.get_permission_analytics()
            return {
                **analytics,
                "retrieved_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get permission analytics: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_audit_log(self, limit: int = Query(100, ge=1, le=1000, description="Number of events to return"),
                           event_type: Optional[str] = Query(None, description="Filter by event type"),
                           user_id: Optional[str] = Query(None, description="Filter by user ID"),
                           current_user: dict = Depends(self._get_current_user)) -> dict:
        """Get RBAC audit log."""
        try:
            # Filter audit log
            audit_events = self.rbac_manager.audit_log
            
            if event_type:
                audit_events = [e for e in audit_events if e.get("action") == event_type]
            
            if user_id:
                audit_events = [e for e in audit_events if e.get("user_id") == user_id]
            
            # Sort by timestamp (newest first) and limit
            audit_events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            audit_events = audit_events[:limit]
            
            return {
                "events": audit_events,
                "total_events": len(audit_events),
                "filters_applied": {
                    "event_type": event_type,
                    "user_id": user_id,
                    "limit": limit
                },
                "retrieved_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get audit log: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def health_check(self) -> dict:
        """RBAC system health check."""
        try:
            # Basic health checks
            total_roles = len(self.rbac_manager.roles)
            active_roles = sum(1 for role in self.rbac_manager.roles.values() if role.active)
            total_assignments = sum(len(assignments) for assignments in self.rbac_manager.user_assignments.values())
            
            health_status = {
                "status": "healthy",
                "rbac_manager": {
                    "total_roles": total_roles,
                    "active_roles": active_roles,
                    "total_assignments": total_assignments
                },
                "permission_middleware": {
                    "registered_endpoints": len(self.permission_middleware.endpoint_permissions),
                    "cache_enabled": self.permission_middleware.cache_enabled,
                    "performance_stats": self.permission_middleware.performance_stats
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # Helper methods
    
    async def _get_current_user(self) -> dict:
        """
        Extract current user from authentication context.
        This would be implemented based on your authentication middleware.
        """
        # Placeholder implementation - in reality this would extract from request context
        return {
            "user_id": "current_user_id",
            "username": "current_user",
            "roles": ["admin"]
        }
    
    async def _require_permission(self, permission: PermissionType, user: dict) -> bool:
        """Check if current user has required permission."""
        result = await self.rbac_manager.check_permission(
            user_id=user["user_id"],
            permission=permission
        )
        return result.granted