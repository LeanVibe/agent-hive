"""
Security module for LeanVibe Agent Hive.

This module provides comprehensive security features including authentication,
authorization, token management, and vulnerability scanning.
"""

# Import only core security components to avoid dependency issues
try:
    from .auth_service import AuthenticationService, UserRole, User, UserSession
    from .token_manager import SecureTokenManager
    from .security_manager import SecurityManager
    from .quality_gates import SecurityQualityGates
    
    __all__ = [
        'AuthenticationService',
        'UserRole',
        'User',
        'UserSession',
        'SecureTokenManager',
        'SecurityManager',
        'SecurityQualityGates'
    ]
except ImportError as e:
    # Fallback if dependencies are missing
    __all__ = []
    print(f"Warning: Some security modules could not be imported: {e}")

# Optional imports
try:
    from .vulnerability_scanner import VulnerabilityScanner
    from .enhanced_middleware import EnhancedSecurityMiddleware
    __all__.extend(['VulnerabilityScanner', 'EnhancedSecurityMiddleware'])
except ImportError:
    pass