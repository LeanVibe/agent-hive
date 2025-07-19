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

# Optional imports for advanced security features
try:
    from .vulnerability_scanner import VulnerabilityScanner
    from .enhanced_middleware import EnhancedSecurityMiddleware
    __all__.extend(['VulnerabilityScanner', 'EnhancedSecurityMiddleware'])
except ImportError:
    pass

# Advanced Security Features (PR #6)
try:
    from .two_factor_auth import TwoFactorAuthManager, TwoFactorMethod, TrustedDevice, BackupCode
    from .api_key_manager import ApiKeyManager, ApiKeyType, ApiKeyStatus, ApiKeyScope
    from .compliance_reporter import ComplianceReporter, ComplianceStandard, ComplianceStatus, ComplianceControl
    from .threat_detector import MLThreatDetector, ThreatLevel, ThreatCategory, ThreatEvent, ThreatAlert
    
    __all__.extend([
        'TwoFactorAuthManager', 'TwoFactorMethod', 'TrustedDevice', 'BackupCode',
        'ApiKeyManager', 'ApiKeyType', 'ApiKeyStatus', 'ApiKeyScope',
        'ComplianceReporter', 'ComplianceStandard', 'ComplianceStatus', 'ComplianceControl',
        'MLThreatDetector', 'ThreatLevel', 'ThreatCategory', 'ThreatEvent', 'ThreatAlert'
    ])
except ImportError as e:
    print(f"Warning: Advanced security features could not be imported: {e}")

# RBAC System imports
try:
    from .rbac_manager import RBACManager
    __all__.extend(['RBACManager'])
except ImportError:
    pass

# Rate Limiting imports  
try:
    from .rate_limiter import RateLimiter
    __all__.extend(['RateLimiter'])
except ImportError:
    pass

# Advanced Security Coordinator
try:
    from .advanced_security_coordinator import AdvancedSecurityCoordinator, SecurityMetrics
    __all__.extend(['AdvancedSecurityCoordinator', 'SecurityMetrics'])
except ImportError as e:
    print(f"Warning: Advanced Security Coordinator could not be imported: {e}")