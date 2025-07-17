#!/usr/bin/env python3
"""
Production Monitoring Framework Demo.

Demonstrates the complete monitoring system with:
- Agent-level business metrics
- Proactive alerting with anomaly detection
- Distributed tracing for workflows
- Integrated health monitoring
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
import random

from monitoring_integration_framework import MonitoringIntegrationFramework
from business_metrics_monitor import BusinessMetricType
from distributed_tracing_system import WorkflowType


async def main():
    """Demonstrate the complete monitoring framework."""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    print("🚀 Production Monitoring Framework Demo")
    print("=" * 50)
    
    # Initialize monitoring framework
    monitoring = MonitoringIntegrationFramework("demo-agent-hive")
    
    try:
        # Initialize all components
        print("\n📊 Initializing monitoring framework...")
        await monitoring.initialize()
        
        # Wait for systems to stabilize
        await asyncio.sleep(2)
        
        # Validate integration
        print("\n🔍 Validating integration...")
        validation = monitoring.validate_integration()
        print(f"Validation Status: {validation['validation_status']}")
        
        for component, status in validation['checks'].items():
            print(f"  {component}: {status}")
        
        # Demonstrate workflow monitoring
        print("\n🔄 Demonstrating workflow monitoring...")
        
        # Start multiple workflows
        workflows = []
        for i in range(3):
            workflow_id = f"demo_workflow_{i}"
            agents = [f"agent_{j}" for j in range(2, 5)]
            
            trace_id = monitoring.start_workflow_monitoring(
                workflow_id, "task_execution", agents
            )
            workflows.append((workflow_id, agents))
            print(f"  Started workflow {workflow_id} (trace: {trace_id[:8]}...)")
        
        # Simulate agent activities
        print("\n🤖 Simulating agent activities...")
        
        for round_num in range(5):
            print(f"  Round {round_num + 1}/5...")
            
            # Simulate tasks
            for workflow_id, agents in workflows:
                for agent_id in agents:
                    task_id = f"task_{round_num}_{agent_id}"
                    success = random.random() > 0.1  # 90% success rate
                    duration = random.uniform(0.5, 3.0)
                    
                    monitoring.record_agent_task(
                        agent_id, task_id, "processing", success, duration
                    )
            
            # Simulate some conflicts
            if round_num % 2 == 0:
                conflict_agents = random.sample([f"agent_{i}" for i in range(2, 5)], 2)
                monitoring.record_conflict_resolution(
                    f"conflict_{round_num}", conflict_agents, 
                    random.uniform(1.0, 5.0), True
                )
            
            await asyncio.sleep(1)
        
        # Complete workflows
        print("\n✅ Completing workflows...")
        for workflow_id, _ in workflows:
            status = "completed" if random.random() > 0.2 else "failed"
            monitoring.complete_workflow_monitoring(workflow_id, status)
            print(f"  {workflow_id}: {status}")
        
        # Generate some load to trigger alerts
        print("\n⚠️  Generating system load for alerting demo...")
        
        # Simulate high resource usage
        high_load_metrics = {
            "cpu_percent": 95.0,
            "memory_percent": 92.0,
            "error_rate": 0.15,
            "task_throughput": 1.0  # Very low
        }
        
        monitoring.proactive_alerting.process_metrics(high_load_metrics)
        
        await asyncio.sleep(2)
        
        # Show comprehensive dashboard
        print("\n📈 Comprehensive Monitoring Dashboard:")
        print("=" * 50)
        
        dashboard = monitoring.get_comprehensive_dashboard()
        
        # Framework status
        framework_status = dashboard["monitoring_framework"]
        print(f"\n🔧 Framework Status: {framework_status['status']}")
        print(f"   Uptime: {framework_status['uptime_seconds']:.1f}s")
        print(f"   Metrics Processed: {framework_status['metrics_processed']}")
        print(f"   Alerts Generated: {framework_status['alerts_generated']}")
        print(f"   Traces Completed: {framework_status['traces_completed']}")
        
        # Component health
        print(f"\n🩺 Component Health:")
        for component, healthy in framework_status["component_health"].items():
            status = "✅ Healthy" if healthy else "❌ Unhealthy"
            print(f"   {component}: {status}")
        
        # Business metrics
        business = dashboard["business_metrics"]
        print(f"\n💼 Business Metrics:")
        print(f"   Active Tasks: {business.get('active_tasks', 0)}")
        print(f"   Active Conflicts: {business.get('active_conflicts', 0)}")
        print(f"   Hourly Throughput: {business.get('total_hourly_throughput', 0)}")
        print(f"   System Health: {business.get('system_health', 'unknown')}")
        
        # Alerts
        alerts = dashboard["alerts"]
        print(f"\n🚨 Alerts:")
        print(f"   Active Alerts: {alerts['summary'].get('active_alerts_total', 0)}")
        print(f"   Critical: {alerts['summary'].get('active_by_level', {}).get('critical', 0)}")
        print(f"   Warning: {alerts['summary'].get('active_by_level', {}).get('warning', 0)}")
        print(f"   Predictive Alerts: {alerts.get('predictive_alerts', 0)}")
        
        # Distributed tracing
        tracing = dashboard["distributed_tracing"]
        print(f"\n🔍 Distributed Tracing:")
        print(f"   Active Workflows: {tracing.get('active_workflows', 0)}")
        print(f"   Active Agents: {tracing.get('active_agents', 0)}")
        print(f"   Total Spans: {tracing.get('total_spans_tracked', 0)}")
        print(f"   Success Rate: {tracing.get('workflow_success_rate', 0):.1%}")
        
        # System health
        health = dashboard["system_health"]
        print(f"\n💚 System Health:")
        print(f"   Overall Score: {health.get('overall_score', 0):.2f}")
        print(f"   Status: {health.get('status', 'unknown')}")
        
        if health.get('recommendations'):
            print(f"   Recommendations:")
            for rec in health['recommendations'][:3]:
                print(f"     • {rec}")
        
        # System metrics
        system = dashboard["system_metrics"]
        print(f"\n💻 System Metrics:")
        print(f"   CPU: {system.get('cpu_percent', 0):.1f}%")
        print(f"   Memory: {system.get('memory_percent', 0):.1f}%")
        print(f"   Disk: {system.get('disk_percent', 0):.1f}%")
        
        # Demonstrate agent performance
        print(f"\n👤 Agent Performance:")
        for i in range(2, 5):
            agent_id = f"agent_{i}"
            perf = monitoring.get_agent_performance(agent_id)
            throughput = perf["throughput"]
            tracing_data = perf["tracing"]
            
            print(f"   {agent_id}:")
            print(f"     Throughput: {throughput.get('throughput_per_hour', 0):.1f} tasks/hr ({throughput.get('status', 'unknown')})")
            print(f"     Success Rate: {tracing_data.get('success_rate', 0):.1%}")
            print(f"     Avg Duration: {tracing_data.get('avg_span_duration', 0):.2f}s")
        
        # Show active predictive alerts
        predictive_alerts = monitoring.proactive_alerting.get_active_predictive_alerts()
        if predictive_alerts:
            print(f"\n🔮 Predictive Alerts:")
            for alert in predictive_alerts[:3]:  # Show top 3
                print(f"   {alert.severity.value.upper()}: {alert.metric_name}")
                print(f"     Current: {alert.current_value:.2f} → Predicted: {alert.predicted_value:.2f}")
                print(f"     Confidence: {alert.confidence:.1%}")
                print(f"     Recommendation: {alert.recommendation}")
        
        print(f"\n🎉 Demo completed successfully!")
        print(f"📊 Monitoring framework is production-ready with:")
        print(f"   ✅ Agent-level business metrics")
        print(f"   ✅ Proactive alerting with ML-based anomaly detection")
        print(f"   ✅ Distributed tracing for end-to-end visibility")
        print(f"   ✅ Integrated health monitoring")
        print(f"   ✅ Real-time dashboards and APIs")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
    
    finally:
        # Cleanup
        print(f"\n🧹 Shutting down monitoring framework...")
        await monitoring.shutdown()
        print(f"✅ Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())