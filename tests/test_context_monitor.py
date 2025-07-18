"""
Unit tests for ContextMonitor and ContextGrowthPredictor.

Tests extracted from hook_system.py to ensure functionality is preserved
during refactoring process.
"""

import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from intelligence.context_monitor import ContextGrowthPredictor, ContextMonitor

# Add the .claude directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / '.claude'))


class TestContextGrowthPredictor:
    """Test suite for ContextGrowthPredictor functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = Path(f.name)
        yield temp_path
        temp_path.unlink(missing_ok=True)

    @pytest.fixture
    def predictor(self, temp_db):
        """Create ContextGrowthPredictor with temporary database."""
        return ContextGrowthPredictor(temp_db)

    def test_init_creates_database_schema(self, temp_db):
        """Test that initialization creates proper database schema."""
        ContextGrowthPredictor(temp_db)

        # Verify database file exists
        assert temp_db.exists()

        # Verify schema
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()

            # Check context_history table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='context_history'")
            assert cursor.fetchone() is not None

            # Check prediction_accuracy table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='prediction_accuracy'")
            assert cursor.fetchone() is not None

            # Check indexes
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_context_history_agent_time'")
            assert cursor.fetchone() is not None

    def test_record_usage(self, predictor):
        """Test recording usage data."""
        agent_id = "test_agent"
        usage_percent = 0.65
        context = {"task_type": "coding", "task_count": 5}

        predictor.record_usage(agent_id, usage_percent, context)

        # Verify data was recorded
        with sqlite3.connect(predictor.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM context_history WHERE agent_id = ?", (agent_id,))
            result = cursor.fetchone()

            assert result is not None
            assert result[1] == agent_id  # agent_id
            assert result[3] == usage_percent  # usage_percent
            assert result[4] == "coding"  # task_type
            assert result[5] == 5  # task_count

    def test_predict_insufficient_history(self, predictor):
        """Test prediction with insufficient historical data."""
        agent_id = "new_agent"

        # Test with no history
        growth_rate = predictor.predict(agent_id, 0.5)
        assert growth_rate == 0.1  # Default conservative estimate

        # Test with single data point
        predictor.record_usage(agent_id, 0.4)
        growth_rate = predictor.predict(agent_id, 0.5)
        assert growth_rate == 0.1  # Still insufficient

    def test_predict_with_history(self, predictor):
        """Test prediction with sufficient historical data."""
        agent_id = "experienced_agent"

        # Create history with steady 10% growth per hour
        base_time = datetime.now() - timedelta(hours=5)
        for i in range(6):
            usage = 0.3 + (i * 0.1)  # 0.3, 0.4, 0.5, 0.6, 0.7, 0.8
            timestamp = base_time + timedelta(hours=i)

            with sqlite3.connect(predictor.db_path) as conn:
                conn.execute(
                    "INSERT INTO context_history (agent_id, usage_percent, timestamp, created_at) VALUES (?, ?, ?, ?)",
                    (agent_id, usage, timestamp, timestamp)
                )

        growth_rate = predictor.predict(agent_id, 0.8)

        # Should predict growth rate around 0.1 per hour
        assert 0.05 <= growth_rate <= 0.15

    def test_get_prediction_confidence(self, predictor):
        """Test confidence calculation."""
        agent_id = "test_agent"

        # Test with no data
        confidence = predictor.get_prediction_confidence(agent_id)
        assert 0.0 <= confidence <= 1.0

        # Add some recent data points
        for i in range(5):
            predictor.record_usage(agent_id, 0.5 + i * 0.1)

        confidence_with_data = predictor.get_prediction_confidence(agent_id)
        assert confidence_with_data > confidence  # More data = higher confidence

    def test_get_usage_stats_specific_agent(self, predictor):
        """Test getting usage statistics for specific agent."""
        agent_id = "stats_agent"

        # Record some usage data
        usage_values = [0.3, 0.5, 0.7, 0.6, 0.8]
        for usage in usage_values:
            predictor.record_usage(agent_id, usage)

        stats = predictor.get_usage_stats(agent_id, hours=24)

        assert stats["agent_id"] == agent_id
        assert stats["total_records"] == 5
        assert stats["avg_usage"] == sum(usage_values) / len(usage_values)
        assert stats["peak_usage"] == max(usage_values)
        assert stats["min_usage"] == min(usage_values)

    def test_get_usage_stats_all_agents(self, predictor):
        """Test getting usage statistics for all agents."""
        # Record data for multiple agents
        agents = ["agent1", "agent2", "agent3"]
        for agent in agents:
            for usage in [0.4, 0.6, 0.8]:
                predictor.record_usage(agent, usage)

        stats = predictor.get_usage_stats(agent_id=None, hours=24)

        assert stats["agent_id"] == "all"
        assert stats["total_records"] == 9  # 3 agents * 3 records each
        # Average of 0.4, 0.6, 0.8
        assert abs(stats["avg_usage"] - 0.6) < 0.001

    def test_cleanup_old_data(self, predictor):
        """Test cleanup of old data."""
        agent_id = "cleanup_agent"

        # Create old and recent data
        old_time = datetime.now() - timedelta(days=100)
        recent_time = datetime.now() - timedelta(days=10)

        with sqlite3.connect(predictor.db_path) as conn:
            # Old data
            conn.execute(
                "INSERT INTO context_history (agent_id, usage_percent, timestamp, created_at) VALUES (?, ?, ?, ?)",
                (agent_id, 0.5, old_time, old_time)
            )
            # Recent data
            conn.execute(
                "INSERT INTO context_history (agent_id, usage_percent, timestamp, created_at) VALUES (?, ?, ?, ?)",
                (agent_id, 0.7, recent_time, recent_time)
            )

        # Cleanup data older than 90 days
        deleted_count = predictor.cleanup_old_data(days_to_keep=90)

        assert deleted_count >= 1

        # Verify recent data still exists
        with sqlite3.connect(predictor.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM context_history WHERE usage_percent = 0.7")
            assert cursor.fetchone()[0] == 1

            cursor.execute(
                "SELECT COUNT(*) FROM context_history WHERE usage_percent = 0.5")
            assert cursor.fetchone()[0] == 0


class TestContextMonitor:
    """Test suite for ContextMonitor functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        yield temp_path
        Path(temp_path).unlink(missing_ok=True)

    @pytest.fixture
    def monitor(self, temp_db):
        """Create ContextMonitor with temporary database."""
        return ContextMonitor(db_path=temp_db)

    def test_init_creates_predictor(self, temp_db):
        """Test that initialization creates predictor correctly."""
        monitor = ContextMonitor(db_path=temp_db)

        assert isinstance(monitor.predictor, ContextGrowthPredictor)
        assert monitor.db_path == Path(temp_db)

    def test_check_context_normal_usage(self, monitor):
        """Test context check with normal usage levels."""
        agent_id = "normal_agent"
        current_usage = 0.5  # 50% usage

        result = monitor.check_context(agent_id, current_usage)

        assert result["agent_id"] == agent_id
        assert result["current_usage"] == current_usage
        assert result["action_required"] == "none"
        assert result["urgency"] == "low"
        assert "timestamp" in result
        assert "confidence" in result

    def test_check_context_high_usage(self, monitor):
        """Test context check with high usage levels."""
        agent_id = "busy_agent"
        current_usage = 0.7  # 70% usage

        result = monitor.check_context(agent_id, current_usage)

        assert result["current_usage"] == current_usage
        assert result["action_required"] == "monitor_closely"
        assert result["urgency"] == "medium"
        assert "Context usage above 60%" in result["reason"]

    def test_check_context_critical_usage(self, monitor):
        """Test context check with critical usage requiring immediate action."""
        agent_id = "critical_agent"
        current_usage = 0.9  # 90% usage

        # Mock predictor to return high growth rate
        with patch.object(monitor.predictor, 'predict', return_value=0.3):
            result = monitor.check_context(agent_id, current_usage)

        # With 90% usage and 30% growth, should trigger immediate action
        assert result["action_required"] == "immediate_summarize"
        assert result["urgency"] == "critical"
        assert "overflow within" in result["reason"]

    def test_check_context_prepare_checkpoint(self, monitor):
        """Test context check that triggers checkpoint preparation."""
        agent_id = "checkpoint_agent"
        current_usage = 0.75  # 75% usage

        # Mock predictor to return moderate growth rate
        with patch.object(monitor.predictor, 'predict', return_value=0.15):
            result = monitor.check_context(agent_id, current_usage)

        # Should trigger checkpoint preparation
        assert result["action_required"] == "prepare_checkpoint"
        assert result["urgency"] == "high"

    def test_estimate_time_to_limit(self, monitor):
        """Test time to limit estimation."""
        # Test with positive growth
        time_to_limit = monitor._estimate_time_to_limit(0.5, 0.1)
        # (0.85 - 0.5) / 0.1 = 3.5 hours
        assert abs(time_to_limit - 3.5) < 0.001

        # Test with no growth
        time_to_limit = monitor._estimate_time_to_limit(0.8, 0.0)
        assert time_to_limit == 999.0

        # Test with negative growth
        time_to_limit = monitor._estimate_time_to_limit(0.6, -0.1)
        assert time_to_limit == 999.0

    def test_get_usage_stats(self, monitor):
        """Test getting usage statistics."""
        agent_id = "stats_agent"

        # Record some usage through context checks
        monitor.check_context(agent_id, 0.4)
        monitor.check_context(agent_id, 0.6)
        monitor.check_context(agent_id, 0.8)

        stats = monitor.get_usage_stats(agent_id, hours=1)

        assert stats["agent_id"] == agent_id
        assert stats["total_records"] == 3
        assert stats["peak_usage"] == 0.8

    def test_cleanup_old_data(self, monitor):
        """Test cleanup of old monitoring data."""
        # Create some data first
        monitor.check_context("test_agent", 0.5)

        deleted_count = monitor.cleanup_old_data(days_to_keep=30)

        # Should return number of deleted records (may be 0 for recent data)
        assert isinstance(deleted_count, int)
        assert deleted_count >= 0

    @patch('intelligence.context_monitor.get_config')
    def test_uses_config_settings(self, mock_get_config, temp_db):
        """Test that monitor uses configuration settings."""
        mock_config = {
            'intelligence.context.thresholds': {
                'immediate_action': 0.3,
                'prepare_checkpoint': 0.8,
                'monitor_closely': 0.5
            },
            'intelligence.context.target_limit': 0.9,
            'intelligence.context.default_growth_rate': 0.05
        }
        mock_get_config.return_value = Mock()
        mock_get_config.return_value.get.side_effect = lambda key, default: mock_config.get(
            key, default)

        monitor = ContextMonitor(db_path=temp_db)

        # Test with usage that should trigger monitor_closely with custom
        # threshold
        result = monitor.check_context("config_agent", 0.6)

        # Should trigger monitor_closely with custom 50% threshold
        assert result["action_required"] == "monitor_closely"

    def test_context_information_recording(self, monitor):
        """Test that additional context information is properly recorded."""
        agent_id = "context_agent"
        usage = 0.6
        context_info = {
            "task_type": "code_review",
            "task_count": 3
        }

        result = monitor.check_context(agent_id, usage, context_info)

        # Verify the call was successful
        assert result["agent_id"] == agent_id
        assert result["current_usage"] == usage

        # Verify context was recorded in the predictor
        stats = monitor.predictor.get_usage_stats(agent_id, hours=1)
        assert stats["total_records"] == 1

    def test_prediction_confidence_in_response(self, monitor):
        """Test that prediction confidence is included in responses."""
        agent_id = "confidence_agent"

        result = monitor.check_context(agent_id, 0.5)

        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0

    def test_predicted_usage_bounds(self, monitor):
        """Test that predicted usage is properly bounded."""
        agent_id = "bounds_agent"
        current_usage = 0.95

        # Mock very high growth rate that would exceed 100%
        with patch.object(monitor.predictor, 'predict', return_value=0.5):
            result = monitor.check_context(agent_id, current_usage)

        # Predicted usage should be capped at 1.0 (100%)
        assert result["predicted_usage_1h"] <= 1.0
