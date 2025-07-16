#!/usr/bin/env python3
"""
Tests for Event-Driven Coordination System
Foundation Epic Evolution - Real-time Pub/Sub Infrastructure
"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import json
from datetime import datetime
from pathlib import Path

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from coordination_protocols.event_driven_coordinator import (
    EventDrivenCoordinator,
    CoordinationAlert,
    AgentStatus
)


class TestEventDrivenCoordinator:
    """Test suite for EventDrivenCoordinator."""
    
    @pytest_asyncio.fixture
    async def coordinator(self):
        """Create coordinator instance for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_file = temp_path / "coordination_config.json"
            
            config = {
                "coordination_alert_files": [
                    str(temp_path / "coordination_alerts.json")
                ],
                "agent_status_patterns": [
                    str(temp_path / "agent_status_*.json")
                ],
                "watch_directories": [str(temp_path)],
                "event_retention_hours": 1,
                "alert_debounce_seconds": 0.1
            }
            
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            coordinator = EventDrivenCoordinator(str(config_file))
            yield coordinator, temp_path
            
            if coordinator.active:
                await coordinator.stop_coordination()
    
    @pytest.mark.asyncio
    async def test_coordinator_initialization(self, coordinator):
        """Test coordinator initialization."""
        coord, temp_path = coordinator
        
        assert not coord.active
        assert coord.event_stream is not None
        assert coord.config["alert_debounce_seconds"] == 0.1
        assert len(coord.coordination_subscribers) == 0
    
    @pytest.mark.asyncio
    async def test_start_stop_coordination(self, coordinator):
        """Test starting and stopping coordination."""
        coord, temp_path = coordinator
        
        # Start coordination
        await coord.start_coordination()
        assert coord.active
        assert coord.event_stream.stream_active
        
        # Stop coordination
        await coord.stop_coordination()
        assert not coord.active
        assert not coord.event_stream.stream_active
    
    @pytest.mark.asyncio
    async def test_coordination_alert_processing(self, coordinator):
        """Test processing coordination alerts from files."""
        coord, temp_path = coordinator
        
        await coord.start_coordination()
        
        # Create coordination alerts file
        alerts_file = temp_path / "coordination_alerts.json"
        alert_data = {
            "alert_id": "test_alert_001",
            "alert_type": "task_overdue",
            "agent_id": "test-agent",
            "task_id": "task_123",
            "priority": "critical",
            "message": "Task overdue - immediate action required",
            "timestamp": datetime.now().isoformat(),
            "metadata": {"escalation_level": "urgent"}
        }
        
        with open(alerts_file, 'w') as f:
            json.dump([alert_data], f)
        
        # Process the file
        await coord._process_coordination_alerts_file(alerts_file)
        
        # Verify event was published
        stats = await coord.get_coordination_status()
        assert stats["event_stream"]["statistics"]["events_processed"] > 0
    
    @pytest.mark.asyncio
    async def test_agent_status_processing(self, coordinator):
        """Test processing agent status updates."""
        coord, temp_path = coordinator
        
        await coord.start_coordination()
        
        # Create agent status file
        status_file = temp_path / "agent_status_test-agent.json"
        status_data = {
            "agent_id": "test-agent",
            "status": "working",
            "current_task": "task_456",
            "last_activity": datetime.now().isoformat(),
            "worktree_path": "/path/to/worktree",
            "git_status": {"branch": "main", "clean": True}
        }
        
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
        
        # Process the file
        await coord._process_agent_status_file(status_file)
        
        # Verify agent status was cached
        assert "test-agent" in coord.agent_statuses
        agent_status = coord.agent_statuses["test-agent"]
        assert agent_status.agent_id == "test-agent"
        assert agent_status.status == "working"
        assert agent_status.current_task == "task_456"
    
    @pytest.mark.asyncio
    async def test_event_subscription(self, coordinator):
        """Test coordination event subscription."""
        coord, temp_path = coordinator
        
        received_events = []
        
        async def test_subscriber(event_type: str, data: dict):
            received_events.append((event_type, data))
        
        # Subscribe to events
        coord.subscribe_to_coordination_events("test_subscriber", test_subscriber)
        assert "test_subscriber" in coord.coordination_subscribers
        
        await coord.start_coordination()
        
        # Simulate coordination alert
        alert_data = {
            "alert": {
                "alert_type": "escalation",
                "agent_id": "test-agent",
                "priority": "high"
            }
        }
        await coord._handle_coordination_alert(alert_data)
        
        # Check if subscriber received event
        assert len(received_events) == 1
        assert received_events[0][0] == "coordination_alert"
        assert received_events[0][1] == alert_data
        
        # Unsubscribe
        result = coord.unsubscribe_from_coordination_events("test_subscriber")
        assert result is True
        assert "test_subscriber" not in coord.coordination_subscribers
    
    @pytest.mark.asyncio
    async def test_agent_id_extraction(self, coordinator):
        """Test agent ID extraction from file paths."""
        coord, temp_path = coordinator
        
        # Test various file path patterns
        test_cases = [
            (temp_path / "agent-test" / "status.json", {"status": "active"}, "agent-test"),
            (temp_path / "worktrees" / "performance-agent" / "status.json", {}, "performance-agent"),
            (temp_path / "status.json", {"agent_id": "explicit-agent"}, "explicit-agent")
        ]
        
        for file_path, status_data, expected_agent_id in test_cases:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            agent_id = coord._extract_agent_id(file_path, status_data)
            assert agent_id == expected_agent_id
    
    @pytest.mark.asyncio
    async def test_coordination_status(self, coordinator):
        """Test coordination status reporting."""
        coord, temp_path = coordinator
        
        await coord.start_coordination()
        
        status = await coord.get_coordination_status()
        
        assert "active" in status
        assert "coordination_files_watched" in status
        assert "agent_statuses_cached" in status
        assert "subscribers_count" in status
        assert "event_stream" in status
        assert "buffer_stats" in status
        assert "timestamp" in status
        
        assert status["active"] is True
        assert isinstance(status["coordination_files_watched"], int)
        assert isinstance(status["subscribers_count"], int)
    
    @pytest.mark.asyncio
    async def test_event_priority_handling(self, coordinator):
        """Test event priority assignment based on alert data."""
        coord, temp_path = coordinator
        
        await coord.start_coordination()
        
        # Test high priority alert
        critical_alert = {
            "alert_type": "emergency_escalation",
            "priority": "critical",
            "escalation_level": "emergency",
            "agent_id": "test-agent"
        }
        
        await coord._publish_coordination_alert(critical_alert, "test_file.json")
        
        # Test low priority status
        low_status = {
            "agent_id": "test-agent",
            "status": "idle"
        }
        
        await coord._publish_agent_status_update("test-agent", low_status, "test_status.json")
        
        # Verify events were published with appropriate priorities
        stats = await coord.get_coordination_status()
        assert stats["event_stream"]["statistics"]["events_processed"] >= 2
    
    def test_coordination_alert_dataclass(self):
        """Test CoordinationAlert dataclass."""
        alert = CoordinationAlert(
            alert_id="test_001",
            alert_type="task_overdue",
            agent_id="test-agent",
            task_id="task_123",
            priority="high",
            message="Test alert",
            timestamp=datetime.now(),
            metadata={"test": "data"}
        )
        
        assert alert.alert_id == "test_001"
        assert alert.alert_type == "task_overdue"
        assert alert.agent_id == "test-agent"
        assert alert.task_id == "task_123"
        assert alert.priority == "high"
    
    def test_agent_status_dataclass(self):
        """Test AgentStatus dataclass."""
        status = AgentStatus(
            agent_id="test-agent",
            status="active",
            last_activity=datetime.now(),
            current_task="task_456",
            worktree_path="/path/to/worktree",
            git_status={"branch": "main"},
            metadata={"extra": "info"}
        )
        
        assert status.agent_id == "test-agent"
        assert status.status == "active"
        assert status.current_task == "task_456"
        assert status.worktree_path == "/path/to/worktree"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])