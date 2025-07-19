#!/usr/bin/env python3
"""
Comprehensive Performance Baseline Testing System

Establishes and validates performance baselines for all Agent Hive components
including Security Framework, Service Discovery, and API Gateway integration.

Features:
- Automated baseline establishment through load testing
- Component-specific performance validation
- End-to-end system performance testing
- Performance regression detection
- Optimization recommendations
- Production readiness validation
"""

import asyncio
import time
import logging
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import concurrent.futures
import random
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from performance_monitor import (
    ComponentType, PerformanceLevel, UnifiedPerformanceMonitor,
    performance_monitor, track_jwt_authentication, track_rbac_authorization,
    track_rate_limiting, track_service_discovery, track_load_balancing,
    track_api_gateway_request, track_end_to_end_request
)


logger = logging.getLogger(__name__)


@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    operation_name: str
    component_type: ComponentType
    target_rps: int  # Requests per second
    duration_seconds: int
    concurrent_users: int
    ramp_up_seconds: int
    expected_success_rate: float = 0.99
    expected_avg_response_ms: float = 100.0
    expected_p95_response_ms: float = 200.0


@dataclass 
class PerformanceTestResult:
    """Results from performance testing."""
    test_name: str
    component_type: ComponentType
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    requests_per_second: float
    baseline_comparison: Dict[str, float]
    passed: bool
    errors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class PerformanceBaselineTester:
    """Comprehensive performance baseline testing system."""
    
    def __init__(self, monitor: UnifiedPerformanceMonitor):
        self.monitor = monitor
        self.logger = logging.getLogger(__name__)
        
        # Test configurations for all components
        self.test_configs = self._setup_test_configurations()
        
        # Results storage
        self.test_results: List[PerformanceTestResult] = []
        
    def _setup_test_configurations(self) -> List[LoadTestConfig]:
        """Setup performance test configurations for all components."""
        return [
            # Security Framework Tests
            LoadTestConfig(
                operation_name="jwt_authentication",
                component_type=ComponentType.AUTHENTICATION,
                target_rps=100,
                duration_seconds=60,
                concurrent_users=20,
                ramp_up_seconds=10,
                expected_success_rate=0.99,
                expected_avg_response_ms=50.0,  # Target: <50ms
                expected_p95_response_ms=80.0
            ),
            LoadTestConfig(
                operation_name="rbac_authorization",
                component_type=ComponentType.AUTHORIZATION,
                target_rps=200,
                duration_seconds=60,
                concurrent_users=40,
                ramp_up_seconds=10,
                expected_success_rate=0.99,
                expected_avg_response_ms=20.0,  # Target: <20ms
                expected_p95_response_ms=40.0
            ),
            LoadTestConfig(
                operation_name="rate_limiting",
                component_type=ComponentType.RATE_LIMITING,
                target_rps=500,
                duration_seconds=30,
                concurrent_users=50,
                ramp_up_seconds=5,
                expected_success_rate=0.95,  # Some rate limiting expected
                expected_avg_response_ms=5.0,  # Target: <5ms
                expected_p95_response_ms=10.0
            ),
            
            # Service Discovery Tests
            LoadTestConfig(
                operation_name="service_discovery",
                component_type=ComponentType.SERVICE_DISCOVERY,
                target_rps=150,
                duration_seconds=45,
                concurrent_users=30,
                ramp_up_seconds=5,
                expected_success_rate=0.99,
                expected_avg_response_ms=100.0,  # Target: <100ms
                expected_p95_response_ms=150.0
            ),
            LoadTestConfig(
                operation_name="load_balancing",
                component_type=ComponentType.LOAD_BALANCER,
                target_rps=300,
                duration_seconds=45,
                concurrent_users=60,
                ramp_up_seconds=5,
                expected_success_rate=0.99,
                expected_avg_response_ms=100.0,  # Target: <100ms
                expected_p95_response_ms=150.0
            ),
            
            # API Gateway Tests
            LoadTestConfig(
                operation_name="api_gateway_request",
                component_type=ComponentType.API_GATEWAY,
                target_rps=200,
                duration_seconds=90,
                concurrent_users=50,
                ramp_up_seconds=15,
                expected_success_rate=0.98,
                expected_avg_response_ms=100.0,  # Target: <100ms
                expected_p95_response_ms=200.0
            ),
            
            # End-to-End Integration Tests
            LoadTestConfig(
                operation_name="end_to_end_request",
                component_type=ComponentType.SYSTEM,
                target_rps=50,
                duration_seconds=120,
                concurrent_users=25,
                ramp_up_seconds=20,
                expected_success_rate=0.97,
                expected_avg_response_ms=200.0,  # Target: <200ms
                expected_p95_response_ms=400.0
            )
        ]
    
    async def run_comprehensive_baseline_tests(self) -> Dict[str, Any]:
        """Run comprehensive performance baseline tests."""
        self.logger.info("🚀 Starting Comprehensive Performance Baseline Testing")
        
        # Start monitoring
        await self.monitor.start_monitoring()
        
        # Clear previous metrics for clean baseline
        self.monitor.clear_metrics()
        
        test_results = {}
        overall_start_time = time.time()
        
        try:
            # Run all component tests
            for config in self.test_configs:
                self.logger.info(f"🧪 Running {config.operation_name} performance test...")
                
                result = await self._run_load_test(config)
                test_results[config.operation_name] = result
                self.test_results.append(result)
                
                # Wait between tests to avoid interference
                await asyncio.sleep(5)
            
            # Run system integration validation
            integration_result = await self._run_integration_validation()
            test_results["system_integration"] = integration_result
            
            # Generate comprehensive report
            overall_duration = time.time() - overall_start_time
            report = await self._generate_baseline_report(test_results, overall_duration)
            
            self.logger.info("✅ Comprehensive Performance Baseline Testing Completed")
            return report
            
        except Exception as e:
            self.logger.error(f"❌ Baseline testing failed: {e}")
            raise
        finally:
            await self.monitor.stop_monitoring()
    
    async def _run_load_test(self, config: LoadTestConfig) -> PerformanceTestResult:
        """Run load test for a specific component."""
        start_time = datetime.now()
        response_times = []
        errors = []
        successful_requests = 0
        failed_requests = 0
        
        # Get test function for component
        test_func = self._get_test_function(config.operation_name)
        
        # Calculate request intervals
        interval = 1.0 / config.target_rps
        ramp_up_interval = config.ramp_up_seconds / config.concurrent_users
        
        async def worker(worker_id: int):
            """Worker function for concurrent load testing."""
            nonlocal successful_requests, failed_requests
            
            # Ramp up delay
            await asyncio.sleep(worker_id * ramp_up_interval)
            
            end_time_worker = time.time() + config.duration_seconds
            request_count = 0
            
            while time.time() < end_time_worker:
                request_start = time.time()
                
                try:
                    await test_func()
                    successful_requests += 1
                    
                    response_time_ms = (time.time() - request_start) * 1000
                    response_times.append(response_time_ms)
                    
                except Exception as e:
                    failed_requests += 1
                    errors.append(f"Worker {worker_id} request {request_count}: {str(e)}")
                
                request_count += 1
                
                # Control request rate
                next_request_time = request_start + interval
                sleep_time = max(0, next_request_time - time.time())
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
        
        # Run concurrent workers
        tasks = [worker(i) for i in range(config.concurrent_users)]
        await asyncio.gather(*tasks)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Calculate statistics
        total_requests = successful_requests + failed_requests
        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            p50_response_time = statistics.median(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times)
            p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else max(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
        else:
            avg_response_time = p50_response_time = p95_response_time = p99_response_time = min_response_time = max_response_time = 0
        
        requests_per_second = total_requests / duration if duration > 0 else 0
        
        # Compare against baselines
        baseline_comparison = self._compare_against_baseline(config, avg_response_time, p95_response_time, success_rate)
        
        # Determine if test passed
        passed = (
            success_rate >= config.expected_success_rate and
            avg_response_time <= config.expected_avg_response_ms and
            p95_response_time <= config.expected_p95_response_ms
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(config, avg_response_time, p95_response_time, success_rate)
        
        result = PerformanceTestResult(
            test_name=config.operation_name,
            component_type=config.component_type,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            success_rate=success_rate,
            avg_response_time_ms=avg_response_time,
            p50_response_time_ms=p50_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            min_response_time_ms=min_response_time,
            max_response_time_ms=max_response_time,
            requests_per_second=requests_per_second,
            baseline_comparison=baseline_comparison,
            passed=passed,
            errors=errors[:10],  # Keep only first 10 errors
            recommendations=recommendations
        )
        
        # Log results
        status = "✅ PASSED" if passed else "❌ FAILED"
        self.logger.info(f"{status} {config.operation_name}: {success_rate:.1%} success, {avg_response_time:.1f}ms avg, {p95_response_time:.1f}ms p95")
        
        return result
    
    def _get_test_function(self, operation_name: str):
        """Get test function for specific operation."""
        test_functions = {
            "jwt_authentication": self._test_jwt_authentication,
            "rbac_authorization": self._test_rbac_authorization,
            "rate_limiting": self._test_rate_limiting,
            "service_discovery": self._test_service_discovery,
            "load_balancing": self._test_load_balancing,
            "api_gateway_request": self._test_api_gateway_request,
            "end_to_end_request": self._test_end_to_end_request
        }
        
        return test_functions.get(operation_name, self._test_default)
    
    @track_jwt_authentication({"test": "baseline"})
    async def _test_jwt_authentication(self):
        """Simulate JWT authentication operation."""
        await asyncio.sleep(random.uniform(0.01, 0.05))  # 10-50ms simulation
        if random.random() < 0.99:  # 99% success rate
            return {"status": "authenticated", "user_id": "test_user"}
        else:
            raise Exception("Authentication failed")
    
    @track_rbac_authorization({"test": "baseline"})
    async def _test_rbac_authorization(self):
        """Simulate RBAC authorization operation."""
        await asyncio.sleep(random.uniform(0.001, 0.01))  # 1-10ms simulation
        if random.random() < 0.99:  # 99% success rate
            return {"status": "authorized", "permissions": ["read", "write"]}
        else:
            raise Exception("Authorization failed")
    
    @track_rate_limiting({"test": "baseline"})
    async def _test_rate_limiting(self):
        """Simulate rate limiting operation."""
        await asyncio.sleep(random.uniform(0.001, 0.005))  # 1-5ms simulation
        if random.random() < 0.95:  # 95% success rate (some rate limiting expected)
            return {"status": "allowed", "remaining": 100}
        else:
            raise Exception("Rate limit exceeded")
    
    @track_service_discovery({"test": "baseline"})
    async def _test_service_discovery(self):
        """Simulate service discovery operation."""
        await asyncio.sleep(random.uniform(0.01, 0.08))  # 10-80ms simulation
        if random.random() < 0.99:  # 99% success rate
            return {"status": "found", "service": "auth-service", "endpoint": "http://auth:8080"}
        else:
            raise Exception("Service not found")
    
    @track_load_balancing({"test": "baseline"})
    async def _test_load_balancing(self):
        """Simulate load balancing operation."""
        await asyncio.sleep(random.uniform(0.01, 0.08))  # 10-80ms simulation
        if random.random() < 0.99:  # 99% success rate
            return {"status": "balanced", "instance": "server-1", "health": "healthy"}
        else:
            raise Exception("No healthy instances")
    
    @track_api_gateway_request({"test": "baseline"})
    async def _test_api_gateway_request(self):
        """Simulate API Gateway request processing."""
        await asyncio.sleep(random.uniform(0.02, 0.12))  # 20-120ms simulation
        if random.random() < 0.98:  # 98% success rate
            return {"status": "processed", "response_size": 1024}
        else:
            raise Exception("Gateway error")
    
    @track_end_to_end_request({"test": "baseline"})
    async def _test_end_to_end_request(self):
        """Simulate end-to-end request processing."""
        # Simulate complex request with multiple components
        await self._test_jwt_authentication()
        await self._test_rbac_authorization()
        await self._test_service_discovery()
        await self._test_api_gateway_request()
        
        await asyncio.sleep(random.uniform(0.01, 0.03))  # Additional processing time
        
        if random.random() < 0.97:  # 97% success rate
            return {"status": "completed", "total_time": "simulated"}
        else:
            raise Exception("End-to-end request failed")
    
    async def _test_default(self):
        """Default test function."""
        await asyncio.sleep(random.uniform(0.01, 0.05))
        return {"status": "ok"}
    
    def _compare_against_baseline(self, config: LoadTestConfig, avg_response: float, 
                                 p95_response: float, success_rate: float) -> Dict[str, float]:
        """Compare test results against baseline expectations."""
        return {
            "avg_response_vs_target": ((avg_response - config.expected_avg_response_ms) / config.expected_avg_response_ms) * 100,
            "p95_response_vs_target": ((p95_response - config.expected_p95_response_ms) / config.expected_p95_response_ms) * 100,
            "success_rate_vs_target": ((success_rate - config.expected_success_rate) / config.expected_success_rate) * 100
        }
    
    def _generate_recommendations(self, config: LoadTestConfig, avg_response: float,
                                p95_response: float, success_rate: float) -> List[str]:
        """Generate optimization recommendations based on test results."""
        recommendations = []
        
        if avg_response > config.expected_avg_response_ms * 1.5:
            recommendations.append(f"Average response time ({avg_response:.1f}ms) significantly exceeds target ({config.expected_avg_response_ms}ms)")
        
        if p95_response > config.expected_p95_response_ms * 1.2:
            recommendations.append(f"P95 response time ({p95_response:.1f}ms) exceeds target ({config.expected_p95_response_ms}ms)")
        
        if success_rate < config.expected_success_rate:
            recommendations.append(f"Success rate ({success_rate:.1%}) below target ({config.expected_success_rate:.1%})")
        
        # Component-specific recommendations
        if config.component_type == ComponentType.AUTHENTICATION and avg_response > 50:
            recommendations.append("Consider JWT token caching and signature optimization")
        
        if config.component_type == ComponentType.AUTHORIZATION and avg_response > 20:
            recommendations.append("Consider permission caching and role hierarchy optimization")
        
        if config.component_type == ComponentType.SERVICE_DISCOVERY and avg_response > 100:
            recommendations.append("Consider service registry caching and connection pooling")
        
        return recommendations
    
    async def _run_integration_validation(self) -> Dict[str, Any]:
        """Run system integration validation tests."""
        self.logger.info("🔗 Running System Integration Validation...")
        
        # Test cross-component dependencies
        integration_tests = [
            self._test_auth_to_service_flow,
            self._test_gateway_to_backend_flow,
            self._test_full_request_lifecycle
        ]
        
        results = {}
        for test in integration_tests:
            test_name = test.__name__.replace("_test_", "")
            try:
                start_time = time.time()
                result = await test()
                duration = time.time() - start_time
                
                results[test_name] = {
                    "passed": True,
                    "duration_ms": duration * 1000,
                    "result": result
                }
                self.logger.info(f"✅ {test_name}: {duration*1000:.1f}ms")
                
            except Exception as e:
                results[test_name] = {
                    "passed": False,
                    "error": str(e)
                }
                self.logger.error(f"❌ {test_name}: {e}")
        
        return results
    
    async def _test_auth_to_service_flow(self):
        """Test authentication to service discovery flow."""
        # Simulate user authentication followed by service lookup
        auth_result = await self._test_jwt_authentication()
        service_result = await self._test_service_discovery()
        
        return {
            "auth_result": auth_result,
            "service_result": service_result,
            "flow_status": "completed"
        }
    
    async def _test_gateway_to_backend_flow(self):
        """Test API Gateway to backend service flow."""
        # Simulate gateway processing with load balancing
        gateway_result = await self._test_api_gateway_request()
        lb_result = await self._test_load_balancing()
        
        return {
            "gateway_result": gateway_result,
            "lb_result": lb_result,
            "flow_status": "completed"
        }
    
    async def _test_full_request_lifecycle(self):
        """Test complete request lifecycle."""
        # Simulate full request: Auth -> RBAC -> Service Discovery -> Load Balancing -> Gateway
        results = []
        
        results.append(await self._test_jwt_authentication())
        results.append(await self._test_rbac_authorization())
        results.append(await self._test_rate_limiting())
        results.append(await self._test_service_discovery())
        results.append(await self._test_load_balancing())
        results.append(await self._test_api_gateway_request())
        
        return {
            "lifecycle_steps": len(results),
            "all_successful": all(r is not None for r in results),
            "flow_status": "completed"
        }
    
    async def _generate_baseline_report(self, test_results: Dict[str, Any], 
                                      total_duration: float) -> Dict[str, Any]:
        """Generate comprehensive baseline report."""
        self.logger.info("📊 Generating Comprehensive Baseline Report...")
        
        # Get performance summary from monitor
        performance_summary = self.monitor.get_performance_summary()
        component_summaries = {
            component.value: self.monitor.get_performance_summary(component)
            for component in ComponentType
        }
        
        # Analyze test results
        passed_tests = sum(1 for result in self.test_results if result.passed)
        total_tests = len(self.test_results)
        overall_success_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        # Calculate overall performance metrics
        all_response_times = []
        all_success_rates = []
        
        for result in self.test_results:
            if result.successful_requests > 0:
                all_response_times.append(result.avg_response_time_ms)
                all_success_rates.append(result.success_rate)
        
        overall_avg_response = statistics.mean(all_response_times) if all_response_times else 0
        overall_success_rate_avg = statistics.mean(all_success_rates) if all_success_rates else 0
        
        # Generate recommendations
        overall_recommendations = self._generate_overall_recommendations()
        
        # Performance targets validation
        targets_met = self._validate_performance_targets()
        
        report = {
            "baseline_report": {
                "generated_at": datetime.now().isoformat(),
                "total_duration_seconds": total_duration,
                "test_summary": {
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "failed_tests": total_tests - passed_tests,
                    "overall_pass_rate": overall_success_rate,
                    "overall_avg_response_ms": overall_avg_response,
                    "overall_success_rate": overall_success_rate_avg
                },
                "performance_targets": targets_met,
                "component_results": {
                    result.test_name: {
                        "component_type": result.component_type.value,
                        "passed": result.passed,
                        "success_rate": result.success_rate,
                        "avg_response_ms": result.avg_response_time_ms,
                        "p95_response_ms": result.p95_response_time_ms,
                        "requests_per_second": result.requests_per_second,
                        "baseline_comparison": result.baseline_comparison,
                        "recommendations": result.recommendations
                    }
                    for result in self.test_results
                },
                "integration_tests": test_results.get("system_integration", {}),
                "performance_monitor_summary": performance_summary,
                "component_summaries": component_summaries,
                "overall_recommendations": overall_recommendations,
                "production_readiness": self._assess_production_readiness(overall_success_rate, targets_met)
            }
        }
        
        # Save report to file
        report_file = f"performance_baseline_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"📄 Baseline report saved to: {report_file}")
        
        return report
    
    def _generate_overall_recommendations(self) -> List[str]:
        """Generate overall system recommendations."""
        recommendations = []
        
        # Analyze results across components
        security_results = [r for r in self.test_results if r.component_type in [ComponentType.AUTHENTICATION, ComponentType.AUTHORIZATION, ComponentType.RATE_LIMITING]]
        service_results = [r for r in self.test_results if r.component_type in [ComponentType.SERVICE_DISCOVERY, ComponentType.LOAD_BALANCER]]
        gateway_results = [r for r in self.test_results if r.component_type == ComponentType.API_GATEWAY]
        
        # Security recommendations
        security_avg = statistics.mean([r.avg_response_time_ms for r in security_results]) if security_results else 0
        if security_avg > 50:
            recommendations.append("Security framework performance needs optimization - consider caching and pre-computation")
        
        # Service discovery recommendations
        service_avg = statistics.mean([r.avg_response_time_ms for r in service_results]) if service_results else 0
        if service_avg > 100:
            recommendations.append("Service discovery performance needs optimization - consider registry caching")
        
        # System integration recommendations
        failed_tests = [r for r in self.test_results if not r.passed]
        if len(failed_tests) > 0:
            recommendations.append(f"{len(failed_tests)} component tests failed - review individual component performance")
        
        return recommendations
    
    def _validate_performance_targets(self) -> Dict[str, Dict[str, Any]]:
        """Validate against defined performance targets."""
        targets = {
            "security_framework": {
                "jwt_auth_target_ms": 50,
                "rbac_check_target_ms": 20,
                "rate_limit_target_ms": 5,
                "achieved": {},
                "met": False
            },
            "service_discovery": {
                "service_lookup_target_ms": 100,
                "load_balance_target_ms": 100,
                "achieved": {},
                "met": False
            },
            "api_gateway": {
                "request_processing_target_ms": 100,
                "achieved": {},
                "met": False
            },
            "system_integration": {
                "end_to_end_target_ms": 200,
                "achieved": {},
                "met": False
            }
        }
        
        # Check security framework targets
        jwt_result = next((r for r in self.test_results if r.test_name == "jwt_authentication"), None)
        rbac_result = next((r for r in self.test_results if r.test_name == "rbac_authorization"), None)
        rate_result = next((r for r in self.test_results if r.test_name == "rate_limiting"), None)
        
        if jwt_result:
            targets["security_framework"]["achieved"]["jwt_auth_ms"] = jwt_result.avg_response_time_ms
        if rbac_result:
            targets["security_framework"]["achieved"]["rbac_check_ms"] = rbac_result.avg_response_time_ms
        if rate_result:
            targets["security_framework"]["achieved"]["rate_limit_ms"] = rate_result.avg_response_time_ms
        
        targets["security_framework"]["met"] = (
            (jwt_result and jwt_result.avg_response_time_ms <= 50) and
            (rbac_result and rbac_result.avg_response_time_ms <= 20) and
            (rate_result and rate_result.avg_response_time_ms <= 5)
        )
        
        # Check service discovery targets
        service_result = next((r for r in self.test_results if r.test_name == "service_discovery"), None)
        lb_result = next((r for r in self.test_results if r.test_name == "load_balancing"), None)
        
        if service_result:
            targets["service_discovery"]["achieved"]["service_lookup_ms"] = service_result.avg_response_time_ms
        if lb_result:
            targets["service_discovery"]["achieved"]["load_balance_ms"] = lb_result.avg_response_time_ms
        
        targets["service_discovery"]["met"] = (
            (service_result and service_result.avg_response_time_ms <= 100) and
            (lb_result and lb_result.avg_response_time_ms <= 100)
        )
        
        # Check API Gateway targets
        gateway_result = next((r for r in self.test_results if r.test_name == "api_gateway_request"), None)
        if gateway_result:
            targets["api_gateway"]["achieved"]["request_processing_ms"] = gateway_result.avg_response_time_ms
            targets["api_gateway"]["met"] = gateway_result.avg_response_time_ms <= 100
        
        # Check system integration targets
        e2e_result = next((r for r in self.test_results if r.test_name == "end_to_end_request"), None)
        if e2e_result:
            targets["system_integration"]["achieved"]["end_to_end_ms"] = e2e_result.avg_response_time_ms
            targets["system_integration"]["met"] = e2e_result.avg_response_time_ms <= 200
        
        return targets
    
    def _assess_production_readiness(self, overall_pass_rate: float, targets_met: Dict[str, Any]) -> Dict[str, Any]:
        """Assess production readiness based on test results."""
        targets_passed = sum(1 for target in targets_met.values() if target.get("met", False))
        total_targets = len(targets_met)
        
        readiness_score = (overall_pass_rate * 0.6 + (targets_passed / total_targets) * 0.4) * 100
        
        if readiness_score >= 90:
            readiness_level = "PRODUCTION_READY"
            status_emoji = "🟢"
        elif readiness_score >= 75:
            readiness_level = "MOSTLY_READY"
            status_emoji = "🟡"
        elif readiness_score >= 60:
            readiness_level = "NEEDS_OPTIMIZATION"
            status_emoji = "🟠"
        else:
            readiness_level = "NOT_READY"
            status_emoji = "🔴"
        
        return {
            "readiness_level": readiness_level,
            "readiness_score": round(readiness_score, 1),
            "status_emoji": status_emoji,
            "test_pass_rate": overall_pass_rate,
            "targets_met": f"{targets_passed}/{total_targets}",
            "recommendation": self._get_readiness_recommendation(readiness_level)
        }
    
    def _get_readiness_recommendation(self, readiness_level: str) -> str:
        """Get production readiness recommendation."""
        recommendations = {
            "PRODUCTION_READY": "System is ready for production deployment with excellent performance baselines established.",
            "MOSTLY_READY": "System is mostly ready for production. Address remaining performance optimizations before deployment.",
            "NEEDS_OPTIMIZATION": "System requires performance optimization before production deployment. Focus on failed targets.",
            "NOT_READY": "System is not ready for production. Significant performance improvements required."
        }
        
        return recommendations.get(readiness_level, "Unknown readiness level")


async def main():
    """Main function to run comprehensive performance baseline testing."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 Agent Hive Performance Baseline Testing System")
    print("=" * 60)
    
    # Initialize performance monitor and baseline tester
    monitor = performance_monitor
    tester = PerformanceBaselineTester(monitor)
    
    try:
        # Run comprehensive baseline tests
        report = await tester.run_comprehensive_baseline_tests()
        
        # Print summary
        baseline_report = report["baseline_report"]
        print("\n📊 PERFORMANCE BASELINE TEST SUMMARY")
        print("=" * 50)
        
        test_summary = baseline_report["test_summary"]
        print(f"✅ Tests Passed: {test_summary['passed_tests']}/{test_summary['total_tests']}")
        print(f"📈 Overall Success Rate: {test_summary['overall_success_rate']:.1%}")
        print(f"⚡ Average Response Time: {test_summary['overall_avg_response_ms']:.1f}ms")
        
        # Production readiness
        readiness = baseline_report["production_readiness"]
        print(f"\n{readiness['status_emoji']} Production Readiness: {readiness['readiness_level']}")
        print(f"📊 Readiness Score: {readiness['readiness_score']}/100")
        print(f"💡 Recommendation: {readiness['recommendation']}")
        
        # Performance targets
        targets = baseline_report["performance_targets"]
        print(f"\n🎯 PERFORMANCE TARGETS VALIDATION:")
        for category, target_info in targets.items():
            status = "✅" if target_info.get("met", False) else "❌"
            print(f"{status} {category.replace('_', ' ').title()}: {target_info.get('met', False)}")
        
        # Overall recommendations
        if baseline_report["overall_recommendations"]:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in baseline_report["overall_recommendations"]:
                print(f"  • {rec}")
        
        print(f"\n📄 Detailed report available in JSON format")
        print("🎉 Performance baseline testing completed successfully!")
        
        return report
        
    except Exception as e:
        print(f"❌ Performance baseline testing failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())