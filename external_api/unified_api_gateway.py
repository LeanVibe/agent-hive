"""
Unified API Gateway with Integrated Security

Production-ready API Gateway that integrates:
- Real FastAPI HTTP server
- Unified security endpoints
- Service discovery
- Performance monitoring
- Comprehensive logging
"""

import asyncio
import logging
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .api_gateway import ApiGateway
from .security_endpoints import security_router
from .models import ApiGatewayConfig
from config.unified_security_config import get_security_config


logger = logging.getLogger(__name__)


class UnifiedApiGateway(ApiGateway):
    """
    Unified API Gateway with integrated security components.
    
    Extends the base ApiGateway with:
    - Unified security endpoints
    - Enhanced monitoring
    - Production-ready configuration
    """
    
    def __init__(self, config: Optional[ApiGatewayConfig] = None, service_discovery=None):
        """
        Initialize unified API gateway.
        
        Args:
            config: API gateway configuration
            service_discovery: Service discovery instance
        """
        # Get unified security config
        security_config = get_security_config()
        
        # Override config with security settings if not provided
        if config is None:
            config = ApiGatewayConfig(
                **security_config.get_api_gateway_config()
            )
        
        super().__init__(config, service_discovery)
        
        # Initialize security integration
        self.security_config = security_config
        
        logger.info("Unified API Gateway initialized with security integration")
    
    def _init_fastapi_app(self) -> None:
        """Initialize FastAPI application with unified security integration."""
        if not self.app:
            self.app = FastAPI(
                title="LeanVibe Agent Hive - Unified API Gateway",
                description="Production-ready API Gateway with unified security components",
                version="1.0.0",
                docs_url="/docs" if self.security_config.profile.value == "development" else None,
                redoc_url="/redoc" if self.security_config.profile.value == "development" else None
            )
        
        # Add CORS middleware with security config
        if self.config.enable_cors:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.security_config.api_gateway.cors_origins,
                allow_credentials=True,
                allow_methods=self.security_config.api_gateway.cors_methods,
                allow_headers=self.security_config.api_gateway.cors_headers,
            )
        
        # Include unified security endpoints
        self.app.include_router(security_router)
        logger.info("✅ Unified security endpoints integrated successfully")
        
        # Add enhanced health check endpoint
        @self.app.get("/health")
        async def unified_health_check():
            """Enhanced health check with security status."""
            try:
                # Get base health check
                base_health = await self.health_check()
                
                # Add security status
                security_status = {
                    "security_profile": self.security_config.profile.value,
                    "auth_methods": [method.value for method in self.security_config.auth.enabled_methods],
                    "monitoring_enabled": self.security_config.monitoring.enabled,
                    "audit_enabled": self.security_config.audit.enabled
                }
                
                return {
                    **base_health,
                    "security": security_status,
                    "unified_gateway": True
                }
                
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return {
                    "status": "unhealthy",
                    "error": str(e),
                    "unified_gateway": True
                }
        
        # Add metrics endpoint
        @self.app.get("/metrics")
        async def get_metrics():
            """Get API Gateway metrics."""
            try:
                return {
                    "gateway_info": self.get_gateway_info(),
                    "route_stats": self.get_route_statistics(),
                    "security_profile": self.security_config.profile.value,
                    "performance": {
                        "target_response_time_ms": 200,
                        "max_request_size_mb": self.security_config.api_gateway.max_request_size_mb,
                        "timeout_seconds": self.security_config.api_gateway.request_timeout_seconds
                    }
                }
            except Exception as e:
                logger.error(f"Metrics endpoint failed: {e}")
                return {"error": f"Metrics unavailable: {str(e)}"}
        
        # Add API documentation endpoint
        @self.app.get("/api/info")
        async def get_api_info():
            """Get API information and available endpoints."""
            return {
                "title": "LeanVibe Agent Hive - Unified API Gateway",
                "version": "1.0.0",
                "security_endpoints": {
                    "validate": "/api/security/validate",
                    "login": "/api/security/auth/login",
                    "refresh": "/api/security/auth/refresh",
                    "logout": "/api/security/auth/logout",
                    "status": "/api/security/status",
                    "audit": "/api/security/audit/events",
                    "health": "/api/security/health"
                },
                "gateway_endpoints": {
                    "health": "/health",
                    "metrics": "/metrics",
                    "info": "/api/info"
                },
                "configuration": {
                    "cors_enabled": self.config.enable_cors,
                    "auth_required": self.config.auth_required,
                    "rate_limiting": {
                        "requests_per_minute": self.config.rate_limit_requests,
                        "window_seconds": self.config.rate_limit_window
                    }
                }
            }
        
        logger.info("✅ Unified API Gateway FastAPI application initialized")
    
    async def start_server(self) -> None:
        """Start the unified API gateway server."""
        if self.server_started:
            logger.warning("Unified API gateway already started")
            return
        
        try:
            logger.info(f"🚀 Starting Unified API Gateway on {self.config.host}:{self.config.port}")
            
            # Initialize FastAPI app if not already done
            if not self.app:
                self._init_fastapi_app()
            
            # Configure uvicorn with security settings
            uvicorn_config = uvicorn.Config(
                app=self.app,
                host=self.config.host,
                port=self.config.port,
                log_level="info" if self.security_config.profile.value == "development" else "warning",
                access_log=self.security_config.api_gateway.enable_request_logging,
                reload=self.security_config.profile.value == "development"
            )
            
            self.server = uvicorn.Server(uvicorn_config)
            
            # Start server in background task
            self.server_task = asyncio.create_task(self.server.serve())
            
            # Wait for server to start
            await asyncio.sleep(0.1)
            
            self.server_started = True
            logger.info(f"✅ Unified API Gateway started successfully on {self.config.host}:{self.config.port}")
            logger.info(f"🔐 Security profile: {self.security_config.profile.value}")
            logger.info(f"📊 Monitoring enabled: {self.security_config.monitoring.enabled}")
            logger.info(f"📝 Audit logging enabled: {self.security_config.audit.enabled}")
            
        except Exception as e:
            logger.error(f"❌ Failed to start unified API gateway: {e}")
            raise
    
    async def get_security_info(self) -> dict:
        """Get security information for monitoring."""
        return {
            "profile": self.security_config.profile.value,
            "auth_methods": [method.value for method in self.security_config.auth.enabled_methods],
            "rbac_enabled": True,
            "monitoring_enabled": self.security_config.monitoring.enabled,
            "audit_enabled": self.security_config.audit.enabled,
            "rate_limiting": {
                "enabled": self.security_config.rate_limiting.enabled,
                "requests_per_minute": self.security_config.rate_limiting.requests_per_minute,
                "per_endpoint_limits": self.security_config.rate_limiting.per_endpoint_limits
            },
            "cors": {
                "enabled": self.security_config.api_gateway.enable_cors,
                "origins": self.security_config.api_gateway.cors_origins,
                "methods": self.security_config.api_gateway.cors_methods
            }
        }


# Factory function for creating unified API gateway
def create_unified_api_gateway(host: str = "localhost", port: int = 8081) -> UnifiedApiGateway:
    """
    Factory function to create unified API gateway instance.
    
    Args:
        host: Gateway host
        port: Gateway port
        
    Returns:
        Configured unified API gateway instance
    """
    security_config = get_security_config()
    
    gateway_config = ApiGatewayConfig(
        host=host,
        port=port,
        **security_config.get_api_gateway_config()
    )
    
    return UnifiedApiGateway(gateway_config)


# Main entry point for running the unified API gateway
async def main():
    """Main entry point for running the unified API gateway."""
    gateway = create_unified_api_gateway()
    
    try:
        await gateway.start_server()
        logger.info("Unified API Gateway is running. Press Ctrl+C to stop.")
        
        # Keep the server running
        while gateway.server_started:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down unified API gateway...")
        await gateway.stop_server()
    except Exception as e:
        logger.error(f"Gateway error: {e}")
        await gateway.stop_server()
        raise


if __name__ == "__main__":
    asyncio.run(main())