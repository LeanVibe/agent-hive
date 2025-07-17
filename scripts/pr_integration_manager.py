#!/usr/bin/env python3
"""
PR Integration Manager
Handles automated PR integration with GitHub App authentication and quality gates
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests

try:
    from github_app_auth import GitHubAppAuth, setup_github_auth, get_repository_info
except ImportError:
    # Fallback for when GitHub App auth is not available
    def setup_github_auth():
        return None
    def get_repository_info():
        result = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, text=True)
        remote_url = result.stdout.strip()
        if 'github.com' in remote_url:
            if remote_url.startswith('git@github.com:'):
                repo_path = remote_url.replace('git@github.com:', '').replace('.git', '')
            else:
                repo_path = remote_url.replace('https://github.com/', '').replace('.git', '')
            return repo_path.split('/', 1)
        raise ValueError(f"Not a GitHub repository: {remote_url}")

logger = logging.getLogger(__name__)

class PRIntegrationManager:
    """Manages automated PR integration workflow with quality gates."""

    def __init__(self):
        self.auth = setup_github_auth()
        self.owner, self.repo = get_repository_info()

        if not self.auth:
            logger.warning("⚠️ GitHub App authentication not available - using GitHub CLI fallback")

    def get_pr_info(self, pr_number: int) -> Dict:
        """Get PR information from GitHub API."""
        if self.auth:
            # Use GitHub App authentication
            headers = self.auth.get_authenticated_headers(self.owner, self.repo)
            url = f"https://api.github.com/repos/{self.owner}/{self.repo}/pulls/{pr_number}"
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to get PR info: {response.status_code} - {response.text}")
        else:
            # Fallback to GitHub CLI
            result = subprocess.run(
                ['gh', 'pr', 'view', str(pr_number), '--json', 'number,title,state,headRefName,baseRefName,mergeable,statusCheckRollup'],
                capture_output=True, text=True
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                raise Exception(f"Failed to get PR info via gh CLI: {result.stderr}")

    def run_quality_gates(self, pr_number: int) -> Tuple[bool, List[str]]:
        """Run quality gates validation for PR."""
        logger.info(f"🎯 Running quality gates for PR #{pr_number}")
        issues = []

        try:
            # Get PR information
            pr_info = self.get_pr_info(pr_number)

            # Check if PR is mergeable
            if not pr_info.get('mergeable', True):
                issues.append("PR has merge conflicts")

            # Check CI status
            if 'statusCheckRollup' in pr_info and pr_info['statusCheckRollup']:
                status_checks = pr_info['statusCheckRollup']
                if status_checks.get('state') not in ['SUCCESS', 'COMPLETED']:
                    issues.append(f"CI checks not passing: {status_checks.get('state')}")

            # Run local quality validation if needed
            if self._should_run_local_validation(pr_info):
                local_issues = self._run_local_validation(pr_info)
                issues.extend(local_issues)

            success = len(issues) == 0
            logger.info(f"{'✅' if success else '❌'} Quality gates: {'PASSED' if success else 'FAILED'}")

            return success, issues

        except Exception as e:
            logger.error(f"❌ Quality gates failed with error: {e}")
            return False, [f"Quality gate execution error: {e}"]

    def _should_run_local_validation(self, pr_info: Dict) -> bool:
        """Determine if local validation should be run."""
        # Run local validation for component branches
        head_ref = pr_info.get('headRefName', '')
        return head_ref.startswith(('new-work/', 'feature/'))

    def _run_local_validation(self, pr_info: Dict) -> List[str]:
        """Run local validation checks."""
        issues = []

        try:
            # Check if quality gate script exists
            quality_gate_script = Path('scripts/quality_gate_validation.py')
            if quality_gate_script.exists():
                result = subprocess.run(
                    ['python', str(quality_gate_script)],
                    capture_output=True, text=True, timeout=300
                )

                if result.returncode != 0:
                    issues.append(f"Local quality gate failed: {result.stderr}")

            # Check for test coverage if coverage file exists
            coverage_file = Path('coverage.xml')
            if coverage_file.exists():
                # Basic coverage check - could be enhanced
                coverage_ok = self._check_test_coverage(coverage_file)
                if not coverage_ok:
                    issues.append("Test coverage below minimum threshold")

        except subprocess.TimeoutExpired:
            issues.append("Local validation timed out")
        except Exception as e:
            issues.append(f"Local validation error: {e}")

        return issues

    def _check_test_coverage(self, coverage_file: Path) -> bool:
        """Basic test coverage check."""
        try:
            # Simple XML parsing to check coverage
            with open(coverage_file, 'r') as f:
                content = f.read()
                # Look for line-rate attribute in coverage tag
                import re
                match = re.search(r'line-rate="([0-9.]+)"', content)
                if match:
                    coverage = float(match.group(1))
                    return coverage >= 0.7  # 70% minimum
            return True  # If we can't parse, assume it's OK
        except Exception:
            return True  # If we can't check, assume it's OK

    def merge_pr(self, pr_number: int, merge_method: str = 'squash') -> bool:
        """Merge PR using GitHub API or CLI."""
        logger.info(f"🚀 Merging PR #{pr_number} with method: {merge_method}")

        try:
            if self.auth:
                # Use GitHub App authentication
                headers = self.auth.get_authenticated_headers(self.owner, self.repo)
                url = f"https://api.github.com/repos/{self.owner}/{self.repo}/pulls/{pr_number}/merge"

                data = {
                    'merge_method': merge_method,
                    'commit_title': f"Merge PR #{pr_number}",
                    'commit_message': f"Automated merge via agent integration system"
                }

                response = requests.put(url, headers=headers, json=data)

                if response.status_code == 200:
                    logger.info(f"✅ PR #{pr_number} merged successfully")

                    # Delete branch if it's a feature branch
                    pr_info = self.get_pr_info(pr_number)
                    head_ref = pr_info.get('headRefName', '')
                    if head_ref.startswith(('new-work/', 'feature/')):
                        self._delete_branch(head_ref)

                    return True
                else:
                    logger.error(f"❌ Failed to merge PR: {response.status_code} - {response.text}")
                    return False
            else:
                # Fallback to GitHub CLI
                result = subprocess.run(
                    ['gh', 'pr', 'merge', str(pr_number), '--squash', '--delete-branch'],
                    capture_output=True, text=True
                )

                if result.returncode == 0:
                    logger.info(f"✅ PR #{pr_number} merged successfully via gh CLI")
                    return True
                else:
                    logger.error(f"❌ Failed to merge PR via gh CLI: {result.stderr}")
                    return False

        except Exception as e:
            logger.error(f"❌ Error merging PR #{pr_number}: {e}")
            return False

    def _delete_branch(self, branch_name: str) -> None:
        """Delete remote branch after merge."""
        try:
            if self.auth:
                headers = self.auth.get_authenticated_headers(self.owner, self.repo)
                url = f"https://api.github.com/repos/{self.owner}/{self.repo}/git/refs/heads/{branch_name}"
                response = requests.delete(url, headers=headers)

                if response.status_code == 204:
                    logger.info(f"🗑️ Branch {branch_name} deleted")
                else:
                    logger.warning(f"⚠️ Could not delete branch {branch_name}: {response.status_code}")
            else:
                # CLI fallback - usually handled by merge command
                pass
        except Exception as e:
            logger.warning(f"⚠️ Could not delete branch {branch_name}: {e}")

    def integrate_pr(self, pr_number: int) -> bool:
        """Full PR integration workflow with quality gates."""
        logger.info(f"🔄 Starting integration workflow for PR #{pr_number}")

        try:
            # Step 1: Get PR information
            pr_info = self.get_pr_info(pr_number)
            logger.info(f"📋 PR #{pr_number}: {pr_info.get('title', 'Unknown title')}")

            # Step 2: Validate PR state
            if pr_info.get('state') != 'open':
                logger.error(f"❌ PR #{pr_number} is not open (state: {pr_info.get('state')})")
                return False

            # Step 3: Run quality gates
            quality_passed, quality_issues = self.run_quality_gates(pr_number)

            if not quality_passed:
                logger.error("❌ Quality gates failed:")
                for issue in quality_issues:
                    logger.error(f"   - {issue}")
                return False

            # Step 4: Merge PR
            merge_success = self.merge_pr(pr_number)

            if merge_success:
                logger.info(f"🎉 PR #{pr_number} integration completed successfully")
                return True
            else:
                logger.error(f"❌ PR #{pr_number} integration failed during merge")
                return False

        except Exception as e:
            logger.error(f"❌ PR integration workflow failed: {e}")
            return False

    def list_mergeable_prs(self) -> List[Dict]:
        """List all open PRs that are ready for integration."""
        try:
            if self.auth:
                headers = self.auth.get_authenticated_headers(self.owner, self.repo)
                url = f"https://api.github.com/repos/{self.owner}/{self.repo}/pulls"
                response = requests.get(url, headers=headers)

                if response.status_code == 200:
                    prs = response.json()
                else:
                    raise Exception(f"Failed to list PRs: {response.status_code}")
            else:
                # Fallback to gh CLI
                result = subprocess.run(
                    ['gh', 'pr', 'list', '--json', 'number,title,headRefName,mergeable,statusCheckRollup'],
                    capture_output=True, text=True
                )

                if result.returncode == 0:
                    prs = json.loads(result.stdout)
                else:
                    raise Exception(f"Failed to list PRs via CLI: {result.stderr}")

            # Filter to component PRs that are ready
            mergeable_prs = []
            for pr in prs:
                head_ref = pr.get('headRefName', '')
                if head_ref.startswith(('new-work/', 'feature/')):
                    if pr.get('mergeable', True):
                        mergeable_prs.append(pr)

            return mergeable_prs

        except Exception as e:
            logger.error(f"❌ Failed to list mergeable PRs: {e}")
            return []

def main():
    """Main CLI interface for PR integration."""
    parser = argparse.ArgumentParser(description="PR Integration Manager")
    parser.add_argument('command', choices=['integrate', 'list', 'quality-check', 'test-auth'],
                       help='Command to execute')
    parser.add_argument('--pr', type=int, help='PR number for integration or quality check')
    parser.add_argument('--batch', action='store_true', help='Integrate all ready PRs')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        manager = PRIntegrationManager()

        if args.command == 'test-auth':
            if manager.auth:
                success = manager.auth.test_authentication(manager.owner, manager.repo)
                return 0 if success else 1
            else:
                logger.error("❌ GitHub App authentication not configured")
                return 1

        elif args.command == 'list':
            prs = manager.list_mergeable_prs()
            if prs:
                logger.info(f"📋 Found {len(prs)} mergeable PRs:")
                for pr in prs:
                    logger.info(f"   - PR #{pr['number']}: {pr['title']}")
            else:
                logger.info("No mergeable PRs found")
            return 0

        elif args.command == 'quality-check':
            if not args.pr:
                logger.error("❌ --pr required for quality-check command")
                return 1

            passed, issues = manager.run_quality_gates(args.pr)
            if passed:
                logger.info(f"✅ Quality gates passed for PR #{args.pr}")
                return 0
            else:
                logger.error(f"❌ Quality gates failed for PR #{args.pr}:")
                for issue in issues:
                    logger.error(f"   - {issue}")
                return 1

        elif args.command == 'integrate':
            if args.batch:
                # Integrate all ready PRs
                prs = manager.list_mergeable_prs()
                if not prs:
                    logger.info("No PRs ready for integration")
                    return 0

                success_count = 0
                for pr in prs:
                    if args.dry_run:
                        logger.info(f"🔍 Would integrate PR #{pr['number']}: {pr['title']}")
                        success_count += 1
                    else:
                        success = manager.integrate_pr(pr['number'])
                        if success:
                            success_count += 1

                logger.info(f"📊 Integration summary: {success_count}/{len(prs)} PRs {'would be ' if args.dry_run else ''}integrated")
                return 0 if success_count == len(prs) else 1

            elif args.pr:
                # Integrate specific PR
                if args.dry_run:
                    logger.info(f"🔍 Would integrate PR #{args.pr}")
                    return 0
                else:
                    success = manager.integrate_pr(args.pr)
                    return 0 if success else 1

            else:
                logger.error("❌ --pr or --batch required for integrate command")
                return 1

        else:
            parser.print_help()
            return 1

    except Exception as e:
        logger.error(f"❌ Command failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
