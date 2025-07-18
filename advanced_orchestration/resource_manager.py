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