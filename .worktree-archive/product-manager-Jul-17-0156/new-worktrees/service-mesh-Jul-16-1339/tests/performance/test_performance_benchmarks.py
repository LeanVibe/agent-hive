"""
Performance benchmarks for LeanVibe Quality Agent

This module provides comprehensive performance benchmarks to ensure
the system meets performance requirements and detect regressions.
"""

import pytest
import time
import asyncio
import sys
import tempfile
import concurrent.futures
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add the .claude directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude'))

from state.state_manager import StateManager, AgentState, TaskState
from task_queue_module.task_queue import TaskQueue, Task


class PerformanceBenchmarks:
    """Performance benchmarking utilities."""

    @staticmethod
    def benchmark_function(func, *args, **kwargs):
        """Benchmark a function execution time."""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()

        return {
            "result": result,
            "duration": end_time - start_time,
            "timestamp": datetime.now().isoformat()
        }

    @staticmethod
    async def benchmark_async_function(func, *args, **kwargs):
        """Benchmark an async function execution time."""
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        end_time = time.perf_counter()

        return {
            "result": result,
            "duration": end_time - start_time,
            "timestamp": datetime.now().isoformat()
        }

    @staticmethod
    def assert_performance_threshold(benchmark_result: Dict[str, Any],
                                   threshold: float,
                                   operation: str):
        """Assert that a benchmark meets performance threshold."""
        duration = benchmark_result["duration"]
        assert duration <= threshold, (
            f"{operation} took {duration:.4f}s, "
            f"expected <= {threshold:.4f}s"
        )


@pytest.mark.performance
class TestStateManagerPerformance:
    """Performance tests for StateManager."""

    def test_state_manager_init_performance(self):
        """Test StateManager initialization performance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            benchmark = PerformanceBenchmarks.benchmark_function(
                StateManager, Path(temp_dir)
            )

            # Should initialize within 100ms
            PerformanceBenchmarks.assert_performance_threshold(
                benchmark, 0.1, "StateManager initialization"
            )

    def test_agent_state_crud_performance(self):
        """Test agent state CRUD operations performance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = StateManager(Path(temp_dir))

            # Create test agent state
            agent_state = AgentState(
                agent_id="perf-test-agent",
                status="idle",
                context_usage=0.5,
                capabilities=["python", "javascript"],
                performance_metrics={"speed": 0.8, "accuracy": 0.9}
            )

            # Test create performance
            create_benchmark = PerformanceBenchmarks.benchmark_function(
                manager.update_agent_state, agent_state
            )
            PerformanceBenchmarks.assert_performance_threshold(
                create_benchmark, 0.05, "Agent state creation"
            )

            # Test read performance
            read_benchmark = PerformanceBenchmarks.benchmark_function(
                manager.get_agent_state, "perf-test-agent"
            )
            PerformanceBenchmarks.assert_performance_threshold(
                read_benchmark, 0.01, "Agent state read"
            )

            # Test update performance
            agent_state.status = "busy"
            update_benchmark = PerformanceBenchmarks.benchmark_function(
                manager.update_agent_state, agent_state
            )
            PerformanceBenchmarks.assert_performance_threshold(
                update_benchmark, 0.05, "Agent state update"
            )

    def test_task_state_crud_performance(self):
        """Test task state CRUD operations performance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = StateManager(Path(temp_dir))

            # Create test task state
            task_state = TaskState(
                task_id="perf-test-task",
                status="pending",
                agent_id="perf-test-agent",
                priority=1,
                metadata={"type": "performance_test", "complexity": "high"}
            )

            # Test create performance
            create_benchmark = PerformanceBenchmarks.benchmark_function(
                manager.update_task_state, task_state
            )
            PerformanceBenchmarks.assert_performance_threshold(
                create_benchmark, 0.05, "Task state creation"
            )

            # Test read performance
            read_benchmark = PerformanceBenchmarks.benchmark_function(
                manager.get_task_state, "perf-test-task"
            )
            PerformanceBenchmarks.assert_performance_threshold(
                read_benchmark, 0.01, "Task state read"
            )

    def test_bulk_operations_performance(self):
        """Test bulk operations performance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = StateManager(Path(temp_dir))

            # Create 100 agent states
            agents = [
                AgentState(
                    agent_id=f"agent-{i:03d}",
                    status="idle",
                    context_usage=0.1 * i,
                    capabilities=["python"],
                    performance_metrics={"speed": 0.8}
                )
                for i in range(100)
            ]

            # Test bulk create performance
            start_time = time.perf_counter()
            for agent in agents:
                manager.update_agent_state(agent)
            bulk_create_time = time.perf_counter() - start_time

            # Should create 100 agents within 2 seconds
            assert bulk_create_time <= 2.0, (
                f"Bulk agent creation took {bulk_create_time:.4f}s, "
                f"expected <= 2.0s"
            )

            # Test bulk read performance
            start_time = time.perf_counter()
            for i in range(100):
                manager.get_agent_state(f"agent-{i:03d}")
            bulk_read_time = time.perf_counter() - start_time

            # Should read 100 agents within 1 second
            assert bulk_read_time <= 1.0, (
                f"Bulk agent read took {bulk_read_time:.4f}s, "
                f"expected <= 1.0s"
            )

    def test_concurrent_operations_performance(self):
        """Test concurrent operations performance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = StateManager(Path(temp_dir))

            def update_agent_state(agent_id: str):
                """Update agent state in thread."""
                agent_state = AgentState(
                    agent_id=agent_id,
                    status="busy",
                    context_usage=0.75,
                    capabilities=["concurrent_test"],
                    performance_metrics={"speed": 0.9}
                )
                manager.update_agent_state(agent_state)
                return manager.get_agent_state(agent_id)

            # Test concurrent updates
            start_time = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(update_agent_state, f"concurrent-agent-{i}")
                    for i in range(50)
                ]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]

            concurrent_time = time.perf_counter() - start_time

            # Should handle 50 concurrent operations within 3 seconds
            assert concurrent_time <= 3.0, (
                f"Concurrent operations took {concurrent_time:.4f}s, "
                f"expected <= 3.0s"
            )

            # Verify all operations completed successfully
            assert len(results) == 50
            assert all(result is not None for result in results)


@pytest.mark.performance
class TestTaskQueuePerformance:
    """Performance tests for TaskQueue."""

    @pytest.mark.asyncio
    async def test_task_queue_operations_performance(self):
        """Test task queue operations performance."""
        queue = TaskQueue()

        # Create test tasks
        tasks = [
            Task(
                id=f"perf-task-{i:03d}",
                type="performance_test",
                description=f"Performance test task {i}",
                priority=i % 10,
                data={"test_data": f"data_{i}"}
            )
            for i in range(100)
        ]

        # Test bulk enqueue performance
        enqueue_benchmark = await PerformanceBenchmarks.benchmark_async_function(
            self._bulk_enqueue, queue, tasks
        )
        PerformanceBenchmarks.assert_performance_threshold(
            enqueue_benchmark, 0.5, "Bulk task enqueue"
        )

        # Test bulk dequeue performance
        dequeue_benchmark = await PerformanceBenchmarks.benchmark_async_function(
            self._bulk_dequeue, queue, 100
        )
        PerformanceBenchmarks.assert_performance_threshold(
            dequeue_benchmark, 0.5, "Bulk task dequeue"
        )

    async def _bulk_enqueue(self, queue: TaskQueue, tasks: List[Task]):
        """Enqueue tasks in bulk."""
        for task in tasks:
            await queue.enqueue(task)

    async def _bulk_dequeue(self, queue: TaskQueue, count: int):
        """Dequeue tasks in bulk."""
        results = []
        for _ in range(count):
            task = await queue.dequeue()
            if task:
                results.append(task)
        return results

    @pytest.mark.asyncio
    async def test_task_queue_concurrent_access(self):
        """Test task queue concurrent access performance."""
        queue = TaskQueue()

        async def producer():
            """Producer coroutine."""
            for i in range(50):
                task = Task(
                    id=f"concurrent-task-{i:03d}",
                    type="concurrent_test",
                    description=f"Concurrent test task {i}",
                    priority=5,
                    data={"producer": "test"}
                )
                await queue.enqueue(task)

        async def consumer():
            """Consumer coroutine."""
            consumed = 0
            while consumed < 50:
                task = await queue.dequeue()
                if task:
                    consumed += 1
                else:
                    await asyncio.sleep(0.01)  # Small delay if no task available
            return consumed

        # Test concurrent producer/consumer
        start_time = time.perf_counter()

        # Run producer and consumer concurrently
        producer_task = asyncio.create_task(producer())
        consumer_task = asyncio.create_task(consumer())

        await asyncio.gather(producer_task, consumer_task)

        concurrent_time = time.perf_counter() - start_time

        # Should handle concurrent access within 2 seconds
        assert concurrent_time <= 2.0, (
            f"Concurrent access took {concurrent_time:.4f}s, "
            f"expected <= 2.0s"
        )


@pytest.mark.performance
class TestMemoryPerformance:
    """Memory performance tests."""

    def test_memory_usage_under_load(self):
        """Test memory usage under load."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create large number of objects
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = StateManager(Path(temp_dir))

            # Create 1000 agent states
            for i in range(1000):
                agent_state = AgentState(
                    agent_id=f"memory-test-agent-{i:04d}",
                    status="idle",
                    context_usage=0.5,
                    capabilities=["python", "javascript", "memory_test"],
                    performance_metrics={
                        "speed": 0.8,
                        "accuracy": 0.9,
                        "memory_efficiency": 0.85
                    },
                    metadata={
                        "test_data": f"large_data_string_{i}" * 100,
                        "iteration": i,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                manager.update_agent_state(agent_state)

            # Check memory usage
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory

            # Should not use more than 50MB additional memory
            assert memory_increase <= 50, (
                f"Memory increase: {memory_increase:.2f}MB, "
                f"expected <= 50MB"
            )

    def test_memory_cleanup_performance(self):
        """Test memory cleanup performance."""
        import gc
        import psutil
        import os

        process = psutil.Process(os.getpid())

        # Create and destroy objects
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = StateManager(Path(temp_dir))

            # Create large dataset
            for i in range(500):
                agent_state = AgentState(
                    agent_id=f"cleanup-test-agent-{i:04d}",
                    status="idle",
                    context_usage=0.5,
                    capabilities=["cleanup_test"],
                    performance_metrics={"speed": 0.8},
                    metadata={"large_data": "x" * 10000}
                )
                manager.update_agent_state(agent_state)

            memory_before_cleanup = process.memory_info().rss / 1024 / 1024

            # Cleanup old data
            cleanup_benchmark = PerformanceBenchmarks.benchmark_function(
                manager.cleanup_old_data, 0  # Clean all data
            )

            # Force garbage collection
            gc.collect()

            memory_after_cleanup = process.memory_info().rss / 1024 / 1024

            # Cleanup should complete within 2 seconds
            PerformanceBenchmarks.assert_performance_threshold(
                cleanup_benchmark, 2.0, "Memory cleanup"
            )

            # Should free some memory (at least 5MB)
            memory_freed = memory_before_cleanup - memory_after_cleanup
            assert memory_freed >= 5, (
                f"Memory freed: {memory_freed:.2f}MB, "
                f"expected >= 5MB"
            )


@pytest.mark.performance
@pytest.mark.asyncio
class TestSystemPerformance:
    """System-level performance tests."""

    async def test_end_to_end_performance(self):
        """Test end-to-end system performance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = StateManager(Path(temp_dir))
            queue = TaskQueue()

            # Simulate end-to-end workflow
            start_time = time.perf_counter()

            # Step 1: Create agent
            agent_state = AgentState(
                agent_id="e2e-test-agent",
                status="idle",
                context_usage=0.0,
                capabilities=["python", "javascript"],
                performance_metrics={"speed": 0.8}
            )
            manager.update_agent_state(agent_state)

            # Step 2: Create and enqueue tasks
            tasks = []
            for i in range(10):
                task = Task(
                    id=f"e2e-task-{i:02d}",
                    type="code_generation",
                    description=f"Generate code for task {i}",
                    priority=5,
                    data={"prompt": f"Generate function {i}"}
                )
                tasks.append(task)
                await queue.enqueue(task)

            # Step 3: Process tasks
            for task in tasks:
                # Simulate task processing
                dequeued_task = await queue.dequeue()
                assert dequeued_task is not None

                # Update agent state
                agent_state.status = "busy"
                agent_state.context_usage = 0.75
                manager.update_agent_state(agent_state)

                # Create task state
                task_state = TaskState(
                    task_id=dequeued_task.id,
                    status="completed",
                    agent_id="e2e-test-agent",
                    priority=5,
                    metadata={"completion_time": time.perf_counter()}
                )
                manager.update_task_state(task_state)

            # Step 4: Finalize
            agent_state.status = "idle"
            agent_state.context_usage = 0.0
            manager.update_agent_state(agent_state)

            total_time = time.perf_counter() - start_time

            # End-to-end workflow should complete within 5 seconds
            assert total_time <= 5.0, (
                f"End-to-end workflow took {total_time:.4f}s, "
                f"expected <= 5.0s"
            )

            # Verify system state
            system_state = manager.get_system_state()
            assert system_state.active_agents >= 0
            assert system_state.completed_tasks >= 0
