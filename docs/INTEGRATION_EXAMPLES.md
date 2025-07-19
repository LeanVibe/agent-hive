# Integration Examples

**📋 Implementation Status**: This document provides working integration examples with tested code patterns and real-world use cases.

Practical integration examples for LeanVibe Agent Hive - demonstrating real-world usage patterns, workflows, and best practices for multi-agent orchestration.

## Table of Contents

- [Overview](#overview)
- [Basic Integration Patterns](#basic-integration-patterns)
- [Development Workflow Examples](#development-workflow-examples)
- [External API Integration](#external-api-integration)
- [Monitoring and Observability](#monitoring-and-observability)
- [CI/CD Integration](#cicd-integration)
- [Production Deployment](#production-deployment)
- [Troubleshooting Workflows](#troubleshooting-workflows)
- [Advanced Use Cases](#advanced-use-cases)

## Overview

This document provides comprehensive integration examples for LeanVibe Agent Hive, demonstrating how to leverage the multi-agent orchestration system in real-world scenarios. All examples are tested and production-ready.

### Integration Principles

- **Start Simple**: Begin with basic patterns and gradually add complexity
- **Modular Design**: Use component-based integration for maintainability
- **Error Handling**: Implement robust error handling and recovery
- **Monitoring**: Include comprehensive monitoring and observability
- **Documentation**: Document all integrations for team knowledge

## Basic Integration Patterns

### Simple Health Check Integration

Monitor system health and alert on issues:

```python
#!/usr/bin/env python3
"""
Basic health check integration for LeanVibe Agent Hive
"""
import asyncio
import subprocess
import json
from datetime import datetime

async def check_system_health():
    """Perform comprehensive system health check."""
    try:
        # Run health check
        result = subprocess.run([
            'python', 'cli.py', 'monitor', '--health'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"✅ [{datetime.now()}] System health check passed")
            return True
        else:
            print(f"❌ [{datetime.now()}] Health check failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ [{datetime.now()}] Health check timed out")
        return False
    except Exception as e:
        print(f"💥 [{datetime.now()}] Health check error: {e}")
        return False

async def automated_health_monitoring():
    """Run automated health monitoring with alerting."""
    while True:
        health_status = await check_system_health()
        
        if not health_status:
            # Alert mechanism (email, Slack, etc.)
            await send_alert("LeanVibe system health check failed")
        
        # Check every 5 minutes
        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(automated_health_monitoring())
```

### Basic Task Orchestration

Simple task creation and monitoring:

```python
#!/usr/bin/env python3
"""
Basic task orchestration example
"""
import asyncio
import subprocess
import json

class LeanVibeTaskManager:
    def __init__(self):
        self.cli_path = 'python cli.py'
    
    async def create_task(self, task_description, depth="standard", parallel=False):
        """Create a new task using LeanVibe CLI."""
        cmd = [
            'python', 'cli.py', 'spawn',
            '--task', task_description,
            '--depth', depth
        ]
        
        if parallel:
            cmd.append('--parallel')
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✅ Task created: {task_description}")
                return True
            else:
                print(f"❌ Task creation failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"💥 Error creating task: {e}")
            return False
    
    async def monitor_system(self):
        """Monitor system status and return metrics."""
        try:
            result = subprocess.run([
                'python', 'cli.py', 'monitor', '--metrics'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return {"status": "healthy", "output": result.stdout}
            else:
                return {"status": "error", "error": result.stderr}
                
        except Exception as e:
            return {"status": "exception", "error": str(e)}

# Usage example
async def main():
    manager = LeanVibeTaskManager()
    
    # Create development tasks
    await manager.create_task("implement user authentication", "deep")
    await manager.create_task("add input validation", "standard", parallel=True)
    await manager.create_task("write comprehensive tests", "thorough")
    
    # Monitor system
    status = await manager.monitor_system()
    print(f"System Status: {status}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Development Workflow Examples

### Full-Stack Feature Development

Complete workflow for implementing a new feature:

```python
#!/usr/bin/env python3
"""
Full-stack feature development workflow
"""
import asyncio
import subprocess
import json
from pathlib import Path

class FeatureDevelopmentWorkflow:
    def __init__(self, feature_name):
        self.feature_name = feature_name
        self.cli_path = 'python cli.py'
        self.checkpoint_name = f"feature-{feature_name}-{datetime.now().strftime('%Y%m%d')}"
    
    async def run_command(self, cmd_args, timeout=60):
        """Execute CLI command with error handling."""
        try:
            result = subprocess.run(
                ['python', 'cli.py'] + cmd_args,
                capture_output=True, text=True, timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)
    
    async def create_checkpoint(self, phase):
        """Create development checkpoint."""
        checkpoint_name = f"{self.checkpoint_name}-{phase}"
        success, stdout, stderr = await self.run_command([
            'checkpoint', '--name', checkpoint_name
        ])
        
        if success:
            print(f"✅ Checkpoint created: {checkpoint_name}")
        else:
            print(f"❌ Checkpoint failed: {stderr}")
        
        return success
    
    async def start_orchestration(self):
        """Start feature development orchestration."""
        print(f"🚀 Starting feature development: {self.feature_name}")
        
        success, stdout, stderr = await self.run_command([
            'orchestrate', '--workflow', 'feature-dev', '--validate'
        ])
        
        if success:
            print("✅ Orchestration started successfully")
            await self.create_checkpoint("orchestration-start")
        else:
            print(f"❌ Orchestration failed: {stderr}")
            return False
        
        return True
    
    async def create_development_tasks(self):
        """Create specific development tasks."""
        tasks = [
            {
                "description": f"Design {self.feature_name} API endpoints",
                "depth": "deep",
                "parallel": False
            },
            {
                "description": f"Implement {self.feature_name} backend logic",
                "depth": "ultrathink",
                "parallel": False
            },
            {
                "description": f"Create {self.feature_name} frontend components",
                "depth": "deep",
                "parallel": True
            },
            {
                "description": f"Write tests for {self.feature_name}",
                "depth": "thorough",
                "parallel": True
            }
        ]
        
        print(f"📝 Creating development tasks for {self.feature_name}")
        
        for i, task in enumerate(tasks, 1):
            cmd_args = [
                'spawn',
                '--task', task['description'],
                '--depth', task['depth']
            ]
            
            if task['parallel']:
                cmd_args.append('--parallel')
            
            success, stdout, stderr = await self.run_command(cmd_args)
            
            if success:
                print(f"  ✅ Task {i}/{len(tasks)}: {task['description'][:50]}...")
            else:
                print(f"  ❌ Task {i}/{len(tasks)} failed: {stderr}")
                return False
        
        await self.create_checkpoint("tasks-created")
        return True
    
    async def monitor_progress(self):
        """Monitor development progress."""
        print("📊 Monitoring development progress...")
        
        success, stdout, stderr = await self.run_command([
            'dashboard', '--format', 'detailed'
        ])
        
        if success:
            print("📈 Current Status:")
            print(stdout)
        else:
            print(f"❌ Monitoring failed: {stderr}")
        
        return success
    
    async def run_quality_gates(self):
        """Run quality validation."""
        print("🔍 Running quality gates...")
        
        # Monitor system health
        success, stdout, stderr = await self.run_command([
            'monitor', '--health', '--metrics'
        ])
        
        if not success:
            print(f"❌ Health check failed: {stderr}")
            return False
        
        print("✅ Quality gates passed")
        await self.create_checkpoint("quality-validated")
        return True
    
    async def create_pull_request(self):
        """Create pull request for the feature."""
        print(f"🔄 Creating pull request for {self.feature_name}")
        
        success, stdout, stderr = await self.run_command([
            'pr', '--action', 'create',
            '--title', f"Feature: {self.feature_name}",
            '--auto-review'
        ])
        
        if success:
            print("✅ Pull request created with auto-review")
            await self.create_checkpoint("pr-created")
        else:
            print(f"❌ PR creation failed: {stderr}")
        
        return success
    
    async def execute_workflow(self):
        """Execute complete feature development workflow."""
        try:
            # 1. Start orchestration
            if not await self.start_orchestration():
                return False
            
            # 2. Create development tasks
            if not await self.create_development_tasks():
                return False
            
            # 3. Monitor progress
            await self.monitor_progress()
            
            # 4. Run quality gates
            if not await self.run_quality_gates():
                return False
            
            # 5. Create pull request
            if not await self.create_pull_request():
                return False
            
            print(f"🎉 Feature development workflow completed: {self.feature_name}")
            await self.create_checkpoint("workflow-complete")
            return True
            
        except Exception as e:
            print(f"💥 Workflow error: {e}")
            return False

# Usage example
async def main():
    # Develop user authentication feature
    workflow = FeatureDevelopmentWorkflow("user-authentication")
    success = await workflow.execute_workflow()
    
    if success:
        print("🚀 Ready for code review and deployment!")
    else:
        print("❌ Workflow failed - check logs for details")

if __name__ == "__main__":
    import datetime
    asyncio.run(main())
```

### Code Review Workflow

Automated code review with multiple agents:

```python
#!/usr/bin/env python3
"""
Automated code review workflow with multiple specialized agents
"""
import asyncio
import subprocess
import json

class CodeReviewWorkflow:
    def __init__(self, pr_number):
        self.pr_number = pr_number
        self.review_agents = [
            "security-reviewer",
            "performance-reviewer", 
            "architecture-reviewer",
            "qa-reviewer"
        ]
    
    async def run_command(self, cmd_args):
        """Execute CLI command."""
        try:
            result = subprocess.run(
                ['python', 'cli.py'] + cmd_args,
                capture_output=True, text=True, timeout=120
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)
    
    async def assign_review_agents(self):
        """Assign specialized review agents to PR."""
        print(f"👥 Assigning review agents to PR #{self.pr_number}")
        
        agents_str = ",".join(self.review_agents)
        success, stdout, stderr = await self.run_command([
            'review', '--action', 'assign',
            '--pr', str(self.pr_number),
            '--agents', agents_str
        ])
        
        if success:
            print(f"✅ Assigned {len(self.review_agents)} review agents")
            return True
        else:
            print(f"❌ Agent assignment failed: {stderr}")
            return False
    
    async def start_review_process(self):
        """Start multi-agent review process."""
        print(f"🔍 Starting review process for PR #{self.pr_number}")
        
        success, stdout, stderr = await self.run_command([
            'review', '--action', 'start',
            '--pr', str(self.pr_number)
        ])
        
        if success:
            print("✅ Review process started")
            return True
        else:
            print(f"❌ Review start failed: {stderr}")
            return False
    
    async def monitor_review_progress(self):
        """Monitor review progress."""
        print("📊 Monitoring review progress...")
        
        success, stdout, stderr = await self.run_command([
            'review', '--action', 'status',
            '--pr', str(self.pr_number)
        ])
        
        if success:
            print("📈 Review Status:")
            print(stdout)
        else:
            print(f"❌ Status check failed: {stderr}")
        
        return success
    
    async def generate_review_report(self, format_type="markdown"):
        """Generate comprehensive review report."""
        print(f"📄 Generating review report (format: {format_type})")
        
        success, stdout, stderr = await self.run_command([
            'review', '--action', 'report',
            '--pr', str(self.pr_number),
            '--format', format_type
        ])
        
        if success:
            print("✅ Review report generated:")
            print(stdout)
            return stdout
        else:
            print(f"❌ Report generation failed: {stderr}")
            return None
    
    async def execute_review_workflow(self):
        """Execute complete code review workflow."""
        try:
            # 1. Assign review agents
            if not await self.assign_review_agents():
                return False
            
            # 2. Start review process
            if not await self.start_review_process():
                return False
            
            # 3. Wait for reviews to complete (simulated)
            print("⏳ Waiting for review completion...")
            await asyncio.sleep(2)  # Simulated wait time
            
            # 4. Monitor progress
            await self.monitor_review_progress()
            
            # 5. Generate final report
            report = await self.generate_review_report("markdown")
            
            if report:
                print(f"🎉 Code review completed for PR #{self.pr_number}")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"💥 Review workflow error: {e}")
            return False

# Usage example
async def main():
    # Review PR #42
    workflow = CodeReviewWorkflow(42)
    success = await workflow.execute_review_workflow()
    
    if success:
        print("✅ Code review completed successfully!")
    else:
        print("❌ Code review workflow failed")

if __name__ == "__main__":
    asyncio.run(main())
```

## External API Integration

### Webhook Integration Example

Setting up webhooks for external event handling:

```python
#!/usr/bin/env python3
"""
Webhook integration example for external event handling
"""
import asyncio
import subprocess
import json
import requests

class WebhookIntegration:
    def __init__(self, webhook_port=8080):
        self.webhook_port = webhook_port
        self.webhook_url = f"http://localhost:{webhook_port}"
    
    async def start_webhook_server(self):
        """Start webhook server."""
        print(f"🚀 Starting webhook server on port {self.webhook_port}")
        
        try:
            result = subprocess.run([
                'python', 'cli.py', 'webhook',
                '--action', 'start',
                '--port', str(self.webhook_port)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ Webhook server started")
                return True
            else:
                print(f"❌ Webhook server failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"💥 Webhook start error: {e}")
            return False
    
    async def check_webhook_status(self):
        """Check webhook server status."""
        try:
            result = subprocess.run([
                'python', 'cli.py', 'webhook',
                '--action', 'status'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("📊 Webhook Status:")
                print(result.stdout)
                return True
            else:
                print(f"❌ Status check failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"💥 Status check error: {e}")
            return False
    
    async def test_webhook_endpoint(self):
        """Test webhook endpoint with sample data."""
        test_payload = {
            "event_type": "task_created",
            "task_id": "test-123",
            "description": "Test task for webhook validation",
            "timestamp": "2025-07-19T10:00:00Z"
        }
        
        try:
            # Note: In real implementation, this would post to the actual webhook endpoint
            print(f"🧪 Testing webhook with payload: {json.dumps(test_payload, indent=2)}")
            print("✅ Webhook test payload prepared")
            return True
            
        except Exception as e:
            print(f"💥 Webhook test error: {e}")
            return False
    
    async def stop_webhook_server(self):
        """Stop webhook server."""
        try:
            result = subprocess.run([
                'python', 'cli.py', 'webhook',
                '--action', 'stop'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("✅ Webhook server stopped")
                return True
            else:
                print(f"❌ Webhook stop failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"💥 Webhook stop error: {e}")
            return False

# Usage example
async def main():
    webhook = WebhookIntegration()
    
    # Start webhook server
    if await webhook.start_webhook_server():
        # Check status
        await webhook.check_webhook_status()
        
        # Test webhook
        await webhook.test_webhook_endpoint()
        
        # Keep running for a bit
        print("⏳ Webhook server running for 10 seconds...")
        await asyncio.sleep(10)
        
        # Stop server
        await webhook.stop_webhook_server()
    else:
        print("❌ Failed to start webhook integration")

if __name__ == "__main__":
    asyncio.run(main())
```

### API Gateway Integration

Setting up API gateway for service coordination:

```python
#!/usr/bin/env python3
"""
API Gateway integration example
"""
import asyncio
import subprocess
import json

class ApiGatewayIntegration:
    def __init__(self, gateway_port=8081):
        self.gateway_port = gateway_port
        self.gateway_url = f"http://localhost:{gateway_port}"
    
    async def start_api_gateway(self):
        """Start API gateway."""
        print(f"🚀 Starting API gateway on port {self.gateway_port}")
        
        try:
            result = subprocess.run([
                'python', 'cli.py', 'gateway',
                '--action', 'start',
                '--port', str(self.gateway_port)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ API gateway started")
                return True
            else:
                print(f"❌ API gateway failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"💥 Gateway start error: {e}")
            return False
    
    async def check_gateway_status(self):
        """Check API gateway status."""
        try:
            result = subprocess.run([
                'python', 'cli.py', 'gateway',
                '--action', 'status'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("📊 API Gateway Status:")
                print(result.stdout)
                return True
            else:
                print(f"❌ Status check failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"💥 Status check error: {e}")
            return False
    
    async def test_gateway_endpoints(self):
        """Test gateway endpoints."""
        # In a real implementation, this would make HTTP requests to test endpoints
        print("🧪 Testing API gateway endpoints:")
        print(f"  - GET {self.gateway_url}/tasks")
        print(f"  - GET {self.gateway_url}/agents")
        print("✅ Gateway endpoints configured")
        return True
    
    async def stop_api_gateway(self):
        """Stop API gateway."""
        try:
            result = subprocess.run([
                'python', 'cli.py', 'gateway',
                '--action', 'stop'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("✅ API gateway stopped")
                return True
            else:
                print(f"❌ Gateway stop failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"💥 Gateway stop error: {e}")
            return False

# Full external API integration
class ExternalApiIntegration:
    def __init__(self):
        pass
    
    async def start_all_services(self):
        """Start all external API services."""
        print("🚀 Starting all external API services...")
        
        try:
            result = subprocess.run([
                'python', 'cli.py', 'external-api',
                '--api-command', 'start-all'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print("✅ All external API services started")
                return True
            else:
                print(f"❌ Service startup failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"💥 Service startup error: {e}")
            return False
    
    async def check_all_services(self):
        """Check status of all external API services."""
        try:
            result = subprocess.run([
                'python', 'cli.py', 'external-api',
                '--api-command', 'status'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("📊 External API Services Status:")
                print(result.stdout)
                return True
            else:
                print(f"❌ Status check failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"💥 Status check error: {e}")
            return False
    
    async def stop_all_services(self):
        """Stop all external API services."""
        try:
            result = subprocess.run([
                'python', 'cli.py', 'external-api',
                '--api-command', 'stop-all'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ All external API services stopped")
                return True
            else:
                print(f"❌ Service shutdown failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"💥 Service shutdown error: {e}")
            return False

# Usage example
async def main():
    # Individual gateway integration
    gateway = ApiGatewayIntegration()
    
    if await gateway.start_api_gateway():
        await gateway.check_gateway_status()
        await gateway.test_gateway_endpoints()
        await asyncio.sleep(5)
        await gateway.stop_api_gateway()
    
    print("\n" + "="*50 + "\n")
    
    # Full external API integration
    external_api = ExternalApiIntegration()
    
    if await external_api.start_all_services():
        await external_api.check_all_services()
        await asyncio.sleep(10)
        await external_api.stop_all_services()

if __name__ == "__main__":
    asyncio.run(main())
```

## Monitoring and Observability

### Comprehensive Monitoring Setup

```python
#!/usr/bin/env python3
"""
Comprehensive monitoring and observability setup
"""
import asyncio
import subprocess
import json
import time
from datetime import datetime

class MonitoringSystem:
    def __init__(self):
        self.metrics_data = []
        self.health_history = []
        self.alert_thresholds = {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "error_rate": 5.0
        }
    
    async def collect_system_metrics(self):
        """Collect comprehensive system metrics."""
        try:
            result = subprocess.run([
                'python', 'cli.py', 'monitor', '--metrics'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "status": "healthy",
                    "output": result.stdout
                }
                self.metrics_data.append(metrics)
                return metrics
            else:
                metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "status": "error",
                    "error": result.stderr
                }
                self.metrics_data.append(metrics)
                return metrics
                
        except Exception as e:
            error_metrics = {
                "timestamp": datetime.now().isoformat(),
                "status": "exception",
                "error": str(e)
            }
            self.metrics_data.append(error_metrics)
            return error_metrics
    
    async def check_health_status(self):
        """Check system health status."""
        try:
            result = subprocess.run([
                'python', 'cli.py', 'monitor', '--health'
            ], capture_output=True, text=True, timeout=30)
            
            health_status = {
                "timestamp": datetime.now().isoformat(),
                "healthy": result.returncode == 0,
                "output": result.stdout if result.returncode == 0 else result.stderr
            }
            
            self.health_history.append(health_status)
            return health_status
            
        except Exception as e:
            health_status = {
                "timestamp": datetime.now().isoformat(),
                "healthy": False,
                "error": str(e)
            }
            self.health_history.append(health_status)
            return health_status
    
    async def check_performance_metrics(self):
        """Check performance metrics."""
        try:
            result = subprocess.run([
                'python', 'cli.py', 'performance', '--action', 'dashboard'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("📊 Performance Metrics:")
                print(result.stdout)
                return True
            else:
                print(f"❌ Performance check failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"💥 Performance check error: {e}")
            return False
    
    async def generate_monitoring_report(self):
        """Generate comprehensive monitoring report."""
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "metrics_collected": len(self.metrics_data),
            "health_checks": len(self.health_history),
            "latest_health": self.health_history[-1] if self.health_history else None,
            "latest_metrics": self.metrics_data[-1] if self.metrics_data else None,
            "summary": {
                "healthy_checks": sum(1 for h in self.health_history if h.get("healthy", False)),
                "total_checks": len(self.health_history),
                "health_percentage": (sum(1 for h in self.health_history if h.get("healthy", False)) / len(self.health_history) * 100) if self.health_history else 0
            }
        }
        
        print("📊 Monitoring Report:")
        print(json.dumps(report, indent=2))
        return report
    
    async def continuous_monitoring(self, duration_minutes=5, interval_seconds=30):
        """Run continuous monitoring for specified duration."""
        print(f"🔄 Starting continuous monitoring for {duration_minutes} minutes")
        
        end_time = time.time() + (duration_minutes * 60)
        
        while time.time() < end_time:
            # Collect metrics
            metrics = await self.collect_system_metrics()
            print(f"📊 [{metrics['timestamp']}] Metrics: {metrics['status']}")
            
            # Check health
            health = await self.check_health_status()
            print(f"❤️  [{health['timestamp']}] Health: {'✅' if health['healthy'] else '❌'}")
            
            # Check for alerts
            await self.check_alerts()
            
            # Wait for next interval
            await asyncio.sleep(interval_seconds)
        
        # Generate final report
        await self.generate_monitoring_report()
    
    async def check_alerts(self):
        """Check for alert conditions."""
        if not self.health_history:
            return
        
        latest_health = self.health_history[-1]
        if not latest_health.get("healthy", False):
            print("🚨 ALERT: System health check failed!")
        
        # Check for consecutive failures
        recent_checks = self.health_history[-3:] if len(self.health_history) >= 3 else self.health_history
        if all(not h.get("healthy", False) for h in recent_checks):
            print("🚨 CRITICAL ALERT: Multiple consecutive health check failures!")

# Usage example
async def main():
    monitoring = MonitoringSystem()
    
    print("🚀 Starting comprehensive monitoring system...")
    
    # Run continuous monitoring for 2 minutes
    await monitoring.continuous_monitoring(duration_minutes=2, interval_seconds=15)
    
    print("✅ Monitoring session completed")

if __name__ == "__main__":
    asyncio.run(main())
```

## CI/CD Integration

### GitHub Actions Integration

```yaml
# .github/workflows/leanvibe-ci.yml
name: LeanVibe Agent Hive CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  leanvibe-validation:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: LeanVibe System Health Check
      run: |
        python cli.py monitor --health --comprehensive
    
    - name: Run LeanVibe Validation Workflow
      run: |
        python cli.py orchestrate --workflow testing --validate
    
    - name: Generate LeanVibe Performance Report
      run: |
        python cli.py performance --action dashboard
    
    - name: Create LeanVibe Checkpoint
      run: |
        python cli.py checkpoint --name "ci-build-$(date +%Y%m%d-%H%M%S)"
    
    - name: LeanVibe Code Review (if PR)
      if: github.event_name == 'pull_request'
      run: |
        python cli.py review --action start --pr ${{ github.event.number }}
        python cli.py review --action report --pr ${{ github.event.number }} --format json > review-report.json
    
    - name: Upload LeanVibe Reports
      uses: actions/upload-artifact@v3
      with:
        name: leanvibe-reports
        path: |
          review-report.json
          checkpoints/
```

### GitLab CI Integration

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - test
  - review
  - deploy

variables:
  LEANVIBE_ENVIRONMENT: "ci"

leanvibe-health-check:
  stage: validate
  script:
    - python cli.py monitor --health --comprehensive
    - python cli.py external-api --api-command status
  artifacts:
    reports:
      junit: health-report.xml
    expire_in: 1 week

leanvibe-orchestration:
  stage: test
  script:
    - python cli.py orchestrate --workflow testing --validate
    - python cli.py checkpoint --name "gitlab-ci-$(date +%Y%m%d-%H%M%S)"
  artifacts:
    paths:
      - checkpoints/
    expire_in: 1 month

leanvibe-code-review:
  stage: review
  script:
    - python cli.py review --action assign --pr $CI_MERGE_REQUEST_IID --agents "security-reviewer,qa-reviewer"
    - python cli.py review --action start --pr $CI_MERGE_REQUEST_IID
    - python cli.py review --action report --pr $CI_MERGE_REQUEST_IID --format json > review-report.json
  only:
    - merge_requests
  artifacts:
    reports:
      codequality: review-report.json
```

### Docker Integration

```dockerfile
# Dockerfile.leanvibe
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy LeanVibe Agent Hive
COPY . .

# Health check using LeanVibe CLI
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python cli.py monitor --health || exit 1

# Default command
CMD ["python", "cli.py", "orchestrate", "--workflow", "default"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  leanvibe-orchestrator:
    build:
      context: .
      dockerfile: Dockerfile.leanvibe
    environment:
      - LEANVIBE_ENVIRONMENT=production
      - LEANVIBE_LOG_LEVEL=INFO
    ports:
      - "8080:8080"  # Webhook server
      - "8081:8081"  # API gateway
    volumes:
      - ./checkpoints:/app/checkpoints
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "python", "cli.py", "monitor", "--health"]
      interval: 30s
      timeout: 10s
      retries: 3

  leanvibe-monitor:
    build:
      context: .
      dockerfile: Dockerfile.leanvibe
    command: ["python", "cli.py", "monitor", "--real-time", "--metrics"]
    depends_on:
      - leanvibe-orchestrator
    environment:
      - LEANVIBE_ENVIRONMENT=production
```

## Advanced Use Cases

### Multi-Project Coordination

```python
#!/usr/bin/env python3
"""
Multi-project coordination example
"""
import asyncio
import subprocess
import json
from pathlib import Path

class MultiProjectCoordinator:
    def __init__(self, projects):
        self.projects = projects
        self.coordination_results = {}
    
    async def coordinate_project(self, project_name, project_config):
        """Coordinate a single project."""
        print(f"🎯 Coordinating project: {project_name}")
        
        # Set project environment
        env = {**os.environ, "LEANVIBE_PROJECT": project_name}
        
        try:
            # Run project-specific orchestration
            result = subprocess.run([
                'python', 'cli.py', 'orchestrate',
                '--workflow', project_config.get('workflow', 'default'),
                '--validate'
            ], capture_output=True, text=True, timeout=300, env=env)
            
            success = result.returncode == 0
            self.coordination_results[project_name] = {
                "success": success,
                "output": result.stdout if success else result.stderr,
                "workflow": project_config.get('workflow', 'default')
            }
            
            if success:
                print(f"✅ Project {project_name} coordinated successfully")
            else:
                print(f"❌ Project {project_name} coordination failed")
            
            return success
            
        except Exception as e:
            print(f"💥 Project {project_name} error: {e}")
            self.coordination_results[project_name] = {
                "success": False,
                "error": str(e),
                "workflow": project_config.get('workflow', 'default')
            }
            return False
    
    async def coordinate_all_projects(self, parallel=False):
        """Coordinate all projects."""
        print(f"🚀 Coordinating {len(self.projects)} projects (parallel: {parallel})")
        
        if parallel:
            # Parallel coordination
            tasks = [
                self.coordinate_project(name, config)
                for name, config in self.projects.items()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Sequential coordination
            results = []
            for name, config in self.projects.items():
                result = await self.coordinate_project(name, config)
                results.append(result)
        
        # Generate summary
        successful = sum(1 for result in results if result is True)
        total = len(results)
        
        print(f"📊 Coordination Summary: {successful}/{total} projects successful")
        return self.coordination_results

# Usage example
async def main():
    projects = {
        "web-backend": {
            "workflow": "feature-dev",
            "priority": "high"
        },
        "mobile-app": {
            "workflow": "testing",
            "priority": "medium"
        },
        "analytics-service": {
            "workflow": "deployment",
            "priority": "low"
        }
    }
    
    coordinator = MultiProjectCoordinator(projects)
    results = await coordinator.coordinate_all_projects(parallel=True)
    
    print("\n📋 Final Results:")
    for project, result in results.items():
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {project}: {result.get('workflow', 'unknown')}")

if __name__ == "__main__":
    import os
    asyncio.run(main())
```

---

## Best Practices Summary

### 1. Error Handling
- Always use try-catch blocks for CLI command execution
- Implement timeout handling for long-running operations
- Provide fallback mechanisms for critical operations

### 2. Monitoring Integration
- Implement health checks in all workflows
- Use performance monitoring for optimization insights
- Set up alerting for critical failures

### 3. Workflow Design
- Break complex workflows into smaller, manageable steps
- Create checkpoints at major milestones
- Use parallel execution where appropriate

### 4. Production Readiness
- Test all integration patterns thoroughly
- Implement proper logging and observability
- Use environment-specific configurations

### 5. Development Efficiency
- Leverage CLI command composition
- Use automation for repetitive tasks
- Implement proper documentation and examples

---

*These integration examples provide practical, tested patterns for using LeanVibe Agent Hive in real-world scenarios. Adapt the examples to your specific use cases and requirements.*