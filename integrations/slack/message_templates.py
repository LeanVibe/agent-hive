#!/usr/bin/env python3
"""
Slack Message Templates for LeanVibe Agent Hive

Professional, clear, and actionable message formatting for different notification types.
Focus: Consistent branding, clear information hierarchy, immediate understanding.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum

# Import types to avoid circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .slack_notifier import (
        PriorityChangeEvent, 
        CompletionEvent, 
        SprintEvent
    )


class NotificationPriority(Enum):
    """Notification priority levels for Slack messages."""
    URGENT = "urgent"          # P0 changes, critical blockers
    HIGH = "high"             # P1 changes, completions
    MEDIUM = "medium"         # P2 changes, sprint updates
    LOW = "low"               # General updates


class MessageType(Enum):
    """Types of Slack messages."""
    PRIORITY_CHANGE = "priority_change"
    COMPLETION = "completion"
    SPRINT_UPDATE = "sprint_update"
    CUSTOM = "custom"


class SlackMessageTemplate:
    """
    Template generator for Slack messages.
    
    Provides consistent, professional formatting for all notification types.
    """

    def __init__(self):
        """Initialize message template generator."""
        self.brand_name = "LeanVibe Agent Hive"
        self.brand_emoji = "🎯"
        
        # Color scheme for different priorities
        self.priority_colors = {
            NotificationPriority.URGENT: "#FF0000",    # Red
            NotificationPriority.HIGH: "#FF8C00",      # Orange
            NotificationPriority.MEDIUM: "#1E90FF",    # Blue
            NotificationPriority.LOW: "#32CD32"        # Green
        }
        
        # Emoji mapping for priorities
        self.priority_emojis = {
            NotificationPriority.URGENT: "🚨",
            NotificationPriority.HIGH: "⚠️",
            NotificationPriority.MEDIUM: "📋",
            NotificationPriority.LOW: "ℹ️"
        }

    def create_priority_change_message(self, event: Any, 
                                     notification_priority: NotificationPriority) -> Dict[str, Any]:
        """
        Create Slack message for priority change.
        
        Args:
            event: Priority change event data
            notification_priority: Notification priority level
            
        Returns:
            Dict: Slack message payload
        """
        priority_emoji = self.priority_emojis[notification_priority]
        color = self.priority_colors[notification_priority]
        
        # Determine change direction
        change_emoji = self._get_priority_change_emoji(event.old_priority, event.new_priority)
        
        # Create main text
        main_text = f"{priority_emoji} **Priority Change Alert**"
        
        # Create attachment with details
        attachment = {
            "color": color,
            "title": f"{self.brand_emoji} {self.brand_name} - Priority Update",
            "title_link": event.context.get("url", ""),
            "fields": [
                {
                    "title": "Item",
                    "value": f"*{event.item_title}*",
                    "short": False
                },
                {
                    "title": "Priority Change",
                    "value": f"{event.old_priority} {change_emoji} {event.new_priority}",
                    "short": True
                },
                {
                    "title": "Changed By",
                    "value": event.changed_by,
                    "short": True
                }
            ],
            "footer": f"{self.brand_name}",
            "footer_icon": ":robot_face:",
            "ts": int(event.timestamp.timestamp())
        }
        
        # Add context if available
        if event.context.get("reason"):
            attachment["fields"].append({
                "title": "Reason",
                "value": event.context["reason"],
                "short": False
            })
            
        # Add action if this is urgent
        if notification_priority == NotificationPriority.URGENT:
            attachment["fields"].append({
                "title": "Action Required",
                "value": "🔥 *Immediate attention needed*",
                "short": False
            })

        return {
            "text": main_text,
            "attachments": [attachment],
            "username": f"{self.brand_name}",
            "icon_emoji": ":robot_face:"
        }

    def create_completion_message(self, event: Any, 
                                notification_priority: NotificationPriority) -> Dict[str, Any]:
        """
        Create Slack message for task completion.
        
        Args:
            event: Completion event data
            notification_priority: Notification priority level
            
        Returns:
            Dict: Slack message payload
        """
        # Completion messages are always positive
        color = "#00AA00"  # Green
        
        # Create main text
        main_text = f"✅ **Task Completed** - {event.priority}"
        
        # Create attachment with details
        attachment = {
            "color": color,
            "title": f"{self.brand_emoji} {self.brand_name} - Completion Alert",
            "title_link": event.context.get("url", ""),
            "fields": [
                {
                    "title": "Completed Item",
                    "value": f"*{event.item_title}*",
                    "short": False
                },
                {
                    "title": "Priority",
                    "value": f"{self._get_priority_display(event.priority)}",
                    "short": True
                },
                {
                    "title": "Completed By",
                    "value": event.completed_by,
                    "short": True
                }
            ],
            "footer": f"{self.brand_name}",
            "footer_icon": ":white_check_mark:",
            "ts": int(event.timestamp.timestamp())
        }
        
        # Add completion time if available
        if event.context.get("duration"):
            attachment["fields"].append({
                "title": "Duration",
                "value": event.context["duration"],
                "short": True
            })
            
        # Add next steps if available
        if event.context.get("next_steps"):
            attachment["fields"].append({
                "title": "Next Steps",
                "value": event.context["next_steps"],
                "short": False
            })

        return {
            "text": main_text,
            "attachments": [attachment],
            "username": f"{self.brand_name}",
            "icon_emoji": ":white_check_mark:"
        }

    def create_sprint_message(self, event: Any) -> Dict[str, Any]:
        """
        Create Slack message for sprint milestone.
        
        Args:
            event: Sprint event data
            
        Returns:
            Dict: Slack message payload
        """
        # Sprint messages use blue theme
        color = "#1E90FF"
        
        # Create progress bar
        progress_bar = self._create_progress_bar(event.progress)
        
        # Create main text
        main_text = f"📊 **Sprint Update** - {event.milestone}"
        
        # Create attachment with details
        attachment = {
            "color": color,
            "title": f"{self.brand_emoji} {self.brand_name} - Sprint Milestone",
            "fields": [
                {
                    "title": "Milestone",
                    "value": f"*{event.milestone}*",
                    "short": False
                },
                {
                    "title": "Progress",
                    "value": f"{progress_bar} {event.progress:.1f}%",
                    "short": True
                },
                {
                    "title": "Completed Items",
                    "value": str(len(event.completed_items)),
                    "short": True
                }
            ],
            "footer": f"{self.brand_name}",
            "footer_icon": ":chart_with_upwards_trend:",
            "ts": int(event.timestamp.timestamp())
        }
        
        # Add completed items list if not too long
        if event.completed_items and len(event.completed_items) <= 5:
            items_text = "\n".join([f"• {item}" for item in event.completed_items])
            attachment["fields"].append({
                "title": "Recently Completed",
                "value": items_text,
                "short": False
            })
        elif len(event.completed_items) > 5:
            attachment["fields"].append({
                "title": "Recently Completed",
                "value": f"• {event.completed_items[0]}\n• {event.completed_items[1]}\n• ... and {len(event.completed_items) - 2} more",
                "short": False
            })

        return {
            "text": main_text,
            "attachments": [attachment],
            "username": f"{self.brand_name}",
            "icon_emoji": ":chart_with_upwards_trend:"
        }

    def create_custom_message(self, title: str, message: str, 
                            priority: NotificationPriority,
                            context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create custom Slack message.
        
        Args:
            title: Message title
            message: Message content
            priority: Notification priority
            context: Additional context data
            
        Returns:
            Dict: Slack message payload
        """
        priority_emoji = self.priority_emojis[priority]
        color = self.priority_colors[priority]
        
        # Create main text
        main_text = f"{priority_emoji} **{title}**"
        
        # Create attachment
        attachment = {
            "color": color,
            "title": f"{self.brand_emoji} {self.brand_name} - Custom Notification",
            "text": message,
            "footer": f"{self.brand_name}",
            "footer_icon": ":robot_face:",
            "ts": int(datetime.now(timezone.utc).timestamp())
        }
        
        # Add context fields if provided
        if context:
            fields = []
            for key, value in context.items():
                if key not in ["url", "link"]:  # Skip special fields
                    fields.append({
                        "title": key.replace("_", " ").title(),
                        "value": str(value),
                        "short": len(str(value)) < 50
                    })
            
            if fields:
                attachment["fields"] = fields
                
        # Add link if provided
        if context.get("url") or context.get("link"):
            attachment["title_link"] = context.get("url") or context.get("link")

        return {
            "text": main_text,
            "attachments": [attachment],
            "username": f"{self.brand_name}",
            "icon_emoji": ":robot_face:"
        }

    def _get_priority_change_emoji(self, old_priority: str, new_priority: str) -> str:
        """Get emoji representing priority change direction."""
        # Extract numeric parts for comparison
        old_num = int(old_priority[1:]) if old_priority.startswith('P') else 99
        new_num = int(new_priority[1:]) if new_priority.startswith('P') else 99
        
        if new_num < old_num:
            return "⬆️"  # Increasing priority (lower number = higher priority)
        elif new_num > old_num:
            return "⬇️"  # Decreasing priority
        else:
            return "➡️"  # Same priority level

    def _get_priority_display(self, priority: str) -> str:
        """Get enhanced priority display with emoji."""
        priority_displays = {
            "P0": "🔥 P0 - Critical",
            "P1": "⚡ P1 - High",
            "P2": "📋 P2 - Medium",
            "P3": "📝 P3 - Low"
        }
        return priority_displays.get(priority, f"📋 {priority}")

    def _create_progress_bar(self, progress: float, length: int = 10) -> str:
        """Create visual progress bar."""
        filled = int(progress * length / 100)
        bar = "█" * filled + "░" * (length - filled)
        return f"`{bar}`"