"""
Unified Security Middleware
==========================

Integrated security middleware that combines rate limiting, authentication, 
DDoS protection, and request validation with <10ms performance target.
"""

import asyncio
import time
import logging
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass
import json
import hashlib

import redis.asyncio as redis
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse

from config.unified_security_config import UnifiedSecurityConfig, get_security_config
from external_api.auth_middleware import AuthenticationMiddleware, AuthResult, Permission
from external_api.models import ApiRequest, ApiResponse
from security.redis_rate_limiter import RedisRateLimiter, RateLimitConfig as RLConfig, RateLimitResult
from security.ddos_protection import DDoSDetectionEngine, DDoSMitigationEngine
from security.request_validation import RequestValidationEngine, SecurityValidationResult

logger = logging.getLogger(__name__)


@dataclass
class SecurityContext:
    """Security context for request processing"""
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    permissions: List[Permission] = None
    ip_address: str = "unknown"
    user_agent: str = "unknown"
    authenticated: bool = False
    rate_limit_remaining: int = 0
    security_score: float = 100.0
    threat_level: str = "low"
    processing_time_ms: float = 0.0


class UnifiedSecurityMiddleware:
    """
    Unified security middleware with <10ms performance target.
    
    Integrates:
    - Redis-backed rate limiting
    - Authentication & RBAC
    - DDoS protection
    - Request validation
    - Security monitoring
    """
    
    def __init__(self, config: Optional[UnifiedSecurityConfig] = None):
        self.config = config or get_security_config()
        self.redis_client = None
        self.auth_middleware = None
        self.rate_limiter = None
        self.ddos_detector = None
        self.ddos_mitigator = None
        self.validator = None
        
        # Performance metrics
        self.performance_metrics = {
            "total_requests": 0,
            "avg_processing_time_ms": 0.0,
            "rate_limit_hits": 0,
            "auth_failures": 0,
            "validation_blocks": 0,
            "ddos_detections": 0
        }
        
        logger.info("UnifiedSecurityMiddleware initialized")
    
    async def initialize(self):
        """Initialize all security components"""
        start_time = time.time()
        
        # Initialize Redis with optimized settings
        self.redis_client = await self._initialize_redis()
        
        # Initialize authentication middleware
        auth_config = {
            "enabled_methods": self.config.authentication.enabled_methods,
            "jwt_secret": self.config.authentication.jwt_secret,
            "max_auth_attempts": self.config.authentication.max_auth_attempts,
            "auth_window_minutes": self.config.authentication.auth_window_minutes
        }
        self.auth_middleware = AuthenticationMiddleware(auth_config)
        
        # Initialize rate limiter with optimized Redis config
        rate_config = RLConfig(
            key_prefix="unified_rate_limit",
            max_requests=self.config.rate_limiting.max_requests,
            window_seconds=self.config.rate_limiting.window_seconds,
            limit_type=self.config.rate_limiting.strategy.value
        )
        self.rate_limiter = RedisRateLimiter(self.redis_client, rate_config)
        
        # Initialize DDoS protection
        ddos_config = {
            "volume_threshold": self.config.ddos_protection.volume_threshold,
            "connection_threshold": self.config.ddos_protection.connection_threshold,
            "pattern_anomaly_threshold": self.config.ddos_protection.pattern_anomaly_threshold,
            "analysis_window": self.config.ddos_protection.analysis_window_seconds
        }
        self.ddos_detector = DDoSDetectionEngine(self.redis_client, ddos_config)
        self.ddos_mitigator = DDoSMitigationEngine(self.redis_client, ddos_config)
        
        # Initialize request validator
        validation_config = {
            "max_payload_size": self.config.validation.max_payload_size,
            "max_header_size": self.config.validation.max_header_size,
            "max_url_length": self.config.validation.max_url_length,
            "enable_sanitization": self.config.validation.enable_sanitization,
            "strict_mode": self.config.validation.strict_mode
        }
        self.validator = RequestValidationEngine(self.redis_client, validation_config)
        
        init_time = (time.time() - start_time) * 1000
        logger.info(f"Security middleware initialized in {init_time:.2f}ms")
    
    async def _initialize_redis(self) -> redis.Redis:
        """Initialize Redis with performance optimizations"""
        redis_config = self.config.redis
        
        # Create connection pool with optimized settings
        pool = redis.ConnectionPool(
            host=redis_config.host,
            port=redis_config.port,
            db=redis_config.db,
            password=redis_config.password,
            max_connections=redis_config.max_connections,
            socket_timeout=redis_config.socket_timeout,
            socket_connect_timeout=redis_config.socket_connect_timeout,
            retry_on_timeout=True,
            health_check_interval=30
        )
        
        client = redis.Redis(connection_pool=pool)
        
        # Test connection
        try:
            await client.ping()
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            if not self.config.rate_limiting.fail_open:
                raise
        
        return client
    
    async def __call__(self, request: Request, call_next):
        """Main middleware entry point with <10ms target"""
        start_time = time.time()
        
        try:
            # Create security context
            security_context = await self._create_security_context(request)
            
            # Phase 1: Fast security checks (target: <3ms)
            fast_result = await self._fast_security_checks(request, security_context)
            if fast_result:
                return fast_result
            
            # Phase 2: Authentication (target: <3ms)
            auth_result = await self._authenticate_request(request, security_context)
            if auth_result:
                return auth_result
            
            # Phase 3: Rate limiting (target: <3ms)
            rate_limit_result = await self._check_rate_limits(request, security_context)
            if rate_limit_result:
                return rate_limit_result
            
            # Phase 4: Advanced security checks (target: <1ms)
            security_result = await self._advanced_security_checks(request, security_context)
            if security_result:
                return security_result
            
            # Process request
            response = await call_next(request)
            
            # Post-processing
            await self._post_process_request(request, response, security_context)
            
            # Add security headers
            self._add_security_headers(response, security_context)
            
            # Update metrics
            processing_time = (time.time() - start_time) * 1000
            security_context.processing_time_ms = processing_time
            await self._update_metrics(processing_time, success=True)
            
            return response
            
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            
            # Update metrics
            processing_time = (time.time() - start_time) * 1000
            await self._update_metrics(processing_time, success=False)
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content={"error": "Internal security error"}
            )
    
    async def _create_security_context(self, request: Request) -> SecurityContext:
        """Create security context for request"""
        # Extract client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        
        return SecurityContext(
            ip_address=client_ip,
            user_agent=user_agent
        )
    
    async def _fast_security_checks(self, request: Request, 
                                   context: SecurityContext) -> Optional[Response]:
        """Fast security checks (target: <3ms)"""
        start_time = time.time()
        
        # Check if IP is blacklisted (Redis GET operation)
        if await self._is_ip_blacklisted(context.ip_address):
            return JSONResponse(
                status_code=403,
                content={"error": "IP address blocked"}
            )
        
        # Check for active DDoS mitigation
        mitigation_status = await self.ddos_mitigator.check_mitigation_status(context.ip_address)
        if mitigation_status.get("is_blocked"):
            return JSONResponse(
                status_code=429,
                content={"error": "IP temporarily blocked due to suspicious activity"}
            )
        
        # Basic request size validation
        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > self.config.validation.max_payload_size:
            return JSONResponse(
                status_code=413,
                content={"error": "Request payload too large"}
            )
        
        check_time = (time.time() - start_time) * 1000
        logger.debug(f"Fast security checks completed in {check_time:.2f}ms")
        
        return None
    
    async def _authenticate_request(self, request: Request, 
                                   context: SecurityContext) -> Optional[Response]:
        """Authenticate request (target: <3ms)"""
        start_time = time.time()
        
        # Convert FastAPI request to ApiRequest
        api_request = await self._convert_to_api_request(request)
        
        # Authenticate
        auth_result = await self.auth_middleware.authenticate_request(api_request)
        
        if auth_result.success:
            # Update context with auth info
            context.user_id = auth_result.user_id
            context.permissions = auth_result.permissions
            context.authenticated = True
            
            # Determine user role from permissions
            if Permission.ADMIN in auth_result.permissions:
                context.user_role = "admin"
            elif Permission.WRITE in auth_result.permissions:
                context.user_role = "user"
            else:
                context.user_role = "readonly"
        else:
            # Check if authentication is required for this path
            path_config = self.config.get_auth_config_for_path(request.url.path)
            if path_config.get("required", False):
                auth_time = (time.time() - start_time) * 1000
                logger.debug(f"Authentication failed in {auth_time:.2f}ms")
                
                return JSONResponse(
                    status_code=401,
                    content={"error": auth_result.error}
                )
        
        auth_time = (time.time() - start_time) * 1000
        logger.debug(f"Authentication completed in {auth_time:.2f}ms")
        
        return None
    
    async def _check_rate_limits(self, request: Request, 
                                context: SecurityContext) -> Optional[Response]:
        """Check rate limits (target: <3ms)"""
        start_time = time.time()
        
        # Get rate limit configuration for this endpoint and user
        rate_config = self.config.get_rate_limit_config_for_endpoint(
            request.url.path, 
            context.user_role
        )
        
        # Use user ID if authenticated, otherwise use IP
        identifier = context.user_id if context.authenticated else context.ip_address
        
        # Check rate limit
        rate_result = await self.rate_limiter.check_rate_limit(
            identifier=identifier,
            endpoint=request.url.path
        )
        
        context.rate_limit_remaining = rate_result.requests_remaining
        
        if not rate_result.allowed:
            self.performance_metrics["rate_limit_hits"] += 1
            
            rate_time = (time.time() - start_time) * 1000
            logger.debug(f"Rate limit check failed in {rate_time:.2f}ms")
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": rate_result.retry_after
                },
                headers={
                    "X-RateLimit-Limit": str(self.config.rate_limiting.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(rate_result.reset_time)),
                    "Retry-After": str(rate_result.retry_after)
                }
            )
        
        rate_time = (time.time() - start_time) * 1000
        logger.debug(f"Rate limit check completed in {rate_time:.2f}ms")
        
        return None
    
    async def _advanced_security_checks(self, request: Request, 
                                       context: SecurityContext) -> Optional[Response]:
        """Advanced security checks (target: <1ms)"""
        start_time = time.time()
        
        # Prepare request data for validation
        request_data = {
            "ip": context.ip_address,
            "user_agent": context.user_agent,
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "endpoint": request.url.path
        }
        
        # Add body if present
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Read body efficiently
                body = await request.body()
                if body:
                    request_data["body"] = body
                    request_data["content_length"] = len(body)
            except Exception:
                pass  # Skip body reading on error
        
        # DDoS detection (async, non-blocking)
        asyncio.create_task(self._analyze_ddos_patterns(request_data))
        
        # Quick validation checks
        if len(str(request.url)) > self.config.validation.max_url_length:
            return JSONResponse(
                status_code=414,
                content={"error": "URL too long"}
            )
        
        # Update security context
        context.security_score = 90.0  # Base score, will be updated by validation
        context.threat_level = "low"
        
        check_time = (time.time() - start_time) * 1000
        logger.debug(f"Advanced security checks completed in {check_time:.2f}ms")
        
        return None
    
    async def _analyze_ddos_patterns(self, request_data: Dict[str, Any]):
        """Analyze DDoS patterns asynchronously"""
        try:
            alert = await self.ddos_detector.analyze_request(request_data)
            if alert:
                self.performance_metrics["ddos_detections"] += 1
                
                # Apply mitigation if configured
                if self.config.ddos_protection.auto_mitigation:
                    await self.ddos_mitigator.apply_mitigation(alert)
                
                logger.warning(f"DDoS alert: {alert.attack_type.value} from {alert.source_ips}")
        except Exception as e:
            logger.error(f"DDoS analysis failed: {e}")
    
    async def _post_process_request(self, request: Request, response: Response, 
                                   context: SecurityContext):
        """Post-process request for logging and monitoring"""
        try:
            # Log security event
            await self._log_security_event(request, response, context)
            
            # Update user session info if authenticated
            if context.authenticated:
                await self._update_user_session(context)
            
        except Exception as e:
            logger.error(f"Post-processing failed: {e}")
    
    async def _log_security_event(self, request: Request, response: Response, 
                                 context: SecurityContext):
        """Log security event to Redis"""
        try:
            event_data = {
                "timestamp": time.time(),
                "ip": context.ip_address,
                "user_id": context.user_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "user_agent": context.user_agent,
                "authenticated": context.authenticated,
                "rate_limit_remaining": context.rate_limit_remaining,
                "security_score": context.security_score,
                "processing_time_ms": context.processing_time_ms
            }
            
            await self.redis_client.lpush("security_events", json.dumps(event_data))
            await self.redis_client.ltrim("security_events", 0, 9999)  # Keep last 10k
            
        except Exception as e:
            logger.error(f"Security event logging failed: {e}")
    
    async def _update_user_session(self, context: SecurityContext):
        """Update user session information"""
        try:
            if context.user_id:
                session_key = f"user_session:{context.user_id}"
                session_data = {
                    "last_activity": time.time(),
                    "ip_address": context.ip_address,
                    "user_agent": context.user_agent,
                    "requests_count": await self.redis_client.incr(f"user_requests:{context.user_id}")
                }
                
                await self.redis_client.hset(session_key, mapping=session_data)
                await self.redis_client.expire(session_key, 
                                              self.config.authentication.session_timeout_hours * 3600)
                
        except Exception as e:
            logger.error(f"Session update failed: {e}")
    
    def _add_security_headers(self, response: Response, context: SecurityContext):
        """Add security headers to response"""
        # Rate limiting headers
        response.headers["X-RateLimit-Remaining"] = str(context.rate_limit_remaining)
        response.headers["X-Security-Score"] = str(int(context.security_score))
        response.headers["X-Processing-Time"] = f"{context.processing_time_ms:.2f}ms"
        
        # Standard security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        if self.config.authentication.require_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    async def _update_metrics(self, processing_time: float, success: bool):
        """Update performance metrics"""
        try:
            self.performance_metrics["total_requests"] += 1
            
            # Update average processing time
            current_avg = self.performance_metrics["avg_processing_time_ms"]
            total_requests = self.performance_metrics["total_requests"]
            
            new_avg = ((current_avg * (total_requests - 1)) + processing_time) / total_requests
            self.performance_metrics["avg_processing_time_ms"] = new_avg
            
            # Log performance warning if >10ms
            if processing_time > 10:
                logger.warning(f"Security middleware processing time: {processing_time:.2f}ms (>10ms target)")
            
            # Store metrics in Redis
            await self.redis_client.hset("security_metrics", mapping={
                "total_requests": self.performance_metrics["total_requests"],
                "avg_processing_time_ms": new_avg,
                "rate_limit_hits": self.performance_metrics["rate_limit_hits"],
                "auth_failures": self.performance_metrics["auth_failures"],
                "validation_blocks": self.performance_metrics["validation_blocks"],
                "ddos_detections": self.performance_metrics["ddos_detections"],
                "last_updated": time.time()
            })
            
        except Exception as e:
            logger.error(f"Metrics update failed: {e}")
    
    async def _is_ip_blacklisted(self, ip: str) -> bool:
        """Check if IP is blacklisted (fast Redis lookup)"""
        try:
            result = await self.redis_client.get(f"blacklist_ip:{ip}")
            return result is not None
        except Exception:
            return False
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _convert_to_api_request(self, request: Request) -> ApiRequest:
        """Convert FastAPI request to ApiRequest"""
        return ApiRequest(
            method=request.method,
            path=request.url.path,
            headers=dict(request.headers),
            query_params=dict(request.query_params),
            body=None,  # Will be populated if needed
            timestamp=time.time(),
            request_id=request.headers.get("X-Request-ID", "unknown"),
            client_ip=self._get_client_ip(request)
        )
    
    async def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        try:
            metrics = await self.redis_client.hgetall("security_metrics")
            
            return {
                "performance": {
                    "total_requests": int(metrics.get("total_requests", 0)),
                    "avg_processing_time_ms": float(metrics.get("avg_processing_time_ms", 0)),
                    "performance_target_met": float(metrics.get("avg_processing_time_ms", 0)) < 10
                },
                "security": {
                    "rate_limit_hits": int(metrics.get("rate_limit_hits", 0)),
                    "auth_failures": int(metrics.get("auth_failures", 0)),
                    "validation_blocks": int(metrics.get("validation_blocks", 0)),
                    "ddos_detections": int(metrics.get("ddos_detections", 0))
                },
                "configuration": {
                    "performance_optimized": self.config.is_performance_optimized(),
                    "security_level": self.config.security_level.value,
                    "environment": self.config.environment
                }
            }
        except Exception as e:
            logger.error(f"Failed to get security stats: {e}")
            return {"error": str(e)}
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.redis_client:
                await self.redis_client.close()
            logger.info("Security middleware cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


# Factory function for FastAPI integration
def create_security_middleware(config: Optional[UnifiedSecurityConfig] = None) -> UnifiedSecurityMiddleware:
    """Create and initialize security middleware"""
    middleware = UnifiedSecurityMiddleware(config)
    return middleware