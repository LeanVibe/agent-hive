#!/usr/bin/env python3
"""
Tests for the Baseline Metrics System

Comprehensive test suite for the observability baseline metrics components.
"""

import pytest
import json
import time
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sqlite3

from observability.baseline_metrics import (
    BaselineMetric,
    PerformanceBaseline,
    MetricsCollector,
    BaselineAnalyzer,
    metrics_collector,
    start_baseline_monitoring,
    stop_baseline_monitoring,
    get_baseline_report
)


class TestBaselineMetric:
    """Test BaselineMetric class functionality."""
    
    def test_baseline_metric_creation(self):
        """Test basic baseline metric creation."""
        timestamp = datetime.now()
        metric = BaselineMetric(
            metric_name="cpu_usage",
            value=45.5,
            unit="%",
            timestamp=timestamp,
            agent_id="agent_001",
            session_id="session_001",
            metadata={"host": "localhost"}
        )
        
        assert metric.metric_name == "cpu_usage"
        assert metric.value == 45.5
        assert metric.unit == "%"
        assert metric.timestamp == timestamp
        assert metric.agent_id == "agent_001"
        assert metric.session_id == "session_001"
        assert metric.metadata["host"] == "localhost"
    
    def test_baseline_metric_serialization(self):
        """Test baseline metric serialization to dictionary."""
        timestamp = datetime.now()
        metric = BaselineMetric(
            metric_name="memory_usage",
            value=256.0,
            unit="MB",
            timestamp=timestamp,
            metadata={"process": "agent_hive"}
        )
        
        metric_dict = metric.to_dict()
        
        assert metric_dict["metric_name"] == "memory_usage"
        assert metric_dict["value"] == 256.0
        assert metric_dict["unit"] == "MB"
        assert "timestamp" in metric_dict
        assert metric_dict["metadata"]["process"] == "agent_hive"


class TestPerformanceBaseline:
    """Test PerformanceBaseline class functionality."""
    
    def test_performance_baseline_creation(self):
        """Test performance baseline creation with defaults."""
        baseline = PerformanceBaseline()
        
        assert baseline.agent_coordination_success_rate == 0.95
        assert baseline.avg_task_assignment_time == 0.5
        assert baseline.features_per_week == 7.5
        assert baseline.bug_rate == 0.03
        assert baseline.mttr_seconds == 240.0
        assert baseline.memory_usage_mb == 256.0
        assert baseline.timestamp is not None
    
    def test_performance_baseline_custom_values(self):
        """Test performance baseline with custom values."""
        custom_timestamp = datetime.now()
        baseline = PerformanceBaseline(
            agent_coordination_success_rate=0.99,
            features_per_week=15.0,
            bug_rate=0.01,
            timestamp=custom_timestamp
        )
        
        assert baseline.agent_coordination_success_rate == 0.99
        assert baseline.features_per_week == 15.0
        assert baseline.bug_rate == 0.01
        assert baseline.timestamp == custom_timestamp


class TestMetricsCollector:
    """Test MetricsCollector class functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.collector = MetricsCollector(db_path=self.temp_db.name)
    
    def teardown_method(self):
        """Clean up test environment."""
        self.collector.stop_collection()
        os.unlink(self.temp_db.name)
    
    def test_metrics_collector_initialization(self):
        """Test metrics collector initialization."""
        assert self.collector.db_path == self.temp_db.name
        assert len(self.collector.metrics_history) == 0
        assert isinstance(self.collector.current_baseline, PerformanceBaseline)
        assert self.collector.collection_interval == 60
        assert self.collector.running is False
    
    def test_database_initialization(self):
        """Test database initialization."""
        # Check if tables exist
        with sqlite3.connect(self.collector.db_path) as conn:
            cursor = conn.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('baseline_metrics', 'performance_baselines')
            ''')
            tables = [row[0] for row in cursor.fetchall()]
        
        assert 'baseline_metrics' in tables
        assert 'performance_baselines' in tables
    
    def test_record_metric(self):
        """Test metric recording."""
        timestamp = datetime.now()
        
        self.collector.record_metric(
            metric_name="test_metric",
            value=42.0,
            unit="units",
            timestamp=timestamp,
            agent_id="agent_001",
            metadata={"test": "data"}
        )
        
        # Check in-memory storage
        assert len(self.collector.metrics_history) == 1
        metric = self.collector.metrics_history[0]
        assert metric.metric_name == "test_metric"
        assert metric.value == 42.0
        assert metric.unit == "units"
        assert metric.agent_id == "agent_001"
        
        # Check database storage
        with sqlite3.connect(self.collector.db_path) as conn:
            cursor = conn.execute('SELECT * FROM baseline_metrics')
            rows = cursor.fetchall()
        
        assert len(rows) == 1
        assert rows[0][1] == "test_metric"  # metric_name
        assert rows[0][2] == 42.0  # value
        assert rows[0][3] == "units"  # unit
        assert rows[0][5] == "agent_001"  # agent_id
    
    def test_get_metric_stats(self):
        """Test metric statistics retrieval."""
        # Record test metrics
        base_time = datetime.now()
        test_values = [10.0, 20.0, 30.0, 40.0, 50.0]
        
        for i, value in enumerate(test_values):
            timestamp = base_time + timedelta(minutes=i)
            self.collector.record_metric("test_metric", value, "units", timestamp)
        
        # Get statistics
        stats = self.collector.get_metric_stats("test_metric", hours=1)
        
        assert stats["metric_name"] == "test_metric"
        assert stats["count"] == 5
        assert stats["mean"] == 30.0
        assert stats["median"] == 30.0
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
        assert stats["latest"] == 50.0
    
    def test_get_metric_stats_no_data(self):
        """Test metric statistics with no data."""
        stats = self.collector.get_metric_stats("nonexistent_metric")
        
        assert "error" in stats
        assert "No data found" in stats["error"]
    
    def test_get_baseline_summary(self):
        """Test baseline summary retrieval."""
        # Record some metrics
        self.collector.record_metric("memory_usage_mb", 128.0, "MB")
        self.collector.record_metric("cpu_usage_percent", 25.0, "%")
        
        summary = self.collector.get_baseline_summary()
        
        assert "timestamp" in summary
        assert summary["metrics_collected"] == 2
        assert summary["collection_running"] is False
        assert summary["baseline_version"] == "1.0.0"
        assert "current_baseline" in summary
        assert "key_metrics" in summary
    
    def test_save_and_load_baseline_snapshot(self):
        """Test baseline snapshot save and load."""
        # Save baseline
        self.collector.save_baseline_snapshot("test_v1.0")
        
        # Load baseline
        loaded_baseline = self.collector.load_baseline_snapshot("test_v1.0")
        
        assert loaded_baseline is not None
        assert loaded_baseline.agent_coordination_success_rate == 0.95
        assert loaded_baseline.features_per_week == 7.5
        assert loaded_baseline.bug_rate == 0.03
    
    def test_export_metrics_json(self):
        """Test metrics export to JSON."""
        # Record test metrics
        self.collector.record_metric("test_metric", 42.0, "units")
        self.collector.record_metric("test_metric", 43.0, "units")
        
        # Export to temporary file
        temp_export = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        temp_export.close()
        
        try:
            self.collector.export_metrics(temp_export.name, "json")
            
            # Verify export
            with open(temp_export.name, 'r') as f:
                exported_data = json.load(f)
            
            assert "export_timestamp" in exported_data
            assert "metrics_count" in exported_data
            assert exported_data["metrics_count"] == 2
            assert "metrics" in exported_data
            assert len(exported_data["metrics"]) == 2
            
        finally:
            os.unlink(temp_export.name)
    
    def test_export_metrics_csv(self):
        """Test metrics export to CSV."""
        # Record test metrics
        self.collector.record_metric("test_metric", 42.0, "units")
        
        # Export to temporary file
        temp_export = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        temp_export.close()
        
        try:
            self.collector.export_metrics(temp_export.name, "csv")
            
            # Verify export
            with open(temp_export.name, 'r') as f:
                content = f.read()
            
            assert "metric_name" in content
            assert "test_metric" in content
            assert "42.0" in content
            
        finally:
            os.unlink(temp_export.name)
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    @patch('psutil.pids')
    def test_collect_system_metrics(self, mock_pids, mock_net, mock_disk, mock_cpu, mock_memory):
        """Test system metrics collection."""
        # Mock psutil calls
        mock_memory.return_value = MagicMock(used=268435456, percent=25.0)  # 256MB
        mock_cpu.return_value = 35.0
        mock_disk.return_value = MagicMock(percent=45.0)
        mock_net.return_value = MagicMock(bytes_sent=1000, bytes_recv=2000)
        mock_pids.return_value = [1, 2, 3, 4, 5]
        
        # Collect metrics
        self.collector._collect_system_metrics()
        
        # Verify metrics were recorded
        assert len(self.collector.metrics_history) > 0
        
        # Check specific metrics
        metric_names = [m.metric_name for m in self.collector.metrics_history]
        assert "memory_usage_mb" in metric_names
        assert "cpu_usage_percent" in metric_names
        assert "disk_usage_percent" in metric_names
        assert "process_count" in metric_names
    
    def test_start_stop_collection(self):
        """Test starting and stopping metrics collection."""
        # Start collection
        self.collector.start_collection()
        assert self.collector.running is True
        assert self.collector.collection_thread is not None
        
        # Stop collection
        self.collector.stop_collection()
        assert self.collector.running is False


class TestBaselineAnalyzer:
    """Test BaselineAnalyzer class functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.collector = MetricsCollector(db_path=self.temp_db.name)
        self.analyzer = BaselineAnalyzer(self.collector)
    
    def teardown_method(self):
        """Clean up test environment."""
        self.collector.stop_collection()
        os.unlink(self.temp_db.name)
    
    def test_analyze_trends_insufficient_data(self):
        """Test trend analysis with insufficient data."""
        result = self.analyzer.analyze_trends("nonexistent_metric")
        
        assert "error" in result
        assert "Insufficient data" in result["error"]
    
    def test_analyze_trends_with_data(self):
        """Test trend analysis with sufficient data."""
        # Record metrics with increasing trend
        base_time = datetime.now() - timedelta(hours=5)
        for i in range(10):
            timestamp = base_time + timedelta(hours=i)
            value = 10.0 + i * 2.0  # Increasing trend
            self.collector.record_metric("test_metric", value, "units", timestamp)
        
        # Analyze trends
        result = self.analyzer.analyze_trends("test_metric", hours=6)
        
        assert result["metric_name"] == "test_metric"
        assert result["trend"] == "increasing"
        assert result["slope"] > 0
        assert result["data_points"] >= 1
        assert "latest_value" in result
        assert "average_value" in result
    
    def test_identify_performance_opportunities_good_performance(self):
        """Test performance opportunity identification with good performance."""
        # Record good performance metrics
        self.collector.record_metric("memory_usage_mb", 200.0, "MB")
        self.collector.record_metric("cpu_usage_percent", 30.0, "%")
        
        opportunities = self.analyzer.identify_performance_opportunities()
        
        assert opportunities["opportunities_count"] == 0
        assert opportunities["overall_health"] == "good"
        assert "opportunities" in opportunities
    
    def test_identify_performance_opportunities_poor_performance(self):
        """Test performance opportunity identification with poor performance."""
        # Record poor performance metrics
        self.collector.record_metric("memory_usage_mb", 500.0, "MB")
        self.collector.record_metric("cpu_usage_percent", 80.0, "%")
        
        opportunities = self.analyzer.identify_performance_opportunities()
        
        assert opportunities["opportunities_count"] > 0
        assert opportunities["overall_health"] == "needs_attention"
        
        # Check specific opportunities
        opportunity_categories = [opp["category"] for opp in opportunities["opportunities"]]
        assert "memory" in opportunity_categories
        assert "cpu" in opportunity_categories
    
    def test_generate_baseline_report(self):
        """Test baseline report generation."""
        # Record some metrics
        self.collector.record_metric("memory_usage_mb", 128.0, "MB")
        self.collector.record_metric("cpu_usage_percent", 25.0, "%")
        
        report = self.analyzer.generate_baseline_report()
        
        assert "report_timestamp" in report
        assert "baseline_version" in report
        assert "system_summary" in report
        assert "performance_opportunities" in report
        assert "trends" in report
        assert "roadmap_progress" in report
        
        # Check roadmap progress structure
        roadmap = report["roadmap_progress"]
        assert "agent_coordination_success_rate" in roadmap
        assert "features_per_week" in roadmap
        assert "mttr_seconds" in roadmap
        
        # Each progress item should have current, target, and progress
        for metric_name, metric_data in roadmap.items():
            assert "current" in metric_data
            assert "target" in metric_data
            assert "progress" in metric_data


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    def test_start_stop_baseline_monitoring(self):
        """Test global monitoring start/stop functions."""
        # These functions should work with the global metrics_collector
        start_baseline_monitoring()
        assert metrics_collector.running is True
        
        stop_baseline_monitoring()
        assert metrics_collector.running is False
    
    @patch('observability.baseline_metrics.baseline_analyzer')
    def test_get_baseline_report(self, mock_analyzer):
        """Test global baseline report function."""
        # Mock the analyzer response
        mock_report = {
            "report_timestamp": "2024-01-01T00:00:00",
            "baseline_version": "1.0.0",
            "system_summary": {"metrics_collected": 0}
        }
        mock_analyzer.generate_baseline_report.return_value = mock_report
        
        report = get_baseline_report()
        
        assert report == mock_report
        mock_analyzer.generate_baseline_report.assert_called_once()


class TestIntegration:
    """Integration tests for the complete baseline metrics system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.collector = MetricsCollector(db_path=self.temp_db.name)
        self.analyzer = BaselineAnalyzer(self.collector)
    
    def teardown_method(self):
        """Clean up test environment."""
        self.collector.stop_collection()
        os.unlink(self.temp_db.name)
    
    def test_complete_baseline_workflow(self):
        """Test complete baseline metrics workflow."""
        # Record various metrics
        metrics_data = [
            ("memory_usage_mb", 128.0, "MB"),
            ("cpu_usage_percent", 25.0, "%"),
            ("disk_usage_percent", 45.0, "%"),
            ("response_time_ms", 150.0, "ms"),
            ("throughput_rps", 100.0, "rps")
        ]
        
        for metric_name, value, unit in metrics_data:
            self.collector.record_metric(metric_name, value, unit)
        
        # Get statistics for each metric
        for metric_name, _, _ in metrics_data:
            stats = self.collector.get_metric_stats(metric_name)
            assert "error" not in stats
            assert stats["count"] == 1
            assert stats["latest"] == stats["mean"]
        
        # Generate baseline summary
        summary = self.collector.get_baseline_summary()
        assert summary["metrics_collected"] == len(metrics_data)
        assert "current_baseline" in summary
        
        # Save and load baseline snapshot
        self.collector.save_baseline_snapshot("integration_test")
        loaded_baseline = self.collector.load_baseline_snapshot("integration_test")
        assert loaded_baseline is not None
        
        # Generate performance analysis
        opportunities = self.analyzer.identify_performance_opportunities()
        assert "opportunities" in opportunities
        assert "overall_health" in opportunities
        
        # Generate complete report
        report = self.analyzer.generate_baseline_report()
        assert "report_timestamp" in report
        assert "system_summary" in report
        assert "performance_opportunities" in report
        assert "roadmap_progress" in report
        
        # Export metrics
        temp_export = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        temp_export.close()
        
        try:
            self.collector.export_metrics(temp_export.name, "json")
            
            with open(temp_export.name, 'r') as f:
                exported_data = json.load(f)
            
            assert exported_data["metrics_count"] == len(metrics_data)
            assert len(exported_data["metrics"]) == len(metrics_data)
            
        finally:
            os.unlink(temp_export.name)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])