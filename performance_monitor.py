#!/usr/bin/env python3
"""
Performance Monitoring Module

Provides real-time performance tracking with <2s response time targets
and automated alerting for performance degradation.
"""

import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from contextlib import asynccontextmanager


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """Real-time performance monitoring with alerting."""
    
    def __init__(self, target_response_time: float = 2.0):
        self.target_response_time = target_response_time
        self.metrics: List[PerformanceMetrics] = []
        self.alerts: List[str] = []
        self.logger = logging.getLogger(__name__)
        
        # Performance thresholds
        self.thresholds = {
            'warning': target_response_time * 0.8,  # 1.6s
            'critical': target_response_time,       # 2.0s
            'failure': target_response_time * 1.5   # 3.0s
        }
    
    @asynccontextmanager
    async def track_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """Context manager for tracking operation performance."""
        start_time = time.time()
        metric = PerformanceMetrics(
            operation_name=operation_name,
            start_time=start_time,
            metadata=metadata or {}
        )
        
        try:
            yield metric
            metric.success = True
        except Exception as e:
            metric.success = False
            metric.error_message = str(e)
            self.logger.error(f"Operation {operation_name} failed: {e}")
            raise
        finally:
            end_time = time.time()
            duration = end_time - start_time
            
            metric.end_time = end_time
            metric.duration = duration
            
            self.metrics.append(metric)
            self._check_performance_thresholds(metric)
    
    def _check_performance_thresholds(self, metric: PerformanceMetrics) -> None:
        """Check if performance thresholds are exceeded."""
        if not metric.duration:
            return
        
        if metric.duration >= self.thresholds['failure']:
            alert = f"🔴 CRITICAL: {metric.operation_name} took {metric.duration:.2f}s (target: {self.target_response_time}s)"
            self.alerts.append(alert)
            self.logger.critical(alert)
        elif metric.duration >= self.thresholds['critical']:
            alert = f"🟡 WARNING: {metric.operation_name} took {metric.duration:.2f}s (approaching {self.target_response_time}s limit)"
            self.alerts.append(alert)
            self.logger.warning(alert)
        elif metric.duration >= self.thresholds['warning']:
            self.logger.info(f"📊 INFO: {metric.operation_name} took {metric.duration:.2f}s")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        if not self.metrics:
            return {"status": "no_data", "message": "No performance data available"}
        
        successful_metrics = [m for m in self.metrics if m.success and m.duration]
        failed_metrics = [m for m in self.metrics if not m.success]
        
        if not successful_metrics:
            return {"status": "all_failed", "failed_count": len(failed_metrics)}
        
        durations = [m.duration for m in successful_metrics]
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)
        
        # Calculate performance score (0-100)
        performance_score = max(0, 100 - (avg_duration / self.target_response_time * 50))
        
        # Count threshold violations
        violations = {
            'warning': len([d for d in durations if d >= self.thresholds['warning']]),
            'critical': len([d for d in durations if d >= self.thresholds['critical']]),
            'failure': len([d for d in durations if d >= self.thresholds['failure']])
        }
        
        return {
            "status": "healthy" if avg_duration < self.target_response_time else "degraded",
            "performance_score": round(performance_score, 1),
            "target_response_time": self.target_response_time,
            "metrics": {
                "total_operations": len(self.metrics),
                "successful_operations": len(successful_metrics),
                "failed_operations": len(failed_metrics),
                "average_duration": round(avg_duration, 3),
                "max_duration": round(max_duration, 3),
                "min_duration": round(min_duration, 3)
            },
            "violations": violations,
            "recent_alerts": self.alerts[-10:] if self.alerts else []
        }
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get statistics for a specific operation."""
        operation_metrics = [m for m in self.metrics if m.operation_name == operation_name and m.duration]
        
        if not operation_metrics:
            return {"status": "no_data", "operation": operation_name}
        
        durations = [m.duration for m in operation_metrics]
        success_rate = len([m for m in operation_metrics if m.success]) / len(operation_metrics) * 100
        
        return {
            "operation": operation_name,
            "count": len(operation_metrics),
            "success_rate": round(success_rate, 1),
            "average_duration": round(sum(durations) / len(durations), 3),
            "max_duration": round(max(durations), 3),
            "min_duration": round(min(durations), 3),
            "exceeds_target": len([d for d in durations if d > self.target_response_time])
        }
    
    def clear_metrics(self) -> None:
        """Clear all collected metrics."""
        self.metrics.clear()
        self.alerts.clear()
    
    def print_dashboard(self) -> None:
        """Print performance dashboard."""
        summary = self.get_performance_summary()
        
        print("🚀 PERFORMANCE DASHBOARD")
        print("=" * 25)
        
        if summary["status"] == "no_data":
            print("📊 No performance data available")
            return
        
        status_emoji = "✅" if summary["status"] == "healthy" else "⚠️"
        print(f"{status_emoji} Status: {summary['status'].title()}")
        print(f"📊 Performance Score: {summary['performance_score']}/100")
        print(f"🎯 Target Response Time: {summary['target_response_time']}s")
        print()
        
        metrics = summary["metrics"]
        print("📈 METRICS:")
        print(f"  Operations: {metrics['total_operations']} ({metrics['successful_operations']} successful)")
        print(f"  Avg Duration: {metrics['average_duration']}s")
        print(f"  Range: {metrics['min_duration']}s - {metrics['max_duration']}s")
        print()
        
        violations = summary["violations"]
        if any(violations.values()):
            print("⚠️ THRESHOLD VIOLATIONS:")
            if violations['failure']:
                print(f"  🔴 Critical: {violations['failure']} operations")
            if violations['critical']:
                print(f"  🟡 Warning: {violations['critical']} operations")
            if violations['warning']:
                print(f"  📊 Info: {violations['warning']} operations")
            print()
        
        if summary["recent_alerts"]:
            print("🔔 RECENT ALERTS:")
            for alert in summary["recent_alerts"]:
                print(f"  {alert}")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def performance_tracked(operation_name: str, metadata: Optional[Dict[str, Any]] = None):
    """Decorator for tracking function performance."""
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            async with performance_monitor.track_operation(operation_name, metadata):
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to create a simple timing wrapper
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                metric = PerformanceMetrics(
                    operation_name=operation_name,
                    start_time=start_time,
                    end_time=time.time(),
                    duration=duration,
                    success=True,
                    metadata=metadata or {}
                )
                performance_monitor.metrics.append(metric)
                performance_monitor._check_performance_thresholds(metric)
                return result
            except Exception as e:
                duration = time.time() - start_time
                metric = PerformanceMetrics(
                    operation_name=operation_name,
                    start_time=start_time,
                    end_time=time.time(),
                    duration=duration,
                    success=False,
                    error_message=str(e),
                    metadata=metadata or {}
                )
                performance_monitor.metrics.append(metric)
                performance_monitor._check_performance_thresholds(metric)
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator