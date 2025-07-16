"""
Event Streaming for External API Integration

Provides real-time event streaming capabilities for broadcasting
system events to external consumers and handling event processing.
"""

import asyncio
import json
import logging
import time
import uuid
import gzip
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, AsyncGenerator
from dataclasses import asdict
from collections import deque

from .models import (
    EventStreamConfig,
    StreamEvent,
    EventPriority
)


logger = logging.getLogger(__name__)


class EventBuffer:
    """Thread-safe event buffer for streaming."""
    
    def __init__(self, max_size: int):
        """Initialize event buffer."""
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)
        self.lock = asyncio.Lock()
        self._total_events = 0
        self._dropped_events = 0
    
    async def add_event(self, event: StreamEvent) -> bool:
        """
        Add event to buffer.
        
        Args:
            event: Stream event to add
            
        Returns:
            True if added successfully, False if buffer full
        """
        async with self.lock:
            if len(self.buffer) >= self.max_size:
                self._dropped_events += 1
                return False
            
            self.buffer.append(event)
            self._total_events += 1
            return True
    
    async def get_events(self, count: int) -> List[StreamEvent]:
        """
        Get events from buffer.
        
        Args:
            count: Maximum number of events to retrieve
            
        Returns:
            List of events
        """
        async with self.lock:
            events = []
            for _ in range(min(count, len(self.buffer))):
                if self.buffer:
                    events.append(self.buffer.popleft())
            return events
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get buffer statistics."""
        async with self.lock:
            return {
                "current_size": len(self.buffer),
                "max_size": self.max_size,
                "total_events": self._total_events,
                "dropped_events": self._dropped_events,
                "utilization": len(self.buffer) / self.max_size if self.max_size > 0 else 0
            }


class EventStreaming:
    """
    Event streaming system for real-time event distribution.
    
    Provides event buffering, compression, batching, and delivery
    to external consumers with retry mechanisms.
    """
    
    def __init__(self, config: EventStreamConfig):
        """
        Initialize event streaming system.
        
        Args:
            config: Event streaming configuration
        """
        self.config = config
        self.buffer = EventBuffer(config.buffer_size)
        self.consumers: Dict[str, Callable] = {}
        self.filters: Dict[str, Callable] = {}
        self.stream_active = False
        self.flush_task: Optional[asyncio.Task] = None
        self.stats = {
            "events_processed": 0,
            "events_delivered": 0,
            "events_failed": 0,
            "batches_sent": 0,
            "compression_ratio": 0.0
        }
        
        logger.info(f"EventStreaming initialized for stream: {config.stream_name}")
    
    async def start_streaming(self) -> None:
        """Start the event streaming system."""
        if self.stream_active:
            logger.warning("Event streaming already active")
            return
            
        try:
            logger.info(f"Starting event streaming for: {self.config.stream_name}")
            
            self.stream_active = True
            self.flush_task = asyncio.create_task(self._flush_loop())
            
            logger.info("Event streaming started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start event streaming: {e}")
            raise
    
    async def stop_streaming(self) -> None:
        """Stop the event streaming system."""
        if not self.stream_active:
            logger.warning("Event streaming not active")
            return
            
        try:
            logger.info("Stopping event streaming...")
            
            self.stream_active = False
            
            if self.flush_task:
                self.flush_task.cancel()
                try:
                    await self.flush_task
                except asyncio.CancelledError:
                    pass
            
            # Flush remaining events
            await self._flush_events()
            
            logger.info("Event streaming stopped")
            
        except Exception as e:
            logger.error(f"Error stopping event streaming: {e}")
            raise
    
    async def publish_event(self, event_type: str, data: Dict[str, Any], 
                          partition_key: str, priority: EventPriority = EventPriority.MEDIUM,
                          tags: Optional[Dict[str, str]] = None) -> bool:
        """
        Publish an event to the stream.
        
        Args:
            event_type: Type of event
            data: Event data
            partition_key: Partitioning key for event distribution
            priority: Event priority level
            tags: Optional metadata tags
            
        Returns:
            True if event was accepted, False otherwise
        """
        if not self.stream_active:
            logger.warning("Cannot publish event: streaming not active")
            return False
        
        try:
            event = StreamEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                timestamp=datetime.now(),
                data=data,
                partition_key=partition_key,
                priority=priority,
                tags=tags or {}
            )
            
            # Apply filters
            for filter_name, filter_func in self.filters.items():
                if not await filter_func(event):
                    logger.debug(f"Event {event.event_id} filtered out by {filter_name}")
                    return False
            
            # Add to buffer
            success = await self.buffer.add_event(event)
            if success:
                self.stats["events_processed"] += 1
                logger.debug(f"Published event {event.event_id} of type {event_type}")
            else:
                self.stats["events_failed"] += 1
                logger.warning(f"Failed to buffer event {event.event_id}: buffer full")
            
            return success
            
        except Exception as e:
            logger.error(f"Error publishing event: {e}")
            self.stats["events_failed"] += 1
            return False
    
    def register_consumer(self, consumer_id: str, consumer_func: Callable) -> None:
        """
        Register an event consumer.
        
        Args:
            consumer_id: Unique identifier for the consumer
            consumer_func: Async function to handle events
        """
        if not asyncio.iscoroutinefunction(consumer_func):
            raise ValueError("Consumer function must be async")
            
        self.consumers[consumer_id] = consumer_func
        logger.info(f"Registered consumer: {consumer_id}")
    
    def unregister_consumer(self, consumer_id: str) -> bool:
        """
        Unregister an event consumer.
        
        Args:
            consumer_id: Consumer identifier to remove
            
        Returns:
            True if consumer was removed, False if not found
        """
        if consumer_id in self.consumers:
            del self.consumers[consumer_id]
            logger.info(f"Unregistered consumer: {consumer_id}")
            return True
        return False
    
    def add_filter(self, filter_name: str, filter_func: Callable) -> None:
        """
        Add an event filter.
        
        Args:
            filter_name: Unique name for the filter
            filter_func: Async function that returns True to keep event
        """
        if not asyncio.iscoroutinefunction(filter_func):
            raise ValueError("Filter function must be async")
            
        self.filters[filter_name] = filter_func
        logger.info(f"Added filter: {filter_name}")
    
    def remove_filter(self, filter_name: str) -> bool:
        """
        Remove an event filter.
        
        Args:
            filter_name: Filter name to remove
            
        Returns:
            True if filter was removed, False if not found
        """
        if filter_name in self.filters:
            del self.filters[filter_name]
            logger.info(f"Removed filter: {filter_name}")
            return True
        return False
    
    async def _flush_loop(self) -> None:
        """Main flush loop for periodic event delivery."""
        while self.stream_active:
            try:
                await asyncio.sleep(self.config.flush_interval)
                await self._flush_events()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")
    
    async def _flush_events(self) -> None:
        """Flush buffered events to consumers."""
        if not self.consumers:
            return
        
        try:
            # Get events from buffer
            events = await self.buffer.get_events(self.config.batch_size)
            if not events:
                return
            
            # Group events by priority for processing
            priority_groups = self._group_events_by_priority(events)
            
            # Process each priority group
            for priority, event_group in priority_groups.items():
                batch_data = await self._prepare_batch(event_group)
                await self._deliver_batch(batch_data)
            
            self.stats["batches_sent"] += 1
            logger.debug(f"Flushed {len(events)} events in batch")
            
        except Exception as e:
            logger.error(f"Error flushing events: {e}")
    
    def _group_events_by_priority(self, events: List[StreamEvent]) -> Dict[EventPriority, List[StreamEvent]]:
        """Group events by priority level."""
        groups = {}
        for event in events:
            if event.priority not in groups:
                groups[event.priority] = []
            groups[event.priority].append(event)
        return groups
    
    async def _prepare_batch(self, events: List[StreamEvent]) -> Dict[str, Any]:
        """
        Prepare batch data for delivery.
        
        Args:
            events: List of events to batch
            
        Returns:
            Batch data
        """
        batch_data = {
            "batch_id": str(uuid.uuid4()),
            "stream_name": self.config.stream_name,
            "timestamp": datetime.now().isoformat(),
            "event_count": len(events),
            "events": [asdict(event) for event in events]
        }
        
        # Apply compression if enabled
        if self.config.compression_enabled:
            batch_data = await self._compress_batch(batch_data)
        
        return batch_data
    
    async def _compress_batch(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compress batch data.
        
        Args:
            batch_data: Raw batch data
            
        Returns:
            Compressed batch data
        """
        try:
            # Custom JSON encoder for datetime and enum serialization
            def json_serializer(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif hasattr(obj, 'value'):  # Handle enums
                    return obj.value
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            # Serialize to JSON with custom encoder
            json_data = json.dumps(batch_data, default=json_serializer).encode('utf-8')
            original_size = len(json_data)
            
            # Compress with gzip
            compressed_data = gzip.compress(json_data)
            compressed_size = len(compressed_data)
            
            # Update compression ratio stats
            if original_size > 0:
                compression_ratio = compressed_size / original_size
                self.stats["compression_ratio"] = (
                    (self.stats["compression_ratio"] + compression_ratio) / 2
                    if self.stats["compression_ratio"] > 0 else compression_ratio
                )
            
            return {
                "compressed": True,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "data": compressed_data.hex()  # Store as hex string
            }
            
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return batch_data
    
    async def _deliver_batch(self, batch_data: Dict[str, Any]) -> None:
        """
        Deliver batch to all registered consumers.
        
        Args:
            batch_data: Batch data to deliver
        """
        delivery_tasks = []
        
        for consumer_id, consumer_func in self.consumers.items():
            task = asyncio.create_task(
                self._deliver_to_consumer(consumer_id, consumer_func, batch_data)
            )
            delivery_tasks.append(task)
        
        # Wait for all deliveries to complete
        if delivery_tasks:
            results = await asyncio.gather(*delivery_tasks, return_exceptions=True)
            
            # Count successful deliveries
            successful = sum(1 for result in results if not isinstance(result, Exception))
            failed = len(results) - successful
            
            self.stats["events_delivered"] += successful
            self.stats["events_failed"] += failed
    
    async def _deliver_to_consumer(self, consumer_id: str, consumer_func: Callable, 
                                 batch_data: Dict[str, Any]) -> None:
        """
        Deliver batch to a specific consumer with retries.
        
        Args:
            consumer_id: Consumer identifier
            consumer_func: Consumer function
            batch_data: Batch data to deliver
        """
        for attempt in range(self.config.max_retries + 1):
            try:
                await consumer_func(batch_data)
                logger.debug(f"Delivered batch to consumer {consumer_id}")
                return
                
            except Exception as e:
                logger.error(f"Delivery attempt {attempt + 1} failed for consumer {consumer_id}: {e}")
                
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    logger.error(f"All delivery attempts failed for consumer {consumer_id}")
                    raise
    
    def get_stream_info(self) -> Dict[str, Any]:
        """Get stream information."""
        return {
            "stream_name": self.config.stream_name,
            "stream_active": self.stream_active,
            "consumers_count": len(self.consumers),
            "filters_count": len(self.filters),
            "config": asdict(self.config),
            "statistics": self.stats
        }
    
    async def get_buffer_stats(self) -> Dict[str, Any]:
        """Get buffer statistics."""
        return await self.buffer.get_stats()
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on event streaming.
        
        Returns:
            Health status information
        """
        buffer_stats = await self.buffer.get_stats()
        
        return {
            "status": "healthy" if self.stream_active else "unhealthy",
            "stream_active": self.stream_active,
            "consumers_registered": len(self.consumers),
            "buffer_utilization": buffer_stats["utilization"],
            "events_processed": self.stats["events_processed"],
            "events_delivered": self.stats["events_delivered"],
            "config_valid": True,
            "timestamp": datetime.now().isoformat()
        }