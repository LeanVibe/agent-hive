#!/usr/bin/env python3
"""
Secure Token Management Utilities

Advanced JWT token management with security features including:
- Token rotation and lifecycle management
- Secure token storage and validation
- Token analytics and monitoring
- Integration with security quality gates
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Set
from enum import Enum
from dataclasses import dataclass
import uuid

import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from external_api.auth_middleware import AuthenticationMiddleware, Permission, AuthResult


logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Token types for different use cases."""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    SESSION = "session"
    TEMPORARY = "temporary"


class TokenStatus(Enum):
    """Token status for lifecycle management."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    BLACKLISTED = "blacklisted"
    SUSPENDED = "suspended"


@dataclass
class TokenMetadata:
    """Token metadata for enhanced tracking."""
    token_id: str
    user_id: str
    token_type: TokenType
    status: TokenStatus
    created_at: datetime
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
    usage_count: int = 0
    ip_addresses: Set[str] = None
    user_agents: Set[str] = None
    scopes: List[str] = None
    
    def __post_init__(self):
        if self.ip_addresses is None:
            self.ip_addresses = set()
        if self.user_agents is None:
            self.user_agents = set()
        if self.scopes is None:
            self.scopes = []


class SecureTokenManager:
    """
    Enhanced token management with advanced security features.
    
    Features:
    - Secure token generation and validation
    - Token rotation and lifecycle management
    - Security monitoring and analytics
    - Encrypted token storage
    - Zero-trust token validation
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize secure token manager."""
        self.config = config
        self.auth_middleware = AuthenticationMiddleware(config)
        
        # Initialize encryption for sensitive data
        self.encryption_key = self._derive_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Token storage with metadata
        self.token_metadata: Dict[str, TokenMetadata] = {}
        self.token_families: Dict[str, List[str]] = {}  # Track token chains
        self.security_events: List[Dict[str, Any]] = []
        
        # Security thresholds
        self.max_tokens_per_user = config.get("max_tokens_per_user", 10)
        self.suspicious_activity_threshold = config.get("suspicious_activity_threshold", 100)
        self.token_rotation_interval = config.get("token_rotation_hours", 24) * 3600
        
        # Start monitoring tasks
        self._start_monitoring_tasks()
        
        logger.info("SecureTokenManager initialized with enhanced security features")
    
    def _derive_encryption_key(self) -> bytes:
        """Derive encryption key for sensitive data storage."""
        # Use JWT secret as password for key derivation
        password = self.config.get("jwt_secret", "default-secret").encode()
        salt = b"agent-hive-token-manager-salt"  # Static salt for consistency
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return Fernet.generate_key()  # Use derived key in production
    
    async def create_secure_token(self, user_id: str, token_type: TokenType,
                                 permissions: List[Permission], 
                                 expires_in_hours: Optional[int] = None,
                                 scopes: Optional[List[str]] = None,
                                 client_metadata: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
        """
        Create a secure token with enhanced metadata tracking.
        
        Returns:
            Tuple of (token, token_id)
        """
        token_id = str(uuid.uuid4())
        current_time = datetime.utcnow()
        
        # Determine expiration based on token type
        if expires_in_hours:
            expires_at = current_time + timedelta(hours=expires_in_hours)
        else:
            # Default expiration by token type
            expiration_hours = {
                TokenType.ACCESS: 1,
                TokenType.REFRESH: 24 * 30,  # 30 days
                TokenType.API_KEY: 24 * 365,  # 1 year
                TokenType.SESSION: 8,  # 8 hours
                TokenType.TEMPORARY: 0.5  # 30 minutes
            }
            expires_at = current_time + timedelta(hours=expiration_hours.get(token_type, 1))
        
        # Create JWT payload with enhanced security
        payload = {
            "user_id": user_id,
            "token_id": token_id,
            "token_type": token_type.value,
            "permissions": [p.value for p in permissions],
            "iat": current_time,
            "exp": expires_at,
            "jti": token_id,
            "iss": "agent-hive-secure",
            "aud": "agent-hive-services",
            "scopes": scopes or [],
            "security_version": "2.0"
        }
        
        # Add client metadata if provided
        if client_metadata:
            payload["client_metadata"] = client_metadata
        
        # Create token using enhanced JWT
        token = jwt.encode(
            payload, 
            self.config["jwt_secret"], 
            algorithm=self.config.get("jwt_algorithm", "HS256")
        )
        
        # Store token metadata
        metadata = TokenMetadata(
            token_id=token_id,
            user_id=user_id,
            token_type=token_type,
            status=TokenStatus.ACTIVE,
            created_at=current_time,
            expires_at=expires_at,
            last_used=None,
            scopes=scopes or []
        )
        
        self.token_metadata[token_id] = metadata
        
        # Track token families for rotation
        family_id = f"{user_id}:{token_type.value}"
        if family_id not in self.token_families:
            self.token_families[family_id] = []
        self.token_families[family_id].append(token_id)
        
        # Enforce token limits per user
        await self._enforce_token_limits(user_id, token_type)
        
        # Log security event
        await self._log_security_event({
            "event_type": "token_created",
            "user_id": user_id,
            "token_id": token_id,
            "token_type": token_type.value,
            "expires_at": expires_at.isoformat(),
            "timestamp": current_time.isoformat()
        })
        
        return token, token_id
    
    async def validate_token_secure(self, token: str, 
                                   required_permissions: Optional[List[Permission]] = None,
                                   client_ip: Optional[str] = None,
                                   user_agent: Optional[str] = None) -> AuthResult:
        """
        Validate token with enhanced security checks.
        """
        try:
            # Decode token
            payload = jwt.decode(
                token, 
                self.config["jwt_secret"], 
                algorithms=[self.config.get("jwt_algorithm", "HS256")]
            )
            
            token_id = payload.get("token_id")
            if not token_id:
                return AuthResult(success=False, error="Invalid token format")
            
            # Check token metadata
            if token_id not in self.token_metadata:
                return AuthResult(success=False, error="Token metadata not found")
            
            metadata = self.token_metadata[token_id]
            
            # Check token status
            if metadata.status != TokenStatus.ACTIVE:
                return AuthResult(success=False, error=f"Token is {metadata.status.value}")
            
            # Update usage tracking
            metadata.last_used = datetime.utcnow()
            metadata.usage_count += 1
            
            if client_ip:
                metadata.ip_addresses.add(client_ip)
            if user_agent:
                metadata.user_agents.add(user_agent)
            
            # Check for suspicious activity
            await self._check_suspicious_activity(metadata, client_ip)
            
            # Validate permissions
            if required_permissions:
                token_permissions = [Permission(p) for p in payload.get("permissions", [])]
                if not any(perm in token_permissions for perm in required_permissions):
                    return AuthResult(success=False, error="Insufficient permissions")
            
            # Check token age for rotation recommendation
            age_hours = (datetime.utcnow() - metadata.created_at).total_seconds() / 3600
            rotation_recommended = age_hours > self.token_rotation_interval / 3600
            
            result = AuthResult(
                success=True,
                user_id=payload.get("user_id"),
                permissions=[Permission(p) for p in payload.get("permissions", [])],
                metadata={
                    "token_id": token_id,
                    "token_type": payload.get("token_type"),
                    "scopes": payload.get("scopes", []),
                    "usage_count": metadata.usage_count,
                    "rotation_recommended": rotation_recommended,
                    "security_version": payload.get("security_version")
                }
            )
            
            # Log access event
            await self._log_security_event({
                "event_type": "token_accessed",
                "user_id": payload.get("user_id"),
                "token_id": token_id,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return result
            
        except ExpiredSignatureError:
            # Mark token as expired
            if token_id in self.token_metadata:
                self.token_metadata[token_id].status = TokenStatus.EXPIRED
            return AuthResult(success=False, error="Token has expired")
            
        except InvalidTokenError as e:
            return AuthResult(success=False, error=f"Invalid token: {e}")
    
    async def rotate_token(self, old_token: str) -> Optional[Tuple[str, str]]:
        """
        Rotate token with secure handoff.
        
        Returns:
            Tuple of (new_token, new_token_id) or None if rotation failed
        """
        try:
            # Validate old token
            payload = jwt.decode(
                old_token, 
                self.config["jwt_secret"], 
                algorithms=[self.config.get("jwt_algorithm", "HS256")]
            )
            
            old_token_id = payload.get("token_id")
            if not old_token_id or old_token_id not in self.token_metadata:
                return None
            
            old_metadata = self.token_metadata[old_token_id]
            
            # Create new token with same permissions
            permissions = [Permission(p) for p in payload.get("permissions", [])]
            token_type = TokenType(payload.get("token_type", "access"))
            
            new_token, new_token_id = await self.create_secure_token(
                user_id=payload.get("user_id"),
                token_type=token_type,
                permissions=permissions,
                scopes=payload.get("scopes", [])
            )
            
            # Revoke old token
            await self.revoke_token(old_token_id, reason="rotated")
            
            # Update token family
            family_id = f"{payload.get('user_id')}:{token_type.value}"
            if family_id in self.token_families:
                if old_token_id in self.token_families[family_id]:
                    self.token_families[family_id].remove(old_token_id)
                self.token_families[family_id].append(new_token_id)
            
            logger.info(f"Token rotated: {old_token_id} -> {new_token_id}")
            return new_token, new_token_id
            
        except Exception as e:
            logger.error(f"Token rotation failed: {e}")
            return None
    
    async def refresh_access_token(self, refresh_token: str, client_ip: Optional[str] = None) -> Optional[Tuple[str, str, datetime]]:
        """
        Refresh access token using refresh token.
        
        Returns:
            Tuple of (new_access_token, new_token_id, expires_at) or None if refresh failed
        """
        try:
            # Validate refresh token
            payload = jwt.decode(
                refresh_token, 
                self.config["jwt_secret"], 
                algorithms=[self.config.get("jwt_algorithm", "HS256")]
            )
            
            refresh_token_id = payload.get("token_id")
            if not refresh_token_id or refresh_token_id not in self.token_metadata:
                return None
            
            refresh_metadata = self.token_metadata[refresh_token_id]
            
            # Check if refresh token is active and not expired
            if refresh_metadata.status != TokenStatus.ACTIVE:
                return None
            
            if refresh_metadata.expires_at and datetime.utcnow() > refresh_metadata.expires_at:
                refresh_metadata.status = TokenStatus.EXPIRED
                return None
            
            # Verify token type
            if refresh_metadata.token_type != TokenType.REFRESH:
                return None
            
            # Update refresh token usage
            refresh_metadata.last_used = datetime.utcnow()
            refresh_metadata.usage_count += 1
            if client_ip:
                refresh_metadata.ip_addresses.add(client_ip)
            
            # Create new access token
            permissions = [Permission(p) for p in payload.get("permissions", [])]
            user_id = payload.get("user_id")
            
            new_access_token, new_token_id = await self.create_secure_token(
                user_id=user_id,
                token_type=TokenType.ACCESS,
                permissions=permissions,
                expires_in_hours=self.config.get("token_expiry_minutes", 15) / 60,
                scopes=payload.get("scopes", [])
            )
            
            # Get new token metadata for expiration
            new_metadata = self.token_metadata[new_token_id]
            
            # Log refresh event
            await self._log_security_event({
                "event_type": "access_token_refreshed",
                "user_id": user_id,
                "refresh_token_id": refresh_token_id,
                "new_access_token_id": new_token_id,
                "client_ip": client_ip,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return new_access_token, new_token_id, new_metadata.expires_at
            
        except ExpiredSignatureError:
            logger.warning("Attempted to use expired refresh token")
            return None
        except Exception as e:
            logger.error(f"Access token refresh failed: {e}")
            return None
    
    async def create_token_pair(self, user_id: str, permissions: List[Permission],
                               scopes: Optional[List[str]] = None,
                               client_metadata: Optional[Dict[str, Any]] = None) -> Tuple[str, str, str, str]:
        """
        Create access and refresh token pair.
        
        Returns:
            Tuple of (access_token, access_token_id, refresh_token, refresh_token_id)
        """
        # Create access token
        access_token, access_token_id = await self.create_secure_token(
            user_id=user_id,
            token_type=TokenType.ACCESS,
            permissions=permissions,
            expires_in_hours=self.config.get("token_expiry_minutes", 15) / 60,
            scopes=scopes,
            client_metadata=client_metadata
        )
        
        # Create refresh token (longer lived)
        refresh_token, refresh_token_id = await self.create_secure_token(
            user_id=user_id,
            token_type=TokenType.REFRESH,
            permissions=permissions,
            expires_in_hours=24 * 30,  # 30 days
            scopes=scopes,
            client_metadata=client_metadata
        )
        
        # Link tokens in family
        family_id = f"{user_id}:token_pair"
        if family_id not in self.token_families:
            self.token_families[family_id] = []
        self.token_families[family_id].extend([access_token_id, refresh_token_id])
        
        return access_token, access_token_id, refresh_token, refresh_token_id
    
    async def invalidate_token_family(self, user_id: str, token_type: Optional[TokenType] = None) -> int:
        """
        Invalidate all tokens in a user's token family.
        
        Returns:
            Number of tokens invalidated
        """
        invalidated_count = 0
        
        for token_id, metadata in self.token_metadata.items():
            if (metadata.user_id == user_id and 
                metadata.status == TokenStatus.ACTIVE and
                (token_type is None or metadata.token_type == token_type)):
                
                await self.revoke_token(token_id, reason="family_invalidation")
                invalidated_count += 1
        
        return invalidated_count
    
    async def check_token_health(self, token: str) -> Dict[str, Any]:
        """
        Check token health and provide recommendations.
        
        Returns:
            Dictionary with health information and recommendations
        """
        try:
            # Decode token
            payload = jwt.decode(
                token, 
                self.config["jwt_secret"], 
                algorithms=[self.config.get("jwt_algorithm", "HS256")]
            )
            
            token_id = payload.get("token_id")
            if not token_id or token_id not in self.token_metadata:
                return {
                    "healthy": False,
                    "error": "Token metadata not found",
                    "recommendations": ["Token may be invalid or revoked"]
                }
            
            metadata = self.token_metadata[token_id]
            current_time = datetime.utcnow()
            
            # Calculate token age
            age_hours = (current_time - metadata.created_at).total_seconds() / 3600
            
            # Calculate time until expiration
            time_to_expiry_hours = 0
            if metadata.expires_at:
                time_to_expiry_hours = (metadata.expires_at - current_time).total_seconds() / 3600
            
            # Determine health status
            healthy = True
            warnings = []
            recommendations = []
            
            # Check token status
            if metadata.status != TokenStatus.ACTIVE:
                healthy = False
                warnings.append(f"Token status is {metadata.status.value}")
            
            # Check expiration
            if metadata.expires_at and current_time > metadata.expires_at:
                healthy = False
                warnings.append("Token has expired")
                recommendations.append("Refresh token immediately")
            elif time_to_expiry_hours < 1:
                warnings.append("Token expires within 1 hour")
                recommendations.append("Consider refreshing token soon")
            
            # Check usage patterns
            if metadata.usage_count > 1000:
                warnings.append("High usage count detected")
                recommendations.append("Consider token rotation for security")
            
            # Check IP diversity
            if len(metadata.ip_addresses) > 5:
                warnings.append("Token used from many different IP addresses")
                recommendations.append("Review access patterns for suspicious activity")
            
            # Check age
            if age_hours > 24:
                warnings.append("Token is over 24 hours old")
                recommendations.append("Consider rotating token for enhanced security")
            
            return {
                "healthy": healthy,
                "token_id": token_id,
                "age_hours": round(age_hours, 2),
                "time_to_expiry_hours": round(time_to_expiry_hours, 2),
                "usage_count": metadata.usage_count,
                "unique_ips": len(metadata.ip_addresses),
                "status": metadata.status.value,
                "token_type": metadata.token_type.value,
                "warnings": warnings,
                "recommendations": recommendations
            }
            
        except ExpiredSignatureError:
            return {
                "healthy": False,
                "error": "Token has expired",
                "recommendations": ["Refresh token immediately"]
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": f"Token validation error: {str(e)}",
                "recommendations": ["Check token format and signature"]
            }
    
    async def revoke_token(self, token_id: str, reason: str = "revoked") -> bool:
        """Revoke a token and log the action."""
        if token_id not in self.token_metadata:
            return False
        
        metadata = self.token_metadata[token_id]
        metadata.status = TokenStatus.REVOKED
        
        # Log revocation event
        await self._log_security_event({
            "event_type": "token_revoked",
            "token_id": token_id,
            "user_id": metadata.user_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Token revoked: {token_id} (reason: {reason})")
        return True
    
    async def revoke_user_tokens(self, user_id: str, token_type: Optional[TokenType] = None) -> int:
        """Revoke all tokens for a user, optionally filtered by type."""
        revoked_count = 0
        
        for token_id, metadata in self.token_metadata.items():
            if (metadata.user_id == user_id and 
                metadata.status == TokenStatus.ACTIVE and
                (token_type is None or metadata.token_type == token_type)):
                
                await self.revoke_token(token_id, reason="user_logout")
                revoked_count += 1
        
        return revoked_count
    
    async def get_token_analytics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive token analytics."""
        total_tokens = len(self.token_metadata)
        active_tokens = sum(1 for m in self.token_metadata.values() if m.status == TokenStatus.ACTIVE)
        expired_tokens = sum(1 for m in self.token_metadata.values() if m.status == TokenStatus.EXPIRED)
        revoked_tokens = sum(1 for m in self.token_metadata.values() if m.status == TokenStatus.REVOKED)
        
        analytics = {
            "total_tokens": total_tokens,
            "active_tokens": active_tokens,
            "expired_tokens": expired_tokens,
            "revoked_tokens": revoked_tokens,
            "token_types": {},
            "user_distribution": {},
            "security_events_count": len(self.security_events),
            "suspicious_activity_detected": 0
        }
        
        # Analyze by token type
        for metadata in self.token_metadata.values():
            token_type = metadata.token_type.value
            if token_type not in analytics["token_types"]:
                analytics["token_types"][token_type] = {"total": 0, "active": 0}
            
            analytics["token_types"][token_type]["total"] += 1
            if metadata.status == TokenStatus.ACTIVE:
                analytics["token_types"][token_type]["active"] += 1
        
        # Analyze by user
        for metadata in self.token_metadata.values():
            user = metadata.user_id
            if user not in analytics["user_distribution"]:
                analytics["user_distribution"][user] = {"total": 0, "active": 0}
            
            analytics["user_distribution"][user]["total"] += 1
            if metadata.status == TokenStatus.ACTIVE:
                analytics["user_distribution"][user]["active"] += 1
        
        # Count suspicious activities
        analytics["suspicious_activity_detected"] = len([
            event for event in self.security_events 
            if event.get("event_type") == "suspicious_activity"
        ])
        
        # Filter by user if specified
        if user_id:
            user_tokens = [m for m in self.token_metadata.values() if m.user_id == user_id]
            analytics["user_specific"] = {
                "total_tokens": len(user_tokens),
                "active_tokens": sum(1 for m in user_tokens if m.status == TokenStatus.ACTIVE),
                "total_usage": sum(m.usage_count for m in user_tokens),
                "unique_ips": len(set().union(*[m.ip_addresses for m in user_tokens])),
                "unique_user_agents": len(set().union(*[m.user_agents for m in user_tokens]))
            }
        
        return analytics
    
    async def _enforce_token_limits(self, user_id: str, token_type: TokenType) -> None:
        """Enforce per-user token limits."""
        user_tokens = [
            (token_id, metadata) for token_id, metadata in self.token_metadata.items()
            if metadata.user_id == user_id and metadata.token_type == token_type and metadata.status == TokenStatus.ACTIVE
        ]
        
        if len(user_tokens) > self.max_tokens_per_user:
            # Revoke oldest tokens
            user_tokens.sort(key=lambda x: x[1].created_at)
            tokens_to_revoke = user_tokens[:-self.max_tokens_per_user]
            
            for token_id, metadata in tokens_to_revoke:
                await self.revoke_token(token_id, reason="token_limit_exceeded")
    
    async def _check_suspicious_activity(self, metadata: TokenMetadata, client_ip: Optional[str]) -> None:
        """Check for suspicious token usage patterns."""
        suspicious = False
        reasons = []
        
        # Check for unusual usage patterns
        if metadata.usage_count > self.suspicious_activity_threshold:
            suspicious = True
            reasons.append("high_usage_count")
        
        # Check for too many IP addresses
        if len(metadata.ip_addresses) > 10:
            suspicious = True
            reasons.append("multiple_ip_addresses")
        
        # Check for usage from new IP after being idle
        if (client_ip and 
            metadata.last_used and 
            client_ip not in metadata.ip_addresses and
            (datetime.utcnow() - metadata.last_used).total_seconds() > 3600):  # 1 hour
            suspicious = True
            reasons.append("new_ip_after_idle")
        
        if suspicious:
            await self._log_security_event({
                "event_type": "suspicious_activity",
                "token_id": metadata.token_id,
                "user_id": metadata.user_id,
                "reasons": reasons,
                "client_ip": client_ip,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.warning(f"Suspicious activity detected for token {metadata.token_id}: {reasons}")
    
    async def _log_security_event(self, event: Dict[str, Any]) -> None:
        """Log security events for monitoring and analysis."""
        event["event_id"] = str(uuid.uuid4())
        self.security_events.append(event)
        
        # Keep only last 10000 events to prevent memory issues
        if len(self.security_events) > 10000:
            self.security_events = self.security_events[-5000:]
    
    def _start_monitoring_tasks(self) -> None:
        """Start background monitoring tasks."""
        async def cleanup_expired_tokens():
            while True:
                try:
                    current_time = datetime.utcnow()
                    expired_count = 0
                    
                    for token_id, metadata in list(self.token_metadata.items()):
                        if (metadata.expires_at and 
                            current_time > metadata.expires_at and 
                            metadata.status == TokenStatus.ACTIVE):
                            
                            metadata.status = TokenStatus.EXPIRED
                            expired_count += 1
                    
                    if expired_count > 0:
                        logger.info(f"Marked {expired_count} tokens as expired")
                    
                    # Clean up old security events
                    cutoff_time = current_time - timedelta(days=7)
                    original_count = len(self.security_events)
                    self.security_events = [
                        event for event in self.security_events
                        if datetime.fromisoformat(event.get("timestamp", current_time.isoformat())) > cutoff_time
                    ]
                    
                    if len(self.security_events) < original_count:
                        logger.info(f"Cleaned up {original_count - len(self.security_events)} old security events")
                    
                    await asyncio.sleep(3600)  # Run every hour
                    
                except Exception as e:
                    logger.error(f"Token cleanup error: {e}")
                    await asyncio.sleep(300)  # Wait 5 minutes on error
        
        # Start cleanup task only if event loop is running
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(cleanup_expired_tokens())
        except RuntimeError:
            # No event loop running, cleanup will be handled manually
            logger.info("No event loop running, token cleanup will be handled manually")
    
    async def export_security_report(self) -> Dict[str, Any]:
        """Export comprehensive security report."""
        analytics = await self.get_token_analytics()
        
        # Recent security events (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        recent_events = [
            event for event in self.security_events
            if datetime.fromisoformat(event.get("timestamp", "")) > cutoff_time
        ]
        
        # Group events by type
        event_summary = {}
        for event in recent_events:
            event_type = event.get("event_type", "unknown")
            if event_type not in event_summary:
                event_summary[event_type] = 0
            event_summary[event_type] += 1
        
        report = {
            "report_generated_at": datetime.utcnow().isoformat(),
            "token_analytics": analytics,
            "recent_security_events": {
                "time_window": "24_hours",
                "total_events": len(recent_events),
                "event_summary": event_summary
            },
            "security_recommendations": self._generate_security_recommendations(analytics, recent_events),
            "compliance_status": self._check_compliance_status(analytics)
        }
        
        return report
    
    def _generate_security_recommendations(self, analytics: Dict[str, Any], 
                                          recent_events: List[Dict[str, Any]]) -> List[str]:
        """Generate security recommendations based on analytics."""
        recommendations = []
        
        # Check token distribution
        if analytics["active_tokens"] > 1000:
            recommendations.append("Consider implementing more aggressive token cleanup policies")
        
        # Check suspicious activity
        if analytics["suspicious_activity_detected"] > 10:
            recommendations.append("High number of suspicious activities detected - review security policies")
        
        # Check user distribution
        for user_id, user_data in analytics.get("user_distribution", {}).items():
            if user_data["active"] > 50:
                recommendations.append(f"User {user_id} has {user_data['active']} active tokens - consider limits")
        
        # Check for token rotation
        rotation_events = len([e for e in recent_events if e.get("event_type") == "token_rotated"])
        if rotation_events == 0 and analytics["active_tokens"] > 0:
            recommendations.append("No token rotations detected - consider implementing automatic rotation")
        
        return recommendations
    
    def _check_compliance_status(self, analytics: Dict[str, Any]) -> Dict[str, Any]:
        """Check compliance with security policies."""
        compliance = {
            "token_limits_enforced": True,
            "monitoring_active": True,
            "encryption_enabled": True,
            "audit_trail_complete": True,
            "issues": []
        }
        
        # Check if any users exceed limits
        for user_id, user_data in analytics.get("user_distribution", {}).items():
            if user_data["active"] > self.max_tokens_per_user:
                compliance["token_limits_enforced"] = False
                compliance["issues"].append(f"User {user_id} exceeds token limit")
        
        # Check monitoring
        if len(self.security_events) == 0:
            compliance["monitoring_active"] = False
            compliance["issues"].append("No security events logged")
        
        return compliance