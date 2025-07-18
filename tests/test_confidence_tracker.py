"""
Unit tests for ConfidenceTracker ML system.

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
from intelligence.confidence_tracker import ConfidenceTracker

# Add the .claude directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / '.claude'))


class TestConfidenceTracker:
    """Test suite for ConfidenceTracker ML functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        yield temp_path
        Path(temp_path).unlink(missing_ok=True)

    @pytest.fixture
    def tracker(self, temp_db):
        """Create ConfidenceTracker with temporary database."""
        return ConfidenceTracker(db_path=temp_db)

    def test_init_creates_database_schema(self, temp_db):
        """Test that initialization creates proper database schema."""
        ConfidenceTracker(db_path=temp_db)

        # Verify database file exists
        assert Path(temp_db).exists()

        # Verify schema
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()

            # Check decisions table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='decisions'")
            assert cursor.fetchone() is not None

            # Check patterns table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='patterns'")
            assert cursor.fetchone() is not None

            # Check indexes
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_decisions_context_hash'")
            assert cursor.fetchone() is not None

    def test_should_involve_human_no_pattern_data(self, tracker):
        """Test decision making with no historical pattern data."""
        context = {
            "task_type": "feature_implementation",
            "agent_confidence": 0.8,
            "gemini_confidence": 0.75,
            "has_security_implications": False
        }

        should_involve, confidence = tracker.should_involve_human(context)

        # Should calculate combined confidence (0.8 + 0.75) / 2 = 0.775
        # Should not involve human since > 0.75 threshold
        assert not should_involve
        assert confidence == 0.775

    def test_should_involve_human_high_risk(self, tracker):
        """Test decision making with high risk factors."""
        context = {
            "task_type": "security_fix",
            "agent_confidence": 0.8,
            "gemini_confidence": 0.8,
            "has_security_implications": True,
            "has_architecture_changes": True
        }

        # Calculate expected risk score: 0.4 + 0.3 = 0.7
        risk_score = tracker._calculate_risk(context)
        assert risk_score == 0.7

        should_involve, confidence = tracker.should_involve_human(context)

        # High risk (>0.7) should trigger 0.85 threshold
        # Combined confidence = 0.8, which is < 0.85
        # But since risk_score = 0.7 (not > 0.7), it uses base threshold 0.75
        # Combined confidence = 0.8, which is > 0.75
        assert not should_involve  # Fixed expectation
        assert confidence == 0.8

    def test_should_involve_human_very_high_risk(self, tracker):
        """Test decision making with very high risk factors that exceed 0.7 threshold."""
        context = {
            "task_type": "security_fix",
            "agent_confidence": 0.8,
            "gemini_confidence": 0.8,
            "has_security_implications": True,
            "has_architecture_changes": True,
            "affects_performance": True  # This should push risk > 0.7
        }

        # Calculate expected risk score: 0.4 + 0.3 + 0.2 = 0.9 > 0.7
        risk_score = tracker._calculate_risk(context)
        assert abs(risk_score - 0.9) < 0.001  # Use approximate comparison

        should_involve, confidence = tracker.should_involve_human(context)

        # Very high risk (>0.7) should trigger 0.85 threshold
        # Combined confidence = 0.8, which is < 0.85
        assert should_involve
        assert confidence == 0.8

    def test_should_involve_human_learned_pattern(self, tracker):
        """Test decision making with learned high-success pattern."""
        context = {
            "task_type": "test_implementation",
            "complexity": "low",
            "agent_confidence": 0.7,
            "gemini_confidence": 0.7
        }

        # Create pattern with high success rate
        context_hash = tracker._hash_context(context)
        with sqlite3.connect(tracker.db_path) as conn:
            conn.execute(
                "INSERT INTO patterns VALUES (?, ?, ?, ?, ?)",
                (context_hash, 0.95, 10, datetime.now(), datetime.now())
            )

        should_involve, confidence = tracker.should_involve_human(context)

        # Should not involve human due to learned pattern
        assert not should_involve
        assert confidence == 0.95

    def test_record_outcome_creates_decision_record(self, tracker):
        """Test recording decision outcomes."""
        context = {
            "task_type": "bug_fix",
            "agent_confidence": 0.8,
            "gemini_confidence": 0.75
        }

        decision_id = "test_decision_123"
        tracker.record_outcome(decision_id, context, True, "success")

        # Verify decision was recorded
        with sqlite3.connect(tracker.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM decisions WHERE id = ?", (decision_id,))
            result = cursor.fetchone()

            assert result is not None
            assert result[1] == tracker._hash_context(context)  # context_hash
            assert result[2] == 0.8  # agent_confidence
            assert result[3] == 0.75  # gemini_confidence
            assert result[4] == 1  # human_involved (True)
            assert result[5] == "success"  # outcome

    def test_record_outcome_updates_patterns(self, tracker):
        """Test that recording outcomes updates pattern statistics."""
        context = {
            "task_type": "refactoring",
            "complexity": "medium"
        }

        # Record multiple outcomes for same pattern
        tracker.record_outcome("decision_1", context, False, "success")
        tracker.record_outcome("decision_2", context, False, "success")
        tracker.record_outcome("decision_3", context, False, "failure")

        # Check pattern statistics
        context_hash = tracker._hash_context(context)
        with sqlite3.connect(tracker.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT success_rate, sample_count FROM patterns WHERE pattern_hash = ?",
                (context_hash,
                 ))
            result = cursor.fetchone()

            assert result is not None
            assert result[0] == 2 / 3  # 2 successes out of 3 = 0.667
            assert result[1] == 3  # 3 total samples

    def test_get_pattern_stats_specific_context(self, tracker):
        """Test getting statistics for specific context pattern."""
        context = {
            "task_type": "documentation",
            "complexity": "low"
        }

        # Record some outcomes
        tracker.record_outcome("doc_1", context, False, "success")
        tracker.record_outcome("doc_2", context, False, "success")

        stats = tracker.get_pattern_stats(context)

        assert stats["success_rate"] == 1.0
        assert stats["sample_count"] == 2
        assert "last_updated" in stats
        assert stats["pattern_hash"] == tracker._hash_context(context)

    def test_get_pattern_stats_overall(self, tracker):
        """Test getting overall pattern statistics."""
        # Create multiple patterns
        contexts = [
            {"task_type": "feature", "complexity": "high"},
            {"task_type": "bugfix", "complexity": "low"},
            {"task_type": "test", "complexity": "medium"}
        ]

        for i, context in enumerate(contexts):
            tracker.record_outcome(f"decision_{i}", context, False, "success")

        stats = tracker.get_pattern_stats()

        assert stats["total_patterns"] == 3
        assert stats["total_decisions"] == 3
        assert stats["avg_success_rate"] == 1.0
        assert "last_activity" in stats

    def test_get_pattern_stats_no_data(self, tracker):
        """Test getting statistics when no data exists."""
        context = {"task_type": "nonexistent"}
        stats = tracker.get_pattern_stats(context)

        assert stats["sample_count"] == 0
        assert stats["pattern_hash"] == tracker._hash_context(context)

    def test_hash_context_consistency(self, tracker):
        """Test that context hashing is consistent."""
        context1 = {
            "task_type": "feature",
            "complexity": "high",
            "has_security_implications": True
        }

        context2 = {
            "complexity": "high",
            "task_type": "feature",
            "has_security_implications": True
        }

        # Same content, different order should produce same hash
        hash1 = tracker._hash_context(context1)
        hash2 = tracker._hash_context(context2)

        assert hash1 == hash2
        assert len(hash1) == 16  # MD5 hash truncated to 16 chars

    def test_calculate_risk_score(self, tracker):
        """Test risk score calculation."""
        # Test low risk context
        low_risk_context = {
            "task_type": "documentation",
            "has_security_implications": False,
            "has_architecture_changes": False
        }

        low_risk = tracker._calculate_risk(low_risk_context)
        assert low_risk == 0.0

        # Test high risk context
        high_risk_context = {
            "task_type": "security_fix",
            "has_security_implications": True,
            "has_architecture_changes": True,
            "affects_performance": True,
            "is_customer_facing": True
        }

        high_risk = tracker._calculate_risk(high_risk_context)
        # Should be 0.4 + 0.3 + 0.2 + 0.3 = 1.2, capped at 1.0
        assert high_risk == 1.0

    def test_cleanup_old_data(self, tracker):
        """Test cleanup of old decision data."""
        # Create old and recent decisions
        old_context = {"task_type": "old_task"}
        recent_context = {"task_type": "recent_task"}

        # Record decisions with different timestamps
        with sqlite3.connect(tracker.db_path) as conn:
            cursor = conn.cursor()

            # Old decision (100 days ago)
            old_time = datetime.now() - timedelta(days=100)
            cursor.execute(
                "INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("old_decision", tracker._hash_context(old_context), 0.8, 0.8,
                 False, "success", old_time, old_time)
            )

            # Recent decision (10 days ago)
            recent_time = datetime.now() - timedelta(days=10)
            cursor.execute(
                "INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("recent_decision",
                 tracker._hash_context(recent_context),
                 0.8,
                 0.8,
                 False,
                 "success",
                 recent_time,
                 recent_time))

            conn.commit()

        # Cleanup data older than 90 days
        deleted_count = tracker.cleanup_old_data(days_to_keep=90)

        # Should have deleted 1 record (old decision)
        assert deleted_count >= 1

        # Verify recent decision still exists
        with sqlite3.connect(tracker.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM decisions WHERE id = 'recent_decision'")
            assert cursor.fetchone()[0] == 1

            cursor.execute(
                "SELECT COUNT(*) FROM decisions WHERE id = 'old_decision'")
            assert cursor.fetchone()[0] == 0

    @patch('intelligence.confidence_tracker.get_config')
    def test_uses_config_settings(self, mock_get_config, temp_db):
        """Test that tracker uses configuration settings."""
        mock_config = {
            'intelligence.confidence.min_samples': 3,
            'intelligence.confidence.high_success_threshold': 0.85,
            'intelligence.confidence.base_threshold': 0.8,
            'intelligence.confidence.high_risk_threshold': 0.9,
            'intelligence.confidence.risk_factors': {
                'has_security_implications': 0.5,
                'has_architecture_changes': 0.4
            }
        }
        mock_get_config.return_value = Mock()
        mock_get_config.return_value.get.side_effect = lambda key, default: mock_config.get(
            key, default)

        tracker = ConfidenceTracker(db_path=temp_db)

        # Test with high risk context - need risk > 0.7 to trigger high
        # threshold
        context = {
            "agent_confidence": 0.85,
            "gemini_confidence": 0.85,
            "has_security_implications": True,
            "has_architecture_changes": True,
            "affects_performance": True  # Total risk: 0.5 + 0.4 + 0.2 = 1.1 > 0.7
        }

        should_involve, confidence = tracker.should_involve_human(context)

        # Should use configured high_risk_threshold (0.9)
        # Combined confidence = 0.85, which is < 0.9
        assert should_involve
        assert confidence == 0.85
