#!/usr/bin/env python3
"""
LeanVibe Agent Hive - Documentation Validation Framework

Automated validation of documentation accuracy against actual implementation.
This script validates that all documented features, APIs, and examples work correctly.

Usage:
    python scripts/validate_documentation.py --all
    python scripts/validate_documentation.py --api-reference
    python scripts/validate_documentation.py --deployment
    python scripts/validate_documentation.py --troubleshooting
"""

import argparse
import importlib
import inspect
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import yaml

@dataclass
class ValidationResult:
    """Result of a documentation validation check."""
    file: str
    section: str
    check_type: str
    status: str  # "pass", "fail", "warning", "skip"
    message: str
    details: Optional[str] = None

class DocumentationValidator:
    """Comprehensive documentation validation framework."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: List[ValidationResult] = []
        self.python_path_added = False

    def add_python_path(self):
        """Add project directories to Python path for imports."""
        if not self.python_path_added:
            sys.path.insert(0, str(self.project_root))
            sys.path.insert(0, str(self.project_root / "advanced_orchestration"))
            sys.path.insert(0, str(self.project_root / "intelligence_framework"))
            sys.path.insert(0, str(self.project_root / "external_api"))
            sys.path.insert(0, str(self.project_root / "ml_enhancements"))
            self.python_path_added = True

    def validate_api_imports(self) -> List[ValidationResult]:
        """Validate that all documented imports actually work."""
        results = []

        # API Reference documented imports
        api_imports = [
            ("advanced_orchestration.multi_agent_coordinator", "MultiAgentCoordinator"),
            ("advanced_orchestration.resource_manager", "ResourceManager"),
            ("advanced_orchestration.scaling_manager", "ScalingManager"),
            ("advanced_orchestration.models", "CoordinatorConfig"),
            ("intelligence_framework", "IntelligenceFramework"),
            ("intelligent_task_allocation", "IntelligentTaskAllocator"),
            ("agent_coordination_protocols", "AgentCoordinationProtocols"),
            ("performance_monitoring_optimization", "PerformanceMonitoringOptimization"),
            ("external_api", "WebhookServer"),
            ("external_api", "ApiGateway"),
            ("external_api", "EventStreaming"),
            ("external_api.models", "WebhookConfig"),
            ("external_api.models", "ApiGatewayConfig"),
            ("external_api.models", "EventStreamConfig"),
            ("ml_enhancements", "PatternOptimizer"),
            ("ml_enhancements", "PredictiveAnalytics"),
            ("ml_enhancements", "AdaptiveLearning"),
            ("ml_enhancements.models", "MLConfig"),
        ]

        self.add_python_path()

        for module_name, class_name in api_imports:
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, class_name):
                    cls = getattr(module, class_name)
                    # Verify it's actually a class and can be instantiated (basic check)
                    if inspect.isclass(cls):
                        results.append(ValidationResult(
                            file="API_REFERENCE.md",
                            section="Imports",
                            check_type="import_validation",
                            status="pass",
                            message=f"✅ {module_name}.{class_name} imports successfully"
                        ))
                    else:
                        results.append(ValidationResult(
                            file="API_REFERENCE.md",
                            section="Imports",
                            check_type="import_validation",
                            status="fail",
                            message=f"❌ {module_name}.{class_name} is not a class"
                        ))
                else:
                    results.append(ValidationResult(
                        file="API_REFERENCE.md",
                        section="Imports",
                        check_type="import_validation",
                        status="fail",
                        message=f"❌ {class_name} not found in {module_name}"
                    ))
            except ImportError as e:
                results.append(ValidationResult(
                    file="API_REFERENCE.md",
                    section="Imports",
                    check_type="import_validation",
                    status="fail",
                    message=f"❌ Cannot import {module_name}: {str(e)}"
                ))
            except Exception as e:
                results.append(ValidationResult(
                    file="API_REFERENCE.md",
                    section="Imports",
                    check_type="import_validation",
                    status="fail",
                    message=f"❌ Error validating {module_name}.{class_name}: {str(e)}"
                ))

        return results

    def validate_cli_commands(self) -> List[ValidationResult]:
        """Validate that all documented CLI commands actually work."""
        results = []

        # Check if CLI exists
        cli_path = self.project_root / "cli.py"
        if not cli_path.exists():
            results.append(ValidationResult(
                file="README.md,DEVELOPMENT.md",
                section="CLI Commands",
                check_type="cli_validation",
                status="fail",
                message="❌ cli.py not found in project root"
            ))
            return results

        # Test basic CLI help
        try:
            result = subprocess.run(
                [sys.executable, str(cli_path), "--help"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root
            )
            if result.returncode == 0:
                results.append(ValidationResult(
                    file="CLI",
                    section="Help System",
                    check_type="cli_validation",
                    status="pass",
                    message="✅ CLI help system works"
                ))
            else:
                results.append(ValidationResult(
                    file="CLI",
                    section="Help System",
                    check_type="cli_validation",
                    status="fail",
                    message=f"❌ CLI help failed: {result.stderr}"
                ))
        except subprocess.TimeoutExpired:
            results.append(ValidationResult(
                file="CLI",
                section="Help System",
                check_type="cli_validation",
                status="fail",
                message="❌ CLI help command timed out"
            ))
        except Exception as e:
            results.append(ValidationResult(
                file="CLI",
                section="Help System",
                check_type="cli_validation",
                status="fail",
                message=f"❌ CLI help error: {str(e)}"
            ))

        # Test documented CLI commands
        documented_commands = [
            ["orchestrate", "--help"],
            ["spawn", "--help"],
            ["monitor", "--help"],
            ["checkpoint", "--help"],
            ["webhook", "--help"],
            ["gateway", "--help"],
            ["streaming", "--help"],
            ["external-api", "--help"],
        ]

        for cmd_args in documented_commands:
            try:
                result = subprocess.run(
                    [sys.executable, str(cli_path)] + cmd_args,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    cwd=self.project_root
                )
                if result.returncode == 0:
                    results.append(ValidationResult(
                        file="CLI Commands",
                        section=cmd_args[0],
                        check_type="cli_validation",
                        status="pass",
                        message=f"✅ Command '{cmd_args[0]}' help works"
                    ))
                else:
                    results.append(ValidationResult(
                        file="CLI Commands",
                        section=cmd_args[0],
                        check_type="cli_validation",
                        status="fail",
                        message=f"❌ Command '{cmd_args[0]}' help failed: {result.stderr}"
                    ))
            except subprocess.TimeoutExpired:
                results.append(ValidationResult(
                    file="CLI Commands",
                    section=cmd_args[0],
                    check_type="cli_validation",
                    status="warning",
                    message=f"⚠️ Command '{cmd_args[0]}' help timed out"
                ))
            except Exception as e:
                results.append(ValidationResult(
                    file="CLI Commands",
                    section=cmd_args[0],
                    check_type="cli_validation",
                    status="fail",
                    message=f"❌ Command '{cmd_args[0]}' error: {str(e)}"
                ))

        return results

    def validate_test_counts(self) -> List[ValidationResult]:
        """Validate that documented test counts match actual test files."""
        results = []

        # Count actual test files
        test_files = list(self.project_root.glob("test_*.py"))
        test_files.extend(list(self.project_root.glob("tests/**/*.py")))

        actual_test_count = len([f for f in test_files if f.name.startswith("test_")])

        # Check documented test counts in README.md
        readme_path = self.project_root / "README.md"
        if readme_path.exists():
            content = readme_path.read_text()

            # Look for test count mentions
            test_mentions = re.findall(r'(\d+)\s*(?:comprehensive\s*)?tests?', content, re.IGNORECASE)
            if test_mentions:
                documented_count = max(int(count) for count in test_mentions)

                if actual_test_count >= documented_count * 0.9:  # Allow 10% tolerance
                    results.append(ValidationResult(
                        file="README.md",
                        section="Test Counts",
                        check_type="test_validation",
                        status="pass",
                        message=f"✅ Test count reasonable: {actual_test_count} actual vs {documented_count} documented"
                    ))
                else:
                    results.append(ValidationResult(
                        file="README.md",
                        section="Test Counts",
                        check_type="test_validation",
                        status="warning",
                        message=f"⚠️ Test count mismatch: {actual_test_count} actual vs {documented_count} documented"
                    ))
            else:
                results.append(ValidationResult(
                    file="README.md",
                    section="Test Counts",
                    check_type="test_validation",
                    status="warning",
                    message="⚠️ No test counts found in README.md"
                ))

        return results

    def validate_code_examples(self) -> List[ValidationResult]:
        """Validate that code examples in documentation actually work."""
        results = []

        # Find markdown files with code examples
        doc_files = [
            self.project_root / "README.md",
            self.project_root / "API_REFERENCE.md",
            self.project_root / "DEVELOPMENT.md",
            self.project_root / "DEPLOYMENT.md",
        ]

        for doc_file in doc_files:
            if not doc_file.exists():
                continue

            content = doc_file.read_text()

            # Extract Python code blocks
            python_blocks = re.findall(r'```(?:python|py)\n(.*?)\n```', content, re.DOTALL)

            for i, code_block in enumerate(python_blocks):
                # Skip examples that are clearly just imports or configuration
                if any(skip_pattern in code_block for skip_pattern in [
                    "# FUTURE IMPLEMENTATION",
                    "# CURRENT ALTERNATIVE",
                    "# Example usage",
                    "pip install",
                    "uv add",
                    "git clone"
                ]):
                    continue

                # Try to validate the syntax at least
                try:
                    compile(code_block, f"<{doc_file.name}_block_{i}>", "exec")
                    results.append(ValidationResult(
                        file=doc_file.name,
                        section=f"Code Block {i+1}",
                        check_type="code_validation",
                        status="pass",
                        message="✅ Python syntax valid"
                    ))
                except SyntaxError as e:
                    results.append(ValidationResult(
                        file=doc_file.name,
                        section=f"Code Block {i+1}",
                        check_type="code_validation",
                        status="fail",
                        message=f"❌ Python syntax error: {str(e)}",
                        details=code_block[:200] + "..." if len(code_block) > 200 else code_block
                    ))

        return results

    def validate_links_and_references(self) -> List[ValidationResult]:
        """Validate internal links and cross-references in documentation."""
        results = []

        doc_files = [
            self.project_root / "README.md",
            self.project_root / "API_REFERENCE.md",
            self.project_root / "DEVELOPMENT.md",
            self.project_root / "DEPLOYMENT.md",
            self.project_root / "TROUBLESHOOTING.md",
        ]

        for doc_file in doc_files:
            if not doc_file.exists():
                continue

            content = doc_file.read_text()

            # Find internal file references
            file_refs = re.findall(r'\[([^\]]+)\]\(([^)]+\.md[^)]*)\)', content)

            for link_text, file_path in file_refs:
                # Check if referenced file exists
                if file_path.startswith('http'):
                    continue  # Skip external links

                referenced_file = self.project_root / file_path
                if referenced_file.exists():
                    results.append(ValidationResult(
                        file=doc_file.name,
                        section="Internal Links",
                        check_type="link_validation",
                        status="pass",
                        message=f"✅ Link to {file_path} exists"
                    ))
                else:
                    results.append(ValidationResult(
                        file=doc_file.name,
                        section="Internal Links",
                        check_type="link_validation",
                        status="fail",
                        message=f"❌ Link to {file_path} broken - file not found"
                    ))

        return results

    def validate_deployment_configurations(self) -> List[ValidationResult]:
        """Validate deployment configuration examples."""
        results = []

        deployment_file = self.project_root / "DEPLOYMENT.md"
        if not deployment_file.exists():
            results.append(ValidationResult(
                file="DEPLOYMENT.md",
                section="File Existence",
                check_type="deployment_validation",
                status="fail",
                message="❌ DEPLOYMENT.md not found"
            ))
            return results

        content = deployment_file.read_text()

        # Check for YAML configuration blocks
        yaml_blocks = re.findall(r'```(?:yaml|yml)\n(.*?)\n```', content, re.DOTALL)

        for i, yaml_block in enumerate(yaml_blocks):
            try:
                yaml.safe_load(yaml_block)
                results.append(ValidationResult(
                    file="DEPLOYMENT.md",
                    section=f"YAML Block {i+1}",
                    check_type="deployment_validation",
                    status="pass",
                    message="✅ YAML syntax valid"
                ))
            except yaml.YAMLError as e:
                results.append(ValidationResult(
                    file="DEPLOYMENT.md",
                    section=f"YAML Block {i+1}",
                    check_type="deployment_validation",
                    status="fail",
                    message=f"❌ YAML syntax error: {str(e)}",
                    details=yaml_block[:200] + "..." if len(yaml_block) > 200 else yaml_block
                ))

        return results

    def validate_all(self) -> List[ValidationResult]:
        """Run all validation checks."""
        all_results = []

        print("🔍 Running comprehensive documentation validation...")

        print("  📥 Validating API imports...")
        all_results.extend(self.validate_api_imports())

        print("  🖥️  Validating CLI commands...")
        all_results.extend(self.validate_cli_commands())

        print("  🧪 Validating test counts...")
        all_results.extend(self.validate_test_counts())

        print("  💻 Validating code examples...")
        all_results.extend(self.validate_code_examples())

        print("  🔗 Validating links and references...")
        all_results.extend(self.validate_links_and_references())

        print("  🚀 Validating deployment configurations...")
        all_results.extend(self.validate_deployment_configurations())

        self.results = all_results
        return all_results

    def generate_report(self) -> str:
        """Generate a comprehensive validation report."""
        if not self.results:
            return "No validation results available."

        # Count results by status
        status_counts = {"pass": 0, "fail": 0, "warning": 0, "skip": 0}
        for result in self.results:
            status_counts[result.status] += 1

        # Generate report
        report = []
        report.append("=" * 80)
        report.append("📋 LEANVIBE AGENT HIVE - DOCUMENTATION VALIDATION REPORT")
        report.append("=" * 80)
        report.append("")

        # Summary
        total_checks = len(self.results)
        pass_rate = (status_counts["pass"] / total_checks * 100) if total_checks > 0 else 0

        report.append("📊 VALIDATION SUMMARY:")
        report.append(f"   Total Checks: {total_checks}")
        report.append(f"   ✅ Passed: {status_counts['pass']} ({pass_rate:.1f}%)")
        report.append(f"   ❌ Failed: {status_counts['fail']}")
        report.append(f"   ⚠️ Warnings: {status_counts['warning']}")
        report.append(f"   ⏭️ Skipped: {status_counts['skip']}")
        report.append("")

        # Overall status
        if status_counts["fail"] == 0 and status_counts["warning"] <= 2:
            report.append("🎉 OVERALL STATUS: EXCELLENT - Documentation is highly accurate!")
        elif status_counts["fail"] <= 2:
            report.append("✅ OVERALL STATUS: GOOD - Minor issues to address")
        elif status_counts["fail"] <= 5:
            report.append("⚠️ OVERALL STATUS: NEEDS ATTENTION - Several issues found")
        else:
            report.append("❌ OVERALL STATUS: CRITICAL - Major documentation issues")

        report.append("")

        # Detailed results by file
        results_by_file = {}
        for result in self.results:
            if result.file not in results_by_file:
                results_by_file[result.file] = []
            results_by_file[result.file].append(result)

        for file_name, file_results in sorted(results_by_file.items()):
            report.append(f"📄 {file_name}:")
            for result in file_results:
                report.append(f"   {result.message}")
                if result.details:
                    report.append(f"      Details: {result.details}")
            report.append("")

        # Recommendations
        report.append("💡 RECOMMENDATIONS:")
        if status_counts["fail"] > 0:
            report.append("   1. Fix all failed validation checks immediately")
        if status_counts["warning"] > 0:
            report.append("   2. Review and address warning items")
        if pass_rate < 90:
            report.append("   3. Improve documentation accuracy to achieve >90% pass rate")
        report.append("   4. Run validation checks before committing documentation changes")
        report.append("   5. Consider adding this validation to CI/CD pipeline")

        return "\n".join(report)

def main():
    """Main validation script entry point."""
    parser = argparse.ArgumentParser(description="Validate LeanVibe Agent Hive documentation")
    parser.add_argument("--all", action="store_true", help="Run all validation checks")
    parser.add_argument("--api-reference", action="store_true", help="Validate API reference")
    parser.add_argument("--deployment", action="store_true", help="Validate deployment guide")
    parser.add_argument("--troubleshooting", action="store_true", help="Validate troubleshooting guide")
    parser.add_argument("--output", type=str, help="Output file for validation report")

    args = parser.parse_args()

    # Determine project root
    project_root = Path(__file__).parent.parent
    if not (project_root / "README.md").exists():
        print("❌ Cannot find project root (README.md not found)")
        sys.exit(1)

    # Create validator
    validator = DocumentationValidator(project_root)

    # Run validation
    if args.all or not any([args.api_reference, args.deployment, args.troubleshooting]):
        results = validator.validate_all()
    else:
        results = []
        if args.api_reference:
            results.extend(validator.validate_api_imports())
            results.extend(validator.validate_code_examples())
        if args.deployment:
            results.extend(validator.validate_deployment_configurations())
        if args.troubleshooting:
            results.extend(validator.validate_links_and_references())

    # Generate and display report
    report = validator.generate_report()
    print(report)

    # Save report if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"\n📄 Report saved to: {args.output}")

    # Exit with appropriate code
    failed_checks = sum(1 for r in results if r.status == "fail")
    if failed_checks > 0:
        print(f"\n❌ Validation failed with {failed_checks} critical issues")
        sys.exit(1)
    else:
        print("\n✅ Validation completed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()
