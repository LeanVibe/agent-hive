#!/usr/bin/env python3
"""
Migration Tools Test Script

Comprehensive testing of migration tools with all available agents.
Validates compatibility layer, migration manager, and rollback capabilities.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from migration_tools.compatibility_layer import TmuxMessageBridge, DualModeOperator
from migration_tools.migration_manager import MigrationManager, MigrationConfig, MigrationStrategy
from migration_tools.validation import MigrationValidator
from migration_tools.rollback import RollbackManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationTestSuite:
    """Comprehensive test suite for migration tools."""

    def __init__(self):
        self.bridge = None
        self.migration_manager = None
        self.validator = None
        self.rollback_manager = None
        self.test_results = []

    async def run_all_tests(self):
        """Run all migration tests."""
        logger.info("🚀 Starting Migration Tools Test Suite")

        try:
            # Initialize components
            await self._initialize_components()

            # Run test phases
            await self._test_compatibility_layer()
            await self._test_agent_discovery()
            await self._test_validation_framework()
            await self._test_migration_planning()
            await self._test_rollback_system()
            await self._test_end_to_end_migration()

            # Generate test report
            self._generate_test_report()

        except Exception as e:
            logger.error(f"❌ Test suite failed: {e}")
            raise
        finally:
            await self._cleanup_components()

    async def _initialize_components(self):
        """Initialize all migration components."""
        logger.info("🔧 Initializing migration components...")

        # Initialize bridge
        self.bridge = TmuxMessageBridge()
        await self.bridge.start(enable_message_bus=False)  # Tmux-only for testing

        # Initialize validator
        self.validator = MigrationValidator(self.bridge)

        # Initialize rollback manager
        self.rollback_manager = RollbackManager(self.bridge)
        await self.rollback_manager.start()

        # Initialize migration manager
        config = MigrationConfig(
            strategy=MigrationStrategy.GRADUAL,
            validation_timeout=60,
            monitoring_duration=30,  # Shortened for testing
            dry_run=True  # Safe testing mode
        )
        self.migration_manager = MigrationManager(config)
        await self.migration_manager.start()

        self._record_test_result("component_initialization", True, "All components initialized successfully")

    async def _test_compatibility_layer(self):
        """Test compatibility layer functionality."""
        logger.info("🔗 Testing compatibility layer...")

        try:
            # Test agent discovery
            agent_status = await self.bridge.get_agent_status()
            discovered_agents = len(agent_status.get("agents", {}))

            if discovered_agents > 0:
                self._record_test_result("agent_discovery", True, f"Discovered {discovered_agents} agents")
            else:
                self._record_test_result("agent_discovery", False, "No agents discovered")
                return

            # Test message sending to first agent
            first_agent = list(agent_status["agents"].keys())[0]
            message_success = await self.bridge.send_message(first_agent, "Test message from migration test")

            self._record_test_result("message_sending", message_success,
                                   f"Message sending to {first_agent}: {'success' if message_success else 'failed'}")

            # Test statistics collection
            stats = self.bridge.stats
            stats_available = len(stats) > 0
            self._record_test_result("statistics_collection", stats_available,
                                   f"Statistics collection: {dict(stats)}")

        except Exception as e:
            self._record_test_result("compatibility_layer", False, f"Compatibility layer test failed: {e}")

    async def _test_agent_discovery(self):
        """Test agent discovery across the system."""
        logger.info("🔍 Testing agent discovery...")

        try:
            # Discover agents
            discovery_result = await self.migration_manager.discover_agents()

            total_agents = discovery_result["total_agents"]
            migration_candidates = len(discovery_result["migration_candidates"])

            self._record_test_result("agent_discovery_comprehensive", total_agents > 0,
                                   f"Discovered {total_agents} agents, {migration_candidates} migration ready")

            # Test individual agent capabilities
            for agent_info in discovery_result["agents"]:
                agent_name = agent_info["name"]
                capabilities = agent_info["capabilities"]

                logger.info(f"  Agent {agent_name}: {capabilities}")

            self._record_test_result("agent_capabilities", True, "Agent capabilities assessed")

        except Exception as e:
            self._record_test_result("agent_discovery", False, f"Agent discovery failed: {e}")

    async def _test_validation_framework(self):
        """Test validation framework."""
        logger.info("✅ Testing validation framework...")

        try:
            # Test pre-migration validation
            pre_validation = await self.validator.validate_pre_migration_conditions()
            self._record_test_result("pre_migration_validation", pre_validation.passed,
                                   f"Pre-migration validation: {pre_validation.message}")

            # Test system resources validation
            resource_validation = await self.validator.validate_system_resources()
            self._record_test_result("resource_validation", resource_validation.passed,
                                   f"Resource validation: {resource_validation.message}")

            # Test agent connectivity validation
            agent_status = await self.bridge.get_agent_status()
            agents = list(agent_status.get("agents", {}).keys())

            if agents:
                connectivity_validation = await self.validator.validate_agent_connectivity(agents[:2])  # Test first 2
                self._record_test_result("connectivity_validation", connectivity_validation.passed,
                                       f"Connectivity validation: {connectivity_validation.message}")

        except Exception as e:
            self._record_test_result("validation_framework", False, f"Validation framework failed: {e}")

    async def _test_migration_planning(self):
        """Test migration planning capabilities."""
        logger.info("📋 Testing migration planning...")

        try:
            # Create migration plan
            plan = await self.migration_manager.create_migration_plan()

            plan_valid = plan is not None and "agents" in plan
            self._record_test_result("migration_planning", plan_valid,
                                   f"Migration plan created: {len(plan.get('agents', []))} agents, {plan.get('strategy')}")

            # Validate the plan
            if plan_valid:
                plan_validation = await self.validator.validate_migration_plan(plan)
                self._record_test_result("plan_validation", plan_validation.passed,
                                       f"Plan validation: {plan_validation.message}")

        except Exception as e:
            self._record_test_result("migration_planning", False, f"Migration planning failed: {e}")

    async def _test_rollback_system(self):
        """Test rollback system."""
        logger.info("🔄 Testing rollback system...")

        try:
            # Create safety checkpoint
            checkpoint_success = await self.rollback_manager.create_checkpoint("test_checkpoint", "testing")
            self._record_test_result("checkpoint_creation", checkpoint_success,
                                   f"Checkpoint creation: {'success' if checkpoint_success else 'failed'}")

            # List checkpoints
            checkpoints = await self.rollback_manager.list_checkpoints()
            checkpoint_list_valid = len(checkpoints) > 0
            self._record_test_result("checkpoint_listing", checkpoint_list_valid,
                                   f"Checkpoint listing: {len(checkpoints)} checkpoints")

            # Validate checkpoint
            if checkpoints:
                checkpoint_id = checkpoints[0]["checkpoint_id"]
                validation = await self.rollback_manager.validate_checkpoint(checkpoint_id)
                self._record_test_result("checkpoint_validation", validation["valid"],
                                       f"Checkpoint validation: {validation}")

            # Test rollback status
            status = self.rollback_manager.get_rollback_status()
            status_valid = "checkpoint_count" in status
            self._record_test_result("rollback_status", status_valid,
                                   f"Rollback status: {status['checkpoint_count']} checkpoints")

        except Exception as e:
            self._record_test_result("rollback_system", False, f"Rollback system failed: {e}")

    async def _test_end_to_end_migration(self):
        """Test end-to-end migration process (dry run)."""
        logger.info("🎯 Testing end-to-end migration (dry run)...")

        try:
            # Create migration plan
            plan = await self.migration_manager.create_migration_plan()

            if not plan:
                self._record_test_result("e2e_migration", False, "No migration plan available")
                return

            # Execute dry run migration
            execution_result = await self.migration_manager.execute_migration(dry_run=True)

            migration_success = execution_result["status"] in ["completed", "completed_with_issues"]
            self._record_test_result("e2e_migration_execution", migration_success,
                                   f"Migration execution: {execution_result['status']}")

            # Test migration health monitoring
            health_status = await self.migration_manager.monitor_migration_health()
            health_available = "overall_health" in health_status
            self._record_test_result("migration_monitoring", health_available,
                                   f"Health monitoring: {health_status.get('overall_health', 'unknown')}")

            # Test migration status
            status = self.migration_manager.get_migration_status()
            status_valid = "current_phase" in status
            self._record_test_result("migration_status", status_valid,
                                   f"Migration status: {status.get('current_phase', 'unknown')}")

        except Exception as e:
            self._record_test_result("e2e_migration", False, f"End-to-end migration failed: {e}")

    def _record_test_result(self, test_name: str, passed: bool, message: str):
        """Record a test result."""
        result = {
            "test": test_name,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)

        status_icon = "✅" if passed else "❌"
        logger.info(f"{status_icon} {test_name}: {message}")

    def _generate_test_report(self):
        """Generate comprehensive test report."""
        logger.info("📊 Generating test report...")

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["passed"])
        success_rate = passed_tests / total_tests if total_tests > 0 else 0

        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": success_rate,
                "timestamp": datetime.now().isoformat()
            },
            "test_results": self.test_results,
            "conclusions": self._generate_conclusions()
        }

        # Save report to file
        report_file = Path("migration_test_report.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        # Print summary
        logger.info(f"📈 Test Results Summary:")
        logger.info(f"   Total Tests: {total_tests}")
        logger.info(f"   Passed: {passed_tests}")
        logger.info(f"   Failed: {total_tests - passed_tests}")
        logger.info(f"   Success Rate: {success_rate:.1%}")
        logger.info(f"   Report saved to: {report_file}")

        # Print failed tests
        failed_tests = [r for r in self.test_results if not r["passed"]]
        if failed_tests:
            logger.warning("❌ Failed Tests:")
            for test in failed_tests:
                logger.warning(f"   - {test['test']}: {test['message']}")

        return report

    def _generate_conclusions(self):
        """Generate test conclusions and recommendations."""
        conclusions = []

        # Analyze test results
        passed_tests = [r for r in self.test_results if r["passed"]]
        failed_tests = [r for r in self.test_results if not r["passed"]]

        if len(passed_tests) == len(self.test_results):
            conclusions.append("✅ All migration tools are functioning correctly")
            conclusions.append("✅ System is ready for production migration")
        elif len(passed_tests) >= len(self.test_results) * 0.8:
            conclusions.append("⚠️ Most migration tools are working, but some issues need attention")
            conclusions.append("⚠️ Review failed tests before production migration")
        else:
            conclusions.append("❌ Significant issues found in migration tools")
            conclusions.append("❌ Do not proceed with production migration until issues are resolved")

        # Specific recommendations
        test_names = [r["test"] for r in self.test_results]

        if "agent_discovery" in [r["test"] for r in failed_tests]:
            conclusions.append("🔧 Fix agent discovery issues before migration")

        if "validation_framework" in [r["test"] for r in failed_tests]:
            conclusions.append("🔧 Validation framework needs repair")

        if "rollback_system" in [r["test"] for r in failed_tests]:
            conclusions.append("🔧 Rollback system is critical - fix before migration")

        return conclusions

    async def _cleanup_components(self):
        """Cleanup components after testing."""
        logger.info("🧹 Cleaning up components...")

        try:
            if self.migration_manager:
                await self.migration_manager.stop()

            if self.rollback_manager:
                await self.rollback_manager.stop()

            if self.bridge:
                await self.bridge.stop()

            logger.info("✅ Cleanup completed")

        except Exception as e:
            logger.warning(f"⚠️ Cleanup issues: {e}")


async def main():
    """Main test execution."""
    test_suite = MigrationTestSuite()

    try:
        await test_suite.run_all_tests()
        logger.info("🎉 Migration tools test suite completed successfully!")

    except Exception as e:
        logger.error(f"💥 Test suite failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
