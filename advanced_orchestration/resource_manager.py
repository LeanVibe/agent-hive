"""
Resource Manager for managing system resources across multiple agents.

This module provides resource allocation, tracking, and optimization capabilities
for the multi-agent system.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import psutil

from .models import (
    ResourceRequirements, ResourceAllocation, ResourceUsage, ResourceLimits,
    ResourceOptimization, ResourceAllocationException
)


class ResourceManager:
    """
    Resource Manager for allocating and tracking system resources.
    
    This class provides:
    - Resource allocation and deallocation
    - Resource usage monitoring
    - Resource optimization recommendations
    - Resource constraint validation
    """

    def __init__(self, limits: ResourceLimits):
        """
        Initialize the ResourceManager.
        
        Args:
            limits: System resource limits
        """
        self.limits = limits
        self.logger = logging.getLogger(__name__)
        
        # Resource tracking
        self.allocated_resources: Dict[str, ResourceAllocation] = {}
        self.total_allocated = ResourceRequirements(
            cpu_cores=0,
            memory_mb=0,
            disk_mb=0,
            network_mbps=0
        )
        
        # Usage monitoring
        self.usage_history: List[ResourceUsage] = []
        self.monitoring_active = False
        
        self.logger.info(f"ResourceManager initialized with limits: {limits}")

    async def allocate_resources(self, agent_id: str, requirements: ResourceRequirements) -> ResourceAllocation:
        """
        Allocate resources to an agent.
        
        Args:
            agent_id: ID of the agent requesting resources
            requirements: Resource requirements
            
        Returns:
            ResourceAllocation: Allocated resources
            
        Raises:
            ResourceAllocationException: If allocation fails
        """
        try:
            # Check if agent already has resources allocated
            if agent_id in self.allocated_resources:
                raise ResourceAllocationException(f"Agent {agent_id} already has resources allocated")
            
            # Validate resource constraints
            if not await self.check_resource_constraints(requirements):
                raise ResourceAllocationException("Insufficient resources available")
            
            # Create allocation
            allocation = ResourceAllocation(
                agent_id=agent_id,
                allocated_cpu=requirements.cpu_cores,
                allocated_memory=requirements.memory_mb,
                allocated_disk=requirements.disk_mb,
                allocated_network=requirements.network_mbps,
                allocation_time=datetime.now()
            )
            
            # Update tracking
            self.allocated_resources[agent_id] = allocation
            self.total_allocated.cpu_cores += requirements.cpu_cores
            self.total_allocated.memory_mb += requirements.memory_mb
            self.total_allocated.disk_mb += requirements.disk_mb
            self.total_allocated.network_mbps += requirements.network_mbps
            
            self.logger.info(f"Resources allocated to agent {agent_id}: {requirements}")
            return allocation
            
        except Exception as e:
            self.logger.error(f"Failed to allocate resources to agent {agent_id}: {e}")
            raise ResourceAllocationException(f"Resource allocation failed: {e}")

    async def deallocate_resources(self, agent_id: str) -> bool:
        """
        Deallocate resources from an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            bool: True if deallocation successful
        """
        try:
            if agent_id not in self.allocated_resources:
                self.logger.warning(f"No resources allocated to agent {agent_id}")
                return False
            
            allocation = self.allocated_resources[agent_id]
            
            # Update tracking
            self.total_allocated.cpu_cores -= allocation.allocated_cpu
            self.total_allocated.memory_mb -= allocation.allocated_memory
            self.total_allocated.disk_mb -= allocation.allocated_disk
            self.total_allocated.network_mbps -= allocation.allocated_network
            
            # Remove allocation
            del self.allocated_resources[agent_id]
            
            self.logger.info(f"Resources deallocated from agent {agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to deallocate resources from agent {agent_id}: {e}")
            return False

    async def get_resource_usage(self) -> ResourceUsage:
        """
        Get current system resource usage.
        
        Returns:
            ResourceUsage: Current resource usage
        """
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Calculate network usage (simplified)
            network_percent = 0.0
            net_io = psutil.net_io_counters()
            if net_io:
                # Simplified network usage calculation
                network_percent = min(100.0, (net_io.bytes_sent + net_io.bytes_recv) / (1024 * 1024) * 0.1)
            
            usage = ResourceUsage(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk.percent,
                network_percent=network_percent,
                timestamp=datetime.now()
            )
            
            # Add to history
            if len(self.usage_history) >= 1000:
                self.usage_history.pop(0)
            self.usage_history.append(usage)
            
            return usage
            
        except Exception as e:
            self.logger.error(f"Failed to get resource usage: {e}")
            return ResourceUsage(
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_percent=0.0,
                network_percent=0.0
            )

    async def check_resource_constraints(self, requirements: ResourceRequirements) -> bool:
        """
        Check if resource requirements can be satisfied.
        
        Args:
            requirements: Resource requirements to check
            
        Returns:
            bool: True if requirements can be satisfied
        """
        # Check against limits
        if (self.total_allocated.cpu_cores + requirements.cpu_cores > self.limits.max_cpu_cores):
            return False
        
        if (self.total_allocated.memory_mb + requirements.memory_mb > self.limits.max_memory_mb):
            return False
        
        if (self.total_allocated.disk_mb + requirements.disk_mb > self.limits.max_disk_mb):
            return False
        
        if (self.total_allocated.network_mbps + requirements.network_mbps > self.limits.max_network_mbps):
            return False
        
        # Check against current system usage
        current_usage = await self.get_resource_usage()
        
        # Allow allocation if current usage is below 90%
        if current_usage.cpu_percent > 90.0:
            return False
        
        if current_usage.memory_percent > 90.0:
            return False
        
        if current_usage.disk_percent > 90.0:
            return False
        
        return True

    async def optimize_resource_allocation(self) -> List[ResourceOptimization]:
        """
        Generate resource optimization recommendations.
        
        Returns:
            List[ResourceOptimization]: Optimization recommendations
        """
        optimizations: list[ResourceOptimization] = []
        
        try:
            # Analyze usage patterns
            if len(self.usage_history) < 10:
                return optimizations
            
            # Calculate average usage over last 10 measurements
            recent_usage = self.usage_history[-10:]
            avg_cpu = sum(u.cpu_percent for u in recent_usage) / len(recent_usage)
            avg_memory = sum(u.memory_percent for u in recent_usage) / len(recent_usage)
            avg_disk = sum(u.disk_percent for u in recent_usage) / len(recent_usage)
            avg_network = sum(u.network_percent for u in recent_usage) / len(recent_usage)
            
            # Generate optimization recommendations
            for agent_id, allocation in self.allocated_resources.items():
                # Check if agent is over-allocated
                optimization = await self._analyze_agent_allocation(
                    agent_id, allocation, avg_cpu, avg_memory, avg_disk, avg_network
                )
                if optimization:
                    optimizations.append(optimization)
            
            self.logger.info(f"Generated {len(optimizations)} resource optimizations")
            return optimizations
            
        except Exception as e:
            self.logger.error(f"Failed to optimize resource allocation: {e}")
            return optimizations

    async def _analyze_agent_allocation(self, agent_id: str, allocation: ResourceAllocation,
                                       avg_cpu: float, avg_memory: float, avg_disk: float,
                                       avg_network: float) -> Optional[ResourceOptimization]:
        """
        Analyze a single agent's resource allocation.
        
        Args:
            agent_id: Agent ID
            allocation: Current allocation
            avg_cpu: Average CPU usage
            avg_memory: Average memory usage
            avg_disk: Average disk usage
            avg_network: Average network usage
            
        Returns:
            ResourceOptimization: Optimization recommendation or None
        """
        # Calculate utilization efficiency
        cpu_efficiency = min(100.0, avg_cpu / max(1.0, allocation.allocated_cpu * 10))
        memory_efficiency = min(100.0, avg_memory / max(1.0, (allocation.allocated_memory / 1024) * 10))
        
        # Check for over-allocation
        if cpu_efficiency < 50.0 or memory_efficiency < 50.0:
            # Recommend reducing allocation
            recommended_cpu = max(1, int(allocation.allocated_cpu * 0.8))
            recommended_memory = max(512, int(allocation.allocated_memory * 0.8))
            
            recommended_allocation = ResourceAllocation(
                agent_id=agent_id,
                allocated_cpu=recommended_cpu,
                allocated_memory=recommended_memory,
                allocated_disk=allocation.allocated_disk,
                allocated_network=allocation.allocated_network,
                allocation_time=datetime.now()
            )
            
            expected_improvement = (100.0 - max(cpu_efficiency, memory_efficiency)) / 100.0
            
            return ResourceOptimization(
                agent_id=agent_id,
                current_allocation=allocation,
                recommended_allocation=recommended_allocation,
                expected_improvement=expected_improvement,
                reason=f"Over-allocated resources detected (CPU: {cpu_efficiency:.1f}%, Memory: {memory_efficiency:.1f}%)"
            )
        
        # Check for under-allocation
        elif cpu_efficiency > 90.0 or memory_efficiency > 90.0:
            # Recommend increasing allocation
            recommended_cpu = int(allocation.allocated_cpu * 1.2)
            recommended_memory = int(allocation.allocated_memory * 1.2)
            
            # Check if we can satisfy the increase
            requirements = ResourceRequirements(
                cpu_cores=recommended_cpu - allocation.allocated_cpu,
                memory_mb=recommended_memory - allocation.allocated_memory
            )
            
            if await self.check_resource_constraints(requirements):
                recommended_allocation = ResourceAllocation(
                    agent_id=agent_id,
                    allocated_cpu=recommended_cpu,
                    allocated_memory=recommended_memory,
                    allocated_disk=allocation.allocated_disk,
                    allocated_network=allocation.allocated_network,
                    allocation_time=datetime.now()
                )
                
                expected_improvement = (min(cpu_efficiency, memory_efficiency) - 90.0) / 100.0
                
                return ResourceOptimization(
                    agent_id=agent_id,
                    current_allocation=allocation,
                    recommended_allocation=recommended_allocation,
                    expected_improvement=expected_improvement,
                    reason=f"Under-allocated resources detected (CPU: {cpu_efficiency:.1f}%, Memory: {memory_efficiency:.1f}%)"
                )
        
        return None

    async def get_allocation_summary(self) -> Dict[str, Any]:
        """
        Get resource allocation summary.
        
        Returns:
            Dict[str, any]: Allocation summary
        """
        current_usage = await self.get_resource_usage()
        
        return {
            'total_allocated': {
                'cpu_cores': self.total_allocated.cpu_cores,
                'memory_mb': self.total_allocated.memory_mb,
                'disk_mb': self.total_allocated.disk_mb,
                'network_mbps': self.total_allocated.network_mbps
            },
            'limits': {
                'max_cpu_cores': self.limits.max_cpu_cores,
                'max_memory_mb': self.limits.max_memory_mb,
                'max_disk_mb': self.limits.max_disk_mb,
                'max_network_mbps': self.limits.max_network_mbps
            },
            'current_usage': {
                'cpu_percent': current_usage.cpu_percent,
                'memory_percent': current_usage.memory_percent,
                'disk_percent': current_usage.disk_percent,
                'network_percent': current_usage.network_percent
            },
            'allocation_efficiency': {
                'cpu': (self.total_allocated.cpu_cores / self.limits.max_cpu_cores) * 100,
                'memory': (self.total_allocated.memory_mb / self.limits.max_memory_mb) * 100,
                'disk': (self.total_allocated.disk_mb / self.limits.max_disk_mb) * 100,
                'network': (self.total_allocated.network_mbps / self.limits.max_network_mbps) * 100
            },
            'active_allocations': len(self.allocated_resources),
            'agents': list(self.allocated_resources.keys())
        }

    async def start_monitoring(self) -> None:
        """Start resource usage monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        asyncio.create_task(self._monitor_resources())
        self.logger.info("Resource monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop resource usage monitoring."""
        self.monitoring_active = False
        self.logger.info("Resource monitoring stopped")

    async def _monitor_resources(self) -> None:
        """Background resource monitoring task."""
        while self.monitoring_active:
            try:
                await self.get_resource_usage()
                await asyncio.sleep(10)  # Monitor every 10 seconds
            except Exception as e:
                self.logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(30)  # Wait longer on error

    def get_agent_allocation(self, agent_id: str) -> Optional[ResourceAllocation]:
        """
        Get resource allocation for a specific agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            ResourceAllocation: Agent's resource allocation or None
        """
        return self.allocated_resources.get(agent_id)

    def get_available_resources(self) -> ResourceRequirements:
        """
        Get available resources that can be allocated.
        
        Returns:
            ResourceRequirements: Available resources
        """
        return ResourceRequirements(
            cpu_cores=max(0, self.limits.max_cpu_cores - self.total_allocated.cpu_cores),
            memory_mb=max(0, self.limits.max_memory_mb - self.total_allocated.memory_mb),
            disk_mb=max(0, self.limits.max_disk_mb - self.total_allocated.disk_mb),
            network_mbps=max(0, self.limits.max_network_mbps - self.total_allocated.network_mbps)
        )

    def get_resource_efficiency(self) -> Dict[str, float]:
        """
        Get resource efficiency metrics.
        
        Returns:
            Dict[str, float]: Efficiency metrics
        """
        if not self.usage_history:
            return {'cpu': 0.0, 'memory': 0.0, 'disk': 0.0, 'network': 0.0}
        
        # Calculate average efficiency over recent history
        recent_usage = self.usage_history[-10:] if len(self.usage_history) >= 10 else self.usage_history
        
        avg_cpu = sum(u.cpu_percent for u in recent_usage) / len(recent_usage)
        avg_memory = sum(u.memory_percent for u in recent_usage) / len(recent_usage)
        avg_disk = sum(u.disk_percent for u in recent_usage) / len(recent_usage)
        avg_network = sum(u.network_percent for u in recent_usage) / len(recent_usage)
        
        return {
            'cpu': avg_cpu,
            'memory': avg_memory,
            'disk': avg_disk,
            'network': avg_network
        }