#!/usr/bin/env python3
"""
JWT Core Manager

Essential JWT token operations for Agent Hive authentication.
Focused on core create, validate, and revoke operations.
"""

import jwt
import time
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from external_api.auth_middleware import Permission, AuthResult


logger = logging.getLogger(__name__)


class TokenType(Enum):
    """JWT token types."""
    ACCESS = "access"
    REFRESH = "refresh"


class TokenStatus(Enum):
    """Token status."""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass
class TokenData:
    """Token data for tracking."""
    token_id: str
    user_id: str
    token_type: TokenType
    expires_at: datetime
    status: TokenStatus
    permissions: List[Permission]


class JWTCore:
    """
    Core JWT token manager with essential operations.
    
    Features:
    - Secure JWT token creation and validation
    - Token revocation with blacklist
    - Permission-based access control
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize JWT core manager."""
        self.secret_key = config.get("jwt_secret", "change-this-secret")
        self.algorithm = config.get("jwt_algorithm", "HS256")
        self.default_expiry_hours = config.get("token_expiry_hours", 1)
        
        # Token storage
        self.tokens: Dict[str, TokenData] = {}
        self.blacklist: set = set()
        
        logger.info("JWT Core initialized")
    
    async def create_token(self, user_id: str, token_type: TokenType,
                          permissions: List[Permission], 
                          expires_in_hours: Optional[float] = None) -> Tuple[str, str]:
        """
        Create a JWT token.
        
        Returns:
            Tuple of (token, token_id)
        """
        # Generate unique token ID
        token_id = str(uuid.uuid4())
        
        # Calculate expiration
        if expires_in_hours is None:
            expires_in_hours = self.default_expiry_hours
        
        issued_at = datetime.utcnow()
        expires_at = issued_at + timedelta(hours=expires_in_hours)
        
        # Create token payload
        payload = {
            "token_id": token_id,
            "user_id": user_id,
            "token_type": token_type.value,
            "permissions": [p.value for p in permissions],
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
            "iss": "agent-hive",
            "sub": user_id
        }
        
        # Generate JWT token
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # Store token data
        self.tokens[token_id] = TokenData(
            token_id=token_id,
            user_id=user_id,
            token_type=token_type,
            expires_at=expires_at,
            status=TokenStatus.ACTIVE,
            permissions=permissions
        )
        
        logger.info(f"Created {token_type.value} token for user {user_id}")
        return token, token_id
    
    async def validate_token(self, token: str, 
                           required_permissions: Optional[List[Permission]] = None) -> AuthResult:
        """
        Validate JWT token.
        
        Returns:
            AuthResult with validation status
        """
        try:
            # Decode token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            token_id = payload.get("token_id")
            
            if not token_id:
                return AuthResult(success=False, error="Invalid token format")
            
            # Check blacklist
            if token_id in self.blacklist:
                return AuthResult(success=False, error="Token revoked")
            
            # Get token data
            token_data = self.tokens.get(token_id)
            if not token_data:
                return AuthResult(success=False, error="Token not found")
            
            # Check status
            if token_data.status != TokenStatus.ACTIVE:
                return AuthResult(success=False, error=f"Token {token_data.status.value}")
            
            # Check expiration
            if datetime.utcnow() > token_data.expires_at:
                token_data.status = TokenStatus.EXPIRED
                return AuthResult(success=False, error="Token expired")
            
            # Check permissions
            if required_permissions:
                token_perms = set(token_data.permissions)
                required_perms = set(required_permissions)
                
                if not required_perms.issubset(token_perms):
                    return AuthResult(success=False, error="Insufficient permissions")
            
            # Success
            return AuthResult(
                success=True,
                user_id=token_data.user_id,
                permissions=token_data.permissions,
                metadata={
                    "token_id": token_id,
                    "token_type": token_data.token_type.value,
                    "expires_at": token_data.expires_at.isoformat()
                }
            )
            
        except jwt.ExpiredSignatureError:
            return AuthResult(success=False, error="Token expired")
        except jwt.InvalidTokenError:
            return AuthResult(success=False, error="Invalid token")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return AuthResult(success=False, error="Validation failed")
    
    async def revoke_token(self, token_id: str) -> bool:
        """
        Revoke a token.
        
        Returns:
            True if successfully revoked
        """
        try:
            # Add to blacklist
            self.blacklist.add(token_id)
            
            # Update status
            if token_id in self.tokens:
                self.tokens[token_id].status = TokenStatus.REVOKED
            
            logger.info(f"Token {token_id} revoked")
            return True
            
        except Exception as e:
            logger.error(f"Token revocation failed: {e}")
            return False
    
    async def revoke_user_tokens(self, user_id: str, 
                               exclude_token_id: Optional[str] = None) -> int:
        """
        Revoke all tokens for a user.
        
        Returns:
            Number of tokens revoked
        """
        revoked_count = 0
        
        for token_id, token_data in self.tokens.items():
            if (token_data.user_id == user_id and 
                token_data.status == TokenStatus.ACTIVE and
                token_id != exclude_token_id):
                
                if await self.revoke_token(token_id):
                    revoked_count += 1
        
        logger.info(f"Revoked {revoked_count} tokens for user {user_id}")
        return revoked_count
    
    def get_active_count(self, user_id: Optional[str] = None) -> int:
        """Get active token count."""
        active_tokens = [t for t in self.tokens.values() if t.status == TokenStatus.ACTIVE]
        if user_id:
            active_tokens = [t for t in active_tokens if t.user_id == user_id]
        return len(active_tokens)
    
    def cleanup_expired(self) -> int:
        """Clean up expired tokens."""
        current_time = datetime.utcnow()
        expired_count = 0
        
        for token_data in self.tokens.values():
            if (token_data.expires_at < current_time and 
                token_data.status == TokenStatus.ACTIVE):
                token_data.status = TokenStatus.EXPIRED
                self.blacklist.add(token_data.token_id)
                expired_count += 1
        
        return expired_count