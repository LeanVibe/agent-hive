"""Common authentication models and types.

Shared authentication classes to prevent circular imports between
security and external_api modules.
"""

from enum import Enum
from typing import Dict, Any, Optional, List


class Permission(Enum):
    """System permissions."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    EXECUTE = "execute"


class AuthResult:
    """Authentication result."""

    def __init__(self, success: bool, user_id: Optional[str] = None,
                 permissions: Optional[List[Permission]] = None,
                 error: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self.success = success
        self.user_id = user_id
        self.permissions = permissions or []
        self.error = error
        self.metadata = metadata or {}
    
    def __repr__(self) -> str:
        return f"AuthResult(success={self.success}, user_id={self.user_id}, error={self.error})"
