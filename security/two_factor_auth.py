#!/usr/bin/env python3
"""
Two-Factor Authentication (2FA) System

Enterprise-grade two-factor authentication with TOTP support, backup codes,
device management, and comprehensive security monitoring for LeanVibe Agent Hive.
"""

import asyncio
import base64
import hashlib
import hmac
import io
import logging
import qrcode
import secrets
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Set
from dataclasses import dataclass
from enum import Enum

try:
    import pyotp
    PYOTP_AVAILABLE = True
except ImportError:
    PYOTP_AVAILABLE = False

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

from config.auth_models import Permission, AuthResult
try:
    from security.security_manager import SecurityManager
except ImportError:
    SecurityManager = None


logger = logging.getLogger(__name__)


class TwoFactorMethod(Enum):
    """Two-factor authentication methods."""
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    BACKUP_CODES = "backup_codes"
    HARDWARE_TOKEN = "hardware_token"


class DeviceStatus(Enum):
    """Device registration status."""
    PENDING = "pending"
    VERIFIED = "verified"
    TRUSTED = "trusted"
    REVOKED = "revoked"
    SUSPICIOUS = "suspicious"


@dataclass
class TrustedDevice:
    """Trusted device for 2FA bypass."""
    device_id: str
    user_id: str
    device_name: str
    device_fingerprint: str
    ip_address: str
    user_agent: str
    status: DeviceStatus
    created_at: datetime
    last_used: datetime
    expires_at: Optional[datetime]
    trust_score: float = 1.0
    verification_count: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class BackupCode:
    """Backup code for 2FA recovery."""
    code: str
    user_id: str
    created_at: datetime
    used_at: Optional[datetime] = None
    is_used: bool = False


@dataclass
class TwoFactorSession:
    """Two-factor authentication session."""
    session_id: str
    user_id: str
    challenge_type: TwoFactorMethod
    challenge_created: datetime
    challenge_expires: datetime
    verification_attempts: int = 0
    max_attempts: int = 3
    completed: bool = False
    device_id: Optional[str] = None
    ip_address: Optional[str] = None


class TwoFactorAuthManager:
    """
    Comprehensive two-factor authentication management system.
    
    Features:
    - TOTP (Time-based One-Time Password) support
    - Backup codes for account recovery
    - Trusted device management
    - Device fingerprinting and tracking
    - Security event monitoring
    - Integration with existing authentication flow
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, security_manager: Optional[Any] = None):
        """Initialize two-factor authentication manager."""
        self.config = config or self._get_default_config()
        self.security_manager = security_manager or (SecurityManager() if SecurityManager else None)
        
        # Storage for 2FA data (in production, use database)
        self.user_secrets: Dict[str, str] = {}  # user_id -> secret
        self.trusted_devices: Dict[str, List[TrustedDevice]] = {}  # user_id -> devices
        self.backup_codes: Dict[str, List[BackupCode]] = {}  # user_id -> codes
        self.two_factor_sessions: Dict[str, TwoFactorSession] = {}
        self.security_events: List[Dict[str, Any]] = []
        
        # Configuration
        self.totp_window = self.config.get("totp_window", 1)
        self.backup_code_count = self.config.get("backup_code_count", 10)
        self.trusted_device_duration_days = self.config.get("trusted_device_duration_days", 30)
        self.max_trusted_devices = self.config.get("max_trusted_devices", 5)
        self.require_device_verification = self.config.get("require_device_verification", True)
        
        # Start cleanup tasks
        self._start_cleanup_tasks()
        
        logger.info("TwoFactorAuthManager initialized")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default 2FA configuration."""
        return {
            "totp_window": 1,
            "backup_code_count": 10,
            "trusted_device_duration_days": 30,
            "max_trusted_devices": 5,
            "require_device_verification": True,
            "issuer_name": "LeanVibe Agent Hive",
            "qr_code_size": 256
        }
    
    async def setup_totp_for_user(self, user_id: str, username: str, email: str) -> Tuple[bool, str, Optional[str], Optional[bytes]]:
        """
        Set up TOTP for a user.
        
        Returns:
            Tuple of (success, message, secret, qr_code_image)
        """
        try:
            if not PYOTP_AVAILABLE:
                return False, "TOTP not available (pyotp not installed)", None, None
            
            # Generate secret
            secret = pyotp.random_base32()
            
            # Store secret
            self.user_secrets[user_id] = secret
            
            # Generate TOTP URI
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(
                name=email,
                issuer_name=self.config.get("issuer_name", "LeanVibe Agent Hive")
            )
            
            # Generate QR code
            qr_code_image = await self._generate_qr_code(provisioning_uri)
            
            # Generate backup codes
            backup_codes = await self._generate_backup_codes(user_id)
            
            # Log security event
            await self._log_security_event({
                "event_type": "2fa_setup_initiated",
                "user_id": user_id,
                "method": "totp",
                "backup_codes_generated": len(backup_codes),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"TOTP setup initiated for user: {user_id}")
            return True, "TOTP setup successful", secret, qr_code_image
            
        except Exception as e:
            logger.error(f"Failed to setup TOTP for user {user_id}: {e}")
            return False, f"TOTP setup failed: {e}", None, None
    
    async def verify_totp_setup(self, user_id: str, totp_code: str) -> Tuple[bool, str]:
        """Verify TOTP setup with initial code."""
        try:
            if not PYOTP_AVAILABLE:
                return False, "TOTP not available"
            
            secret = self.user_secrets.get(user_id)
            if not secret:
                return False, "TOTP not set up for this user"
            
            # Verify code
            totp = pyotp.TOTP(secret)
            if totp.verify(totp_code, valid_window=self.totp_window):
                # Log successful setup
                await self._log_security_event({
                    "event_type": "2fa_setup_completed",
                    "user_id": user_id,
                    "method": "totp",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                logger.info(f"TOTP setup completed for user: {user_id}")
                return True, "TOTP setup verified successfully"
            else:
                await self._log_security_event({
                    "event_type": "2fa_setup_verification_failed",
                    "user_id": user_id,
                    "method": "totp",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                return False, "Invalid TOTP code"
                
        except Exception as e:
            logger.error(f"TOTP setup verification failed for user {user_id}: {e}")
            return False, f"TOTP verification failed: {e}"
    
    async def create_two_factor_challenge(self, user_id: str, challenge_type: TwoFactorMethod, 
                                        device_id: Optional[str] = None, ip_address: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """Create a two-factor authentication challenge."""
        try:
            # Check if user has 2FA enabled
            if not await self._user_has_2fa_enabled(user_id):
                return False, "2FA not enabled for user", None
            
            # Check if device is trusted
            if device_id and await self._is_device_trusted(user_id, device_id):
                return True, "Device is trusted - 2FA bypass", None
            
            # Create challenge session
            session_id = str(uuid.uuid4())
            current_time = datetime.utcnow()
            
            session = TwoFactorSession(
                session_id=session_id,
                user_id=user_id,
                challenge_type=challenge_type,
                challenge_created=current_time,
                challenge_expires=current_time + timedelta(minutes=5),
                device_id=device_id,
                ip_address=ip_address
            )
            
            self.two_factor_sessions[session_id] = session
            
            # Log challenge creation
            await self._log_security_event({
                "event_type": "2fa_challenge_created",
                "user_id": user_id,
                "session_id": session_id,
                "challenge_type": challenge_type.value,
                "device_id": device_id,
                "ip_address": ip_address,
                "timestamp": current_time.isoformat()
            })
            
            return True, "2FA challenge created", session_id
            
        except Exception as e:
            logger.error(f"Failed to create 2FA challenge for user {user_id}: {e}")
            return False, f"2FA challenge creation failed: {e}", None
    
    async def verify_two_factor_challenge(self, session_id: str, verification_code: str, 
                                        device_fingerprint: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """Verify two-factor authentication challenge."""
        try:
            # Get session
            session = self.two_factor_sessions.get(session_id)
            if not session:
                return False, "Invalid or expired challenge session", None
            
            # Check session expiration
            if datetime.utcnow() > session.challenge_expires:
                del self.two_factor_sessions[session_id]
                return False, "Challenge session has expired", None
            
            # Check attempt limits
            if session.verification_attempts >= session.max_attempts:
                del self.two_factor_sessions[session_id]
                await self._log_security_event({
                    "event_type": "2fa_max_attempts_exceeded",
                    "user_id": session.user_id,
                    "session_id": session_id,
                    "attempts": session.verification_attempts,
                    "timestamp": datetime.utcnow().isoformat()
                })
                return False, "Maximum verification attempts exceeded", None
            
            session.verification_attempts += 1
            
            # Verify code based on challenge type
            verification_result = False
            trusted_device_id = None
            
            if session.challenge_type == TwoFactorMethod.TOTP:
                verification_result = await self._verify_totp_code(session.user_id, verification_code)
            elif session.challenge_type == TwoFactorMethod.BACKUP_CODES:
                verification_result = await self._verify_backup_code(session.user_id, verification_code)
            
            if verification_result:
                session.completed = True
                
                # Create trusted device if requested
                if device_fingerprint and self.require_device_verification:
                    trusted_device_id = await self._create_trusted_device(
                        user_id=session.user_id,
                        device_fingerprint=device_fingerprint,
                        ip_address=session.ip_address,
                        device_id=session.device_id
                    )
                
                # Log successful verification
                await self._log_security_event({
                    "event_type": "2fa_verification_successful",
                    "user_id": session.user_id,
                    "session_id": session_id,
                    "challenge_type": session.challenge_type.value,
                    "attempts": session.verification_attempts,
                    "trusted_device_created": trusted_device_id is not None,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                logger.info(f"2FA verification successful for user: {session.user_id}")
                return True, "2FA verification successful", trusted_device_id
            else:
                # Log failed verification
                await self._log_security_event({
                    "event_type": "2fa_verification_failed",
                    "user_id": session.user_id,
                    "session_id": session_id,
                    "challenge_type": session.challenge_type.value,
                    "attempts": session.verification_attempts,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                return False, "Invalid verification code", None
                
        except Exception as e:
            logger.error(f"2FA verification failed for session {session_id}: {e}")
            return False, f"2FA verification failed: {e}", None
    
    async def generate_backup_codes(self, user_id: str) -> Tuple[bool, str, Optional[List[str]]]:
        """Generate new backup codes for user."""
        try:
            # Revoke existing backup codes
            if user_id in self.backup_codes:
                for code in self.backup_codes[user_id]:
                    code.is_used = True
            
            # Generate new codes
            backup_codes = await self._generate_backup_codes(user_id)
            code_values = [code.code for code in backup_codes]
            
            # Log backup code generation
            await self._log_security_event({
                "event_type": "backup_codes_generated",
                "user_id": user_id,
                "code_count": len(backup_codes),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Generated {len(backup_codes)} backup codes for user: {user_id}")
            return True, "Backup codes generated successfully", code_values
            
        except Exception as e:
            logger.error(f"Failed to generate backup codes for user {user_id}: {e}")
            return False, f"Backup code generation failed: {e}", None
    
    async def get_trusted_devices(self, user_id: str) -> List[Dict[str, Any]]:
        """Get list of trusted devices for user."""
        devices = self.trusted_devices.get(user_id, [])
        return [
            {
                "device_id": device.device_id,
                "device_name": device.device_name,
                "status": device.status.value,
                "created_at": device.created_at.isoformat(),
                "last_used": device.last_used.isoformat(),
                "expires_at": device.expires_at.isoformat() if device.expires_at else None,
                "trust_score": device.trust_score,
                "verification_count": device.verification_count,
                "ip_address": device.ip_address,
                "user_agent": device.user_agent
            }
            for device in devices
            if device.status in [DeviceStatus.VERIFIED, DeviceStatus.TRUSTED]
        ]
    
    async def revoke_trusted_device(self, user_id: str, device_id: str) -> Tuple[bool, str]:
        """Revoke a trusted device."""
        try:
            devices = self.trusted_devices.get(user_id, [])
            for device in devices:
                if device.device_id == device_id:
                    device.status = DeviceStatus.REVOKED
                    
                    # Log device revocation
                    await self._log_security_event({
                        "event_type": "trusted_device_revoked",
                        "user_id": user_id,
                        "device_id": device_id,
                        "device_name": device.device_name,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    logger.info(f"Trusted device revoked for user {user_id}: {device_id}")
                    return True, "Trusted device revoked successfully"
            
            return False, "Trusted device not found"
            
        except Exception as e:
            logger.error(f"Failed to revoke trusted device {device_id} for user {user_id}: {e}")
            return False, f"Device revocation failed: {e}"
    
    async def disable_two_factor_auth(self, user_id: str) -> Tuple[bool, str]:
        """Disable two-factor authentication for user."""
        try:
            # Remove user's 2FA data
            self.user_secrets.pop(user_id, None)
            self.backup_codes.pop(user_id, None)
            self.trusted_devices.pop(user_id, None)
            
            # Remove any active sessions
            sessions_to_remove = [
                session_id for session_id, session in self.two_factor_sessions.items()
                if session.user_id == user_id
            ]
            for session_id in sessions_to_remove:
                del self.two_factor_sessions[session_id]
            
            # Log 2FA disabling
            await self._log_security_event({
                "event_type": "2fa_disabled",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Two-factor authentication disabled for user: {user_id}")
            return True, "Two-factor authentication disabled successfully"
            
        except Exception as e:
            logger.error(f"Failed to disable 2FA for user {user_id}: {e}")
            return False, f"2FA disabling failed: {e}"
    
    async def get_two_factor_status(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive 2FA status for user."""
        try:
            has_totp = user_id in self.user_secrets
            backup_codes = self.backup_codes.get(user_id, [])
            unused_backup_codes = [code for code in backup_codes if not code.is_used]
            trusted_devices = self.trusted_devices.get(user_id, [])
            active_devices = [
                device for device in trusted_devices
                if device.status in [DeviceStatus.VERIFIED, DeviceStatus.TRUSTED]
            ]
            
            return {
                "user_id": user_id,
                "2fa_enabled": has_totp,
                "methods": {
                    "totp": has_totp,
                    "backup_codes": len(unused_backup_codes) > 0
                },
                "backup_codes": {
                    "total": len(backup_codes),
                    "unused": len(unused_backup_codes),
                    "used": len([code for code in backup_codes if code.is_used])
                },
                "trusted_devices": {
                    "total": len(trusted_devices),
                    "active": len(active_devices),
                    "revoked": len([
                        device for device in trusted_devices
                        if device.status == DeviceStatus.REVOKED
                    ])
                },
                "security_level": self._calculate_security_level(user_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to get 2FA status for user {user_id}: {e}")
            return {"error": f"Failed to get 2FA status: {e}"}
    
    # Private helper methods
    
    async def _generate_qr_code(self, provisioning_uri: str) -> bytes:
        """Generate QR code image for TOTP setup."""
        try:
            if not QRCODE_AVAILABLE:
                logger.warning("QR code generation not available (qrcode library not installed)")
                return b""
            
            import qrcode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to bytes
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            return img_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to generate QR code: {e}")
            return b""
    
    async def _generate_backup_codes(self, user_id: str) -> List[BackupCode]:
        """Generate backup codes for user."""
        codes = []
        current_time = datetime.utcnow()
        
        for _ in range(self.backup_code_count):
            # Generate 8-character alphanumeric code
            code_value = ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(8))
            
            backup_code = BackupCode(
                code=code_value,
                user_id=user_id,
                created_at=current_time
            )
            codes.append(backup_code)
        
        # Store codes
        self.backup_codes[user_id] = codes
        
        return codes
    
    async def _verify_totp_code(self, user_id: str, code: str) -> bool:
        """Verify TOTP code."""
        if not PYOTP_AVAILABLE:
            return False
        
        secret = self.user_secrets.get(user_id)
        if not secret:
            return False
        
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=self.totp_window)
        except Exception as e:
            logger.error(f"TOTP verification error for user {user_id}: {e}")
            return False
    
    async def _verify_backup_code(self, user_id: str, code: str) -> bool:
        """Verify backup code."""
        backup_codes = self.backup_codes.get(user_id, [])
        
        for backup_code in backup_codes:
            if backup_code.code == code.upper() and not backup_code.is_used:
                backup_code.is_used = True
                backup_code.used_at = datetime.utcnow()
                return True
        
        return False
    
    async def _user_has_2fa_enabled(self, user_id: str) -> bool:
        """Check if user has 2FA enabled."""
        return user_id in self.user_secrets
    
    async def _is_device_trusted(self, user_id: str, device_id: str) -> bool:
        """Check if device is trusted for user."""
        devices = self.trusted_devices.get(user_id, [])
        current_time = datetime.utcnow()
        
        for device in devices:
            if (device.device_id == device_id and
                device.status == DeviceStatus.TRUSTED and
                (device.expires_at is None or current_time < device.expires_at)):
                
                # Update last used timestamp
                device.last_used = current_time
                device.verification_count += 1
                return True
        
        return False
    
    async def _create_trusted_device(self, user_id: str, device_fingerprint: str, 
                                   ip_address: Optional[str] = None, device_id: Optional[str] = None) -> str:
        """Create a new trusted device."""
        try:
            # Generate device ID if not provided
            if not device_id:
                device_id = str(uuid.uuid4())
            
            current_time = datetime.utcnow()
            expires_at = current_time + timedelta(days=self.trusted_device_duration_days)
            
            # Generate device name based on user agent or fingerprint
            device_name = f"Device-{device_fingerprint[:8]}"
            
            trusted_device = TrustedDevice(
                device_id=device_id,
                user_id=user_id,
                device_name=device_name,
                device_fingerprint=device_fingerprint,
                ip_address=ip_address or "unknown",
                user_agent="unknown",
                status=DeviceStatus.TRUSTED,
                created_at=current_time,
                last_used=current_time,
                expires_at=expires_at,
                verification_count=1
            )
            
            # Add to user's devices
            if user_id not in self.trusted_devices:
                self.trusted_devices[user_id] = []
            
            # Enforce device limit
            user_devices = self.trusted_devices[user_id]
            if len(user_devices) >= self.max_trusted_devices:
                # Remove oldest device
                oldest_device = min(user_devices, key=lambda d: d.created_at)
                user_devices.remove(oldest_device)
            
            user_devices.append(trusted_device)
            
            return device_id
            
        except Exception as e:
            logger.error(f"Failed to create trusted device for user {user_id}: {e}")
            return ""
    
    def _calculate_security_level(self, user_id: str) -> str:
        """Calculate security level based on 2FA configuration."""
        has_totp = user_id in self.user_secrets
        backup_codes = self.backup_codes.get(user_id, [])
        unused_backup_codes = [code for code in backup_codes if not code.is_used]
        trusted_devices = self.trusted_devices.get(user_id, [])
        active_devices = [
            device for device in trusted_devices
            if device.status in [DeviceStatus.VERIFIED, DeviceStatus.TRUSTED]
        ]
        
        if not has_totp:
            return "disabled"
        elif has_totp and len(unused_backup_codes) > 5 and len(active_devices) > 0:
            return "high"
        elif has_totp and len(unused_backup_codes) > 0:
            return "medium"
        else:
            return "basic"
    
    async def _log_security_event(self, event: Dict[str, Any]) -> None:
        """Log security event."""
        event["event_id"] = str(uuid.uuid4())
        self.security_events.append(event)
        
        # Keep only last 5000 events
        if len(self.security_events) > 5000:
            self.security_events = self.security_events[-2500:]
        
        # Integrate with security manager if available
        if self.security_manager:
            await self.security_manager.log_security_event(event)
    
    def _start_cleanup_tasks(self) -> None:
        """Start background cleanup tasks."""
        async def cleanup_expired_sessions():
            while True:
                try:
                    current_time = datetime.utcnow()
                    expired_sessions = []
                    
                    for session_id, session in self.two_factor_sessions.items():
                        if current_time > session.challenge_expires:
                            expired_sessions.append(session_id)
                    
                    for session_id in expired_sessions:
                        del self.two_factor_sessions[session_id]
                    
                    if expired_sessions:
                        logger.debug(f"Cleaned up {len(expired_sessions)} expired 2FA sessions")
                    
                    await asyncio.sleep(300)  # Run every 5 minutes
                    
                except Exception as e:
                    logger.error(f"2FA session cleanup error: {e}")
                    await asyncio.sleep(60)
        
        async def cleanup_expired_devices():
            while True:
                try:
                    current_time = datetime.utcnow()
                    
                    for user_id, devices in self.trusted_devices.items():
                        for device in devices:
                            if (device.expires_at and 
                                current_time > device.expires_at and 
                                device.status == DeviceStatus.TRUSTED):
                                device.status = DeviceStatus.REVOKED
                    
                    await asyncio.sleep(3600)  # Run every hour
                    
                except Exception as e:
                    logger.error(f"Trusted device cleanup error: {e}")
                    await asyncio.sleep(300)
        
        # Start cleanup tasks if event loop is available
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(cleanup_expired_sessions())
            loop.create_task(cleanup_expired_devices())
        except RuntimeError:
            logger.info("No event loop running, 2FA cleanup will be handled manually")
    
    async def get_two_factor_analytics(self) -> Dict[str, Any]:
        """Get comprehensive 2FA analytics."""
        try:
            total_users_with_2fa = len(self.user_secrets)
            total_trusted_devices = sum(len(devices) for devices in self.trusted_devices.values())
            total_backup_codes = sum(len(codes) for codes in self.backup_codes.values())
            
            # Active sessions
            current_time = datetime.utcnow()
            active_sessions = sum(
                1 for session in self.two_factor_sessions.values()
                if current_time <= session.challenge_expires and not session.completed
            )
            
            # Security event statistics
            event_counts = {}
            for event in self.security_events:
                event_type = event.get("event_type", "unknown")
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            return {
                "overview": {
                    "users_with_2fa": total_users_with_2fa,
                    "total_trusted_devices": total_trusted_devices,
                    "total_backup_codes": total_backup_codes,
                    "active_2fa_sessions": active_sessions
                },
                "security_events": {
                    "total": len(self.security_events),
                    "by_type": event_counts
                },
                "configuration": {
                    "totp_window": self.totp_window,
                    "backup_code_count": self.backup_code_count,
                    "trusted_device_duration_days": self.trusted_device_duration_days,
                    "max_trusted_devices": self.max_trusted_devices,
                    "require_device_verification": self.require_device_verification
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get 2FA analytics: {e}")
            return {"error": f"Failed to get 2FA analytics: {e}"}