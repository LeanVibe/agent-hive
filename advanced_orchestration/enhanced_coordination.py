"""
Enhanced Multi-Agent Coordination Protocols.

This module provides advanced coordination capabilities that build on the existing
MultiAgentCoordinator and WorkflowCoordinator to implement:
- Intelligent task routing with ML-based agent selection
- Dynamic dependency management and parallel execution optimization
- Real-time coordination metrics and performance monitoring
- Adaptive load balancing and resource optimization
- Quality gate integration and validation workflows
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from collections import defaultdict, deque
import json
import uuid
import statistics

from .models import (
    AgentInfo, AgentStatus, TaskStatus, TaskPriority, EnhancedTaskAssignment,
    WorkflowDefinition, WorkflowState, CoordinationMetrics, IntelligentRouting,
    QualityGate, TaskDependency, DependencyType, AgentSpecialization,
    AgentCapabilities, LoadBalancingStrategy, CoordinatorConfig,
    TaskDistributionException, CoordinatorException
)
from .multi_agent_coordinator import MultiAgentCoordinator
from .workflow_coordinator import WorkflowCoordinator
from .performance_monitor import PerformanceMonitor, PerformanceMetric, PerformanceMetricType
from .analytics_dashboard import AnalyticsDashboard, DashboardView


class EnhancedCoordinationProtocol:
    """
    Enhanced coordination protocol for multi-agent orchestration.
    
    Provides advanced coordination capabilities including:
    - Intelligent task routing with ML-based prediction
    - Dynamic dependency resolution and parallel optimization
    - Real-time performance monitoring and adaptation
    - Quality gate integration and validation
    - Adaptive resource allocation and load balancing
    """

    def __init__(self, config: CoordinatorConfig):
        """
        Initialize enhanced coordination protocol.
        
        Args:
            config: Coordinator configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Core coordinators
        self.multi_agent_coordinator = MultiAgentCoordinator(config)
        self.workflow_coordinator = WorkflowCoordinator(config)
        
        # Performance monitoring and analytics
        self.performance_monitor = PerformanceMonitor()
        self.analytics_dashboard = AnalyticsDashboard(self.performance_monitor)
        
        # Enhanced coordination state
        self.coordination_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.intelligent_routing_cache: Dict[str, Tuple[str, float]] = {}
        self.dependency_resolution_cache: Dict[str, List[str]] = {}
        self.parallel_execution_analytics: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self.agent_performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.task_completion_times: Dict[str, List[float]] = defaultdict(list)
        self.coordination_efficiency_metrics: Dict[str, float] = {}
        
        # Real-time monitoring
        self.running = False
        self.coordination_events: deque = deque(maxlen=1000)
        self.performance_alerts: List[Dict[str, Any]] = []
        
        # Enhanced routing configuration
        self.intelligent_routing = IntelligentRouting(
            use_ml_prediction=True,
            consider_agent_history=True,
            adapt_to_performance=True,
            learning_enabled=True
        )
        
        self.logger.info("Enhanced coordination protocol initialized")

    async def start(self) -> None:
        """Start the enhanced coordination protocol."""
        self.running = True
        await self.multi_agent_coordinator.start()
        await self.workflow_coordinator.start()
        
        # Start performance monitoring
        self.performance_monitor.start_monitoring()
        
        # Start enhanced monitoring tasks
        asyncio.create_task(self._enhanced_coordination_monitor())
        asyncio.create_task(self._intelligent_routing_optimizer())
        asyncio.create_task(self._dependency_resolution_optimizer())
        asyncio.create_task(self._performance_analytics_processor())
        
        self.logger.info("Enhanced coordination protocol started")

    async def stop(self) -> None:
        """Stop the enhanced coordination protocol."""
        self.running = False
        
        # Stop performance monitoring
        self.performance_monitor.stop_monitoring()
        
        await self.workflow_coordinator.stop()
        await self.multi_agent_coordinator.stop()
        self.logger.info("Enhanced coordination protocol stopped")

    async def execute_enhanced_workflow(
        self, 
        workflow_def: WorkflowDefinition,
        context: Dict[str, Any] = None
    ) -> WorkflowState:
        """
        Execute workflow with enhanced coordination protocols.
        
        Args:
            workflow_def: Workflow definition
            context: Execution context
            
        Returns:
            WorkflowState: Current workflow state
        """
        try:
            # Register workflow with enhanced capabilities
            await self.workflow_coordinator.register_workflow(workflow_def)
            
            # Analyze and optimize workflow structure
            await self._analyze_workflow_structure(workflow_def)
            
            # Execute workflow with intelligent coordination
            workflow_state = await self.workflow_coordinator.execute_workflow(
                workflow_def.workflow_id, context or {}
            )
            
            # Start enhanced monitoring for this workflow
            asyncio.create_task(self._monitor_workflow_execution(workflow_def.workflow_id))
            
            # Log coordination event
            await self._log_coordination_event("workflow_started", {
                "workflow_id": workflow_def.workflow_id,
                "task_count": len(workflow_def.tasks),
                "parallel_execution": workflow_def.parallel_execution
            })
            
            return workflow_state
            
        except Exception as e:
            self.logger.error(f"Enhanced workflow execution failed: {e}")
            raise CoordinatorException(f"Enhanced workflow execution failed: {e}")

    async def intelligent_task_routing(
        self, 
        task: EnhancedTaskAssignment,
        available_agents: List[str]
    ) -> Optional[str]:
        """
        Perform intelligent task routing using ML-based agent selection.
        
        Args:
            task: Task to route
            available_agents: List of available agent IDs
            
        Returns:
            str: Selected agent ID or None if no suitable agent
        """
        try:
            if not available_agents:
                return None
            
            # Check routing cache first
            cache_key = f"{task.task_id}_{task.agent_specialization.value}"
            if cache_key in self.intelligent_routing_cache:
                cached_agent, confidence = self.intelligent_routing_cache[cache_key]
                if cached_agent in available_agents and confidence > self.intelligent_routing.confidence_threshold:
                    return cached_agent
            
            # Perform intelligent routing
            agent_scores = await self._calculate_agent_scores(task, available_agents)
            
            if not agent_scores:
                return available_agents[0]  # Fallback to first available
            
            # Select best agent
            best_agent = max(agent_scores, key=agent_scores.get)
            best_score = agent_scores[best_agent]
            
            # Cache the result
            self.intelligent_routing_cache[cache_key] = (best_agent, best_score)
            
            # Log routing decision
            await self._log_coordination_event("intelligent_routing", {
                "task_id": task.task_id,
                "selected_agent": best_agent,
                "score": best_score,
                "specialization": task.agent_specialization.value
            })
            
            return best_agent
            
        except Exception as e:
            self.logger.error(f"Intelligent task routing failed: {e}")
            return available_agents[0] if available_agents else None

    async def resolve_dynamic_dependencies(
        self, 
        workflow_id: str,
        task_id: str
    ) -> List[str]:
        """
        Resolve dynamic dependencies for a task.
        
        Args:
            workflow_id: Workflow ID
            task_id: Task ID
            
        Returns:
            List[str]: List of dependency task IDs that must complete first
        """
        try:
            # Check cache first
            cache_key = f"{workflow_id}_{task_id}"
            if cache_key in self.dependency_resolution_cache:
                return self.dependency_resolution_cache[cache_key]
            
            # Get workflow state
            workflow_state = await self.workflow_coordinator.get_workflow_state(workflow_id)
            if not workflow_state:
                return []
            
            # Get workflow definition
            workflow_def = self.workflow_coordinator.workflow_definitions.get(workflow_id)
            if not workflow_def:
                return []
            
            # Resolve dependencies
            dependencies = await self._resolve_task_dependencies(workflow_def, task_id)
            
            # Apply dynamic optimization
            optimized_dependencies = await self._optimize_dependency_chain(
                workflow_def, task_id, dependencies
            )
            
            # Cache the result
            self.dependency_resolution_cache[cache_key] = optimized_dependencies
            
            # Log dependency resolution
            await self._log_coordination_event("dependency_resolution", {
                "workflow_id": workflow_id,
                "task_id": task_id,
                "dependencies": optimized_dependencies,
                "optimization_applied": len(optimized_dependencies) != len(dependencies)
            })
            
            return optimized_dependencies
            
        except Exception as e:
            self.logger.error(f"Dynamic dependency resolution failed: {e}")
            return []

    async def optimize_parallel_execution(
        self, 
        workflow_id: str,
        task_groups: List[List[str]]
    ) -> List[List[str]]:
        """
        Optimize parallel execution groups for maximum efficiency.
        
        Args:
            workflow_id: Workflow ID
            task_groups: Current parallel execution groups
            
        Returns:
            List[List[str]]: Optimized execution groups
        """
        try:
            # Get workflow performance history
            workflow_analytics = self.parallel_execution_analytics.get(workflow_id, {})
            
            # Analyze current groups
            group_analysis = await self._analyze_parallel_groups(workflow_id, task_groups)
            
            # Optimize based on historical performance
            optimized_groups = await self._optimize_groups_by_performance(
                workflow_id, task_groups, group_analysis
            )
            
            # Apply resource-based optimization
            resource_optimized_groups = await self._optimize_groups_by_resources(
                optimized_groups
            )
            
            # Update analytics
            self.parallel_execution_analytics[workflow_id] = {
                "original_groups": len(task_groups),
                "optimized_groups": len(resource_optimized_groups),
                "optimization_time": datetime.now(),
                "expected_improvement": group_analysis.get("expected_improvement", 0.0)
            }
            
            # Log optimization
            await self._log_coordination_event("parallel_optimization", {
                "workflow_id": workflow_id,
                "original_groups": len(task_groups),
                "optimized_groups": len(resource_optimized_groups),
                "improvement": group_analysis.get("expected_improvement", 0.0)
            })
            
            return resource_optimized_groups
            
        except Exception as e:
            self.logger.error(f"Parallel execution optimization failed: {e}")
            return task_groups

    async def monitor_real_time_coordination(self) -> CoordinationMetrics:
        """
        Monitor real-time coordination metrics.
        
        Returns:
            CoordinationMetrics: Current coordination metrics
        """
        try:
            # Get current coordinator state
            coordinator_state = await self.multi_agent_coordinator.get_coordinator_state()
            
            # Calculate enhanced metrics
            workflow_completion_rate = await self._calculate_workflow_completion_rate()
            parallel_efficiency = await self._calculate_parallel_efficiency()
            task_distribution_balance = await self._calculate_task_distribution_balance()
            quality_consistency = await self._calculate_quality_consistency()
            dependency_resolution_time = await self._calculate_dependency_resolution_time()
            agent_utilization = await self._calculate_agent_utilization()
            coordination_overhead = await self._calculate_coordination_overhead()
            
            # Create metrics object
            metrics = CoordinationMetrics(
                workflow_completion_rate=workflow_completion_rate,
                parallel_efficiency=parallel_efficiency,
                task_distribution_balance=task_distribution_balance,
                quality_consistency=quality_consistency,
                dependency_resolution_time=dependency_resolution_time,
                agent_utilization=agent_utilization,
                coordination_overhead=coordination_overhead
            )
            
            # Store metrics
            self.coordination_efficiency_metrics.update({
                "workflow_completion_rate": workflow_completion_rate,
                "parallel_efficiency": parallel_efficiency,
                "task_distribution_balance": task_distribution_balance,
                "quality_consistency": quality_consistency,
                "coordination_overhead": coordination_overhead
            })
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Real-time coordination monitoring failed: {e}")
            return CoordinationMetrics(
                workflow_completion_rate=0.0,
                parallel_efficiency=0.0,
                task_distribution_balance=0.0,
                quality_consistency=0.0,
                dependency_resolution_time=0.0,
                agent_utilization={},
                coordination_overhead=1.0
            )

    async def _calculate_agent_scores(
        self, 
        task: EnhancedTaskAssignment, 
        available_agents: List[str]
    ) -> Dict[str, float]:
        """Calculate agent scores for intelligent routing."""
        agent_scores = {}
        
        for agent_id in available_agents:
            score = 0.0
            
            # Get agent capabilities
            agent_capabilities = self.workflow_coordinator.agent_capabilities.get(agent_id)
            if agent_capabilities:
                # Specialization match
                if agent_capabilities.specialization == task.agent_specialization:
                    score += 0.4
                
                # Skill level
                score += agent_capabilities.skill_level * 0.3
                
                # Performance history
                if agent_id in self.agent_performance_history:
                    recent_performance = list(self.agent_performance_history[agent_id])
                    if recent_performance:
                        avg_performance = statistics.mean(recent_performance)
                        score += avg_performance * 0.3
            
            # Current load
            coordinator_state = await self.multi_agent_coordinator.get_coordinator_state()
            if agent_id in coordinator_state.active_agents:
                agent_info = coordinator_state.active_agents[agent_id]
                load_factor = 1.0 - (agent_info.active_tasks / max(1, 10))  # Normalize to 0-1
                score *= load_factor
            
            agent_scores[agent_id] = score
        
        return agent_scores

    async def _resolve_task_dependencies(
        self, 
        workflow_def: WorkflowDefinition, 
        task_id: str
    ) -> List[str]:
        """Resolve task dependencies from workflow definition."""
        dependencies = []
        
        for dependency in workflow_def.dependencies:
            if dependency.task_id == task_id:
                dependencies.append(dependency.depends_on)
        
        return dependencies

    async def _optimize_dependency_chain(
        self, 
        workflow_def: WorkflowDefinition, 
        task_id: str, 
        dependencies: List[str]
    ) -> List[str]:
        """Optimize dependency chain for parallel execution."""
        if not dependencies:
            return dependencies
        
        # Check if any dependencies can be parallelized
        optimized_deps = []
        
        for dep in dependencies:
            # Check if dependency is truly blocking
            dep_obj = next((d for d in workflow_def.dependencies 
                          if d.task_id == task_id and d.depends_on == dep), None)
            
            if dep_obj and dep_obj.dependency_type == DependencyType.SOFT:
                # Soft dependencies can be optimized
                continue
            
            optimized_deps.append(dep)
        
        return optimized_deps

    async def _analyze_parallel_groups(
        self, 
        workflow_id: str, 
        task_groups: List[List[str]]
    ) -> Dict[str, Any]:
        """Analyze parallel execution groups."""
        analysis = {
            "group_count": len(task_groups),
            "total_tasks": sum(len(group) for group in task_groups),
            "max_group_size": max(len(group) for group in task_groups) if task_groups else 0,
            "min_group_size": min(len(group) for group in task_groups) if task_groups else 0,
            "expected_improvement": 0.0
        }
        
        # Calculate potential improvement
        if task_groups:
            current_parallel_efficiency = len(task_groups) / analysis["total_tasks"]
            optimal_parallel_efficiency = min(1.0, analysis["total_tasks"] / 
                                            self.config.max_agents)
            analysis["expected_improvement"] = optimal_parallel_efficiency - current_parallel_efficiency
        
        return analysis

    async def _optimize_groups_by_performance(
        self, 
        workflow_id: str, 
        task_groups: List[List[str]], 
        analysis: Dict[str, Any]
    ) -> List[List[str]]:
        """Optimize groups based on historical performance."""
        # For now, return original groups
        # In production, this would use ML models to predict optimal groupings
        return task_groups

    async def _optimize_groups_by_resources(
        self, 
        task_groups: List[List[str]]
    ) -> List[List[str]]:
        """Optimize groups based on available resources."""
        # Get current resource utilization
        coordinator_state = await self.multi_agent_coordinator.get_coordinator_state()
        available_agents = len([agent for agent in coordinator_state.active_agents.values() 
                              if agent.status == AgentStatus.HEALTHY])
        
        # Limit parallel groups to available agents
        if len(task_groups) > available_agents:
            # Merge smaller groups
            optimized_groups = []
            current_group = []
            
            for group in sorted(task_groups, key=len, reverse=True):
                if len(optimized_groups) < available_agents:
                    optimized_groups.append(group)
                else:
                    # Merge with existing groups
                    smallest_group_idx = min(range(len(optimized_groups)), 
                                           key=lambda i: len(optimized_groups[i]))
                    optimized_groups[smallest_group_idx].extend(group)
            
            return optimized_groups
        
        return task_groups

    async def _calculate_workflow_completion_rate(self) -> float:
        """Calculate workflow completion rate."""
        active_workflows = len(self.workflow_coordinator.active_workflows)
        if active_workflows == 0:
            return 1.0
        
        completed_workflows = len([w for w in self.workflow_coordinator.active_workflows.values() 
                                 if w.status == "completed"])
        return completed_workflows / active_workflows

    async def _calculate_parallel_efficiency(self) -> float:
        """Calculate parallel execution efficiency."""
        if not self.parallel_execution_analytics:
            return 0.0
        
        efficiencies = []
        for workflow_id, analytics in self.parallel_execution_analytics.items():
            if "expected_improvement" in analytics:
                efficiencies.append(analytics["expected_improvement"])
        
        return statistics.mean(efficiencies) if efficiencies else 0.0

    async def _calculate_task_distribution_balance(self) -> float:
        """Calculate task distribution balance."""
        coordinator_state = await self.multi_agent_coordinator.get_coordinator_state()
        
        if not coordinator_state.active_agents:
            return 1.0
        
        task_counts = [agent.active_tasks for agent in coordinator_state.active_agents.values()]
        if not task_counts:
            return 1.0
        
        mean_tasks = statistics.mean(task_counts)
        if mean_tasks == 0:
            return 1.0
        
        variance = statistics.variance(task_counts) if len(task_counts) > 1 else 0
        return 1.0 / (1.0 + variance / mean_tasks)

    async def _calculate_quality_consistency(self) -> float:
        """Calculate quality consistency across tasks."""
        quality_scores = []
        
        for task in self.workflow_coordinator.enhanced_tasks.values():
            if task.quality_score > 0:
                quality_scores.append(task.quality_score)
        
        if not quality_scores:
            return 0.0
        
        return statistics.mean(quality_scores)

    async def _calculate_dependency_resolution_time(self) -> float:
        """Calculate average dependency resolution time."""
        if not self.task_completion_times:
            return 0.0
        
        all_times = []
        for times in self.task_completion_times.values():
            all_times.extend(times)
        
        return statistics.mean(all_times) if all_times else 0.0

    async def _calculate_agent_utilization(self) -> Dict[str, float]:
        """Calculate agent utilization metrics."""
        coordinator_state = await self.multi_agent_coordinator.get_coordinator_state()
        
        utilization = {}
        for agent_id, agent_info in coordinator_state.active_agents.items():
            if agent_info.current_usage:
                utilization[agent_id] = (
                    agent_info.current_usage.cpu_percent + 
                    agent_info.current_usage.memory_percent
                ) / 2.0
            else:
                utilization[agent_id] = 0.0
        
        return utilization

    async def _calculate_coordination_overhead(self) -> float:
        """Calculate coordination overhead."""
        # Simplified calculation - in production, this would measure actual overhead
        return 0.1  # 10% overhead

    async def _analyze_workflow_structure(self, workflow_def: WorkflowDefinition) -> None:
        """Analyze workflow structure for optimization opportunities."""
        # Create dependency graph
        dependency_graph = defaultdict(set)
        for dep in workflow_def.dependencies:
            dependency_graph[dep.task_id].add(dep.depends_on)
        
        # Identify optimization opportunities
        optimization_opportunities = {
            "parallel_groups": [],
            "dependency_chains": [],
            "critical_path": []
        }
        
        # Store analysis results
        self.coordination_history[workflow_def.workflow_id].append({
            "timestamp": datetime.now(),
            "analysis": "workflow_structure",
            "opportunities": optimization_opportunities
        })

    async def _monitor_workflow_execution(self, workflow_id: str) -> None:
        """Monitor workflow execution in real-time."""
        while self.running:
            try:
                workflow_state = await self.workflow_coordinator.get_workflow_state(workflow_id)
                if not workflow_state or workflow_state.status == "completed":
                    break
                
                # Update performance metrics
                await self._update_workflow_performance_metrics(workflow_id, workflow_state)
                
                # Check for performance alerts
                await self._check_performance_alerts(workflow_id)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Workflow monitoring error for {workflow_id}: {e}")
                break

    async def _update_workflow_performance_metrics(
        self, 
        workflow_id: str, 
        workflow_state: WorkflowState
    ) -> None:
        """Update workflow performance metrics."""
        metrics = {
            "progress": workflow_state.progress_percentage,
            "active_tasks": len(workflow_state.active_tasks),
            "completed_tasks": len(workflow_state.completed_tasks),
            "failed_tasks": len(workflow_state.failed_tasks),
            "timestamp": datetime.now()
        }
        
        self.coordination_history[workflow_id].append(metrics)

    async def _check_performance_alerts(self, workflow_id: str) -> None:
        """Check for performance alerts."""
        workflow_state = await self.workflow_coordinator.get_workflow_state(workflow_id)
        if not workflow_state:
            return
        
        # Check for stalled workflows
        if workflow_state.progress_percentage < 50 and \
           datetime.now() - workflow_state.started_at > timedelta(hours=2):
            alert = {
                "type": "workflow_stalled",
                "workflow_id": workflow_id,
                "progress": workflow_state.progress_percentage,
                "duration": (datetime.now() - workflow_state.started_at).total_seconds() / 3600,
                "timestamp": datetime.now()
            }
            self.performance_alerts.append(alert)

    async def _log_coordination_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log coordination event."""
        event = {
            "type": event_type,
            "timestamp": datetime.now(),
            "data": data
        }
        self.coordination_events.append(event)

    async def _enhanced_coordination_monitor(self) -> None:
        """Enhanced coordination monitoring."""
        while self.running:
            try:
                await asyncio.sleep(30)
                
                # Update real-time metrics
                await self.monitor_real_time_coordination()
                
                # Check for optimization opportunities
                await self._identify_optimization_opportunities()
                
            except Exception as e:
                self.logger.error(f"Enhanced coordination monitoring error: {e}")

    async def _intelligent_routing_optimizer(self) -> None:
        """Intelligent routing optimizer."""
        while self.running:
            try:
                await asyncio.sleep(60)
                
                # Clear old cache entries
                current_time = datetime.now()
                cache_ttl = timedelta(minutes=30)
                
                # This would clear cache entries older than TTL
                # For now, we'll just clear the entire cache periodically
                if len(self.intelligent_routing_cache) > 1000:
                    self.intelligent_routing_cache.clear()
                
            except Exception as e:
                self.logger.error(f"Intelligent routing optimization error: {e}")

    async def _dependency_resolution_optimizer(self) -> None:
        """Dependency resolution optimizer."""
        while self.running:
            try:
                await asyncio.sleep(90)
                
                # Clear old dependency cache
                if len(self.dependency_resolution_cache) > 500:
                    self.dependency_resolution_cache.clear()
                
            except Exception as e:
                self.logger.error(f"Dependency resolution optimization error: {e}")

    async def _performance_analytics_processor(self) -> None:
        """Performance analytics processor."""
        while self.running:
            try:
                await asyncio.sleep(120)
                
                # Process performance analytics
                await self._process_performance_analytics()
                
            except Exception as e:
                self.logger.error(f"Performance analytics processing error: {e}")

    async def _process_performance_analytics(self) -> None:
        """Process performance analytics."""
        # Update agent performance history
        coordinator_state = await self.multi_agent_coordinator.get_coordinator_state()
        
        for agent_id, agent_info in coordinator_state.active_agents.items():
            if agent_info.current_usage:
                performance_score = 1.0 - (agent_info.current_usage.cpu_percent + 
                                         agent_info.current_usage.memory_percent) / 2.0
                self.agent_performance_history[agent_id].append(performance_score)

    async def _identify_optimization_opportunities(self) -> None:
        """Identify coordination optimization opportunities."""
        # Analyze current coordination efficiency
        metrics = await self.monitor_real_time_coordination()
        
        # Identify areas for improvement
        opportunities = []
        
        if metrics.parallel_efficiency < 0.7:
            opportunities.append("parallel_execution_optimization")
        
        if metrics.task_distribution_balance < 0.6:
            opportunities.append("load_balancing_optimization")
        
        if metrics.coordination_overhead > 0.2:
            opportunities.append("coordination_overhead_reduction")
        
        # Log opportunities
        if opportunities:
            await self._log_coordination_event("optimization_opportunities", {
                "opportunities": opportunities,
                "current_metrics": {
                    "parallel_efficiency": metrics.parallel_efficiency,
                    "task_distribution_balance": metrics.task_distribution_balance,
                    "coordination_overhead": metrics.coordination_overhead
                }
            })

    def get_coordination_statistics(self) -> Dict[str, Any]:
        """Get comprehensive coordination statistics."""
        return {
            "active_workflows": len(self.workflow_coordinator.active_workflows),
            "coordination_events": len(self.coordination_events),
            "performance_alerts": len(self.performance_alerts),
            "routing_cache_size": len(self.intelligent_routing_cache),
            "dependency_cache_size": len(self.dependency_resolution_cache),
            "agent_performance_tracked": len(self.agent_performance_history),
            "coordination_efficiency": self.coordination_efficiency_metrics,
            "recent_events": list(self.coordination_events)[-10:] if self.coordination_events else []
        }