# .claude/dashboard/unified_view.py
class UnifiedDashboard:
    """Single pane of glass for all monitoring"""

    def __init__(self):
        self.alert_manager = SmartAlertManager()
        self.metric_aggregator = MetricAggregator()

    def get_status_line(self):
        """One-line status summary"""
        metrics = self.metric_aggregator.get_current()

        if metrics.all_healthy:
            return f"✅ All systems go | {metrics.velocity} features/week | {metrics.autonomy}% autonomous"
        else:
            return f"⚠️  {metrics.issue_count} issues | Next decision in {metrics.time_to_decision}"

    def get_smart_alerts(self):
        """Only show what needs attention"""
        all_alerts = self.alert_manager.get_all()

        # Filter based on learned patterns
        relevant = self.alert_manager.filter_by_relevance(all_alerts)

        # Group similar alerts
        grouped = self.alert_manager.group_similar(relevant)

        # Prioritize by impact
        return self.alert_manager.prioritize(grouped)
