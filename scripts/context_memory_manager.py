#!/usr/bin/env python3
"""
Context Memory Manager - Automated memory consolidation and context management
Monitors context usage and triggers sleep/wake patterns to preserve knowledge
"""

import argparse
import hashlib
import json
import logging
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ContextMemoryManager:
    """Manages context window usage and automatic memory consolidation"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.memory_dir = Path(".claude/memory")
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # Backup memory directory for redundancy
        self.backup_memory_dir = Path(".claude/memory_backup")
        self.backup_memory_dir.mkdir(parents=True, exist_ok=True)

        # Context thresholds
        self.warning_threshold = 70  # Start preparing for consolidation
        self.critical_threshold = 85  # Immediate consolidation required
        self.emergency_threshold = 95  # Emergency sleep/wake cycle

    def _calculate_checksum(self, content: str) -> str:
        """Calculate SHA-256 checksum of content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _atomic_write_file(
            self,
            file_path: Path,
            content: str,
            backup: bool = True) -> bool:
        """
        Write file atomically using temp file and rename.
        Includes checksum generation and optional backup.
        """
        try:
            # Calculate checksum
            checksum = self._calculate_checksum(content)

            # Create content with checksum metadata
            if file_path.suffix == '.json':
                # For JSON files, add checksum to the data
                try:
                    data = json.loads(content)
                    # Calculate checksum of original data (without metadata)
                    original_checksum = self._calculate_checksum(
                        json.dumps(data, separators=(',', ':'), sort_keys=True))
                    data['_checksum'] = original_checksum
                    data['_timestamp'] = datetime.now().isoformat()
                    final_content = json.dumps(data, indent=2)
                except json.JSONDecodeError:
                    # If not valid JSON, treat as plain text
                    final_content = content
            else:
                # For markdown/text files, add checksum as comment
                final_content = f"{content}\n\n<!-- Checksum: {checksum} -->\n<!-- Timestamp: {
                    datetime.now().isoformat()} -->"

            # Write to temporary file first
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=file_path.parent,
                prefix=f'.{file_path.name}.tmp',
                delete=False
            ) as tmp_file:
                tmp_file.write(final_content)
                tmp_path = Path(tmp_file.name)

            # Atomic rename to final destination
            tmp_path.rename(file_path)

            # Create backup copy if requested
            if backup and self.backup_memory_dir.exists():
                backup_path = self.backup_memory_dir / file_path.name
                with open(backup_path, 'w') as backup_file:
                    backup_file.write(final_content)

            logger.debug(f"✅ Atomic write successful: {file_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Atomic write failed for {file_path}: {e}")
            # Clean up temp file if it exists
            if 'tmp_path' in locals() and tmp_path.exists():
                tmp_path.unlink()
            return False

    def _verify_file_integrity(self, file_path: Path) -> bool:
        """Verify file integrity using stored checksum"""
        try:
            if not file_path.exists():
                return False

            with open(file_path, 'r') as f:
                content = f.read()

            if file_path.suffix == '.json':
                # For JSON files, check embedded checksum
                try:
                    data = json.loads(content)
                    stored_checksum = data.get('_checksum')
                    if stored_checksum:
                        # Remove checksum and timestamp for verification
                        verification_data = {k: v for k, v in data.items()
                                             if not k.startswith('_')}
                        # Use consistent JSON formatting (no indent for
                        # checksum calculation)
                        verification_content = json.dumps(
                            verification_data, separators=(
                                ',', ':'), sort_keys=True)
                        calculated_checksum = self._calculate_checksum(
                            verification_content)
                        logger.debug(f"Stored checksum: {stored_checksum}")
                        logger.debug(
                            f"Calculated checksum: {calculated_checksum}")
                        return stored_checksum == calculated_checksum
                except json.JSONDecodeError:
                    pass
            else:
                # For markdown/text files, extract checksum from comment
                checksum_match = re.search(
                    r'<!-- Checksum: ([a-f0-9]{64}) -->', content)
                if checksum_match:
                    stored_checksum = checksum_match.group(1)
                    # Remove checksum and timestamp lines for verification
                    clean_content = re.sub(
                        r'\n\n<!-- Checksum: [a-f0-9]{64} -->\n<!-- Timestamp: .* -->', '', content)
                    calculated_checksum = self._calculate_checksum(
                        clean_content)
                    return stored_checksum == calculated_checksum

            # If no checksum found, consider file valid but warn
            logger.warning(
                f"⚠️ No checksum found in {file_path} - consider it valid but unverified")
            return True

        except Exception as e:
            logger.error(f"❌ File integrity check failed for {file_path}: {e}")
            return False

    def get_context_usage(self) -> Optional[float]:
        """
        Get current context window usage percentage
        """
        try:
            # Try to extract from Claude Code interface
            # This is a simplified version - in practice would need Claude Code
            # API

            # For now, estimate based on conversation length and complexity
            # In a real implementation, this would query Claude Code directly

            # Placeholder calculation based on file sizes and activity
            total_size = 0
            for file_type in ["*.py", "*.md", "*.json"]:
                files = list(self.project_root.rglob(file_type))
                total_size += sum(f.stat().st_size for f in files if f.exists())

            # Rough estimation: >50MB of active files suggests high context
            # usage
            estimated_usage = min(90, (total_size / (50 * 1024 * 1024)) * 70)

            logger.info(f"📊 Estimated context usage: {estimated_usage:.1f}%")
            return estimated_usage

        except Exception as e:
            logger.warning(f"Could not determine context usage: {e}")
            return None

    def check_context_threshold(self) -> Tuple[bool, str]:
        """Check if context usage requires action"""
        usage = self.get_context_usage()

        if usage is None:
            return False, "unknown"

        if usage >= self.emergency_threshold:
            return True, "emergency"
        elif usage >= self.critical_threshold:
            return True, "critical"
        elif usage >= self.warning_threshold:
            return True, "warning"
        else:
            return False, "normal"

    async def consolidate_memory(self, level: str = "normal") -> bool:
        """Consolidate current context into persistent memory"""
        try:
            logger.info(f"🧠 Starting memory consolidation (level: {level})")

            # 1. Save current state
            current_state = await self._capture_current_state()

            # 2. Update essential knowledge
            await self._update_essential_knowledge(current_state)

            # 3. Consolidate learning
            if level in ["critical", "emergency"]:
                await self._deep_consolidation(current_state)
            else:
                await self._light_consolidation(current_state)

            # 4. Save memory snapshot
            await self._save_memory_snapshot(current_state, level)

            logger.info(f"✅ Memory consolidation completed (level: {level})")
            return True

        except Exception as e:
            logger.error(f"❌ Memory consolidation failed: {e}")
            return False

    async def _capture_current_state(self) -> Dict:
        """Capture current project and agent state"""
        state = {
            "timestamp": datetime.now().isoformat(),
            "agent_status": {},
            "project_status": {},
            "active_work": {},
            "critical_insights": []
        }

        try:
            # Get agent status
            cmd = [
                "python",
                "scripts/check_agent_status.py",
                "--format",
                "json"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                try:
                    state["agent_status"] = json.loads(result.stdout)
                except json.JSONDecodeError:
                    state["agent_status"] = {"raw_output": result.stdout}

            # Get git status
            cmd = ["git", "status", "--porcelain"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                state["project_status"]["uncommitted_changes"] = result.stdout.strip()

            # Get recent commits
            cmd = ["git", "log", "--oneline", "-10"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                state["project_status"]["recent_commits"] = result.stdout.strip()

            # Get PR status
            cmd = ["gh", "pr", "list", "--state", "open",
                   "--json", "number,title,headRefName"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                try:
                    state["project_status"]["open_prs"] = json.loads(
                        result.stdout)
                except json.JSONDecodeError:
                    pass

            # Check active agent worktrees
            worktree_paths = list(Path("new-worktrees").glob("*"))
            state["active_work"]["worktrees"] = [
                str(p) for p in worktree_paths]

        except Exception as e:
            logger.warning(f"Error capturing state: {e}")

        return state

    async def _update_essential_knowledge(self, current_state: Dict):
        """Update the essential knowledge file with latest discoveries"""
        essential_file = self.memory_dir / "ESSENTIAL_WORKFLOW_KNOWLEDGE.md"

        if not essential_file.exists():
            logger.warning(
                "Essential knowledge file not found - creating new one")
            return

        try:
            # Read current essential knowledge
            with open(essential_file, 'r') as f:
                content = f.read()

            # Update timestamp
            updated_content = re.sub(
                r'\*Last Updated: [^*]+\*',
                f'*Last Updated: {
    datetime.now().strftime("%Y-%m-%d")} - Auto-updated by context manager*',
                content
            )

            # Add current project status if significantly changed
            if current_state.get("project_status", {}).get("recent_commits"):
                recent_work = current_state["project_status"]["recent_commits"].split('\n')[
                    0]
                if "## 📋 CURRENT PROJECT STATUS" in updated_content:
                    # Update the current status section
                    status_pattern = r'(## 📋 CURRENT PROJECT STATUS.*?)(### |\## |$)'
                    updated_content = re.sub(
                        status_pattern,
                        f'\\1\n### **Latest Work** \\n- {recent_work}\\n\\n\\2',
                        updated_content,
                        flags=re.DOTALL)

            # Write updated content
            with open(essential_file, 'w') as f:
                f.write(updated_content)

            logger.info("✅ Essential knowledge updated")

        except Exception as e:
            logger.error(f"Failed to update essential knowledge: {e}")

    async def _light_consolidation(self, current_state: Dict):
        """Light memory consolidation - preserve key insights"""
        consolidation_file = self.memory_dir / "LIGHT_CONSOLIDATION.md"

        insights = [
            "# Light Memory Consolidation",
            f"**Timestamp**: {current_state['timestamp']}",
            "",
            "## Key Working Systems",
            "- Agent Communication: `scripts/fixed_agent_communication.py`",
            "- Quality Gates: Evidence-based validation required",
            "- Git Workflow: Commit + push mandatory before completion",
            "",
            "## Current Focus",
        ]

        # Add current agent status
        if current_state.get("agent_status"):
            insights.append("### Agent Status")
            if isinstance(current_state["agent_status"], dict):
                for agent, status in current_state["agent_status"].items():
                    insights.append(f"- {agent}: {status}")
            else:
                insights.append(
                    f"- Status check: {str(current_state['agent_status'])[:200]}...")

        # Add recent work
        if current_state.get("project_status", {}).get("recent_commits"):
            insights.append("\n### Recent Work")
            for commit in current_state["project_status"]["recent_commits"].split('\n')[
                    :3]:
                if commit.strip():
                    insights.append(f"- {commit}")

        with open(consolidation_file, 'w') as f:
            f.write('\n'.join(insights))

        logger.info("✅ Light consolidation saved")

    async def _deep_consolidation(self, current_state: Dict):
        """Deep memory consolidation - comprehensive state preservation"""
        consolidation_file = self.memory_dir / \
            f"DEEP_CONSOLIDATION_{datetime.now().strftime('%Y%m%d_%H%M')}.md"

        comprehensive_state = {
            "consolidation_type": "deep",
            "timestamp": current_state["timestamp"],
            "context_trigger": "High context usage detected",
            "agent_status": current_state.get("agent_status", {}),
            "project_status": current_state.get("project_status", {}),
            "active_work": current_state.get("active_work", {}),
            "critical_reminders": [
                "Use scripts/fixed_agent_communication.py for agent messaging",
                "Always verify git commits and pushes before claiming completion",
                "Evidence-based validation required for all claims",
                "Quality gates mandatory before integration"
            ]
        }

        with open(consolidation_file, 'w') as f:
            json.dump(comprehensive_state, f, indent=2)

        logger.info(f"✅ Deep consolidation saved: {consolidation_file}")

    async def _save_memory_snapshot(self, current_state: Dict, level: str):
        """Save memory snapshot for wake protocol"""
        snapshot_file = self.memory_dir / "LATEST_MEMORY_SNAPSHOT.json"

        snapshot = {
            "consolidation_level": level,
            "timestamp": current_state["timestamp"],
            "state": current_state,
            "wake_instructions": [
                "Read .claude/memory/ESSENTIAL_WORKFLOW_KNOWLEDGE.md immediately",
                "Check agent status with scripts/check_agent_status.py",
                "Verify current work with git status and PR status",
                "Resume coordination using proper communication scripts"]}

        with open(snapshot_file, 'w') as f:
            json.dump(snapshot, f, indent=2)

        logger.info("✅ Memory snapshot saved for wake protocol")

    async def wake_from_memory(self) -> Dict:
        """Restore essential knowledge and state from memory"""
        logger.info("🌅 Initiating wake protocol - restoring memory")

        wake_summary = {
            "essential_knowledge_restored": False,
            "memory_snapshot_restored": False,
            "current_state_verified": False,
            "recommendations": []
        }

        try:
            # 1. Restore essential knowledge
            essential_file = self.memory_dir / "ESSENTIAL_WORKFLOW_KNOWLEDGE.md"
            if essential_file.exists():
                with open(essential_file, 'r') as f:
                    essential_content = f.read()

                wake_summary["essential_knowledge_restored"] = True
                wake_summary["essential_knowledge_summary"] = essential_content[:500] + "..."
                logger.info("✅ Essential workflow knowledge restored")

            # 2. Restore latest memory snapshot
            snapshot_file = self.memory_dir / "LATEST_MEMORY_SNAPSHOT.json"
            if snapshot_file.exists():
                with open(snapshot_file, 'r') as f:
                    snapshot = json.load(f)

                wake_summary["memory_snapshot_restored"] = True
                wake_summary["last_consolidation"] = snapshot.get("timestamp")
                wake_summary["consolidation_level"] = snapshot.get(
                    "consolidation_level")

                # Include wake instructions
                wake_summary["wake_instructions"] = snapshot.get(
                    "wake_instructions", [])
                logger.info("✅ Memory snapshot restored")

            # 3. Verify current state
            current_state = await self._capture_current_state()
            wake_summary["current_state_verified"] = True
            wake_summary["current_timestamp"] = current_state["timestamp"]

            # 4. Generate recommendations
            wake_summary["recommendations"] = [
                "Review essential workflow knowledge",
                "Check agent status and coordination",
                "Verify current work and priorities",
                "Use proper communication scripts for agent coordination"
            ]

            logger.info("🎯 Wake protocol completed successfully")

        except Exception as e:
            logger.error(f"❌ Wake protocol error: {e}")
            wake_summary["error"] = str(e)

        return wake_summary

    async def monitor_context_continuous(self, check_interval: int = 300):
        """Continuously monitor context usage and trigger consolidation"""
        logger.info(
            f"👁️ Starting continuous context monitoring (interval: {check_interval}s)")

        while True:
            try:
                needs_action, level = self.check_context_threshold()

                if needs_action:
                    logger.warning(f"🚨 Context threshold reached: {level}")

                    if level == "emergency":
                        logger.critical(
                            "🔴 EMERGENCY: Immediate sleep/wake cycle required")
                        await self.consolidate_memory("emergency")
                        # In practice, would trigger Claude Code sleep/wake
                        # here

                    elif level == "critical":
                        logger.warning(
                            "🟠 CRITICAL: Memory consolidation required")
                        await self.consolidate_memory("critical")

                    elif level == "warning":
                        logger.info(
                            "🟡 WARNING: Preparing memory consolidation")
                        await self.consolidate_memory("normal")

                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"Error in context monitoring: {e}")
                await asyncio.sleep(60)  # Wait before retrying


async def main():
    parser = argparse.ArgumentParser(description="Context Memory Manager")
    parser.add_argument("--check", action="store_true",
                        help="Check current context usage")
    parser.add_argument(
        "--consolidate",
        choices=[
            "normal",
            "critical",
            "emergency"],
        help="Force memory consolidation")
    parser.add_argument("--wake", action="store_true",
                        help="Wake from memory (restore essential knowledge)")
    parser.add_argument("--monitor", action="store_true",
                        help="Start continuous monitoring")
    parser.add_argument("--interval", type=int, default=300,
                        help="Monitoring interval in seconds")

    args = parser.parse_args()

    manager = ContextMemoryManager()

    if args.check:
        usage = manager.get_context_usage()
        needs_action, level = manager.check_context_threshold()

        print(
            f"📊 Context Usage: {
                usage:.1f}%" if usage else "Context usage unknown")
        print(f"🎯 Threshold Status: {level}")
        if needs_action:
            print("⚠️ Action Required: Memory consolidation recommended")

    elif args.consolidate:
        success = await manager.consolidate_memory(args.consolidate)
        if success:
            print(f"✅ Memory consolidation completed ({args.consolidate})")
        else:
            print("❌ Memory consolidation failed")
            sys.exit(1)

    elif args.wake:
        wake_summary = await manager.wake_from_memory()
        print("🌅 Wake Protocol Results:")
        for key, value in wake_summary.items():
            if key != "essential_knowledge_summary":  # Too long for display
                print(f"  {key}: {value}")

    elif args.monitor:
        await manager.monitor_context_continuous(args.interval)

    else:
        parser.print_help()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
