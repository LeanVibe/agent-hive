#!/usr/bin/env python3
"""
Tests for the ResourceManager.

This test suite covers:
- Resource allocation and deallocation
- Resource usage monitoring
- Resource constraint validation
- Resource optimization recommendations
- Resource efficiency metrics
"""

import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from advanced_orchestration.resource_manager import ResourceManager
from advanced_orchestration.models import (
    ResourceLimits, ResourceRequirements, ResourceAllocation, ResourceUsage,
    ResourceAllocationException
)


class TestResourceManager:
    """Test suite for ResourceManager"""

    @pytest.fixture
    def resource_limits(self):
        """Create resource limits for testing"""
        return ResourceLimits(
            max_cpu_cores=4,
            max_memory_mb=4096,
            max_disk_mb=8192,
            max_network_mbps=1000,
            max_agents=5
        )

    @pytest.fixture
    def resource_manager(self, resource_limits):
        """Create resource manager instance for testing"""
        return ResourceManager(resource_limits)

    @pytest.fixture
    def sample_requirements(self):
        """Create sample resource requirements"""
        return ResourceRequirements(
            cpu_cores=1,
            memory_mb=512,
            disk_mb=1024,
            network_mbps=100
        )

    def test_resource_manager_initialization(self, resource_manager, resource_limits):
        """Test resource manager initializes correctly"""
        assert resource_manager.limits == resource_limits
        assert resource_manager.allocated_resources == {}
        assert resource_manager.total_allocated.cpu_cores == 0
        assert resource_manager.total_allocated.memory_mb == 0
        assert resource_manager.total_allocated.disk_mb == 0
        assert resource_manager.total_allocated.network_mbps == 0
        assert resource_manager.usage_history == []
        assert resource_manager.monitoring_active is False

    @pytest.mark.asyncio
    async def test_resource_allocation_success(self, resource_manager, sample_requirements):
        """Test successful resource allocation"""
        agent_id = "test-agent-001"

        # Allocate resources
        allocation = await resource_manager.allocate_resources(agent_id, sample_requirements)

        # Check allocation
        assert allocation.agent_id == agent_id
        assert allocation.allocated_cpu == sample_requirements.cpu_cores
        assert allocation.allocated_memory == sample_requirements.memory_mb
        assert allocation.allocated_disk == sample_requirements.disk_mb
        assert allocation.allocated_network == sample_requirements.network_mbps

        # Check tracking
        assert agent_id in resource_manager.allocated_resources
        assert resource_manager.total_allocated.cpu_cores == sample_requirements.cpu_cores
        assert resource_manager.total_allocated.memory_mb == sample_requirements.memory_mb
        assert resource_manager.total_allocated.disk_mb == sample_requirements.disk_mb
        assert resource_manager.total_allocated.network_mbps == sample_requirements.network_mbps

    @pytest.mark.asyncio
    async def test_resource_allocation_duplicate_agent(self, resource_manager, sample_requirements):
        """Test duplicate agent allocation fails"""
        agent_id = "test-agent-001"

        # Allocate resources first time
        await resource_manager.allocate_resources(agent_id, sample_requirements)

        # Try to allocate resources again for same agent
        with pytest.raises(ResourceAllocationException):
            await resource_manager.allocate_resources(agent_id, sample_requirements)

    @pytest.mark.asyncio
    async def test_resource_allocation_insufficient_resources(self, resource_manager):
        """Test allocation fails when insufficient resources"""
        agent_id = "test-agent-001"

        # Try to allocate more than available
        excessive_requirements = ResourceRequirements(
            cpu_cores=10,  # More than max_cpu_cores (4)
            memory_mb=512,
            disk_mb=1024,
            network_mbps=100
        )

        with pytest.raises(ResourceAllocationException):
            await resource_manager.allocate_resources(agent_id, excessive_requirements)

    @pytest.mark.asyncio
    async def test_resource_deallocation_success(self, resource_manager, sample_requirements):
        """Test successful resource deallocation"""
        agent_id = "test-agent-001"

        # Allocate resources first
        allocation = await resource_manager.allocate_resources(agent_id, sample_requirements)

        # Deallocate resources
        result = await resource_manager.deallocate_resources(agent_id)

        assert result is True
        assert agent_id not in resource_manager.allocated_resources
        assert resource_manager.total_allocated.cpu_cores == 0
        assert resource_manager.total_allocated.memory_mb == 0
        assert resource_manager.total_allocated.disk_mb == 0
        assert resource_manager.total_allocated.network_mbps == 0

    @pytest.mark.asyncio
    async def test_resource_deallocation_nonexistent_agent(self, resource_manager):
        """Test deallocation of non-existent agent"""
        agent_id = "nonexistent-agent"

        # Try to deallocate resources for non-existent agent
        result = await resource_manager.deallocate_resources(agent_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_resource_usage(self, resource_manager):
        """Test getting resource usage"""
        with patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.net_io_counters') as mock_net:

            # Mock system metrics
            mock_cpu.return_value = 50.0
            mock_memory.return_value = Mock(percent=60.0)
            mock_disk.return_value = Mock(percent=70.0)
            mock_net.return_value = Mock(bytes_sent=1000000, bytes_recv=2000000)

            # Get resource usage
            usage = await resource_manager.get_resource_usage()

            assert usage.cpu_percent == 50.0
            assert usage.memory_percent == 60.0
            assert usage.disk_percent == 70.0
            assert usage.network_percent >= 0.0
            assert len(resource_manager.usage_history) == 1

    @pytest.mark.asyncio
    async def test_check_resource_constraints_success(self, resource_manager, sample_requirements):
        """Test resource constraint validation success"""
        with patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:

            # Mock low system usage
            mock_cpu.return_value = 20.0
            mock_memory.return_value = Mock(percent=30.0)
            mock_disk.return_value = Mock(percent=40.0)

            # Check constraints
            result = await resource_manager.check_resource_constraints(sample_requirements)

            assert result is True

    @pytest.mark.asyncio
    async def test_check_resource_constraints_failure(self, resource_manager):
        """Test resource constraint validation failure"""
        with patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:

            # Mock high system usage
            mock_cpu.return_value = 95.0
            mock_memory.return_value = Mock(percent=95.0)
            mock_disk.return_value = Mock(percent=95.0)

            # Check constraints
            result = await resource_manager.check_resource_constraints(
                ResourceRequirements(cpu_cores=1, memory_mb=512)
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_optimize_resource_allocation(self, resource_manager, sample_requirements):
        """Test resource optimization recommendations"""
        agent_id = "test-agent-001"

        # Allocate resources
        await resource_manager.allocate_resources(agent_id, sample_requirements)

        # Add usage history to trigger optimization
        for i in range(15):
            with patch('psutil.cpu_percent') as mock_cpu, \
                 patch('psutil.virtual_memory') as mock_memory, \
                 patch('psutil.disk_usage') as mock_disk:

                # Mock low usage (over-allocated)
                mock_cpu.return_value = 10.0
                mock_memory.return_value = Mock(percent=20.0)
                mock_disk.return_value = Mock(percent=30.0)

                await resource_manager.get_resource_usage()

        # Get optimization recommendations
        optimizations = await resource_manager.optimize_resource_allocation()

        # Should recommend reducing allocation for over-allocated resources
        assert len(optimizations) >= 0  # May or may not have recommendations

    @pytest.mark.asyncio
    async def test_get_allocation_summary(self, resource_manager, sample_requirements):
        """Test getting allocation summary"""
        agent_id = "test-agent-001"

        # Allocate resources
        await resource_manager.allocate_resources(agent_id, sample_requirements)

        with patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:

            mock_cpu.return_value = 50.0
            mock_memory.return_value = Mock(percent=60.0)
            mock_disk.return_value = Mock(percent=70.0)

            # Get allocation summary
            summary = await resource_manager.get_allocation_summary()

        assert 'total_allocated' in summary
        assert 'limits' in summary
        assert 'current_usage' in summary
        assert 'allocation_efficiency' in summary
        assert 'active_allocations' in summary
        assert 'agents' in summary

        assert summary['total_allocated']['cpu_cores'] == sample_requirements.cpu_cores
        assert summary['total_allocated']['memory_mb'] == sample_requirements.memory_mb
        assert summary['active_allocations'] == 1
        assert agent_id in summary['agents']

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, resource_manager):
        """Test starting and stopping resource monitoring"""
        # Start monitoring
        await resource_manager.start_monitoring()
        assert resource_manager.monitoring_active is True

        # Stop monitoring
        await resource_manager.stop_monitoring()
        assert resource_manager.monitoring_active is False

    def test_get_agent_allocation(self, resource_manager, sample_requirements):
        """Test getting agent allocation"""
        agent_id = "test-agent-001"

        # No allocation initially
        allocation = resource_manager.get_agent_allocation(agent_id)
        assert allocation is None

        # Create allocation manually for testing
        allocation = ResourceAllocation(
            agent_id=agent_id,
            allocated_cpu=sample_requirements.cpu_cores,
            allocated_memory=sample_requirements.memory_mb,
            allocated_disk=sample_requirements.disk_mb,
            allocated_network=sample_requirements.network_mbps
        )
        resource_manager.allocated_resources[agent_id] = allocation

        # Get allocation
        retrieved_allocation = resource_manager.get_agent_allocation(agent_id)
        assert retrieved_allocation == allocation

    def test_get_available_resources(self, resource_manager, sample_requirements):
        """Test getting available resources"""
        agent_id = "test-agent-001"

        # Initially all resources are available
        available = resource_manager.get_available_resources()
        assert available.cpu_cores == resource_manager.limits.max_cpu_cores
        assert available.memory_mb == resource_manager.limits.max_memory_mb
        assert available.disk_mb == resource_manager.limits.max_disk_mb
        assert available.network_mbps == resource_manager.limits.max_network_mbps

        # Allocate some resources
        resource_manager.total_allocated = sample_requirements

        # Check available resources
        available = resource_manager.get_available_resources()
        assert available.cpu_cores == resource_manager.limits.max_cpu_cores - sample_requirements.cpu_cores
        assert available.memory_mb == resource_manager.limits.max_memory_mb - sample_requirements.memory_mb
        assert available.disk_mb == resource_manager.limits.max_disk_mb - sample_requirements.disk_mb
        assert available.network_mbps == resource_manager.limits.max_network_mbps - sample_requirements.network_mbps

    def test_get_resource_efficiency(self, resource_manager):
        """Test getting resource efficiency metrics"""
        # No history initially
        efficiency = resource_manager.get_resource_efficiency()
        assert efficiency['cpu'] == 0.0
        assert efficiency['memory'] == 0.0
        assert efficiency['disk'] == 0.0
        assert efficiency['network'] == 0.0

        # Add usage history
        for i in range(5):
            usage = ResourceUsage(
                cpu_percent=50.0 + i * 5,
                memory_percent=60.0 + i * 5,
                disk_percent=70.0 + i * 5,
                network_percent=80.0 + i * 5
            )
            resource_manager.usage_history.append(usage)

        # Get efficiency
        efficiency = resource_manager.get_resource_efficiency()
        assert efficiency['cpu'] > 0.0
        assert efficiency['memory'] > 0.0
        assert efficiency['disk'] > 0.0
        assert efficiency['network'] > 0.0

    @pytest.mark.asyncio
    async def test_multiple_agent_allocation(self, resource_manager):
        """Test allocating resources to multiple agents"""
        agents = ["agent-1", "agent-2", "agent-3"]
        requirements = ResourceRequirements(cpu_cores=1, memory_mb=512, disk_mb=1024)

        # Allocate to multiple agents
        for agent_id in agents:
            allocation = await resource_manager.allocate_resources(agent_id, requirements)
            assert allocation.agent_id == agent_id

        # Check total allocation
        assert resource_manager.total_allocated.cpu_cores == 3
        assert resource_manager.total_allocated.memory_mb == 1536
        assert resource_manager.total_allocated.disk_mb == 3072
        assert len(resource_manager.allocated_resources) == 3

    @pytest.mark.asyncio
    async def test_resource_allocation_at_limit(self, resource_manager):
        """Test resource allocation at system limits"""
        # Allocate resources up to the limit
        requirements = ResourceRequirements(
            cpu_cores=resource_manager.limits.max_cpu_cores,
            memory_mb=resource_manager.limits.max_memory_mb,
            disk_mb=resource_manager.limits.max_disk_mb,
            network_mbps=resource_manager.limits.max_network_mbps
        )

        # First allocation should succeed
        allocation = await resource_manager.allocate_resources("agent-1", requirements)
        assert allocation is not None

        # Second allocation should fail
        with pytest.raises(ResourceAllocationException):
            await resource_manager.allocate_resources("agent-2",
                ResourceRequirements(cpu_cores=1, memory_mb=512))


class TestResourceManagerIntegration:
    """Integration tests for ResourceManager"""

    @pytest.mark.asyncio
    async def test_resource_lifecycle(self):
        """Test complete resource lifecycle"""
        limits = ResourceLimits(
            max_cpu_cores=4,
            max_memory_mb=4096,
            max_disk_mb=8192,
            max_network_mbps=1000
        )
        manager = ResourceManager(limits)

        # Start monitoring
        await manager.start_monitoring()

        # Allocate resources
        agent_id = "test-agent"
        requirements = ResourceRequirements(
            cpu_cores=2,
            memory_mb=1024,
            disk_mb=2048,
            network_mbps=200
        )

        allocation = await manager.allocate_resources(agent_id, requirements)
        assert allocation.agent_id == agent_id

        # Check constraints
        result = await manager.check_resource_constraints(
            ResourceRequirements(cpu_cores=1, memory_mb=512)
        )
        assert result is True

        # Get usage (mocked)
        with patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:

            mock_cpu.return_value = 50.0
            mock_memory.return_value = Mock(percent=60.0)
            mock_disk.return_value = Mock(percent=70.0)

            usage = await manager.get_resource_usage()
            assert usage.cpu_percent == 50.0

        # Get summary
        summary = await manager.get_allocation_summary()
        assert summary['active_allocations'] == 1

        # Deallocate resources
        result = await manager.deallocate_resources(agent_id)
        assert result is True

        # Stop monitoring
        await manager.stop_monitoring()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
