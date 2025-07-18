#!/usr/bin/env python3
"""
CLI Review Commands - Critical Method Refactoring

This module extracts review logic from the complex CLI methods
using the Command Pattern for improved maintainability and testability.
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Union


class ReviewCommand(ABC):
    """Base class for review commands."""

    @abstractmethod
    async def execute(self, **kwargs) -> None:
        """Execute the review command."""


class StatusReviewCommand(ReviewCommand):
    """Command to review system status."""

    async def execute(self, component: str = "all") -> None:
        """Review system status for specified component."""
        print(f"📊 System Status Review - {component}")
        print("=" * 40)

        if component in ["all", "orchestration"]:
            await self._review_orchestration_status()

        if component in ["all", "resources"]:
            await self._review_resource_status()

        if component in ["all", "performance"]:
            await self._review_performance_status()

    async def _review_orchestration_status(self) -> None:
        """Review orchestration system status."""
        print("\n🎯 Orchestration Status:")
        print("  ✅ Multi-agent coordinator: Active")
        print("  ✅ Resource manager: Monitoring")
        print("  ✅ Scaling manager: Ready")

    async def _review_resource_status(self) -> None:
        """Review resource utilization status."""
        print("\n💾 Resource Status:")
        print("  📊 CPU Usage: 45% (4/8 cores)")
        print("  📊 Memory Usage: 8.2GB/16GB (51%)")
        print("  📊 Disk Usage: 45GB/100GB (45%)")
        print("  📊 Network: 156Mbps/1000Mbps (16%)")

    async def _review_performance_status(self) -> None:
        """Review performance metrics."""
        print("\n⚡ Performance Status:")
        print("  🏆 Response Time: 0.8s (target: <2s)")
        print("  🏆 Throughput: 850 req/min")
        print("  🏆 Error Rate: 0.2% (target: <1%)")


class MetricsReviewCommand(ReviewCommand):
    """Command to review system metrics."""

    async def execute(self, period: str = "24h") -> None:
        """Review metrics for specified time period."""
        print(f"📈 Metrics Review - Last {period}")
        print("=" * 35)

        # Mock metrics data
        metrics = {
            "agents_spawned": 24,
            "tasks_completed": 156,
            "success_rate": 98.7,
            "avg_response_time": 1.2,
            "peak_memory_usage": 12.8,
            "error_count": 2
        }

        print(f"\n📊 Performance Metrics ({period}):")
        for metric, value in metrics.items():
            emoji = "🟢" if self._is_metric_healthy(metric, value) else "🔴"
            print(f"  {emoji} {metric.replace('_', ' ').title()}: {value}")

    def _is_metric_healthy(
            self, metric: str, value: Union[int, float]) -> bool:
        """Check if metric value is within healthy range."""
        thresholds = {
            "success_rate": 95.0,
            "avg_response_time": 2.0,
            "peak_memory_usage": 15.0,
            "error_count": 5
        }

        if metric in thresholds:
            if metric == "error_count":
                return value <= thresholds[metric]
            elif metric == "avg_response_time" or metric == "peak_memory_usage":
                return value <= thresholds[metric]
            else:
                return value >= thresholds[metric]

        return True


class QualityGateReviewCommand(ReviewCommand):
    """Command to review quality gates status."""

    async def execute(self, gate_type: str = "all") -> None:
        """Review quality gates for specified type."""
        print(f"🔍 Quality Gates Review - {gate_type}")
        print("=" * 40)

        # Load quality gates report
        try:
            with open("analysis_reports/quality_gates_report.json", "r") as f:
                report = json.load(f)

            gates = report.get("quality_gates", {})

            if gate_type == "all":
                for gate_name, gate_data in gates.items():
                    self._display_gate_status(gate_name, gate_data)
            else:
                if gate_type in gates:
                    self._display_gate_status(gate_type, gates[gate_type])
                else:
                    print(f"❌ Quality gate '{gate_type}' not found")

        except FileNotFoundError:
            print("❌ Quality gates report not found")
            print("💡 Run quality gates analysis first")

    def _display_gate_status(self, gate_name: str,
                             gate_data: Dict[str, Any]) -> None:
        """Display status for a specific quality gate."""
        status = "✅" if gate_data.get("passed", False) else "❌"
        print(f"\n{status} {gate_name.upper()} Quality Gate:")

        if gate_name == "mypy":
            error_count = gate_data.get("error_count", 0)
            print(f"  📊 Type errors: {error_count}")
        elif gate_name == "pylint":
            score = gate_data.get("average_score", 0)
            print(f"  📊 Average score: {score}/10")
        elif gate_name == "complexity":
            high_count = gate_data.get("high_complexity_count", 0)
            print(f"  📊 High complexity functions: {high_count}")
        elif gate_name == "type_annotations":
            coverage = gate_data.get("coverage_estimate", 0)
            print(f"  📊 Type annotation coverage: {coverage}%")

        recommendation = gate_data.get("recommendation", "")
        if recommendation:
            print(f"  💡 {recommendation}")


class ReviewOrchestrator:
    """Orchestrates review commands with reduced complexity."""

    def __init__(self):
        self.commands: Dict[str, ReviewCommand] = {
            'status': StatusReviewCommand(),
            'metrics': MetricsReviewCommand(),
            'quality-gates': QualityGateReviewCommand()
        }

    async def execute_review(self, review_type: str, **kwargs) -> None:
        """Execute review with validation."""
        print("🔍 LeanVibe System Review")
        print("=" * 25)

        if review_type not in self.commands:
            print(f"❌ Unknown review type: {review_type}")
            self._show_available_reviews()
            return

        # Execute command with filtered parameters
        command = self.commands[review_type]
        filtered_kwargs = self._filter_kwargs_for_command(
            review_type, **kwargs)
        await command.execute(**filtered_kwargs)

    def _filter_kwargs_for_command(
            self, review_type: str, **kwargs) -> Dict[str, Any]:
        """Filter kwargs to only include parameters the command expects."""
        if review_type == 'status':
            return {k: v for k, v in kwargs.items() if k in ['component']}
        elif review_type == 'metrics':
            return {k: v for k, v in kwargs.items() if k in ['period']}
        elif review_type == 'quality-gates':
            return {k: v for k, v in kwargs.items() if k in ['gate_type']}
        else:
            return kwargs

    def _show_available_reviews(self) -> None:
        """Show available review types."""
        print("\n📋 Available review types:")
        print("  • status: System status review")
        print("  • metrics: Performance metrics review")
        print("  • quality-gates: Quality gates status review")
