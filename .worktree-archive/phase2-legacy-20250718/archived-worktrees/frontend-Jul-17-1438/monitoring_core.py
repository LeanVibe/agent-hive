#!/usr/bin/env python3
"""
Monitoring Core - Minimal baseline metrics collection
Foundation Epic Phase 1: Micro-component strategy

Essential system monitoring with SQLite storage.
Compliant micro-component: <300 lines core functionality.
"""

import sqlite3
import psutil
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


class MonitoringCore:
    """Minimal monitoring core with essential metrics collection."""
    
    def __init__(self, db_path: str = "monitoring.db"):
        self.db_path = db_path
        self.running = False
        self._init_database()
    
    def _init_database(self):
        """Initialize monitoring database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON metrics(timestamp)')
    
    def record_metric(self, name: str, value: float):
        """Record a single metric."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT INTO metrics (metric_name, value, timestamp) VALUES (?, ?, ?)',
                (name, value, datetime.now().isoformat())
            )
    
    def get_latest_metrics(self) -> Dict[str, Any]:
        """Get latest system metrics."""
        metrics = {}
        
        # CPU
        metrics['cpu_percent'] = psutil.cpu_percent(interval=0.1)
        
        # Memory
        memory = psutil.virtual_memory()
        metrics['memory_percent'] = memory.percent
        metrics['memory_mb'] = memory.used / (1024 * 1024)
        
        # Disk
        disk = psutil.disk_usage('/')
        metrics['disk_percent'] = disk.percent
        
        return metrics
    
    def collect_and_store(self):
        """Collect current metrics and store them."""
        metrics = self.get_latest_metrics()
        for name, value in metrics.items():
            self.record_metric(name, value)
        return metrics
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get basic health status."""
        metrics = self.get_latest_metrics()
        
        # Simple health scoring
        health_score = 100.0
        if metrics['cpu_percent'] > 80:
            health_score -= 30
        if metrics['memory_percent'] > 85:
            health_score -= 30
        if metrics['disk_percent'] > 90:
            health_score -= 40
        
        status = "healthy" if health_score > 70 else "warning" if health_score > 40 else "critical"
        
        return {
            "status": status,
            "health_score": health_score,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
    
    def start_monitoring(self):
        """Start monitoring (basic implementation)."""
        self.running = True
        logger.info("Monitoring core started")
    
    def stop_monitoring(self):
        """Stop monitoring."""
        self.running = False
        logger.info("Monitoring core stopped")


# Global instance
monitoring = MonitoringCore()


def get_system_health() -> Dict[str, Any]:
    """API function to get system health."""
    return monitoring.get_health_status()


def collect_metrics() -> Dict[str, Any]:
    """API function to collect current metrics."""
    return monitoring.collect_and_store()


if __name__ == "__main__":
    print("Monitoring Core - Micro Component Test")
    print("=" * 40)
    
    # Test basic functionality
    health = get_system_health()
    print(f"System Status: {health['status']}")
    print(f"Health Score: {health['health_score']:.1f}")
    
    # Collect metrics
    metrics = collect_metrics()
    print(f"CPU: {metrics['cpu_percent']:.1f}%")
    print(f"Memory: {metrics['memory_mb']:.0f}MB ({metrics['memory_percent']:.1f}%)")
    print(f"Disk: {metrics['disk_percent']:.1f}%")
    
    print("\nMonitoring core test complete!")