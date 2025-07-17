#!/usr/bin/env python3
"""
Comprehensive Integration Test for Unified Security API

Tests all components of the unified security system:
- Security Integration
- Unified Security Config
- Security Endpoints
- API Gateway Integration
- Performance Benchmarks (<200ms target)
"""

import asyncio
import time
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UnifiedSecurityIntegrationTest:
    """Comprehensive integration test for unified security system."""
    
    def __init__(self):
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "total": 0,
            "performance_tests": [],
            "errors": []
        }
    
    def log_test(self, test_name: str, passed: bool, duration_ms: float = 0, error: str = None):
        """Log test result."""
        self.test_results["total"] += 1
        
        if passed:
            self.test_results["passed"] += 1
            status = "✅ PASS"
        else:
            self.test_results["failed"] += 1
            status = "❌ FAIL"
            if error:
                self.test_results["errors"].append(f"{test_name}: {error}")
        
        if duration_ms > 0:
            self.test_results["performance_tests"].append({
                "test": test_name,
                "duration_ms": duration_ms,
                "passed": passed,
                "target_met": duration_ms < 200
            })
        
        logger.info(f"{status} {test_name} ({duration_ms:.2f}ms)")
    
    async def test_security_config(self) -> bool:
        """Test unified security configuration."""
        try:
            start_time = time.time()
            
            from config.unified_security_config import get_security_config, SecurityProfile
            
            # Test default config
            config = get_security_config()
            assert config.profile == SecurityProfile.DEVELOPMENT
            assert config.auth.enabled_methods is not None
            assert config.rbac.roles is not None
            
            # Test production config
            prod_config = get_security_config(SecurityProfile.PRODUCTION)
            assert prod_config.profile == SecurityProfile.PRODUCTION
            assert prod_config.auth.require_tls == True
            assert prod_config.enforce_https == True
            
            # Test config accessors
            auth_config = config.get_auth_config()
            assert "enabled_methods" in auth_config
            assert "jwt_secret" in auth_config
            
            duration = (time.time() - start_time) * 1000
            self.log_test("Security Config", True, duration)
            return True
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test("Security Config", False, duration, str(e))
            return False
    
    async def test_security_integration(self) -> bool:
        """Test security integration module."""
        try:
            start_time = time.time()
            
            from security_integration import SecurityIntegration, SecurityValidationRequest
            
            # Initialize security integration
            security = SecurityIntegration()
            
            # Test basic validation
            request = SecurityValidationRequest(
                command="ls -la",
                input_data="test input",
                user_id="test_user"
            )
            
            result = await security.validate_unified_security(request)
            assert result is not None
            assert hasattr(result, 'valid')
            assert hasattr(result, 'risk_level')
            
            duration = (time.time() - start_time) * 1000
            self.log_test("Security Integration", True, duration)
            return True
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test("Security Integration", False, duration, str(e))
            return False
    
    async def test_security_validation_performance(self) -> bool:
        """Test security validation performance (<200ms target)."""
        try:
            from security_integration import SecurityIntegration, SecurityValidationRequest
            
            security = SecurityIntegration()
            
            # Test multiple validation scenarios
            test_cases = [
                {"name": "Command Validation", "request": SecurityValidationRequest(command="ls -la", user_id="test")},
                {"name": "Input Validation", "request": SecurityValidationRequest(input_data="test input", user_id="test")},
                {"name": "Combined Validation", "request": SecurityValidationRequest(
                    command="ls -la", 
                    input_data="test input",
                    permissions_required=["read"],
                    user_id="test"
                )}
            ]
            
            all_passed = True
            
            for test_case in test_cases:
                start_time = time.time()
                
                result = await security.validate_unified_security(test_case["request"])
                
                duration = (time.time() - start_time) * 1000
                
                # Performance target: <200ms
                target_met = duration < 200
                
                if not target_met:
                    all_passed = False
                
                self.log_test(f"Performance - {test_case['name']}", target_met, duration)
            
            return all_passed
            
        except Exception as e:
            self.log_test("Security Validation Performance", False, 0, str(e))
            return False
    
    async def test_auth_middleware(self) -> bool:
        """Test authentication middleware."""
        try:
            start_time = time.time()
            
            from external_api.auth_middleware import AuthenticationMiddleware
            
            # Test middleware initialization
            config = {
                "enabled_methods": ["api_key", "jwt"],
                "jwt_secret": "test-secret",
                "max_auth_attempts": 5
            }
            
            auth_middleware = AuthenticationMiddleware(config)
            assert auth_middleware.config == config
            assert auth_middleware.api_keys == {}
            
            duration = (time.time() - start_time) * 1000
            self.log_test("Auth Middleware", True, duration)
            return True
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test("Auth Middleware", False, duration, str(e))
            return False
    
    async def test_security_manager(self) -> bool:
        """Test security manager."""
        try:
            start_time = time.time()
            
            from security.security_manager import SecurityManager
            
            # Test security manager initialization
            config = {
                "enable_command_validation": True,
                "enable_input_sanitization": True,
                "audit_enabled": True,
                "audit_database_path": ":memory:",
                "audit_retention_days": 30
            }
            
            security_manager = SecurityManager(config)
            
            # Test command validation
            result = await security_manager.validate_command("ls -la", "test_user")
            assert "valid" in result
            assert "risk_level" in result
            
            duration = (time.time() - start_time) * 1000
            self.log_test("Security Manager", True, duration)
            return True
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test("Security Manager", False, duration, str(e))
            return False
    
    async def test_unified_api_gateway(self) -> bool:
        """Test unified API gateway."""
        try:
            start_time = time.time()
            
            from external_api.unified_api_gateway import UnifiedApiGateway, create_unified_api_gateway
            
            # Test gateway creation
            gateway = create_unified_api_gateway(host="localhost", port=8082)
            assert gateway is not None
            assert hasattr(gateway, 'security_config')
            assert hasattr(gateway, 'start_server')
            
            # Test security info
            security_info = await gateway.get_security_info()
            assert "profile" in security_info
            assert "auth_methods" in security_info
            assert "rbac_enabled" in security_info
            
            duration = (time.time() - start_time) * 1000
            self.log_test("Unified API Gateway", True, duration)
            return True
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test("Unified API Gateway", False, duration, str(e))
            return False
    
    async def test_security_endpoints(self) -> bool:
        """Test security endpoints configuration."""
        try:
            start_time = time.time()
            
            from external_api.security_endpoints import router, ValidationRequest, ValidationResponse
            
            # Test router configuration
            assert router.prefix == "/api/security"
            assert "security" in router.tags
            
            # Test Pydantic models
            test_request = ValidationRequest(
                command="ls -la",
                input_data="test",
                user_id="test_user"
            )
            
            assert test_request.command == "ls -la"
            assert test_request.user_id == "test_user"
            
            duration = (time.time() - start_time) * 1000
            self.log_test("Security Endpoints", True, duration)
            return True
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test("Security Endpoints", False, duration, str(e))
            return False
    
    async def test_comprehensive_integration(self) -> bool:
        """Test comprehensive integration of all components."""
        try:
            start_time = time.time()
            
            # Test that all components can work together
            from config.unified_security_config import get_security_config
            from security_integration import SecurityIntegration
            from external_api.unified_api_gateway import UnifiedApiGateway
            
            # Get security config
            config = get_security_config()
            
            # Initialize security integration
            security = SecurityIntegration(config)
            
            # Create unified gateway
            gateway = UnifiedApiGateway()
            
            # Test security status
            status = await security.get_security_status()
            assert status["status"] == "operational"
            
            # Test gateway security info
            security_info = await gateway.get_security_info()
            assert security_info["profile"] == config.profile.value
            
            duration = (time.time() - start_time) * 1000
            self.log_test("Comprehensive Integration", True, duration)
            return True
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test("Comprehensive Integration", False, duration, str(e))
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        logger.info("🚀 Starting Unified Security Integration Tests")
        logger.info("=" * 60)
        
        test_methods = [
            self.test_security_config,
            self.test_security_integration,
            self.test_auth_middleware,
            self.test_security_manager,
            self.test_unified_api_gateway,
            self.test_security_endpoints,
            self.test_security_validation_performance,
            self.test_comprehensive_integration
        ]
        
        overall_start = time.time()
        
        for test_method in test_methods:
            try:
                await test_method()
            except Exception as e:
                logger.error(f"Test method {test_method.__name__} failed: {e}")
                self.test_results["failed"] += 1
                self.test_results["total"] += 1
        
        overall_duration = (time.time() - overall_start) * 1000
        
        # Calculate performance summary
        performance_summary = {
            "total_tests": len(self.test_results["performance_tests"]),
            "target_met": sum(1 for t in self.test_results["performance_tests"] if t["target_met"]),
            "average_duration": sum(t["duration_ms"] for t in self.test_results["performance_tests"]) / len(self.test_results["performance_tests"]) if self.test_results["performance_tests"] else 0,
            "max_duration": max(t["duration_ms"] for t in self.test_results["performance_tests"]) if self.test_results["performance_tests"] else 0
        }
        
        # Print summary
        logger.info("=" * 60)
        logger.info("🔍 TEST SUMMARY")
        logger.info(f"Total Tests: {self.test_results['total']}")
        logger.info(f"Passed: {self.test_results['passed']}")
        logger.info(f"Failed: {self.test_results['failed']}")
        logger.info(f"Success Rate: {(self.test_results['passed'] / self.test_results['total']) * 100:.1f}%")
        logger.info(f"Overall Duration: {overall_duration:.2f}ms")
        
        logger.info("⚡ PERFORMANCE SUMMARY")
        logger.info(f"Performance Tests: {performance_summary['total_tests']}")
        logger.info(f"Target Met (<200ms): {performance_summary['target_met']}")
        logger.info(f"Average Duration: {performance_summary['average_duration']:.2f}ms")
        logger.info(f"Max Duration: {performance_summary['max_duration']:.2f}ms")
        
        if self.test_results["errors"]:
            logger.error("❌ ERRORS:")
            for error in self.test_results["errors"]:
                logger.error(f"  - {error}")
        
        success = self.test_results["failed"] == 0
        
        if success:
            logger.info("✅ ALL TESTS PASSED - UNIFIED SECURITY INTEGRATION SUCCESSFUL!")
        else:
            logger.error("❌ SOME TESTS FAILED - REVIEW REQUIRED")
        
        return {
            "success": success,
            "results": self.test_results,
            "performance": performance_summary,
            "overall_duration_ms": overall_duration
        }


async def main():
    """Main test execution."""
    test_runner = UnifiedSecurityIntegrationTest()
    
    try:
        results = await test_runner.run_all_tests()
        
        # Exit with appropriate code
        sys.exit(0 if results["success"] else 1)
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())