#!/usr/bin/env python3
"""
Quality Gate Synchronization Script

Automatically synchronizes quality gate improvements across branches
to ensure consistent quality standards throughout the development process.
"""

import subprocess
import sys
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse
import logging
import hashlib
import difflib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('.claude/logs/quality_gate_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class QualityGateSync:
    """Manages quality gate synchronization across branches"""
    
    def __init__(self, repo_path: str = ".", dry_run: bool = False):
        self.repo_path = Path(repo_path)
        self.dry_run = dry_run
        self.quality_files = [
            ".quality-gates.json",
            "scripts/run_quality_gates.py",
            "scripts/quality_gate_validation.py",
            ".flake8",
            ".mypy.ini",
            "pyproject.toml",
            "requirements-dev.txt"
        ]
        
    def run_sync(self) -> Dict[str, Any]:
        """Run complete quality gate synchronization"""
        logger.info("🔄 Starting quality gate synchronization...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": self.dry_run,
            "branches_analyzed": [],
            "quality_improvements": [],
            "sync_actions": [],
            "conflicts": [],
            "summary": {}
        }
        
        try:
            # 1. Analyze all branches for quality configurations
            branches = self._get_branches_with_quality_configs()
            results["branches_analyzed"] = branches
            
            # 2. Identify quality improvements
            improvements = self._identify_quality_improvements(branches)
            results["quality_improvements"] = improvements
            
            # 3. Sync improvements across branches
            sync_actions = self._sync_quality_improvements(improvements)
            results["sync_actions"] = sync_actions
            
            # 4. Handle conflicts
            conflicts = self._handle_conflicts(sync_actions)
            results["conflicts"] = conflicts
            
            # 5. Generate summary
            summary = self._generate_summary(results)
            results["summary"] = summary
            
            logger.info(f"✅ Quality gate sync completed: {len(improvements)} improvements synced")
            return results
            
        except Exception as e:
            logger.error(f"❌ Quality gate sync failed: {e}")
            results["error"] = str(e)
            return results
    
    def _get_branches_with_quality_configs(self) -> List[Dict[str, Any]]:
        """Get all branches with quality configurations"""
        branches = []
        
        try:
            # Get all branches
            result = subprocess.run([
                "git", "branch", "-a", "--format=%(refname:short)"
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            all_branches = [
                b.strip() for b in result.stdout.strip().split('\n') 
                if b.strip() and not b.strip().startswith("origin/")
            ]
            
            for branch in all_branches:
                if branch in ["main", "master"]:
                    continue
                    
                try:
                    # Check if branch has quality configurations
                    quality_config = self._analyze_branch_quality_config(branch)
                    if quality_config["has_quality_files"]:
                        branches.append({
                            "name": branch,
                            "quality_config": quality_config
                        })
                        
                except Exception as e:
                    logger.warning(f"Failed to analyze quality config for {branch}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to get branches: {e}")
            
        return branches
    
    def _analyze_branch_quality_config(self, branch_name: str) -> Dict[str, Any]:
        """Analyze quality configuration for a specific branch"""
        config = {
            "has_quality_files": False,
            "quality_files": {},
            "quality_scores": {},
            "last_updated": None
        }
        
        try:
            # Check each quality file
            for quality_file in self.quality_files:
                file_info = self._get_file_info_from_branch(branch_name, quality_file)
                if file_info:
                    config["quality_files"][quality_file] = file_info
                    config["has_quality_files"] = True
            
            # Get quality scores if available
            if config["has_quality_files"]:
                scores = self._get_quality_scores_from_branch(branch_name)
                config["quality_scores"] = scores
                
                # Get last update time
                config["last_updated"] = self._get_last_quality_update(branch_name)
            
            return config
            
        except Exception as e:
            logger.warning(f"Failed to analyze quality config for {branch_name}: {e}")
            return config
    
    def _get_file_info_from_branch(self, branch_name: str, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file information from a specific branch"""
        try:
            # Check if file exists in branch
            result = subprocess.run([
                "git", "show", f"{branch_name}:{file_path}"
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            if result.returncode == 0:
                content = result.stdout
                return {
                    "path": file_path,
                    "content": content,
                    "hash": hashlib.sha256(content.encode()).hexdigest(),
                    "size": len(content)
                }
            else:
                return None
                
        except Exception as e:
            logger.warning(f"Failed to get file info for {file_path} from {branch_name}: {e}")
            return None
    
    def _get_quality_scores_from_branch(self, branch_name: str) -> Dict[str, Any]:
        """Get quality scores from a branch"""
        try:
            # Switch to branch temporarily to run quality gates
            current_branch = subprocess.run([
                "git", "rev-parse", "--abbrev-ref", "HEAD"
            ], cwd=self.repo_path, capture_output=True, text=True).stdout.strip()
            
            if not self.dry_run:
                # Switch to target branch
                subprocess.run([
                    "git", "checkout", branch_name
                ], cwd=self.repo_path, capture_output=True, text=True)
                
                try:
                    # Run quality gates
                    result = subprocess.run([
                        "python", "scripts/run_quality_gates.py", "--json"
                    ], cwd=self.repo_path, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        return json.loads(result.stdout)
                    else:
                        return {"error": "Failed to run quality gates"}
                        
                finally:
                    # Switch back to original branch
                    subprocess.run([
                        "git", "checkout", current_branch
                    ], cwd=self.repo_path, capture_output=True, text=True)
            
            return {"dry_run": True}
            
        except Exception as e:
            logger.warning(f"Failed to get quality scores from {branch_name}: {e}")
            return {"error": str(e)}
    
    def _get_last_quality_update(self, branch_name: str) -> Optional[str]:
        """Get last update time for quality files in a branch"""
        try:
            quality_file_paths = " ".join(self.quality_files)
            result = subprocess.run([
                "git", "log", "-1", "--format=%ai", branch_name, "--", *self.quality_files
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            else:
                return None
                
        except Exception as e:
            logger.warning(f"Failed to get last quality update for {branch_name}: {e}")
            return None
    
    def _identify_quality_improvements(self, branches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify quality improvements across branches"""
        improvements = []
        
        # Get main branch quality config for comparison
        main_config = self._analyze_branch_quality_config("main")
        
        for branch in branches:
            branch_config = branch["quality_config"]
            
            # Compare each quality file
            for file_path, file_info in branch_config["quality_files"].items():
                main_file_info = main_config["quality_files"].get(file_path)
                
                if not main_file_info:
                    # New quality file
                    improvements.append({
                        "type": "new_file",
                        "file_path": file_path,
                        "source_branch": branch["name"],
                        "target_branch": "main",
                        "content": file_info["content"],
                        "priority": "high"
                    })
                    
                elif file_info["hash"] != main_file_info["hash"]:
                    # Modified quality file
                    improvement = self._analyze_file_improvement(
                        file_path, main_file_info, file_info, branch["name"]
                    )
                    if improvement:
                        improvements.append(improvement)
            
            # Compare quality scores
            if branch_config["quality_scores"] and main_config["quality_scores"]:
                score_improvement = self._analyze_score_improvement(
                    main_config["quality_scores"], 
                    branch_config["quality_scores"],
                    branch["name"]
                )
                if score_improvement:
                    improvements.append(score_improvement)
        
        return improvements
    
    def _analyze_file_improvement(self, file_path: str, main_file: Dict[str, Any], 
                                 branch_file: Dict[str, Any], branch_name: str) -> Optional[Dict[str, Any]]:
        """Analyze if a file change represents an improvement"""
        try:
            # Generate diff
            diff = list(difflib.unified_diff(
                main_file["content"].splitlines(keepends=True),
                branch_file["content"].splitlines(keepends=True),
                fromfile=f"main:{file_path}",
                tofile=f"{branch_name}:{file_path}"
            ))
            
            # Analyze diff for improvements
            improvement_indicators = [
                "min_coverage", "max_complexity", "quality_gates",
                "pylint", "mypy", "flake8", "test", "security"
            ]
            
            added_lines = [line for line in diff if line.startswith('+')]
            has_improvements = any(
                indicator in line.lower() for line in added_lines 
                for indicator in improvement_indicators
            )
            
            if has_improvements:
                return {
                    "type": "file_improvement",
                    "file_path": file_path,
                    "source_branch": branch_name,
                    "target_branch": "main",
                    "diff": ''.join(diff),
                    "priority": self._assess_improvement_priority(file_path, diff)
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to analyze file improvement for {file_path}: {e}")
            return None
    
    def _assess_improvement_priority(self, file_path: str, diff: List[str]) -> str:
        """Assess the priority of an improvement"""
        high_priority_files = [".quality-gates.json", "scripts/run_quality_gates.py"]
        high_priority_keywords = ["error", "security", "coverage", "critical"]
        
        if file_path in high_priority_files:
            return "high"
        
        diff_text = ''.join(diff).lower()
        if any(keyword in diff_text for keyword in high_priority_keywords):
            return "high"
        
        return "medium"
    
    def _analyze_score_improvement(self, main_scores: Dict[str, Any], 
                                  branch_scores: Dict[str, Any], branch_name: str) -> Optional[Dict[str, Any]]:
        """Analyze if branch has better quality scores"""
        try:
            improvements = []
            
            # Compare pylint scores
            main_pylint = main_scores.get("quality_gates", {}).get("pylint", {}).get("average_score", 0)
            branch_pylint = branch_scores.get("quality_gates", {}).get("pylint", {}).get("average_score", 0)
            
            if branch_pylint > main_pylint:
                improvements.append(f"Pylint: {branch_pylint:.2f} > {main_pylint:.2f}")
            
            # Compare mypy error count
            main_mypy = main_scores.get("quality_gates", {}).get("mypy", {}).get("error_count", float('inf'))
            branch_mypy = branch_scores.get("quality_gates", {}).get("mypy", {}).get("error_count", float('inf'))
            
            if branch_mypy < main_mypy:
                improvements.append(f"MyPy errors: {branch_mypy} < {main_mypy}")
            
            # Compare complexity
            main_complexity = main_scores.get("quality_gates", {}).get("complexity", {}).get("high_complexity_count", float('inf'))
            branch_complexity = branch_scores.get("quality_gates", {}).get("complexity", {}).get("high_complexity_count", float('inf'))
            
            if branch_complexity < main_complexity:
                improvements.append(f"Complexity: {branch_complexity} < {main_complexity}")
            
            if improvements:
                return {
                    "type": "score_improvement",
                    "source_branch": branch_name,
                    "target_branch": "main",
                    "improvements": improvements,
                    "priority": "high"
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to analyze score improvement for {branch_name}: {e}")
            return None
    
    def _sync_quality_improvements(self, improvements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sync quality improvements across branches"""
        sync_actions = []
        
        for improvement in improvements:
            if improvement["type"] in ["new_file", "file_improvement"]:
                action = {
                    "type": "sync_file",
                    "file_path": improvement["file_path"],
                    "source_branch": improvement["source_branch"],
                    "target_branch": improvement["target_branch"],
                    "status": "pending"
                }
                
                if not self.dry_run:
                    try:
                        success = self._sync_file(improvement)
                        action["status"] = "completed" if success else "failed"
                    except Exception as e:
                        action["status"] = "failed"
                        action["error"] = str(e)
                else:
                    action["status"] = "dry_run"
                
                sync_actions.append(action)
            
            elif improvement["type"] == "score_improvement":
                action = {
                    "type": "recommend_merge",
                    "source_branch": improvement["source_branch"],
                    "improvements": improvement["improvements"],
                    "priority": improvement["priority"]
                }
                
                if not self.dry_run:
                    self._recommend_merge(improvement)
                    action["status"] = "completed"
                else:
                    action["status"] = "dry_run"
                
                sync_actions.append(action)
        
        return sync_actions
    
    def _sync_file(self, improvement: Dict[str, Any]) -> bool:
        """Sync a specific file improvement"""
        try:
            file_path = improvement["file_path"]
            source_branch = improvement["source_branch"]
            target_branch = improvement["target_branch"]
            
            # Get current branch
            current_branch = subprocess.run([
                "git", "rev-parse", "--abbrev-ref", "HEAD"
            ], cwd=self.repo_path, capture_output=True, text=True).stdout.strip()
            
            # Switch to target branch
            subprocess.run([
                "git", "checkout", target_branch
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            try:
                # Copy file from source branch
                result = subprocess.run([
                    "git", "show", f"{source_branch}:{file_path}"
                ], cwd=self.repo_path, capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Write file content
                    target_file = self.repo_path / file_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    target_file.write_text(result.stdout)
                    
                    # Stage the file
                    subprocess.run([
                        "git", "add", file_path
                    ], cwd=self.repo_path, capture_output=True, text=True)
                    
                    # Commit if there are changes
                    result = subprocess.run([
                        "git", "diff", "--cached", "--name-only"
                    ], cwd=self.repo_path, capture_output=True, text=True)
                    
                    if result.stdout.strip():
                        subprocess.run([
                            "git", "commit", "-m", f"chore: Sync quality improvements from {source_branch} for {file_path}"
                        ], cwd=self.repo_path, capture_output=True, text=True)
                        
                        logger.info(f"✅ Synced {file_path} from {source_branch} to {target_branch}")
                        return True
                    else:
                        logger.info(f"ℹ️  No changes to sync for {file_path}")
                        return True
                else:
                    logger.error(f"Failed to get file content from {source_branch}:{file_path}")
                    return False
                    
            finally:
                # Switch back to original branch
                subprocess.run([
                    "git", "checkout", current_branch
                ], cwd=self.repo_path, capture_output=True, text=True)
                
        except Exception as e:
            logger.error(f"Failed to sync file {improvement['file_path']}: {e}")
            return False
    
    def _recommend_merge(self, improvement: Dict[str, Any]):
        """Recommend merging a branch with quality improvements"""
        try:
            source_branch = improvement["source_branch"]
            improvements_text = "\n".join(f"- {imp}" for imp in improvement["improvements"])
            
            message = f"""
🚀 Quality Improvement Recommendation

Branch: {source_branch}
Quality Improvements:
{improvements_text}

This branch has measurable quality improvements and should be considered for integration.
"""
            
            logger.info(f"📊 Quality improvement recommendation: {message}")
            
            # Write to notifications file
            notifications_file = self.repo_path / ".claude/logs/quality_recommendations.log"
            notifications_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(notifications_file, 'a') as f:
                f.write(f"{datetime.now().isoformat()}: {message}\n")
                
        except Exception as e:
            logger.error(f"Failed to recommend merge for {improvement['source_branch']}: {e}")
    
    def _handle_conflicts(self, sync_actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Handle conflicts in quality gate synchronization"""
        conflicts = []
        
        failed_actions = [action for action in sync_actions if action.get("status") == "failed"]
        
        for action in failed_actions:
            conflict = {
                "action": action,
                "resolution": "manual_review_required",
                "recommendations": []
            }
            
            if action["type"] == "sync_file":
                conflict["recommendations"].append(f"Manually review and merge {action['file_path']}")
                conflict["recommendations"].append("Check for syntax errors or configuration conflicts")
            
            conflicts.append(conflict)
        
        return conflicts
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of sync results"""
        summary = {
            "total_branches": len(results["branches_analyzed"]),
            "total_improvements": len(results["quality_improvements"]),
            "successful_syncs": len([a for a in results["sync_actions"] if a.get("status") == "completed"]),
            "failed_syncs": len([a for a in results["sync_actions"] if a.get("status") == "failed"]),
            "conflicts": len(results["conflicts"]),
            "recommendations": []
        }
        
        # Generate recommendations
        if summary["failed_syncs"] > 0:
            summary["recommendations"].append(f"🔧 {summary['failed_syncs']} sync operations failed - manual review required")
        
        if summary["conflicts"] > 0:
            summary["recommendations"].append(f"⚠️  {summary['conflicts']} conflicts detected - manual resolution needed")
        
        if summary["successful_syncs"] > 0:
            summary["recommendations"].append(f"✅ {summary['successful_syncs']} quality improvements synced successfully")
        
        return summary


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Sync quality gates across branches")
    parser.add_argument("--dry-run", action="store_true", help="Don't make changes, just analyze")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--repo", default=".", help="Repository path")
    
    args = parser.parse_args()
    
    # Run sync
    sync = QualityGateSync(args.repo, args.dry_run)
    results = sync.run_sync()
    
    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"🔄 Quality Gate Sync Results")
        print(f"============================")
        print(f"📊 Branches analyzed: {results['summary']['total_branches']}")
        print(f"⚡ Improvements found: {results['summary']['total_improvements']}")
        print(f"✅ Successful syncs: {results['summary']['successful_syncs']}")
        print(f"❌ Failed syncs: {results['summary']['failed_syncs']}")
        print(f"⚠️  Conflicts: {results['summary']['conflicts']}")
        
        if results["summary"]["recommendations"]:
            print("\n📝 Recommendations:")
            for rec in results["summary"]["recommendations"]:
                print(f"  • {rec}")
        
        if results.get("error"):
            print(f"\n❌ Error: {results['error']}")
            sys.exit(1)
    
    # Exit with appropriate code
    sys.exit(0 if not results.get("error") else 1)


if __name__ == "__main__":
    main()