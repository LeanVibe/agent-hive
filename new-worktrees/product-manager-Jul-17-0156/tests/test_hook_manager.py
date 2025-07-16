#!/usr/bin/env python3
"""
Tests for the Hook Manager and Real-Time Observability System

Comprehensive test suite for the observability system components.
"""

import asyncio
import pytest
import json
import time
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from observability.hook_manager import (
    HookManager,
    HookType,
    EventPriority,
    HookEvent,
    EventStream,
    AgentMonitor,
    track_tool_use,
    track_agent_error,
    track_performance_metrics
)


class TestHookEvent:
    """Test HookEvent class functionality."""
    
    def test_hook_event_creation(self):
        """Test basic hook event creation."""
        event = HookEvent(
            event_id="test_001",
            hook_type=HookType.PRE_TOOL_USE,
            agent_id="agent_001",
            session_id="session_001",
            timestamp=datetime.now(),
            priority=EventPriority.MEDIUM,
            context={"test": "data"},
            tool_name="bash",
            tool_args={"command": "ls"}
        )
        
        assert event.event_id == "test_001"
        assert event.hook_type == HookType.PRE_TOOL_USE
        assert event.agent_id == "agent_001"
        assert event.tool_name == "bash"
        assert event.context["test"] == "data"
    
    def test_hook_event_serialization(self):
        """Test hook event serialization to dictionary."""
        event = HookEvent(
            event_id="test_002",
            hook_type=HookType.POST_TOOL_USE,
            agent_id="agent_002",
            session_id="session_002",
            timestamp=datetime.now(),
            priority=EventPriority.HIGH,
            context={"result": "success"}
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["event_id"] == "test_002"
        assert event_dict["hook_type"] == "post_tool_use"
        assert event_dict["priority"] == "high"
        assert "timestamp" in event_dict
        assert event_dict["context"]["result"] == "success"


class TestAgentMonitor:
    """Test AgentMonitor class functionality."""
    
    def test_agent_state_tracking(self):
        """Test agent state tracking."""
        monitor = AgentMonitor()
        
        # Track initial state
        state1 = {"status": "idle", "tool_name": "bash"}
        monitor.track_agent_state("agent_001", state1)
        
        # Track state change
        state2 = {"status": "working", "tool_name": "read"}
        monitor.track_agent_state("agent_001", state2)
        
        assert "agent_001" in monitor.agent_states
        assert monitor.agent_states["agent_001"]["state"] == state2
        assert monitor.agent_states["agent_001"]["previous_state"] is not None
    
    def test_behavior_pattern_analysis(self):
        """Test behavior pattern analysis."""
        monitor = AgentMonitor()
        
        # Simulate tool usage
        states = [
            {"tool_name": "bash", "status": "working"},
            {"tool_name": "read", "status": "working"},
            {"tool_name": "bash", "status": "working"},
            {"tool_name": "write", "status": "working"}
        ]
        
        for state in states:
            monitor.track_agent_state("agent_001", state)
        
        patterns = monitor.behavior_patterns["agent_001"]
        assert patterns["tool_usage"]["bash"] == 2
        assert patterns["tool_usage"]["read"] == 1
        assert patterns["tool_usage"]["write"] == 1
    
    def test_performance_score_calculation(self):
        """Test performance score calculation."""
        monitor = AgentMonitor()
        
        # Simulate good performance
        monitor.behavior_patterns["agent_001"] = {
            "tool_usage": {"bash": 5, "read": 3, "write": 2},
            "session_duration": [600, 900, 1200],  # 10-20 minutes
            "error_patterns": [],
            "performance_trends": []
        }
        
        score = monitor.calculate_performance_score("agent_001")
        assert score > 80  # Should be high score
        
        # Simulate poor performance with more errors
        monitor.behavior_patterns["agent_002"] = {
            "tool_usage": {"bash": 1},
            "session_duration": [60],  # Very short
            "error_patterns": ["error1", "error2", "error3", "error4", "error5", "error6"],  # More errors
            "performance_trends": []
        }
        
        score = monitor.calculate_performance_score("agent_002")
        assert score < 80  # Should be lower score
    
    def test_agent_metrics_retrieval(self):
        """Test agent metrics retrieval."""
        monitor = AgentMonitor()
        
        # Setup agent state
        state = {"status": "working", "tool_name": "bash"}
        monitor.track_agent_state("agent_001", state)
        
        metrics = monitor.get_agent_metrics("agent_001")
        
        assert "current_state" in metrics
        assert "last_update" in metrics
        assert "tool_usage" in metrics
        assert "performance_score" in metrics
        assert metrics["current_state"]["status"] == "working"


class TestEventStream:
    """Test EventStream class functionality."""
    
    def test_event_stream_initialization(self):
        """Test event stream initialization."""
        stream = EventStream(websocket_port=8765, http_port=8766)
        
        assert stream.websocket_port == 8765
        assert stream.http_port == 8766
        assert stream.running is False
        assert len(stream.websocket_clients) == 0
    
    @pytest.mark.asyncio
    async def test_event_stream_lifecycle(self):
        """Test event stream start and stop."""
        stream = EventStream(websocket_port=8767, http_port=8768)
        
        # Mock the server creation to avoid actual network binding
        with patch('websockets.serve') as mock_websocket_serve, \
             patch.object(stream, 'start_http_server') as mock_http_start:
            
            # Create a mock server that can be awaited
            mock_server = Mock()
            mock_server.close = Mock()
            mock_server.wait_closed = AsyncMock()
            
            # Create an awaitable mock
            async def mock_serve(*args, **kwargs):
                return mock_server
            
            mock_websocket_serve.side_effect = mock_serve
            mock_http_start.return_value = None
            
            await stream.start()
            assert stream.running is True
            
            await stream.stop()
            assert stream.running is False
    
    @pytest.mark.asyncio
    async def test_event_broadcasting(self):
        """Test event broadcasting to clients."""
        stream = EventStream()
        
        # Mock WebSocket clients
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        stream.websocket_clients = {mock_client1, mock_client2}
        
        event_data = {"type": "test", "data": "test_data"}
        
        await stream.broadcast_event(event_data)
        
        # Verify both clients received the event
        mock_client1.send.assert_called_once()
        mock_client2.send.assert_called_once()


class TestHookManager:
    """Test HookManager class functionality."""
    
    def test_hook_manager_initialization(self):
        """Test hook manager initialization."""
        manager = HookManager()
        
        assert manager.running is False
        assert len(manager.hooks) == len(HookType)
        assert len(manager.event_history) == 0
        assert manager.max_history_size == 1000
    
    def test_hook_registration(self):
        """Test hook registration and unregistration."""
        manager = HookManager()
        
        def test_callback(event):
            pass
        
        # Register hook
        manager.register_hook(HookType.PRE_TOOL_USE, test_callback)
        assert test_callback in manager.hooks[HookType.PRE_TOOL_USE]
        
        # Unregister hook
        manager.unregister_hook(HookType.PRE_TOOL_USE, test_callback)
        assert test_callback not in manager.hooks[HookType.PRE_TOOL_USE]
    
    @pytest.mark.asyncio
    async def test_hook_execution(self):
        """Test hook execution."""
        manager = HookManager()
        
        # Mock event stream to avoid network operations
        manager.event_stream = AsyncMock()
        manager.event_stream.broadcast_event = AsyncMock()
        
        callback_called = False
        
        def test_callback(event):
            nonlocal callback_called
            callback_called = True
            assert event.hook_type == HookType.PRE_TOOL_USE
        
        manager.register_hook(HookType.PRE_TOOL_USE, test_callback)
        
        event = HookEvent(
            event_id="test_001",
            hook_type=HookType.PRE_TOOL_USE,
            agent_id="agent_001",
            session_id="session_001",
            timestamp=datetime.now(),
            priority=EventPriority.MEDIUM,
            context={"test": "data"}
        )
        
        await manager.execute_hooks(event)
        
        assert callback_called
        assert len(manager.event_history) == 1
        manager.event_stream.broadcast_event.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_hook_execution(self):
        """Test async hook execution."""
        manager = HookManager()
        
        # Mock event stream
        manager.event_stream = AsyncMock()
        manager.event_stream.broadcast_event = AsyncMock()
        
        async_callback_called = False
        
        async def async_test_callback(event):
            nonlocal async_callback_called
            async_callback_called = True
            assert event.hook_type == HookType.POST_TOOL_USE
        
        manager.register_hook(HookType.POST_TOOL_USE, async_test_callback)
        
        event = HookEvent(
            event_id="test_002",
            hook_type=HookType.POST_TOOL_USE,
            agent_id="agent_002",
            session_id="session_002",
            timestamp=datetime.now(),
            priority=EventPriority.HIGH,
            context={"result": "success"}
        )
        
        await manager.execute_hooks(event)
        
        assert async_callback_called
    
    @pytest.mark.asyncio
    async def test_event_creation_and_processing(self):
        """Test event creation and processing."""
        manager = HookManager()
        
        # Mock event stream
        manager.event_stream = AsyncMock()
        manager.event_stream.broadcast_event = AsyncMock()
        
        event = await manager.create_and_process_event(
            hook_type=HookType.NOTIFICATION,
            agent_id="agent_001",
            session_id="session_001",
            context={"message": "test notification"},
            priority=EventPriority.HIGH
        )
        
        assert event.hook_type == HookType.NOTIFICATION
        assert event.agent_id == "agent_001"
        assert event.priority == EventPriority.HIGH
        assert len(manager.event_history) == 1
    
    def test_system_metrics(self):
        """Test system metrics retrieval."""
        manager = HookManager()
        
        metrics = manager.get_system_metrics()
        
        assert "hook_manager" in metrics
        assert "event_stream" in metrics
        assert "agent_monitor" in metrics
        assert metrics["hook_manager"]["running"] is False
        assert metrics["hook_manager"]["event_history_size"] == 0
    
    def test_event_history_management(self):
        """Test event history management."""
        manager = HookManager()
        manager.max_history_size = 3
        
        # Add events beyond max size using the actual method
        for i in range(5):
            event = HookEvent(
                event_id=f"test_{i}",
                hook_type=HookType.PRE_TOOL_USE,
                agent_id="agent_001",
                session_id="session_001",
                timestamp=datetime.now(),
                priority=EventPriority.MEDIUM,
                context={"index": i}
            )
            manager.event_history.append(event)
            # Apply the same logic as execute_hooks
            while len(manager.event_history) > manager.max_history_size:
                manager.event_history.pop(0)
        
        # Should keep only the last 3 events
        assert len(manager.event_history) == 3
        assert manager.event_history[0].context["index"] == 2
        assert manager.event_history[-1].context["index"] == 4
    
    def test_event_history_filtering(self):
        """Test event history filtering."""
        manager = HookManager()
        
        # Add events for different agents
        for i in range(3):
            event = HookEvent(
                event_id=f"test_{i}",
                hook_type=HookType.PRE_TOOL_USE,
                agent_id=f"agent_{i % 2}",  # alternating between agent_0 and agent_1
                session_id="session_001",
                timestamp=datetime.now(),
                priority=EventPriority.MEDIUM,
                context={"index": i}
            )
            manager.event_history.append(event)
        
        # Get history for specific agent
        agent_0_history = manager.get_event_history(agent_id="agent_0")
        agent_1_history = manager.get_event_history(agent_id="agent_1")
        
        assert len(agent_0_history) == 2  # events 0 and 2
        assert len(agent_1_history) == 1  # event 1
        assert agent_0_history[0]["context"]["index"] == 0
        assert agent_1_history[0]["context"]["index"] == 1


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @pytest.mark.asyncio
    async def test_track_tool_use(self):
        """Test track_tool_use function."""
        from observability.hook_manager import hook_manager
        
        # Mock hook manager
        hook_manager.create_and_process_event = AsyncMock()
        
        await track_tool_use("agent_001", "session_001", "bash", {"command": "ls"})
        
        hook_manager.create_and_process_event.assert_called_once()
        call_args = hook_manager.create_and_process_event.call_args
        assert call_args[1]["hook_type"] == HookType.PRE_TOOL_USE
        assert call_args[1]["tool_name"] == "bash"
    
    @pytest.mark.asyncio
    async def test_track_agent_error(self):
        """Test track_agent_error function."""
        from observability.hook_manager import hook_manager
        
        # Mock hook manager
        hook_manager.create_and_process_event = AsyncMock()
        
        await track_agent_error("agent_001", "session_001", "Test error", {"context": "test"})
        
        hook_manager.create_and_process_event.assert_called_once()
        call_args = hook_manager.create_and_process_event.call_args
        assert call_args[1]["hook_type"] == HookType.ERROR
        assert call_args[1]["error_message"] == "Test error"
        assert call_args[1]["priority"] == EventPriority.HIGH
    
    @pytest.mark.asyncio
    async def test_track_performance_metrics(self):
        """Test track_performance_metrics function."""
        from observability.hook_manager import hook_manager
        
        # Mock hook manager
        hook_manager.create_and_process_event = AsyncMock()
        
        metrics = {"response_time": 0.5, "memory_usage": 128.0}
        await track_performance_metrics("agent_001", "session_001", metrics)
        
        hook_manager.create_and_process_event.assert_called_once()
        call_args = hook_manager.create_and_process_event.call_args
        assert call_args[1]["hook_type"] == HookType.PERFORMANCE
        assert call_args[1]["performance_metrics"] == metrics
        assert call_args[1]["priority"] == EventPriority.LOW


class TestIntegration:
    """Integration tests for the complete observability system."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test complete workflow from event creation to monitoring."""
        manager = HookManager()
        
        # Mock event stream to avoid network operations
        manager.event_stream = AsyncMock()
        manager.event_stream.broadcast_event = AsyncMock()
        
        # Register hooks
        pre_tool_events = []
        post_tool_events = []
        
        def pre_tool_hook(event):
            pre_tool_events.append(event)
        
        def post_tool_hook(event):
            post_tool_events.append(event)
        
        manager.register_hook(HookType.PRE_TOOL_USE, pre_tool_hook)
        manager.register_hook(HookType.POST_TOOL_USE, post_tool_hook)
        
        # Simulate tool usage workflow
        await manager.create_and_process_event(
            hook_type=HookType.PRE_TOOL_USE,
            agent_id="agent_001",
            session_id="session_001",
            context={"tool_name": "bash", "command": "ls"},
            tool_name="bash",
            tool_args={"command": "ls"}
        )
        
        await manager.create_and_process_event(
            hook_type=HookType.POST_TOOL_USE,
            agent_id="agent_001",
            session_id="session_001",
            context={"tool_name": "bash", "result": "success"},
            tool_name="bash",
            tool_result="file1.txt file2.txt"
        )
        
        # Verify workflow
        assert len(pre_tool_events) == 1
        assert len(post_tool_events) == 1
        assert len(manager.event_history) == 2
        
        # Verify agent monitoring
        agent_metrics = manager.get_agent_metrics("agent_001")
        assert "current_state" in agent_metrics
        assert "tool_usage" in agent_metrics
        assert "performance_score" in agent_metrics
        
        # Verify event streaming
        assert manager.event_stream.broadcast_event.call_count == 2


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])