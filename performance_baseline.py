#!/usr/bin/env python3
"""
Performance Baseline Metrics Collection
Establishes baseline performance metrics for the Agent Hive system.
"""

from datetime import datetime
from pathlib import Path
import json
import os
import sys
import time

import psutil
import sqlite3

class PerformanceBaseline:
    """Collects and reports baseline performance metrics."""

    def __init__(self):
        self.metrics: Dict[str, Any] = {}
        self.start_time = time.time()

    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system-level performance metrics."""
        try:
            return {
                "timestamp": datetime.now().isoformat(),
                "python_version": sys.version,
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "memory_used": psutil.virtual_memory().used,
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('.').percent,
                "process_memory": psutil.Process().memory_info().rss
            }
        except Exception as e:
            return {"error": str(e)}

    def collect_database_metrics(self) -> Dict[str, Any]:
        """Collect database file metrics."""
        db_metrics = {}

        # Find all SQLite databases
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.endswith('.db'):
                    file_path = os.path.join(root, file)
                    try:
                        size = os.path.getsize(file_path)
                        db_metrics[file] = {
                            "size_bytes": size,
                            "size_kb": size / 1024,
                            "path": file_path
                        }

                        # Try to get table info
                        try:
                            conn = sqlite3.connect(file_path)
                            cursor = conn.cursor()
                            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                            tables = [row[0] for row in cursor.fetchall()]
                            db_metrics[file]["tables"] = tables
                            conn.close()
                        except Exception:
                            db_metrics[file]["tables"] = []

                    except Exception as e:
                        db_metrics[file] = {"error": str(e)}

        return db_metrics

    def collect_file_metrics(self) -> Dict[str, Any]:
        """Collect file system metrics."""
        file_metrics = {
            "python_files": 0,
            "total_lines": 0,
            "largest_files": []
        }

        large_files = []

        for root, dirs, files in os.walk('.'):
            # Skip hidden directories and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        size = os.path.getsize(file_path)
                        file_metrics["python_files"] += 1

                        # Count lines
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = len(f.readlines())
                            file_metrics["total_lines"] += lines

                        large_files.append({
                            "file": file_path,
                            "size_bytes": size,
                            "lines": lines
                        })
                    except Exception:
                        continue

        # Sort by size and keep top 10
        large_files.sort(key=lambda x: x["size_bytes"], reverse=True)
        file_metrics["largest_files"] = large_files[:10]

        return file_metrics

    def measure_import_performance(self) -> Dict[str, Any]:
        """Measure import performance of key modules."""
        import_metrics = {}

        modules_to_test = [
            "json",
            "sqlite3",
            "psutil",
            "pathlib",
            "typing"
        ]

        for module in modules_to_test:
            try:
                start_time = time.time()
                __import__(module)
                import_time = time.time() - start_time
                import_metrics[module] = {
                    "import_time": import_time,
                    "success": True
                }
            except Exception as e:
                import_metrics[module] = {
                    "import_time": None,
                    "success": False,
                    "error": str(e)
                }

        return import_metrics

    def generate_report(self) -> str:
        """Generate a comprehensive performance baseline report."""
        print("🔍 Collecting System Metrics...")
        system_metrics = self.collect_system_metrics()

        print("🗄️  Collecting Database Metrics...")
        db_metrics = self.collect_database_metrics()

        print("📁 Collecting File Metrics...")
        file_metrics = self.collect_file_metrics()

        print("⚡ Measuring Import Performance...")
        import_metrics = self.measure_import_performance()

        total_time = time.time() - self.start_time

        # Compile all metrics
        all_metrics = {
            "collection_time": total_time,
            "system": system_metrics,
            "databases": db_metrics,
            "files": file_metrics,
            "imports": import_metrics
        }

        # Save to file
        with open('performance_baseline.json', 'w') as f:
            json.dump(all_metrics, f, indent=2)

        # Generate readable report
        report = []
        report.append("=" * 50)
        report.append("🚀 PERFORMANCE BASELINE REPORT")
        report.append("=" * 50)

        # System metrics
        if "error" not in system_metrics:
            report.append(f"🖥️  System Information:")
            report.append(f"   CPU Cores: {system_metrics['cpu_count']}")
            report.append(f"   CPU Usage: {system_metrics['cpu_percent']:.1f}%")
            report.append(f"   Memory: {system_metrics['memory_used'] / (1024**3):.1f}GB / {system_metrics['memory_total'] / (1024**3):.1f}GB ({system_metrics['memory_percent']:.1f}%)")
            report.append(f"   Process Memory: {system_metrics['process_memory'] / (1024**2):.1f}MB")
            report.append(f"   Disk Usage: {system_metrics['disk_usage']:.1f}%")

        # Database metrics
        report.append(f"\n🗄️  Database Files: {len(db_metrics)}")
        for db_name, db_info in db_metrics.items():
            if "error" not in db_info:
                report.append(f"   {db_name}: {db_info['size_kb']:.1f}KB ({len(db_info['tables'])} tables)")

        # File metrics
        report.append(f"\n📁 Code Files:")
        report.append(f"   Python Files: {file_metrics['python_files']}")
        report.append(f"   Total Lines: {file_metrics['total_lines']:,}")
        report.append(f"   Largest Files:")
        for file_info in file_metrics['largest_files'][:5]:
            report.append(f"      {file_info['file']}: {file_info['lines']} lines, {file_info['size_bytes']/1024:.1f}KB")

        # Import performance
        report.append(f"\n⚡ Import Performance:")
        for module, metrics in import_metrics.items():
            if metrics['success']:
                report.append(f"   {module}: {metrics['import_time']*1000:.1f}ms")
            else:
                report.append(f"   {module}: FAILED - {metrics['error']}")

        report.append(f"\n⏱️  Total Collection Time: {total_time:.2f}s")
        report.append("=" * 50)

        return "\n".join(report)


def main():
    """Main execution function."""
    baseline = PerformanceBaseline()
    report = baseline.generate_report()
    print(report)

    # Save report to file
    with open('performance_baseline_report.txt', 'w') as f:
        f.write(report)

    print(f"\n💾 Results saved to:")
    print(f"   - performance_baseline.json (raw data)")
    print(f"   - performance_baseline_report.txt (formatted report)")


if __name__ == "__main__":
    main()