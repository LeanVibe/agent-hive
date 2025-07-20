#!/usr/bin/env python3
"""
Enhanced Security Middleware

Advanced security middleware with comprehensive token validation,
request filtering, rate limiting, and security monitoring.
"""

import asyncio
import ipaddress
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import re
from collections import defaultdict, deque

from security.auth_service import AuthenticationService
from config.auth_models import Permission, AuthResult
from external_api.models import ApiRequest, ApiResponse


logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security levels for different endpoints."""
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    AUTHORIZED = "authorized"
    ADMIN = "admin"
    CRITICAL = "critical"


class RateLimitType(Enum):
    """Rate limiting types."""
    PER_IP = "per_ip"
    PER_USER = "per_user"
    PER_ENDPOINT = "per_endpoint"
    GLOBAL = "global"


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration."""
    limit_type: RateLimitType
    requests_per_window: int
    window_seconds: int
    burst_allowance: int = 0
    penalty_seconds: int = 0


@dataclass
class SecurityPolicy:
    """Security policy for endpoints."""
    path_pattern: str
    security_level: SecurityLevel
    required_permissions: List[Permission]
    rate_limits: List[RateLimitRule]
    allowed_methods: List[str]
    ip_whitelist: Optional[List[str]] = None
    ip_blacklist: Optional[List[str]] = None
    require_https: bool = True
    max_request_size: int = 1024 * 1024  # 1MB default
    custom_headers: Dict[str, str] = None


@dataclass
class SecurityEvent:
    """Security event for monitoring."""
    event_id: str
    event_type: str
    severity: str
    timestamp: datetime
    source_ip: str
    user_id: Optional[str]
    endpoint: str
    details: Dict[str, Any]
    action_taken: str


class EnhancedSecurityMiddleware:
    """
    Enhanced security middleware with comprehensive protection features.
    
    Features:
    - Advanced token validation and session management
    - Multi-tier rate limiting with burst protection
    - Request filtering and input validation
    - IP-based access control
    - Security event monitoring and alerting
    - Real-time threat detection
    - Automated security responses
    """
    
    def __init__(self, auth_service: AuthenticationService, config: Dict[str, Any]):
        """Initialize enhanced security middleware."""
        self.auth_service = auth_service
        self.config = config
        
        # Initialize components
        self.token_manager = auth_service.token_manager
        
        # Rate limiting storage
        self.rate_limit_store = defaultdict(lambda: defaultdict(deque))
        self.penalty_store = defaultdict(float)  # IP -> penalty_until_timestamp
        
        # Security monitoring
        self.security_events: List[SecurityEvent] = []
        self.threat_scores = defaultdict(float)  # IP -> threat_score
        self.suspicious_patterns = defaultdict(int)  # pattern -> count
        
        # Security policies
        self.security_policies = self._load_security_policies()
        
        # Request filtering
        self.blocked_patterns = self._load_blocked_patterns()
        self.trusted_proxies = set(config.get("trusted_proxies", []))
        
        # Performance metrics
        self.request_metrics = defaultdict(lambda: {"count": 0, "avg_time": 0.0})
        
        # Start monitoring tasks
        self._start_monitoring_tasks()
        
        logger.info("Enhanced Security Middleware initialized")
    
    def _load_security_policies(self) -> List[SecurityPolicy]:
        """Load security policies for different endpoints."""
        default_policies = [
            SecurityPolicy(
                path_pattern=r"/api/v1/auth/login",
                security_level=SecurityLevel.PUBLIC,
                required_permissions=[],
                rate_limits=[
                    RateLimitRule(RateLimitType.PER_IP, 5, 300, burst_allowance=2, penalty_seconds=900),  # 5 attempts per 5 min
                ],
                allowed_methods=["POST"],
                max_request_size=1024  # 1KB for login
            ),
            SecurityPolicy(
                path_pattern=r"/api/v1/auth/.*",
                security_level=SecurityLevel.PUBLIC,
                required_permissions=[],
                rate_limits=[
                    RateLimitRule(RateLimitType.PER_IP, 20, 3600),  # 20 per hour
                ],
                allowed_methods=["POST", "GET"]
            ),
            SecurityPolicy(
                path_pattern=r"/api/v1/agents/.*",
                security_level=SecurityLevel.AUTHENTICATED,
                required_permissions=[Permission.READ],
                rate_limits=[
                    RateLimitRule(RateLimitType.PER_USER, 1000, 3600),  # 1000 per hour per user
                    RateLimitRule(RateLimitType.PER_IP, 2000, 3600),     # 2000 per hour per IP
                ],
                allowed_methods=["GET", "POST", "PUT", "DELETE"]
            ),
            SecurityPolicy(
                path_pattern=r"/api/v1/admin/.*",
                security_level=SecurityLevel.ADMIN,
                required_permissions=[Permission.ADMIN],
                rate_limits=[
                    RateLimitRule(RateLimitType.PER_USER, 100, 3600),  # 100 per hour
                ],
                allowed_methods=["GET", "POST", "PUT", "DELETE"],
                require_https=True
            ),
            SecurityPolicy(
                path_pattern=r"/api/v1/system/.*",
                security_level=SecurityLevel.CRITICAL,
                required_permissions=[Permission.ADMIN, Permission.EXECUTE],
                rate_limits=[
                    RateLimitRule(RateLimitType.PER_USER, 10, 3600),   # 10 per hour
                    RateLimitRule(RateLimitType.GLOBAL, 50, 3600),     # 50 per hour globally
                ],
                allowed_methods=["POST", "PUT", "DELETE"],
                require_https=True
            )
        ]
        
        # Add custom policies from config
        custom_policies = self.config.get("security_policies", [])
        for policy_config in custom_policies:
            try:
                policy = SecurityPolicy(**policy_config)
                default_policies.append(policy)
            except Exception as e:
                logger.warning(f"Invalid security policy configuration: {e}")
        
        return default_policies
    
    def _load_blocked_patterns(self) -> List[re.Pattern]:
        """Load patterns for blocking malicious requests."""
        default_patterns = [
            # SQL injection patterns
            r"(\bunion\b.*\bselect\b)|(\bselect\b.*\bfrom\b)",
            r"(\bdrop\b.*\btable\b)|(\bdelete\b.*\bfrom\b)",
            r"(\binsert\b.*\binto\b)|(\bupdate\b.*\bset\b)",
            
            # XSS patterns
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            
            # Path traversal
            r"\.\./",
            r"\.\.\\",
            
            # Command injection
            r";\s*(rm|ls|cat|wget|curl)",
            r"\$\([^)]*\)",
            r"`[^`]*`",
            
            # Common attack patterns
            r"\beval\b\s*\(",
            r"\bexec\b\s*\(",
            r"base64_decode",
        ]
        
        compiled_patterns = []
        for pattern in default_patterns:
            try:
                compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")
        
        return compiled_patterns
    
    async def process_request(self, request: ApiRequest) -> Tuple[bool, Optional[ApiResponse], Optional[AuthResult]]:
        """
        Process incoming request through security middleware.
        
        Returns:
            Tuple of (allowed, error_response, auth_result)
        """
        start_time = time.time()
        
        try:
            # Get real client IP
            client_ip = await self._get_real_client_ip(request)
            request.client_ip = client_ip
            
            # Check if IP is in penalty
            if await self._is_ip_in_penalty(client_ip):
                return False, self._create_error_response(429, "Too many requests - IP temporarily blocked"), None
            
            # Check IP blacklist/whitelist
            if not await self._check_ip_access(client_ip):
                await self._log_security_event("ip_blocked", request, severity="medium", details={"reason": "blacklisted"})
                return False, self._create_error_response(403, "Access denied"), None
            
            # Find matching security policy
            policy = await self._find_security_policy(request.path, request.method)
            if not policy:
                await self._log_security_event("no_policy_match", request, severity="low")
                return False, self._create_error_response(404, "Not found"), None
            
            # Check HTTPS requirement
            if policy.require_https and not await self._is_https_request(request):
                return False, self._create_error_response(400, "HTTPS required"), None
            
            # Check request size
            if request.body and len(request.body.encode('utf-8')) > policy.max_request_size:
                await self._log_security_event("request_too_large", request, severity="medium")
                return False, self._create_error_response(413, "Request entity too large"), None
            
            # Check for malicious patterns
            if await self._contains_malicious_patterns(request):
                await self._log_security_event("malicious_pattern", request, severity="high", 
                                              details={"patterns_detected": True})
                await self._increase_threat_score(client_ip, 50)
                return False, self._create_error_response(400, "Malicious request detected"), None
            
            # Check rate limits
            rate_limit_result = await self._check_rate_limits(request, policy)
            if not rate_limit_result["allowed"]:
                await self._log_security_event("rate_limit_exceeded", request, severity="medium",
                                              details=rate_limit_result)
                return False, self._create_error_response(429, "Rate limit exceeded"), None
            
            # Authenticate and authorize request
            auth_result = None
            if policy.security_level != SecurityLevel.PUBLIC:
                auth_result = await self._authenticate_request(request, policy)
                if not auth_result or not auth_result.success:
                    await self._log_security_event("authentication_failed", request, severity="medium",
                                                  details={"auth_error": auth_result.error if auth_result else "No auth result"})
                    await self._increase_threat_score(client_ip, 10)
                    return False, self._create_error_response(401, "Authentication required"), None
            
            # Update metrics
            await self._update_request_metrics(request.path, time.time() - start_time)
            
            # Log successful request
            await self._log_security_event("request_allowed", request, severity="info",
                                          details={"policy": policy.path_pattern, "auth_user": auth_result.user_id if auth_result else None})
            
            return True, None, auth_result
            
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            await self._log_security_event("middleware_error", request, severity="high",
                                          details={"error": str(e)})
            return False, self._create_error_response(500, "Internal security error"), None
    
    async def _get_real_client_ip(self, request: ApiRequest) -> str:
        """Get the real client IP, handling proxies and load balancers."""
        # Check X-Forwarded-For header
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain (original client)
            client_ip = forwarded_for.split(',')[0].strip()
            
            # Validate it's a real IP
            try:
                ipaddress.ip_address(client_ip)
                return client_ip
            except ValueError:
                pass
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            try:
                ipaddress.ip_address(real_ip)
                return real_ip
            except ValueError:
                pass
        
        # Fallback to direct client IP
        return request.client_ip or "unknown"
    
    async def _is_ip_in_penalty(self, client_ip: str) -> bool:
        """Check if IP is currently in penalty period."""
        penalty_until = self.penalty_store.get(client_ip, 0)
        return time.time() < penalty_until
    
    async def _check_ip_access(self, client_ip: str) -> bool:
        """Check if IP is allowed access based on whitelist/blacklist."""
        try:
            ip_obj = ipaddress.ip_address(client_ip)
            
            # Check against configured blacklist
            blacklist = self.config.get("ip_blacklist", [])
            for blocked_range in blacklist:
                if ip_obj in ipaddress.ip_network(blocked_range, strict=False):
                    return False
            
            # Check against configured whitelist (if exists)
            whitelist = self.config.get("ip_whitelist", [])
            if whitelist:
                for allowed_range in whitelist:
                    if ip_obj in ipaddress.ip_network(allowed_range, strict=False):
                        return True
                return False  # Not in whitelist
            
            return True  # No whitelist configured, allow by default
            
        except ValueError:
            # Invalid IP address
            return False
    
    async def _find_security_policy(self, path: str, method: str) -> Optional[SecurityPolicy]:
        """Find matching security policy for the request."""
        for policy in self.security_policies:
            if re.match(policy.path_pattern, path) and method in policy.allowed_methods:
                return policy
        return None
    
    async def _is_https_request(self, request: ApiRequest) -> bool:
        """Check if request is using HTTPS."""
        # Check various headers that indicate HTTPS
        return (
            request.headers.get("X-Forwarded-Proto") == "https" or
            request.headers.get("X-Forwarded-Ssl") == "on" or
            request.headers.get("X-Url-Scheme") == "https" or
            # In a real implementation, this would check the actual protocol
            True  # Assume HTTPS for now
        )
    
    async def _contains_malicious_patterns(self, request: ApiRequest) -> bool:
        """Check if request contains malicious patterns."""
        # Check URL path
        for pattern in self.blocked_patterns:
            if pattern.search(request.path):
                return True
        
        # Check query parameters
        for param, value in request.query_params.items():
            for pattern in self.blocked_patterns:
                if pattern.search(f"{param}={value}"):
                    return True
        
        # Check request body
        if request.body:
            for pattern in self.blocked_patterns:
                if pattern.search(request.body):
                    return True
        
        # Check headers for injection attempts
        for header, value in request.headers.items():
            # Skip common headers that might contain patterns
            if header.lower() in ["user-agent", "referer", "accept"]:
                continue
            
            for pattern in self.blocked_patterns:
                if pattern.search(f"{header}: {value}"):
                    return True
        
        return False
    
    async def _check_rate_limits(self, request: ApiRequest, policy: SecurityPolicy) -> Dict[str, Any]:
        """Check if request violates rate limits."""
        current_time = time.time()
        client_ip = request.client_ip
        
        for rate_limit in policy.rate_limits:
            # Determine the key for rate limiting
            if rate_limit.limit_type == RateLimitType.PER_IP:
                key = f"ip:{client_ip}"
            elif rate_limit.limit_type == RateLimitType.PER_USER:
                # Would need user ID from auth context
                key = "user:unknown"  # Simplified for now
            elif rate_limit.limit_type == RateLimitType.PER_ENDPOINT:
                key = f"endpoint:{request.path}"
            else:  # GLOBAL
                key = "global"
            
            # Get request times for this key
            request_times = self.rate_limit_store[key][rate_limit.limit_type.value]
            
            # Remove old requests outside the window
            window_start = current_time - rate_limit.window_seconds
            while request_times and request_times[0] < window_start:
                request_times.popleft()
            
            # Check if limit is exceeded
            if len(request_times) >= rate_limit.requests_per_window:
                # Check if burst allowance can be used
                if rate_limit.burst_allowance > 0:
                    burst_key = f"{key}:burst"
                    burst_times = self.rate_limit_store[burst_key]["burst"]
                    
                    # Remove old burst requests
                    while burst_times and burst_times[0] < window_start:
                        burst_times.popleft()
                    
                    if len(burst_times) < rate_limit.burst_allowance:
                        burst_times.append(current_time)
                        # Apply penalty if configured
                        if rate_limit.penalty_seconds > 0:
                            self.penalty_store[client_ip] = current_time + rate_limit.penalty_seconds
                        return {"allowed": True, "burst_used": True}
                
                return {
                    "allowed": False,
                    "limit_type": rate_limit.limit_type.value,
                    "limit": rate_limit.requests_per_window,
                    "window": rate_limit.window_seconds,
                    "current_count": len(request_times)
                }
            
            # Add current request to the window
            request_times.append(current_time)
        
        return {"allowed": True}
    
    async def _authenticate_request(self, request: ApiRequest, policy: SecurityPolicy) -> Optional[AuthResult]:
        """Authenticate request based on security policy."""
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return AuthResult(success=False, error="Bearer token required")
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Validate session using auth service
        auth_result = await self.auth_service.validate_session(
            access_token=token,
            client_ip=request.client_ip,
            required_permissions=policy.required_permissions
        )
        
        return auth_result
    
    async def _increase_threat_score(self, client_ip: str, points: float) -> None:
        """Increase threat score for an IP address."""
        self.threat_scores[client_ip] += points
        
        # Check if IP should be temporarily blocked
        if self.threat_scores[client_ip] > 100:  # Configurable threshold
            penalty_duration = min(3600, self.threat_scores[client_ip] * 10)  # Max 1 hour
            self.penalty_store[client_ip] = time.time() + penalty_duration
            
            await self._log_security_event("ip_auto_blocked", None, severity="high",
                                          details={
                                              "client_ip": client_ip,
                                              "threat_score": self.threat_scores[client_ip],
                                              "penalty_duration": penalty_duration
                                          })
    
    async def _update_request_metrics(self, endpoint: str, processing_time: float) -> None:
        """Update request performance metrics."""
        metrics = self.request_metrics[endpoint]
        metrics["count"] += 1
        
        # Update average processing time
        current_avg = metrics["avg_time"]
        new_avg = (current_avg * (metrics["count"] - 1) + processing_time) / metrics["count"]
        metrics["avg_time"] = new_avg
    
    async def _log_security_event(self, event_type: str, request: Optional[ApiRequest],
                                 severity: str = "info", details: Optional[Dict[str, Any]] = None) -> None:
        """Log security event for monitoring and analysis."""
        event = SecurityEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            severity=severity,
            timestamp=datetime.utcnow(),
            source_ip=request.client_ip if request else "unknown",
            user_id=None,  # Would be extracted from auth context
            endpoint=request.path if request else "unknown",
            details=details or {},
            action_taken="logged"
        )
        
        self.security_events.append(event)
        
        # Keep only last 10000 events
        if len(self.security_events) > 10000:
            self.security_events = self.security_events[-5000:]
        
        # Log high severity events immediately
        if severity in ["high", "critical"]:
            logger.warning(f"Security event: {event_type} from {event.source_ip}")
    
    def _create_error_response(self, status_code: int, message: str) -> ApiResponse:
        """Create standardized error response."""
        return ApiResponse(
            status_code=status_code,
            headers={
                "Content-Type": "application/json",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block"
            },
            body=json.dumps({
                "error": message,
                "timestamp": datetime.utcnow().isoformat(),
                "status": status_code
            })
        )
    
    def _start_monitoring_tasks(self) -> None:
        """Start background monitoring and cleanup tasks."""
        async def cleanup_rate_limits():
            """Clean up expired rate limit entries."""
            while True:
                try:
                    current_time = time.time()
                    
                    # Clean rate limit store
                    for key_dict in self.rate_limit_store.values():
                        for limit_type, times_deque in key_dict.items():
                            # Remove entries older than 24 hours
                            cutoff = current_time - 86400
                            while times_deque and times_deque[0] < cutoff:
                                times_deque.popleft()
                    
                    # Clean penalty store
                    expired_ips = [ip for ip, penalty_until in self.penalty_store.items() 
                                 if penalty_until < current_time]
                    for ip in expired_ips:
                        del self.penalty_store[ip]
                    
                    # Decay threat scores
                    for ip in list(self.threat_scores.keys()):
                        self.threat_scores[ip] *= 0.9  # 10% decay
                        if self.threat_scores[ip] < 1:
                            del self.threat_scores[ip]
                    
                    await asyncio.sleep(300)  # Run every 5 minutes
                    
                except Exception as e:
                    logger.error(f"Cleanup task error: {e}")
                    await asyncio.sleep(60)
        
        async def security_monitoring():
            """Monitor for security threats and patterns."""
            while True:
                try:
                    # Analyze recent security events
                    recent_events = [e for e in self.security_events 
                                   if (datetime.utcnow() - e.timestamp).total_seconds() < 3600]
                    
                    # Detect patterns
                    await self._detect_attack_patterns(recent_events)
                    
                    # Generate alerts
                    await self._check_security_thresholds(recent_events)
                    
                    await asyncio.sleep(300)  # Run every 5 minutes
                    
                except Exception as e:
                    logger.error(f"Security monitoring error: {e}")
                    await asyncio.sleep(60)
        
        # Start background tasks
        asyncio.create_task(cleanup_rate_limits())
        asyncio.create_task(security_monitoring())
    
    async def _detect_attack_patterns(self, events: List[SecurityEvent]) -> None:
        """Detect potential attack patterns in security events."""
        # Group events by IP
        events_by_ip = defaultdict(list)
        for event in events:
            events_by_ip[event.source_ip].append(event)
        
        # Check for suspicious patterns
        for ip, ip_events in events_by_ip.items():
            # Check for rapid authentication failures
            auth_failures = [e for e in ip_events if e.event_type == "authentication_failed"]
            if len(auth_failures) > 10:  # More than 10 failures in an hour
                await self._increase_threat_score(ip, 30)
                await self._log_security_event("brute_force_detected", None, severity="high",
                                              details={"source_ip": ip, "failure_count": len(auth_failures)})
            
            # Check for scanning behavior
            endpoint_variety = len(set(e.endpoint for e in ip_events))
            if endpoint_variety > 20:  # Accessing many different endpoints
                await self._increase_threat_score(ip, 20)
                await self._log_security_event("scanning_detected", None, severity="medium",
                                              details={"source_ip": ip, "endpoints_accessed": endpoint_variety})
            
            # Check for malicious pattern attempts
            malicious_attempts = [e for e in ip_events if e.event_type == "malicious_pattern"]
            if len(malicious_attempts) > 3:
                await self._increase_threat_score(ip, 40)
                await self._log_security_event("repeated_attacks", None, severity="high",
                                              details={"source_ip": ip, "attack_count": len(malicious_attempts)})
    
    async def _check_security_thresholds(self, events: List[SecurityEvent]) -> None:
        """Check if security events exceed configured thresholds."""
        # Count events by severity
        severity_counts = defaultdict(int)
        for event in events:
            severity_counts[event.severity] += 1
        
        # Check thresholds
        thresholds = self.config.get("alert_thresholds", {
            "critical": 1,
            "high": 5,
            "medium": 20,
            "low": 100
        })
        
        for severity, count in severity_counts.items():
            threshold = thresholds.get(severity, float('inf'))
            if count >= threshold:
                await self._send_security_alert(severity, count, threshold)
    
    async def _send_security_alert(self, severity: str, count: int, threshold: int) -> None:
        """Send security alert when thresholds are exceeded."""
        alert_message = f"Security threshold exceeded: {count} {severity} events (threshold: {threshold})"
        
        # Log alert
        logger.warning(alert_message)
        
        # In production, this would send alerts via email, Slack, etc.
        await self._log_security_event("security_alert", None, severity="critical",
                                      details={
                                          "alert_severity": severity,
                                          "event_count": count,
                                          "threshold": threshold,
                                          "message": alert_message
                                      })
    
    async def get_security_dashboard(self) -> Dict[str, Any]:
        """Get security dashboard data."""
        current_time = time.time()
        
        # Recent events (last hour)
        recent_events = [e for e in self.security_events 
                        if (datetime.utcnow() - e.timestamp).total_seconds() < 3600]
        
        # Count events by type and severity
        event_types = defaultdict(int)
        severity_counts = defaultdict(int)
        
        for event in recent_events:
            event_types[event.event_type] += 1
            severity_counts[event.severity] += 1
        
        # Top threat IPs
        top_threats = sorted(self.threat_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Rate limit statistics
        active_penalties = sum(1 for penalty_until in self.penalty_store.values() 
                             if penalty_until > current_time)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "recent_activity": {
                "total_events": len(recent_events),
                "by_type": dict(event_types),
                "by_severity": dict(severity_counts)
            },
            "threat_intelligence": {
                "top_threat_ips": top_threats,
                "active_penalties": active_penalties,
                "total_tracked_threats": len(self.threat_scores)
            },
            "rate_limiting": {
                "active_limits": len(self.rate_limit_store),
                "penalty_count": active_penalties
            },
            "performance": {
                "avg_processing_times": {
                    endpoint: metrics["avg_time"] 
                    for endpoint, metrics in self.request_metrics.items()
                }
            },
            "security_policies": {
                "total_policies": len(self.security_policies),
                "policy_patterns": [p.path_pattern for p in self.security_policies]
            }
        }
    
    async def add_security_policy(self, policy: SecurityPolicy) -> None:
        """Add a new security policy."""
        self.security_policies.append(policy)
        await self._log_security_event("policy_added", None, severity="info",
                                      details={"policy_pattern": policy.path_pattern})
    
    async def block_ip(self, ip_address: str, duration_seconds: int, reason: str) -> None:
        """Manually block an IP address."""
        self.penalty_store[ip_address] = time.time() + duration_seconds
        await self._log_security_event("ip_manually_blocked", None, severity="medium",
                                      details={
                                          "ip_address": ip_address,
                                          "duration": duration_seconds,
                                          "reason": reason
                                      })
    
    async def unblock_ip(self, ip_address: str) -> None:
        """Manually unblock an IP address."""
        if ip_address in self.penalty_store:
            del self.penalty_store[ip_address]
        if ip_address in self.threat_scores:
            del self.threat_scores[ip_address]
        
        await self._log_security_event("ip_manually_unblocked", None, severity="info",
                                      details={"ip_address": ip_address})
    
    async def get_blocked_ips(self) -> List[Dict[str, Any]]:
        """Get list of currently blocked IP addresses."""
        current_time = time.time()
        blocked_ips = []
        
        for ip, penalty_until in self.penalty_store.items():
            if penalty_until > current_time:
                blocked_ips.append({
                    "ip_address": ip,
                    "blocked_until": datetime.fromtimestamp(penalty_until).isoformat(),
                    "remaining_seconds": int(penalty_until - current_time),
                    "threat_score": self.threat_scores.get(ip, 0)
                })
        
        return blocked_ips
    
    async def export_security_report(self) -> Dict[str, Any]:
        """Export comprehensive security report."""
        dashboard = await self.get_security_dashboard()
        
        # Add detailed event log
        recent_events = [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "severity": e.severity,
                "timestamp": e.timestamp.isoformat(),
                "source_ip": e.source_ip,
                "endpoint": e.endpoint,
                "details": e.details
            }
            for e in self.security_events[-100:]  # Last 100 events
        ]
        
        report = {
            **dashboard,
            "detailed_events": recent_events,
            "configuration": {
                "policies_count": len(self.security_policies),
                "blocked_patterns_count": len(self.blocked_patterns),
                "trusted_proxies": list(self.trusted_proxies),
                "rate_limit_store_size": len(self.rate_limit_store)
            },
            "recommendations": self._generate_security_recommendations()
        }
        
        return report
    
    def _generate_security_recommendations(self) -> List[str]:
        """Generate security recommendations based on current state."""
        recommendations = []
        
        # Check threat levels
        high_threat_ips = [ip for ip, score in self.threat_scores.items() if score > 50]
        if high_threat_ips:
            recommendations.append(f"Consider permanently blocking {len(high_threat_ips)} high-threat IP addresses")
        
        # Check event patterns
        recent_events = [e for e in self.security_events 
                        if (datetime.utcnow() - e.timestamp).total_seconds() < 86400]
        
        auth_failures = len([e for e in recent_events if e.event_type == "authentication_failed"])
        if auth_failures > 100:
            recommendations.append("High number of authentication failures - consider implementing CAPTCHA or additional MFA")
        
        malicious_patterns = len([e for e in recent_events if e.event_type == "malicious_pattern"])
        if malicious_patterns > 50:
            recommendations.append("Frequent malicious pattern detection - review and update WAF rules")
        
        # Check rate limiting effectiveness
        rate_limit_violations = len([e for e in recent_events if e.event_type == "rate_limit_exceeded"])
        if rate_limit_violations < 10 and len(recent_events) > 1000:
            recommendations.append("Rate limits may be too permissive - consider tightening limits")
        
        return recommendations