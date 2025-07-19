#!/usr/bin/env python3
"""
Event Detector for Priority Changes and Completions

Monitors various sources for priority changes, completions, and sprint updates:
- BACKLOG.md file changes
- Git commit messages  
- Issue status changes
- Sprint milestone updates

Focus: Lightweight, file-based detection with git integration.
"""

import re
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json

from .slack_notifier import (
    PriorityChangeEvent, 
    CompletionEvent, 
    SprintEvent,
    SlackNotifier
)


@dataclass
class BacklogItem:
    """Represents a backlog item."""
    id: str
    title: str
    priority: str
    status: str
    assignee: Optional[str] = None
    context: Dict[str, Any] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}


class EventDetector:
    """
    Detects priority changes, completions, and sprint updates from various sources.
    
    Provides integration with BACKLOG.md files, git commits, and manual triggers.
    """

    def __init__(self, slack_notifier: SlackNotifier, 
                 backlog_path: Optional[str] = None):
        """
        Initialize event detector.
        
        Args:
            slack_notifier: Slack notifier instance
            backlog_path: Path to BACKLOG.md file (optional)
        """
        self.slack_notifier = slack_notifier
        self.backlog_path = backlog_path or self._find_backlog_file()
        self.logger = logging.getLogger(__name__)
        
        # Cache for tracking changes
        self._last_backlog_items: Dict[str, BacklogItem] = {}
        self._last_backlog_hash: Optional[str] = None
        
        # Pattern matchers
        self.priority_pattern = re.compile(r'\b(P[0-3])\b')
        self.status_pattern = re.compile(r'\[(TODO|IN_PROGRESS|DONE|BLOCKED)\]', re.IGNORECASE)
        self.item_id_pattern = re.compile(r'#(\d+)')

    def _find_backlog_file(self) -> Optional[str]:
        """Find BACKLOG.md file in project."""
        search_paths = [
            Path.cwd() / "BACKLOG.md",
            Path.cwd() / "docs" / "BACKLOG.md",
            Path.cwd() / "planning" / "BACKLOG.md",
            Path.cwd().parent / "BACKLOG.md"
        ]
        
        for path in search_paths:
            if path.exists():
                self.logger.info(f"Found BACKLOG.md at {path}")
                return str(path)
                
        self.logger.warning("No BACKLOG.md file found")
        return None

    async def check_for_changes(self) -> List[Any]:
        """
        Check for any changes that should trigger notifications.
        
        Returns:
            List: Events that were detected and notified
        """
        events = []
        
        try:
            # Check BACKLOG.md for changes
            if self.backlog_path:
                backlog_events = await self._check_backlog_changes()
                events.extend(backlog_events)
                
            # Check git commits for completion indicators
            git_events = await self._check_git_commits()
            events.extend(git_events)
            
            # Check for sprint milestone updates
            sprint_events = await self._check_sprint_updates()
            events.extend(sprint_events)
            
            self.logger.info(f"Detected {len(events)} events for notification")
            return events
            
        except Exception as e:
            self.logger.error(f"Error checking for changes: {e}")
            return []

    async def _check_backlog_changes(self) -> List[Any]:
        """Check BACKLOG.md for priority and status changes."""
        events = []
        
        try:
            if not self.backlog_path or not Path(self.backlog_path).exists():
                return events
                
            # Parse current backlog
            current_items = self._parse_backlog_file(self.backlog_path)
            
            # Compare with previous state
            for item_id, current_item in current_items.items():
                if item_id in self._last_backlog_items:
                    previous_item = self._last_backlog_items[item_id]
                    
                    # Check for priority change
                    if current_item.priority != previous_item.priority:
                        event = PriorityChangeEvent(
                            item_id=item_id,
                            item_title=current_item.title,
                            old_priority=previous_item.priority,
                            new_priority=current_item.priority,
                            changed_by="backlog-sync",
                            timestamp=datetime.now(timezone.utc),
                            context={
                                "source": "BACKLOG.md",
                                "file_path": self.backlog_path
                            }
                        )
                        
                        # Send notification
                        success = await self.slack_notifier.notify_priority_change(event)
                        if success:
                            events.append(event)
                            
                    # Check for completion
                    if (previous_item.status.upper() != "DONE" and 
                        current_item.status.upper() == "DONE"):
                        event = CompletionEvent(
                            item_id=item_id,
                            item_title=current_item.title,
                            priority=current_item.priority,
                            completed_by=current_item.assignee or "unknown",
                            timestamp=datetime.now(timezone.utc),
                            context={
                                "source": "BACKLOG.md",
                                "file_path": self.backlog_path,
                                "previous_status": previous_item.status
                            }
                        )
                        
                        # Send notification
                        success = await self.slack_notifier.notify_completion(event)
                        if success:
                            events.append(event)
            
            # Update cache
            self._last_backlog_items = current_items
            
        except Exception as e:
            self.logger.error(f"Error checking backlog changes: {e}")
            
        return events

    async def _check_git_commits(self) -> List[Any]:
        """Check recent git commits for completion indicators."""
        events = []
        
        try:
            # Get recent commits (last 10)
            import subprocess
            import shutil
            
            git_path = shutil.which('git')
            if not git_path:
                return events
                
            result = subprocess.run([
                git_path, 'log', '--oneline', '-n', '10', '--grep=complete', '--grep=done', '--grep=finish'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                commits = result.stdout.strip().split('\n')
                
                for commit_line in commits:
                    # Parse commit for completion indicators
                    completion_event = self._parse_completion_commit(commit_line)
                    if completion_event:
                        # Send notification
                        success = await self.slack_notifier.notify_completion(completion_event)
                        if success:
                            events.append(completion_event)
                            
        except subprocess.TimeoutExpired:
            self.logger.warning("Git command timed out")
        except Exception as e:
            self.logger.warning(f"Error checking git commits: {e}")
            
        return events

    async def _check_sprint_updates(self) -> List[Any]:
        """Check for sprint milestone updates."""
        events = []
        
        try:
            # Calculate sprint progress from BACKLOG.md
            if self.backlog_path and Path(self.backlog_path).exists():
                progress_data = self._calculate_sprint_progress()
                
                if progress_data and progress_data["progress"] % 25 == 0:  # Milestone reached
                    event = SprintEvent(
                        milestone=f"{progress_data['progress']:.0f}% Complete",
                        progress=progress_data["progress"],
                        completed_items=progress_data["completed_items"],
                        timestamp=datetime.now(timezone.utc),
                        context={
                            "source": "BACKLOG.md",
                            "total_items": progress_data["total_items"],
                            "completed_count": progress_data["completed_count"]
                        }
                    )
                    
                    # Send notification
                    success = await self.slack_notifier.notify_sprint_update(event)
                    if success:
                        events.append(event)
                        
        except Exception as e:
            self.logger.error(f"Error checking sprint updates: {e}")
            
        return events

    async def manually_trigger_priority_change(self, item_id: str, item_title: str,
                                             old_priority: str, new_priority: str,
                                             changed_by: str = "manual") -> bool:
        """
        Manually trigger a priority change notification.
        
        Args:
            item_id: Item identifier
            item_title: Item title
            old_priority: Previous priority
            new_priority: New priority
            changed_by: Who made the change
            
        Returns:
            bool: True if notification sent successfully
        """
        event = PriorityChangeEvent(
            item_id=item_id,
            item_title=item_title,
            old_priority=old_priority,
            new_priority=new_priority,
            changed_by=changed_by,
            timestamp=datetime.now(timezone.utc),
            context={"source": "manual_trigger"}
        )
        
        return await self.slack_notifier.notify_priority_change(event)

    async def manually_trigger_completion(self, item_id: str, item_title: str,
                                        priority: str, completed_by: str = "manual") -> bool:
        """
        Manually trigger a completion notification.
        
        Args:
            item_id: Item identifier  
            item_title: Item title
            priority: Item priority
            completed_by: Who completed it
            
        Returns:
            bool: True if notification sent successfully
        """
        event = CompletionEvent(
            item_id=item_id,
            item_title=item_title,
            priority=priority,
            completed_by=completed_by,
            timestamp=datetime.now(timezone.utc),
            context={"source": "manual_trigger"}
        )
        
        return await self.slack_notifier.notify_completion(event)

    def _parse_backlog_file(self, file_path: str) -> Dict[str, BacklogItem]:
        """Parse BACKLOG.md file and extract items."""
        items = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse markdown format
            lines = content.split('\n')
            for line_num, line in enumerate(lines):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                # Look for item patterns: - [STATUS] PRIORITY: Title #ID
                item = self._parse_backlog_line(line, line_num)
                if item:
                    items[item.id] = item
                    
        except Exception as e:
            self.logger.error(f"Error parsing backlog file: {e}")
            
        return items

    def _parse_backlog_line(self, line: str, line_num: int) -> Optional[BacklogItem]:
        """Parse a single line from BACKLOG.md."""
        # Pattern: - [STATUS] PRIORITY: Title #ID (@assignee)
        match = re.match(
            r'-\s*\[([^\]]+)\]\s*(P[0-3]):\s*([^#@]+?)(?:\s*#(\d+))?(?:\s*@(\w+))?\s*$',
            line, re.IGNORECASE
        )
        
        if match:
            status, priority, title, item_id, assignee = match.groups()
            
            # Use line number as ID if not provided
            if not item_id:
                item_id = str(line_num)
                
            return BacklogItem(
                id=item_id,
                title=title.strip(),
                priority=priority.upper(),
                status=status.upper(),
                assignee=assignee,
                context={"line_number": line_num}
            )
            
        return None

    def _parse_completion_commit(self, commit_line: str) -> Optional[CompletionEvent]:
        """Parse git commit for completion indicators."""
        # Extract commit hash and message
        parts = commit_line.split(' ', 1)
        if len(parts) < 2:
            return None
            
        commit_hash = parts[0]
        message = parts[1]
        
        # Look for completion patterns
        completion_patterns = [
            r'complete[sd]?\s+(.+?)(?:\s+#(\d+))?',
            r'finish[ed]?\s+(.+?)(?:\s+#(\d+))?',
            r'done\s+(.+?)(?:\s+#(\d+))?',
            r'implement[ed]?\s+(.+?)(?:\s+#(\d+))?'
        ]
        
        for pattern in completion_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                item_id = match.group(2) or commit_hash[:8]
                
                # Extract priority from commit message or default to P2
                priority_match = self.priority_pattern.search(message)
                priority = priority_match.group(1) if priority_match else "P2"
                
                return CompletionEvent(
                    item_id=item_id,
                    item_title=title,
                    priority=priority,
                    completed_by="git-commit",
                    timestamp=datetime.now(timezone.utc),
                    context={
                        "source": "git_commit",
                        "commit_hash": commit_hash,
                        "commit_message": message
                    }
                )
                
        return None

    def _calculate_sprint_progress(self) -> Optional[Dict[str, Any]]:
        """Calculate current sprint progress from backlog."""
        if not self.backlog_path or not Path(self.backlog_path).exists():
            return None
            
        items = self._parse_backlog_file(self.backlog_path)
        if not items:
            return None
            
        total_items = len(items)
        completed_items = [item for item in items.values() if item.status.upper() == "DONE"]
        completed_count = len(completed_items)
        
        progress = (completed_count / total_items * 100) if total_items > 0 else 0
        
        return {
            "progress": progress,
            "total_items": total_items,
            "completed_count": completed_count,
            "completed_items": [item.title for item in completed_items[:5]]  # Limit to 5
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current detector status."""
        return {
            "backlog_path": self.backlog_path,
            "backlog_exists": self.backlog_path and Path(self.backlog_path).exists(),
            "cached_items": len(self._last_backlog_items),
            "last_check": datetime.now(timezone.utc).isoformat()
        }