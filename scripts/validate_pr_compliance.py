#!/usr/bin/env python3
"""
LeanVibe Agent Hive - PR Compliance Validation

This script validates PR compliance with the <500 line limit and other requirements.
Used in pre-commit hooks to prevent requirement violations.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Constants
MAX_PR_LINES = 500
REQUIREMENTS_VERSION = "1.0"

class PRComplianceValidator:
    """Validates PR compliance with requirements"""
    
    def __init__(self):
        """Initialize validator"""
        self.max_lines = MAX_PR_LINES
        self.requirements_file = Path("AGENT_REQUIREMENTS.md")
    
    def get_pr_stats(self) -> dict:
        """
        Get PR statistics from git diff
        
        Returns:
            dict: PR statistics including line counts
        """
        try:
            # Get diff stats
            result = subprocess.run(
                ['git', 'diff', '--cached', '--stat'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {"error": "Failed to get git diff stats"}
            
            # Parse diff output
            lines = result.stdout.strip().split('\n')
            if not lines or lines == ['']:
                return {"files": 0, "insertions": 0, "deletions": 0, "total_lines": 0}
            
            # Get summary line (last line)
            summary_line = lines[-1]
            
            # Parse summary: "X files changed, Y insertions(+), Z deletions(-)"
            files_changed = 0
            insertions = 0
            deletions = 0
            
            if "file" in summary_line:
                parts = summary_line.split(',')
                
                for part in parts:
                    part = part.strip()
                    if "file" in part:
                        files_changed = int(part.split()[0])
                    elif "insertion" in part:
                        insertions = int(part.split()[0])
                    elif "deletion" in part:
                        deletions = int(part.split()[0])
            
            total_lines = insertions + deletions
            
            return {
                "files": files_changed,
                "insertions": insertions,
                "deletions": deletions,
                "total_lines": total_lines
            }
            
        except Exception as e:
            return {"error": f"Error getting PR stats: {e}"}
    
    def validate_pr_size(self) -> bool:
        """
        Validate PR size against limit
        
        Returns:
            bool: True if compliant, False if violation
        """
        stats = self.get_pr_stats()
        
        if "error" in stats:
            print(f"❌ ERROR: {stats['error']}")
            return False
        
        total_lines = stats["total_lines"]
        
        print(f"📊 PR STATISTICS:")
        print(f"   Files changed: {stats['files']}")
        print(f"   Insertions: {stats['insertions']}")
        print(f"   Deletions: {stats['deletions']}")
        print(f"   Total lines: {total_lines}")
        print(f"   Limit: {self.max_lines}")
        
        if total_lines > self.max_lines:
            print(f"\n🚨 PR SIZE VIOLATION DETECTED!")
            print(f"   Current: {total_lines} lines")
            print(f"   Limit: {self.max_lines} lines")
            print(f"   Violation: {total_lines - self.max_lines} lines over limit")
            print(f"   Ratio: {total_lines / self.max_lines:.1f}x over limit")
            
            print(f"\n⚠️  REQUIRED ACTIONS:")
            print(f"   1. STOP - Do not commit this PR")
            print(f"   2. BREAK DOWN - Split into multiple PRs")
            print(f"   3. RESUBMIT - Each PR must be <{self.max_lines} lines")
            print(f"   4. VALIDATE - Check each PR before commit")
            
            print(f"\n📋 BREAKDOWN STRATEGY:")
            suggested_prs = (total_lines // self.max_lines) + 1
            print(f"   Suggested PRs: {suggested_prs}")
            print(f"   Target size: ~{total_lines // suggested_prs} lines per PR")
            
            return False
        
        print(f"\n✅ PR SIZE COMPLIANT: {total_lines} lines (<{self.max_lines})")
        return True
    
    def validate_file_changes(self) -> bool:
        """
        Validate that file changes are reasonable
        
        Returns:
            bool: True if compliant, False if concerning
        """
        try:
            # Get list of changed files
            result = subprocess.run(
                ['git', 'diff', '--cached', '--name-only'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print("❌ ERROR: Failed to get changed files")
                return False
            
            files = result.stdout.strip().split('\n')
            files = [f for f in files if f]  # Remove empty strings
            
            if not files:
                print("📋 No files changed")
                return True
            
            print(f"📁 CHANGED FILES ({len(files)}):")
            for file in files:
                print(f"   - {file}")
            
            # Check for concerning patterns
            concerning_patterns = [
                ("Too many files", len(files) > 20),
                ("Binary files", any(f.endswith(('.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip')) for f in files)),
                ("Config files", any(f.endswith(('.env', '.key', '.pem', '.p12')) for f in files)),
                ("Large directories", any('node_modules' in f or '__pycache__' in f for f in files))
            ]
            
            warnings = []
            for pattern, condition in concerning_patterns:
                if condition:
                    warnings.append(pattern)
            
            if warnings:
                print(f"\n⚠️  POTENTIAL CONCERNS:")
                for warning in warnings:
                    print(f"   - {warning}")
                print(f"   Review these changes carefully")
            
            return True
            
        except Exception as e:
            print(f"❌ ERROR validating file changes: {e}")
            return False
    
    def validate_commit_message(self) -> bool:
        """
        Validate commit message follows conventions
        
        Returns:
            bool: True if compliant, False if non-compliant
        """
        try:
            # Get commit message from git
            result = subprocess.run(
                ['git', 'log', '--format=%B', '-n', '1', 'HEAD'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # No commits yet, check if we can get staged message
                return True
            
            message = result.stdout.strip()
            
            if not message:
                print("⚠️  WARNING: Empty commit message")
                return True
            
            # Check for conventional commit format
            conventional_prefixes = [
                'feat:', 'fix:', 'docs:', 'style:', 'refactor:',
                'test:', 'chore:', 'perf:', 'ci:', 'build:'
            ]
            
            has_conventional = any(message.startswith(prefix) for prefix in conventional_prefixes)
            
            if not has_conventional:
                print("⚠️  WARNING: Consider using conventional commit format")
                print("   Examples: feat:, fix:, docs:, refactor:, test:")
            
            return True
            
        except Exception as e:
            print(f"❌ ERROR validating commit message: {e}")
            return True  # Don't fail on commit message issues
    
    def run_full_validation(self) -> bool:
        """
        Run full PR compliance validation
        
        Returns:
            bool: True if fully compliant, False if violations found
        """
        print("🛡️ LEANVIBE PR COMPLIANCE VALIDATION")
        print("=" * 50)
        
        # Check requirements file exists
        if not self.requirements_file.exists():
            print(f"⚠️  WARNING: Requirements file {self.requirements_file} not found")
        
        # Run all validations
        validations = [
            ("PR Size Limit", self.validate_pr_size),
            ("File Changes", self.validate_file_changes),
            ("Commit Message", self.validate_commit_message),
        ]
        
        all_passed = True
        
        for name, validator in validations:
            print(f"\n🔍 VALIDATING: {name}")
            print("-" * 30)
            
            passed = validator()
            
            if passed:
                print(f"✅ PASSED: {name}")
            else:
                print(f"❌ FAILED: {name}")
                all_passed = False
        
        print("\n" + "=" * 50)
        
        if all_passed:
            print("✅ ALL VALIDATIONS PASSED - PR COMPLIANT")
            print("🚀 Ready for commit and review")
        else:
            print("❌ VALIDATION FAILURES DETECTED")
            print("🛑 Fix issues before committing")
        
        return all_passed

def main():
    """Main CLI interface for validation"""
    parser = argparse.ArgumentParser(
        description="LeanVibe PR Compliance Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full validation
  python validate_pr_compliance.py --validate
  
  # Check only PR size
  python validate_pr_compliance.py --size-only
  
  # Use in pre-commit hook
  python validate_pr_compliance.py --validate --strict
        """
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Run full PR compliance validation'
    )
    
    parser.add_argument(
        '--size-only',
        action='store_true',
        help='Check only PR size limit'
    )
    
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Strict mode - fail on any violation'
    )
    
    parser.add_argument(
        '--max-lines',
        type=int,
        default=MAX_PR_LINES,
        help=f'Maximum PR lines (default: {MAX_PR_LINES})'
    )
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = PRComplianceValidator()
    validator.max_lines = args.max_lines
    
    # Run validation
    if args.validate:
        success = validator.run_full_validation()
        if not success and args.strict:
            sys.exit(1)
    
    elif args.size_only:
        print("🛡️ PR SIZE VALIDATION")
        print("=" * 30)
        success = validator.validate_pr_size()
        if not success:
            sys.exit(1)
    
    else:
        parser.print_help()
        print("\n🛡️ PREVENTION-FIRST APPROACH")
        print("Validate PR compliance before committing.")
        print(f"Maximum PR size: {MAX_PR_LINES} lines")

if __name__ == '__main__':
    main()