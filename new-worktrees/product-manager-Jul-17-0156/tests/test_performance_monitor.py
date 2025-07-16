"""
Tests for the Performance Monitor system.

This module tests the comprehensive performance monitoring, analytics,
and optimization capabilities for the enhanced multi-agent coordination system.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from advanced_orchestration.performance_monitor import (
    PerformanceMonitor, PerformanceMetric, PerformanceMetricType,
    PerformanceAlert, PerformanceThreshold, PerformanceReport
)


class TestPerformanceMonitor:
    """Test suite for PerformanceMonitor."""
    
    @pytest.fixture
    def performance_monitor(self):
        """Create a performance monitor instance."""
        return PerformanceMonitor()
    
    @pytest.fixture
    def sample_metric(self):
        """Create a sample performance metric."""
        return PerformanceMetric(
            metric_type=PerformanceMetricType.LATENCY,
            value=1.5,
            timestamp=datetime.now(),
            agent_id="test-agent",
            workflow_id="test-workflow",
            task_id="test-task"
        )
    
    def test_initialization(self, performance_monitor):
        """Test performance monitor initialization."""
        monitor = performance_monitor
        
        assert monitor.metrics_store is not None
        assert monitor.alerts == []
        assert monitor.performance_history is not None
        assert monitor.agent_metrics is not None
        assert monitor.workflow_metrics is not None
        assert not monitor.running
        assert monitor.monitor_thread is None
        assert monitor.lock is not None
        
        # Check thresholds are properly configured
        assert PerformanceMetricType.LATENCY in monitor.thresholds
        assert PerformanceMetricType.THROUGHPUT in monitor.thresholds
        assert PerformanceMetricType.ERROR_RATE in monitor.thresholds
        
        # Check optimization strategies are configured
        assert PerformanceMetricType.LATENCY in monitor.optimization_strategies
        assert PerformanceMetricType.THROUGHPUT in monitor.optimization_strategies
    
    def test_start_stop_monitoring(self, performance_monitor):
        """Test starting and stopping performance monitoring."""
        monitor = performance_monitor
        
        # Test start
        monitor.start_monitoring()
        assert monitor.running
        assert monitor.monitor_thread is not None
        assert monitor.monitor_thread.is_alive()
        
        # Test stop
        monitor.stop_monitoring()
        assert not monitor.running
        
        # Wait for thread to finish
        time.sleep(0.1)
    
    def test_record_metric(self, performance_monitor, sample_metric):
        """Test recording performance metrics."""
        monitor = performance_monitor
        
        # Record metric
        monitor.record_metric(sample_metric)
        
        # Check metric was stored
        assert len(monitor.metrics_store) == 1
        stored_metric = monitor.metrics_store[0]
        assert stored_metric.metric_type == sample_metric.metric_type
        assert stored_metric.value == sample_metric.value
        assert stored_metric.agent_id == sample_metric.agent_id
        
        # Check agent metrics were updated
        assert sample_metric.agent_id in monitor.agent_metrics
        assert sample_metric.metric_type in monitor.agent_metrics[sample_metric.agent_id]
        assert sample_metric.value in monitor.agent_metrics[sample_metric.agent_id][sample_metric.metric_type]
        
        # Check workflow metrics were updated
        assert sample_metric.workflow_id in monitor.workflow_metrics
        assert sample_metric.metric_type in monitor.workflow_metrics[sample_metric.workflow_id]
        
        # Check performance history was updated
        history_key = f"{sample_metric.metric_type.value}_{sample_metric.agent_id}"
        assert history_key in monitor.performance_history
        assert sample_metric.value in monitor.performance_history[history_key]
    
    def test_threshold_violation_detection(self, performance_monitor):
        """Test threshold violation detection and alert generation."""
        monitor = performance_monitor
        
        # Create metric that violates critical threshold
        critical_metric = PerformanceMetric(
            metric_type=PerformanceMetricType.LATENCY,
            value=10.0,  # Exceeds critical threshold of 5.0
            timestamp=datetime.now(),
            agent_id="slow-agent"
        )
        
        monitor.record_metric(critical_metric)
        
        # Check alert was generated
        assert len(monitor.alerts) == 1
        alert = monitor.alerts[0]
        assert alert.metric_type == PerformanceMetricType.LATENCY
        assert alert.severity == "critical"
        assert alert.current_value == 10.0
        assert alert.agent_id == "slow-agent"
        assert alert.recommendation is not None
    
    def test_warning_threshold_detection(self, performance_monitor):
        """Test warning threshold detection."""
        monitor = performance_monitor
        
        # Create metric that violates warning threshold
        warning_metric = PerformanceMetric(
            metric_type=PerformanceMetricType.LATENCY,
            value=3.0,  # Exceeds warning threshold of 2.0 but not critical
            timestamp=datetime.now(),
            agent_id="slow-agent"
        )
        
        monitor.record_metric(warning_metric)
        
        # Check warning alert was generated
        assert len(monitor.alerts) == 1
        alert = monitor.alerts[0]
        assert alert.severity == "warning"
        assert alert.current_value == 3.0
    
    def test_optimization_threshold_detection(self, performance_monitor):
        """Test optimization opportunity detection."""
        monitor = performance_monitor
        
        # Create metric that indicates optimization opportunity
        optimization_metric = PerformanceMetric(
            metric_type=PerformanceMetricType.LATENCY,
            value=0.5,  # Below optimization threshold of 1.0
            timestamp=datetime.now(),
            agent_id="fast-agent"
        )
        
        monitor.record_metric(optimization_metric)
        
        # Check optimization alert was generated
        assert len(monitor.alerts) == 1
        alert = monitor.alerts[0]
        assert alert.severity == "optimization"
        assert alert.current_value == 0.5
    
    def test_recommendation_generation(self, performance_monitor):
        """Test performance recommendation generation."""
        monitor = performance_monitor
        
        # Test different metric types
        test_cases = [
            (PerformanceMetricType.LATENCY, "Consider optimizing task routing"),
            (PerformanceMetricType.THROUGHPUT, "Consider increasing agent parallelism"),
            (PerformanceMetricType.ERROR_RATE, "Review error handling"),
            (PerformanceMetricType.COORDINATION_EFFICIENCY, "Optimize agent communication"),
        ]
        
        threshold = PerformanceThreshold(
            PerformanceMetricType.LATENCY,
            warning_threshold=2.0,
            critical_threshold=5.0,
            optimization_threshold=1.0,
            measurement_unit="seconds"
        )
        
        for metric_type, expected_phrase in test_cases:
            metric = PerformanceMetric(
                metric_type=metric_type,
                value=10.0,
                timestamp=datetime.now(),
                agent_id="test-agent"
            )
            
            recommendation = monitor._generate_recommendation(metric, threshold)
            assert expected_phrase in recommendation
            assert "test-agent" in recommendation
    
    def test_system_metrics_collection(self, performance_monitor):
        """Test system-wide metrics collection."""
        monitor = performance_monitor
        
        # Mock some workflow metrics to enable calculation
        monitor.workflow_metrics["test-workflow"] = {
            PerformanceMetricType.WORKFLOW_COMPLETION_TIME: [10.0, 12.0, 8.0, 15.0]
        }
        
        # Test coordination efficiency calculation
        efficiency = monitor._calculate_coordination_efficiency()
        assert efficiency is not None
        assert 0.0 <= efficiency <= 1.0
    
    def test_parallel_efficiency_calculation(self, performance_monitor):
        """Test parallel execution efficiency calculation."""
        monitor = performance_monitor
        
        # Mock agent metrics
        monitor.agent_metrics["agent-1"] = {
            PerformanceMetricType.AGENT_PRODUCTIVITY: [10.0, 12.0, 9.0]
        }
        monitor.agent_metrics["agent-2"] = {
            PerformanceMetricType.AGENT_PRODUCTIVITY: [8.0, 11.0, 10.0]
        }
        
        efficiency = monitor._calculate_parallel_efficiency()
        assert efficiency is not None
        assert 0.0 <= efficiency <= 1.0
    
    def test_performance_trends_analysis(self, performance_monitor):
        """Test performance trend analysis."""
        monitor = performance_monitor
        
        # Add performance history that shows degradation
        history_key = f"{PerformanceMetricType.LATENCY.value}_global"
        monitor.performance_history[history_key] = [1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
        
        # Capture log output to verify trend detection
        with patch.object(monitor.logger, 'warning') as mock_warning:
            monitor._analyze_performance_trends()
            
            # Should detect degradation
            mock_warning.assert_called()
            warning_call = mock_warning.call_args[0][0]
            assert "Performance degradation detected" in warning_call
            assert PerformanceMetricType.LATENCY.value in warning_call
    
    def test_performance_report_generation(self, performance_monitor):
        """Test comprehensive performance report generation."""
        monitor = performance_monitor
        
        # Add some sample metrics
        metrics = [
            PerformanceMetric(PerformanceMetricType.LATENCY, 2.0, datetime.now()),
            PerformanceMetric(PerformanceMetricType.THROUGHPUT, 15.0, datetime.now()),
            PerformanceMetric(PerformanceMetricType.ERROR_RATE, 0.05, datetime.now()),
        ]
        
        for metric in metrics:
            monitor.record_metric(metric)
        
        # Generate report
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        report = monitor.generate_performance_report((start_time, end_time))
        
        assert isinstance(report, PerformanceReport)
        assert report.report_id is not None
        assert report.generated_at is not None
        assert report.time_period == (start_time, end_time)
        assert report.metrics_summary is not None
        assert len(report.metrics_summary) > 0
        
        # Check metrics summary structure
        for metric_type, stats in report.metrics_summary.items():
            assert "avg" in stats
            assert "min" in stats
            assert "max" in stats
            assert "count" in stats
    
    def test_real_time_metrics(self, performance_monitor):
        """Test real-time metrics retrieval."""
        monitor = performance_monitor
        
        # Add recent metrics
        recent_time = datetime.now()
        metrics = [
            PerformanceMetric(PerformanceMetricType.LATENCY, 1.5, recent_time),
            PerformanceMetric(PerformanceMetricType.THROUGHPUT, 20.0, recent_time),
        ]
        
        for metric in metrics:
            monitor.record_metric(metric)
        
        # Get real-time metrics
        real_time_data = monitor.get_real_time_metrics()
        
        assert "timestamp" in real_time_data
        assert "metrics" in real_time_data
        assert "active_alerts" in real_time_data
        assert "total_measurements" in real_time_data
        
        # Check metrics structure
        metrics_data = real_time_data["metrics"]
        assert PerformanceMetricType.LATENCY.value in metrics_data
        assert PerformanceMetricType.THROUGHPUT.value in metrics_data
        
        latency_data = metrics_data[PerformanceMetricType.LATENCY.value]
        assert "current" in latency_data
        assert "avg_5min" in latency_data
        assert latency_data["current"] == 1.5
    
    def test_agent_performance_summary(self, performance_monitor):
        """Test agent-specific performance summary."""
        monitor = performance_monitor
        
        # Add agent-specific metrics
        agent_metrics = [
            PerformanceMetric(PerformanceMetricType.LATENCY, 1.0, datetime.now(), agent_id="agent-1"),
            PerformanceMetric(PerformanceMetricType.LATENCY, 1.2, datetime.now(), agent_id="agent-1"),
            PerformanceMetric(PerformanceMetricType.THROUGHPUT, 15.0, datetime.now(), agent_id="agent-1"),
            PerformanceMetric(PerformanceMetricType.LATENCY, 2.0, datetime.now(), agent_id="agent-2"),
        ]
        
        for metric in agent_metrics:
            monitor.record_metric(metric)
        
        # Get agent performance summary
        summary = monitor.get_agent_performance_summary()
        
        assert "agent-1" in summary
        assert "agent-2" in summary
        
        agent1_summary = summary["agent-1"]
        assert PerformanceMetricType.LATENCY.value in agent1_summary
        assert PerformanceMetricType.THROUGHPUT.value in agent1_summary
        
        latency_stats = agent1_summary[PerformanceMetricType.LATENCY.value]
        assert "current" in latency_stats
        assert "average" in latency_stats
        assert "best" in latency_stats
        assert "stability" in latency_stats
        
        # Check values
        assert latency_stats["current"] == 1.2  # Last recorded value
        assert latency_stats["average"] == 1.1  # Average of 1.0 and 1.2
        assert latency_stats["best"] == 1.0     # Minimum for latency
    
    def test_trend_calculation(self, performance_monitor):
        """Test performance trend calculation."""
        monitor = performance_monitor
        
        # Test improving trend
        improving_values = [5.0, 4.5, 4.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0]
        improving_trend = monitor._calculate_trend(improving_values)
        assert improving_trend < 0  # Negative trend for latency is good (improving)
        
        # Test degrading trend
        degrading_values = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
        degrading_trend = monitor._calculate_trend(degrading_values)
        assert degrading_trend > 0  # Positive trend for latency is bad (degrading)
        
        # Test stable trend
        stable_values = [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0]
        stable_trend = monitor._calculate_trend(stable_values)
        assert abs(stable_trend) < 0.1  # Near zero for stable performance
        
        # Test edge cases
        assert monitor._calculate_trend([]) == 0.0
        assert monitor._calculate_trend([1.0]) == 0.0
    
    def test_metric_ring_buffer(self, performance_monitor):
        """Test that metrics store maintains ring buffer size."""
        monitor = performance_monitor
        
        # Add more metrics than buffer size
        buffer_size = 10000
        excess_metrics = buffer_size + 100
        
        for i in range(excess_metrics):
            metric = PerformanceMetric(
                PerformanceMetricType.LATENCY,
                float(i),
                datetime.now()
            )
            monitor.record_metric(metric)
        
        # Check that buffer size is maintained
        assert len(monitor.metrics_store) == buffer_size
        
        # Check that oldest metrics were evicted (values should start from 100)
        oldest_metric = monitor.metrics_store[0]
        assert oldest_metric.value >= 100.0
    
    def test_alert_cleanup(self, performance_monitor):
        """Test automatic cleanup of old alerts."""
        monitor = performance_monitor
        
        # Create old and new alerts
        old_time = datetime.now() - timedelta(hours=25)  # Older than 24 hours
        new_time = datetime.now()
        
        old_alert = PerformanceAlert(
            alert_id="old_alert",
            metric_type=PerformanceMetricType.LATENCY,
            severity="warning",
            current_value=3.0,
            threshold_value=2.0,
            timestamp=old_time
        )
        
        new_alert = PerformanceAlert(
            alert_id="new_alert",
            metric_type=PerformanceMetricType.LATENCY,
            severity="warning",
            current_value=3.0,
            threshold_value=2.0,
            timestamp=new_time
        )
        
        monitor.alerts = [old_alert, new_alert]
        
        # Run cleanup
        monitor._cleanup_old_alerts()
        
        # Check that only new alert remains
        assert len(monitor.alerts) == 1
        assert monitor.alerts[0].alert_id == "new_alert"
    
    def test_performance_recommendations(self, performance_monitor):
        """Test performance improvement recommendation generation."""
        monitor = performance_monitor
        
        # Create metrics summary with various performance levels
        metrics_summary = {
            PerformanceMetricType.LATENCY: {"avg": 6.0},  # Critical
            PerformanceMetricType.THROUGHPUT: {"avg": 8.0},  # Warning
            PerformanceMetricType.ERROR_RATE: {"avg": 0.008},  # Optimization opportunity
        }
        
        recommendations = monitor._generate_performance_recommendations(metrics_summary)
        
        assert len(recommendations) == 3
        
        # Check critical recommendation
        critical_rec = next(rec for rec in recommendations if "CRITICAL" in rec)
        assert "latency" in critical_rec.lower()
        assert "immediate action required" in critical_rec.lower()
        
        # Check warning recommendation
        warning_rec = next(rec for rec in recommendations if "WARNING" in rec)
        assert "throughput" in warning_rec.lower()
        assert "consider optimization" in warning_rec.lower()
        
        # Check optimization opportunity
        opportunity_rec = next(rec for rec in recommendations if "OPPORTUNITY" in rec)
        assert "error_rate" in opportunity_rec.lower()
        assert "excellent" in opportunity_rec.lower()


class TestPerformanceIntegration:
    """Integration tests for performance monitoring system."""
    
    @pytest.fixture
    def running_monitor(self):
        """Create a running performance monitor."""
        monitor = PerformanceMonitor()
        monitor.start_monitoring()
        yield monitor
        monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_concurrent_metric_recording(self, running_monitor):
        """Test concurrent metric recording."""
        monitor = running_monitor
        
        # Record metrics concurrently
        async def record_metrics(agent_id, count):
            for i in range(count):
                metric = PerformanceMetric(
                    PerformanceMetricType.LATENCY,
                    float(i),
                    datetime.now(),
                    agent_id=agent_id
                )
                monitor.record_metric(metric)
                await asyncio.sleep(0.01)  # Small delay
        
        # Run concurrent tasks
        tasks = [
            record_metrics("agent-1", 10),
            record_metrics("agent-2", 10),
            record_metrics("agent-3", 10),
        ]
        
        await asyncio.gather(*tasks)
        
        # Check that all metrics were recorded
        assert len(monitor.metrics_store) == 30
        assert len(monitor.agent_metrics) == 3
        
        # Check that each agent has correct number of metrics
        for agent_id in ["agent-1", "agent-2", "agent-3"]:
            assert agent_id in monitor.agent_metrics
            latency_metrics = monitor.agent_metrics[agent_id][PerformanceMetricType.LATENCY]
            assert len(latency_metrics) == 10
    
    def test_monitoring_lifecycle(self):
        """Test complete monitoring lifecycle."""
        monitor = PerformanceMonitor()
        
        # Start monitoring
        monitor.start_monitoring()
        assert monitor.running
        assert monitor.monitor_thread.is_alive()
        
        # Record some metrics
        metrics = [
            PerformanceMetric(PerformanceMetricType.LATENCY, 2.0, datetime.now()),
            PerformanceMetric(PerformanceMetricType.THROUGHPUT, 15.0, datetime.now()),
        ]
        
        for metric in metrics:
            monitor.record_metric(metric)
        
        # Wait for monitoring loop to process
        time.sleep(0.1)
        
        # Check that monitoring is active
        assert monitor.running
        assert len(monitor.metrics_store) == 2
        
        # Stop monitoring
        monitor.stop_monitoring()
        assert not monitor.running
        
        # Wait for thread to finish
        time.sleep(0.1)
        assert not monitor.monitor_thread.is_alive()
    
    def test_performance_optimization_workflow(self):
        """Test complete performance optimization workflow."""
        monitor = PerformanceMonitor()
        
        # Step 1: Record problematic metrics
        problematic_metric = PerformanceMetric(
            PerformanceMetricType.LATENCY,
            10.0,  # Critical latency
            datetime.now(),
            agent_id="slow-agent"
        )
        monitor.record_metric(problematic_metric)
        
        # Step 2: Check alert generation
        assert len(monitor.alerts) == 1
        alert = monitor.alerts[0]
        assert alert.severity == "critical"
        assert alert.auto_fix_available
        
        # Step 3: Generate performance report
        report = monitor.generate_performance_report()
        assert len(report.recommendations) > 0
        
        # Step 4: Check that critical issue is flagged in recommendations
        critical_recommendations = [rec for rec in report.recommendations if "CRITICAL" in rec]
        assert len(critical_recommendations) > 0
        
        # Step 5: Verify real-time metrics reflect the issue
        real_time_data = monitor.get_real_time_metrics()
        assert real_time_data["active_alerts"] > 0