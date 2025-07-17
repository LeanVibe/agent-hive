#!/usr/bin/env python3
"""
Live Migration Test - Zero-Disruption Validation

Tests live migration of service-mesh-Jul-16-1221 agent with comprehensive
monitoring and validation to ensure zero workflow disruption.
"""

import asyncio
import json
import logging
import sys
import time
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


class LiveMigrationTest:
    """Live migration test for zero-disruption validation."""

    def __init__(self, target_agent="service-mesh-Jul-16-1221"):
        self.target_agent = target_agent
        self.bridge = None
        self.migration_manager = None
        self.validator = None
        self.rollback_manager = None
        self.test_results = []
        self.migration_phases = []

    async def run_live_migration_test(self):
        """Execute live migration test with comprehensive monitoring."""
        logger.info(f"🚀 Starting Live Migration Test - Target: {self.target_agent}")

        try:
            # Phase 1: Initialize and validate readiness
            await self._initialize_migration_system()
            await self._validate_agent_readiness()

            # Phase 2: Create safety checkpoint
            await self._create_pre_migration_checkpoint()

            # Phase 3: Execute gradual migration
            await self._execute_gradual_migration()

            # Phase 4: Validate zero-disruption success
            await self._validate_zero_disruption_success()

            # Phase 5: Test rollback capability (optional)
            await self._test_rollback_capability()

            # Generate comprehensive report
            self._generate_migration_report()

        except Exception as e:
            logger.error(f"❌ Live migration test failed: {e}")
            await self._emergency_rollback()
            raise
        finally:
            await self._cleanup_migration_system()

    async def _initialize_migration_system(self):
        """Initialize migration system components."""
        logger.info("🔧 Initializing migration system...")

        # Initialize bridge (tmux-only for safety)
        self.bridge = TmuxMessageBridge()
        await self.bridge.start(enable_message_bus=False)

        # Initialize validator
        self.validator = MigrationValidator(self.bridge)

        # Initialize rollback manager
        self.rollback_manager = RollbackManager(self.bridge)
        await self.rollback_manager.start()

        # Initialize migration manager with conservative settings
        config = MigrationConfig(
            strategy=MigrationStrategy.GRADUAL,
            validation_timeout=60,
            monitoring_duration=120,  # 2 minutes monitoring
            dry_run=False,  # LIVE MIGRATION
            backup_enabled=True,
            rollback_threshold=0.9  # High safety threshold
        )
        self.migration_manager = MigrationManager(config)
        await self.migration_manager.start()

        self._record_phase("system_initialization", True, "Migration system initialized successfully")

    async def _validate_agent_readiness(self):
        """Validate target agent is ready for migration."""
        logger.info(f"🔍 Validating {self.target_agent} readiness...")

        # Check agent exists and is accessible
        agent_status = await self.bridge.get_agent_status(self.target_agent)
        if "error" in agent_status:
            raise Exception(f"Agent {self.target_agent} not accessible: {agent_status['error']}")

        # Validate agent is in tmux mode
        if agent_status.get("mode") != "tmux":
            raise Exception(f"Agent {self.target_agent} not in tmux mode: {agent_status.get('mode')}")

        # Test message communication
        test_message = f"Pre-migration communication test - {datetime.now().isoformat()}"
        send_success = await self.bridge.send_message(self.target_agent, test_message)
        if not send_success:
            raise Exception(f"Failed to communicate with {self.target_agent}")

        # Validate agent capabilities
        capabilities = agent_status.get("capabilities", [])
        logger.info(f"  Agent capabilities: {capabilities}")

        # Check tmux availability
        tmux_available = agent_status.get("tmux_available", False)
        if not tmux_available:
            raise Exception(f"Tmux not available for {self.target_agent}")

        self._record_phase("agent_readiness", True,
                          f"Agent {self.target_agent} ready for migration - capabilities: {capabilities}")

    async def _create_pre_migration_checkpoint(self):
        """Create comprehensive safety checkpoint before migration."""
        logger.info("💾 Creating pre-migration safety checkpoint...")

        checkpoint_id = f"pre_migration_{self.target_agent}_{int(time.time())}"

        # Create checkpoint
        checkpoint_success = await self.rollback_manager.create_checkpoint(
            checkpoint_id,
            migration_phase="pre_migration"
        )

        if not checkpoint_success:
            raise Exception("Failed to create pre-migration checkpoint")

        # Validate checkpoint
        validation = await self.rollback_manager.validate_checkpoint(checkpoint_id)
        if not validation["valid"]:
            raise Exception(f"Checkpoint validation failed: {validation}")

        self.pre_migration_checkpoint = checkpoint_id
        self._record_phase("checkpoint_creation", True,
                          f"Safety checkpoint created: {checkpoint_id}")

    async def _execute_gradual_migration(self):
        """Execute gradual migration through all phases."""
        logger.info("🔄 Executing gradual migration...")

        # Phase 1: tmux → hybrid
        await self._migrate_to_hybrid_mode()

        # Phase 2: hybrid → message_bus (if message bus available)
        if self.bridge.message_bus:
            await self._migrate_to_message_bus_mode()
        else:
            logger.info("ℹ️ Message bus not available - testing hybrid mode only")

    async def _migrate_to_hybrid_mode(self):
        """Migrate agent to hybrid mode."""
        logger.info(f"📡 Migrating {self.target_agent} to hybrid mode...")

        # Record baseline performance
        baseline_start = time.time()
        baseline_test = await self.bridge.send_message(
            self.target_agent,
            f"Baseline test before hybrid migration - {datetime.now().isoformat()}"
        )
        baseline_time = time.time() - baseline_start

        # Migrate to hybrid
        migration_success = await self.bridge.migrate_agent(self.target_agent, "hybrid")
        if not migration_success:
            raise Exception(f"Failed to migrate {self.target_agent} to hybrid mode")

        # Test communication in hybrid mode
        hybrid_start = time.time()
        hybrid_test = await self.bridge.send_message(
            self.target_agent,
            f"Hybrid mode communication test - {datetime.now().isoformat()}"
        )
        hybrid_time = time.time() - hybrid_start

        # Validate agent status
        status = await self.bridge.get_agent_status(self.target_agent)
        if status.get("mode") != "hybrid":
            raise Exception(f"Agent mode not updated to hybrid: {status.get('mode')}")

        # Performance comparison
        performance_impact = hybrid_time - baseline_time
        logger.info(f"  Performance impact: {performance_impact:.3f}s")

        self._record_phase("hybrid_migration", True,
                          f"Successfully migrated to hybrid mode - performance impact: {performance_impact:.3f}s")

        # Monitor for stability
        await self._monitor_agent_stability("hybrid", duration=30)

    async def _migrate_to_message_bus_mode(self):
        """Migrate agent to full message bus mode."""
        logger.info(f"📨 Migrating {self.target_agent} to message bus mode...")

        # Record hybrid performance
        hybrid_start = time.time()
        hybrid_test = await self.bridge.send_message(
            self.target_agent,
            f"Pre-message-bus test - {datetime.now().isoformat()}"
        )
        hybrid_time = time.time() - hybrid_start

        # Migrate to message bus
        migration_success = await self.bridge.migrate_agent(self.target_agent, "message_bus")
        if not migration_success:
            logger.warning(f"Failed to migrate {self.target_agent} to message_bus mode - staying in hybrid")
            return

        # Test communication in message bus mode
        bus_start = time.time()
        bus_test = await self.bridge.send_message(
            self.target_agent,
            f"Message bus communication test - {datetime.now().isoformat()}"
        )
        bus_time = time.time() - bus_start

        # Validate agent status
        status = await self.bridge.get_agent_status(self.target_agent)
        if status.get("mode") != "message_bus":
            raise Exception(f"Agent mode not updated to message_bus: {status.get('mode')}")

        # Performance comparison
        performance_impact = bus_time - hybrid_time
        logger.info(f"  Performance impact: {performance_impact:.3f}s")

        self._record_phase("message_bus_migration", True,
                          f"Successfully migrated to message_bus mode - performance impact: {performance_impact:.3f}s")

        # Monitor for stability
        await self._monitor_agent_stability("message_bus", duration=30)

    async def _monitor_agent_stability(self, mode, duration=30):
        """Monitor agent stability in current mode."""
        logger.info(f"📊 Monitoring {self.target_agent} stability in {mode} mode for {duration}s...")

        start_time = time.time()
        test_count = 0
        success_count = 0
        response_times = []

        while time.time() - start_time < duration:
            test_start = time.time()
            test_message = f"Stability test {test_count + 1} in {mode} mode - {datetime.now().isoformat()}"

            success = await self.bridge.send_message(self.target_agent, test_message)
            response_time = time.time() - test_start

            test_count += 1
            if success:
                success_count += 1
                response_times.append(response_time)

            await asyncio.sleep(2)  # Test every 2 seconds

        # Calculate stability metrics
        success_rate = success_count / test_count if test_count > 0 else 0
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        logger.info(f"  Stability metrics: {success_count}/{test_count} success ({success_rate:.1%})")
        logger.info(f"  Average response time: {avg_response_time:.3f}s")

        # Check if stability meets requirements
        if success_rate < 0.95:  # 95% success rate required
            raise Exception(f"Agent stability below threshold: {success_rate:.1%}")

        self._record_phase(f"stability_{mode}", True,
                          f"Agent stable in {mode} mode - {success_rate:.1%} success rate, {avg_response_time:.3f}s avg response")

    async def _validate_zero_disruption_success(self):
        """Validate that migration achieved zero disruption."""
        logger.info("✅ Validating zero-disruption success...")

        # Get current agent status
        status = await self.bridge.get_agent_status(self.target_agent)

        # Check agent is responsive
        test_message = f"Post-migration validation - {datetime.now().isoformat()}"
        communication_success = await self.bridge.send_message(self.target_agent, test_message)

        if not communication_success:
            raise Exception("Post-migration communication failed")

        # Check migration statistics
        bridge_stats = self.bridge.stats
        failed_messages = bridge_stats.get("failed_messages", 0)
        total_messages = (
            bridge_stats.get("tmux_messages", 0) +
            bridge_stats.get("message_bus_messages", 0) +
            bridge_stats.get("bridge_messages", 0)
        )

        success_rate = (total_messages - failed_messages) / total_messages if total_messages > 0 else 1.0

        logger.info(f"  Overall message success rate: {success_rate:.1%}")
        logger.info(f"  Current agent mode: {status.get('mode', 'unknown')}")
        logger.info(f"  Agent capabilities maintained: {status.get('capabilities', [])}")

        # Validate zero disruption criteria
        if success_rate < 0.98:  # 98% success rate for zero disruption
            raise Exception(f"Message success rate below zero-disruption threshold: {success_rate:.1%}")

        self._record_phase("zero_disruption_validation", True,
                          f"Zero-disruption validated - {success_rate:.1%} success rate, agent fully operational")

    async def _test_rollback_capability(self):
        """Test rollback capability from current state."""
        logger.info("🔄 Testing rollback capability...")

        # Get current mode
        status = await self.bridge.get_agent_status(self.target_agent)
        current_mode = status.get("mode", "unknown")

        # Test rollback to tmux
        rollback_result = await self.rollback_manager.execute_rollback(
            checkpoint_id=self.pre_migration_checkpoint,
            reason="Testing rollback capability"
        )

        if rollback_result["status"] != "completed":
            logger.warning(f"Rollback test had issues: {rollback_result.get('errors', [])}")
        else:
            logger.info("✅ Rollback capability validated")

        # Validate agent is back in tmux mode
        post_rollback_status = await self.bridge.get_agent_status(self.target_agent)
        final_mode = post_rollback_status.get("mode", "unknown")

        # Test communication after rollback
        rollback_test = await self.bridge.send_message(
            self.target_agent,
            f"Post-rollback communication test - {datetime.now().isoformat()}"
        )

        self._record_phase("rollback_test", rollback_test and final_mode == "tmux",
                          f"Rollback test: {current_mode} → {final_mode}, communication: {'success' if rollback_test else 'failed'}")

    async def _emergency_rollback(self):
        """Execute emergency rollback on failure."""
        logger.critical("🚨 Executing emergency rollback...")

        try:
            if hasattr(self, 'pre_migration_checkpoint'):
                await self.rollback_manager.execute_rollback(
                    checkpoint_id=self.pre_migration_checkpoint,
                    reason="Emergency rollback due to migration failure"
                )
            else:
                # Manual rollback
                await self.bridge.migrate_agent(self.target_agent, "tmux")
        except Exception as e:
            logger.critical(f"Emergency rollback failed: {e}")

    def _record_phase(self, phase_name: str, success: bool, message: str):
        """Record migration phase result."""
        phase_result = {
            "phase": phase_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.migration_phases.append(phase_result)

        status_icon = "✅" if success else "❌"
        logger.info(f"{status_icon} {phase_name}: {message}")

    def _generate_migration_report(self):
        """Generate comprehensive migration test report."""
        logger.info("📊 Generating migration test report...")

        total_phases = len(self.migration_phases)
        successful_phases = sum(1 for phase in self.migration_phases if phase["success"])
        success_rate = successful_phases / total_phases if total_phases > 0 else 0

        report = {
            "migration_test_summary": {
                "target_agent": self.target_agent,
                "total_phases": total_phases,
                "successful_phases": successful_phases,
                "success_rate": success_rate,
                "zero_disruption_achieved": success_rate >= 0.95,
                "test_timestamp": datetime.now().isoformat()
            },
            "migration_phases": self.migration_phases,
            "bridge_statistics": dict(self.bridge.stats) if self.bridge else {},
            "final_agent_status": None,
            "recommendations": self._generate_recommendations()
        }

        # Get final agent status
        try:
            if self.bridge:
                final_status = asyncio.create_task(self.bridge.get_agent_status(self.target_agent))
                report["final_agent_status"] = final_status.result() if final_status.done() else "unavailable"
        except:
            report["final_agent_status"] = "error_retrieving_status"

        # Save report
        report_file = Path(f"live_migration_report_{self.target_agent}_{int(time.time())}.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        # Print summary
        logger.info(f"📈 Migration Test Results:")
        logger.info(f"   Target Agent: {self.target_agent}")
        logger.info(f"   Total Phases: {total_phases}")
        logger.info(f"   Successful: {successful_phases}")
        logger.info(f"   Success Rate: {success_rate:.1%}")
        logger.info(f"   Zero Disruption: {'✅ YES' if report['migration_test_summary']['zero_disruption_achieved'] else '❌ NO'}")
        logger.info(f"   Report saved: {report_file}")

        return report

    def _generate_recommendations(self):
        """Generate recommendations based on test results."""
        recommendations = []

        # Analyze phase results
        failed_phases = [phase for phase in self.migration_phases if not phase["success"]]

        if not failed_phases:
            recommendations.append("✅ All migration phases successful - ready for full rollout")
            recommendations.append("✅ Zero-disruption migration validated")
        else:
            recommendations.append(f"⚠️ {len(failed_phases)} phases failed - review before full rollout")
            for phase in failed_phases:
                recommendations.append(f"   - {phase['phase']}: {phase['message']}")

        # Performance recommendations
        bridge_stats = self.bridge.stats if self.bridge else {}
        failed_messages = bridge_stats.get("failed_messages", 0)

        if failed_messages > 0:
            recommendations.append(f"⚠️ {failed_messages} message failures detected - investigate reliability")

        return recommendations

    async def _cleanup_migration_system(self):
        """Cleanup migration system components."""
        logger.info("🧹 Cleaning up migration system...")

        try:
            if self.migration_manager:
                await self.migration_manager.stop()

            if self.rollback_manager:
                await self.rollback_manager.stop()

            if self.bridge:
                await self.bridge.stop()

            logger.info("✅ Migration system cleanup completed")

        except Exception as e:
            logger.warning(f"⚠️ Cleanup issues: {e}")


async def main():
    """Main execution for live migration test."""
    target_agent = "service-mesh-Jul-16-1221"

    test = LiveMigrationTest(target_agent)

    try:
        await test.run_live_migration_test()
        logger.info("🎉 Live migration test completed successfully!")

    except Exception as e:
        logger.error(f"💥 Live migration test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
