#!/usr/bin/env python3
"""
Balanced Workflow Management Script

Implements a balanced approach between infrastructure fixes, quality improvements,
and feature development to prevent technical debt accumulation.
"""

import subprocess
import sys
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse
import logging
from enum import Enum
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('.claude/logs/balanced_workflow.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TaskType(Enum):
    INFRASTRUCTURE = "infrastructure"
    QUALITY = "quality"
    FEATURE = "feature"
    SECURITY = "security"
    DOCUMENTATION = "documentation"

class WorkflowBalance:
    """Manages balanced workflow between different types of development tasks"""
    
    def __init__(self, repo_path: str = ".", dry_run: bool = False):
        self.repo_path = Path(repo_path)
        self.dry_run = dry_run
        
        # Balance ratios (adjustable based on project needs)
        self.balance_ratios = {
            TaskType.INFRASTRUCTURE: 0.30,  # 30% infrastructure
            TaskType.QUALITY: 0.25,         # 25% quality improvements
            TaskType.FEATURE: 0.35,         # 35% feature development
            TaskType.SECURITY: 0.10         # 10% security improvements
        }
        
        # Quality gate thresholds
        self.quality_thresholds = {
            "pylint_min": 8.0,
            "mypy_errors_max": 100,
            "complexity_max": 10,
            "test_coverage_min": 80
        }
        
    def assess_workflow_balance(self) -> Dict[str, Any]:
        """Assess current workflow balance and make recommendations"""
        logger.info("⚖️  Assessing workflow balance...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "current_tasks": [],
            "balance_assessment": {},
            "quality_gates": {},
            "recommendations": [],
            "blocked_tasks": [],
            "priority_actions": []
        }
        
        try:
            # 1. Analyze current tasks
            current_tasks = self._analyze_current_tasks()
            results["current_tasks"] = current_tasks
            
            # 2. Assess balance
            balance_assessment = self._assess_balance(current_tasks)
            results["balance_assessment"] = balance_assessment
            
            # 3. Check quality gates
            quality_gates = self._check_quality_gates()
            results["quality_gates"] = quality_gates
            
            # 4. Identify blocked tasks
            blocked_tasks = self._identify_blocked_tasks(quality_gates)
            results["blocked_tasks"] = blocked_tasks
            
            # 5. Generate recommendations
            recommendations = self._generate_recommendations(balance_assessment, quality_gates, blocked_tasks)
            results["recommendations"] = recommendations
            
            # 6. Prioritize actions
            priority_actions = self._prioritize_actions(recommendations, blocked_tasks)
            results["priority_actions"] = priority_actions
            
            logger.info(f"✅ Workflow balance assessment completed")
            return results
            
        except Exception as e:
            logger.error(f"❌ Workflow balance assessment failed: {e}")
            results["error"] = str(e)
            return results
    
    def _analyze_current_tasks(self) -> List[Dict[str, Any]]:
        """Analyze current development tasks"""
        tasks = []
        
        try:
            # Get current branches
            result = subprocess.run([
                "git", "branch", "--format=%(refname:short)|%(committerdate:iso)|%(subject)"
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            for line in result.stdout.strip().split('\n'):
                if line and '|' in line:
                    parts = line.split('|', 2)
                    if len(parts) >= 3:
                        branch_name = parts[0].strip()
                        commit_date = parts[1].strip()
                        subject = parts[2].strip()
                        
                        if branch_name not in ["main", "master"] and not branch_name.startswith("origin/"):
                            task = self._classify_task(branch_name, subject)
                            task.update({
                                "branch": branch_name,
                                "last_commit": commit_date,
                                "subject": subject
                            })
                            tasks.append(task)
            
            # Add tasks from open PRs if GitHub CLI is available
            try:
                pr_tasks = self._get_pr_tasks()
                tasks.extend(pr_tasks)
            except Exception as e:
                logger.warning(f"Could not get PR tasks: {e}")
            
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to analyze current tasks: {e}")
            return []
    
    def _classify_task(self, branch_name: str, subject: str) -> Dict[str, Any]:
        """Classify a task based on branch name and commit subject"""
        task = {
            "type": TaskType.FEATURE.value,
            "priority": TaskPriority.MEDIUM.value,
            "estimated_effort": "medium",
            "tags": []
        }
        
        # Analyze branch name
        branch_lower = branch_name.lower()
        subject_lower = subject.lower()
        
        # Infrastructure classification
        if any(keyword in branch_lower for keyword in [
            "infra", "infrastructure", "deploy", "ci", "cd", "build", "config"
        ]):
            task["type"] = TaskType.INFRASTRUCTURE.value
            task["priority"] = TaskPriority.HIGH.value
            task["tags"].append("infrastructure")
        
        # Quality classification
        elif any(keyword in branch_lower for keyword in [
            "quality", "lint", "mypy", "test", "refactor", "cleanup", "debt"
        ]):
            task["type"] = TaskType.QUALITY.value
            task["priority"] = TaskPriority.MEDIUM.value
            task["tags"].append("quality")
        
        # Security classification
        elif any(keyword in branch_lower for keyword in [
            "security", "auth", "jwt", "vulnerability", "fix-cve"
        ]):
            task["type"] = TaskType.SECURITY.value
            task["priority"] = TaskPriority.HIGH.value
            task["tags"].append("security")
        
        # Feature classification (default)
        else:
            if any(keyword in branch_lower for keyword in [
                "feat", "feature", "add", "new", "implement"
            ]):
                task["type"] = TaskType.FEATURE.value
                task["tags"].append("feature")
        
        # Analyze commit subject for priority
        if any(keyword in subject_lower for keyword in [
            "critical", "urgent", "hotfix", "fix", "bug"
        ]):
            task["priority"] = TaskPriority.HIGH.value
        elif any(keyword in subject_lower for keyword in [
            "major", "important", "breaking"
        ]):
            task["priority"] = TaskPriority.HIGH.value
        elif any(keyword in subject_lower for keyword in [
            "minor", "docs", "typo", "style"
        ]):
            task["priority"] = TaskPriority.LOW.value
        
        # Estimate effort
        if any(keyword in subject_lower for keyword in [
            "major", "complete", "implement", "refactor"
        ]):
            task["estimated_effort"] = "high"
        elif any(keyword in subject_lower for keyword in [
            "fix", "update", "improve", "enhance"
        ]):
            task["estimated_effort"] = "medium"
        else:
            task["estimated_effort"] = "low"
        
        return task
    
    def _get_pr_tasks(self) -> List[Dict[str, Any]]:
        """Get tasks from open pull requests"""
        tasks = []
        
        try:
            result = subprocess.run([
                "gh", "pr", "list", "--json", "number,title,headRefName,createdAt,author"
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            if result.returncode == 0:
                prs = json.loads(result.stdout)
                
                for pr in prs:
                    task = self._classify_task(pr["headRefName"], pr["title"])
                    task.update({
                        "branch": pr["headRefName"],
                        "pr_number": pr["number"],
                        "title": pr["title"],
                        "created_at": pr["createdAt"],
                        "author": pr["author"]["login"],
                        "source": "pr"
                    })
                    tasks.append(task)
            
            return tasks
            
        except Exception as e:
            logger.warning(f"Failed to get PR tasks: {e}")
            return []
    
    def _assess_balance(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess current balance of task types"""
        # Count tasks by type
        task_counts = {}
        for task_type in TaskType:
            task_counts[task_type.value] = len([t for t in tasks if t["type"] == task_type.value])
        
        total_tasks = len(tasks)
        
        # Calculate current ratios
        current_ratios = {}
        for task_type, count in task_counts.items():
            current_ratios[task_type] = count / total_tasks if total_tasks > 0 else 0
        
        # Calculate deviation from ideal ratios
        deviations = {}
        for task_type in TaskType:
            ideal_ratio = self.balance_ratios.get(task_type, 0)
            current_ratio = current_ratios.get(task_type.value, 0)
            deviations[task_type.value] = current_ratio - ideal_ratio
        
        # Assess balance status
        balance_status = "balanced"
        if any(abs(dev) > 0.15 for dev in deviations.values()):
            balance_status = "imbalanced"
        
        return {
            "total_tasks": total_tasks,
            "task_counts": task_counts,
            "current_ratios": current_ratios,
            "ideal_ratios": {t.value: r for t, r in self.balance_ratios.items()},
            "deviations": deviations,
            "balance_status": balance_status
        }
    
    def _check_quality_gates(self) -> Dict[str, Any]:
        """Check current quality gate status"""
        quality_gates = {
            "status": "unknown",
            "gates": {},
            "blocking_issues": [],
            "recommendations": []
        }
        
        try:
            # Run quality gates
            result = subprocess.run([
                "python", "scripts/run_quality_gates.py", "--json"
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            if result.returncode == 0:
                gate_results = json.loads(result.stdout)
                quality_gates["status"] = "pass" if gate_results.get("success") else "fail"
                quality_gates["gates"] = gate_results.get("checks", {})
                
                # Check for blocking issues
                for gate_name, gate_result in quality_gates["gates"].items():
                    if not gate_result.get("passed", False):
                        quality_gates["blocking_issues"].append({
                            "gate": gate_name,
                            "errors": gate_result.get("errors", [])
                        })
                
                # Generate recommendations
                if quality_gates["status"] == "fail":
                    quality_gates["recommendations"].append("Quality gates are failing - prioritize quality improvements")
                
            else:
                quality_gates["status"] = "error"
                quality_gates["error"] = result.stderr
                
        except Exception as e:
            quality_gates["status"] = "error"
            quality_gates["error"] = str(e)
            
        return quality_gates
    
    def _identify_blocked_tasks(self, quality_gates: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify tasks that are blocked by quality gates"""
        blocked_tasks = []
        
        # If quality gates are failing, certain tasks should be blocked
        if quality_gates["status"] == "fail":
            blocking_issues = quality_gates.get("blocking_issues", [])
            
            for issue in blocking_issues:
                blocked_tasks.append({
                    "type": "quality_gate_failure",
                    "gate": issue["gate"],
                    "errors": issue["errors"],
                    "blocking_rule": "No new features or infrastructure changes until quality gates pass",
                    "allowed_tasks": ["quality", "security"]
                })
        
        return blocked_tasks
    
    def _generate_recommendations(self, balance_assessment: Dict[str, Any], 
                                quality_gates: Dict[str, Any], 
                                blocked_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate workflow recommendations"""
        recommendations = []
        
        # Balance recommendations
        deviations = balance_assessment["deviations"]
        
        for task_type, deviation in deviations.items():
            if deviation > 0.15:  # Too many tasks of this type
                recommendations.append({
                    "type": "balance_adjustment",
                    "priority": "medium",
                    "action": f"Reduce {task_type} tasks",
                    "reason": f"Current ratio {balance_assessment['current_ratios'][task_type]:.2f} exceeds ideal {self.balance_ratios.get(TaskType(task_type), 0):.2f}",
                    "suggested_action": f"Complete or deprioritize some {task_type} tasks"
                })
            elif deviation < -0.15:  # Too few tasks of this type
                recommendations.append({
                    "type": "balance_adjustment",
                    "priority": "medium",
                    "action": f"Increase {task_type} tasks",
                    "reason": f"Current ratio {balance_assessment['current_ratios'][task_type]:.2f} below ideal {self.balance_ratios.get(TaskType(task_type), 0):.2f}",
                    "suggested_action": f"Add more {task_type} tasks to the pipeline"
                })
        
        # Quality gate recommendations
        if quality_gates["status"] == "fail":
            recommendations.append({
                "type": "quality_gate_blocker",
                "priority": "critical",
                "action": "Fix quality gate failures",
                "reason": "Quality gates are blocking development progress",
                "suggested_action": "Prioritize quality improvements over new features"
            })
        
        # Blocked task recommendations
        if blocked_tasks:
            recommendations.append({
                "type": "unblock_tasks",
                "priority": "high",
                "action": "Unblock development tasks",
                "reason": f"{len(blocked_tasks)} tasks are currently blocked",
                "suggested_action": "Address blocking issues before proceeding with new work"
            })
        
        return recommendations
    
    def _prioritize_actions(self, recommendations: List[Dict[str, Any]], 
                           blocked_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize actions based on recommendations and blocked tasks"""
        priority_actions = []
        
        # Critical actions first
        critical_recs = [r for r in recommendations if r["priority"] == "critical"]
        for rec in critical_recs:
            priority_actions.append({
                "priority": 1,
                "action": rec["action"],
                "type": rec["type"],
                "deadline": "immediate",
                "estimated_effort": "high"
            })
        
        # High priority actions
        high_recs = [r for r in recommendations if r["priority"] == "high"]
        for rec in high_recs:
            priority_actions.append({
                "priority": 2,
                "action": rec["action"],
                "type": rec["type"],
                "deadline": "within_24_hours",
                "estimated_effort": "medium"
            })
        
        # Medium priority actions
        medium_recs = [r for r in recommendations if r["priority"] == "medium"]
        for rec in medium_recs:
            priority_actions.append({
                "priority": 3,
                "action": rec["action"],
                "type": rec["type"],
                "deadline": "within_week",
                "estimated_effort": "low"
            })
        
        return priority_actions
    
    def enforce_quality_gates(self) -> Dict[str, Any]:
        """Enforce quality gates as blockers"""
        logger.info("🛡️  Enforcing quality gates...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "quality_status": "unknown",
            "enforcement_actions": [],
            "blocked_operations": []
        }
        
        try:
            # Check quality gates
            quality_gates = self._check_quality_gates()
            results["quality_status"] = quality_gates["status"]
            
            if quality_gates["status"] == "fail":
                # Block certain operations
                blocked_operations = [
                    "feature_development",
                    "infrastructure_changes",
                    "merging_to_main"
                ]
                
                results["blocked_operations"] = blocked_operations
                
                # Take enforcement actions
                if not self.dry_run:
                    enforcement_actions = self._take_enforcement_actions(quality_gates)
                    results["enforcement_actions"] = enforcement_actions
                else:
                    results["enforcement_actions"] = [{"action": "dry_run", "status": "would_enforce"}]
                
                logger.warning(f"⚠️  Quality gates failing - blocking {len(blocked_operations)} operations")
            else:
                logger.info("✅ Quality gates passing - no enforcement needed")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Quality gate enforcement failed: {e}")
            results["error"] = str(e)
            return results
    
    def _take_enforcement_actions(self, quality_gates: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Take enforcement actions when quality gates fail"""
        actions = []
        
        # Create quality gate status file
        try:
            status_file = self.repo_path / ".quality_gate_status"
            status_data = {
                "status": "BLOCKED",
                "timestamp": datetime.now().isoformat(),
                "failing_gates": [issue["gate"] for issue in quality_gates.get("blocking_issues", [])],
                "message": "Development operations blocked due to quality gate failures"
            }
            
            with open(status_file, 'w') as f:
                json.dump(status_data, f, indent=2)
            
            actions.append({
                "action": "create_status_file",
                "status": "completed",
                "file": str(status_file)
            })
            
        except Exception as e:
            actions.append({
                "action": "create_status_file",
                "status": "failed",
                "error": str(e)
            })
        
        # Update pre-commit hooks if they exist
        try:
            hooks_dir = self.repo_path / ".githooks"
            if hooks_dir.exists():
                pre_commit_hook = hooks_dir / "pre-commit"
                if pre_commit_hook.exists():
                    # Add quality gate check to pre-commit hook
                    hook_content = pre_commit_hook.read_text()
                    if "quality_gate_check" not in hook_content:
                        hook_content += "\n# Quality gate enforcement\npython scripts/run_quality_gates.py || exit 1\n"
                        pre_commit_hook.write_text(hook_content)
                        
                        actions.append({
                            "action": "update_pre_commit_hook",
                            "status": "completed"
                        })
                        
        except Exception as e:
            actions.append({
                "action": "update_pre_commit_hook",
                "status": "failed",
                "error": str(e)
            })
        
        return actions


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Manage balanced workflow")
    parser.add_argument("--assess", action="store_true", help="Assess current workflow balance")
    parser.add_argument("--enforce", action="store_true", help="Enforce quality gates as blockers")
    parser.add_argument("--status", action="store_true", help="Show current workflow status")
    parser.add_argument("--dry-run", action="store_true", help="Don't take actions, just analyze")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--repo", default=".", help="Repository path")
    
    args = parser.parse_args()
    
    # Create workflow manager
    workflow = WorkflowBalance(args.repo, args.dry_run)
    
    if args.assess:
        results = workflow.assess_workflow_balance()
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("⚖️  Workflow Balance Assessment")
            print("==============================")
            print(f"📊 Total tasks: {results['balance_assessment']['total_tasks']}")
            print(f"🎯 Balance status: {results['balance_assessment']['balance_status']}")
            print(f"🛡️  Quality gates: {results['quality_gates']['status']}")
            print(f"🚫 Blocked tasks: {len(results['blocked_tasks'])}")
            print(f"📝 Recommendations: {len(results['recommendations'])}")
            
            if results["priority_actions"]:
                print("\n🚀 Priority Actions:")
                for action in results["priority_actions"][:3]:  # Show top 3
                    print(f"  {action['priority']}. {action['action']} ({action['deadline']})")
    
    elif args.enforce:
        results = workflow.enforce_quality_gates()
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("🛡️  Quality Gate Enforcement")
            print("============================")
            print(f"📊 Quality status: {results['quality_status']}")
            print(f"🚫 Blocked operations: {len(results.get('blocked_operations', []))}")
            print(f"⚡ Enforcement actions: {len(results.get('enforcement_actions', []))}")
    
    elif args.status:
        # Show current status
        results = workflow.assess_workflow_balance()
        
        print("📊 Current Workflow Status")
        print("==========================")
        print(f"Tasks: {results['balance_assessment']['total_tasks']}")
        print(f"Balance: {results['balance_assessment']['balance_status']}")
        print(f"Quality Gates: {results['quality_gates']['status']}")
        
        if results["priority_actions"]:
            print(f"Next Action: {results['priority_actions'][0]['action']}")
    
    else:
        parser.print_help()
        sys.exit(1)
    
    # Exit with appropriate code
    if "error" in results:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()