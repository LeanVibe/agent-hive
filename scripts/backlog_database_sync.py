#!/usr/bin/env python3
"""
BACKLOG.md Database Integration and Analytics System

This system complements the existing BACKLOG.md workflow by providing:
- Analytics database for velocity tracking and trend analysis
- Historical change tracking for all backlog items
- Sprint metrics and retrospective data
- Optional sync system (BACKLOG.md remains single source of truth)

The database serves as an analytics layer only - BACKLOG.md workflow is unchanged.
"""

import re
import sqlite3
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import argparse


class BacklogDatabaseSync:
    """Manages database sync and analytics for BACKLOG.md."""
    
    def __init__(self, repo_path: str = ".", db_path: Optional[str] = None):
        self.repo_path = Path(repo_path)
        self.backlog_path = self.repo_path / "BACKLOG.md"
        self.db_path = Path(db_path) if db_path else self.repo_path / "database" / "backlog_analytics.db"
        self.batch_id = str(uuid.uuid4())
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database with schema if it doesn't exist."""
        schema_path = self.repo_path / "database" / "schema.sql"
        
        if not schema_path.exists():
            print(f"❌ Database schema not found at {schema_path}")
            return
        
        with sqlite3.connect(self.db_path) as conn:
            with open(schema_path, 'r') as f:
                conn.executescript(f.read())
            conn.commit()
    
    def _parse_estimate(self, estimate_str: str) -> Optional[float]:
        """Parse estimate string to hours (e.g., '2hr' -> 2.0, '30min' -> 0.5)."""
        if not estimate_str:
            return None
        
        # Handle different estimate formats
        estimate_str = estimate_str.lower().strip()
        
        # Match patterns like "2hr", "30min", "1.5hr", "45 min"
        if 'hr' in estimate_str or 'hour' in estimate_str:
            match = re.search(r'(\d+\.?\d*)', estimate_str)
            if match:
                return float(match.group(1))
        elif 'min' in estimate_str:
            match = re.search(r'(\d+)', estimate_str)
            if match:
                return float(match.group(1)) / 60.0  # Convert minutes to hours
        
        return None
    
    def _get_file_hash(self) -> str:
        """Get hash of BACKLOG.md for change detection."""
        if not self.backlog_path.exists():
            return ""
        
        with open(self.backlog_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def parse_backlog_items(self) -> List[Dict]:
        """Enhanced parser that extracts all metadata from BACKLOG.md."""
        if not self.backlog_path.exists():
            print(f"❌ BACKLOG.md not found at {self.backlog_path}")
            return []
        
        with open(self.backlog_path, 'r') as f:
            content = f.read()
        
        items = []
        current_priority = None
        current_section = None
        
        # Enhanced patterns for parsing
        priority_pattern = r'^## 🔥 (P\d+).*$|^## 🚀 (P\d+).*$|^## 📊 (P\d+).*$|^## 🎯 (P\d+).*$'
        section_pattern = r'^### (.+)$'
        completed_task_pattern = r'^- \[x\] \*\*(.*?)\*\* - (.*?) \(Est: (.*?)\)(.*?)✅'
        pending_task_pattern = r'^- \[ \] \*\*(.*?)\*\* - (.*?) \(Est: (.*?)\)'
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Check for priority section
            priority_match = re.match(priority_pattern, line)
            if priority_match:
                # Extract priority from any of the capture groups
                current_priority = next(group for group in priority_match.groups() if group is not None)
                current_section = None  # Reset section when priority changes
                continue
            
            # Check for section
            section_match = re.match(section_pattern, line)
            if section_match and current_priority:
                current_section = section_match.group(1).strip()
                continue
            
            # Check for completed tasks
            completed_match = re.match(completed_task_pattern, line)
            if completed_match and current_priority:
                title = completed_match.group(1).strip()
                description = completed_match.group(2).strip()
                estimate = completed_match.group(3).strip()
                completion_info = completed_match.group(4).strip() if len(completed_match.groups()) > 3 else ""
                
                # Extract GitHub issue reference
                github_issue = None
                github_match = re.search(r'\(GitHub #(\d+)\)', line)
                if github_match:
                    github_issue = int(github_match.group(1))
                
                # Parse estimate to hours
                estimate_hours = self._parse_estimate(estimate)
                
                items.append({
                    'title': title,
                    'description': description,
                    'estimate': estimate,
                    'estimate_hours': estimate_hours,
                    'priority': current_priority,
                    'status': 'completed',
                    'github_issue': github_issue,
                    'section': current_section or 'General',
                    'raw_line': line,
                    'line_number': line_num,
                    'completion_info': completion_info
                })
                continue
            
            # Check for pending tasks
            pending_match = re.match(pending_task_pattern, line)
            if pending_match and current_priority:
                title = pending_match.group(1).strip()
                description = pending_match.group(2).strip()
                estimate = pending_match.group(3).strip()
                
                # Extract GitHub issue reference
                github_issue = None
                github_match = re.search(r'\(GitHub #(\d+)\)', line)
                if github_match:
                    github_issue = int(github_match.group(1))
                
                # Parse estimate to hours
                estimate_hours = self._parse_estimate(estimate)
                
                items.append({
                    'title': title,
                    'description': description,
                    'estimate': estimate,
                    'estimate_hours': estimate_hours,
                    'priority': current_priority,
                    'status': 'pending',
                    'github_issue': github_issue,
                    'section': current_section or 'General',
                    'raw_line': line,
                    'line_number': line_num,
                    'completion_info': ''
                })
        
        return items
    
    def sync_to_database(self, dry_run: bool = True) -> Dict:
        """Sync BACKLOG.md items to database and track changes."""
        start_time = datetime.now()
        print(f"🔄 Syncing BACKLOG.md to database (dry_run={dry_run})")
        
        # Check if file has changed
        current_hash = self._get_file_hash()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get last sync hash
            cursor.execute("""
                SELECT backlog_md_hash FROM sync_log 
                ORDER BY sync_date DESC LIMIT 1
            """)
            last_hash_row = cursor.fetchone()
            last_hash = last_hash_row[0] if last_hash_row else None
            
            if current_hash == last_hash and not dry_run:
                print("📄 No changes detected in BACKLOG.md, skipping sync")
                return {'status': 'no_changes', 'items_processed': 0}
        
        # Parse current backlog items
        current_items = self.parse_backlog_items()
        
        stats = {
            'items_processed': len(current_items),
            'items_created': 0,
            'items_updated': 0,
            'items_completed': 0,
            'errors': []
        }
        
        if dry_run:
            print(f"📋 WOULD process {len(current_items)} items")
            for item in current_items:
                print(f"  - {item['status'].upper()}: {item['title']} ({item['priority']})")
            return stats
        
        # Actual database sync
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            
            for item in current_items:
                try:
                    # Check if item exists
                    cursor.execute("""
                        SELECT id, status, priority, description, estimate_hours, completed_date 
                        FROM backlog_items 
                        WHERE title = ? AND priority = ? AND section = ?
                    """, (item['title'], item['priority'], item['section']))
                    
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Update existing item
                        item_id, old_status, old_priority, old_description, old_estimate_hours, old_completed_date = existing
                        
                        # Track changes
                        changes = []
                        if old_status != item['status']:
                            changes.append(('status_changed', old_status, item['status']))
                            if item['status'] == 'completed' and not old_completed_date:
                                stats['items_completed'] += 1
                        
                        if old_description != item['description']:
                            changes.append(('description_changed', old_description, item['description']))
                        
                        if old_estimate_hours != item['estimate_hours']:
                            changes.append(('estimate_changed', str(old_estimate_hours), str(item['estimate_hours'])))
                        
                        # Update item
                        cursor.execute("""
                            UPDATE backlog_items SET
                                description = ?, estimate = ?, estimate_hours = ?,
                                status = ?, github_issue = ?, last_updated = ?,
                                raw_line = ?, completed_date = ?
                            WHERE id = ?
                        """, (
                            item['description'], item['estimate'], item['estimate_hours'],
                            item['status'], item['github_issue'], now,
                            item['raw_line'],
                            now if item['status'] == 'completed' and not old_completed_date else old_completed_date,
                            item_id
                        ))
                        
                        # Record changes in history
                        for change_type, old_value, new_value in changes:
                            cursor.execute("""
                                INSERT INTO item_history 
                                (item_id, change_date, change_type, old_value, new_value, sync_batch_id)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (item_id, now, change_type, old_value, new_value, self.batch_id))
                        
                        if changes:
                            stats['items_updated'] += 1
                    
                    else:
                        # Create new item
                        cursor.execute("""
                            INSERT INTO backlog_items 
                            (title, description, priority, status, estimate, estimate_hours,
                             github_issue, created_date, completed_date, last_updated, 
                             raw_line, section)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            item['title'], item['description'], item['priority'], 
                            item['status'], item['estimate'], item['estimate_hours'],
                            item['github_issue'], now,
                            now if item['status'] == 'completed' else None,
                            now, item['raw_line'], item['section']
                        ))
                        
                        item_id = cursor.lastrowid
                        
                        # Record creation in history
                        cursor.execute("""
                            INSERT INTO item_history 
                            (item_id, change_date, change_type, old_value, new_value, sync_batch_id)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (item_id, now, 'created', None, item['status'], self.batch_id))
                        
                        stats['items_created'] += 1
                        if item['status'] == 'completed':
                            stats['items_completed'] += 1
                
                except Exception as e:
                    error_msg = f"Error processing item '{item['title']}': {e}"
                    print(f"❌ {error_msg}")
                    stats['errors'].append(error_msg)
            
            # Record sync operation
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            cursor.execute("""
                INSERT INTO sync_log 
                (sync_date, batch_id, items_processed, items_created, items_updated, 
                 items_completed, errors, processing_time_ms, backlog_md_hash, source_file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now, self.batch_id, stats['items_processed'], stats['items_created'],
                stats['items_updated'], stats['items_completed'], 
                json.dumps(stats['errors']), processing_time, current_hash, str(self.backlog_path)
            ))
            
            conn.commit()
        
        print(f"✅ Sync complete: {stats['items_processed']} processed, {stats['items_created']} created, {stats['items_updated']} updated")
        return stats
    
    def update_sprint_metrics(self, sprint_date: Optional[str] = None) -> None:
        """Update aggregated sprint metrics."""
        if not sprint_date:
            sprint_date = datetime.now().strftime('%Y-%m-%d')
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Calculate current metrics
            cursor.execute("""
                SELECT 
                    priority,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN estimate_hours IS NOT NULL THEN estimate_hours ELSE 0 END) as total_hours,
                    SUM(CASE WHEN status = 'completed' AND estimate_hours IS NOT NULL THEN estimate_hours ELSE 0 END) as completed_hours
                FROM backlog_items 
                GROUP BY priority
            """)
            
            priority_data = {row[0]: row[1:] for row in cursor.fetchall()}
            
            # Calculate totals and velocity score
            total_items = sum(data[0] for data in priority_data.values())
            completed_items = sum(data[1] for data in priority_data.values())
            total_hours = sum(data[2] for data in priority_data.values())
            completed_hours = sum(data[3] for data in priority_data.values())
            
            # Calculate velocity score (weighted by priority)
            priority_weights = {'P0': 4, 'P1': 3, 'P2': 2, 'P3': 1}
            velocity_score = 0
            total_weight = 0
            
            for priority, (total, completed, _, _) in priority_data.items():
                weight = priority_weights.get(priority, 1)
                velocity_score += (completed / max(total, 1)) * weight * total
                total_weight += weight * total
            
            velocity_score = velocity_score / max(total_weight, 1) if total_weight > 0 else 0
            
            # Upsert sprint metrics
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
                INSERT OR REPLACE INTO sprint_metrics 
                (sprint_date, total_items, completed_items,
                 p0_items, p1_items, p2_items, p3_items,
                 p0_completed, p1_completed, p2_completed, p3_completed,
                 total_estimate_hours, completed_estimate_hours, velocity_score, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sprint_date, total_items, completed_items,
                priority_data.get('P0', (0,))[0], priority_data.get('P1', (0,))[0], 
                priority_data.get('P2', (0,))[0], priority_data.get('P3', (0,))[0],
                priority_data.get('P0', (0, 0))[1], priority_data.get('P1', (0, 0))[1],
                priority_data.get('P2', (0, 0))[1], priority_data.get('P3', (0, 0))[1],
                total_hours, completed_hours, velocity_score, now
            ))
            
            conn.commit()
        
        print(f"📊 Sprint metrics updated for {sprint_date}")


def main():
    """CLI entry point for database sync and analytics."""
    parser = argparse.ArgumentParser(description="BACKLOG.md Database Integration and Analytics")
    parser.add_argument('--action', choices=['sync', 'metrics', 'status'], 
                       default='sync', help='Action to perform')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without executing')
    parser.add_argument('--repo-path', default='.', 
                       help='Path to repository root')
    parser.add_argument('--db-path', 
                       help='Custom database path (default: {repo}/database/backlog_analytics.db)')
    parser.add_argument('--sprint-date', 
                       help='Sprint date for metrics (YYYY-MM-DD, default: today)')
    
    args = parser.parse_args()
    
    try:
        sync_manager = BacklogDatabaseSync(args.repo_path, args.db_path)
        
        if args.action == 'sync':
            stats = sync_manager.sync_to_database(dry_run=args.dry_run)
            if not args.dry_run:
                sync_manager.update_sprint_metrics(args.sprint_date)
            
        elif args.action == 'metrics':
            sync_manager.update_sprint_metrics(args.sprint_date)
            
        elif args.action == 'status':
            # Show current database status
            with sqlite3.connect(sync_manager.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM backlog_items")
                total_items = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM backlog_items WHERE status = 'completed'")
                completed_items = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM sync_log")
                sync_count = cursor.fetchone()[0]
                
                print(f"📊 Database Status:")
                print(f"  Total Items: {total_items}")
                print(f"  Completed Items: {completed_items}")
                print(f"  Completion Rate: {100 * completed_items / max(total_items, 1):.1f}%")
                print(f"  Sync Operations: {sync_count}")
                print(f"  Database: {sync_manager.db_path}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())