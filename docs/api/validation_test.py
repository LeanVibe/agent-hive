#!/usr/bin/env python3
"""
API Reference Validation Test Script

This script validates all code examples in the API reference documentation
to ensure they work correctly with the current implementation.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def test_advanced_orchestration():
    """Test Advanced Orchestration APIs"""
    print("🔄 Testing Advanced Orchestration APIs...")

    try:
        # Test imports
        from advanced_orchestration import (
            MultiAgentCoordinator,
            ResourceManager,
            ScalingManager,
        )
        from advanced_orchestration.models import (
            CoordinatorConfig,
            LoadBalancingStrategy,
            ResourceLimits,
            ResourceRequirements,
        )
        print("✅ Advanced Orchestration imports successful")

        # Test MultiAgentCoordinator initialization
        config = CoordinatorConfig(
            max_agents=20,
            load_balancing_strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
            health_check_interval=30
        )
        MultiAgentCoordinator(config)
        print("✅ MultiAgentCoordinator initialization successful")

        # Test ResourceManager initialization
        resource_limits = ResourceLimits(
            max_cpu_cores=8,
            max_memory_mb=16384,
            max_disk_mb=102400,
            max_network_mbps=1000
        )
        ResourceManager(resource_limits)
        print("✅ ResourceManager initialization successful")

        # Test ScalingManager initialization
        ScalingManager(resource_limits)
        print("✅ ScalingManager initialization successful")

        # Test ResourceRequirements
        ResourceRequirements(
            cpu_cores=2,
            memory_mb=1024,
            disk_mb=500,
            network_mbps=10
        )
        print("✅ ResourceRequirements creation successful")

        return True

    except Exception as e:
        print(f"❌ Advanced Orchestration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_external_api():
    """Test External API Integration"""
    print("🔄 Testing External API Integration...")

    try:
        # Test imports
        from external_api import ApiGateway, EventStreaming, WebhookServer
        from external_api.models import (
            ApiGatewayConfig,
            EventStreamConfig,
            WebhookConfig,
        )
        print("✅ External API imports successful")

        # Test WebhookServer initialization
        webhook_config = WebhookConfig(
            host="localhost",
            port=8080,
            rate_limit_requests=50,
            max_payload_size=1024000
        )
        WebhookServer(webhook_config)
        print("✅ WebhookServer initialization successful")

        # Test ApiGateway initialization
        gateway_config = ApiGatewayConfig(
            host="localhost",
            port=8081,
            enable_cors=True,
            rate_limit_requests=100
        )
        ApiGateway(gateway_config)
        print("✅ ApiGateway initialization successful")

        # Test EventStreaming initialization
        stream_config = EventStreamConfig(
            compression_enabled=True,
            batch_size=100,
            flush_interval=5  # seconds
        )
        EventStreaming(stream_config)
        print("✅ EventStreaming initialization successful")

        return True

    except Exception as e:
        print(f"❌ External API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_ml_enhancements():
    """Test ML Enhancement APIs"""
    print("🔄 Testing ML Enhancement APIs...")

    try:
        # Test imports
        from ml_enhancements import (
            AdaptiveLearning,
            PatternOptimizer,
            PredictiveAnalytics,
        )
        from ml_enhancements.models import MLConfig
        print("✅ ML Enhancement imports successful")

        # Test AdaptiveLearning initialization
        ml_config = MLConfig(
            learning_rate=0.01,
            confidence_threshold=0.8,
            update_frequency=100
        )
        AdaptiveLearning(ml_config)
        print("✅ AdaptiveLearning initialization successful")

        # Test PatternOptimizer initialization
        PatternOptimizer(ml_config)
        print("✅ PatternOptimizer initialization successful")

        # Test PredictiveAnalytics initialization
        PredictiveAnalytics(ml_config)
        print("✅ PredictiveAnalytics initialization successful")

        # Test feedback data creation
        {
            "task_id": "task-123",
            "outcome": "success",
            "confidence_score": 0.85,
            "execution_time": 2.5,
            "user_satisfaction": 9
        }
        print("✅ Feedback data creation successful")

        return True

    except Exception as e:
        print(f"❌ ML Enhancement test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cli_integration():
    """Test CLI integration examples"""
    print("🔄 Testing CLI integration...")

    try:
        # Test CLI imports
        from cli import LeanVibeCLI
        print("✅ CLI imports successful")

        # Test CLI initialization
        LeanVibeCLI()
        print("✅ CLI initialization successful")

        return True

    except Exception as e:
        print(f"❌ CLI integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all validation tests"""
    print("🚀 Starting API Reference Validation Tests")
    print("=" * 50)

    tests = [
        ("Advanced Orchestration", test_advanced_orchestration),
        ("External API Integration", test_external_api),
        ("ML Enhancements", test_ml_enhancements),
        ("CLI Integration", test_cli_integration)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        result = await test_func()
        results.append((test_name, result))

    print("\n🎯 Test Results Summary")
    print("=" * 50)

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n📊 Total: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All API reference examples validated successfully!")
        return 0
    else:
        print("⚠️  Some API reference examples need fixes")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
