#!/usr/bin/env python3
"""
Launch multi-agent documentation coordination using enhanced orchestration.

This script coordinates 5 specialized agents working in parallel on documentation
and tutorial implementation using the enhanced coordination protocols.
"""

import asyncio
import logging
import sys
from datetime import datetime

# Add the orchestration agent path
sys.path.append('/Users/bogdan/work/leanvibe-dev/agent-hive/worktrees/orchestration-agent')

from advanced_orchestration import EnhancedOrchestrationCLI
from advanced_orchestration.models import (
    CoordinatorConfig, ResourceLimits
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Launch multi-agent documentation coordination."""
    print("🚀 LAUNCHING MULTI-AGENT DOCUMENTATION COORDINATION")
    print("=" * 60)

    # Create enhanced coordinator configuration
    config = CoordinatorConfig(
        max_agents=5,
        min_agents=5,
        health_check_interval=30.0,
        load_balance_interval=60.0,
        enable_auto_scaling=True,
        resource_limits=ResourceLimits(
            max_agents=5,
            max_cpu_cores=8,
            max_memory_mb=8192,
            max_disk_mb=20480,
            max_network_mbps=1000
        )
    )

    # Initialize enhanced orchestration CLI
    cli = EnhancedOrchestrationCLI()

    try:
        # Step 1: Initialize the enhanced orchestration system
        print("\n📋 STEP 1: Initializing Enhanced Orchestration System")
        await cli.initialize(config.__dict__)
        print("✅ Enhanced orchestration system initialized")

        # Step 2: Register specialized agents
        print("\n👥 STEP 2: Registering Specialized Agents")

        # Use the built-in registration method
        await cli.register_specialized_agents()
        print("✅ All 5 specialized agents registered successfully:")
        print("  📝 Documentation Agent - documentation specialization")
        print("  🎓 Tutorial Agent - tutorial specialization")
        print("  🔗 Integration Agent - integration specialization")
        print("  🔍 Quality Agent - quality assurance specialization")
        print("  📦 Archive Agent - archival specialization")

        # Step 3: Create documentation workflow
        print("\n📋 STEP 3: Creating Documentation Workflow")

        # First create the workflow
        workflow_id = await cli.create_documentation_workflow()
        print(f"✅ Documentation workflow created: {workflow_id}")

        # Then execute it
        result = await cli.execute_workflow(workflow_id)
        print(f"📊 Workflow execution started: {result['status']}")
        print(f"🎯 Enhanced Features: {result['enhanced_features']}")

        # Step 4: Monitor execution
        print("\n📊 STEP 4: Monitoring Multi-Agent Execution")

        # Get system statistics
        stats_result = await cli.get_system_statistics()
        print("📊 System Statistics:")
        stats = stats_result['coordination_stats']
        print(f"  • Active workflows: {stats['active_workflows']}")
        print(f"  • Total tasks: {stats['total_tasks']}")
        print(f"  • Registered agents: {stats['registered_agents']}")

        # Get workflow status
        workflow_status = await cli.get_workflow_status(workflow_id)
        print("\n📋 Workflow Status:")
        print(f"  • Status: {workflow_status['status']}")
        print(f"  • Progress: {workflow_status['progress']:.1f}%")
        print(f"  • Active tasks: {len(workflow_status['active_tasks'])}")
        print(f"  • Completed tasks: {len(workflow_status['completed_tasks'])}")

        # Step 5: Report coordination status
        print("\n🎉 MULTI-AGENT COORDINATION LAUNCHED SUCCESSFULLY!")
        print("=" * 60)
        print("🚀 5 specialized agents now coordinating in parallel")
        print("🧠 Enhanced coordination protocols active")
        print("📊 Real-time monitoring and analytics enabled")
        print("🔄 Intelligent routing and dependency management operational")

        print(f"\n⏰ Coordination started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📋 Workflow ID: {result['workflow_id']}")
        print(f"🎯 Expected completion: {result.get('estimated_completion', 'calculating...')}")

        # Keep monitoring
        print("\n🔄 Entering continuous monitoring mode...")
        while True:
            await asyncio.sleep(60)  # Check every minute

            # Get updated metrics
            metrics_result = await cli.get_coordination_metrics()
            metrics = metrics_result['real_time_metrics']

            print(f"📊 [{datetime.now().strftime('%H:%M:%S')}] Coordination Status:")
            print(f"  • Workflow completion: {metrics['workflow_completion_rate']:.1%}")
            print(f"  • Parallel efficiency: {metrics['parallel_efficiency']:.1%}")
            print(f"  • Quality consistency: {metrics['quality_consistency']:.1%}")

            # Check for completion
            if metrics['workflow_completion_rate'] >= 0.95:
                print("🎉 DOCUMENTATION COORDINATION COMPLETED!")
                break

    except KeyboardInterrupt:
        print("\n⏹️  Coordination monitoring stopped by user")

    except Exception as e:
        print(f"\n❌ Error in coordination launch: {e}")
        logger.error(f"Coordination launch error: {e}", exc_info=True)

    finally:
        # Cleanup
        print("\n🧹 Shutting down enhanced orchestration system...")
        await cli.shutdown()
        print("✅ Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
