#!/usr/bin/env python3
"""
Rate Limit Enforcement Middleware for API Gateway

Integrates the advanced rate limiting system with the API Gateway to provide
comprehensive protection against abuse while maintaining optimal performance.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Tuple
import json
import uuid

from .models import ApiRequest, ApiResponse
from security.rate_limiter import RateLimiter, RateLimitStatus, RateLimitConfig, RateLimitScope, RateLimitStrategy
from config.auth_models import Permission


logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Rate limiting middleware for API Gateway integration.
    
    Features:
    - Seamless integration with API Gateway request processing
    - Context-aware rate limiting based on user, endpoint, IP, and roles
    - Configurable rate limit headers for client information
    - Monitoring and alerting integration
    - Performance optimized with minimal request overhead
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize rate limit middleware."""
        self.config = config or self._get_default_config()
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(self.config.get("rate_limiter", {}))
        
        # Middleware configuration
        self.enabled = self.config.get("enabled", True)
        self.bypass_patterns = self.config.get("bypass_patterns", [])
        self.custom_error_messages = self.config.get("custom_error_messages", {})
        self.include_headers = self.config.get("include_headers", True)
        self.log_violations = self.config.get("log_violations", True)
        
        # Performance tracking
        self.processed_requests = 0
        self.blocked_requests = 0
        self.bypass_count = 0
        self.processing_times = []
        
        # Load custom rate limit rules from config
        self._load_custom_rules()
        
        # Setup monitoring
        if self.config.get("enable_monitoring", True):
            self._setup_monitoring()
        
        logger.info("Rate Limit Middleware initialized and integrated with API Gateway")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default middleware configuration."""
        return {
            "enabled": True,
            "include_headers": True,
            "log_violations": True,
            "enable_monitoring": True,
            "bypass_patterns": [
                "/health",
                "/metrics",
                "/favicon.ico",
                "*.css",
                "*.js",
                "*.png",
                "*.jpg"
            ],
            "custom_error_messages": {
                "default": "Rate limit exceeded. Please try again later.",
                "global_protection": "System is under high load. Please try again later.",
                "admin_endpoint_protection": "Administrative endpoint rate limit exceeded.",
                "per_user_standard": "User rate limit exceeded. Please reduce request frequency."
            },
            "rate_limiter": {
                "performance_target_ms": 3.0,
                "cleanup_interval_seconds": 600,
                "max_violations_stored": 5000
            },
            "role_based_limits": {
                "SuperAdmin": {
                    "requests_per_minute": 1000,
                    "burst_capacity": 1500
                },
                "Admin": {
                    "requests_per_minute": 500,
                    "burst_capacity": 750
                },
                "User": {
                    "requests_per_minute": 100,
                    "burst_capacity": 150
                },
                "Guest": {
                    "requests_per_minute": 10,
                    "burst_capacity": 15
                }
            },
            "endpoint_specific_limits": {
                "/api/v1/auth/login": {
                    "requests_per_minute": 5,
                    "window_seconds": 300  # 5 requests per 5 minutes
                },
                "/api/v1/admin/*": {
                    "requests_per_minute": 20,
                    "window_seconds": 60
                },
                "/api/v1/agents/create": {
                    "requests_per_minute": 10,
                    "window_seconds": 60
                }
            }
        }
    
    def _load_custom_rules(self) -> None:
        """Load custom rate limiting rules from configuration."""
        # Load role-based limits
        role_limits = self.config.get("role_based_limits", {})
        for role, limits in role_limits.items():
            rule = RateLimitConfig(
                name=f"role_limit_{role.lower()}",
                scope=RateLimitScope.PER_ROLE,
                strategy=RateLimitStrategy.TOKEN_BUCKET,
                requests_per_window=limits["requests_per_minute"],
                window_seconds=60,
                burst_capacity=limits.get("burst_capacity"),
                refill_rate=limits["requests_per_minute"] / 60.0,
                priority=15,
                metadata={"role": role}
            )
            self.rate_limiter.add_rule(rule)
        
        # Load endpoint-specific limits
        endpoint_limits = self.config.get("endpoint_specific_limits", {})
        for endpoint, limits in endpoint_limits.items():
            rule = RateLimitConfig(
                name=f"endpoint_limit_{hash(endpoint)}",
                scope=RateLimitScope.PER_ENDPOINT,
                strategy=RateLimitStrategy.SLIDING_WINDOW,
                requests_per_window=limits["requests_per_minute"],
                window_seconds=limits.get("window_seconds", 60),
                target_pattern=endpoint,
                priority=25,
                metadata={"endpoint_pattern": endpoint}
            )
            self.rate_limiter.add_rule(rule)
    
    async def process_request(self, request: ApiRequest, next_handler: Callable) -> ApiResponse:
        """
        Process request through rate limiting middleware.
        
        Args:
            request: Incoming API request
            next_handler: Next middleware or handler in chain
            
        Returns:
            API response with rate limiting applied
        """
        start_time = time.time()
        
        try:
            self.processed_requests += 1
            
            # Check if middleware is enabled
            if not self.enabled:
                return await next_handler(request)
            
            # Check bypass patterns
            if self._should_bypass(request):
                self.bypass_count += 1
                return await next_handler(request)
            
            # Extract request context for rate limiting
            context = await self._extract_request_context(request)
            
            # Check rate limits
            rate_limit_status = await self.rate_limiter.check_rate_limit(context)
            
            # Record processing time
            processing_time = (time.time() - start_time) * 1000
            self.processing_times.append(processing_time)
            
            # Keep only recent processing times
            if len(self.processing_times) > 1000:
                self.processing_times = self.processing_times[-500:]
            
            if not rate_limit_status.allowed:
                # Rate limit exceeded
                self.blocked_requests += 1
                
                if self.log_violations and rate_limit_status.violation:
                    self._log_rate_limit_violation(request, rate_limit_status)
                
                return self._create_rate_limit_error_response(request, rate_limit_status)
            
            # Rate limit passed - proceed with request
            response = await next_handler(request)
            
            # Add rate limit headers if enabled
            if self.include_headers:
                self._add_rate_limit_headers(response, rate_limit_status)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            # Fail open - allow request to proceed
            return await next_handler(request)
    
    async def _extract_request_context(self, request: ApiRequest) -> Dict[str, Any]:
        """Extract context information for rate limiting."""
        context = {
            "endpoint": request.path,
            "method": request.method,
            "client_ip": request.client_ip,
            "user_agent": request.headers.get("User-Agent", "unknown"),
            "timestamp": datetime.utcnow()
        }
        
        # Extract user information if available
        user_id = request.headers.get("X-User-ID")
        if user_id:
            context["user_id"] = user_id
        
        # Extract user roles if available
        user_roles = request.headers.get("X-User-Roles", "")
        if user_roles:
            context["user_roles"] = [role.strip() for role in user_roles.split(",") if role.strip()]
        
        # Extract additional context from headers
        if "X-API-Key" in request.headers:
            context["api_key"] = request.headers["X-API-Key"]
        
        if "X-Client-Type" in request.headers:
            context["client_type"] = request.headers["X-Client-Type"]
        
        return context
    
    def _should_bypass(self, request: ApiRequest) -> bool:
        """Check if request should bypass rate limiting."""
        import fnmatch
        
        for pattern in self.bypass_patterns:
            if fnmatch.fnmatch(request.path, pattern):
                return True
        
        return False
    
    def _log_rate_limit_violation(self, request: ApiRequest, status: RateLimitStatus) -> None:
        """Log rate limit violation for monitoring."""
        violation_data = {
            "violation_id": status.violation.violation_id if status.violation else str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "request": {
                "method": request.method,
                "path": request.path,
                "client_ip": request.client_ip,
                "user_agent": request.headers.get("User-Agent", "unknown"),
                "user_id": request.headers.get("X-User-ID"),
                "user_roles": request.headers.get("X-User-Roles")
            },
            "rate_limit": {
                "rule_name": status.metadata.get("rule_name"),
                "remaining": status.remaining,
                "retry_after": status.retry_after
            }
        }
        
        logger.warning(f"Rate limit violation: {json.dumps(violation_data, indent=2)}")
        
        # Send to monitoring system if configured
        self._send_to_monitoring(violation_data)
    
    def _create_rate_limit_error_response(self, request: ApiRequest, status: RateLimitStatus) -> ApiResponse:
        """Create error response for rate limit exceeded."""
        rule_name = status.metadata.get("rule_name", "default")
        error_message = self.custom_error_messages.get(rule_name, self.custom_error_messages.get("default"))
        
        error_body = {
            "error": "rate_limit_exceeded",
            "message": error_message,
            "details": {
                "limit_remaining": status.remaining,
                "reset_time": status.reset_time.isoformat(),
                "retry_after_seconds": status.retry_after
            },
            "request_id": request.request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        headers = {"Content-Type": "application/json"}
        
        # Add rate limit headers
        if self.include_headers:
            rate_limit_headers = self.rate_limiter.get_rate_limit_headers(status)
            headers.update(rate_limit_headers)
        
        return ApiResponse(
            status_code=429,  # Too Many Requests
            headers=headers,
            body=error_body,
            timestamp=datetime.utcnow(),
            processing_time=0.0,
            request_id=request.request_id
        )
    
    def _add_rate_limit_headers(self, response: ApiResponse, status: RateLimitStatus) -> None:
        """Add rate limit headers to successful response."""
        rate_limit_headers = self.rate_limiter.get_rate_limit_headers(status)
        response.headers.update(rate_limit_headers)
    
    def _setup_monitoring(self) -> None:
        """Setup monitoring and alerting callbacks."""
        def violation_alert_callback(violation):
            """Handle rate limit violation alerts."""
            alert_data = {
                "alert_type": "rate_limit_violation",
                "severity": violation.severity,
                "rule_name": violation.rule_name,
                "violation_key": violation.key,
                "timestamp": violation.violated_at.isoformat(),
                "client_info": violation.client_info,
                "requests_count": violation.requests_count,
                "window_limit": violation.window_limit
            }
            
            logger.error(f"Rate limit violation alert: {json.dumps(alert_data, indent=2)}")
            
            # Send high severity violations to external monitoring
            if violation.severity == "high":
                self._send_critical_alert(alert_data)
        
        self.rate_limiter.add_alert_callback(violation_alert_callback)
    
    def _send_to_monitoring(self, data: Dict[str, Any]) -> None:
        """Send data to monitoring system."""
        # In production, this would integrate with monitoring systems
        # like Prometheus, DataDog, New Relic, etc.
        pass
    
    def _send_critical_alert(self, alert_data: Dict[str, Any]) -> None:
        """Send critical alert to external systems."""
        # In production, this would integrate with alerting systems
        # like PagerDuty, Slack, email notifications, etc.
        pass
    
    async def get_middleware_stats(self) -> Dict[str, Any]:
        """Get middleware performance and usage statistics."""
        avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        
        rate_limiter_stats = self.rate_limiter.get_rate_limit_stats()
        
        return {
            "middleware": {
                "enabled": self.enabled,
                "processed_requests": self.processed_requests,
                "blocked_requests": self.blocked_requests,
                "bypass_count": self.bypass_count,
                "block_rate_percent": (self.blocked_requests / max(1, self.processed_requests)) * 100,
                "bypass_rate_percent": (self.bypass_count / max(1, self.processed_requests)) * 100,
                "avg_processing_time_ms": avg_processing_time,
                "max_processing_time_ms": max(self.processing_times) if self.processing_times else 0,
                "performance_target_met": avg_processing_time <= self.config.get("rate_limiter", {}).get("performance_target_ms", 3.0)
            },
            "rate_limiter": rate_limiter_stats,
            "configuration": {
                "bypass_patterns": self.bypass_patterns,
                "include_headers": self.include_headers,
                "log_violations": self.log_violations,
                "custom_rules_count": len(self.config.get("role_based_limits", {})) + len(self.config.get("endpoint_specific_limits", {}))
            }
        }
    
    async def update_rate_limits(self, updates: Dict[str, Any]) -> bool:
        """Update rate limiting configuration dynamically."""
        try:
            # Update role-based limits
            if "role_based_limits" in updates:
                for role, limits in updates["role_based_limits"].items():
                    rule_name = f"role_limit_{role.lower()}"
                    
                    # Remove existing rule
                    self.rate_limiter.remove_rule(rule_name)
                    
                    # Add updated rule
                    rule = RateLimitConfig(
                        name=rule_name,
                        scope=RateLimitScope.PER_ROLE,
                        strategy=RateLimitStrategy.TOKEN_BUCKET,
                        requests_per_window=limits["requests_per_minute"],
                        window_seconds=60,
                        burst_capacity=limits.get("burst_capacity"),
                        refill_rate=limits["requests_per_minute"] / 60.0,
                        priority=15,
                        metadata={"role": role}
                    )
                    self.rate_limiter.add_rule(rule)
            
            # Update endpoint-specific limits
            if "endpoint_specific_limits" in updates:
                for endpoint, limits in updates["endpoint_specific_limits"].items():
                    rule_name = f"endpoint_limit_{hash(endpoint)}"
                    
                    # Remove existing rule
                    self.rate_limiter.remove_rule(rule_name)
                    
                    # Add updated rule
                    rule = RateLimitConfig(
                        name=rule_name,
                        scope=RateLimitScope.PER_ENDPOINT,
                        strategy=RateLimitStrategy.SLIDING_WINDOW,
                        requests_per_window=limits["requests_per_minute"],
                        window_seconds=limits.get("window_seconds", 60),
                        target_pattern=endpoint,
                        priority=25,
                        metadata={"endpoint_pattern": endpoint}
                    )
                    self.rate_limiter.add_rule(rule)
            
            # Update middleware configuration
            if "middleware_config" in updates:
                self.config.update(updates["middleware_config"])
                self.enabled = self.config.get("enabled", True)
                self.include_headers = self.config.get("include_headers", True)
                self.log_violations = self.config.get("log_violations", True)
            
            logger.info("Rate limiting configuration updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update rate limiting configuration: {e}")
            return False
    
    async def reset_user_limits(self, user_id: str) -> Dict[str, Any]:
        """Reset rate limits for a specific user."""
        reset_count = self.rate_limiter.reset_user_limits(user_id)
        
        return {
            "user_id": user_id,
            "reset_count": reset_count,
            "timestamp": datetime.utcnow().isoformat(),
            "success": True
        }
    
    async def reset_ip_limits(self, client_ip: str) -> Dict[str, Any]:
        """Reset rate limits for a specific IP address."""
        reset_count = self.rate_limiter.reset_ip_limits(client_ip)
        
        return {
            "client_ip": client_ip,
            "reset_count": reset_count,
            "timestamp": datetime.utcnow().isoformat(),
            "success": True
        }
    
    async def get_user_rate_limit_status(self, user_id: str) -> Dict[str, Any]:
        """Get current rate limit status for a specific user."""
        # Create mock context for user
        context = {
            "user_id": user_id,
            "endpoint": "/api/v1/general",
            "client_ip": "127.0.0.1",
            "user_roles": [],
            "timestamp": datetime.utcnow()
        }
        
        # Check current status without consuming limits
        # Note: This is a simplified implementation - in production you'd want
        # a read-only check that doesn't consume rate limit tokens
        status = await self.rate_limiter.check_rate_limit(context)
        
        return {
            "user_id": user_id,
            "allowed": status.allowed,
            "remaining": status.remaining,
            "reset_time": status.reset_time.isoformat(),
            "retry_after": status.retry_after,
            "violations_count": len([v for v in self.rate_limiter.get_recent_violations(1) 
                                   if v.client_info.get("user_id") == user_id]),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_rate_limit_config(self) -> Dict[str, Any]:
        """Get current rate limiting configuration."""
        return {
            "middleware_config": {
                "enabled": self.enabled,
                "include_headers": self.include_headers,
                "log_violations": self.log_violations,
                "bypass_patterns": self.bypass_patterns
            },
            "rate_limiter_config": self.rate_limiter.export_config(),
            "custom_rules": {
                "role_based_limits": self.config.get("role_based_limits", {}),
                "endpoint_specific_limits": self.config.get("endpoint_specific_limits", {})
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on rate limiting middleware."""
        try:
            # Test basic functionality with a mock request
            test_context = {
                "user_id": "health_check_user",
                "endpoint": "/health",
                "client_ip": "127.0.0.1",
                "timestamp": datetime.utcnow()
            }
            
            start_time = time.time()
            status = await self.rate_limiter.check_rate_limit(test_context)
            check_time = (time.time() - start_time) * 1000
            
            avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
            performance_target = self.config.get("rate_limiter", {}).get("performance_target_ms", 3.0)
            
            return {
                "status": "healthy" if check_time < performance_target else "degraded",
                "enabled": self.enabled,
                "performance": {
                    "last_check_time_ms": check_time,
                    "avg_check_time_ms": avg_processing_time,
                    "performance_target_ms": performance_target,
                    "target_met": avg_processing_time < performance_target
                },
                "statistics": {
                    "processed_requests": self.processed_requests,
                    "blocked_requests": self.blocked_requests,
                    "bypass_count": self.bypass_count,
                    "active_rules": len(self.rate_limiter.rules),
                    "recent_violations": len(self.rate_limiter.get_recent_violations(1))
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }