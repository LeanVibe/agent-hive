"""
Performance validation tests for distributed state architecture.

Validates that the PostgreSQL + Redis migration meets performance targets
and resolves SQLite bottlenecks.
"""

import asyncio
import pytest
import time
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid

from state.postgresql_state_manager import PostgreSQLStateManager, PostgreSQLConfig
from state.redis_state_manager import RedisStateManager, RedisConfig
from state.hybrid_state_manager import HybridStateManager, HybridConfig


class PerformanceTestConfig:
    """Configuration for performance tests."""
    
    # Performance targets from migration specification
    MAX_CACHE_READ_LATENCY_MS = 10.0
    MAX_DB_WRITE_LATENCY_MS = 50.0
    MIN_CACHE_HIT_RATIO = 0.95
    MIN_CONCURRENT_AGENTS = 100
    MIN_TASK_THROUGHPUT = 1000  # tasks per second
    
    # Test parameters
    CONCURRENT_OPERATIONS = 100
    BATCH_SIZE = 1000
    TEST_DURATION_SECONDS = 30


@pytest.fixture
async def postgresql_manager():
    """PostgreSQL manager fixture for testing."""
    config = PostgreSQLConfig(
        host="localhost",
        port=5432,
        database="agent_hive_test",
        username="test_user",
        password="test_password",
        min_connections=5,
        max_connections=20
    )
    
    manager = PostgreSQLStateManager(config)
    if await manager.initialize():
        yield manager
        await manager.close()
    else:
        pytest.skip("PostgreSQL not available for testing")


@pytest.fixture
async def redis_manager():
    """Redis manager fixture for testing."""
    config = RedisConfig(
        host="localhost",
        port=6379,
        database=1,  # Use test database
        max_connections=20
    )
    
    manager = RedisStateManager(config)
    if await manager.initialize():
        yield manager
        await manager.close()
    else:
        pytest.skip("Redis not available for testing")


@pytest.fixture
async def hybrid_manager(postgresql_manager, redis_manager):
    """Hybrid manager fixture combining PostgreSQL and Redis."""
    pg_config = postgresql_manager.config
    redis_config = redis_manager.config
    
    hybrid_config = HybridConfig(
        postgresql_config=pg_config,
        redis_config=redis_config,
        cache_hit_ratio_target=PerformanceTestConfig.MIN_CACHE_HIT_RATIO
    )
    
    manager = HybridStateManager(hybrid_config)
    if await manager.initialize():
        yield manager
        await manager.close()
    else:
        pytest.skip("Hybrid manager initialization failed")


class PerformanceBenchmark:
    """Utility class for performance benchmarking."""
    
    @staticmethod
    async def measure_latency(operation) -> float:
        """Measure operation latency in milliseconds."""
        start_time = time.perf_counter()
        await operation()
        end_time = time.perf_counter()
        return (end_time - start_time) * 1000
    
    @staticmethod
    async def measure_throughput(operation, duration_seconds: int) -> float:
        """Measure operation throughput (operations per second)."""
        start_time = time.time()
        operations_completed = 0
        
        while (time.time() - start_time) < duration_seconds:
            await operation()
            operations_completed += 1
        
        actual_duration = time.time() - start_time
        return operations_completed / actual_duration
    
    @staticmethod
    async def concurrent_operations(operations: List, max_concurrent: int = 100):
        """Execute operations concurrently with controlled concurrency."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_operation(op):
            async with semaphore:
                return await op()
        
        tasks = [limited_operation(op) for op in operations]
        return await asyncio.gather(*tasks, return_exceptions=True)


@pytest.mark.asyncio
class TestPostgreSQLPerformance:
    """Test PostgreSQL performance characteristics."""
    
    async def test_agent_registration_latency(self, postgresql_manager):
        """Test agent registration meets latency requirements."""
        latencies = []
        
        for i in range(100):
            agent_id = f"test_agent_{i}_{uuid.uuid4()}"
            capabilities = ["test", "benchmark"]
            
            latency = await PerformanceBenchmark.measure_latency(
                lambda: postgresql_manager.register_agent(agent_id, capabilities)
            )
            latencies.append(latency)
        
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        
        assert avg_latency < PerformanceTestConfig.MAX_DB_WRITE_LATENCY_MS, \
            f"Average latency {avg_latency:.2f}ms exceeds target {PerformanceTestConfig.MAX_DB_WRITE_LATENCY_MS}ms"
        
        assert p95_latency < PerformanceTestConfig.MAX_DB_WRITE_LATENCY_MS * 2, \
            f"P95 latency {p95_latency:.2f}ms exceeds threshold"
    
    async def test_concurrent_agent_operations(self, postgresql_manager):
        """Test concurrent agent operations support."""
        agent_count = PerformanceTestConfig.MIN_CONCURRENT_AGENTS
        
        # Create operations for concurrent execution
        operations = []
        for i in range(agent_count):
            agent_id = f"concurrent_agent_{i}_{uuid.uuid4()}"
            capabilities = ["concurrent", "test"]
            operations.append(
                lambda aid=agent_id, caps=capabilities: postgresql_manager.register_agent(aid, caps)
            )
        
        start_time = time.time()
        results = await PerformanceBenchmark.concurrent_operations(operations, agent_count)
        duration = time.time() - start_time
        
        # Check that all operations succeeded
        successful_ops = sum(1 for r in results if not isinstance(r, Exception))
        assert successful_ops >= agent_count * 0.95, \
            f"Only {successful_ops}/{agent_count} operations succeeded"
        
        # Check duration is reasonable (should complete within seconds, not minutes)
        assert duration < 30, f"Concurrent operations took {duration:.2f}s, too slow"
    
    async def test_batch_operations_performance(self, postgresql_manager):
        """Test batch operations for improved performance."""
        batch_size = PerformanceTestConfig.BATCH_SIZE
        
        # Prepare batch update data
        updates = []
        agent_ids = []
        
        # First, create agents
        for i in range(batch_size):
            agent_id = f"batch_agent_{i}_{uuid.uuid4()}"
            agent_ids.append(agent_id)
            await postgresql_manager.register_agent(agent_id, ["batch", "test"])
        
        # Prepare batch updates
        for agent_id in agent_ids:
            updates.append({
                "agent_id": agent_id,
                "status": "busy",
                "context_usage": 0.75
            })
        
        # Measure batch update performance
        latency = await PerformanceBenchmark.measure_latency(
            lambda: postgresql_manager.batch_update_agents(updates)
        )
        
        # Batch operations should be much faster than individual operations
        max_batch_latency = PerformanceTestConfig.MAX_DB_WRITE_LATENCY_MS * 5  # Allow 5x for batch
        assert latency < max_batch_latency, \
            f"Batch update latency {latency:.2f}ms exceeds threshold {max_batch_latency}ms"


@pytest.mark.asyncio
class TestRedisPerformance:
    """Test Redis performance characteristics."""
    
    async def test_cache_read_latency(self, redis_manager):
        """Test cache read operations meet latency requirements."""
        # Set up test data
        test_data = {"status": "active", "context_usage": 0.5, "last_activity": datetime.now().isoformat()}
        agent_id = f"cache_test_{uuid.uuid4()}"
        
        await redis_manager.set_agent_state(agent_id, test_data)
        
        # Measure read latencies
        latencies = []
        for _ in range(100):
            latency = await PerformanceBenchmark.measure_latency(
                lambda: redis_manager.get_agent_state(agent_id)
            )
            latencies.append(latency)
        
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]
        
        assert avg_latency < PerformanceTestConfig.MAX_CACHE_READ_LATENCY_MS, \
            f"Average cache read latency {avg_latency:.2f}ms exceeds target {PerformanceTestConfig.MAX_CACHE_READ_LATENCY_MS}ms"
        
        assert p95_latency < PerformanceTestConfig.MAX_CACHE_READ_LATENCY_MS * 2, \
            f"P95 cache read latency {p95_latency:.2f}ms exceeds threshold"
    
    async def test_stream_throughput(self, redis_manager):
        """Test Redis Streams task queue throughput."""
        target_throughput = PerformanceTestConfig.MIN_TASK_THROUGHPUT
        test_duration = 5  # 5 seconds test
        
        async def queue_task():
            task_data = {
                "task_id": str(uuid.uuid4()),
                "priority": 5,
                "metadata": {"test": True}
            }
            return await redis_manager.queue_task(task_data)
        
        throughput = await PerformanceBenchmark.measure_throughput(
            queue_task, test_duration
        )
        
        assert throughput >= target_throughput * 0.8, \
            f"Stream throughput {throughput:.0f} ops/sec below target {target_throughput} ops/sec"
    
    async def test_concurrent_cache_operations(self, redis_manager):
        """Test concurrent cache operations."""
        concurrent_ops = PerformanceTestConfig.CONCURRENT_OPERATIONS
        
        # Prepare concurrent cache operations
        operations = []
        for i in range(concurrent_ops):
            agent_id = f"concurrent_cache_{i}_{uuid.uuid4()}"
            state_data = {"status": "busy", "priority": i % 10}
            
            operations.append(
                lambda aid=agent_id, data=state_data: redis_manager.set_agent_state(aid, data)
            )
        
        start_time = time.time()
        results = await PerformanceBenchmark.concurrent_operations(operations)
        duration = time.time() - start_time
        
        successful_ops = sum(1 for r in results if not isinstance(r, Exception))
        assert successful_ops >= concurrent_ops * 0.95, \
            f"Only {successful_ops}/{concurrent_ops} cache operations succeeded"
        
        # Should complete very quickly due to Redis performance
        assert duration < 5, f"Concurrent cache operations took {duration:.2f}s"


@pytest.mark.asyncio
class TestHybridManagerPerformance:
    """Test hybrid manager performance and cache effectiveness."""
    
    async def test_cache_hit_ratio(self, hybrid_manager):
        """Test cache hit ratio meets target."""
        # Set up test agents in the system
        agent_ids = []
        for i in range(50):
            agent_id = f"cache_ratio_test_{i}_{uuid.uuid4()}"
            agent_ids.append(agent_id)
            await hybrid_manager.register_agent(agent_id, ["test"])
        
        # First pass: populate cache
        for agent_id in agent_ids:
            await hybrid_manager.get_agent_state(agent_id)
        
        # Reset stats to measure actual cache performance
        hybrid_manager._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "read_operations": 0,
            "write_operations": 0,
            "average_latency": 0.0
        }
        
        # Second pass: should hit cache
        for _ in range(3):  # Multiple passes to test cache effectiveness
            for agent_id in agent_ids:
                await hybrid_manager.get_agent_state(agent_id)
        
        stats = hybrid_manager.get_performance_stats()
        cache_hit_ratio = stats["cache_hit_ratio"]
        
        assert cache_hit_ratio >= PerformanceTestConfig.MIN_CACHE_HIT_RATIO, \
            f"Cache hit ratio {cache_hit_ratio:.3f} below target {PerformanceTestConfig.MIN_CACHE_HIT_RATIO}"
    
    async def test_write_through_performance(self, hybrid_manager):
        """Test write-through caching performance."""
        agent_id = f"write_through_test_{uuid.uuid4()}"
        
        # Register agent
        await hybrid_manager.register_agent(agent_id, ["performance", "test"])
        
        # Measure write-through update performance
        update_data = {
            "status": "busy",
            "context_usage": 0.8,
            "performance_metrics": {"latency": 25.5, "throughput": 150}
        }
        
        latency = await PerformanceBenchmark.measure_latency(
            lambda: hybrid_manager.update_agent_state(agent_id, update_data)
        )
        
        assert latency < PerformanceTestConfig.MAX_DB_WRITE_LATENCY_MS * 1.5, \
            f"Write-through latency {latency:.2f}ms exceeds threshold"
        
        # Verify both stores are updated
        pg_state = await hybrid_manager.postgresql.get_agent_state(agent_id)
        cached_state = await hybrid_manager.redis.get_agent_state(agent_id)
        
        assert pg_state is not None, "PostgreSQL state not updated"
        assert cached_state is not None, "Cache not updated"
        assert pg_state["status"] == update_data["status"], "PostgreSQL state inconsistent"
        assert cached_state["status"] == update_data["status"], "Cache state inconsistent"
    
    async def test_concurrent_hybrid_operations(self, hybrid_manager):
        """Test concurrent operations across hybrid architecture."""
        concurrent_agents = PerformanceTestConfig.MIN_CONCURRENT_AGENTS
        
        # Mix of read and write operations
        operations = []
        
        # 70% reads, 30% writes (typical workload)
        for i in range(concurrent_agents):
            agent_id = f"hybrid_concurrent_{i}_{uuid.uuid4()}"
            
            if i < concurrent_agents * 0.7:  # Read operations
                operations.append(
                    lambda aid=agent_id: hybrid_manager.get_agent_state(aid)
                )
            else:  # Write operations
                capabilities = ["concurrent", "hybrid"]
                operations.append(
                    lambda aid=agent_id, caps=capabilities: hybrid_manager.register_agent(aid, caps)
                )
        
        start_time = time.time()
        results = await PerformanceBenchmark.concurrent_operations(operations)
        duration = time.time() - start_time
        
        # Count successful operations
        successful_ops = sum(1 for r in results if not isinstance(r, Exception))
        success_rate = successful_ops / len(operations)
        
        assert success_rate >= 0.95, \
            f"Success rate {success_rate:.3f} below 95% threshold"
        
        assert duration < 20, \
            f"Concurrent hybrid operations took {duration:.2f}s, too slow"


@pytest.mark.asyncio
class TestPerformanceRegression:
    """Test for performance regressions compared to SQLite."""
    
    async def test_no_performance_regression(self, hybrid_manager):
        """Ensure distributed architecture performs better than SQLite baseline."""
        # This test would normally compare against SQLite performance
        # For now, we validate against absolute performance targets
        
        agent_id = f"regression_test_{uuid.uuid4()}"
        
        # Agent registration (write operation)
        register_latency = await PerformanceBenchmark.measure_latency(
            lambda: hybrid_manager.register_agent(agent_id, ["regression", "test"])
        )
        
        # Agent state retrieval (read operation)
        read_latency = await PerformanceBenchmark.measure_latency(
            lambda: hybrid_manager.get_agent_state(agent_id)
        )
        
        # These should be significantly better than SQLite's ~2500ms write times
        assert register_latency < 100, \
            f"Registration latency {register_latency:.2f}ms indicates regression"
        
        assert read_latency < 20, \
            f"Read latency {read_latency:.2f}ms indicates regression"
    
    async def test_memory_efficiency(self, hybrid_manager):
        """Test memory usage remains efficient under load."""
        # Create many agents to test memory usage
        agent_count = 1000
        
        # Get baseline memory usage
        initial_health = await hybrid_manager.health_check()
        initial_redis_memory = initial_health["redis"]["memory_usage"]["used_memory"]
        
        # Create agents
        for i in range(agent_count):
            agent_id = f"memory_test_{i}_{uuid.uuid4()}"
            await hybrid_manager.register_agent(agent_id, ["memory", "test"])
        
        # Check memory usage
        final_health = await hybrid_manager.health_check()
        final_redis_memory = final_health["redis"]["memory_usage"]["used_memory"]
        
        memory_increase = final_redis_memory - initial_redis_memory
        memory_per_agent = memory_increase / agent_count
        
        # Each agent should use less than 1KB in Redis (very conservative)
        assert memory_per_agent < 1024, \
            f"Memory usage per agent {memory_per_agent:.0f} bytes too high"


# Performance test runner
if __name__ == "__main__":
    async def run_performance_tests():
        """Run all performance tests."""
        import sys
        
        # Configure test logging
        import logging
        logging.basicConfig(level=logging.INFO)
        
        print("🚀 Running Distributed State Performance Tests...")
        
        # Run pytest with performance markers
        import subprocess
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            __file__,
            "-v",
            "--tb=short",
            "-x"  # Stop on first failure
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        
        return result.returncode == 0
    
    # Run the tests
    success = asyncio.run(run_performance_tests())
    exit(0 if success else 1)