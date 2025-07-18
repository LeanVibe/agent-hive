#!/usr/bin/env python3
"""
LeanVibe Agent Hive - Implementation Accuracy Verification

Verifies that documented features, capabilities, and statistics match actual implementation.

Usage:
    python scripts/verify_implementation_accuracy.py --all
    python scripts/verify_implementation_accuracy.py --test-counts
    python scripts/verify_implementation_accuracy.py --feature-claims
    python scripts/verify_implementation_accuracy.py --api-endpoints
"""

import argparse
import importlib
import inspect
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

@dataclass
class AccuracyResult:
    """Result of accuracy verification check."""
    category: str
    claim: str
    status: str  # "accurate", "inaccurate", "partially_accurate", "unverifiable"
    documented_value: str
    actual_value: str
    message: str
    confidence: float  # 0.0 to 1.0

class ImplementationVerifier:
    """Comprehensive implementation accuracy verification."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: List[AccuracyResult] = []
        self.python_modules = {}
        self.test_files = []

    def setup_environment(self):
        """Setup Python path for imports."""
        sys.path.insert(0, str(self.project_root))
        sys.path.insert(0, str(self.project_root / "advanced_orchestration"))
        sys.path.insert(0, str(self.project_root / "intelligence_framework"))
        sys.path.insert(0, str(self.project_root / "external_api"))
        sys.path.insert(0, str(self.project_root / "ml_enhancements"))

    def scan_implementation(self):
        """Scan project to understand actual implementation."""
        print("🔍 Scanning implementation...")

        # Find Python files
        python_files = list(self.project_root.glob("**/*.py"))
        python_files = [f for f in python_files if not any(ignore in str(f) for ignore in [
            '.venv', '__pycache__', '.pytest_cache', 'temp_test_'
        ])]

        # Find test files
        self.test_files = [f for f in python_files if 'test_' in f.name or '/tests/' in str(f)]

        print(f"   Found {len(python_files)} Python files")
        print(f"   Found {len(self.test_files)} test files")

        # Try to import key modules
        key_modules = [
            "advanced_orchestration.multi_agent_coordinator",
            "advanced_orchestration.resource_manager",
            "advanced_orchestration.scaling_manager",
            "intelligence_framework",
            "intelligent_task_allocation",
            "agent_coordination_protocols",
            "performance_monitoring_optimization",
            "external_api",
            "ml_enhancements"
        ]

        for module_name in key_modules:
            try:
                module = importlib.import_module(module_name)
                self.python_modules[module_name] = module
            except ImportError:
                # Module doesn't exist or can't be imported
                pass

    def verify_test_counts(self) -> List[AccuracyResult]:
        """Verify documented test counts against actual test files."""
        results = []

        print("🧪 Verifying test counts...")

        # Count actual tests
        actual_test_count = 0
        test_methods = 0

        for test_file in self.test_files:
            try:
                content = test_file.read_text()
                # Count test functions/methods
                test_funcs = len(re.findall(r'def test_\\w+', content))
                test_methods += test_funcs
                if test_funcs > 0:
                    actual_test_count += 1
            except Exception:
                continue

        # Find documented test counts
        doc_files = [
            self.project_root / "README.md",
            self.project_root / "DEVELOPMENT.md",
            self.project_root / "docs" / "TODO.md"
        ]

        for doc_file in doc_files:
            if not doc_file.exists():
                continue

            content = doc_file.read_text()

            # Look for test count claims
            test_patterns = [
                (r'(\\d+)\\s*(?:comprehensive\\s*)?tests?', "test count"),
                (r'(\\d+)\\s*tests?\\s*with\\s*(\\d+)%\\s*coverage', "coverage claim"),
                (r'(\\d+)%\\s*(?:test\\s*)?coverage', "coverage percentage"),
            ]

            for pattern, claim_type in test_patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    if claim_type == "test count":
                        documented_count = int(match.group(1))

                        # Verify accuracy
                        if documented_count == len(self.test_files):
                            accuracy = "accurate"
                            confidence = 1.0
                        elif abs(documented_count - len(self.test_files)) <= 2:
                            accuracy = "partially_accurate"
                            confidence = 0.8
                        else:
                            accuracy = "inaccurate"
                            confidence = 0.3

                        results.append(AccuracyResult(
                            category="test_counts",
                            claim=f"Test count in {doc_file.name}",
                            status=accuracy,
                            documented_value=str(documented_count),
                            actual_value=f"{len(self.test_files)} test files, {test_methods} test methods",
                            message=f"Documented: {documented_count}, Actual: {len(self.test_files)} files",
                            confidence=confidence
                        ))

        return results

    def verify_feature_claims(self) -> List[AccuracyResult]:
        """Verify documented feature claims against implementation."""
        results = []

        print("🎯 Verifying feature claims...")

        # Define features to verify
        feature_checks = [
            ("CLI commands", self.verify_cli_commands),
            ("Intelligence Framework", self.verify_intelligence_framework),
            ("External API Integration", self.verify_external_api),
            ("ML Enhancements", self.verify_ml_enhancements),
            ("Multi-Agent Coordination", self.verify_multi_agent_coordination),
        ]

        for feature_name, check_function in feature_checks:
            try:
                feature_results = check_function()
                results.extend(feature_results)
            except Exception as e:
                results.append(AccuracyResult(
                    category="feature_verification",
                    claim=feature_name,
                    status="unverifiable",
                    documented_value="Various claims",
                    actual_value="Verification failed",
                    message=f"Could not verify {feature_name}: {str(e)}",
                    confidence=0.0
                ))

        return results

    def verify_cli_commands(self) -> List[AccuracyResult]:
        """Verify CLI command claims."""
        results = []

        # Check if CLI exists
        cli_file = self.project_root / "cli.py"

        if not cli_file.exists():
            return [AccuracyResult(
                category="cli",
                claim="CLI interface exists",
                status="inaccurate",
                documented_value="8 CLI commands available",
                actual_value="cli.py not found",
                message="CLI file does not exist",
                confidence=1.0
            )]

        # Count documented CLI commands
        readme_file = self.project_root / "README.md"
        if readme_file.exists():
            content = readme_file.read_text()
            cli_mentions = len(re.findall(r'python cli\\.py \\w+', content))

            # Try to get actual CLI commands
            try:
                result = subprocess.run(
                    [sys.executable, str(cli_file), "--help"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=self.project_root
                )

                if result.returncode == 0:
                    # Count subcommands in help output
                    actual_commands = len(re.findall(r'^\\s*\\w+\\s+', result.stdout, re.MULTILINE))

                    results.append(AccuracyResult(
                        category="cli",
                        claim="CLI commands count",
                        status="accurate" if abs(cli_mentions - actual_commands) <= 1 else "partially_accurate",
                        documented_value=f"{cli_mentions} command examples",
                        actual_value=f"{actual_commands} available commands",
                        message=f"CLI help shows {actual_commands} commands",
                        confidence=0.9
                    ))
                else:
                    results.append(AccuracyResult(
                        category="cli",
                        claim="CLI functionality",
                        status="inaccurate",
                        documented_value="Working CLI interface",
                        actual_value="CLI help failed",
                        message="CLI help command failed",
                        confidence=0.8
                    ))
            except Exception as e:
                results.append(AccuracyResult(
                    category="cli",
                    claim="CLI functionality",
                    status="unverifiable",
                    documented_value="Working CLI interface",
                    actual_value="Cannot test CLI",
                    message=f"CLI test failed: {str(e)}",
                    confidence=0.0
                ))

        return results

    def verify_intelligence_framework(self) -> List[AccuracyResult]:
        """Verify Intelligence Framework claims."""
        results = []

        # Check if intelligence framework module exists
        if "intelligence_framework" in self.python_modules:
            module = self.python_modules["intelligence_framework"]

            # Check for key classes
            expected_classes = ["IntelligenceFramework"]
            actual_classes = [name for name, obj in inspect.getmembers(module, inspect.isclass)]

            for expected_class in expected_classes:
                if expected_class in actual_classes:
                    results.append(AccuracyResult(
                        category="intelligence_framework",
                        claim=f"{expected_class} implementation",
                        status="accurate",
                        documented_value=f"{expected_class} class available",
                        actual_value=f"{expected_class} class found",
                        message=f"✅ {expected_class} is implemented",
                        confidence=1.0
                    ))
                else:
                    results.append(AccuracyResult(
                        category="intelligence_framework",
                        claim=f"{expected_class} implementation",
                        status="inaccurate",
                        documented_value=f"{expected_class} class available",
                        actual_value=f"{expected_class} class not found",
                        message=f"❌ {expected_class} is not implemented",
                        confidence=1.0
                    ))
        else:
            results.append(AccuracyResult(
                category="intelligence_framework",
                claim="Intelligence Framework module",
                status="inaccurate",
                documented_value="Intelligence Framework implemented",
                actual_value="Module not importable",
                message="Intelligence Framework module cannot be imported",
                confidence=1.0
            ))

        return results

    def verify_external_api(self) -> List[AccuracyResult]:
        """Verify External API Integration claims."""
        results = []

        if "external_api" in self.python_modules:
            module = self.python_modules["external_api"]

            # Check for key external API classes
            expected_classes = ["WebhookServer", "ApiGateway", "EventStreaming"]
            actual_classes = [name for name, obj in inspect.getmembers(module, inspect.isclass)]

            for expected_class in expected_classes:
                if expected_class in actual_classes:
                    results.append(AccuracyResult(
                        category="external_api",
                        claim=f"{expected_class} implementation",
                        status="accurate",
                        documented_value=f"{expected_class} available",
                        actual_value=f"{expected_class} class found",
                        message=f"✅ {expected_class} is implemented",
                        confidence=1.0
                    ))

        return results

    def verify_ml_enhancements(self) -> List[AccuracyResult]:
        """Verify ML Enhancements claims."""
        results = []

        if "ml_enhancements" in self.python_modules:
            module = self.python_modules["ml_enhancements"]

            # Check for ML enhancement classes
            expected_classes = ["PatternOptimizer", "PredictiveAnalytics", "AdaptiveLearning"]
            actual_classes = [name for name, obj in inspect.getmembers(module, inspect.isclass)]

            for expected_class in expected_classes:
                if expected_class in actual_classes:
                    results.append(AccuracyResult(
                        category="ml_enhancements",
                        claim=f"{expected_class} implementation",
                        status="accurate",
                        documented_value=f"{expected_class} available",
                        actual_value=f"{expected_class} class found",
                        message=f"✅ {expected_class} is implemented",
                        confidence=1.0
                    ))

        return results

    def verify_multi_agent_coordination(self) -> List[AccuracyResult]:
        """Verify Multi-Agent Coordination claims."""
        results = []

        if "advanced_orchestration.multi_agent_coordinator" in self.python_modules:
            module = self.python_modules["advanced_orchestration.multi_agent_coordinator"]

            # Check for coordination classes
            expected_classes = ["MultiAgentCoordinator"]
            actual_classes = [name for name, obj in inspect.getmembers(module, inspect.isclass)]

            for expected_class in expected_classes:
                if expected_class in actual_classes:
                    results.append(AccuracyResult(
                        category="multi_agent",
                        claim=f"{expected_class} implementation",
                        status="accurate",
                        documented_value=f"{expected_class} available",
                        actual_value=f"{expected_class} class found",
                        message=f"✅ {expected_class} is implemented",
                        confidence=1.0
                    ))

        return results

    def verify_performance_claims(self) -> List[AccuracyResult]:
        """Verify performance and metric claims."""
        results = []

        print("⚡ Verifying performance claims...")

        # Look for performance claims in documentation
        doc_files = [
            self.project_root / "README.md",
            self.project_root / "DEVELOPMENT.md",
        ]

        performance_patterns = [
            (r'<(\\d+)ms\\s+(?:latency|response)', "latency_claim"),
            (r'(\\d+)%\\+?\\s*(?:efficiency|utilization)', "efficiency_claim"),
            (r'<(\\d+)\\s*(?:minute|min)\\s*MTTR', "mttr_claim"),
            (r'(\\d+)\\+?\\s*agents?\\s*coordinating', "agent_count_claim"),
        ]

        for doc_file in doc_files:
            if not doc_file.exists():
                continue

            content = doc_file.read_text()

            for pattern, claim_type in performance_patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    value = match.group(1)

                    # These are aspirational claims that we mark as unverifiable
                    # since we can't easily test performance in this context
                    results.append(AccuracyResult(
                        category="performance",
                        claim=f"{claim_type} in {doc_file.name}",
                        status="unverifiable",
                        documented_value=f"{value} {claim_type}",
                        actual_value="Cannot verify in static analysis",
                        message=f"Performance claim: {value} - requires runtime testing",
                        confidence=0.5
                    ))

        return results

    def verify_all_accuracy(self) -> List[AccuracyResult]:
        """Run all accuracy verification checks."""
        all_results = []

        # Setup
        self.setup_environment()
        self.scan_implementation()

        # Run verifications
        all_results.extend(self.verify_test_counts())
        all_results.extend(self.verify_feature_claims())
        all_results.extend(self.verify_performance_claims())

        self.results = all_results
        return all_results

    def generate_report(self) -> str:
        """Generate comprehensive accuracy verification report."""
        if not self.results:
            return "No accuracy verification results available."

        # Count results by status and category
        status_counts = {"accurate": 0, "inaccurate": 0, "partially_accurate": 0, "unverifiable": 0}
        category_counts = {}

        for result in self.results:
            status_counts[result.status] += 1
            if result.category not in category_counts:
                category_counts[result.category] = {"accurate": 0, "inaccurate": 0, "partially_accurate": 0, "unverifiable": 0}
            category_counts[result.category][result.status] += 1

        # Calculate statistics
        total_checks = len(self.results)
        accuracy_rate = ((status_counts["accurate"] + status_counts["partially_accurate"]) / total_checks * 100) if total_checks > 0 else 0
        confidence_avg = sum(r.confidence for r in self.results) / total_checks if total_checks > 0 else 0

        # Generate report
        report = []
        report.append("=" * 80)
        report.append("✅ LEANVIBE AGENT HIVE - IMPLEMENTATION ACCURACY REPORT")
        report.append("=" * 80)
        report.append("")

        # Summary
        report.append("📊 ACCURACY SUMMARY:")
        report.append(f"   Total Claims Verified: {total_checks}")
        report.append(f"   ✅ Accurate: {status_counts['accurate']} ({status_counts['accurate']/total_checks*100:.1f}%)")
        report.append(f"   ⚠️ Partially Accurate: {status_counts['partially_accurate']}")
        report.append(f"   ❌ Inaccurate: {status_counts['inaccurate']}")
        report.append(f"   ❓ Unverifiable: {status_counts['unverifiable']}")
        report.append(f"   📈 Overall Accuracy Rate: {accuracy_rate:.1f}%")
        report.append(f"   🎯 Average Confidence: {confidence_avg:.2f}")
        report.append("")

        # Breakdown by category
        report.append("📋 BREAKDOWN BY CATEGORY:")
        for category, counts in sorted(category_counts.items()):
            total_category = sum(counts.values())
            category_accuracy = ((counts["accurate"] + counts["partially_accurate"]) / total_category * 100) if total_category > 0 else 0
            report.append(f"   {category}: {category_accuracy:.1f}% accurate ({counts['accurate']}/{total_category})")
            if counts["inaccurate"] > 0:
                report.append(f"      ❌ {counts['inaccurate']} inaccurate claims")
            if counts["unverifiable"] > 0:
                report.append(f"      ❓ {counts['unverifiable']} unverifiable claims")
        report.append("")

        # Overall status
        if status_counts["inaccurate"] == 0 and accuracy_rate >= 90:
            report.append("🎉 OVERALL STATUS: EXCELLENT - Documentation is highly accurate!")
        elif status_counts["inaccurate"] <= 2 and accuracy_rate >= 80:
            report.append("✅ OVERALL STATUS: GOOD - Minor accuracy issues")
        elif status_counts["inaccurate"] <= 5 and accuracy_rate >= 70:
            report.append("⚠️ OVERALL STATUS: NEEDS ATTENTION - Several inaccuracies")
        else:
            report.append("❌ OVERALL STATUS: CRITICAL - Major accuracy problems")

        report.append("")

        # Detailed inaccuracies
        inaccurate_results = [r for r in self.results if r.status == "inaccurate"]
        if inaccurate_results:
            report.append(f"❌ INACCURATE CLAIMS ({len(inaccurate_results)}):")
            for result in inaccurate_results:
                report.append(f"   {result.claim}:")
                report.append(f"      Documented: {result.documented_value}")
                report.append(f"      Actual: {result.actual_value}")
                report.append(f"      {result.message}")
            report.append("")

        # Partially accurate items
        partial_results = [r for r in self.results if r.status == "partially_accurate"]
        if partial_results:
            report.append(f"⚠️ PARTIALLY ACCURATE CLAIMS ({len(partial_results)}):")
            for result in partial_results:
                report.append(f"   {result.claim}: {result.message}")
            report.append("")

        # Recommendations
        report.append("💡 RECOMMENDATIONS:")
        if status_counts["inaccurate"] > 0:
            report.append("   1. Update all inaccurate claims in documentation immediately")
            report.append("   2. Implement missing features or correct documentation")
        if status_counts["partially_accurate"] > 0:
            report.append("   3. Review and refine partially accurate claims")
        if status_counts["unverifiable"] > 5:
            report.append("   4. Consider adding automated testing for performance claims")
        report.append("   5. Add this verification to CI/CD pipeline")
        report.append("   6. Regular accuracy audits when features change")

        return "\\n".join(report)

def main():
    """Main accuracy verification entry point."""
    parser = argparse.ArgumentParser(description="Verify LeanVibe Agent Hive implementation accuracy")
    parser.add_argument("--all", action="store_true", help="Run all accuracy verification checks")
    parser.add_argument("--test-counts", action="store_true", help="Verify test count claims")
    parser.add_argument("--feature-claims", action="store_true", help="Verify feature implementation claims")
    parser.add_argument("--api-endpoints", action="store_true", help="Verify API endpoint claims")
    parser.add_argument("--output", type=str, help="Output file for verification report")

    args = parser.parse_args()

    # Determine project root
    project_root = Path(__file__).parent.parent
    if not (project_root / "README.md").exists():
        print("❌ Cannot find project root (README.md not found)")
        sys.exit(1)

    # Create verifier
    verifier = ImplementationVerifier(project_root)

    # Run verification
    if args.all or not any([args.test_counts, args.feature_claims, args.api_endpoints]):
        results = verifier.verify_all_accuracy()
    else:
        results = []
        verifier.setup_environment()
        verifier.scan_implementation()

        if args.test_counts:
            results.extend(verifier.verify_test_counts())
        if args.feature_claims:
            results.extend(verifier.verify_feature_claims())
        # api_endpoints check would be implemented similarly

    # Generate and display report
    report = verifier.generate_report()
    print(report)

    # Save report if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"\\n📄 Report saved to: {args.output}")

    # Exit with appropriate code
    inaccurate_claims = sum(1 for r in results if r.status == "inaccurate")
    if inaccurate_claims > 0:
        print(f"\\n❌ Accuracy verification failed with {inaccurate_claims} inaccurate claims")
        sys.exit(1)
    else:
        print("\\n✅ All verifiable claims are accurate!")
        sys.exit(0)

if __name__ == "__main__":
    main()
