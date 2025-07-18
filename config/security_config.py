"""
Security Configuration Management

Handles secure configuration for JWT, database, and other security settings.
"""

import os
import secrets
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class SecurityLevel(Enum):
    """Security level configurations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PRODUCTION = "production"


@dataclass
class JWTConfig:
    """JWT configuration settings."""
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    issuer: str = "agent-hive"
    audience: str = "agent-hive-api"


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    host: str
    port: int
    database: str
    username: str
    password: str
    pool_size: int = 10
    max_overflow: int = 20
    ssl_mode: str = "require"


@dataclass
class PasswordConfig:
    """Password security configuration."""
    min_length: int = 12
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_numbers: bool = True
    require_special_chars: bool = True
    bcrypt_rounds: int = 12  # bcrypt work factor
    max_password_age_days: int = 90
    password_history_count: int = 5
    lockout_attempts: int = 5
    lockout_duration_minutes: int = 30


@dataclass
class SecurityConfig:
    """Main security configuration."""
    jwt: JWTConfig
    database: DatabaseConfig
    password: PasswordConfig
    security_level: SecurityLevel
    rate_limit_per_minute: int = 100
    max_auth_attempts: int = 5
    auth_window_minutes: int = 15
    session_timeout_minutes: int = 30
    https_only: bool = True
    cors_origins: list = None
    enable_2fa: bool = False
    audit_log_retention_days: int = 90
    security_headers_enabled: bool = True
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = []


class SecurityConfigManager:
    """Manages security configuration with environment variable support."""
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.MEDIUM):
        self.security_level = security_level
        self._config: Optional[SecurityConfig] = None
    
    def get_config(self) -> SecurityConfig:
        """Get or create security configuration."""
        if self._config is None:
            self._config = self._create_config()
        return self._config
    
    def _create_config(self) -> SecurityConfig:
        """Create security configuration from environment variables."""
        jwt_config = self._create_jwt_config()
        database_config = self._create_database_config()
        password_config = self._create_password_config()
        
        return SecurityConfig(
            jwt=jwt_config,
            database=database_config,
            password=password_config,
            security_level=self.security_level,
            rate_limit_per_minute=self._get_int_env("RATE_LIMIT_PER_MINUTE", 100),
            max_auth_attempts=self._get_int_env("MAX_AUTH_ATTEMPTS", 5),
            auth_window_minutes=self._get_int_env("AUTH_WINDOW_MINUTES", 15),
            session_timeout_minutes=self._get_int_env("SESSION_TIMEOUT_MINUTES", 30),
            https_only=self._get_bool_env("HTTPS_ONLY", True),
            cors_origins=self._get_list_env("CORS_ORIGINS", []),
            enable_2fa=self._get_bool_env("ENABLE_2FA", False),
            audit_log_retention_days=self._get_int_env("AUDIT_LOG_RETENTION_DAYS", 90),
            security_headers_enabled=self._get_bool_env("SECURITY_HEADERS_ENABLED", True)
        )
    
    def _create_jwt_config(self) -> JWTConfig:
        """Create JWT configuration."""
        secret_key = os.getenv("JWT_SECRET_KEY")
        if not secret_key:
            if self.security_level == SecurityLevel.PRODUCTION:
                raise ValueError("JWT_SECRET_KEY environment variable is required in production")
            else:
                # Generate a secure random key for development
                secret_key = secrets.token_urlsafe(32)
                print(f"WARNING: Generated JWT secret key for development: {secret_key}")
        
        return JWTConfig(
            secret_key=secret_key,
            algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            access_token_expire_minutes=self._get_int_env("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 15),
            refresh_token_expire_days=self._get_int_env("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 30),
            issuer=os.getenv("JWT_ISSUER", "agent-hive"),
            audience=os.getenv("JWT_AUDIENCE", "agent-hive-api")
        )
    
    def _create_database_config(self) -> DatabaseConfig:
        """Create database configuration."""
        return DatabaseConfig(
            host=os.getenv("DB_HOST", "localhost"),
            port=self._get_int_env("DB_PORT", 5432),
            database=os.getenv("DB_NAME", "agent_hive"),
            username=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            pool_size=self._get_int_env("DB_POOL_SIZE", 10),
            max_overflow=self._get_int_env("DB_MAX_OVERFLOW", 20),
            ssl_mode=os.getenv("DB_SSL_MODE", "require")
        )
    
    def _create_password_config(self) -> PasswordConfig:
        """Create password configuration."""
        # Adjust bcrypt rounds based on security level
        bcrypt_rounds = 12  # default
        if self.security_level == SecurityLevel.HIGH:
            bcrypt_rounds = 14
        elif self.security_level == SecurityLevel.PRODUCTION:
            bcrypt_rounds = 15
        elif self.security_level == SecurityLevel.LOW:
            bcrypt_rounds = 10
        
        return PasswordConfig(
            min_length=self._get_int_env("PASSWORD_MIN_LENGTH", 12),
            require_uppercase=self._get_bool_env("PASSWORD_REQUIRE_UPPERCASE", True),
            require_lowercase=self._get_bool_env("PASSWORD_REQUIRE_LOWERCASE", True),
            require_numbers=self._get_bool_env("PASSWORD_REQUIRE_NUMBERS", True),
            require_special_chars=self._get_bool_env("PASSWORD_REQUIRE_SPECIAL", True),
            bcrypt_rounds=self._get_int_env("BCRYPT_ROUNDS", bcrypt_rounds),
            max_password_age_days=self._get_int_env("PASSWORD_MAX_AGE_DAYS", 90),
            password_history_count=self._get_int_env("PASSWORD_HISTORY_COUNT", 5),
            lockout_attempts=self._get_int_env("PASSWORD_LOCKOUT_ATTEMPTS", 5),
            lockout_duration_minutes=self._get_int_env("PASSWORD_LOCKOUT_DURATION", 30)
        )
    
    def _get_int_env(self, key: str, default: int) -> int:
        """Get integer environment variable."""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            print(f"WARNING: Invalid integer value for {key}: {value}, using default {default}")
            return default
    
    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean environment variable."""
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")
    
    def _get_list_env(self, key: str, default: list) -> list:
        """Get list environment variable (comma-separated)."""
        value = os.getenv(key)
        if value is None:
            return default
        return [item.strip() for item in value.split(",") if item.strip()]
    
    def validate_password(self, password: str) -> Dict[str, Any]:
        """Validate a password against security policy."""
        config = self.get_config()
        issues = []
        
        if len(password) < config.password.min_length:
            issues.append(f"Password must be at least {config.password.min_length} characters long")
        
        if config.password.require_uppercase and not any(c.isupper() for c in password):
            issues.append("Password must contain at least one uppercase letter")
        
        if config.password.require_lowercase and not any(c.islower() for c in password):
            issues.append("Password must contain at least one lowercase letter")
        
        if config.password.require_numbers and not any(c.isdigit() for c in password):
            issues.append("Password must contain at least one number")
        
        if config.password.require_special_chars:
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(c in special_chars for c in password):
                issues.append("Password must contain at least one special character")
        
        # Check for common weak patterns
        weak_patterns = ["123", "abc", "password", "admin", "user"]
        password_lower = password.lower()
        for pattern in weak_patterns:
            if pattern in password_lower:
                issues.append(f"Password contains weak pattern: {pattern}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "strength_score": self._calculate_password_strength(password)
        }
    
    def _calculate_password_strength(self, password: str) -> int:
        """Calculate password strength score (0-100)."""
        score = 0
        
        # Length bonus
        score += min(len(password) * 2, 25)
        
        # Character variety bonus
        if any(c.isupper() for c in password):
            score += 10
        if any(c.islower() for c in password):
            score += 10
        if any(c.isdigit() for c in password):
            score += 10
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 15
        
        # Entropy bonus
        unique_chars = len(set(password))
        score += min(unique_chars * 2, 20)
        
        # Penalize common patterns
        if any(pattern in password.lower() for pattern in ["123", "abc", "password"]):
            score -= 20
        
        return max(0, min(100, score))
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration and return validation results."""
        config = self.get_config()
        issues = []
        
        # JWT validation
        if len(config.jwt.secret_key) < 32:
            issues.append("JWT secret key should be at least 32 characters long")
        
        if config.jwt.algorithm not in ["HS256", "HS384", "HS512"]:
            issues.append(f"JWT algorithm {config.jwt.algorithm} is not recommended")
        
        # Database validation
        if not config.database.password and config.security_level == SecurityLevel.PRODUCTION:
            issues.append("Database password is required in production")
        
        # Password policy validation
        if config.password.bcrypt_rounds < 10:
            issues.append("bcrypt rounds should be at least 10 for security")
        if config.password.bcrypt_rounds > 20:
            issues.append("bcrypt rounds above 20 may cause performance issues")
        
        # Security level validation
        if config.security_level == SecurityLevel.PRODUCTION:
            if not config.https_only:
                issues.append("HTTPS should be enforced in production")
            if config.max_auth_attempts > 10:
                issues.append("Max auth attempts should be limited in production")
            if config.password.bcrypt_rounds < 12:
                issues.append("bcrypt rounds should be at least 12 in production")
            if not config.security_headers_enabled:
                issues.append("Security headers should be enabled in production")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "config": config
        }
    
    def get_auth_middleware_config(self) -> Dict[str, Any]:
        """Get configuration for AuthenticationMiddleware."""
        config = self.get_config()
        
        return {
            "enabled_methods": ["api_key", "jwt", "basic"],
            "jwt_secret": config.jwt.secret_key,
            "jwt_algorithm": config.jwt.algorithm,
            "token_expiry_hours": config.jwt.access_token_expire_minutes / 60,
            "max_auth_attempts": config.max_auth_attempts,
            "auth_window_minutes": config.auth_window_minutes,
            "rate_limit_per_minute": config.rate_limit_per_minute
        }


# Global configuration manager instance
security_config_manager = SecurityConfigManager()


def get_security_config() -> SecurityConfig:
    """Get the global security configuration."""
    return security_config_manager.get_config()


def get_auth_config() -> Dict[str, Any]:
    """Get authentication middleware configuration."""
    return security_config_manager.get_auth_middleware_config()