#!/usr/bin/env python3
"""
Escalation Monitor

Monitors for human escalation files and provides notifications.
"""

import os
import time
import glob
from datetime import datetime
from pathlib import Path
from typing import List, Dict

class EscalationMonitor:
    """Monitor for human escalation requests"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.escalation_pattern = "HUMAN_ESCALATION_*.md"
        self.processed_files = set()
    
    def scan_for_escalations(self) -> List[Path]:
        """Scan for new escalation files"""
        escalation_files = list(self.base_dir.glob(self.escalation_pattern))
        new_files = [f for f in escalation_files if f not in self.processed_files]
        return new_files
    
    def process_escalation(self, escalation_file: Path) -> Dict:
        """Process an escalation file"""
        try:
            content = escalation_file.read_text()
            
            # Parse escalation details
            escalation = {
                "file": str(escalation_file),
                "timestamp": escalation_file.stat().st_mtime,
                "content": content,
                "level": self._extract_level(content),
                "summary": self._extract_summary(content),
                "agents": self._extract_agents(content),
                "urgency": self._assess_urgency(content)
            }
            
            return escalation
            
        except Exception as e:
            return {
                "file": str(escalation_file),
                "error": str(e),
                "timestamp": time.time()
            }
    
    def _extract_level(self, content: str) -> str:
        """Extract escalation level from content"""
        for line in content.split('\n'):
            if "ESCALATION LEVEL:" in line:
                level = line.split("ESCALATION LEVEL:")[-1].strip()
                return level.strip("[]")
        return "UNKNOWN"
    
    def _extract_summary(self, content: str) -> str:
        """Extract issue summary"""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "ISSUE SUMMARY:" in line and i + 1 < len(lines):
                return lines[i + 1].strip()
        return "No summary available"
    
    def _extract_agents(self, content: str) -> List[str]:
        """Extract affected agents"""
        agents = []
        in_agents_section = False
        
        for line in content.split('\n'):
            if "AFFECTED AGENTS:" in line:
                in_agents_section = True
                continue
            elif in_agents_section:
                if line.startswith("- ") and ":" in line:
                    agent = line.split(":")[0].replace("- ", "").strip()
                    agents.append(agent)
                elif line.strip() == "" or not line.startswith("- "):
                    break
        
        return agents
    
    def _assess_urgency(self, content: str) -> int:
        """Assess urgency level (1-10)"""
        urgency_keywords = {
            "URGENT": 9,
            "CRITICAL": 10,
            "HIGH": 7,
            "MEDIUM": 5,
            "LOW": 3,
            "STUCK": 8,
            "BLOCKED": 8,
            "FAILED": 9
        }
        
        content_upper = content.upper()
        max_urgency = 1
        
        for keyword, urgency in urgency_keywords.items():
            if keyword in content_upper:
                max_urgency = max(max_urgency, urgency)
        
        return max_urgency
    
    def notify_human(self, escalation: Dict):
        """Notify human about escalation"""
        print("\n" + "🚨" * 20)
        print("  HUMAN ASSISTANCE REQUIRED!")
        print("🚨" * 20)
        print()
        print(f"📁 File: {escalation['file']}")
        print(f"⏰ Time: {datetime.fromtimestamp(escalation['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔥 Level: {escalation['level']}")
        print(f"📊 Urgency: {escalation['urgency']}/10")
        print(f"👥 Agents: {', '.join(escalation['agents'])}")
        print()
        print(f"📝 Summary: {escalation['summary']}")
        print()
        print("📄 Full details in escalation file:")
        print(f"   cat {escalation['file']}")
        print()
        print("🚨" * 20)
        print()
    
    def run_monitor(self, interval: int = 30):
        """Run continuous monitoring"""
        print("🔍 Starting escalation monitor...")
        print(f"📁 Monitoring directory: {self.base_dir}")
        print(f"🔄 Check interval: {interval} seconds")
        print("⏰ Monitoring started at:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print()
        
        while True:
            try:
                new_escalations = self.scan_for_escalations()
                
                for escalation_file in new_escalations:
                    escalation = self.process_escalation(escalation_file)
                    self.notify_human(escalation)
                    self.processed_files.add(escalation_file)
                
                if not new_escalations:
                    print(f"⏳ {datetime.now().strftime('%H:%M:%S')} - No escalations detected")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n👋 Escalation monitoring stopped")
                break
            except Exception as e:
                print(f"❌ Monitor error: {e}")
                time.sleep(interval)
    
    def check_once(self) -> bool:
        """Check for escalations once and return if any found"""
        escalations = self.scan_for_escalations()
        
        if escalations:
            print(f"🚨 Found {len(escalations)} escalation(s):")
            for escalation_file in escalations:
                escalation = self.process_escalation(escalation_file)
                self.notify_human(escalation)
            return True
        else:
            print("✅ No escalations found")
            return False

def main():
    """Main CLI interface"""
    import sys
    
    monitor = EscalationMonitor()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "--check":
            # Single check
            monitor.check_once()
        elif command == "--continuous":
            # Continuous monitoring
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            monitor.run_monitor(interval)
        elif command == "--list":
            # List all escalation files
            files = list(monitor.base_dir.glob(monitor.escalation_pattern))
            if files:
                print(f"📋 Found {len(files)} escalation file(s):")
                for f in sorted(files):
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    print(f"  - {f.name} ({mtime.strftime('%Y-%m-%d %H:%M:%S')})")
            else:
                print("✅ No escalation files found")
        else:
            print("Usage:")
            print("  python monitor_escalations.py --check")
            print("  python monitor_escalations.py --continuous [interval_seconds]")
            print("  python monitor_escalations.py --list")
    else:
        # Default: single check
        monitor.check_once()

if __name__ == "__main__":
    main()