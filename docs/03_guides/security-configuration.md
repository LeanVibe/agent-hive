# Security Configuration Guide

This guide provides comprehensive security configuration for LeanVibe Agent Hive, covering authentication, authorization, encryption, and security best practices.

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Security Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Client    │  │   Admin     │  │   Service   │            │
│  │Application  │  │  Console    │  │Integration  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│         │               │               │                     │
│         │ (Auth)        │ (Auth)        │ (mTLS)              │
│         ▼               ▼               ▼                     │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              API Gateway                                │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│  │  │   Auth      │  │    RBAC     │  │   Rate Limiting │  │  │
│  │  │ Provider    │  │   Engine    │  │      WAF        │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │  │
│  └─────────────────────────────────────────────────────────┘  │
│                           │                                   │
│                           ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Agent Coordination Layer                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│  │  │   Audit     │  │   Crypto    │  │   Secure Comm   │  │  │
│  │  │  Logger     │  │   Service   │  │                 │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │  │
│  └─────────────────────────────────────────────────────────┘  │
│                           │                                   │
│                           ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Secure Data Layer                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│  │  │ Encrypted   │  │   Secret    │  │   Backup &      │  │  │
│  │  │  Storage    │  │ Management  │  │   Recovery      │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Authentication Configuration

### OAuth 2.0 / OpenID Connect

#### Basic OAuth Configuration

```yaml
authentication:
  provider: "oauth2"
  oauth2:
    # Authorization Server
    authorization_url: "https://auth.leanvibe.com/oauth/authorize"
    token_url: "https://auth.leanvibe.com/oauth/token"
    userinfo_url: "https://auth.leanvibe.com/oauth/userinfo"
    revocation_url: "https://auth.leanvibe.com/oauth/revoke"
    
    # Client Configuration
    client_id: "${OAUTH_CLIENT_ID}"
    client_secret: "${OAUTH_CLIENT_SECRET}"
    redirect_uri: "https://api.leanvibe.com/auth/callback"
    
    # Scopes
    scopes: 
      - "openid"
      - "profile"
      - "email"
      - "agents:read"
      - "agents:write"
      - "workflows:read"
      - "workflows:write"
      - "admin"
    
    # Token Configuration
    token_validation:
      verify_signature: true
      verify_audience: true
      verify_issuer: true
      leeway: 30  # seconds
      max_age: 3600  # 1 hour
      
    # Refresh Token
    refresh_token:
      enabled: true
      rotation: true  # Rotate refresh tokens
      expire_days: 30
```

#### JWT Configuration

```yaml
authentication:
  provider: "jwt"
  jwt:
    # Signing Configuration
    secret_key: "${JWT_SECRET_KEY}"  # For HMAC
    algorithm: "HS256"  # Options: HS256, RS256, ES256
    
    # RSA Configuration (for RS256)
    rsa:
      private_key_path: "/etc/ssl/private/jwt-signing.key"
      public_key_path: "/etc/ssl/certs/jwt-signing.pub"
      
    # Token Lifecycle
    expire_minutes: 30
    refresh_expire_days: 7
    not_before_leeway: 5  # seconds
    
    # Claims Configuration
    issuer: "leanvibe-agent-hive"
    audience: ["api.leanvibe.com", "agents.leanvibe.com"]
    
    # Custom Claims
    custom_claims:
      user_id: "required"
      roles: "required"
      permissions: "optional"
      tenant_id: "optional"
      agent_access: "optional"
```

#### Multi-Factor Authentication

```yaml
mfa:
  enabled: true
  required_for_roles: ["admin", "operator"]
  
  # TOTP Configuration
  totp:
    enabled: true
    issuer: "LeanVibe Agent Hive"
    algorithm: "SHA1"
    digits: 6
    period: 30
    
  # SMS Configuration
  sms:
    enabled: true
    provider: "twilio"
    config:
      account_sid: "${TWILIO_ACCOUNT_SID}"
      auth_token: "${TWILIO_AUTH_TOKEN}"
      from_number: "+1234567890"
      
  # Email Configuration
  email:
    enabled: true
    provider: "sendgrid"
    config:
      api_key: "${SENDGRID_API_KEY}"
      from_email: "noreply@leanvibe.com"
      
  # Backup Codes
  backup_codes:
    enabled: true
    count: 10
    length: 8
```

### Implementation

```python
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import jwt
import bcrypt
import pyotp
from dataclasses import dataclass

@dataclass
class User:
    """User model for authentication."""
    user_id: str
    username: str
    email: str
    password_hash: str
    roles: List[str]
    permissions: List[str]
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    is_active: bool = True
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None

class AuthenticationManager:
    """Handles authentication and token management."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.jwt_config = config.get('jwt', {})
        self.mfa_config = config.get('mfa', {})
        
    def authenticate_user(self, username: str, password: str, mfa_token: str = None) -> Optional[User]:
        """Authenticate user with optional MFA."""
        # Get user from database
        user = self._get_user_by_username(username)
        
        if not user or not user.is_active:
            return None
            
        # Check account lockout
        if user.locked_until and user.locked_until > datetime.now():
            raise AuthenticationError("Account is locked")
            
        # Verify password
        if not self._verify_password(password, user.password_hash):
            self._handle_failed_login(user)
            return None
            
        # Check MFA if enabled
        if user.mfa_enabled:
            if not mfa_token:
                raise MFARequiredError("MFA token required")
                
            if not self._verify_mfa_token(user, mfa_token):
                self._handle_failed_login(user)
                return None
        
        # Reset failed attempts on successful login
        self._reset_failed_attempts(user)
        user.last_login = datetime.now()
        
        return user
    
    def generate_tokens(self, user: User) -> Dict[str, str]:
        """Generate access and refresh tokens."""
        now = datetime.utcnow()
        
        # Access token payload
        access_payload = {
            'sub': user.user_id,
            'username': user.username,
            'email': user.email,
            'roles': user.roles,
            'permissions': user.permissions,
            'iat': now,
            'exp': now + timedelta(minutes=self.jwt_config.get('expire_minutes', 30)),
            'iss': self.jwt_config.get('issuer'),
            'aud': self.jwt_config.get('audience')
        }
        
        # Refresh token payload
        refresh_payload = {
            'sub': user.user_id,
            'type': 'refresh',
            'iat': now,
            'exp': now + timedelta(days=self.jwt_config.get('refresh_expire_days', 7)),
            'iss': self.jwt_config.get('issuer')
        }
        
        # Sign tokens
        access_token = jwt.encode(
            access_payload,
            self.jwt_config['secret_key'],
            algorithm=self.jwt_config.get('algorithm', 'HS256')
        )
        
        refresh_token = jwt.encode(
            refresh_payload,
            self.jwt_config['secret_key'],
            algorithm=self.jwt_config.get('algorithm', 'HS256')
        )
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'bearer',
            'expires_in': self.jwt_config.get('expire_minutes', 30) * 60
        }
    
    def verify_token(self, token: str) -> Dict:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.jwt_config['secret_key'],
                algorithms=[self.jwt_config.get('algorithm', 'HS256')],
                audience=self.jwt_config.get('audience'),
                issuer=self.jwt_config.get('issuer'),
                leeway=self.jwt_config.get('leeway', 0)
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def _verify_mfa_token(self, user: User, token: str) -> bool:
        """Verify MFA token."""
        if not user.mfa_secret:
            return False
            
        totp = pyotp.TOTP(user.mfa_secret)
        return totp.verify(token, valid_window=1)
    
    def _handle_failed_login(self, user: User):
        """Handle failed login attempt."""
        user.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.now() + timedelta(minutes=30)
            
    def _reset_failed_attempts(self, user: User):
        """Reset failed login attempts."""
        user.failed_login_attempts = 0
        user.locked_until = None

class MFAManager:
    """Handles multi-factor authentication."""
    
    def setup_totp(self, user: User) -> Dict[str, str]:
        """Setup TOTP for user."""
        secret = pyotp.random_base32()
        
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="LeanVibe Agent Hive"
        )
        
        return {
            'secret': secret,
            'qr_code_uri': provisioning_uri,
            'backup_codes': self._generate_backup_codes()
        }
    
    def verify_totp_setup(self, secret: str, token: str) -> bool:
        """Verify TOTP setup token."""
        totp = pyotp.TOTP(secret)
        return totp.verify(token)
    
    def _generate_backup_codes(self) -> List[str]:
        """Generate backup codes for MFA."""
        import secrets
        import string
        
        codes = []
        for _ in range(10):
            code = ''.join(secrets.choice(string.digits) for _ in range(8))
            codes.append(code)
        return codes
```

## Authorization Configuration

### Role-Based Access Control (RBAC)

```yaml
authorization:
  rbac:
    enabled: true
    
    # Roles Definition
    roles:
      # Super Administrator
      super_admin:
        description: "Full system access"
        permissions: ["*"]
        inherits: []
        
      # System Administrator
      admin:
        description: "System administration"
        permissions:
          - "system:read"
          - "system:write"
          - "users:*"
          - "agents:*"
          - "workflows:*"
          - "configs:*"
        inherits: []
        
      # Operations Team
      operator:
        description: "Operations and monitoring"
        permissions:
          - "agents:read"
          - "agents:start"
          - "agents:stop"
          - "workflows:read"
          - "workflows:execute"
          - "monitoring:read"
          - "logs:read"
        inherits: []
        
      # Developer
      developer:
        description: "Development access"
        permissions:
          - "agents:read"
          - "agents:write"
          - "workflows:read"
          - "workflows:write"
          - "configs:read"
          - "logs:read"
        inherits: ["viewer"]
        
      # Viewer
      viewer:
        description: "Read-only access"
        permissions:
          - "agents:read"
          - "workflows:read"
          - "monitoring:read"
          - "logs:read"
        inherits: []
        
    # Resource-based permissions
    resources:
      agents:
        permissions: ["read", "write", "execute", "delete"]
        actions:
          read: "View agent information"
          write: "Create and modify agents"
          execute: "Start and stop agents"
          delete: "Remove agents"
          
      workflows:
        permissions: ["read", "write", "execute", "delete"]
        actions:
          read: "View workflow definitions"
          write: "Create and modify workflows"
          execute: "Run workflows"
          delete: "Remove workflows"
          
      system:
        permissions: ["read", "write", "admin"]
        actions:
          read: "View system status"
          write: "Modify system configuration"
          admin: "Administrative actions"
```

### Attribute-Based Access Control (ABAC)

```yaml
authorization:
  abac:
    enabled: true
    
    # Policy Engine
    policies:
      # Time-based access
      - name: "business_hours_only"
        description: "Allow access only during business hours"
        condition: |
          hour(now()) >= 9 AND hour(now()) <= 17 AND 
          dayofweek(now()) >= 1 AND dayofweek(now()) <= 5
        effect: "allow"
        resources: ["agents:execute", "workflows:execute"]
        
      # Location-based access
      - name: "office_network_only"
        description: "Restrict admin access to office network"
        condition: |
          user.roles contains 'admin' AND 
          request.ip_address in ['192.168.1.0/24', '10.0.0.0/8']
        effect: "allow"
        resources: ["system:admin"]
        
      # Resource ownership
      - name: "own_resources_only"
        description: "Users can only access their own resources"
        condition: |
          resource.owner == user.user_id OR 
          user.roles contains 'admin'
        effect: "allow"
        resources: ["agents:*", "workflows:*"]
        
      # Environment restrictions
      - name: "production_restrictions"
        description: "Restrict production access"
        condition: |
          (environment == 'production' AND user.roles contains 'operator') OR
          environment != 'production'
        effect: "allow"
        resources: ["workflows:execute"]
```

### Implementation

```python
from typing import Dict, List, Set
from enum import Enum
import re

class Permission(Enum):
    """Permission enumeration."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ADMIN = "admin"

class AuthorizationManager:
    """Handles authorization and access control."""
    
    def __init__(self, config: Dict):
        self.rbac_config = config.get('rbac', {})
        self.abac_config = config.get('abac', {})
        self.roles = self._load_roles()
        self.policies = self._load_policies()
        
    def check_permission(self, user: User, resource: str, action: str, context: Dict = None) -> bool:
        """Check if user has permission for resource action."""
        # RBAC Check
        if self.rbac_config.get('enabled', True):
            if self._check_rbac_permission(user, resource, action):
                # If RBAC allows, check ABAC policies
                if self.abac_config.get('enabled', False):
                    return self._check_abac_policies(user, resource, action, context or {})
                return True
                
        # ABAC only check
        if self.abac_config.get('enabled', False):
            return self._check_abac_policies(user, resource, action, context or {})
            
        return False
    
    def _check_rbac_permission(self, user: User, resource: str, action: str) -> bool:
        """Check RBAC permissions."""
        user_permissions = self._get_user_permissions(user)
        
        # Check wildcard permissions
        if "*" in user_permissions:
            return True
            
        # Check specific resource permissions
        permission_patterns = [
            f"{resource}:*",
            f"{resource}:{action}",
            f"*:{action}"
        ]
        
        for pattern in permission_patterns:
            if pattern in user_permissions:
                return True
                
        return False
    
    def _check_abac_policies(self, user: User, resource: str, action: str, context: Dict) -> bool:
        """Check ABAC policies."""
        for policy in self.policies:
            if self._matches_policy_resources(policy, resource, action):
                if self._evaluate_policy_condition(policy, user, context):
                    return policy.get('effect') == 'allow'
                    
        return False
    
    def _get_user_permissions(self, user: User) -> Set[str]:
        """Get all permissions for user including inherited."""
        permissions = set()
        
        for role_name in user.roles:
            role = self.roles.get(role_name, {})
            
            # Add direct permissions
            role_permissions = role.get('permissions', [])
            permissions.update(role_permissions)
            
            # Add inherited permissions
            for inherited_role in role.get('inherits', []):
                inherited_permissions = self._get_role_permissions(inherited_role)
                permissions.update(inherited_permissions)
                
        return permissions
    
    def _get_role_permissions(self, role_name: str) -> Set[str]:
        """Get permissions for a specific role."""
        role = self.roles.get(role_name, {})
        permissions = set(role.get('permissions', []))
        
        # Recursively get inherited permissions
        for inherited_role in role.get('inherits', []):
            inherited_permissions = self._get_role_permissions(inherited_role)
            permissions.update(inherited_permissions)
            
        return permissions

class SecurityMiddleware:
    """Security middleware for request processing."""
    
    def __init__(self, auth_manager: AuthenticationManager, authz_manager: AuthorizationManager):
        self.auth_manager = auth_manager
        self.authz_manager = authz_manager
        
    async def authenticate_request(self, request) -> Optional[User]:
        """Authenticate incoming request."""
        # Extract token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return None
            
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        try:
            # Verify token
            payload = self.auth_manager.verify_token(token)
            
            # Get user from payload
            user = User(
                user_id=payload['sub'],
                username=payload['username'],
                email=payload['email'],
                roles=payload['roles'],
                permissions=payload['permissions'],
                password_hash="",  # Not needed for request auth
            )
            
            return user
            
        except AuthenticationError:
            return None
    
    async def authorize_request(self, user: User, request) -> bool:
        """Authorize request based on user and resource."""
        # Extract resource and action from request
        resource, action = self._extract_resource_action(request)
        
        # Build context
        context = {
            'ip_address': request.client.host,
            'user_agent': request.headers.get('User-Agent', ''),
            'timestamp': datetime.now(),
            'method': request.method,
            'path': request.url.path
        }
        
        return self.authz_manager.check_permission(user, resource, action, context)
    
    def _extract_resource_action(self, request) -> tuple:
        """Extract resource and action from request."""
        path = request.url.path.strip('/')
        method = request.method.lower()
        
        # Parse API path
        parts = path.split('/')
        
        if len(parts) >= 3 and parts[0] == 'api':
            resource = parts[2]  # e.g., 'agents', 'workflows'
            
            # Map HTTP method to action
            action_map = {
                'get': 'read',
                'post': 'write',
                'put': 'write',
                'patch': 'write',
                'delete': 'delete'
            }
            
            action = action_map.get(method, 'read')
            
            return resource, action
            
        return 'unknown', 'read'
```

## Encryption Configuration

### Data Encryption at Rest

```yaml
encryption:
  at_rest:
    enabled: true
    
    # Database encryption
    database:
      enabled: true
      provider: "aes-256-gcm"
      key_source: "env"  # env, file, vault
      key_env_var: "DATABASE_ENCRYPTION_KEY"
      key_rotation:
        enabled: true
        interval_days: 90
        
    # File system encryption
    filesystem:
      enabled: true
      paths:
        - "/var/lib/leanvibe/data"
        - "/var/lib/leanvibe/logs"
      provider: "luks"
      
    # Backup encryption
    backups:
      enabled: true
      provider: "aes-256-gcm"
      key_source: "vault"
      compression: true
```

### Data Encryption in Transit

```yaml
encryption:
  in_transit:
    # TLS Configuration
    tls:
      enabled: true
      min_version: "1.2"
      max_version: "1.3"
      
      # Certificate configuration
      certificates:
        cert_file: "/etc/ssl/certs/leanvibe.crt"
        key_file: "/etc/ssl/private/leanvibe.key"
        ca_file: "/etc/ssl/certs/ca.crt"
        
      # Cipher suites
      cipher_suites:
        - "TLS_AES_256_GCM_SHA384"
        - "TLS_CHACHA20_POLY1305_SHA256"
        - "TLS_AES_128_GCM_SHA256"
        - "ECDHE-RSA-AES256-GCM-SHA384"
        
    # mTLS for service-to-service
    mtls:
      enabled: true
      require_client_cert: true
      verify_client_cert: true
      
    # Application-level encryption
    application:
      enabled: true
      algorithm: "ChaCha20-Poly1305"
      key_exchange: "X25519"
```

### Secret Management

```yaml
secrets:
  provider: "vault"  # vault, aws_kms, azure_kv, gcp_kms
  
  # HashiCorp Vault
  vault:
    address: "https://vault.leanvibe.com:8200"
    auth_method: "kubernetes"  # kubernetes, aws, azure, gcp, token
    
    # Kubernetes auth
    kubernetes:
      role: "leanvibe-agent-hive"
      service_account_token_path: "/var/run/secrets/kubernetes.io/serviceaccount/token"
      
    # Secret paths
    paths:
      database: "secret/data/leanvibe/database"
      jwt_keys: "secret/data/leanvibe/jwt"
      api_keys: "secret/data/leanvibe/api"
      
    # Auto-renewal
    auto_renew: true
    renew_threshold: 0.1  # Renew when 10% of lease time remaining
```

### Implementation

```python
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class EncryptionManager:
    """Handles encryption and decryption operations."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.fernet = self._init_fernet()
        
    def _init_fernet(self) -> Fernet:
        """Initialize Fernet encryption."""
        # Get encryption key from configuration
        key = self._get_encryption_key()
        return Fernet(key)
        
    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key."""
        key_source = self.config.get('key_source', 'env')
        
        if key_source == 'env':
            key_var = self.config.get('key_env_var', 'ENCRYPTION_KEY')
            key_b64 = os.getenv(key_var)
            
            if not key_b64:
                raise ValueError(f"Encryption key not found in environment variable: {key_var}")
                
            return base64.urlsafe_b64decode(key_b64)
            
        elif key_source == 'file':
            key_file = self.config.get('key_file')
            with open(key_file, 'rb') as f:
                return base64.urlsafe_b64decode(f.read())
                
        else:
            raise ValueError(f"Unsupported key source: {key_source}")
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        encrypted = self.fernet.encrypt(data)
        return base64.urlsafe_b64encode(encrypted).decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data."""
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
        decrypted = self.fernet.decrypt(encrypted_bytes)
        return decrypted.decode('utf-8')
    
    def encrypt_dict(self, data: Dict) -> Dict:
        """Encrypt sensitive fields in dictionary."""
        encrypted = {}
        sensitive_fields = self.config.get('sensitive_fields', [])
        
        for key, value in data.items():
            if key in sensitive_fields:
                encrypted[key] = self.encrypt(str(value))
            else:
                encrypted[key] = value
                
        return encrypted
    
    def decrypt_dict(self, encrypted_data: Dict) -> Dict:
        """Decrypt sensitive fields in dictionary."""
        decrypted = {}
        sensitive_fields = self.config.get('sensitive_fields', [])
        
        for key, value in encrypted_data.items():
            if key in sensitive_fields:
                decrypted[key] = self.decrypt(value)
            else:
                decrypted[key] = value
                
        return decrypted

class SecretManager:
    """Manages secrets from various backends."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.provider = config.get('provider', 'env')
        self.backend = self._init_backend()
        
    def get_secret(self, path: str) -> str:
        """Get secret by path."""
        return self.backend.get_secret(path)
    
    def set_secret(self, path: str, value: str) -> bool:
        """Set secret value."""
        return self.backend.set_secret(path, value)
    
    def delete_secret(self, path: str) -> bool:
        """Delete secret."""
        return self.backend.delete_secret(path)
```

## Network Security

### Firewall Configuration

```yaml
firewall:
  enabled: true
  
  # Default policies
  default_policy:
    incoming: "deny"
    outgoing: "allow"
    forward: "deny"
    
  # Allowed ports
  allowed_ports:
    - port: 22
      protocol: "tcp"
      source: "192.168.1.0/24"  # SSH from management network
      
    - port: 443
      protocol: "tcp"
      source: "0.0.0.0/0"  # HTTPS from anywhere
      
    - port: 8080
      protocol: "tcp"
      source: "10.0.0.0/8"  # API from internal network
      
  # Rate limiting
  rate_limiting:
    enabled: true
    rules:
      - port: 443
        rate: "100/minute"
        burst: 200
        
      - port: 8080
        rate: "1000/minute"
        burst: 2000
```

### WAF (Web Application Firewall)

```yaml
waf:
  enabled: true
  mode: "prevention"  # detection, prevention
  
  # Core rule sets
  core_rules:
    enabled: true
    paranoia_level: 2  # 1-4
    
  # Custom rules
  custom_rules:
    - name: "Block SQL injection"
      pattern: "(?i)(union|select|insert|delete|update|drop|create|alter)\\s+"
      action: "block"
      
    - name: "Rate limit API"
      pattern: "^/api/"
      rate_limit: "100/minute"
      action: "rate_limit"
      
  # IP whitelisting
  whitelist:
    - "192.168.1.0/24"
    - "10.0.0.0/8"
    
  # IP blacklisting
  blacklist:
    - "0.0.0.0/32"  # Example blocked IP
```

## Audit and Logging

### Security Audit Configuration

```yaml
audit:
  enabled: true
  
  # Audit events
  events:
    authentication:
      - "login_success"
      - "login_failure"
      - "logout"
      - "token_refresh"
      - "mfa_setup"
      - "mfa_success"
      - "mfa_failure"
      
    authorization:
      - "permission_granted"
      - "permission_denied"
      - "role_assigned"
      - "role_removed"
      
    system:
      - "config_change"
      - "user_created"
      - "user_deleted"
      - "agent_started"
      - "agent_stopped"
      - "workflow_executed"
      
  # Audit log format
  format: "json"
  
  # Storage configuration
  storage:
    backend: "file"  # file, database, elasticsearch
    file:
      path: "/var/log/leanvibe/audit.log"
      rotation: "daily"
      retention: "365d"
      compression: true
      
  # Real-time monitoring
  monitoring:
    enabled: true
    alerts:
      - event: "login_failure"
        threshold: 5
        window: "5m"
        action: "email"
        
      - event: "permission_denied"
        threshold: 10
        window: "10m"
        action: "slack"
```

### Security Event Monitoring

```python
import json
import logging
from datetime import datetime
from typing import Dict, Any

class SecurityAuditor:
    """Handles security audit logging and monitoring."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = self._setup_logger()
        self.alert_manager = AlertManager(config.get('monitoring', {}))
        
    def log_authentication_event(self, event_type: str, user_id: str, details: Dict[str, Any]):
        """Log authentication-related events."""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'category': 'authentication',
            'user_id': user_id,
            'details': details,
            'source_ip': details.get('ip_address'),
            'user_agent': details.get('user_agent')
        }
        
        self.logger.info(json.dumps(event))
        
        # Check for alerts
        if event_type in ['login_failure', 'mfa_failure']:
            self.alert_manager.check_alert('authentication', event)
    
    def log_authorization_event(self, event_type: str, user_id: str, resource: str, action: str, granted: bool):
        """Log authorization-related events."""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'category': 'authorization',
            'user_id': user_id,
            'resource': resource,
            'action': action,
            'granted': granted
        }
        
        self.logger.info(json.dumps(event))
        
        # Check for alerts
        if not granted:
            self.alert_manager.check_alert('authorization', event)
    
    def log_system_event(self, event_type: str, user_id: str, details: Dict[str, Any]):
        """Log system-related events."""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'category': 'system',
            'user_id': user_id,
            'details': details
        }
        
        self.logger.info(json.dumps(event))
```

## Compliance and Standards

### GDPR Compliance

```yaml
privacy:
  gdpr:
    enabled: true
    
    # Data minimization
    data_minimization:
      enabled: true
      retention_periods:
        user_data: "2years"
        audit_logs: "7years"
        session_data: "30days"
        
    # Right to be forgotten
    data_deletion:
      enabled: true
      automated: true
      verification: true
      
    # Data portability
    data_export:
      enabled: true
      formats: ["json", "csv"]
      encryption: true
      
    # Consent management
    consent:
      required: true
      granular: true
      revocable: true
```

### SOC 2 Compliance

```yaml
compliance:
  soc2:
    enabled: true
    
    # Security controls
    security:
      access_controls: true
      network_security: true
      data_encryption: true
      vulnerability_management: true
      
    # Availability controls
    availability:
      monitoring: true
      backup_recovery: true
      incident_response: true
      
    # Processing integrity
    processing_integrity:
      data_validation: true
      error_handling: true
      audit_trails: true
      
    # Confidentiality
    confidentiality:
      data_classification: true
      access_restrictions: true
      secure_disposal: true
```

## Deployment Security

### Kubernetes Security

```yaml
# security-policies.yaml
apiVersion: v1
kind: Pod
metadata:
  name: agent-hive-secure
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 2000
    seccompProfile:
      type: RuntimeDefault
      
  containers:
  - name: app
    image: leanvibe/agent-hive:latest
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      runAsNonRoot: true
      capabilities:
        drop:
        - ALL
        
    resources:
      limits:
        memory: "1Gi"
        cpu: "500m"
      requests:
        memory: "512Mi"
        cpu: "250m"
        
    volumeMounts:
    - name: tmp
      mountPath: /tmp
    - name: cache
      mountPath: /app/cache
      
  volumes:
  - name: tmp
    emptyDir: {}
  - name: cache
    emptyDir: {}
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: agent-hive-network-policy
spec:
  podSelector:
    matchLabels:
      app: agent-hive
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api-gateway
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
```

## Security Testing

### Automated Security Testing

```yaml
security_testing:
  static_analysis:
    enabled: true
    tools:
      - "semgrep"
      - "bandit"
      - "safety"
    scan_on_commit: true
    
  dynamic_analysis:
    enabled: true
    tools:
      - "zap"
      - "nmap"
    scheduled_scans: "weekly"
    
  dependency_scanning:
    enabled: true
    tools:
      - "snyk"
      - "trivy"
    scan_on_build: true
    
  container_scanning:
    enabled: true
    tools:
      - "clair"
      - "trivy"
    scan_on_push: true
```

### Penetration Testing

```yaml
penetration_testing:
  frequency: "quarterly"
  scope:
    - "web_application"
    - "api_endpoints"
    - "network_infrastructure"
    - "social_engineering"
    
  methodology: "owasp"
  reporting:
    format: "json"
    confidentiality: "confidential"
    retention: "3years"
```

## Incident Response

### Security Incident Response Plan

```yaml
incident_response:
  enabled: true
  
  # Incident classification
  classification:
    critical:
      examples: ["data_breach", "system_compromise", "ransomware"]
      response_time: "15m"
      escalation: "immediate"
      
    high:
      examples: ["privilege_escalation", "unauthorized_access"]
      response_time: "1h"
      escalation: "2h"
      
    medium:
      examples: ["suspicious_activity", "policy_violation"]
      response_time: "4h"
      escalation: "8h"
      
  # Response team
  team:
    primary_contact: "security@leanvibe.com"
    escalation_contacts:
      - "ciso@leanvibe.com"
      - "cto@leanvibe.com"
      
  # Automated responses
  automated_responses:
    account_lockout:
      trigger: "multiple_failed_logins"
      threshold: 5
      duration: "30m"
      
    ip_blocking:
      trigger: "suspicious_activity"
      duration: "24h"
      
    service_isolation:
      trigger: "compromise_detected"
      action: "isolate_service"
```

## Best Practices

### Security Checklist

```yaml
security_checklist:
  authentication:
    - "✓ Strong password policy enforced"
    - "✓ Multi-factor authentication enabled"
    - "✓ JWT tokens properly secured"
    - "✓ Session management implemented"
    - "✓ Account lockout policies in place"
    
  authorization:
    - "✓ Role-based access control implemented"
    - "✓ Principle of least privilege followed"
    - "✓ Resource-level permissions defined"
    - "✓ Regular access reviews conducted"
    
  encryption:
    - "✓ Data encrypted at rest"
    - "✓ Data encrypted in transit"
    - "✓ Strong encryption algorithms used"
    - "✓ Key management implemented"
    - "✓ Certificate management in place"
    
  monitoring:
    - "✓ Security event logging enabled"
    - "✓ Real-time monitoring implemented"
    - "✓ Alerting configured"
    - "✓ Regular security assessments"
    - "✓ Incident response plan documented"
```

## Troubleshooting

### Common Security Issues

**Authentication Failures**
```bash
# Check JWT configuration
leanvibe security validate-jwt-config

# Test token verification
leanvibe security test-token --token "your-jwt-token"

# Check MFA setup
leanvibe security verify-mfa --user-id "user123"
```

**Authorization Issues**
```bash
# Check user permissions
leanvibe security check-permissions --user-id "user123" --resource "agents" --action "read"

# Validate RBAC configuration
leanvibe security validate-rbac

# Test ABAC policies
leanvibe security test-abac --policy "business_hours_only"
```

**Encryption Problems**
```bash
# Test encryption/decryption
leanvibe security test-encryption --data "test message"

# Validate certificates
leanvibe security validate-certs --cert-path "/etc/ssl/certs/leanvibe.crt"

# Check secret access
leanvibe security test-secrets --path "secret/database"
```

This comprehensive security configuration guide ensures that LeanVibe Agent Hive is deployed with enterprise-grade security, meeting compliance requirements and industry best practices.