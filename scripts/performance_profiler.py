#!/usr/bin/env python3
"""
LeanVibe Performance Profiler - Phase 2 Optimization Tool

Advanced performance monitoring and optimization for the LeanVibe Agent Hive.
Identifies bottlenecks, memory leaks, and optimization opportunities.
"""

import asyncio
import cProfile
import io
import json
import logging
import os
import pstats
import psutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import tracemalloc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/performance_profiler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('PerformanceProfiler')


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    disk_usage_mb: float
    network_io: Dict[str, int]
    process_count: int
    load_average: List[float]
    execution_time: float
    function_calls: int
    memory_peak_mb: float


@dataclass
class BottleneckReport:
    """Container for bottleneck analysis."""
    function_name: str
    total_time: float
    calls: int
    time_per_call: float
    cumulative_time: float
    percentage: float
    file_location: str


class PerformanceProfiler:
    """Advanced performance profiler for LeanVibe Agent Hive."""

    def __init__(self, output_dir: str = "performance_reports"):
        """Initialize the performance profiler."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Create logs directory
        Path("logs").mkdir(exist_ok=True)

        self.metrics_history: List[PerformanceMetrics] = []
        self.profiling_active = False
        self.start_time = None

        # Initialize system monitoring
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024

        logger.info("PerformanceProfiler initialized")

    def start_profiling(self):
        """Start performance profiling session."""
        logger.info("🚀 Starting performance profiling session")

        # Start memory tracing
        tracemalloc.start()

        # Initialize profiler
        self.profiler = cProfile.Profile()
        self.profiler.enable()

        self.profiling_active = True
        self.start_time = time.time()

        logger.info("✅ Performance profiling active")

    def stop_profiling(self) -> Dict[str, Any]:
        """Stop profiling and generate report."""
        if not self.profiling_active:
            logger.warning("Profiling not active")
            return {}

        logger.info("🛑 Stopping performance profiling")

        # Stop profiler
        self.profiler.disable()

        # Get memory tracing info
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Generate comprehensive report
        report = self._generate_performance_report(current, peak)

        self.profiling_active = False

        logger.info("✅ Performance profiling stopped")
        return report

    def capture_metrics(self) -> PerformanceMetrics:
        """Capture current system metrics."""
        try:
            # CPU and memory metrics
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            # Disk usage
            disk_usage = psutil.disk_usage('/')
            disk_usage_mb = disk_usage.used / 1024 / 1024

            # Network I/O
            net_io = psutil.net_io_counters()
            network_io = {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv
            } if net_io else {'bytes_sent': 0, 'bytes_recv': 0}

            # System metrics
            load_avg = list(os.getloadavg()) if hasattr(os, 'getloadavg') else [0.0, 0.0, 0.0]
            process_count = len(psutil.pids())

            # Execution time
            execution_time = time.time() - self.start_time if self.start_time else 0

            # Get current memory tracing
            current_memory = 0
            if tracemalloc.is_tracing():
                current, peak = tracemalloc.get_traced_memory()
                current_memory = current / 1024 / 1024

            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                disk_usage_mb=disk_usage_mb,
                network_io=network_io,
                process_count=process_count,
                load_average=load_avg,
                execution_time=execution_time,
                function_calls=0,  # Will be updated in profiling report
                memory_peak_mb=current_memory
            )

            self.metrics_history.append(metrics)
            return metrics

        except Exception as e:
            logger.error(f"Error capturing metrics: {e}")
            return None

    def _generate_performance_report(self, current_memory: int, peak_memory: int) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        logger.info("📊 Generating performance report")

        # Get profiling stats
        stats_io = io.StringIO()
        stats = pstats.Stats(self.profiler, stream=stats_io)
        stats.sort_stats('cumulative')
        stats.print_stats(50)  # Top 50 functions

        # Parse bottlenecks
        bottlenecks = self._parse_bottlenecks(stats)

        # Current metrics
        current_metrics = self.capture_metrics()

        # Generate report
        report = {
            'timestamp': datetime.now().isoformat(),
            'session_duration': time.time() - self.start_time,
            'memory_analysis': {
                'current_mb': current_memory / 1024 / 1024,
                'peak_mb': peak_memory / 1024 / 1024,
                'initial_mb': self.initial_memory,
                'growth_mb': (current_memory / 1024 / 1024) - self.initial_memory
            },
            'bottlenecks': [
                {
                    'function': b.function_name,
                    'total_time': b.total_time,
                    'calls': b.calls,
                    'time_per_call': b.time_per_call,
                    'percentage': b.percentage,
                    'file_location': b.file_location
                }
                for b in bottlenecks[:10]  # Top 10 bottlenecks
            ],
            'system_metrics': {
                'cpu_percent': current_metrics.cpu_percent if current_metrics else 0,
                'memory_mb': current_metrics.memory_mb if current_metrics else 0,
                'disk_usage_mb': current_metrics.disk_usage_mb if current_metrics else 0,
                'process_count': current_metrics.process_count if current_metrics else 0,
                'load_average': current_metrics.load_average if current_metrics else [0, 0, 0]
            },
            'profiling_stats': stats_io.getvalue(),
            'recommendations': self._generate_recommendations(bottlenecks, current_metrics)
        }

        # Save report
        self._save_report(report)

        return report

    def _parse_bottlenecks(self, stats: pstats.Stats) -> List[BottleneckReport]:
        """Parse profiling stats to identify bottlenecks."""
        bottlenecks = []

        # Get stats data
        stats_data = stats.get_stats_profile()
        total_time = stats_data.total_tt

        for func_key, (cc, nc, tt, ct, callers) in stats_data.stats.items():
            filename, line_no, func_name = func_key

            # Skip built-in functions
            if '<built-in>' in filename:
                continue

            # Calculate metrics
            time_per_call = tt / nc if nc > 0 else 0
            percentage = (tt / total_time) * 100 if total_time > 0 else 0

            bottleneck = BottleneckReport(
                function_name=func_name,
                total_time=tt,
                calls=nc,
                time_per_call=time_per_call,
                cumulative_time=ct,
                percentage=percentage,
                file_location=f"{filename}:{line_no}"
            )

            bottlenecks.append(bottleneck)

        # Sort by total time
        bottlenecks.sort(key=lambda x: x.total_time, reverse=True)

        return bottlenecks

    def _generate_recommendations(self, bottlenecks: List[BottleneckReport],
                                  metrics: PerformanceMetrics) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []

        # Memory recommendations
        if metrics and metrics.memory_mb > 500:
            recommendations.append(
                f"🔴 HIGH MEMORY USAGE: {metrics.memory_mb:.1f}MB - Consider memory optimization"
            )

        # CPU recommendations
        if metrics and metrics.cpu_percent > 80:
            recommendations.append(
                f"🔴 HIGH CPU USAGE: {metrics.cpu_percent:.1f}% - Consider CPU optimization"
            )

        # Bottleneck recommendations
        if bottlenecks:
            top_bottleneck = bottlenecks[0]
            if top_bottleneck.percentage > 20:
                recommendations.append(
                    f"🔴 MAJOR BOTTLENECK: {top_bottleneck.function_name} consuming "
                    f"{top_bottleneck.percentage:.1f}% of execution time"
                )

        # Function call recommendations
        high_call_functions = [b for b in bottlenecks if b.calls > 1000]
        if high_call_functions:
            recommendations.append(
                f"🟡 HIGH FREQUENCY CALLS: {len(high_call_functions)} functions "
                f"called >1000 times - Consider optimization"
            )

        # I/O recommendations
        if metrics and metrics.disk_usage_mb > 10000:  # 10GB
            recommendations.append(
                f"🟡 HIGH DISK USAGE: {metrics.disk_usage_mb:.1f}MB - Consider cleanup"
            )

        if not recommendations:
            recommendations.append("✅ No critical performance issues detected")

        return recommendations

    def _save_report(self, report: Dict[str, Any]):
        """Save performance report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"performance_report_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"📋 Performance report saved: {filename}")

    async def monitor_continuously(self, duration_minutes: int = 30):
        """Monitor performance continuously."""
        logger.info(f"🔄 Starting continuous monitoring for {duration_minutes} minutes")

        self.start_profiling()

        end_time = time.time() + (duration_minutes * 60)

        try:
            while time.time() < end_time:
                metrics = self.capture_metrics()
                if metrics:
                    logger.info(
                        f"📊 CPU: {metrics.cpu_percent:.1f}%, "
                        f"Memory: {metrics.memory_mb:.1f}MB, "
                        f"Processes: {metrics.process_count}"
                    )

                await asyncio.sleep(30)  # Capture every 30 seconds

        except KeyboardInterrupt:
            logger.info("🛑 Monitoring stopped by user")
        finally:
            report = self.stop_profiling()
            logger.info("✅ Continuous monitoring completed")
            return report

    def benchmark_cli_operations(self) -> Dict[str, float]:
        """Benchmark CLI operation performance."""
        logger.info("🏃 Benchmarking CLI operations")

        benchmarks = {}

        # Test CLI help command
        start_time = time.time()
        try:
            result = os.system("python cli.py --help > /dev/null 2>&1")
            benchmarks['cli_help'] = time.time() - start_time
        except Exception as e:
            benchmarks['cli_help'] = -1
            logger.warning(f"CLI help benchmark failed: {e}")

        # Test coordination status
        start_time = time.time()
        try:
            result = os.system("python cli.py coordinate --action status > /dev/null 2>&1")
            benchmarks['coordination_status'] = time.time() - start_time
        except Exception as e:
            benchmarks['coordination_status'] = -1
            logger.warning(f"Coordination status benchmark failed: {e}")

        # Test monitoring
        start_time = time.time()
        try:
            result = os.system("python cli.py monitor > /dev/null 2>&1")
            benchmarks['monitor'] = time.time() - start_time
        except Exception as e:
            benchmarks['monitor'] = -1
            logger.warning(f"Monitor benchmark failed: {e}")

        logger.info(f"📊 CLI benchmarks: {benchmarks}")
        return benchmarks

    def generate_optimization_report(self) -> str:
        """Generate optimization report and recommendations."""
        logger.info("📋 Generating optimization report")

        # Capture current metrics
        metrics = self.capture_metrics()

        # Run CLI benchmarks
        benchmarks = self.benchmark_cli_operations()

        # Generate report
        report = f"""
# LeanVibe Performance Optimization Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## System Metrics
- **CPU Usage**: {metrics.cpu_percent:.1f}%
- **Memory Usage**: {metrics.memory_mb:.1f} MB
- **Disk Usage**: {metrics.disk_usage_mb:.1f} MB
- **Process Count**: {metrics.process_count}
- **Load Average**: {metrics.load_average}

## CLI Performance Benchmarks
"""

        for operation, duration in benchmarks.items():
            status = "✅ FAST" if duration < 1.0 else "🟡 SLOW" if duration < 3.0 else "🔴 VERY SLOW"
            report += f"- **{operation}**: {duration:.3f}s {status}\n"

        report += f"""
## Optimization Recommendations

### Immediate Actions
1. **Memory Optimization**: Current usage {metrics.memory_mb:.1f}MB
   - Monitor for memory leaks
   - Optimize data structures
   - Implement garbage collection

2. **CPU Optimization**: Current usage {metrics.cpu_percent:.1f}%
   - Profile CPU-intensive operations
   - Implement async operations where possible
   - Optimize algorithms

### Performance Targets
- **CLI Response Time**: < 1.0s (Current: {benchmarks.get('cli_help', 0):.3f}s)
- **Memory Usage**: < 500MB (Current: {metrics.memory_mb:.1f}MB)
- **CPU Usage**: < 50% (Current: {metrics.cpu_percent:.1f}%)

### Next Steps
1. Run continuous monitoring: `python scripts/performance_profiler.py --monitor`
2. Analyze bottlenecks: `python scripts/performance_profiler.py --profile`
3. Optimize identified issues
4. Re-run benchmarks to verify improvements

---
*Generated by LeanVibe Performance Profiler - Phase 2*
"""

        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"optimization_report_{timestamp}.md"

        with open(filename, 'w') as f:
            f.write(report)

        logger.info(f"📋 Optimization report saved: {filename}")
        return report


async def main():
    """Main entry point for performance profiler."""
    import argparse

    parser = argparse.ArgumentParser(description="LeanVibe Performance Profiler")
    parser.add_argument("--monitor", action="store_true",
                        help="Run continuous monitoring")
    parser.add_argument("--profile", action="store_true",
                        help="Run profiling session")
    parser.add_argument("--benchmark", action="store_true",
                        help="Run CLI benchmarks")
    parser.add_argument("--report", action="store_true",
                        help="Generate optimization report")
    parser.add_argument("--duration", type=int, default=30,
                        help="Monitoring duration in minutes")

    args = parser.parse_args()

    profiler = PerformanceProfiler()

    if args.monitor:
        await profiler.monitor_continuously(args.duration)
    elif args.profile:
        profiler.start_profiling()
        # Simulate some work
        await asyncio.sleep(5)
        report = profiler.stop_profiling()
        print(json.dumps(report, indent=2, default=str))
    elif args.benchmark:
        benchmarks = profiler.benchmark_cli_operations()
        print(json.dumps(benchmarks, indent=2))
    elif args.report:
        report = profiler.generate_optimization_report()
        print(report)
    else:
        print("🚀 LeanVibe Performance Profiler - Phase 2")
        print("Usage: python scripts/performance_profiler.py [--monitor|--profile|--benchmark|--report]")
        print("  --monitor: Run continuous monitoring")
        print("  --profile: Run profiling session")
        print("  --benchmark: Run CLI benchmarks")
        print("  --report: Generate optimization report")


if __name__ == "__main__":
    asyncio.run(main())
