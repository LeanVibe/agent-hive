"""
Tests for EventStreaming component.
"""

import pytest
from datetime import datetime

pytestmark = pytest.mark.asyncio

from external_api.event_streaming import EventStreaming, EventBuffer
from external_api.models import (
    EventStreamConfig,
    StreamEvent,
    EventPriority
)


class TestEventBuffer:
    """Test suite for EventBuffer class."""

    @pytest.fixture
    def event_buffer(self):
        """Create EventBuffer instance."""
        return EventBuffer(max_size=5)

    @pytest.fixture
    def sample_event(self):
        """Create sample stream event."""
        return StreamEvent(
            event_id="test-123",
            event_type="task_created",
            timestamp=datetime.now(),
            data={"task_id": "123", "description": "Test task"},
            partition_key="tasks"
        )

    async def test_buffer_initialization(self, event_buffer):
        """Test event buffer initialization."""
        assert event_buffer.max_size == 5
        assert len(event_buffer.buffer) == 0
        assert event_buffer._total_events == 0
        assert event_buffer._dropped_events == 0

    async def test_add_event_success(self, event_buffer, sample_event):
        """Test successful event addition."""
        result = await event_buffer.add_event(sample_event)
        assert result is True
        assert len(event_buffer.buffer) == 1
        assert event_buffer._total_events == 1
        assert event_buffer._dropped_events == 0

    async def test_add_event_buffer_full(self, event_buffer, sample_event):
        """Test adding events when buffer is full."""
        # Fill buffer to capacity
        for i in range(5):
            event = StreamEvent(
                event_id=f"test-{i}",
                event_type="test",
                timestamp=datetime.now(),
                data={"id": i},
                partition_key="test"
            )
            result = await event_buffer.add_event(event)
            assert result is True

        # Try to add one more (should fail)
        result = await event_buffer.add_event(sample_event)
        assert result is False
        assert len(event_buffer.buffer) == 5  # Still at max
        assert event_buffer._dropped_events == 1

    async def test_get_events(self, event_buffer):
        """Test event retrieval."""
        # Add test events
        events = []
        for i in range(3):
            event = StreamEvent(
                event_id=f"test-{i}",
                event_type="test",
                timestamp=datetime.now(),
                data={"id": i},
                partition_key="test"
            )
            events.append(event)
            await event_buffer.add_event(event)

        # Get all events
        retrieved = await event_buffer.get_events(3)
        assert len(retrieved) == 3
        assert len(event_buffer.buffer) == 0  # Buffer should be empty

        # Verify order (FIFO)
        for i, event in enumerate(retrieved):
            assert event.event_id == f"test-{i}"

    async def test_get_events_partial(self, event_buffer):
        """Test partial event retrieval."""
        # Add test events
        for i in range(3):
            event = StreamEvent(
                event_id=f"test-{i}",
                event_type="test",
                timestamp=datetime.now(),
                data={"id": i},
                partition_key="test"
            )
            await event_buffer.add_event(event)

        # Get only 2 events
        retrieved = await event_buffer.get_events(2)
        assert len(retrieved) == 2
        assert len(event_buffer.buffer) == 1  # One left

        # Get remaining event
        remaining = await event_buffer.get_events(1)
        assert len(remaining) == 1
        assert remaining[0].event_id == "test-2"

    async def test_get_stats(self, event_buffer):
        """Test buffer statistics."""
        # Initial stats
        stats = await event_buffer.get_stats()
        assert stats["current_size"] == 0
        assert stats["max_size"] == 5
        assert stats["total_events"] == 0
        assert stats["dropped_events"] == 0
        assert stats["utilization"] == 0.0

        # Add some events
        for i in range(3):
            event = StreamEvent(
                event_id=f"test-{i}",
                event_type="test",
                timestamp=datetime.now(),
                data={"id": i},
                partition_key="test"
            )
            await event_buffer.add_event(event)

        stats = await event_buffer.get_stats()
        assert stats["current_size"] == 3
        assert stats["total_events"] == 3
        assert stats["utilization"] == 0.6  # 3/5


class TestEventStreaming:
    """Test suite for EventStreaming class."""

    @pytest.fixture
    def stream_config(self):
        """Create test event streaming configuration."""
        return EventStreamConfig(
            stream_name="test-stream",
            buffer_size=10,
            flush_interval=1,  # 1 second for faster testing
            max_retries=2,
            retry_delay=0.1,  # 100ms for faster testing
            compression_enabled=True,
            batch_size=5
        )

    @pytest.fixture
    def event_streaming(self, stream_config):
        """Create EventStreaming instance."""
        return EventStreaming(stream_config)

    @pytest.fixture
    def sample_event_data(self):
        """Create sample event data."""
        return {
            "task_id": "test-123",
            "description": "Test task",
            "status": "created"
        }

    async def test_streaming_initialization(self, event_streaming, stream_config):
        """Test event streaming initialization."""
        assert event_streaming.config == stream_config
        assert isinstance(event_streaming.buffer, EventBuffer)
        assert event_streaming.consumers == {}
        assert event_streaming.filters == {}
        assert not event_streaming.stream_active
        assert event_streaming.flush_task is None
        assert event_streaming.stats["events_processed"] == 0

    async def test_start_stop_streaming(self, event_streaming):
        """Test streaming start and stop functionality."""
        # Test start
        await event_streaming.start_streaming()
        assert event_streaming.stream_active
        assert event_streaming.flush_task is not None

        # Test start when already active
        await event_streaming.start_streaming()  # Should not raise error
        assert event_streaming.stream_active

        # Test stop
        await event_streaming.stop_streaming()
        assert not event_streaming.stream_active
        assert event_streaming.flush_task.cancelled()

        # Test stop when not active
        await event_streaming.stop_streaming()  # Should not raise error
        assert not event_streaming.stream_active

    async def test_publish_event_success(self, event_streaming, sample_event_data):
        """Test successful event publishing."""
        await event_streaming.start_streaming()

        result = await event_streaming.publish_event(
            event_type="task_created",
            data=sample_event_data,
            partition_key="tasks",
            priority=EventPriority.MEDIUM
        )

        assert result is True
        assert event_streaming.stats["events_processed"] == 1

    async def test_publish_event_stream_not_active(self, event_streaming, sample_event_data):
        """Test publishing when streaming is not active."""
        result = await event_streaming.publish_event(
            event_type="task_created",
            data=sample_event_data,
            partition_key="tasks"
        )

        assert result is False
        assert event_streaming.stats["events_processed"] == 0

    async def test_register_consumer(self, event_streaming):
        """Test consumer registration."""
        async def test_consumer(batch_data):
            return {"processed": True}

        # Test successful registration
        event_streaming.register_consumer("test-consumer", test_consumer)
        assert "test-consumer" in event_streaming.consumers
        assert event_streaming.consumers["test-consumer"] == test_consumer

        # Test non-async consumer rejection
        def sync_consumer(batch_data):
            return {"processed": True}

        with pytest.raises(ValueError, match="Consumer function must be async"):
            event_streaming.register_consumer("sync-consumer", sync_consumer)

    async def test_unregister_consumer(self, event_streaming):
        """Test consumer unregistration."""
        async def test_consumer(batch_data):
            return {"processed": True}

        # Register consumer first
        event_streaming.register_consumer("test-consumer", test_consumer)

        # Test successful unregistration
        result = event_streaming.unregister_consumer("test-consumer")
        assert result is True
        assert "test-consumer" not in event_streaming.consumers

        # Test unregistration of non-existent consumer
        result = event_streaming.unregister_consumer("non-existent")
        assert result is False

    async def test_add_filter(self, event_streaming):
        """Test filter addition."""
        async def test_filter(event):
            return event.priority == EventPriority.HIGH

        # Test successful addition
        event_streaming.add_filter("priority-filter", test_filter)
        assert "priority-filter" in event_streaming.filters
        assert event_streaming.filters["priority-filter"] == test_filter

        # Test non-async filter rejection
        def sync_filter(event):
            return True

        with pytest.raises(ValueError, match="Filter function must be async"):
            event_streaming.add_filter("sync-filter", sync_filter)

    async def test_remove_filter(self, event_streaming):
        """Test filter removal."""
        async def test_filter(event):
            return True

        # Add filter first
        event_streaming.add_filter("test-filter", test_filter)

        # Test successful removal
        result = event_streaming.remove_filter("test-filter")
        assert result is True
        assert "test-filter" not in event_streaming.filters

        # Test removal of non-existent filter
        result = event_streaming.remove_filter("non-existent")
        assert result is False

    async def test_event_filtering(self, event_streaming, sample_event_data):
        """Test event filtering during publishing."""
        await event_streaming.start_streaming()

        # Add filter that rejects events
        async def reject_filter(event):
            return False

        event_streaming.add_filter("reject-all", reject_filter)

        result = await event_streaming.publish_event(
            event_type="task_created",
            data=sample_event_data,
            partition_key="tasks"
        )

        assert result is False
        assert event_streaming.stats["events_processed"] == 0

    async def test_flush_events_to_consumers(self, event_streaming, sample_event_data):
        """Test event flushing to consumers."""
        consumed_batches = []

        async def test_consumer(batch_data):
            consumed_batches.append(batch_data)
            return {"processed": True}

        event_streaming.register_consumer("test-consumer", test_consumer)
        await event_streaming.start_streaming()

        # Publish some events
        for i in range(3):
            await event_streaming.publish_event(
                event_type="task_created",
                data={**sample_event_data, "id": i},
                partition_key="tasks"
            )

        # Manually trigger flush
        await event_streaming._flush_events()

        # Should have one batch with 3 events
        assert len(consumed_batches) == 1
        batch = consumed_batches[0]
        assert batch["event_count"] == 3
        assert batch["stream_name"] == "test-stream"
        assert "events" in batch

    async def test_compression(self, event_streaming, sample_event_data):
        """Test batch compression."""
        events = []
        for i in range(3):
            event = StreamEvent(
                event_id=f"test-{i}",
                event_type="task_created",
                timestamp=datetime.now(),
                data={**sample_event_data, "id": i},
                partition_key="tasks"
            )
            events.append(event)

        # Test compression
        batch_data = await event_streaming._prepare_batch(events)

        if event_streaming.config.compression_enabled:
            assert batch_data.get("compressed") is True
            assert "compressed_size" in batch_data
            assert "original_size" in batch_data
            assert batch_data["compressed_size"] < batch_data["original_size"]

    async def test_consumer_retry_logic(self, event_streaming, sample_event_data):
        """Test consumer retry logic on failures."""
        attempt_count = 0

        async def failing_consumer(batch_data):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:  # Fail first 2 attempts
                raise Exception("Consumer error")
            return {"processed": True}

        event_streaming.register_consumer("failing-consumer", failing_consumer)

        # Create batch and deliver
        events = [StreamEvent(
            event_id="test-1",
            event_type="task_created",
            timestamp=datetime.now(),
            data=sample_event_data,
            partition_key="tasks"
        )]

        batch_data = await event_streaming._prepare_batch(events)

        # Should succeed after retries
        await event_streaming._deliver_to_consumer(
            "failing-consumer",
            failing_consumer,
            batch_data
        )

        assert attempt_count == 3  # Initial + 2 retries

    async def test_priority_grouping(self, event_streaming):
        """Test event grouping by priority."""
        events = [
            StreamEvent(
                event_id="high-1",
                event_type="alert",
                timestamp=datetime.now(),
                data={"alert": "critical"},
                partition_key="alerts",
                priority=EventPriority.HIGH
            ),
            StreamEvent(
                event_id="low-1",
                event_type="log",
                timestamp=datetime.now(),
                data={"log": "info"},
                partition_key="logs",
                priority=EventPriority.LOW
            ),
            StreamEvent(
                event_id="high-2",
                event_type="alert",
                timestamp=datetime.now(),
                data={"alert": "error"},
                partition_key="alerts",
                priority=EventPriority.HIGH
            )
        ]

        groups = event_streaming._group_events_by_priority(events)

        assert len(groups) == 2
        assert len(groups[EventPriority.HIGH]) == 2
        assert len(groups[EventPriority.LOW]) == 1
        assert groups[EventPriority.HIGH][0].event_id == "high-1"
        assert groups[EventPriority.HIGH][1].event_id == "high-2"
        assert groups[EventPriority.LOW][0].event_id == "low-1"

    async def test_get_stream_info(self, event_streaming):
        """Test stream information retrieval."""
        async def consumer1(batch):
            pass

        async def filter1(event):
            return True

        event_streaming.register_consumer("consumer1", consumer1)
        event_streaming.add_filter("filter1", filter1)

        info = event_streaming.get_stream_info()

        assert info["stream_name"] == "test-stream"
        assert info["stream_active"] is False
        assert info["consumers_count"] == 1
        assert info["filters_count"] == 1
        assert "config" in info
        assert "statistics" in info

    async def test_get_buffer_stats(self, event_streaming):
        """Test buffer statistics retrieval."""
        stats = await event_streaming.get_buffer_stats()

        assert "current_size" in stats
        assert "max_size" in stats
        assert "total_events" in stats
        assert "dropped_events" in stats
        assert "utilization" in stats

    async def test_health_check(self, event_streaming):
        """Test health check functionality."""
        # Health check when stopped
        health = await event_streaming.health_check()
        assert health["status"] == "unhealthy"
        assert health["stream_active"] is False

        # Start streaming and check again
        await event_streaming.start_streaming()
        health = await event_streaming.health_check()
        assert health["status"] == "healthy"
        assert health["stream_active"] is True
        assert "timestamp" in health

    async def test_stream_config_validation(self):
        """Test event stream configuration validation."""
        # Test invalid buffer size
        with pytest.raises(ValueError, match="Buffer size must be positive"):
            EventStreamConfig(buffer_size=0)

        # Test invalid flush interval
        with pytest.raises(ValueError, match="Flush interval must be positive"):
            EventStreamConfig(flush_interval=0)

        # Test invalid max retries
        with pytest.raises(ValueError, match="Max retries must be non-negative"):
            EventStreamConfig(max_retries=-1)

    async def test_stream_event_validation(self):
        """Test stream event validation."""
        # Test valid event
        event = StreamEvent(
            event_id="test-123",
            event_type="task_created",
            timestamp=datetime.now(),
            data={"task": "test"},
            partition_key="tasks"
        )
        assert event.event_id == "test-123"

        # Test empty event ID
        with pytest.raises(ValueError, match="Event ID cannot be empty"):
            StreamEvent(
                event_id="",
                event_type="task_created",
                timestamp=datetime.now(),
                data={"task": "test"},
                partition_key="tasks"
            )

        # Test empty event type
        with pytest.raises(ValueError, match="Event type cannot be empty"):
            StreamEvent(
                event_id="test-123",
                event_type="",
                timestamp=datetime.now(),
                data={"task": "test"},
                partition_key="tasks"
            )

        # Test empty partition key
        with pytest.raises(ValueError, match="Partition key cannot be empty"):
            StreamEvent(
                event_id="test-123",
                event_type="task_created",
                timestamp=datetime.now(),
                data={"task": "test"},
                partition_key=""
            )
