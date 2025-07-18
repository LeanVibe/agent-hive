"""
Unified Security Configuration for LeanVibe Agent Hive

Centralizes all security configuration for API Gateway, authentication,
authorization, audit logging, and security monitoring.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import timedelta

from external_api.auth_middleware import AuthMethod, Permission
from security.security_manager import RiskLevel, AccessLevel


class SecurityProfile(Enum):
    """Security profiles for different deployment environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class JWTConfig:
    """JWT token configuration."""
    secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET"))
    algorithm: str = "HS256"
    expiry_hours: int = 24
    refresh_expiry_hours: int = 168  # 7 days
    issuer: str = "leanvibe-agent-hive"
    audience: str = "leanvibe-api"


@dataclass
class AuthConfig:
    """Authentication configuration."""
    enabled_methods: List[AuthMethod] = field(default_factory=lambda: [
        AuthMethod.API_KEY, AuthMethod.JWT, AuthMethod.OAUTH2
    ])
    jwt: JWTConfig = field(default_factory=JWTConfig)
    api_key_expiry_days: int = 90
    oauth2_providers: List[str] = field(default_factory=lambda: ["github", "google"])
    max_auth_attempts: int = 5
    auth_window_minutes: int = 15
    require_tls: bool = True
    session_timeout_hours: int = 8


@dataclass
class RBACConfig:
    """Role-Based Access Control configuration."""
    default_role: str = "readonly"
    roles: Dict[str, List[Permission]] = field(default_factory=lambda: {
        "admin": [Permission.READ, Permission.WRITE, Permission.ADMIN, Permission.EXECUTE],
        "developer": [Permission.READ, Permission.WRITE, Permission.EXECUTE],
        "user": [Permission.READ, Permission.WRITE],
        "readonly": [Permission.READ]
    })
    path_permissions: Dict[str, List[Permission]] = field(default_factory=lambda: {
        "/api/security/admin": [Permission.ADMIN],
        "/api/security/audit": [Permission.READ, Permission.ADMIN],
        "/api/security/validate": [Permission.READ, Permission.WRITE],
        "/api/security/monitoring": [Permission.READ, Permission.ADMIN]
    })


@dataclass
class AuditConfig:
    """Audit logging configuration."""
    enabled: bool = True
    log_level: RiskLevel = RiskLevel.LOW
    database_path: str = "security_audit.db"
    retention_days: int = 365
    log_to_file: bool = True
    log_file_path: str = "logs/security_audit.log"
    log_to_syslog: bool = False
    syslog_server: Optional[str] = None
    real_time_alerts: bool = True


@dataclass
class MonitoringConfig:
    """Security monitoring configuration."""
    enabled: bool = True
    scan_interval_minutes: int = 60
    vulnerability_db_update_hours: int = 24
    alert_thresholds: Dict[str, int] = field(default_factory=lambda: {
        "critical": 1,
        "high": 3,
        "medium": 10,
        "low": 50
    })
    notification_channels: List[str] = field(default_factory=lambda: ["email"])
    webhook_urls: List[str] = field(default_factory=list)


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    enabled: bool = True
    requests_per_minute: int = 100
    requests_per_hour: int = 1000
    burst_limit: int = 50
    per_endpoint_limits: Dict[str, int] = field(default_factory=lambda: {
        "/api/security/validate": 200,
        "/api/security/auth/login": 10,
        "/api/security/audit/events": 50
    })


@dataclass
class APIGatewaySecurityConfig:
    """API Gateway security configuration."""
    enable_cors: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["https://app.leanvibe.com"])
    cors_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    cors_headers: List[str] = field(default_factory=lambda: ["Content-Type", "Authorization", "X-API-Key"])
    request_timeout_seconds: int = 30
    max_request_size_mb: int = 10
    enable_request_logging: bool = True
    trust_proxy_headers: bool = False


@dataclass
class UnifiedSecurityConfig:
    """Unified security configuration for all components."""
    profile: SecurityProfile = SecurityProfile.DEVELOPMENT
    auth: AuthConfig = field(default_factory=AuthConfig)
    rbac: RBACConfig = field(default_factory=RBACConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    rate_limiting: RateLimitConfig = field(default_factory=RateLimitConfig)
    api_gateway: APIGatewaySecurityConfig = field(default_factory=APIGatewaySecurityConfig)
    
    # Security features
    enable_command_validation: bool = True
    enable_input_sanitization: bool = True
    enable_sql_injection_protection: bool = True
    enable_xss_protection: bool = True
    enable_csrf_protection: bool = True
    
    # Compliance and standards
    enforce_https: bool = True
    require_strong_passwords: bool = True
    enable_audit_trail: bool = True
    gdpr_compliance: bool = True
    hipaa_compliance: bool = False
    
    def __post_init__(self):
        """Apply profile-specific configurations."""
        if self.profile == SecurityProfile.PRODUCTION:
            self._apply_production_settings()
        elif self.profile == SecurityProfile.STAGING:
            self._apply_staging_settings()
        else:
            self._apply_development_settings()
    
    def _apply_production_settings(self):
        """Apply production security settings."""
        # Stricter authentication
        self.auth.require_tls = True
        self.auth.session_timeout_hours = 4
        self.auth.max_auth_attempts = 3
        
        # Enhanced monitoring
        self.monitoring.scan_interval_minutes = 30
        self.monitoring.real_time_alerts = True
        
        # Stricter rate limiting
        self.rate_limiting.requests_per_minute = 60
        self.rate_limiting.requests_per_hour = 500
        
        # Enhanced audit logging
        self.audit.log_level = RiskLevel.LOW
        self.audit.log_to_syslog = True
        
        # CORS restrictions
        self.api_gateway.cors_origins = ["https://app.leanvibe.com"]
        self.api_gateway.trust_proxy_headers = True
        
        # Enable all security features
        self.enforce_https = True
        self.require_strong_passwords = True
        self.enable_audit_trail = True
    
    def _apply_staging_settings(self):
        """Apply staging security settings."""
        # Moderate authentication
        self.auth.require_tls = True
        self.auth.session_timeout_hours = 6
        
        # Standard monitoring
        self.monitoring.scan_interval_minutes = 60
        
        # Moderate rate limiting
        self.rate_limiting.requests_per_minute = 80
        
        # Enhanced CORS for testing
        self.api_gateway.cors_origins = [
            "https://staging.leanvibe.com",
            "https://test.leanvibe.com"
        ]
    
    def _apply_development_settings(self):
        """Apply development security settings."""
        # Relaxed authentication for development
        self.auth.require_tls = False
        self.auth.session_timeout_hours = 12
        self.auth.max_auth_attempts = 10
        
        # Relaxed monitoring
        self.monitoring.scan_interval_minutes = 120
        self.monitoring.real_time_alerts = False
        
        # Relaxed rate limiting
        self.rate_limiting.requests_per_minute = 200
        
        # Permissive CORS for development
        self.api_gateway.cors_origins = ["*"]
        
        # Some security features disabled for development ease
        self.enforce_https = False
        self.require_strong_passwords = False
    
    def get_auth_config(self) -> Dict[str, Any]:
        """Get authentication configuration for auth middleware."""
        return {
            "enabled_methods": [method.value for method in self.auth.enabled_methods],
            "jwt_secret": self.auth.jwt.secret,
            "jwt_algorithm": self.auth.jwt.algorithm,
            "token_expiry_hours": self.auth.jwt.expiry_hours,
            "max_auth_attempts": self.auth.max_auth_attempts,
            "auth_window_minutes": self.auth.auth_window_minutes,
            "require_tls": self.auth.require_tls
        }
    
    def get_security_manager_config(self) -> Dict[str, Any]:
        """Get configuration for security manager."""
        return {
            "enable_command_validation": self.enable_command_validation,
            "enable_input_sanitization": self.enable_input_sanitization,
            "audit_enabled": self.audit.enabled,
            "audit_database_path": self.audit.database_path,
            "audit_retention_days": self.audit.retention_days,
            "log_level": self.audit.log_level.value
        }
    
    def get_api_gateway_config(self) -> Dict[str, Any]:
        """Get configuration for API Gateway."""
        return {
            "enable_cors": self.api_gateway.enable_cors,
            "cors_origins": self.api_gateway.cors_origins,
            "cors_methods": self.api_gateway.cors_methods,
            "cors_headers": self.api_gateway.cors_headers,
            "request_timeout": self.api_gateway.request_timeout_seconds,
            "max_request_size": self.api_gateway.max_request_size_mb,
            "enable_request_logging": self.api_gateway.enable_request_logging,
            "rate_limit_requests": self.rate_limiting.requests_per_minute,
            "rate_limit_window": 60
        }


def get_security_config(profile: Optional[SecurityProfile] = None) -> UnifiedSecurityConfig:
    """
    Get unified security configuration.
    
    Args:
        profile: Security profile to use (defaults to environment variable)
        
    Returns:
        Unified security configuration
    """
    if profile is None:
        profile_name = os.getenv("SECURITY_PROFILE", "development").lower()
        profile = SecurityProfile(profile_name)
    
    return UnifiedSecurityConfig(profile=profile)


# Default configuration instance
DEFAULT_CONFIG = get_security_config()

# Named configuration instances for compatibility
DEVELOPMENT_CONFIG = get_security_config(SecurityProfile.DEVELOPMENT)
STAGING_CONFIG = get_security_config(SecurityProfile.STAGING)
PRODUCTION_CONFIG = get_security_config(SecurityProfile.PRODUCTION)