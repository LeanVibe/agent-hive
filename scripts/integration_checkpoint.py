#!/usr/bin/env python3
"""
Integration Checkpoint Script

Automatically checks for branch divergence and creates integration opportunities
to prevent valuable work from being lost in feature branches.
"""

import subprocess
import sys
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('.claude/logs/integration_checkpoint.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IntegrationCheckpoint:
    """Manages automated integration checkpoints"""
    
    def __init__(self, repo_path: str = ".", dry_run: bool = False):
        self.repo_path = Path(repo_path)
        self.dry_run = dry_run
        self.divergence_threshold = timedelta(hours=4)
        self.quality_threshold = 0.75  # 75% quality gate pass rate
        
    def run_checkpoint(self) -> Dict[str, Any]:
        """Run complete integration checkpoint"""
        logger.info("🔍 Starting integration checkpoint...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": self.dry_run,
            "branches_analyzed": [],
            "divergent_branches": [],
            "integration_opportunities": [],
            "quality_issues": [],
            "actions_taken": [],
            "recommendations": []
        }
        
        try:
            # 1. Analyze all branches
            branches = self._get_all_branches()
            results["branches_analyzed"] = branches
            
            # 2. Check for divergence
            divergent_branches = self._check_branch_divergence(branches)
            results["divergent_branches"] = divergent_branches
            
            # 3. Identify integration opportunities
            opportunities = self._identify_integration_opportunities(divergent_branches)
            results["integration_opportunities"] = opportunities
            
            # 4. Check quality gates
            quality_issues = self._check_quality_gates(divergent_branches)
            results["quality_issues"] = quality_issues
            
            # 5. Take automated actions
            actions = self._take_automated_actions(opportunities, quality_issues)
            results["actions_taken"] = actions
            
            # 6. Generate recommendations
            recommendations = self._generate_recommendations(results)
            results["recommendations"] = recommendations
            
            logger.info(f"✅ Integration checkpoint completed: {len(opportunities)} opportunities found")
            return results
            
        except Exception as e:
            logger.error(f"❌ Integration checkpoint failed: {e}")
            results["error"] = str(e)
            return results
    
    def _get_all_branches(self) -> List[Dict[str, Any]]:
        """Get all branches with metadata"""
        try:
            # Get all branches
            result = subprocess.run([
                "git", "branch", "-a", "--format=%(refname:short)|%(committerdate:iso)|%(upstream:short)|%(subject)"
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            branches = []
            for line in result.stdout.strip().split('\n'):
                if line and '|' in line:
                    parts = line.split('|', 3)
                    if len(parts) >= 3:
                        branch_info = {
                            "name": parts[0].strip(),
                            "last_commit": parts[1].strip(),
                            "upstream": parts[2].strip() if parts[2].strip() else None,
                            "subject": parts[3].strip() if len(parts) > 3 else ""
                        }
                        
                        # Skip remote tracking branches
                        if not branch_info["name"].startswith("origin/"):
                            branches.append(branch_info)
            
            return branches
            
        except Exception as e:
            logger.error(f"Failed to get branches: {e}")
            return []
    
    def _check_branch_divergence(self, branches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check which branches have diverged from main"""
        divergent_branches = []
        
        for branch in branches:
            if branch["name"] in ["main", "master"]:
                continue
            
            try:
                # Check last commit age
                last_commit_str = branch["last_commit"]
                # Handle timezone-aware datetimes
                if '+' in last_commit_str or last_commit_str.endswith('Z'):
                    # Parse timezone-aware datetime
                    last_commit = datetime.fromisoformat(last_commit_str.replace('Z', '+00:00'))
                    age = datetime.now().replace(tzinfo=last_commit.tzinfo) - last_commit
                else:
                    # Parse timezone-naive datetime
                    last_commit = datetime.fromisoformat(last_commit_str.replace(' ', 'T'))
                    age = datetime.now() - last_commit
                
                # Check commits ahead/behind main
                result = subprocess.run([
                    "git", "rev-list", "--count", f"main..{branch['name']}"
                ], cwd=self.repo_path, capture_output=True, text=True)
                
                commits_ahead = int(result.stdout.strip()) if result.returncode == 0 else 0
                
                result = subprocess.run([
                    "git", "rev-list", "--count", f"{branch['name']}..main"
                ], cwd=self.repo_path, capture_output=True, text=True)
                
                commits_behind = int(result.stdout.strip()) if result.returncode == 0 else 0
                
                # Check if diverged
                if age > self.divergence_threshold or commits_ahead > 0 or commits_behind > 5:
                    divergent_info = {
                        **branch,
                        "age_hours": age.total_seconds() / 3600,
                        "commits_ahead": commits_ahead,
                        "commits_behind": commits_behind,
                        "divergence_score": self._calculate_divergence_score(age, commits_ahead, commits_behind)
                    }
                    divergent_branches.append(divergent_info)
                    
            except Exception as e:
                logger.warning(f"Failed to check divergence for {branch['name']}: {e}")
                
        return divergent_branches
    
    def _calculate_divergence_score(self, age: timedelta, commits_ahead: int, commits_behind: int) -> float:
        """Calculate divergence score (0-1, higher = more divergent)"""
        age_score = min(age.total_seconds() / (24 * 3600), 1.0)  # Days to score
        ahead_score = min(commits_ahead / 10, 1.0)  # Commits ahead
        behind_score = min(commits_behind / 20, 1.0)  # Commits behind
        
        return (age_score * 0.4) + (ahead_score * 0.4) + (behind_score * 0.2)
    
    def _identify_integration_opportunities(self, divergent_branches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify branches that can be safely integrated"""
        opportunities = []
        
        for branch in divergent_branches:
            try:
                # Check if branch has improvements
                improvements = self._analyze_branch_improvements(branch["name"])
                
                if improvements["has_improvements"]:
                    opportunity = {
                        "branch": branch["name"],
                        "divergence_score": branch["divergence_score"],
                        "improvements": improvements,
                        "integration_risk": self._assess_integration_risk(branch["name"]),
                        "recommendation": self._get_integration_recommendation(branch, improvements)
                    }
                    opportunities.append(opportunity)
                    
            except Exception as e:
                logger.warning(f"Failed to analyze improvements for {branch['name']}: {e}")
                
        return opportunities
    
    def _analyze_branch_improvements(self, branch_name: str) -> Dict[str, Any]:
        """Analyze what improvements a branch contains"""
        try:
            # Get diff stats
            result = subprocess.run([
                "git", "diff", "--stat", f"main..{branch_name}"
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            diff_stats = result.stdout.strip()
            
            # Look for quality improvements
            quality_patterns = [
                "quality_gates", "mypy", "pylint", "test_", "requirements",
                "scripts/", "analysis_reports/", "validation", "security"
            ]
            
            has_quality_improvements = any(pattern in diff_stats.lower() for pattern in quality_patterns)
            
            # Get commit subjects
            result = subprocess.run([
                "git", "log", "--oneline", f"main..{branch_name}"
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            commits = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            improvements = {
                "has_improvements": bool(diff_stats and (has_quality_improvements or len(commits) > 0)),
                "has_quality_improvements": has_quality_improvements,
                "commit_count": len(commits),
                "commits": commits[:5],  # First 5 commits
                "diff_stats": diff_stats,
                "improvement_types": self._classify_improvements(diff_stats, commits)
            }
            
            return improvements
            
        except Exception as e:
            logger.error(f"Failed to analyze improvements for {branch_name}: {e}")
            return {"has_improvements": False, "error": str(e)}
    
    def _classify_improvements(self, diff_stats: str, commits: List[str]) -> List[str]:
        """Classify types of improvements in a branch"""
        improvement_types = []
        
        # Check diff stats
        if "test_" in diff_stats.lower():
            improvement_types.append("testing")
        if "quality_gates" in diff_stats.lower():
            improvement_types.append("quality_gates")
        if "mypy" in diff_stats.lower() or "pylint" in diff_stats.lower():
            improvement_types.append("type_checking")
        if "security" in diff_stats.lower():
            improvement_types.append("security")
        if "scripts/" in diff_stats.lower():
            improvement_types.append("automation")
        
        # Check commit messages
        commit_text = ' '.join(commits).lower()
        if "fix" in commit_text:
            improvement_types.append("bug_fixes")
        if "feat" in commit_text:
            improvement_types.append("features")
        if "refactor" in commit_text:
            improvement_types.append("refactoring")
        if "docs" in commit_text:
            improvement_types.append("documentation")
        
        return improvement_types
    
    def _assess_integration_risk(self, branch_name: str) -> str:
        """Assess risk of integrating a branch"""
        try:
            # Check for merge conflicts
            result = subprocess.run([
                "git", "merge-tree", f"$(git merge-base main {branch_name})", "main", branch_name
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            has_conflicts = bool(result.stdout.strip())
            
            # Check file change scope
            result = subprocess.run([
                "git", "diff", "--name-only", f"main..{branch_name}"
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            # Assess risk
            if has_conflicts:
                return "high"
            elif len(changed_files) > 20:
                return "medium"
            elif any("core" in f or "main" in f for f in changed_files):
                return "medium"
            else:
                return "low"
                
        except Exception as e:
            logger.warning(f"Failed to assess integration risk for {branch_name}: {e}")
            return "unknown"
    
    def _get_integration_recommendation(self, branch: Dict[str, Any], improvements: Dict[str, Any]) -> str:
        """Get recommendation for branch integration"""
        if improvements["has_quality_improvements"]:
            if branch["divergence_score"] > 0.8:
                return "urgent_integration"
            elif branch["divergence_score"] > 0.5:
                return "recommend_integration"
            else:
                return "monitor"
        else:
            if branch["divergence_score"] > 0.9:
                return "consider_cleanup"
            else:
                return "monitor"
    
    def _check_quality_gates(self, branches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check quality gates for divergent branches"""
        quality_issues = []
        
        for branch in branches:
            try:
                # Check if quality gates exist and are up to date
                quality_issue = {
                    "branch": branch["name"],
                    "has_quality_config": False,
                    "quality_score": 0.0,
                    "needs_update": False
                }
                
                # Check for quality gate configuration
                config_path = self.repo_path / ".quality-gates.json"
                if config_path.exists():
                    quality_issue["has_quality_config"] = True
                    
                    # Try to run quality gates if not dry run
                    if not self.dry_run:
                        try:
                            result = subprocess.run([
                                "python", "scripts/run_quality_gates.py", "--json"
                            ], cwd=self.repo_path, capture_output=True, text=True)
                            
                            if result.returncode == 0:
                                quality_data = json.loads(result.stdout)
                                quality_issue["quality_score"] = quality_data.get("summary", {}).get("success_rate", 0.0)
                        except Exception as e:
                            logger.warning(f"Failed to run quality gates for {branch['name']}: {e}")
                
                if quality_issue["quality_score"] < self.quality_threshold:
                    quality_issues.append(quality_issue)
                    
            except Exception as e:
                logger.warning(f"Failed to check quality gates for {branch['name']}: {e}")
                
        return quality_issues
    
    def _take_automated_actions(self, opportunities: List[Dict[str, Any]], quality_issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Take automated actions based on analysis"""
        actions = []
        
        for opportunity in opportunities:
            if opportunity["integration_risk"] == "low" and opportunity["recommendation"] == "urgent_integration":
                action = {
                    "type": "create_integration_pr",
                    "branch": opportunity["branch"],
                    "status": "pending"
                }
                
                if not self.dry_run:
                    try:
                        # Create integration PR
                        pr_created = self._create_integration_pr(opportunity)
                        action["status"] = "completed" if pr_created else "failed"
                        action["pr_url"] = pr_created if pr_created else None
                    except Exception as e:
                        action["status"] = "failed"
                        action["error"] = str(e)
                
                actions.append(action)
            
            elif opportunity["recommendation"] == "recommend_integration":
                action = {
                    "type": "notify_developers",
                    "branch": opportunity["branch"],
                    "message": f"Branch {opportunity['branch']} has valuable improvements and should be integrated"
                }
                
                if not self.dry_run:
                    self._notify_developers(action["message"])
                    action["status"] = "completed"
                else:
                    action["status"] = "dry_run"
                
                actions.append(action)
        
        return actions
    
    def _create_integration_pr(self, opportunity: Dict[str, Any]) -> Optional[str]:
        """Create an integration PR for safe opportunities"""
        try:
            branch_name = opportunity["branch"]
            
            # Create PR using gh CLI if available
            pr_title = f"chore: Integrate improvements from {branch_name}"
            pr_body = f"""
## Automated Integration PR

This PR integrates improvements from branch `{branch_name}` that were identified by the integration checkpoint system.

### Improvements Identified:
- **Improvement Types**: {', '.join(opportunity['improvements']['improvement_types'])}
- **Commits**: {opportunity['improvements']['commit_count']} commits
- **Risk Level**: {opportunity['integration_risk']}

### Integration Analysis:
- **Divergence Score**: {opportunity['divergence_score']:.2f}
- **Recommendation**: {opportunity['recommendation']}

### Quality Gate Status:
Will be validated after merge.

---
*This PR was created automatically by the integration checkpoint system.*
"""
            
            result = subprocess.run([
                "gh", "pr", "create",
                "--title", pr_title,
                "--body", pr_body,
                "--head", branch_name,
                "--base", "main"
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Extract PR URL from output
                pr_url = result.stdout.strip()
                logger.info(f"✅ Created integration PR: {pr_url}")
                return pr_url
            else:
                logger.error(f"Failed to create PR: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create integration PR: {e}")
            return None
    
    def _notify_developers(self, message: str):
        """Notify developers of integration opportunities"""
        try:
            # Log the notification
            logger.info(f"📢 Notification: {message}")
            
            # Could integrate with Slack, email, etc. here
            # For now, just write to a notifications file
            notifications_file = self.repo_path / ".claude/logs/integration_notifications.log"
            notifications_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(notifications_file, 'a') as f:
                f.write(f"{datetime.now().isoformat()}: {message}\n")
                
        except Exception as e:
            logger.error(f"Failed to notify developers: {e}")
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Branch divergence recommendations
        if results["divergent_branches"]:
            high_divergence = [b for b in results["divergent_branches"] if b["divergence_score"] > 0.8]
            if high_divergence:
                recommendations.append(f"🚨 {len(high_divergence)} branches have high divergence scores - consider immediate integration")
        
        # Integration opportunities
        if results["integration_opportunities"]:
            urgent = [o for o in results["integration_opportunities"] if o["recommendation"] == "urgent_integration"]
            if urgent:
                recommendations.append(f"⚡ {len(urgent)} branches need urgent integration")
        
        # Quality issues
        if results["quality_issues"]:
            recommendations.append(f"📊 {len(results['quality_issues'])} branches have quality gate issues")
        
        # General recommendations
        if len(results["divergent_branches"]) > 5:
            recommendations.append("🔄 Consider more frequent integration cycles")
        
        return recommendations


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run integration checkpoint")
    parser.add_argument("--dry-run", action="store_true", help="Don't take actions, just analyze")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--repo", default=".", help="Repository path")
    
    args = parser.parse_args()
    
    # Run checkpoint
    checkpoint = IntegrationCheckpoint(args.repo, args.dry_run)
    results = checkpoint.run_checkpoint()
    
    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"🔍 Integration Checkpoint Results")
        print(f"=====================================")
        print(f"📊 Branches analyzed: {len(results['branches_analyzed'])}")
        print(f"🔄 Divergent branches: {len(results['divergent_branches'])}")
        print(f"⚡ Integration opportunities: {len(results['integration_opportunities'])}")
        print(f"📈 Actions taken: {len(results['actions_taken'])}")
        
        if results["recommendations"]:
            print("\n📝 Recommendations:")
            for rec in results["recommendations"]:
                print(f"  • {rec}")
        
        if results.get("error"):
            print(f"\n❌ Error: {results['error']}")
            sys.exit(1)
    
    # Exit with appropriate code
    sys.exit(0 if not results.get("error") else 1)


if __name__ == "__main__":
    main()