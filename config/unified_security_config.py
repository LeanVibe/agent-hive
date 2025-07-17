"""
Unified Security Configuration
=============================

Centralized security configuration for all security middleware components
including rate limiting, authentication, DDoS protection, and validation.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import json

from external_api.models import ApiGatewayConfig


class SecurityLevel(Enum):
    """Security enforcement levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    TOKEN_BUCKET = "token_bucket"
    ADAPTIVE = "adaptive"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    # Core settings
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    max_requests: int = 100
    window_seconds: int = 60
    
    # Performance optimization
    redis_pool_size: int = 10
    connection_timeout_ms: int = 5  # <10ms target
    response_timeout_ms: int = 5   # <10ms target
    batch_operations: bool = True
    
    # Burst handling
    burst_allowance: int = 10
    burst_window_seconds: int = 1
    
    # IP-based controls
    whitelist_ips: List[str] = field(default_factory=list)
    blacklist_ips: List[str] = field(default_factory=list)
    
    # User-based controls
    user_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    role_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "admin": 10.0,
        "user": 1.0,
        "readonly": 0.5
    })
    
    # Endpoint-specific limits
    endpoint_limits: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Failure handling
    fail_open: bool = True  # Allow requests if Redis is down
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60


@dataclass
class AuthenticationConfig:
    """Authentication configuration"""
    enabled_methods: List[str] = field(default_factory=lambda: ["api_key", "jwt"])
    jwt_secret: str = os.getenv("JWT_SECRET", "default-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    
    # Rate limiting for auth
    max_auth_attempts: int = 5
    auth_window_minutes: int = 15
    
    # Security policies
    require_https: bool = True
    session_timeout_hours: int = 8
    max_concurrent_sessions: int = 5
    
    # RBAC settings
    default_role: str = "user"
    admin_paths: List[str] = field(default_factory=lambda: ["/admin", "/system"])
    protected_paths: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class DDoSProtectionConfig:
    """DDoS protection configuration"""
    # Detection thresholds
    volume_threshold: int = 1000  # requests/minute
    connection_threshold: int = 100
    request_size_threshold: int = 1024 * 1024  # 1MB
    pattern_anomaly_threshold: float = 0.8
    
    # Analysis windows
    analysis_window_seconds: int = 300  # 5 minutes
    pattern_window_seconds: int = 60   # 1 minute
    
    # Mitigation settings
    auto_mitigation: bool = True
    mitigation_duration_seconds: int = 3600  # 1 hour
    escalation_threshold: int = 5
    
    # Response actions
    enable_captcha: bool = True
    enable_ip_blocking: bool = True
    enable_rate_limiting: bool = True
    enable_challenge_response: bool = True


@dataclass
class ValidationConfig:
    """Request validation configuration"""
    # Size limits
    max_payload_size: int = 10 * 1024 * 1024  # 10MB
    max_header_size: int = 8192  # 8KB
    max_url_length: int = 2048
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    
    # Security checks
    enable_xss_protection: bool = True
    enable_sql_injection_detection: bool = True
    enable_command_injection_detection: bool = True
    enable_path_traversal_protection: bool = True
    enable_file_type_validation: bool = True
    
    # Content handling
    enable_sanitization: bool = True
    strict_mode: bool = False
    log_all_requests: bool = False
    
    # Allowed file types
    allowed_file_extensions: List[str] = field(default_factory=lambda: [
        ".jpg", ".jpeg", ".png", ".gif", ".pdf", ".doc", ".docx", 
        ".txt", ".csv", ".json", ".xml"
    ])
    
    # Blocked patterns
    blocked_user_agents: List[str] = field(default_factory=lambda: [
        "sqlmap", "nikto", "w3af", "burp", "nessus", "openvas"
    ])


@dataclass
class MonitoringConfig:
    """Security monitoring configuration"""
    # Logging levels
    log_level: str = "INFO"
    security_log_level: str = "WARNING"
    
    # Retention policies
    log_retention_days: int = 30
    metrics_retention_days: int = 90
    
    # Alerting
    enable_alerts: bool = True
    alert_thresholds: Dict[str, int] = field(default_factory=lambda: {
        "critical": 0,
        "high": 3,
        "medium": 15
    })
    
    # Metrics collection
    collect_performance_metrics: bool = True
    collect_security_metrics: bool = True
    metrics_interval_seconds: int = 60
    
    # Reporting
    generate_security_reports: bool = True
    report_interval_hours: int = 24


@dataclass
class RedisConfig:
    """Redis configuration optimized for <10ms performance"""
    # Connection settings
    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6379"))
    db: int = int(os.getenv("REDIS_DB", "0"))
    password: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    # Performance optimization
    connection_pool_size: int = 20
    max_connections: int = 100
    socket_timeout: float = 0.005  # 5ms
    socket_connect_timeout: float = 0.005  # 5ms
    
    # Clustering (if needed)
    cluster_mode: bool = False
    cluster_nodes: List[str] = field(default_factory=list)
    
    # Persistence
    enable_persistence: bool = True
    key_prefix: str = "security:"
    key_expiry_seconds: int = 3600


@dataclass
class UnifiedSecurityConfig:
    """Unified security configuration for all components"""
    # Component configurations
    rate_limiting: RateLimitConfig = field(default_factory=RateLimitConfig)
    authentication: AuthenticationConfig = field(default_factory=AuthenticationConfig)
    ddos_protection: DDoSProtectionConfig = field(default_factory=DDoSProtectionConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    
    # Global settings
    security_level: SecurityLevel = SecurityLevel.HIGH
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug_mode: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Integration settings
    api_gateway: ApiGatewayConfig = field(default_factory=ApiGatewayConfig)
    
    def __post_init__(self):
        """Post-initialization validation and optimization"""
        # Validate critical settings
        if self.rate_limiting.connection_timeout_ms > 10:
            raise ValueError("Rate limiting connection timeout must be ≤10ms for target performance")
        
        if self.rate_limiting.response_timeout_ms > 10:
            raise ValueError("Rate limiting response timeout must be ≤10ms for target performance")
        
        # Environment-specific adjustments
        if self.environment == "production":
            self._apply_production_optimizations()
        elif self.environment == "development":
            self._apply_development_settings()
    
    def _apply_production_optimizations(self):
        """Apply production-specific optimizations"""
        # Stricter security
        self.authentication.require_https = True
        self.validation.strict_mode = True
        self.ddos_protection.auto_mitigation = True
        
        # Performance optimization
        self.redis.connection_pool_size = 50
        self.redis.max_connections = 200
        self.rate_limiting.batch_operations = True
        
        # Monitoring
        self.monitoring.collect_performance_metrics = True
        self.monitoring.log_level = "WARNING"
        
        # Disable debug features
        self.debug_mode = False
        self.validation.log_all_requests = False
    
    def _apply_development_settings(self):
        """Apply development-specific settings"""
        # Relaxed security for development
        self.authentication.require_https = False
        self.validation.strict_mode = False
        
        # Enhanced logging
        self.monitoring.log_level = "DEBUG"
        self.validation.log_all_requests = True
        
        # Smaller limits for faster testing
        self.rate_limiting.max_requests = 1000
        self.ddos_protection.volume_threshold = 500
    
    def get_rate_limit_config_for_endpoint(self, endpoint: str, 
                                         user_role: Optional[str] = None) -> Dict[str, Any]:
        """Get rate limit configuration for a specific endpoint"""
        base_config = {
            "max_requests": self.rate_limiting.max_requests,
            "window_seconds": self.rate_limiting.window_seconds,
            "strategy": self.rate_limiting.strategy.value
        }
        
        # Apply endpoint-specific overrides
        if endpoint in self.rate_limiting.endpoint_limits:
            base_config.update(self.rate_limiting.endpoint_limits[endpoint])
        
        # Apply role-based multipliers
        if user_role and user_role in self.rate_limiting.role_multipliers:
            multiplier = self.rate_limiting.role_multipliers[user_role]
            base_config["max_requests"] = int(base_config["max_requests"] * multiplier)
        
        return base_config
    
    def get_auth_config_for_path(self, path: str) -> Dict[str, Any]:
        """Get authentication configuration for a specific path"""
        config = {
            "methods": self.authentication.enabled_methods,
            "required": True
        }
        
        # Check if path requires admin privileges
        if any(path.startswith(admin_path) for admin_path in self.authentication.admin_paths):
            config["required_role"] = "admin"
        
        # Apply path-specific permissions
        for protected_path, permissions in self.authentication.protected_paths.items():
            if path.startswith(protected_path):
                config["required_permissions"] = permissions
                break
        
        return config
    
    def is_performance_optimized(self) -> bool:
        """Check if configuration meets <10ms performance target"""
        return (
            self.rate_limiting.connection_timeout_ms <= 10 and
            self.rate_limiting.response_timeout_ms <= 10 and
            self.redis.socket_timeout <= 0.01 and
            self.redis.socket_connect_timeout <= 0.01
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "rate_limiting": {
                "strategy": self.rate_limiting.strategy.value,
                "max_requests": self.rate_limiting.max_requests,
                "window_seconds": self.rate_limiting.window_seconds,
                "performance": {
                    "connection_timeout_ms": self.rate_limiting.connection_timeout_ms,
                    "response_timeout_ms": self.rate_limiting.response_timeout_ms,
                    "batch_operations": self.rate_limiting.batch_operations
                }
            },
            "authentication": {
                "enabled_methods": self.authentication.enabled_methods,
                "require_https": self.authentication.require_https,
                "max_auth_attempts": self.authentication.max_auth_attempts
            },
            "ddos_protection": {
                "volume_threshold": self.ddos_protection.volume_threshold,
                "auto_mitigation": self.ddos_protection.auto_mitigation,
                "analysis_window_seconds": self.ddos_protection.analysis_window_seconds
            },
            "validation": {
                "max_payload_size": self.validation.max_payload_size,
                "enable_xss_protection": self.validation.enable_xss_protection,
                "enable_sanitization": self.validation.enable_sanitization
            },
            "redis": {
                "host": self.redis.host,
                "port": self.redis.port,
                "connection_pool_size": self.redis.connection_pool_size,
                "socket_timeout": self.redis.socket_timeout
            },
            "environment": self.environment,
            "security_level": self.security_level.value,
            "performance_optimized": self.is_performance_optimized()
        }
    
    @classmethod
    def from_json_file(cls, config_path: str) -> 'UnifiedSecurityConfig':
        """Load configuration from JSON file"""
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        # Create instance with defaults
        config = cls()
        
        # Apply overrides from file
        for section, values in config_data.items():
            if hasattr(config, section):
                section_config = getattr(config, section)
                for key, value in values.items():
                    if hasattr(section_config, key):
                        setattr(section_config, key, value)
        
        return config
    
    def save_to_json_file(self, config_path: str):
        """Save configuration to JSON file"""
        with open(config_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


# Default configurations for different environments
DEVELOPMENT_CONFIG = UnifiedSecurityConfig(
    rate_limiting=RateLimitConfig(
        max_requests=1000,
        window_seconds=60,
        connection_timeout_ms=5,
        response_timeout_ms=5
    ),
    authentication=AuthenticationConfig(
        require_https=False,
        max_auth_attempts=10
    ),
    ddos_protection=DDoSProtectionConfig(
        volume_threshold=500,
        auto_mitigation=False
    ),
    validation=ValidationConfig(
        strict_mode=False,
        log_all_requests=True
    ),
    monitoring=MonitoringConfig(
        log_level="DEBUG"
    ),
    redis=RedisConfig(
        connection_pool_size=10,
        socket_timeout=0.005
    )
)

PRODUCTION_CONFIG = UnifiedSecurityConfig(
    rate_limiting=RateLimitConfig(
        max_requests=100,
        window_seconds=60,
        connection_timeout_ms=3,
        response_timeout_ms=3,
        batch_operations=True
    ),
    authentication=AuthenticationConfig(
        require_https=True,
        max_auth_attempts=5
    ),
    ddos_protection=DDoSProtectionConfig(
        volume_threshold=1000,
        auto_mitigation=True
    ),
    validation=ValidationConfig(
        strict_mode=True,
        log_all_requests=False
    ),
    monitoring=MonitoringConfig(
        log_level="WARNING"
    ),
    redis=RedisConfig(
        connection_pool_size=50,
        socket_timeout=0.003
    )
)

# Set environment for production config
PRODUCTION_CONFIG.environment = "production"

# Configuration factory
def get_security_config(environment: str = None) -> UnifiedSecurityConfig:
    """Get security configuration for environment"""
    env = environment or os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        config = PRODUCTION_CONFIG
        config._apply_production_optimizations()
        return config
    elif env == "development":
        config = DEVELOPMENT_CONFIG
        config._apply_development_settings()
        return config
    else:
        # Default to development with warnings
        config = DEVELOPMENT_CONFIG
        config.monitoring.log_level = "WARNING"
        return config


# Export main configuration
default_config = get_security_config()