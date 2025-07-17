"""
Unified Security Configuration for LeanVibe Agent Hive.

Provides centralized security configuration management including authentication,
authorization, encryption, and security policy enforcement across all components.
"""

import os
import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class SecurityPolicy:
    """Represents a security policy configuration."""
    policy_id: str
    name: str
    description: str
    rules: List[Dict[str, Any]] = field(default_factory=list)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class AuthenticationConfig:
    """Authentication configuration."""
    method: str = "jwt"  # jwt, basic, oauth2, api_key
    secret_key: str = ""
    algorithm: str = "HS256"
    expiration_minutes: int = 30
    refresh_token_enabled: bool = True
    refresh_token_expiration_days: int = 7
    multi_factor_enabled: bool = False
    password_policy: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthorizationConfig:
    """Authorization configuration."""
    model: str = "rbac"  # rbac, abac, simple
    default_role: str = "user"
    admin_roles: List[str] = field(default_factory=lambda: ["admin", "super_admin"])
    permissions: Dict[str, List[str]] = field(default_factory=dict)
    role_hierarchy: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class EncryptionConfig:
    """Encryption configuration."""
    algorithm: str = "AES-256-GCM"
    key_derivation: str = "PBKDF2"
    salt_rounds: int = 100000
    encryption_at_rest: bool = True
    encryption_in_transit: bool = True
    key_rotation_days: int = 90


@dataclass
class SecurityHeaders:
    """Security headers configuration."""
    content_security_policy: str = "default-src 'self'"
    strict_transport_security: str = "max-age=31536000; includeSubDomains"
    x_content_type_options: str = "nosniff"
    x_frame_options: str = "DENY"
    x_xss_protection: str = "1; mode=block"
    referrer_policy: str = "strict-origin-when-cross-origin"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    enabled: bool = True
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_size: int = 10
    redis_url: Optional[str] = None
    storage_type: str = "memory"  # memory, redis, database


@dataclass
class AuditConfig:
    """Audit logging configuration."""
    enabled: bool = True
    log_level: str = "INFO"
    log_file: str = "security_audit.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    include_request_body: bool = False
    include_response_body: bool = False
    sensitive_fields: List[str] = field(default_factory=lambda: ["password", "token", "secret"])


@dataclass
class UnifiedSecurityConfig:
    """Unified security configuration container."""
    authentication: AuthenticationConfig = field(default_factory=AuthenticationConfig)
    authorization: AuthorizationConfig = field(default_factory=AuthorizationConfig)
    encryption: EncryptionConfig = field(default_factory=EncryptionConfig)
    security_headers: SecurityHeaders = field(default_factory=SecurityHeaders)
    rate_limiting: RateLimitConfig = field(default_factory=RateLimitConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)
    policies: List[SecurityPolicy] = field(default_factory=list)
    environment: str = "development"
    debug_mode: bool = False
    created_at: datetime = field(default_factory=datetime.now)


class SecurityConfigManager:
    """Manages unified security configuration."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize the security configuration manager."""
        self.config_file = config_file or os.getenv("SECURITY_CONFIG_FILE", "security_config.json")
        self.config = self._load_config()
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self) -> UnifiedSecurityConfig:
        """Load security configuration from file or environment."""
        try:
            # Try to load from file first
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                return self._dict_to_config(config_data)
            
            # Fall back to environment variables
            return self._load_from_env()
            
        except Exception as e:
            self.logger.warning(f"Error loading security config: {e}")
            return UnifiedSecurityConfig()
    
    def _load_from_env(self) -> UnifiedSecurityConfig:
        """Load configuration from environment variables."""
        config = UnifiedSecurityConfig()
        
        # Authentication
        config.authentication.method = os.getenv("AUTH_METHOD", "jwt")
        config.authentication.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
        config.authentication.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        config.authentication.expiration_minutes = int(os.getenv("JWT_EXPIRATION_MINUTES", "30"))
        
        # Authorization
        config.authorization.model = os.getenv("AUTHZ_MODEL", "rbac")
        config.authorization.default_role = os.getenv("DEFAULT_ROLE", "user")
        
        # Encryption
        config.encryption.algorithm = os.getenv("ENCRYPTION_ALGORITHM", "AES-256-GCM")
        config.encryption.encryption_at_rest = os.getenv("ENCRYPTION_AT_REST", "true").lower() == "true"
        config.encryption.encryption_in_transit = os.getenv("ENCRYPTION_IN_TRANSIT", "true").lower() == "true"
        
        # Rate limiting
        config.rate_limiting.enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        config.rate_limiting.requests_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        config.rate_limiting.redis_url = os.getenv("REDIS_URL")
        
        # Environment
        config.environment = os.getenv("ENVIRONMENT", "development")
        config.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
        
        return config
    
    def _dict_to_config(self, config_data: Dict[str, Any]) -> UnifiedSecurityConfig:
        """Convert dictionary to UnifiedSecurityConfig."""
        # This is a simplified conversion - real implementation would handle
        # nested dataclass conversion properly
        config = UnifiedSecurityConfig()
        
        # Basic field assignment
        for field_name, value in config_data.items():
            if hasattr(config, field_name):
                setattr(config, field_name, value)
        
        return config
    
    def save_config(self) -> bool:
        """Save configuration to file."""
        try:
            config_data = self._config_to_dict()
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
            return True
        except Exception as e:
            self.logger.error(f"Error saving security config: {e}")
            return False
    
    def _config_to_dict(self) -> Dict[str, Any]:
        """Convert UnifiedSecurityConfig to dictionary."""
        # This is a simplified conversion - real implementation would handle
        # nested dataclass conversion properly
        return {
            "authentication": {
                "method": self.config.authentication.method,
                "algorithm": self.config.authentication.algorithm,
                "expiration_minutes": self.config.authentication.expiration_minutes,
                "refresh_token_enabled": self.config.authentication.refresh_token_enabled,
                "multi_factor_enabled": self.config.authentication.multi_factor_enabled
            },
            "authorization": {
                "model": self.config.authorization.model,
                "default_role": self.config.authorization.default_role,
                "admin_roles": self.config.authorization.admin_roles,
                "permissions": self.config.authorization.permissions,
                "role_hierarchy": self.config.authorization.role_hierarchy
            },
            "encryption": {
                "algorithm": self.config.encryption.algorithm,
                "key_derivation": self.config.encryption.key_derivation,
                "salt_rounds": self.config.encryption.salt_rounds,
                "encryption_at_rest": self.config.encryption.encryption_at_rest,
                "encryption_in_transit": self.config.encryption.encryption_in_transit,
                "key_rotation_days": self.config.encryption.key_rotation_days
            },
            "rate_limiting": {
                "enabled": self.config.rate_limiting.enabled,
                "requests_per_minute": self.config.rate_limiting.requests_per_minute,
                "requests_per_hour": self.config.rate_limiting.requests_per_hour,
                "requests_per_day": self.config.rate_limiting.requests_per_day,
                "burst_size": self.config.rate_limiting.burst_size,
                "storage_type": self.config.rate_limiting.storage_type
            },
            "audit": {
                "enabled": self.config.audit.enabled,
                "log_level": self.config.audit.log_level,
                "log_file": self.config.audit.log_file,
                "max_file_size": self.config.audit.max_file_size,
                "backup_count": self.config.audit.backup_count,
                "include_request_body": self.config.audit.include_request_body,
                "include_response_body": self.config.audit.include_response_body,
                "sensitive_fields": self.config.audit.sensitive_fields
            },
            "environment": self.config.environment,
            "debug_mode": self.config.debug_mode
        }
    
    def get_config(self) -> UnifiedSecurityConfig:
        """Get the current security configuration."""
        return self.config
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update security configuration."""
        try:
            # Apply updates to configuration
            for key, value in updates.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            # Save updated configuration
            return self.save_config()
            
        except Exception as e:
            self.logger.error(f"Error updating security config: {e}")
            return False
    
    def add_policy(self, policy: SecurityPolicy) -> bool:
        """Add a security policy."""
        try:
            self.config.policies.append(policy)
            return self.save_config()
        except Exception as e:
            self.logger.error(f"Error adding security policy: {e}")
            return False
    
    def remove_policy(self, policy_id: str) -> bool:
        """Remove a security policy."""
        try:
            self.config.policies = [p for p in self.config.policies if p.policy_id != policy_id]
            return self.save_config()
        except Exception as e:
            self.logger.error(f"Error removing security policy: {e}")
            return False
    
    def get_policy(self, policy_id: str) -> Optional[SecurityPolicy]:
        """Get a security policy by ID."""
        for policy in self.config.policies:
            if policy.policy_id == policy_id:
                return policy
        return None
    
    def validate_config(self) -> Dict[str, List[str]]:
        """Validate the security configuration."""
        errors = {}
        
        # Validate authentication
        if not self.config.authentication.secret_key:
            errors.setdefault("authentication", []).append("Secret key is required")
        
        if self.config.authentication.expiration_minutes <= 0:
            errors.setdefault("authentication", []).append("Expiration minutes must be positive")
        
        # Validate authorization
        if not self.config.authorization.default_role:
            errors.setdefault("authorization", []).append("Default role is required")
        
        # Validate encryption
        if self.config.encryption.salt_rounds < 1000:
            errors.setdefault("encryption", []).append("Salt rounds should be at least 1000")
        
        # Validate rate limiting
        if self.config.rate_limiting.enabled and self.config.rate_limiting.requests_per_minute <= 0:
            errors.setdefault("rate_limiting", []).append("Requests per minute must be positive")
        
        return errors


# Global configuration manager instance
_config_manager = None


def get_config_manager() -> SecurityConfigManager:
    """Get the global security configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = SecurityConfigManager()
    return _config_manager


def get_security_config() -> UnifiedSecurityConfig:
    """Get the current security configuration."""
    return get_config_manager().get_config()


def get_performance_targets() -> Dict[str, Any]:
    """Get performance targets for security operations."""
    return {
        "authentication_response_time_ms": 100,
        "authorization_response_time_ms": 50,
        "encryption_throughput_mbps": 100,
        "rate_limit_check_time_ms": 10,
        "audit_log_write_time_ms": 5,
        "token_validation_time_ms": 20,
        "password_hash_time_ms": 500,
        "session_lookup_time_ms": 25
    }


def get_security_headers() -> Dict[str, str]:
    """Get security headers configuration."""
    config = get_security_config()
    return {
        "Content-Security-Policy": config.security_headers.content_security_policy,
        "Strict-Transport-Security": config.security_headers.strict_transport_security,
        "X-Content-Type-Options": config.security_headers.x_content_type_options,
        "X-Frame-Options": config.security_headers.x_frame_options,
        "X-XSS-Protection": config.security_headers.x_xss_protection,
        "Referrer-Policy": config.security_headers.referrer_policy
    }


def get_rate_limit_config() -> RateLimitConfig:
    """Get rate limiting configuration."""
    return get_security_config().rate_limiting


def get_audit_config() -> AuditConfig:
    """Get audit configuration."""
    return get_security_config().audit


def is_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    return get_security_config().debug_mode


def get_environment() -> str:
    """Get the current environment."""
    return get_security_config().environment


def create_default_policies() -> List[SecurityPolicy]:
    """Create default security policies."""
    return [
        SecurityPolicy(
            policy_id="default-auth",
            name="Default Authentication Policy",
            description="Default authentication requirements",
            rules=[
                {"require_authentication": True},
                {"allow_anonymous": False},
                {"session_timeout_minutes": 30}
            ]
        ),
        SecurityPolicy(
            policy_id="api-access",
            name="API Access Policy",
            description="API access control policy",
            rules=[
                {"require_api_key": True},
                {"rate_limit_enabled": True},
                {"cors_enabled": True}
            ]
        ),
        SecurityPolicy(
            policy_id="data-protection",
            name="Data Protection Policy",
            description="Data protection and privacy policy",
            rules=[
                {"encrypt_sensitive_data": True},
                {"log_data_access": True},
                {"data_retention_days": 90}
            ]
        )
    ]