#!/usr/bin/env python3
"""
Enhanced Context Usage Monitor - Real-time monitoring with configurable thresholds
Builds on the existing context_memory_manager.py with improved monitoring and user control
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from scripts.context_memory_manager import ContextMemoryManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedContextMonitor(ContextMemoryManager):
    """Enhanced context monitor with configurable thresholds and real-time tracking"""
    
    def __init__(self):
        super().__init__()
        self.config_dir = Path(".claude/config")
        self.config_file = self.config_dir / "context_thresholds.json"
        self.config = self._load_config()
        self.usage_history = []
        self.last_check_time = None
        self.warnings_sent = set()
        
        # Override thresholds from config
        thresholds = self.config.get("thresholds", {})
        self.warning_threshold = thresholds.get("consolidation_light", 75)
        self.critical_threshold = thresholds.get("consolidation_critical", 85) 
        self.emergency_threshold = thresholds.get("sleep_emergency", 95)
        
    def _load_config(self) -> Dict:
        """Load configuration from JSON file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Config file not found at {self.config_file}, using defaults")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            "thresholds": {
                "consolidation_light": 75,
                "consolidation_critical": 85,
                "sleep_emergency": 95
            },
            "monitoring": {
                "check_interval_seconds": 300,
                "warning_advance_notice": 5,
                "enable_automatic_actions": True,
                "enable_background_monitoring": False
            },
            "actions": {
                "75_percent": {
                    "action": "consolidate_light",
                    "notify": True,
                    "message": "🟡 Context usage at 75% - Light consolidation recommended"
                },
                "85_percent": {
                    "action": "consolidate_critical", 
                    "notify": True,
                    "message": "🟠 Context usage at 85% - Critical consolidation required"
                },
                "95_percent": {
                    "action": "sleep_emergency",
                    "notify": True,
                    "message": "🔴 Context usage at 95% - Emergency sleep/wake cycle required"
                }
            },
            "display": {
                "show_percentage": True,
                "show_progress_bar": True,
                "progress_bar_width": 40,
                "color_coding": True
            }
        }
    
    def save_config(self) -> bool:
        """Save current configuration to file"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.config["meta"] = {
                "version": "1.0.0",
                "last_updated": datetime.now().isoformat(),
                "created_by": "Enhanced Context Monitor"
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            logger.info(f"✅ Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save configuration: {e}")
            return False
    
    def get_enhanced_context_usage(self) -> Dict:
        """Enhanced context usage calculation with history tracking"""
        current_time = datetime.now()
        
        # Get base usage from parent class
        base_usage = self.get_context_usage()
        
        # Enhance with additional metrics
        enhanced_usage = {
            "percentage": base_usage if base_usage is not None else 0.0,
            "timestamp": current_time.isoformat(),
            "threshold_status": self.check_context_threshold()[1],
            "time_since_last_check": None,
            "usage_trend": "stable",
            "estimated_time_to_critical": None,
            "estimated_time_to_emergency": None
        }
        
        # Calculate time since last check
        if self.last_check_time:
            time_diff = (current_time - self.last_check_time).total_seconds()
            enhanced_usage["time_since_last_check"] = time_diff
        
        # Add to history
        self.usage_history.append({
            "timestamp": current_time,
            "usage": enhanced_usage["percentage"]
        })
        
        # Keep only last 24 hours of history
        cutoff_time = current_time - timedelta(hours=24)
        self.usage_history = [
            entry for entry in self.usage_history 
            if entry["timestamp"] > cutoff_time
        ]
        
        # Calculate trend if we have enough data
        if len(self.usage_history) >= 3:
            recent_usage = [entry["usage"] for entry in self.usage_history[-3:]]
            if recent_usage[-1] > recent_usage[0] + 5:
                enhanced_usage["usage_trend"] = "increasing"
                # Estimate time to thresholds based on current rate
                if len(self.usage_history) >= 2:
                    rate = (recent_usage[-1] - recent_usage[0]) / len(recent_usage)
                    if rate > 0:
                        current_usage = enhanced_usage["percentage"]
                        if current_usage < self.critical_threshold:
                            time_to_critical = (self.critical_threshold - current_usage) / rate
                            enhanced_usage["estimated_time_to_critical"] = time_to_critical * 300  # Assuming 5min intervals
                        if current_usage < self.emergency_threshold:
                            time_to_emergency = (self.emergency_threshold - current_usage) / rate
                            enhanced_usage["estimated_time_to_emergency"] = time_to_emergency * 300
            elif recent_usage[-1] < recent_usage[0] - 5:
                enhanced_usage["usage_trend"] = "decreasing"
        
        self.last_check_time = current_time
        return enhanced_usage
    
    def get_progress_bar(self, usage_percentage: float, width: int = 40) -> str:
        """Generate a visual progress bar for context usage"""
        filled = int(usage_percentage / 100 * width)
        empty = width - filled
        
        # Color coding based on thresholds
        if usage_percentage >= self.emergency_threshold:
            bar_char = "🔴"
        elif usage_percentage >= self.critical_threshold:
            bar_char = "🟠"
        elif usage_percentage >= self.warning_threshold:
            bar_char = "🟡"
        else:
            bar_char = "🟢"
        
        # For 0% usage, ensure at least some visual representation
        if filled == 0 and usage_percentage > 0:
            filled = 1
            empty = width - 1
        
        progress_bar = bar_char * filled + "⬜" * empty
        return f"[{progress_bar}] {usage_percentage:.1f}%"
    
    def display_context_status(self) -> str:
        """Display comprehensive context status"""
        usage_data = self.get_enhanced_context_usage()
        
        status_lines = [
            "📊 Context Usage Monitor Status",
            "=" * 50,
            f"Current Usage: {usage_data['percentage']:.1f}%",
            f"Threshold Status: {usage_data['threshold_status']}",
            f"Trend: {usage_data['usage_trend']}",
            f"Last Check: {usage_data['timestamp'][:19]}"
        ]
        
        # Add progress bar if enabled
        if self.config.get("display", {}).get("show_progress_bar", True):
            width = self.config.get("display", {}).get("progress_bar_width", 40)
            progress_bar = self.get_progress_bar(usage_data['percentage'], width)
            status_lines.append(f"Progress: {progress_bar}")
        
        # Add threshold information
        status_lines.extend([
            "",
            "🎯 Thresholds:",
            f"  Light Consolidation: {self.warning_threshold}%",
            f"  Critical Consolidation: {self.critical_threshold}%", 
            f"  Emergency Sleep: {self.emergency_threshold}%"
        ])
        
        # Add time estimates if available
        if usage_data.get("estimated_time_to_critical"):
            minutes = int(usage_data["estimated_time_to_critical"] / 60)
            status_lines.append(f"  ⏰ Est. time to critical: {minutes} minutes")
        
        if usage_data.get("estimated_time_to_emergency"):
            minutes = int(usage_data["estimated_time_to_emergency"] / 60)
            status_lines.append(f"  ⏰ Est. time to emergency: {minutes} minutes")
        
        # Add action recommendations
        needs_action, level = self.check_context_threshold()
        if needs_action:
            status_lines.extend([
                "",
                "⚠️  Recommended Actions:",
                self._get_action_message(level)
            ])
        
        return "\n".join(status_lines)
    
    def _get_action_message(self, level: str) -> str:
        """Get action message for threshold level"""
        action_key = f"{self._get_threshold_percentage(level)}_percent"
        action_config = self.config.get("actions", {}).get(action_key, {})
        return action_config.get("message", f"Action required for {level} threshold")
    
    def _get_threshold_percentage(self, level: str) -> str:
        """Convert threshold level to percentage key"""
        level_map = {
            "warning": "75",
            "critical": "85", 
            "emergency": "95"
        }
        return level_map.get(level, "75")
    
    def check_and_notify_thresholds(self) -> List[str]:
        """Check thresholds and return any notifications needed"""
        notifications = []
        usage_data = self.get_enhanced_context_usage()
        usage_percentage = usage_data["percentage"]
        
        # Check each threshold
        thresholds_to_check = [
            (self.emergency_threshold, "emergency", "95"),
            (self.critical_threshold, "critical", "85"),
            (self.warning_threshold, "warning", "75")
        ]
        
        for threshold, level, key in thresholds_to_check:
            if usage_percentage >= threshold:
                threshold_key = f"{key}_percent"
                
                # Only notify once per threshold until usage drops below it
                if threshold_key not in self.warnings_sent:
                    action_config = self.config.get("actions", {}).get(threshold_key, {})
                    if action_config.get("notify", True):
                        notifications.append(action_config.get("message", f"Threshold {threshold}% reached"))
                        self.warnings_sent.add(threshold_key)
                
                break  # Only trigger highest threshold reached
            else:
                # Clear warnings for thresholds we're now below
                threshold_key = f"{key}_percent"
                if threshold_key in self.warnings_sent:
                    self.warnings_sent.remove(threshold_key)
        
        return notifications
    
    def update_threshold(self, threshold_name: str, value: float) -> bool:
        """Update a specific threshold value"""
        try:
            if threshold_name in self.config["thresholds"]:
                old_value = self.config["thresholds"][threshold_name]
                self.config["thresholds"][threshold_name] = value
                
                # Update instance variables
                if threshold_name == "consolidation_light":
                    self.warning_threshold = value
                elif threshold_name == "consolidation_critical":
                    self.critical_threshold = value
                elif threshold_name == "sleep_emergency":
                    self.emergency_threshold = value
                
                logger.info(f"✅ Updated {threshold_name}: {old_value}% → {value}%")
                return self.save_config()
            else:
                logger.error(f"❌ Unknown threshold: {threshold_name}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to update threshold: {e}")
            return False
    
    def get_usage_history_summary(self, hours: int = 6) -> Dict:
        """Get usage history summary for specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_history = [
            entry for entry in self.usage_history 
            if entry["timestamp"] > cutoff_time
        ]
        
        if not recent_history:
            return {"error": "No usage history available"}
        
        usage_values = [entry["usage"] for entry in recent_history]
        
        return {
            "period_hours": hours,
            "data_points": len(recent_history),
            "min_usage": min(usage_values),
            "max_usage": max(usage_values),
            "avg_usage": sum(usage_values) / len(usage_values),
            "current_usage": usage_values[-1] if usage_values else 0,
            "trend": "increasing" if len(usage_values) >= 2 and usage_values[-1] > usage_values[0] else "decreasing" if len(usage_values) >= 2 else "stable"
        }

    async def monitor_with_notifications(self, duration_minutes: int = 60) -> None:
        """Monitor context usage with notifications for specified duration"""
        logger.info(f"🔍 Starting enhanced context monitoring for {duration_minutes} minutes")
        
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        check_interval = self.config.get("monitoring", {}).get("check_interval_seconds", 300)
        
        while datetime.now() < end_time:
            try:
                # Check current usage and get notifications
                notifications = self.check_and_notify_thresholds()
                
                # Display notifications
                for notification in notifications:
                    print(f"\n{notification}")
                    logger.warning(notification)
                
                # Check if automatic actions are enabled
                if self.config.get("monitoring", {}).get("enable_automatic_actions", True):
                    needs_action, level = self.check_context_threshold()
                    if needs_action and level in ["critical", "emergency"]:
                        logger.warning(f"🤖 Automatic action triggered for {level} threshold")
                        await self.consolidate_memory("critical" if level == "critical" else "emergency")
                
                # Wait for next check
                time.sleep(min(check_interval, 60))  # Max 1 minute intervals for monitoring
                
            except Exception as e:
                logger.error(f"Error in enhanced monitoring: {e}")
                time.sleep(60)
        
        logger.info("🏁 Enhanced context monitoring session completed")

def main():
    """Main CLI interface for enhanced context monitor"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Context Usage Monitor")
    parser.add_argument("--status", action="store_true", help="Show current context status")
    parser.add_argument("--history", type=int, default=6, help="Show usage history for N hours")
    parser.add_argument("--monitor", type=int, help="Monitor for N minutes with notifications")
    parser.add_argument("--threshold", nargs=2, metavar=("NAME", "VALUE"), help="Update threshold (consolidation_light|consolidation_critical|sleep_emergency VALUE)")
    parser.add_argument("--config", action="store_true", help="Show current configuration")
    parser.add_argument("--reset-config", action="store_true", help="Reset configuration to defaults")
    
    args = parser.parse_args()
    
    monitor = EnhancedContextMonitor()
    
    if args.status:
        print(monitor.display_context_status())
    
    elif args.history:
        history = monitor.get_usage_history_summary(args.history)
        if "error" not in history:
            print(f"\n📈 Usage History (Last {args.history} hours):")
            print(f"  Data Points: {history['data_points']}")
            print(f"  Min Usage: {history['min_usage']:.1f}%")
            print(f"  Max Usage: {history['max_usage']:.1f}%")
            print(f"  Avg Usage: {history['avg_usage']:.1f}%")
            print(f"  Current: {history['current_usage']:.1f}%")
            print(f"  Trend: {history['trend']}")
        else:
            print(f"❌ {history['error']}")
    
    elif args.monitor:
        import asyncio
        asyncio.run(monitor.monitor_with_notifications(args.monitor))
    
    elif args.threshold:
        name, value = args.threshold
        try:
            threshold_value = float(value)
            if 0 <= threshold_value <= 100:
                success = monitor.update_threshold(name, threshold_value)
                if success:
                    print(f"✅ Updated {name} to {threshold_value}%")
                else:
                    print(f"❌ Failed to update {name}")
            else:
                print("❌ Threshold value must be between 0 and 100")
        except ValueError:
            print("❌ Threshold value must be a number")
    
    elif args.config:
        print("📋 Current Configuration:")
        print(json.dumps(monitor.config, indent=2))
    
    elif args.reset_config:
        monitor.config = monitor._get_default_config()
        if monitor.save_config():
            print("✅ Configuration reset to defaults")
        else:
            print("❌ Failed to reset configuration")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()