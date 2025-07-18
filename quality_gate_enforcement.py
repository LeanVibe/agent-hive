#!/usr/bin/env python3
"""
Quality Gate Enforcement System
Enhanced enforcement for PR size limits and workflow discipline
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

class QualityGateEnforcement:
    """Enhanced quality gate enforcement with strict PR size limits"""
    
    def __init__(self, config_path: str = ".quality-gates.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.enforcement_log = []
        
    def _load_config(self) -> Dict:
        """Load quality gate configuration"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                return json.load(f)
        return self._default_config()
    
    def _default_config(self) -> Dict:
        """Default quality gate configuration"""
        return {
            "agent_name": "pm_coordinator",
            "task_description": "quality_gate_enforcement",
            "created_at": datetime.now().isoformat(),
            "quality_gates": {
                "max_pr_size": 500,
                "required_tests": True,
                "required_docs": True,
                "required_security_review": True,
                "required_performance_check": True,
                "max_complexity": 15,
                "min_coverage": 85
            },
            "enforcement_level": "strict",
            "rules": {
                "pr_size_limit": 500,
                "test_coverage_required": 85,
                "documentation_required": True,
                "security_review_required": True,
                "performance_check_required": True,
                "code_review_required": True,
                "linting_required": True,
                "type_checking_required": True
            }
        }
    
    def check_pr_size(self, pr_number: int) -> Tuple[bool, Dict]:
        """Check PR size against limits"""
        try:
            # Get PR details
            result = subprocess.run(
                ["gh", "pr", "view", str(pr_number), "--json", "additions,deletions,title,author"],
                capture_output=True, text=True, check=True
            )
            pr_data = json.loads(result.stdout)
            
            additions = pr_data.get("additions", 0)
            deletions = pr_data.get("deletions", 0)
            total_changes = additions + deletions
            max_size = self.config["quality_gates"]["max_pr_size"]
            
            violation = {
                "pr_number": pr_number,
                "title": pr_data.get("title", ""),
                "author": pr_data.get("author", {}).get("login", ""),
                "additions": additions,
                "deletions": deletions,
                "total_changes": total_changes,
                "max_allowed": max_size,
                "violation_factor": round(total_changes / max_size, 1),
                "timestamp": datetime.now().isoformat()
            }
            
            is_compliant = total_changes <= max_size
            
            if not is_compliant:
                self.enforcement_log.append(violation)
                
            return is_compliant, violation
            
        except subprocess.CalledProcessError as e:
            return False, {"error": f"Failed to check PR {pr_number}: {e}"}
    
    def enforce_pr_size_limit(self, pr_number: int) -> Dict:
        """Enforce PR size limits with automatic closure"""
        is_compliant, violation_data = self.check_pr_size(pr_number)
        
        if not is_compliant and "error" not in violation_data:
            # Create enforcement message
            enforcement_msg = f"""🚨 QUALITY GATE ENFORCEMENT - PR CLOSED

**WORKFLOW DISCIPLINE VIOLATION:**
- **Size**: {violation_data['total_changes']} changes ({violation_data['violation_factor']}x over limit)
- **Limit**: {violation_data['max_allowed']} lines maximum
- **Policy**: Non-negotiable <500 line PR limits (Week 2 Strategic Plan)

**REQUIRED ACTION:**
1. Break down into {max(1, violation_data['total_changes'] // violation_data['max_allowed'])} smaller PRs
2. Follow incremental development approach
3. Submit manageable, reviewable changes
4. Comply with established workflow discipline

**ENFORCEMENT AUTHORITY:** PM Agent - Quality Gate System
**REFERENCE:** Large PRs cause integration failures and system instability

Agent: Redirect to compliant workflow immediately."""
            
            # Close the PR
            try:
                subprocess.run(
                    ["gh", "pr", "close", str(pr_number), "--comment", enforcement_msg],
                    check=True, capture_output=True, text=True
                )
                
                violation_data["enforcement_action"] = "pr_closed"
                violation_data["enforcement_message"] = enforcement_msg
                
                # Log enforcement
                self._log_enforcement(violation_data)
                
                return {
                    "status": "enforced",
                    "action": "pr_closed",
                    "violation": violation_data
                }
                
            except subprocess.CalledProcessError as e:
                return {
                    "status": "error",
                    "error": f"Failed to close PR {pr_number}: {e}"
                }
        
        return {
            "status": "compliant" if is_compliant else "error",
            "violation": violation_data
        }
    
    def scan_open_prs(self) -> List[Dict]:
        """Scan all open PRs for size violations"""
        violations = []
        
        try:
            # Get all open PRs
            result = subprocess.run(
                ["gh", "pr", "list", "--json", "number,title,author,additions,deletions"],
                capture_output=True, text=True, check=True
            )
            
            prs = json.loads(result.stdout)
            
            for pr in prs:
                pr_number = pr["number"]
                is_compliant, violation_data = self.check_pr_size(pr_number)
                
                if not is_compliant and "error" not in violation_data:
                    violations.append(violation_data)
                    
        except subprocess.CalledProcessError as e:
            return [{"error": f"Failed to scan PRs: {e}"}]
        
        return violations
    
    def _log_enforcement(self, violation_data: Dict):
        """Log enforcement actions"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "pr_size_enforcement",
            "data": violation_data
        }
        
        log_file = Path("quality_gate_enforcement.log")
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    
    def generate_enforcement_report(self) -> Dict:
        """Generate comprehensive enforcement report"""
        violations = self.scan_open_prs()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "enforcement_config": self.config,
            "active_violations": violations,
            "violation_count": len(violations),
            "enforcement_log": self.enforcement_log,
            "recommendations": []
        }
        
        # Generate recommendations
        if violations:
            report["recommendations"].append(
                "Immediately close all oversized PRs and enforce workflow discipline"
            )
            report["recommendations"].append(
                "Implement pre-commit hooks to prevent oversized PR creation"
            )
            report["recommendations"].append(
                "Establish agent training on incremental development practices"
            )
        
        return report

def main():
    """Main enforcement execution"""
    if len(sys.argv) < 2:
        print("Usage: python quality_gate_enforcement.py <command> [args]")
        print("Commands: check_pr <number>, scan_all, enforce_pr <number>, report")
        sys.exit(1)
    
    enforcer = QualityGateEnforcement()
    command = sys.argv[1]
    
    if command == "check_pr" and len(sys.argv) > 2:
        pr_number = int(sys.argv[2])
        is_compliant, violation_data = enforcer.check_pr_size(pr_number)
        print(json.dumps({"compliant": is_compliant, "data": violation_data}, indent=2))
        
    elif command == "scan_all":
        violations = enforcer.scan_open_prs()
        print(json.dumps({"violations": violations}, indent=2))
        
    elif command == "enforce_pr" and len(sys.argv) > 2:
        pr_number = int(sys.argv[2])
        result = enforcer.enforce_pr_size_limit(pr_number)
        print(json.dumps(result, indent=2))
        
    elif command == "report":
        report = enforcer.generate_enforcement_report()
        print(json.dumps(report, indent=2))
        
        # Save report
        report_file = f"quality_gate_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {report_file}")
        
    else:
        print("Invalid command or missing arguments")
        sys.exit(1)

if __name__ == "__main__":
    main()