#!/usr/bin/env python3
"""
BACKLOG.md Analytics and Reporting System

Provides comprehensive analytics and reporting capabilities for BACKLOG.md:
- Velocity tracking and trends
- Sprint retrospective analytics
- Priority change analysis
- Completion time analysis
- Performance metrics and insights

This complements the existing BACKLOG.md workflow with data-driven insights.
"""

import sqlite3
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import argparse


class BacklogAnalytics:
    """Comprehensive analytics for BACKLOG.md database."""
    
    def __init__(self, repo_path: str = ".", db_path: Optional[str] = None):
        self.repo_path = Path(repo_path)
        self.db_path = Path(db_path) if db_path else self.repo_path / "database" / "backlog_analytics.db"
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
    
    def get_current_sprint_status(self) -> Dict:
        """Get real-time sprint progress by priority."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM current_sprint_status")
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return {
                'sprint_status': results,
                'generated_at': datetime.now().isoformat()
            }
    
    def get_velocity_trend(self, days: int = 30) -> Dict:
        """Get velocity trend analysis over specified days."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get historical velocity data
            cursor.execute("""
                SELECT * FROM velocity_trend 
                WHERE sprint_date >= date('now', '-{} days')
                ORDER BY sprint_date DESC
            """.format(days))
            
            columns = [desc[0] for desc in cursor.description]
            velocity_data = []
            for row in cursor.fetchall():
                velocity_data.append(dict(zip(columns, row)))
            
            # Calculate summary statistics
            if velocity_data:
                completion_rates = [d['completion_rate'] for d in velocity_data if d['completion_rate'] is not None]
                avg_completion_rate = sum(completion_rates) / len(completion_rates) if completion_rates else 0
                
                velocity_scores = [d['velocity_score'] for d in velocity_data if d['velocity_score'] is not None]
                avg_velocity_score = sum(velocity_scores) / len(velocity_scores) if velocity_scores else 0
            else:
                avg_completion_rate = 0
                avg_velocity_score = 0
            
            return {
                'velocity_trend': velocity_data,
                'summary': {
                    'average_completion_rate': round(avg_completion_rate, 2),
                    'average_velocity_score': round(avg_velocity_score, 2),
                    'data_points': len(velocity_data),
                    'period_days': days
                },
                'generated_at': datetime.now().isoformat()
            }
    
    def get_priority_change_analysis(self) -> Dict:
        """Analyze how often and why priorities change."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM priority_change_analysis ORDER BY priority_changes DESC")
            
            columns = [desc[0] for desc in cursor.description]
            priority_changes = []
            for row in cursor.fetchall():
                priority_changes.append(dict(zip(columns, row)))
            
            # Calculate statistics
            total_items_with_changes = len(priority_changes)
            if priority_changes:
                avg_changes_per_item = sum(item['priority_changes'] for item in priority_changes) / total_items_with_changes
                max_changes = max(item['priority_changes'] for item in priority_changes)
            else:
                avg_changes_per_item = 0
                max_changes = 0
            
            return {
                'priority_changes': priority_changes,
                'summary': {
                    'items_with_priority_changes': total_items_with_changes,
                    'average_changes_per_item': round(avg_changes_per_item, 2),
                    'max_changes_single_item': max_changes
                },
                'generated_at': datetime.now().isoformat()
            }
    
    def get_completion_time_analysis(self) -> Dict:
        """Analyze item completion times vs estimates."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM completion_time_analysis ORDER BY completed_date DESC")
            
            columns = [desc[0] for desc in cursor.description]
            completion_data = []
            for row in cursor.fetchall():
                completion_data.append(dict(zip(columns, row)))
            
            # Calculate accuracy statistics
            accurate_estimates = []
            for item in completion_data:
                if item['estimate_accuracy_ratio'] is not None:
                    accurate_estimates.append(item['estimate_accuracy_ratio'])
            
            if accurate_estimates:
                avg_accuracy = sum(accurate_estimates) / len(accurate_estimates)
                # Count estimates within 20% of actual time
                good_estimates = sum(1 for ratio in accurate_estimates if 0.8 <= ratio <= 1.2)
                estimate_accuracy_rate = (good_estimates / len(accurate_estimates)) * 100
            else:
                avg_accuracy = 0
                estimate_accuracy_rate = 0
            
            return {
                'completion_analysis': completion_data,
                'summary': {
                    'total_completed_items': len(completion_data),
                    'items_with_estimates': len(accurate_estimates),
                    'average_accuracy_ratio': round(avg_accuracy, 2),
                    'good_estimate_rate': round(estimate_accuracy_rate, 2)
                },
                'generated_at': datetime.now().isoformat()
            }
    
    def get_workload_distribution(self) -> Dict:
        """Analyze workload distribution across priorities and sections."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # By priority
            cursor.execute("""
                SELECT priority, status, COUNT(*) as count,
                       ROUND(SUM(COALESCE(estimate_hours, 0)), 2) as total_hours
                FROM backlog_items 
                GROUP BY priority, status
                ORDER BY priority, status
            """)
            
            priority_distribution = []
            for row in cursor.fetchall():
                priority_distribution.append({
                    'priority': row[0],
                    'status': row[1],
                    'count': row[2],
                    'total_hours': row[3]
                })
            
            # By section
            cursor.execute("""
                SELECT section, COUNT(*) as count,
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                       ROUND(SUM(COALESCE(estimate_hours, 0)), 2) as total_hours
                FROM backlog_items 
                GROUP BY section
                ORDER BY count DESC
            """)
            
            section_distribution = []
            for row in cursor.fetchall():
                completion_rate = (row[2] / row[1] * 100) if row[1] > 0 else 0
                section_distribution.append({
                    'section': row[0],
                    'total_items': row[1],
                    'completed_items': row[2],
                    'completion_rate': round(completion_rate, 2),
                    'total_hours': row[3]
                })
            
            return {
                'priority_distribution': priority_distribution,
                'section_distribution': section_distribution,
                'generated_at': datetime.now().isoformat()
            }
    
    def get_recent_activity(self, days: int = 7) -> Dict:
        """Get recent activity and changes."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Recent changes
            cursor.execute("""
                SELECT h.change_date, h.change_type, h.old_value, h.new_value,
                       b.title, b.priority
                FROM item_history h
                JOIN backlog_items b ON h.item_id = b.id
                WHERE h.change_date >= datetime('now', '-{} days')
                ORDER BY h.change_date DESC
                LIMIT 50
            """.format(days))
            
            recent_changes = []
            for row in cursor.fetchall():
                recent_changes.append({
                    'change_date': row[0],
                    'change_type': row[1],
                    'old_value': row[2],
                    'new_value': row[3],
                    'item_title': row[4],
                    'item_priority': row[5]
                })
            
            # Recent sync operations
            cursor.execute("""
                SELECT sync_date, items_processed, items_created, items_updated, 
                       items_completed, processing_time_ms
                FROM sync_log
                WHERE sync_date >= datetime('now', '-{} days')
                ORDER BY sync_date DESC
                LIMIT 10
            """.format(days))
            
            recent_syncs = []
            for row in cursor.fetchall():
                recent_syncs.append({
                    'sync_date': row[0],
                    'items_processed': row[1],
                    'items_created': row[2],
                    'items_updated': row[3],
                    'items_completed': row[4],
                    'processing_time_ms': row[5]
                })
            
            return {
                'recent_changes': recent_changes,
                'recent_syncs': recent_syncs,
                'period_days': days,
                'generated_at': datetime.now().isoformat()
            }
    
    def generate_comprehensive_report(self, output_format: str = 'json') -> str:
        """Generate comprehensive analytics report."""
        report_data = {
            'report_metadata': {
                'generated_at': datetime.now().isoformat(),
                'database_path': str(self.db_path),
                'report_type': 'comprehensive_backlog_analytics'
            },
            'current_sprint_status': self.get_current_sprint_status(),
            'velocity_trend': self.get_velocity_trend(30),
            'priority_change_analysis': self.get_priority_change_analysis(),
            'completion_time_analysis': self.get_completion_time_analysis(),
            'workload_distribution': self.get_workload_distribution(),
            'recent_activity': self.get_recent_activity(14)
        }
        
        if output_format == 'json':
            return json.dumps(report_data, indent=2)
        
        elif output_format == 'markdown':
            return self._format_markdown_report(report_data)
        
        elif output_format == 'csv':
            # Generate CSV for current sprint status
            return self._format_csv_report(report_data)
        
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _format_markdown_report(self, data: Dict) -> str:
        """Format comprehensive report as Markdown."""
        md = f"""# BACKLOG.md Analytics Report

**Generated**: {data['report_metadata']['generated_at']}  
**Database**: {data['report_metadata']['database_path']}

## 📊 Current Sprint Status

| Priority | Total Items | Completed | Completion % | Total Hours | Completed Hours |
|----------|-------------|-----------|--------------|-------------|-----------------|
"""
        
        for item in data['current_sprint_status']['sprint_status']:
            md += f"| {item['priority']} | {item['total_items']} | {item['completed_items']} | {item['completion_percentage']}% | {item['total_hours']} | {item['completed_hours']} |\n"
        
        md += f"""
## 📈 Velocity Trends (30 days)

**Average Completion Rate**: {data['velocity_trend']['summary']['average_completion_rate']}%  
**Average Velocity Score**: {data['velocity_trend']['summary']['average_velocity_score']}  
**Data Points**: {data['velocity_trend']['summary']['data_points']}

## 🔄 Priority Changes Analysis

**Items with Priority Changes**: {data['priority_change_analysis']['summary']['items_with_priority_changes']}  
**Average Changes per Item**: {data['priority_change_analysis']['summary']['average_changes_per_item']}  
**Max Changes (Single Item)**: {data['priority_change_analysis']['summary']['max_changes_single_item']}

## ⏱️ Completion Time Analysis

**Total Completed Items**: {data['completion_time_analysis']['summary']['total_completed_items']}  
**Items with Estimates**: {data['completion_time_analysis']['summary']['items_with_estimates']}  
**Estimate Accuracy Rate**: {data['completion_time_analysis']['summary']['good_estimate_rate']}%

## 📋 Workload Distribution

### By Section
"""
        
        for section in data['workload_distribution']['section_distribution'][:10]:
            md += f"- **{section['section']}**: {section['total_items']} items ({section['completion_rate']}% complete, {section['total_hours']} hours)\n"
        
        md += f"""
## 🔄 Recent Activity (14 days)

**Recent Changes**: {len(data['recent_activity']['recent_changes'])}  
**Recent Syncs**: {len(data['recent_activity']['recent_syncs'])}

### Latest Changes
"""
        
        for change in data['recent_activity']['recent_changes'][:10]:
            md += f"- **{change['change_date']}**: {change['item_title']} - {change['change_type']} ({change['old_value']} → {change['new_value']})\n"
        
        return md
    
    def _format_csv_report(self, data: Dict) -> str:
        """Format sprint status as CSV."""
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['Priority', 'Total Items', 'Completed Items', 'Completion %', 'Total Hours', 'Completed Hours'])
        
        # Write data
        for item in data['current_sprint_status']['sprint_status']:
            writer.writerow([
                item['priority'],
                item['total_items'],
                item['completed_items'],
                item['completion_percentage'],
                item['total_hours'],
                item['completed_hours']
            ])
        
        return output.getvalue()
    
    def export_data(self, table: str, output_path: str, format: str = 'csv') -> None:
        """Export database table to file."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table}")
            
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            output_file = Path(output_path)
            
            if format == 'csv':
                import csv
                with open(output_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(columns)
                    writer.writerows(rows)
            
            elif format == 'json':
                data = []
                for row in rows:
                    data.append(dict(zip(columns, row)))
                
                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=2)
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
        
        print(f"✅ Exported {table} to {output_file} ({format})")


def main():
    """CLI entry point for analytics and reporting."""
    parser = argparse.ArgumentParser(description="BACKLOG.md Analytics and Reporting")
    parser.add_argument('--action', choices=[
        'status', 'velocity', 'priority-changes', 'completion-times',
        'workload', 'activity', 'report', 'export'
    ], default='status', help='Analytics action to perform')
    parser.add_argument('--format', choices=['json', 'markdown', 'csv'], 
                       default='json', help='Output format')
    parser.add_argument('--days', type=int, default=30,
                       help='Number of days for trend analysis')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--table', help='Database table to export')
    parser.add_argument('--repo-path', default='.', 
                       help='Path to repository root')
    parser.add_argument('--db-path', 
                       help='Custom database path')
    
    args = parser.parse_args()
    
    try:
        analytics = BacklogAnalytics(args.repo_path, args.db_path)
        
        if args.action == 'status':
            result = analytics.get_current_sprint_status()
            output = json.dumps(result, indent=2) if args.format == 'json' else str(result)
            
        elif args.action == 'velocity':
            result = analytics.get_velocity_trend(args.days)
            output = json.dumps(result, indent=2) if args.format == 'json' else str(result)
            
        elif args.action == 'priority-changes':
            result = analytics.get_priority_change_analysis()
            output = json.dumps(result, indent=2) if args.format == 'json' else str(result)
            
        elif args.action == 'completion-times':
            result = analytics.get_completion_time_analysis()
            output = json.dumps(result, indent=2) if args.format == 'json' else str(result)
            
        elif args.action == 'workload':
            result = analytics.get_workload_distribution()
            output = json.dumps(result, indent=2) if args.format == 'json' else str(result)
            
        elif args.action == 'activity':
            result = analytics.get_recent_activity(args.days)
            output = json.dumps(result, indent=2) if args.format == 'json' else str(result)
            
        elif args.action == 'report':
            output = analytics.generate_comprehensive_report(args.format)
            
        elif args.action == 'export':
            if not args.table or not args.output:
                print("❌ Export requires --table and --output arguments")
                return 1
            analytics.export_data(args.table, args.output, args.format)
            return 0
        
        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"✅ Report saved to {args.output}")
        else:
            print(output)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())