#!/usr/bin/env python3
"""
API Key Management System

Enterprise-grade API key management with comprehensive security features including
key rotation, access control, usage analytics, and integration with RBAC for
LeanVibe Agent Hive.
"""

import asyncio
import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config.auth_models import Permission, AuthResult
from security.security_manager import SecurityManager
from security.rate_limiter import RateLimiter


logger = logging.getLogger(__name__)


class ApiKeyType(Enum):
    """API key types for different use cases."""
    PERSONAL = "personal"
    SERVICE = "service"
    INTEGRATION = "integration"
    WEBHOOK = "webhook"
    TEMPORARY = "temporary"
    LEGACY = "legacy"


class ApiKeyStatus(Enum):
    """API key status for lifecycle management."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"
    PENDING_ROTATION = "pending_rotation"


class ApiKeyScope(Enum):
    """API key access scopes."""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"
    SERVICE_ACCOUNT = "service_account"
    INTEGRATION = "integration"
    CUSTOM = "custom"


@dataclass
class ApiKeyMetadata:
    """API key metadata and configuration."""
    key_id: str
    user_id: str
    name: str
    description: str
    key_type: ApiKeyType
    status: ApiKeyStatus
    scope: ApiKeyScope
    permissions: List[Permission]
    created_at: datetime
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
    usage_count: int = 0
    rate_limit_tier: str = "default"
    allowed_ips: Set[str] = None
    allowed_domains: Set[str] = None
    rotation_schedule_days: Optional[int] = None
    last_rotated: Optional[datetime] = None
    created_by: str = "system"
    tags: Set[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.allowed_ips is None:
            self.allowed_ips = set()
        if self.allowed_domains is None:
            self.allowed_domains = set()
        if self.tags is None:
            self.tags = set()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ApiKeyUsage:
    """API key usage tracking."""
    usage_id: str
    key_id: str
    user_id: str
    timestamp: datetime
    endpoint: str
    method: str
    status_code: int
    ip_address: str
    user_agent: str
    response_time_ms: float
    bytes_transferred: int = 0
    error_message: Optional[str] = None


@dataclass
class ApiKeyRotationRecord:
    """API key rotation history."""
    rotation_id: str
    key_id: str
    old_key_hash: str
    new_key_hash: str
    rotated_at: datetime
    rotated_by: str
    rotation_reason: str
    auto_rotation: bool = False


class ApiKeyManager:
    """
    Comprehensive API key management system with enterprise security features.
    
    Features:
    - Secure API key generation and storage
    - Key rotation and lifecycle management
    - Fine-grained permission and scope control
    - Usage analytics and monitoring
    - Rate limiting integration
    - IP and domain restrictions
    - Automatic rotation scheduling
    - Integration with RBAC system
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, 
                 security_manager: Optional[SecurityManager] = None,
                 rate_limiter: Optional[RateLimiter] = None):
        """Initialize API key manager."""
        self.config = config or self._get_default_config()
        self.security_manager = security_manager or SecurityManager()
        self.rate_limiter = rate_limiter
        
        # Initialize encryption for key storage
        self.encryption_key = self._derive_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Storage for API key data (in production, use database)
        self.api_keys: Dict[str, ApiKeyMetadata] = {}  # key_id -> metadata
        self.key_hashes: Dict[str, str] = {}  # key_hash -> key_id
        self.usage_logs: List[ApiKeyUsage] = []
        self.rotation_history: List[ApiKeyRotationRecord] = []
        self.security_events: List[Dict[str, Any]] = []
        
        # Rate limiting tiers
        self.rate_limit_tiers = {
            "basic": {"requests_per_hour": 1000, "burst_limit": 50},
            "standard": {"requests_per_hour": 5000, "burst_limit": 100},
            "premium": {"requests_per_hour": 20000, "burst_limit": 200},
            "enterprise": {"requests_per_hour": 100000, "burst_limit": 500},
            "unlimited": {"requests_per_hour": -1, "burst_limit": -1}
        }
        
        # Start background tasks
        self._start_background_tasks()
        
        logger.info("ApiKeyManager initialized")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default API key configuration."""
        return {
            "key_length": 32,
            "default_expiry_days": 365,
            "max_keys_per_user": 50,
            "auto_rotation_enabled": True,
            "default_rotation_days": 90,
            "usage_log_retention_days": 180,
            "rate_limit_tier": "standard",
            "encryption_salt": "api-key-salt-change-in-production"
        }
    
    def _derive_encryption_key(self) -> bytes:
        """Derive encryption key for API key storage."""
        salt = self.config.get("encryption_salt", "default-salt").encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return Fernet.generate_key()
    
    async def create_api_key(self, user_id: str, name: str, description: str,
                           key_type: ApiKeyType, scope: ApiKeyScope,
                           permissions: List[Permission],
                           expires_in_days: Optional[int] = None,
                           allowed_ips: Optional[List[str]] = None,
                           allowed_domains: Optional[List[str]] = None,
                           rate_limit_tier: str = "standard",
                           tags: Optional[List[str]] = None,
                           created_by: str = "system") -> Tuple[bool, str, Optional[str]]:
        """
        Create a new API key with specified permissions and restrictions.
        
        Returns:
            Tuple of (success, message, api_key)
        """
        try:
            # Check user's key limit
            user_keys = [key for key in self.api_keys.values() if key.user_id == user_id and key.status == ApiKeyStatus.ACTIVE]
            if len(user_keys) >= self.config.get("max_keys_per_user", 50):
                return False, "Maximum number of API keys reached for user", None
            
            # Generate API key
            api_key = self._generate_api_key()
            key_id = str(uuid.uuid4())
            key_hash = self._hash_api_key(api_key)
            
            # Calculate expiration
            current_time = datetime.utcnow()
            if expires_in_days:
                expires_at = current_time + timedelta(days=expires_in_days)
            else:
                expires_at = current_time + timedelta(days=self.config.get("default_expiry_days", 365))
            
            # Create metadata
            metadata = ApiKeyMetadata(
                key_id=key_id,
                user_id=user_id,
                name=name,
                description=description,
                key_type=key_type,
                status=ApiKeyStatus.ACTIVE,
                scope=scope,
                permissions=permissions,
                created_at=current_time,
                expires_at=expires_at,
                last_used=None,
                rate_limit_tier=rate_limit_tier,
                allowed_ips=set(allowed_ips or []),
                allowed_domains=set(allowed_domains or []),
                created_by=created_by,
                tags=set(tags or [])
            )
            
            # Store key metadata
            self.api_keys[key_id] = metadata
            self.key_hashes[key_hash] = key_id
            
            # Set up rate limiting if rate limiter is available
            if self.rate_limiter:
                tier_config = self.rate_limit_tiers.get(rate_limit_tier, self.rate_limit_tiers["standard"])
                await self._setup_rate_limiting(key_id, tier_config)
            
            # Log security event
            await self._log_security_event({
                "event_type": "api_key_created",
                "key_id": key_id,
                "user_id": user_id,
                "name": name,
                "key_type": key_type.value,
                "scope": scope.value,
                "expires_at": expires_at.isoformat(),
                "created_by": created_by,
                "timestamp": current_time.isoformat()
            })
            
            logger.info(f"API key created: {name} ({key_id}) for user {user_id}")
            return True, "API key created successfully", api_key
            
        except Exception as e:
            logger.error(f"Failed to create API key for user {user_id}: {e}")
            return False, f"API key creation failed: {e}", None
    
    async def validate_api_key(self, api_key: str, endpoint: str, method: str,
                             client_ip: str, user_agent: str) -> AuthResult:
        """Validate API key and check permissions."""
        try:
            # Hash the provided key
            key_hash = self._hash_api_key(api_key)
            
            # Find key metadata
            key_id = self.key_hashes.get(key_hash)
            if not key_id:
                await self._log_security_event({
                    "event_type": "api_key_validation_failed",
                    "reason": "key_not_found",
                    "endpoint": endpoint,
                    "method": method,
                    "client_ip": client_ip,
                    "timestamp": datetime.utcnow().isoformat()
                })
                return AuthResult(success=False, error="Invalid API key")
            
            metadata = self.api_keys.get(key_id)
            if not metadata:
                return AuthResult(success=False, error="API key metadata not found")
            
            # Check key status
            if metadata.status != ApiKeyStatus.ACTIVE:
                await self._log_security_event({
                    "event_type": "api_key_validation_failed",
                    "key_id": key_id,
                    "user_id": metadata.user_id,
                    "reason": f"key_status_{metadata.status.value}",
                    "endpoint": endpoint,
                    "client_ip": client_ip,
                    "timestamp": datetime.utcnow().isoformat()
                })
                return AuthResult(success=False, error=f"API key is {metadata.status.value}")
            
            # Check expiration
            current_time = datetime.utcnow()
            if metadata.expires_at and current_time > metadata.expires_at:
                metadata.status = ApiKeyStatus.EXPIRED
                await self._log_security_event({
                    "event_type": "api_key_expired",
                    "key_id": key_id,
                    "user_id": metadata.user_id,
                    "timestamp": current_time.isoformat()
                })
                return AuthResult(success=False, error="API key has expired")
            
            # Check IP restrictions
            if metadata.allowed_ips and client_ip not in metadata.allowed_ips:
                await self._log_security_event({
                    "event_type": "api_key_ip_restriction_violation",
                    "key_id": key_id,
                    "user_id": metadata.user_id,
                    "client_ip": client_ip,
                    "allowed_ips": list(metadata.allowed_ips),
                    "timestamp": current_time.isoformat()
                })
                return AuthResult(success=False, error="IP address not allowed")
            
            # Check rate limiting
            if self.rate_limiter:
                rate_limit_result = await self._check_rate_limit(key_id, client_ip)
                if not rate_limit_result:
                    await self._log_security_event({
                        "event_type": "api_key_rate_limit_exceeded",
                        "key_id": key_id,
                        "user_id": metadata.user_id,
                        "client_ip": client_ip,
                        "timestamp": current_time.isoformat()
                    })
                    return AuthResult(success=False, error="Rate limit exceeded")
            
            # Update usage statistics
            await self._record_api_key_usage(metadata, endpoint, method, client_ip, user_agent)
            
            # Return successful validation result
            return AuthResult(
                success=True,
                user_id=metadata.user_id,
                permissions=metadata.permissions,
                metadata={
                    "key_id": key_id,
                    "key_name": metadata.name,
                    "key_type": metadata.key_type.value,
                    "scope": metadata.scope.value,
                    "rate_limit_tier": metadata.rate_limit_tier,
                    "usage_count": metadata.usage_count,
                    "last_used": metadata.last_used.isoformat() if metadata.last_used else None
                }
            )
            
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return AuthResult(success=False, error="API key validation failed")
    
    async def rotate_api_key(self, key_id: str, rotated_by: str, 
                           rotation_reason: str = "manual_rotation") -> Tuple[bool, str, Optional[str]]:
        """Rotate an API key, generating a new key while maintaining metadata."""
        try:
            # Get current key metadata
            metadata = self.api_keys.get(key_id)
            if not metadata:
                return False, "API key not found", None
            
            if metadata.status != ApiKeyStatus.ACTIVE:
                return False, f"Cannot rotate {metadata.status.value} key", None
            
            # Generate new API key
            new_api_key = self._generate_api_key()
            new_key_hash = self._hash_api_key(new_api_key)
            
            # Find and update old key hash
            old_key_hash = None
            for hash_key, stored_key_id in self.key_hashes.items():
                if stored_key_id == key_id:
                    old_key_hash = hash_key
                    break
            
            if old_key_hash:
                del self.key_hashes[old_key_hash]
            
            # Update key hash mapping
            self.key_hashes[new_key_hash] = key_id
            
            # Update metadata
            current_time = datetime.utcnow()
            metadata.last_rotated = current_time
            metadata.status = ApiKeyStatus.ACTIVE  # Ensure it's still active
            
            # Record rotation
            rotation_record = ApiKeyRotationRecord(
                rotation_id=str(uuid.uuid4()),
                key_id=key_id,
                old_key_hash=old_key_hash or "unknown",
                new_key_hash=new_key_hash,
                rotated_at=current_time,
                rotated_by=rotated_by,
                rotation_reason=rotation_reason,
                auto_rotation=rotated_by == "system"
            )
            self.rotation_history.append(rotation_record)
            
            # Log security event
            await self._log_security_event({
                "event_type": "api_key_rotated",
                "key_id": key_id,
                "user_id": metadata.user_id,
                "name": metadata.name,
                "rotation_reason": rotation_reason,
                "rotated_by": rotated_by,
                "auto_rotation": rotated_by == "system",
                "timestamp": current_time.isoformat()
            })
            
            logger.info(f"API key rotated: {metadata.name} ({key_id}) by {rotated_by}")
            return True, "API key rotated successfully", new_api_key
            
        except Exception as e:
            logger.error(f"Failed to rotate API key {key_id}: {e}")
            return False, f"API key rotation failed: {e}", None
    
    async def revoke_api_key(self, key_id: str, revoked_by: str, 
                           revocation_reason: str = "manual_revocation") -> Tuple[bool, str]:
        """Revoke an API key."""
        try:
            # Get key metadata
            metadata = self.api_keys.get(key_id)
            if not metadata:
                return False, "API key not found"
            
            # Update status
            metadata.status = ApiKeyStatus.REVOKED
            
            # Remove from hash mapping
            hash_to_remove = None
            for hash_key, stored_key_id in self.key_hashes.items():
                if stored_key_id == key_id:
                    hash_to_remove = hash_key
                    break
            
            if hash_to_remove:
                del self.key_hashes[hash_to_remove]
            
            # Log security event
            await self._log_security_event({
                "event_type": "api_key_revoked",
                "key_id": key_id,
                "user_id": metadata.user_id,
                "name": metadata.name,
                "revocation_reason": revocation_reason,
                "revoked_by": revoked_by,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"API key revoked: {metadata.name} ({key_id}) by {revoked_by}")
            return True, "API key revoked successfully"
            
        except Exception as e:
            logger.error(f"Failed to revoke API key {key_id}: {e}")
            return False, f"API key revocation failed: {e}"
    
    async def get_user_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all API keys for a user."""
        user_keys = [key for key in self.api_keys.values() if key.user_id == user_id]
        
        return [
            {
                "key_id": key.key_id,
                "name": key.name,
                "description": key.description,
                "key_type": key.key_type.value,
                "status": key.status.value,
                "scope": key.scope.value,
                "created_at": key.created_at.isoformat(),
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                "last_used": key.last_used.isoformat() if key.last_used else None,
                "usage_count": key.usage_count,
                "rate_limit_tier": key.rate_limit_tier,
                "allowed_ips": list(key.allowed_ips),
                "allowed_domains": list(key.allowed_domains),
                "tags": list(key.tags),
                "last_rotated": key.last_rotated.isoformat() if key.last_rotated else None
            }
            for key in user_keys
        ]
    
    async def get_api_key_usage(self, key_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get usage history for an API key."""
        key_usage = [
            usage for usage in self.usage_logs
            if usage.key_id == key_id
        ]
        
        # Sort by timestamp (most recent first) and limit
        key_usage.sort(key=lambda x: x.timestamp, reverse=True)
        key_usage = key_usage[:limit]
        
        return [
            {
                "usage_id": usage.usage_id,
                "timestamp": usage.timestamp.isoformat(),
                "endpoint": usage.endpoint,
                "method": usage.method,
                "status_code": usage.status_code,
                "ip_address": usage.ip_address,
                "response_time_ms": usage.response_time_ms,
                "bytes_transferred": usage.bytes_transferred,
                "error_message": usage.error_message
            }
            for usage in key_usage
        ]
    
    async def update_api_key_permissions(self, key_id: str, permissions: List[Permission],
                                       updated_by: str) -> Tuple[bool, str]:
        """Update API key permissions."""
        try:
            metadata = self.api_keys.get(key_id)
            if not metadata:
                return False, "API key not found"
            
            if metadata.status != ApiKeyStatus.ACTIVE:
                return False, f"Cannot update {metadata.status.value} key"
            
            old_permissions = metadata.permissions.copy()
            metadata.permissions = permissions
            
            # Log security event
            await self._log_security_event({
                "event_type": "api_key_permissions_updated",
                "key_id": key_id,
                "user_id": metadata.user_id,
                "name": metadata.name,
                "old_permissions": [p.value for p in old_permissions],
                "new_permissions": [p.value for p in permissions],
                "updated_by": updated_by,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return True, "API key permissions updated successfully"
            
        except Exception as e:
            logger.error(f"Failed to update permissions for API key {key_id}: {e}")
            return False, f"Permission update failed: {e}"
    
    async def schedule_key_rotation(self, key_id: str, rotation_days: int) -> Tuple[bool, str]:
        """Schedule automatic rotation for an API key."""
        try:
            metadata = self.api_keys.get(key_id)
            if not metadata:
                return False, "API key not found"
            
            metadata.rotation_schedule_days = rotation_days
            
            # Log security event
            await self._log_security_event({
                "event_type": "api_key_rotation_scheduled",
                "key_id": key_id,
                "user_id": metadata.user_id,
                "rotation_days": rotation_days,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return True, f"Key rotation scheduled every {rotation_days} days"
            
        except Exception as e:
            logger.error(f"Failed to schedule rotation for API key {key_id}: {e}")
            return False, f"Rotation scheduling failed: {e}"
    
    # Private helper methods
    
    def _generate_api_key(self) -> str:
        """Generate a secure API key."""
        key_length = self.config.get("key_length", 32)
        return f"ak_{secrets.token_urlsafe(key_length)}"
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash an API key for secure storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    async def _setup_rate_limiting(self, key_id: str, tier_config: Dict[str, int]) -> None:
        """Set up rate limiting for an API key."""
        if not self.rate_limiter:
            return
        
        # Configure rate limiting based on tier
        if tier_config.get("requests_per_hour", 0) > 0:
            await self.rate_limiter.configure_rate_limit(
                key=f"api_key:{key_id}",
                limit=tier_config["requests_per_hour"],
                window_seconds=3600
            )
    
    async def _check_rate_limit(self, key_id: str, client_ip: str) -> bool:
        """Check rate limit for API key."""
        if not self.rate_limiter:
            return True
        
        # Check both key-based and IP-based rate limits
        key_limit_ok = await self.rate_limiter.check_rate_limit(f"api_key:{key_id}")
        ip_limit_ok = await self.rate_limiter.check_rate_limit(f"api_ip:{client_ip}")
        
        return key_limit_ok and ip_limit_ok
    
    async def _record_api_key_usage(self, metadata: ApiKeyMetadata, endpoint: str, 
                                  method: str, client_ip: str, user_agent: str) -> None:
        """Record API key usage."""
        current_time = datetime.utcnow()
        
        # Update metadata
        metadata.last_used = current_time
        metadata.usage_count += 1
        
        # Create usage record
        usage = ApiKeyUsage(
            usage_id=str(uuid.uuid4()),
            key_id=metadata.key_id,
            user_id=metadata.user_id,
            timestamp=current_time,
            endpoint=endpoint,
            method=method,
            status_code=200,  # Would be set by actual API response
            ip_address=client_ip,
            user_agent=user_agent,
            response_time_ms=0.0  # Would be measured in actual implementation
        )
        
        self.usage_logs.append(usage)
        
        # Keep only recent usage logs
        retention_days = self.config.get("usage_log_retention_days", 180)
        cutoff_date = current_time - timedelta(days=retention_days)
        self.usage_logs = [
            log for log in self.usage_logs
            if log.timestamp > cutoff_date
        ]
    
    async def _log_security_event(self, event: Dict[str, Any]) -> None:
        """Log security event."""
        event["event_id"] = str(uuid.uuid4())
        self.security_events.append(event)
        
        # Keep only last 5000 events
        if len(self.security_events) > 5000:
            self.security_events = self.security_events[-2500:]
        
        # Integrate with security manager
        if self.security_manager and hasattr(self.security_manager, 'log_security_event'):
            try:
                # Try new signature first, fallback to dict
                if hasattr(self.security_manager, '_log_security_event'):
                    self.security_manager._log_security_event(
                        event.get("user_id", "system"),
                        event.get("session_id", "default"),
                        event.get("event_type", "security_event"),
                        event.get("action", "api_key_operation"),
                        "success",
                        getattr(self.security_manager, 'RiskLevel', type('RiskLevel', (), {'LOW': 'low'})).LOW,
                        event
                    )
                else:
                    # Fallback - just log the event
                    logger.info(f"Security event: {event}")
            except Exception as e:
                logger.debug(f"Could not log to security manager: {e}")
    
    def _start_background_tasks(self) -> None:
        """Start background maintenance tasks."""
        async def auto_rotate_keys():
            """Automatically rotate keys based on schedule."""
            while True:
                try:
                    current_time = datetime.utcnow()
                    
                    for metadata in self.api_keys.values():
                        if (metadata.status == ApiKeyStatus.ACTIVE and
                            metadata.rotation_schedule_days and
                            metadata.last_rotated):
                            
                            days_since_rotation = (current_time - metadata.last_rotated).days
                            if days_since_rotation >= metadata.rotation_schedule_days:
                                await self.rotate_api_key(
                                    key_id=metadata.key_id,
                                    rotated_by="system",
                                    rotation_reason="scheduled_rotation"
                                )
                    
                    await asyncio.sleep(3600)  # Check every hour
                    
                except Exception as e:
                    logger.error(f"Auto rotation task error: {e}")
                    await asyncio.sleep(300)
        
        async def expire_keys():
            """Mark expired keys as expired."""
            while True:
                try:
                    current_time = datetime.utcnow()
                    
                    for metadata in self.api_keys.values():
                        if (metadata.status == ApiKeyStatus.ACTIVE and
                            metadata.expires_at and
                            current_time > metadata.expires_at):
                            
                            metadata.status = ApiKeyStatus.EXPIRED
                            
                            await self._log_security_event({
                                "event_type": "api_key_auto_expired",
                                "key_id": metadata.key_id,
                                "user_id": metadata.user_id,
                                "name": metadata.name,
                                "timestamp": current_time.isoformat()
                            })
                    
                    await asyncio.sleep(1800)  # Check every 30 minutes
                    
                except Exception as e:
                    logger.error(f"Key expiration task error: {e}")
                    await asyncio.sleep(300)
        
        # Start background tasks if event loop is available
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(auto_rotate_keys())
            loop.create_task(expire_keys())
        except RuntimeError:
            logger.info("No event loop running, API key background tasks will be handled manually")
    
    async def get_api_key_analytics(self) -> Dict[str, Any]:
        """Get comprehensive API key analytics."""
        try:
            current_time = datetime.utcnow()
            
            # Key statistics
            total_keys = len(self.api_keys)
            active_keys = sum(1 for key in self.api_keys.values() if key.status == ApiKeyStatus.ACTIVE)
            expired_keys = sum(1 for key in self.api_keys.values() if key.status == ApiKeyStatus.EXPIRED)
            revoked_keys = sum(1 for key in self.api_keys.values() if key.status == ApiKeyStatus.REVOKED)
            
            # Usage statistics
            total_usage = len(self.usage_logs)
            last_24h_usage = sum(
                1 for usage in self.usage_logs
                if (current_time - usage.timestamp).total_seconds() < 86400
            )
            
            # Key type distribution
            key_type_counts = {}
            for key in self.api_keys.values():
                key_type = key.key_type.value
                key_type_counts[key_type] = key_type_counts.get(key_type, 0) + 1
            
            # Security events
            event_counts = {}
            for event in self.security_events:
                event_type = event.get("event_type", "unknown")
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            return {
                "overview": {
                    "total_keys": total_keys,
                    "active_keys": active_keys,
                    "expired_keys": expired_keys,
                    "revoked_keys": revoked_keys,
                    "total_usage": total_usage,
                    "usage_last_24h": last_24h_usage,
                    "total_rotations": len(self.rotation_history)
                },
                "key_types": key_type_counts,
                "security_events": {
                    "total": len(self.security_events),
                    "by_type": event_counts
                },
                "rate_limiting": {
                    "available_tiers": list(self.rate_limit_tiers.keys()),
                    "tier_distribution": self._get_tier_distribution()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get API key analytics: {e}")
            return {"error": f"Failed to get API key analytics: {e}"}
    
    def _get_tier_distribution(self) -> Dict[str, int]:
        """Get distribution of keys by rate limit tier."""
        tier_counts = {}
        for key in self.api_keys.values():
            if key.status == ApiKeyStatus.ACTIVE:
                tier = key.rate_limit_tier
                tier_counts[tier] = tier_counts.get(tier, 0) + 1
        return tier_counts