#!/usr/bin/env python3
"""
Development System Setup Script

Sets up the streamlined development system with automated integration checkpoints,
quality gate synchronization, and balanced workflow management.
"""

import subprocess
import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Any
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DevelopmentSystemSetup:
    """Sets up the development system improvements"""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        
    def setup_complete_system(self) -> Dict[str, Any]:
        """Set up the complete development system"""
        logger.info("🚀 Setting up streamlined development system...")
        
        results = {
            "setup_steps": [],
            "success": True,
            "errors": []
        }
        
        try:
            # 1. Create necessary directories
            self._create_directories(results)
            
            # 2. Make scripts executable
            self._make_scripts_executable(results)
            
            # 3. Create cron jobs for integration checkpoints
            self._setup_cron_jobs(results)
            
            # 4. Set up git hooks
            self._setup_git_hooks(results)
            
            # 5. Create configuration files
            self._create_configuration_files(results)
            
            # 6. Test the system
            self._test_system(results)
            
            logger.info("✅ Development system setup completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Development system setup failed: {e}")
            results["success"] = False
            results["errors"].append(str(e))
            
        return results
    
    def _create_directories(self, results: Dict[str, Any]):
        """Create necessary directories"""
        directories = [
            ".claude/logs",
            ".githooks",
            "scripts/automation"
        ]
        
        for directory in directories:
            dir_path = self.repo_path / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 Created directory: {directory}")
            
        results["setup_steps"].append("Created necessary directories")
    
    def _make_scripts_executable(self, results: Dict[str, Any]):
        """Make automation scripts executable"""
        scripts = [
            "scripts/integration_checkpoint.py",
            "scripts/quality_gate_sync.py", 
            "scripts/balanced_workflow.py"
        ]
        
        for script in scripts:
            script_path = self.repo_path / script
            if script_path.exists():
                os.chmod(script_path, 0o755)
                logger.info(f"🔧 Made executable: {script}")
            else:
                logger.warning(f"⚠️  Script not found: {script}")
                
        results["setup_steps"].append("Made scripts executable")
    
    def _setup_cron_jobs(self, results: Dict[str, Any]):
        """Set up cron jobs for automated integration checkpoints"""
        cron_entry = f"""
# Automated Integration Checkpoints (every 4 hours)
0 */4 * * * cd {self.repo_path} && python scripts/integration_checkpoint.py >> .claude/logs/integration_cron.log 2>&1

# Quality Gate Sync (daily)
0 6 * * * cd {self.repo_path} && python scripts/quality_gate_sync.py >> .claude/logs/quality_sync_cron.log 2>&1

# Workflow Balance Check (daily)
0 9 * * * cd {self.repo_path} && python scripts/balanced_workflow.py --assess >> .claude/logs/workflow_balance_cron.log 2>&1
"""
        
        # Write cron entries to a file for user to install
        cron_file = self.repo_path / "scripts/automation/cron_entries.txt"
        cron_file.write_text(cron_entry.strip())
        
        logger.info("📅 Created cron job entries in scripts/automation/cron_entries.txt")
        logger.info("   To install: cat scripts/automation/cron_entries.txt | crontab -")
        
        results["setup_steps"].append("Created cron job entries")
    
    def _setup_git_hooks(self, results: Dict[str, Any]):
        """Set up git hooks for quality gate enforcement"""
        # Pre-commit hook
        pre_commit_hook = self.repo_path / ".githooks/pre-commit"
        pre_commit_content = """#!/bin/bash
# Quality Gate Pre-commit Hook

echo "🔍 Running quality gate sync..."
python scripts/quality_gate_sync.py --dry-run

if [ $? -ne 0 ]; then
    echo "❌ Quality gate sync failed"
    exit 1
fi

echo "✅ Quality gate sync completed"
"""
        
        pre_commit_hook.write_text(pre_commit_content)
        os.chmod(pre_commit_hook, 0o755)
        
        # Configure git to use the hooks
        subprocess.run([
            "git", "config", "core.hooksPath", ".githooks"
        ], cwd=self.repo_path, capture_output=True)
        
        logger.info("🪝 Set up git hooks")
        results["setup_steps"].append("Set up git hooks")
    
    def _create_configuration_files(self, results: Dict[str, Any]):
        """Create configuration files for the development system"""
        # Development system configuration
        config = {
            "integration_checkpoint": {
                "interval_hours": 4,
                "divergence_threshold_hours": 4,
                "quality_threshold": 0.75
            },
            "quality_gate_sync": {
                "auto_sync": True,
                "conflict_resolution": "manual",
                "quality_files": [
                    ".quality-gates.json",
                    "scripts/run_quality_gates.py",
                    "scripts/quality_gate_validation.py"
                ]
            },
            "balanced_workflow": {
                "balance_ratios": {
                    "infrastructure": 0.30,
                    "quality": 0.25,
                    "feature": 0.35,
                    "security": 0.10
                },
                "enforce_quality_gates": True
            }
        }
        
        config_file = self.repo_path / ".development_system_config.json"
        config_file.write_text(json.dumps(config, indent=2))
        
        logger.info("⚙️  Created development system configuration")
        results["setup_steps"].append("Created configuration files")
    
    def _test_system(self, results: Dict[str, Any]):
        """Test the development system"""
        tests = [
            ("Integration Checkpoint", ["python", "scripts/integration_checkpoint.py", "--dry-run"]),
            ("Quality Gate Sync", ["python", "scripts/quality_gate_sync.py", "--dry-run"]),
            ("Balanced Workflow", ["python", "scripts/balanced_workflow.py", "--status"])
        ]
        
        test_results = []
        for test_name, command in tests:
            try:
                result = subprocess.run(
                    command,
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    test_results.append(f"✅ {test_name}: PASSED")
                    logger.info(f"✅ {test_name} test passed")
                else:
                    test_results.append(f"❌ {test_name}: FAILED")
                    logger.error(f"❌ {test_name} test failed: {result.stderr}")
                    
            except Exception as e:
                test_results.append(f"❌ {test_name}: ERROR - {e}")
                logger.error(f"❌ {test_name} test error: {e}")
        
        results["test_results"] = test_results
        results["setup_steps"].append("Tested system components")
    
    def print_setup_summary(self, results: Dict[str, Any]):
        """Print setup summary"""
        print("\n🚀 Development System Setup Summary")
        print("=" * 40)
        
        for step in results["setup_steps"]:
            print(f"✅ {step}")
        
        if results.get("test_results"):
            print("\n🧪 System Tests:")
            for test_result in results["test_results"]:
                print(f"   {test_result}")
        
        if results["success"]:
            print("\n🎉 Setup completed successfully!")
            print("\n📋 Next Steps:")
            print("   1. Install cron jobs: cat scripts/automation/cron_entries.txt | crontab -")
            print("   2. Review configuration: .development_system_config.json")
            print("   3. Test integration: python scripts/integration_checkpoint.py --dry-run")
            print("   4. Monitor logs: .claude/logs/")
        else:
            print("\n❌ Setup encountered errors:")
            for error in results["errors"]:
                print(f"   • {error}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Set up development system")
    parser.add_argument("--repo", default=".", help="Repository path")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    
    args = parser.parse_args()
    
    # Set up system
    setup = DevelopmentSystemSetup(args.repo)
    results = setup.setup_complete_system()
    
    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        setup.print_setup_summary(results)
    
    # Exit with appropriate code
    sys.exit(0 if results["success"] else 1)


if __name__ == "__main__":
    main()