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
class SecurityConfig:
    """Main security configuration."""
    jwt: JWTConfig
    database: DatabaseConfig
    security_level: SecurityLevel
    rate_limit_per_minute: int = 100
    max_auth_attempts: int = 5
    auth_window_minutes: int = 15
    session_timeout_minutes: int = 30
    https_only: bool = True
    cors_origins: list = None
    
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
        
        return SecurityConfig(
            jwt=jwt_config,
            database=database_config,
            security_level=self.security_level,
            rate_limit_per_minute=self._get_int_env("RATE_LIMIT_PER_MINUTE", 100),
            max_auth_attempts=self._get_int_env("MAX_AUTH_ATTEMPTS", 5),
            auth_window_minutes=self._get_int_env("AUTH_WINDOW_MINUTES", 15),
            session_timeout_minutes=self._get_int_env("SESSION_TIMEOUT_MINUTES", 30),
            https_only=self._get_bool_env("HTTPS_ONLY", True),
            cors_origins=self._get_list_env("CORS_ORIGINS", [])
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
        
        # Security level validation
        if config.security_level == SecurityLevel.PRODUCTION:
            if not config.https_only:
                issues.append("HTTPS should be enforced in production")
            if config.max_auth_attempts > 10:
                issues.append("Max auth attempts should be limited in production")
        
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