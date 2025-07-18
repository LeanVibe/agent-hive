#!/usr/bin/env python3
"""
Secure Integration Checkpoint Script

Security-hardened version of the integration checkpoint system with
comprehensive input validation and safe subprocess operations.
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
import re
from dataclasses import dataclass, asdict
from enum import Enum

# Import secure git operations
from secure_git_operations import SecureGitOperations, GitOperationError, SecurityError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('.claude/logs/secure_integration_checkpoint.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IntegrationRisk(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class IntegrationRecommendation(Enum):
    URGENT_INTEGRATION = "urgent_integration"
    RECOMMEND_INTEGRATION = "recommend_integration"
    MONITOR = "monitor"
    CONSIDER_CLEANUP = "consider_cleanup"

@dataclass
class BranchInfo:
    """Structured branch information"""
    name: str
    last_commit: str
    subject: str
    age_hours: float
    commits_ahead: int
    commits_behind: int
    divergence_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ImprovementInfo:
    """Structured improvement information"""
    has_improvements: bool
    has_quality_improvements: bool
    commit_count: int
    improvement_types: List[str]
    commits: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class IntegrationOpportunity:
    """Structured integration opportunity"""
    branch: str
    divergence_score: float
    improvements: ImprovementInfo
    integration_risk: IntegrationRisk
    recommendation: IntegrationRecommendation
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['integration_risk'] = self.integration_risk.value
        result['recommendation'] = self.recommendation.value
        return result

class SecureIntegrationCheckpoint:
    """Security-hardened integration checkpoint manager"""
    
    def __init__(self, repo_path: str = ".", dry_run: bool = False):
        self.repo_path = Path(repo_path).resolve()
        self.dry_run = dry_run
        self.divergence_threshold = timedelta(hours=4)
        self.quality_threshold = 0.75
        
        # Initialize secure git operations
        try:
            self.git_ops = SecureGitOperations(self.repo_path)
            logger.info("✅ Secure git operations initialized")
        except (GitOperationError, SecurityError) as e:
            logger.error(f"❌ Failed to initialize secure git operations: {e}")
            raise
        
        # Validate input parameters
        self._validate_parameters()
    
    def _validate_parameters(self):
        """Validate initialization parameters"""
        if not isinstance(self.dry_run, bool):
            raise SecurityError("dry_run must be boolean")
        
        if not isinstance(self.quality_threshold, (int, float)) or not (0 <= self.quality_threshold <= 1):
            raise SecurityError("quality_threshold must be between 0 and 1")
        
        if not isinstance(self.divergence_threshold, timedelta):
            raise SecurityError("divergence_threshold must be timedelta")
    
    def run_checkpoint(self) -> Dict[str, Any]:
        """Run complete integration checkpoint with security validation"""
        logger.info("🔍 Starting secure integration checkpoint...")
        
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": self.dry_run,
            "security_mode": "enabled",
            "branches_analyzed": [],
            "divergent_branches": [],
            "integration_opportunities": [],
            "quality_issues": [],
            "actions_taken": [],
            "recommendations": []
        }
        
        try:
            # 1. Validate environment
            self._validate_environment()
            
            # 2. Analyze all branches
            branches = self._analyze_branches()
            results["branches_analyzed"] = [branch.to_dict() for branch in branches]
            
            # 3. Check for divergence
            divergent_branches = self._check_branch_divergence(branches)
            results["divergent_branches"] = [branch.to_dict() for branch in divergent_branches]
            
            # 4. Identify integration opportunities
            opportunities = self._identify_integration_opportunities(divergent_branches)
            results["integration_opportunities"] = [opp.to_dict() for opp in opportunities]
            
            # 5. Check quality gates
            quality_issues = self._check_quality_gates(divergent_branches)
            results["quality_issues"] = quality_issues
            
            # 6. Take automated actions
            actions = self._take_automated_actions(opportunities, quality_issues)
            results["actions_taken"] = actions
            
            # 7. Generate recommendations
            recommendations = self._generate_recommendations(results)
            results["recommendations"] = recommendations
            
            logger.info(f"✅ Secure integration checkpoint completed: {len(opportunities)} opportunities found")
            return results
            
        except Exception as e:
            logger.error(f"❌ Secure integration checkpoint failed: {e}")
            results["error"] = str(e)
            return results
    
    def _validate_environment(self):
        """Validate the operating environment"""
        # Check repository state
        try:
            status = self.git_ops.get_status()
            logger.debug(f"Repository status: {len(status.split()) if status else 0} changes")
        except GitOperationError as e:
            raise SecurityError(f"Repository validation failed: {e}")
        
        # Check required directories
        required_dirs = ['.claude/logs', 'scripts']
        for dir_path in required_dirs:
            full_path = self.repo_path / dir_path
            if not full_path.exists():
                logger.warning(f"Creating missing directory: {dir_path}")
                full_path.mkdir(parents=True, exist_ok=True)
    
    def _analyze_branches(self) -> List[BranchInfo]:
        """Analyze all branches with secure operations"""
        try:
            branch_data = self.git_ops.get_branch_info()
            branches = []
            
            for branch_dict in branch_data:
                name = branch_dict['name']
                
                # Skip remote tracking branches and main
                if name.startswith('origin/') or name in ['main', 'master']:
                    continue
                
                try:
                    branch_info = self._create_branch_info(branch_dict)
                    branches.append(branch_info)
                except Exception as e:
                    logger.warning(f"Failed to analyze branch {name}: {e}")
            
            return branches
            
        except GitOperationError as e:
            logger.error(f"Failed to analyze branches: {e}")
            return []
    
    def _create_branch_info(self, branch_dict: Dict[str, str]) -> BranchInfo:
        """Create structured branch information"""
        name = branch_dict['name']
        last_commit_str = branch_dict['last_commit']
        subject = branch_dict['subject']
        
        # Parse commit date safely
        try:
            if '+' in last_commit_str or last_commit_str.endswith('Z'):
                last_commit = datetime.fromisoformat(last_commit_str.replace('Z', '+00:00'))
                age = datetime.now(timezone.utc) - last_commit
            else:
                last_commit = datetime.fromisoformat(last_commit_str.replace(' ', 'T'))
                age = datetime.now() - last_commit
        except ValueError as e:
            logger.warning(f"Failed to parse commit date for {name}: {e}")
            age = timedelta(0)
        
        # Get commits ahead/behind safely
        try:
            commits_ahead = self.git_ops.get_commit_count(f"main..{name}")
            commits_behind = self.git_ops.get_commit_count(f"{name}..main")
        except GitOperationError as e:
            logger.warning(f"Failed to get commit counts for {name}: {e}")
            commits_ahead = 0
            commits_behind = 0
        
        # Calculate divergence score
        divergence_score = self._calculate_divergence_score(age, commits_ahead, commits_behind)
        
        return BranchInfo(
            name=name,
            last_commit=last_commit_str,
            subject=subject,
            age_hours=age.total_seconds() / 3600,
            commits_ahead=commits_ahead,
            commits_behind=commits_behind,
            divergence_score=divergence_score
        )
    
    def _calculate_divergence_score(self, age: timedelta, commits_ahead: int, commits_behind: int) -> float:
        """Calculate divergence score with validation"""
        # Validate inputs
        if not isinstance(age, timedelta):
            return 0.0
        if not isinstance(commits_ahead, int) or commits_ahead < 0:
            commits_ahead = 0
        if not isinstance(commits_behind, int) or commits_behind < 0:
            commits_behind = 0
        
        # Calculate component scores
        age_score = min(age.total_seconds() / (24 * 3600), 1.0)
        ahead_score = min(commits_ahead / 10, 1.0)
        behind_score = min(commits_behind / 20, 1.0)
        
        # Weighted combination
        return (age_score * 0.4) + (ahead_score * 0.4) + (behind_score * 0.2)
    
    def _check_branch_divergence(self, branches: List[BranchInfo]) -> List[BranchInfo]:
        """Check which branches have diverged from main"""
        divergent_branches = []
        
        for branch in branches:
            age = timedelta(hours=branch.age_hours)
            
            # Check if diverged based on age, commits ahead, or commits behind
            if (age > self.divergence_threshold or 
                branch.commits_ahead > 0 or 
                branch.commits_behind > 5):
                divergent_branches.append(branch)
        
        return divergent_branches
    
    def _identify_integration_opportunities(self, divergent_branches: List[BranchInfo]) -> List[IntegrationOpportunity]:
        """Identify branches that can be safely integrated"""
        opportunities = []
        
        for branch in divergent_branches:
            try:
                # Analyze branch improvements
                improvements = self._analyze_branch_improvements(branch.name)
                
                if improvements.has_improvements:
                    # Assess integration risk
                    integration_risk = self._assess_integration_risk(branch.name)
                    
                    # Get recommendation
                    recommendation = self._get_integration_recommendation(branch, improvements, integration_risk)
                    
                    opportunity = IntegrationOpportunity(
                        branch=branch.name,
                        divergence_score=branch.divergence_score,
                        improvements=improvements,
                        integration_risk=integration_risk,
                        recommendation=recommendation
                    )
                    opportunities.append(opportunity)
                    
            except Exception as e:
                logger.warning(f"Failed to analyze improvements for {branch.name}: {e}")
        
        return opportunities
    
    def _analyze_branch_improvements(self, branch_name: str) -> ImprovementInfo:
        """Analyze what improvements a branch contains"""
        try:
            # Get diff stats safely
            diff_stats = self.git_ops.get_diff_stats(f"main..{branch_name}")
            
            # Get commit log safely
            commits = self._get_branch_commits(branch_name)
            
            # Look for quality improvements
            quality_patterns = [
                "quality_gates", "mypy", "pylint", "test_", "requirements",
                "scripts/", "analysis_reports/", "validation", "security"
            ]
            
            has_quality_improvements = any(
                pattern in diff_stats.lower() for pattern in quality_patterns
            )
            
            # Classify improvements
            improvement_types = self._classify_improvements(diff_stats, commits)
            
            return ImprovementInfo(
                has_improvements=bool(diff_stats and (has_quality_improvements or len(commits) > 0)),
                has_quality_improvements=has_quality_improvements,
                commit_count=len(commits),
                improvement_types=improvement_types,
                commits=commits[:5]  # First 5 commits
            )
            
        except GitOperationError as e:
            logger.warning(f"Failed to analyze improvements for {branch_name}: {e}")
            return ImprovementInfo(
                has_improvements=False,
                has_quality_improvements=False,
                commit_count=0,
                improvement_types=[],
                commits=[]
            )
    
    def _get_branch_commits(self, branch_name: str) -> List[str]:
        """Get commits for a branch safely"""
        try:
            # Use git log to get commits
            result = subprocess.run([
                'git', 'log', '--oneline', f'main..{branch_name}'
            ], cwd=self.repo_path, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            else:
                return []
                
        except (subprocess.TimeoutExpired, Exception) as e:
            logger.warning(f"Failed to get commits for {branch_name}: {e}")
            return []
    
    def _classify_improvements(self, diff_stats: str, commits: List[str]) -> List[str]:
        """Classify types of improvements in a branch"""
        improvement_types = []
        
        # Check diff stats
        diff_lower = diff_stats.lower()
        if "test_" in diff_lower:
            improvement_types.append("testing")
        if "quality_gates" in diff_lower:
            improvement_types.append("quality_gates")
        if "mypy" in diff_lower or "pylint" in diff_lower:
            improvement_types.append("type_checking")
        if "security" in diff_lower:
            improvement_types.append("security")
        if "scripts/" in diff_lower:
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
    
    def _assess_integration_risk(self, branch_name: str) -> IntegrationRisk:
        """Assess risk of integrating a branch"""
        try:
            # Check for merge conflicts
            has_conflicts = self.git_ops.check_merge_conflicts("main", branch_name)
            
            if has_conflicts:
                return IntegrationRisk.HIGH
            
            # Check file change scope
            diff_stats = self.git_ops.get_diff_stats(f"main..{branch_name}")
            changed_files = len(diff_stats.split('\n')) if diff_stats else 0
            
            # Assess based on scope
            if changed_files > 20:
                return IntegrationRisk.MEDIUM
            elif any(keyword in diff_stats.lower() for keyword in ["core", "main", "critical"]):
                return IntegrationRisk.MEDIUM
            else:
                return IntegrationRisk.LOW
                
        except GitOperationError as e:
            logger.warning(f"Failed to assess integration risk for {branch_name}: {e}")
            return IntegrationRisk.HIGH  # Conservative default
    
    def _get_integration_recommendation(self, branch: BranchInfo, improvements: ImprovementInfo, 
                                      integration_risk: IntegrationRisk) -> IntegrationRecommendation:
        """Get recommendation for branch integration"""
        if improvements.has_quality_improvements:
            if branch.divergence_score > 0.8:
                return IntegrationRecommendation.URGENT_INTEGRATION
            elif branch.divergence_score > 0.5:
                return IntegrationRecommendation.RECOMMEND_INTEGRATION
            else:
                return IntegrationRecommendation.MONITOR
        else:
            if branch.divergence_score > 0.9:
                return IntegrationRecommendation.CONSIDER_CLEANUP
            else:
                return IntegrationRecommendation.MONITOR
    
    def _check_quality_gates(self, branches: List[BranchInfo]) -> List[Dict[str, Any]]:
        """Check quality gates for divergent branches"""
        quality_issues = []
        
        for branch in branches:
            try:
                quality_issue = {
                    "branch": branch.name,
                    "has_quality_config": False,
                    "quality_score": 0.0,
                    "needs_update": False
                }
                
                # Check for quality gate configuration
                config_path = self.repo_path / ".quality-gates.json"
                if config_path.exists():
                    quality_issue["has_quality_config"] = True
                    
                    # Run quality gates if not dry run
                    if not self.dry_run:
                        try:
                            quality_score = self._run_quality_gates()
                            quality_issue["quality_score"] = quality_score
                        except Exception as e:
                            logger.warning(f"Failed to run quality gates for {branch.name}: {e}")
                
                if quality_issue["quality_score"] < self.quality_threshold:
                    quality_issues.append(quality_issue)
                    
            except Exception as e:
                logger.warning(f"Failed to check quality gates for {branch.name}: {e}")
        
        return quality_issues
    
    def _run_quality_gates(self) -> float:
        """Run quality gates and return score"""
        try:
            result = subprocess.run([
                sys.executable, "scripts/run_quality_gates.py", "--json"
            ], cwd=self.repo_path, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                quality_data = json.loads(result.stdout)
                return float(quality_data.get("summary", {}).get("success_rate", 0.0))
            else:
                return 0.0
                
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to run quality gates: {e}")
            return 0.0
    
    def _take_automated_actions(self, opportunities: List[IntegrationOpportunity], 
                               quality_issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Take automated actions based on analysis"""
        actions = []
        
        for opportunity in opportunities:
            if (opportunity.integration_risk == IntegrationRisk.LOW and 
                opportunity.recommendation == IntegrationRecommendation.URGENT_INTEGRATION):
                
                action = {
                    "type": "create_integration_pr",
                    "branch": opportunity.branch,
                    "status": "pending",
                    "dry_run": self.dry_run
                }
                
                if not self.dry_run:
                    try:
                        pr_url = self._create_integration_pr(opportunity)
                        action["status"] = "completed" if pr_url else "failed"
                        action["pr_url"] = pr_url
                    except Exception as e:
                        action["status"] = "failed"
                        action["error"] = str(e)
                else:
                    action["status"] = "dry_run"
                
                actions.append(action)
        
        return actions
    
    def _create_integration_pr(self, opportunity: IntegrationOpportunity) -> Optional[str]:
        """Create an integration PR for safe opportunities"""
        try:
            # Validate branch name
            if not re.match(r'^[a-zA-Z0-9/_\-\.]+$', opportunity.branch):
                raise SecurityError(f"Invalid branch name: {opportunity.branch}")
            
            # Create PR using gh CLI with safe parameters
            pr_title = f"chore: Integrate improvements from {opportunity.branch}"
            pr_body = f"""
## Automated Integration PR

This PR integrates improvements from branch `{opportunity.branch}` identified by the secure integration checkpoint system.

### Improvements Identified:
- **Improvement Types**: {', '.join(opportunity.improvements.improvement_types)}
- **Commits**: {opportunity.improvements.commit_count} commits
- **Risk Level**: {opportunity.integration_risk.value}

### Integration Analysis:
- **Divergence Score**: {opportunity.divergence_score:.2f}
- **Recommendation**: {opportunity.recommendation.value}

### Security:
- All operations performed with input validation
- Branch name validated against security patterns
- No command injection risks

---
*This PR was created automatically by the secure integration checkpoint system.*
"""
            
            # Use subprocess safely
            result = subprocess.run([
                "gh", "pr", "create",
                "--title", pr_title,
                "--body", pr_body,
                "--head", opportunity.branch,
                "--base", "main"
            ], cwd=self.repo_path, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                pr_url = result.stdout.strip()
                logger.info(f"✅ Created integration PR: {pr_url}")
                return pr_url
            else:
                logger.error(f"Failed to create PR: {result.stderr}")
                return None
                
        except (subprocess.TimeoutExpired, Exception) as e:
            logger.error(f"Failed to create integration PR: {e}")
            return None
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Security recommendations
        recommendations.append("🔒 Security: All operations validated and sanitized")
        
        # Branch divergence recommendations
        if results["divergent_branches"]:
            high_divergence = [b for b in results["divergent_branches"] if b["divergence_score"] > 0.8]
            if high_divergence:
                recommendations.append(f"🚨 {len(high_divergence)} branches have high divergence scores")
        
        # Integration opportunities
        if results["integration_opportunities"]:
            urgent = [o for o in results["integration_opportunities"] if o["recommendation"] == "urgent_integration"]
            if urgent:
                recommendations.append(f"⚡ {len(urgent)} branches need urgent integration")
        
        return recommendations


def main():
    """Main entry point with security validation"""
    parser = argparse.ArgumentParser(description="Run secure integration checkpoint")
    parser.add_argument("--dry-run", action="store_true", help="Don't take actions, just analyze")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--repo", default=".", help="Repository path")
    
    args = parser.parse_args()
    
    # Validate arguments
    if not os.path.exists(args.repo):
        print(f"❌ Repository path does not exist: {args.repo}")
        sys.exit(1)
    
    try:
        # Run secure checkpoint
        checkpoint = SecureIntegrationCheckpoint(args.repo, args.dry_run)
        results = checkpoint.run_checkpoint()
        
        # Output results
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"🔍 Secure Integration Checkpoint Results")
            print(f"========================================")
            print(f"🔒 Security mode: enabled")
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
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()