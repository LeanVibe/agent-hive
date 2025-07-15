"""
CLI Integration for Enhanced Multi-Agent Orchestration.

This module provides CLI commands for managing and executing multi-agent workflows
with the enhanced coordination capabilities.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import click

from .workflow_coordinator import WorkflowCoordinator
from .models import (
    WorkflowDefinition, AgentCapabilities, QualityGate, TaskDependency,
    WorkflowType, AgentSpecialization, TaskPriority, DependencyType,
    CoordinatorConfig, ResourceLimits, IntelligentRouting
)


class OrchestrationCLI:
    """CLI interface for enhanced multi-agent orchestration."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.workflow_coordinator: Optional[WorkflowCoordinator] = None
        self.running = False
    
    async def initialize(self, config: Dict[str, Any] = None) -> None:
        """Initialize the orchestration system."""
        try:
            # Create configuration
            coordinator_config = CoordinatorConfig(
                max_agents=config.get('max_agents', 10) if config else 10,
                min_agents=config.get('min_agents', 2) if config else 2,
                health_check_interval=config.get('health_check_interval', 30.0) if config else 30.0,
                load_balance_interval=config.get('load_balance_interval', 60.0) if config else 60.0,
                enable_auto_scaling=config.get('enable_auto_scaling', True) if config else True,
                resource_limits=ResourceLimits(
                    max_agents=config.get('max_agents', 10) if config else 10,
                    max_cpu_cores=config.get('max_cpu_cores', 8) if config else 8,
                    max_memory_mb=config.get('max_memory_mb', 8192) if config else 8192
                )
            )
            
            # Initialize workflow coordinator
            self.workflow_coordinator = WorkflowCoordinator(coordinator_config)
            await self.workflow_coordinator.start()
            self.running = True
            
            self.logger.info("Enhanced multi-agent orchestration system initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize orchestration system: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the orchestration system."""
        if self.workflow_coordinator:
            await self.workflow_coordinator.stop()
            self.running = False
            self.logger.info("Orchestration system shutdown complete")
    
    async def create_documentation_workflow(self, workflow_id: str = None) -> str:
        """Create the documentation workflow from the plan."""
        if not self.workflow_coordinator:
            raise RuntimeError("Orchestration system not initialized")
        
        workflow_id = workflow_id or f"documentation-workflow-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Create workflow definition based on the plan
        workflow_def = WorkflowDefinition(
            workflow_id=workflow_id,
            workflow_type=WorkflowType.DOCUMENTATION,
            name="Comprehensive Documentation & Tutorial Implementation",
            description="Multi-agent parallel coordination for documentation and tutorial creation",
            tasks=[
                # Track A: Documentation Audit & Updates
                "A.1.1-documentation-inventory",
                "A.1.2-categorize-documents",
                "A.1.3-create-archive-structure",
                "A.1.4-update-readme-index",
                "A.2.1-update-api-reference",
                "A.2.2-enhance-deployment-docs",
                "A.2.3-expand-troubleshooting",
                "A.2.4-modernize-development-docs",
                
                # Track B: Medium Clone Tutorial
                "B.1.1-tutorial-environment-setup",
                "B.1.2-project-initialization",
                "B.2.1-user-authentication-system",
                "B.2.2-article-management-system",
                "B.2.3-social-features-realtime",
                "B.3.1-docker-containerization",
                "B.3.2-monitoring-observability",
                "B.3.3-cicd-pipeline",
                "B.3.4-tutorial-validation",
                
                # Track C: Agent Integration Guide
                "C.1.1-repository-setup-docs",
                "C.1.2-project-integration-config",
                "C.1.3-git-hooks-setup",
                "C.1.4-agent-specialization-config",
                "C.2.1-cli-commands-reference",
                "C.2.2-workflow-coordination-patterns",
                "C.2.3-prompt-engineering-guide",
                "C.2.4-validation-examples",
                
                # Track D: Quality Assurance
                "D.1.1-documentation-validation",
                "D.1.2-code-example-testing",
                "D.1.3-link-validation",
                "D.1.4-accuracy-verification",
                "D.2.1-fresh-environment-testing",
                "D.2.2-step-by-step-validation",
                "D.2.3-performance-benchmarking",
                "D.2.4-troubleshooting-testing",
                
                # Track E: Archive & Maintenance
                "E.1.1-archive-historical-docs",
                "E.1.2-cleanup-duplicates",
                "E.1.3-create-archive-structure",
                "E.1.4-update-git-history",
                "E.2.1-automated-update-triggers",
                "E.2.2-community-feedback-integration",
                "E.2.3-version-sync-monitoring",
                "E.2.4-sustainability-planning"
            ],
            dependencies=[
                # Track A dependencies
                TaskDependency("A.1.2-categorize-documents", "A.1.1-documentation-inventory", DependencyType.BLOCKING),
                TaskDependency("A.1.3-create-archive-structure", "A.1.2-categorize-documents", DependencyType.BLOCKING),
                TaskDependency("A.1.4-update-readme-index", "A.1.3-create-archive-structure", DependencyType.BLOCKING),
                TaskDependency("A.2.1-update-api-reference", "A.1.4-update-readme-index", DependencyType.SOFT),
                TaskDependency("A.2.2-enhance-deployment-docs", "A.2.1-update-api-reference", DependencyType.SOFT),
                TaskDependency("A.2.3-expand-troubleshooting", "A.2.2-enhance-deployment-docs", DependencyType.SOFT),
                TaskDependency("A.2.4-modernize-development-docs", "A.2.3-expand-troubleshooting", DependencyType.SOFT),
                
                # Track B dependencies
                TaskDependency("B.1.2-project-initialization", "B.1.1-tutorial-environment-setup", DependencyType.BLOCKING),
                TaskDependency("B.2.1-user-authentication-system", "B.1.2-project-initialization", DependencyType.BLOCKING),
                TaskDependency("B.2.2-article-management-system", "B.2.1-user-authentication-system", DependencyType.BLOCKING),
                TaskDependency("B.2.3-social-features-realtime", "B.2.2-article-management-system", DependencyType.BLOCKING),
                TaskDependency("B.3.1-docker-containerization", "B.2.3-social-features-realtime", DependencyType.BLOCKING),
                TaskDependency("B.3.2-monitoring-observability", "B.3.1-docker-containerization", DependencyType.BLOCKING),
                TaskDependency("B.3.3-cicd-pipeline", "B.3.2-monitoring-observability", DependencyType.BLOCKING),
                TaskDependency("B.3.4-tutorial-validation", "B.3.3-cicd-pipeline", DependencyType.BLOCKING),
                
                # Track C dependencies
                TaskDependency("C.1.2-project-integration-config", "C.1.1-repository-setup-docs", DependencyType.BLOCKING),
                TaskDependency("C.1.3-git-hooks-setup", "C.1.2-project-integration-config", DependencyType.BLOCKING),
                TaskDependency("C.1.4-agent-specialization-config", "C.1.3-git-hooks-setup", DependencyType.BLOCKING),
                TaskDependency("C.2.1-cli-commands-reference", "C.1.4-agent-specialization-config", DependencyType.BLOCKING),
                TaskDependency("C.2.2-workflow-coordination-patterns", "C.2.1-cli-commands-reference", DependencyType.BLOCKING),
                TaskDependency("C.2.3-prompt-engineering-guide", "C.2.2-workflow-coordination-patterns", DependencyType.BLOCKING),
                TaskDependency("C.2.4-validation-examples", "C.2.3-prompt-engineering-guide", DependencyType.BLOCKING),
                
                # Track D dependencies (validation tasks depend on respective track completions)
                TaskDependency("D.1.1-documentation-validation", "A.2.4-modernize-development-docs", DependencyType.SOFT),
                TaskDependency("D.1.2-code-example-testing", "D.1.1-documentation-validation", DependencyType.BLOCKING),
                TaskDependency("D.1.3-link-validation", "D.1.2-code-example-testing", DependencyType.BLOCKING),
                TaskDependency("D.1.4-accuracy-verification", "D.1.3-link-validation", DependencyType.BLOCKING),
                TaskDependency("D.2.1-fresh-environment-testing", "B.3.4-tutorial-validation", DependencyType.SOFT),
                TaskDependency("D.2.2-step-by-step-validation", "D.2.1-fresh-environment-testing", DependencyType.BLOCKING),
                TaskDependency("D.2.3-performance-benchmarking", "D.2.2-step-by-step-validation", DependencyType.BLOCKING),
                TaskDependency("D.2.4-troubleshooting-testing", "D.2.3-performance-benchmarking", DependencyType.BLOCKING),
                
                # Track E dependencies
                TaskDependency("E.1.2-cleanup-duplicates", "E.1.1-archive-historical-docs", DependencyType.BLOCKING),
                TaskDependency("E.1.3-create-archive-structure", "E.1.2-cleanup-duplicates", DependencyType.BLOCKING),
                TaskDependency("E.1.4-update-git-history", "E.1.3-create-archive-structure", DependencyType.BLOCKING),
                TaskDependency("E.2.1-automated-update-triggers", "E.1.4-update-git-history", DependencyType.BLOCKING),
                TaskDependency("E.2.2-community-feedback-integration", "E.2.1-automated-update-triggers", DependencyType.BLOCKING),
                TaskDependency("E.2.3-version-sync-monitoring", "E.2.2-community-feedback-integration", DependencyType.BLOCKING),
                TaskDependency("E.2.4-sustainability-planning", "E.2.3-version-sync-monitoring", DependencyType.BLOCKING),
                
                # Cross-track integration dependencies
                TaskDependency("C.1.1-repository-setup-docs", "A.1.4-update-readme-index", DependencyType.SOFT),
                TaskDependency("B.1.1-tutorial-environment-setup", "A.1.4-update-readme-index", DependencyType.SOFT),
                TaskDependency("E.1.1-archive-historical-docs", "A.1.2-categorize-documents", DependencyType.BLOCKING),
            ],
            agent_assignments={
                # Track A: Documentation Agent
                "A.1.1-documentation-inventory": AgentSpecialization.DOCUMENTATION,
                "A.1.2-categorize-documents": AgentSpecialization.DOCUMENTATION,
                "A.1.3-create-archive-structure": AgentSpecialization.DOCUMENTATION,
                "A.1.4-update-readme-index": AgentSpecialization.DOCUMENTATION,
                "A.2.1-update-api-reference": AgentSpecialization.DOCUMENTATION,
                "A.2.2-enhance-deployment-docs": AgentSpecialization.DOCUMENTATION,
                "A.2.3-expand-troubleshooting": AgentSpecialization.DOCUMENTATION,
                "A.2.4-modernize-development-docs": AgentSpecialization.DOCUMENTATION,
                
                # Track B: Tutorial Agent
                "B.1.1-tutorial-environment-setup": AgentSpecialization.TUTORIAL,
                "B.1.2-project-initialization": AgentSpecialization.TUTORIAL,
                "B.2.1-user-authentication-system": AgentSpecialization.TUTORIAL,
                "B.2.2-article-management-system": AgentSpecialization.TUTORIAL,
                "B.2.3-social-features-realtime": AgentSpecialization.TUTORIAL,
                "B.3.1-docker-containerization": AgentSpecialization.TUTORIAL,
                "B.3.2-monitoring-observability": AgentSpecialization.TUTORIAL,
                "B.3.3-cicd-pipeline": AgentSpecialization.TUTORIAL,
                "B.3.4-tutorial-validation": AgentSpecialization.TUTORIAL,
                
                # Track C: Integration Agent
                "C.1.1-repository-setup-docs": AgentSpecialization.INTEGRATION,
                "C.1.2-project-integration-config": AgentSpecialization.INTEGRATION,
                "C.1.3-git-hooks-setup": AgentSpecialization.INTEGRATION,
                "C.1.4-agent-specialization-config": AgentSpecialization.INTEGRATION,
                "C.2.1-cli-commands-reference": AgentSpecialization.INTEGRATION,
                "C.2.2-workflow-coordination-patterns": AgentSpecialization.INTEGRATION,
                "C.2.3-prompt-engineering-guide": AgentSpecialization.INTEGRATION,
                "C.2.4-validation-examples": AgentSpecialization.INTEGRATION,
                
                # Track D: Quality Agent
                "D.1.1-documentation-validation": AgentSpecialization.QUALITY,
                "D.1.2-code-example-testing": AgentSpecialization.QUALITY,
                "D.1.3-link-validation": AgentSpecialization.QUALITY,
                "D.1.4-accuracy-verification": AgentSpecialization.QUALITY,
                "D.2.1-fresh-environment-testing": AgentSpecialization.QUALITY,
                "D.2.2-step-by-step-validation": AgentSpecialization.QUALITY,
                "D.2.3-performance-benchmarking": AgentSpecialization.QUALITY,
                "D.2.4-troubleshooting-testing": AgentSpecialization.QUALITY,
                
                # Track E: Archive Agent
                "E.1.1-archive-historical-docs": AgentSpecialization.ARCHIVE,
                "E.1.2-cleanup-duplicates": AgentSpecialization.ARCHIVE,
                "E.1.3-create-archive-structure": AgentSpecialization.ARCHIVE,
                "E.1.4-update-git-history": AgentSpecialization.ARCHIVE,
                "E.2.1-automated-update-triggers": AgentSpecialization.ARCHIVE,
                "E.2.2-community-feedback-integration": AgentSpecialization.ARCHIVE,
                "E.2.3-version-sync-monitoring": AgentSpecialization.ARCHIVE,
                "E.2.4-sustainability-planning": AgentSpecialization.ARCHIVE,
            },
            parallel_execution=True,
            max_parallel_tasks=5,
            estimated_duration=960  # 16 hours total, 2 weeks parallel
        )
        
        # Register workflow
        success = await self.workflow_coordinator.register_workflow(workflow_def)
        if not success:
            raise RuntimeError(f"Failed to register workflow {workflow_id}")
        
        # Create quality gates
        await self._create_quality_gates(workflow_id)
        
        return workflow_id
    
    async def _create_quality_gates(self, workflow_id: str) -> None:
        """Create quality gates for the workflow."""
        quality_gates = [
            # Track A completion gate
            QualityGate(
                gate_id=f"{workflow_id}-track-a-completion",
                workflow_id=workflow_id,
                required_tasks=[
                    "A.1.1-documentation-inventory",
                    "A.1.2-categorize-documents",
                    "A.1.3-create-archive-structure",
                    "A.1.4-update-readme-index",
                    "A.2.1-update-api-reference",
                    "A.2.2-enhance-deployment-docs",
                    "A.2.3-expand-troubleshooting",
                    "A.2.4-modernize-development-docs"
                ],
                quality_threshold=0.9,
                validation_criteria=["completeness", "accuracy", "consistency"],
                blocking=True
            ),
            
            # Track B completion gate
            QualityGate(
                gate_id=f"{workflow_id}-track-b-completion",
                workflow_id=workflow_id,
                required_tasks=[
                    "B.1.1-tutorial-environment-setup",
                    "B.1.2-project-initialization",
                    "B.2.1-user-authentication-system",
                    "B.2.2-article-management-system",
                    "B.2.3-social-features-realtime",
                    "B.3.1-docker-containerization",
                    "B.3.2-monitoring-observability",
                    "B.3.3-cicd-pipeline",
                    "B.3.4-tutorial-validation"
                ],
                quality_threshold=0.85,
                validation_criteria=["functionality", "performance", "usability"],
                blocking=True
            ),
            
            # Final integration gate
            QualityGate(
                gate_id=f"{workflow_id}-final-integration",
                workflow_id=workflow_id,
                required_tasks=[
                    "D.1.4-accuracy-verification",
                    "D.2.4-troubleshooting-testing",
                    "E.2.4-sustainability-planning"
                ],
                quality_threshold=0.95,
                validation_criteria=["integration", "completeness", "production-readiness"],
                blocking=True
            )
        ]
        
        for gate in quality_gates:
            self.workflow_coordinator.quality_gates[gate.gate_id] = gate
    
    async def register_specialized_agents(self) -> None:
        """Register specialized agents for the workflow."""
        if not self.workflow_coordinator:
            raise RuntimeError("Orchestration system not initialized")
        
        # Define agent capabilities
        agent_capabilities = {
            "documentation-agent": AgentCapabilities(
                specialization=AgentSpecialization.DOCUMENTATION,
                skill_level=0.9,
                supported_workflows=[WorkflowType.DOCUMENTATION],
                max_concurrent_tasks=3,
                preferred_task_types=["documentation", "writing", "editing"],
                performance_metrics={"speed": 0.8, "quality": 0.9, "accuracy": 0.95},
                learning_rate=0.1,
                adaptation_score=0.8
            ),
            
            "tutorial-agent": AgentCapabilities(
                specialization=AgentSpecialization.TUTORIAL,
                skill_level=0.85,
                supported_workflows=[WorkflowType.TUTORIAL, WorkflowType.DEVELOPMENT],
                max_concurrent_tasks=2,
                preferred_task_types=["tutorial", "development", "testing"],
                performance_metrics={"speed": 0.9, "quality": 0.8, "practical": 0.9},
                learning_rate=0.15,
                adaptation_score=0.7
            ),
            
            "integration-agent": AgentCapabilities(
                specialization=AgentSpecialization.INTEGRATION,
                skill_level=0.88,
                supported_workflows=[WorkflowType.INTEGRATION, WorkflowType.DEPLOYMENT],
                max_concurrent_tasks=2,
                preferred_task_types=["integration", "configuration", "deployment"],
                performance_metrics={"speed": 0.85, "quality": 0.9, "reliability": 0.95},
                learning_rate=0.12,
                adaptation_score=0.85
            ),
            
            "quality-agent": AgentCapabilities(
                specialization=AgentSpecialization.QUALITY,
                skill_level=0.92,
                supported_workflows=[WorkflowType.QUALITY, WorkflowType.TESTING],
                max_concurrent_tasks=4,
                preferred_task_types=["testing", "validation", "quality-assurance"],
                performance_metrics={"speed": 0.8, "quality": 0.95, "thoroughness": 0.9},
                learning_rate=0.08,
                adaptation_score=0.9
            ),
            
            "archive-agent": AgentCapabilities(
                specialization=AgentSpecialization.ARCHIVE,
                skill_level=0.8,
                supported_workflows=[WorkflowType.ARCHIVE],
                max_concurrent_tasks=3,
                preferred_task_types=["archival", "organization", "maintenance"],
                performance_metrics={"speed": 0.9, "quality": 0.8, "organization": 0.95},
                learning_rate=0.1,
                adaptation_score=0.75
            )
        }
        
        # Register agents
        for agent_id, capabilities in agent_capabilities.items():
            success = await self.workflow_coordinator.register_agent_capabilities(agent_id, capabilities)
            if success:
                self.logger.info(f"Registered {agent_id} with {capabilities.specialization} specialization")
            else:
                self.logger.error(f"Failed to register {agent_id}")
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Execute a workflow and return status."""
        if not self.workflow_coordinator:
            raise RuntimeError("Orchestration system not initialized")
        
        workflow_state = await self.workflow_coordinator.execute_workflow(workflow_id)
        
        return {
            "workflow_id": workflow_state.workflow_id,
            "status": workflow_state.status,
            "progress": workflow_state.progress_percentage,
            "active_tasks": len(workflow_state.active_tasks),
            "completed_tasks": len(workflow_state.completed_tasks),
            "estimated_completion": workflow_state.estimated_completion.isoformat(),
            "started_at": workflow_state.started_at.isoformat()
        }
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get current workflow status."""
        if not self.workflow_coordinator:
            raise RuntimeError("Orchestration system not initialized")
        
        workflow_state = await self.workflow_coordinator.get_workflow_state(workflow_id)
        if not workflow_state:
            return {"error": f"Workflow {workflow_id} not found"}
        
        coordination_metrics = await self.workflow_coordinator.get_coordination_metrics(workflow_id)
        
        return {
            "workflow_id": workflow_state.workflow_id,
            "status": workflow_state.status,
            "progress": workflow_state.progress_percentage,
            "active_tasks": workflow_state.active_tasks,
            "completed_tasks": workflow_state.completed_tasks,
            "failed_tasks": workflow_state.failed_tasks,
            "blocked_tasks": workflow_state.blocked_tasks,
            "estimated_completion": workflow_state.estimated_completion.isoformat(),
            "coordination_metrics": {
                "parallel_efficiency": coordination_metrics.parallel_efficiency if coordination_metrics else 0.0,
                "quality_consistency": coordination_metrics.quality_consistency if coordination_metrics else 0.0,
                "agent_utilization": coordination_metrics.agent_utilization if coordination_metrics else {}
            } if coordination_metrics else None
        }
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        """Get system-wide statistics."""
        if not self.workflow_coordinator:
            raise RuntimeError("Orchestration system not initialized")
        
        stats = self.workflow_coordinator.get_coordination_statistics()
        
        return {
            "system_running": self.running,
            "coordination_stats": stats,
            "timestamp": datetime.now().isoformat()
        }


# CLI Commands
@click.group()
@click.pass_context
def orchestration_cli(ctx):
    """Enhanced multi-agent orchestration CLI."""
    ctx.ensure_object(dict)
    ctx.obj['cli'] = OrchestrationCLI()


@orchestration_cli.command()
@click.option('--config-file', type=click.Path(exists=True), help='Configuration file path')
@click.pass_context
def start(ctx, config_file):
    """Start the orchestration system."""
    cli = ctx.obj['cli']
    
    config = {}
    if config_file:
        with open(config_file, 'r') as f:
            config = json.load(f)
    
    async def run():
        try:
            await cli.initialize(config)
            await cli.register_specialized_agents()
            click.echo("✅ Enhanced multi-agent orchestration system started successfully")
            
            # Keep running until interrupted
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            click.echo("\n⏹️  Shutting down...")
            await cli.shutdown()
        except Exception as e:
            click.echo(f"❌ Error: {e}")
            await cli.shutdown()
    
    asyncio.run(run())


@orchestration_cli.command()
@click.option('--workflow-id', help='Custom workflow ID')
@click.pass_context
def create_documentation_workflow(ctx, workflow_id):
    """Create and register the documentation workflow."""
    cli = ctx.obj['cli']
    
    async def run():
        try:
            workflow_id_result = await cli.create_documentation_workflow(workflow_id)
            click.echo(f"✅ Documentation workflow created: {workflow_id_result}")
            return workflow_id_result
        except Exception as e:
            click.echo(f"❌ Error creating workflow: {e}")
            return None
    
    result = asyncio.run(run())
    if result:
        click.echo(f"📋 Workflow ID: {result}")


@orchestration_cli.command()
@click.argument('workflow_id')
@click.pass_context
def execute(ctx, workflow_id):
    """Execute a workflow."""
    cli = ctx.obj['cli']
    
    async def run():
        try:
            result = await cli.execute_workflow(workflow_id)
            click.echo(f"✅ Workflow execution started")
            click.echo(f"📊 Status: {result['status']}")
            click.echo(f"📈 Progress: {result['progress']:.1f}%")
            click.echo(f"⏱️  Estimated completion: {result['estimated_completion']}")
            return result
        except Exception as e:
            click.echo(f"❌ Error executing workflow: {e}")
            return None
    
    asyncio.run(run())


@orchestration_cli.command()
@click.argument('workflow_id')
@click.option('--watch', is_flag=True, help='Watch for status updates')
@click.pass_context
def status(ctx, workflow_id, watch):
    """Get workflow status."""
    cli = ctx.obj['cli']
    
    async def run():
        try:
            while True:
                result = await cli.get_workflow_status(workflow_id)
                
                if 'error' in result:
                    click.echo(f"❌ {result['error']}")
                    break
                
                click.clear()
                click.echo(f"📋 Workflow: {result['workflow_id']}")
                click.echo(f"📊 Status: {result['status']}")
                click.echo(f"📈 Progress: {result['progress']:.1f}%")
                click.echo(f"⚡ Active tasks: {len(result['active_tasks'])}")
                click.echo(f"✅ Completed tasks: {len(result['completed_tasks'])}")
                click.echo(f"❌ Failed tasks: {len(result['failed_tasks'])}")
                click.echo(f"🚫 Blocked tasks: {len(result['blocked_tasks'])}")
                
                if result['coordination_metrics']:
                    metrics = result['coordination_metrics']
                    click.echo(f"🔗 Parallel efficiency: {metrics['parallel_efficiency']:.1%}")
                    click.echo(f"🎯 Quality consistency: {metrics['quality_consistency']:.1%}")
                    click.echo(f"👥 Agent utilization: {len(metrics['agent_utilization'])} agents")
                
                if not watch:
                    break
                
                await asyncio.sleep(5)
                
        except KeyboardInterrupt:
            click.echo("\n⏹️  Status monitoring stopped")
        except Exception as e:
            click.echo(f"❌ Error getting status: {e}")
    
    asyncio.run(run())


@orchestration_cli.command()
@click.pass_context
def stats(ctx):
    """Get system statistics."""
    cli = ctx.obj['cli']
    
    async def run():
        try:
            result = await cli.get_system_statistics()
            
            click.echo(f"🚀 System running: {result['system_running']}")
            click.echo(f"📊 Coordination Statistics:")
            
            stats = result['coordination_stats']
            click.echo(f"  • Workflows executed: {stats['workflows_executed']}")
            click.echo(f"  • Parallel tasks executed: {stats['parallel_tasks_executed']}")
            click.echo(f"  • Quality gates passed: {stats['quality_gates_passed']}")
            click.echo(f"  • Quality gates failed: {stats['quality_gates_failed']}")
            click.echo(f"  • Active workflows: {stats['active_workflows']}")
            click.echo(f"  • Total tasks: {stats['total_tasks']}")
            click.echo(f"  • Registered agents: {stats['registered_agents']}")
            
            click.echo(f"⏰ Timestamp: {result['timestamp']}")
            
        except Exception as e:
            click.echo(f"❌ Error getting statistics: {e}")
    
    asyncio.run(run())


if __name__ == '__main__':
    orchestration_cli()