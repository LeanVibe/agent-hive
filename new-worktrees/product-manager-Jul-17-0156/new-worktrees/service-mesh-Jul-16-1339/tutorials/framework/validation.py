"""
Tutorial Validation System

Provides comprehensive validation for tutorial content including:
- Content validation
- Code example testing
- Step dependency validation
- User experience testing
"""

import subprocess
import re
import ast
import time
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import json
import tempfile
import os


@dataclass
class ValidationResult:
    """Result of validation operation."""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    tutorial_id: str
    overall_success: bool
    total_validations: int
    passed_validations: int
    failed_validations: int
    results: List[ValidationResult]
    execution_time: float

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_validations == 0:
            return 0.0
        return (self.passed_validations / self.total_validations) * 100


class StepValidator:
    """Validates individual tutorial steps."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def validate_command(self, command: str, expected_output: Optional[str] = None) -> ValidationResult:
        """Validate a command execution."""
        start_time = time.time()

        try:
            # SECURITY FIX: Use list instead of shell=True to prevent command injection
            import shlex
            command_list = shlex.split(command)
            result = subprocess.run(
                command_list,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            execution_time = time.time() - start_time

            if result.returncode == 0:
                if expected_output and expected_output not in result.stdout:
                    return ValidationResult(
                        success=False,
                        message=f"Expected output '{expected_output}' not found",
                        details={"expected": expected_output, "actual": result.stdout},
                        output=result.stdout,
                        execution_time=execution_time
                    )

                return ValidationResult(
                    success=True,
                    message="Command executed successfully",
                    output=result.stdout,
                    execution_time=execution_time
                )
            else:
                return ValidationResult(
                    success=False,
                    message=f"Command failed with return code {result.returncode}",
                    error=result.stderr,
                    execution_time=execution_time
                )

        except subprocess.TimeoutExpired:
            return ValidationResult(
                success=False,
                message="Command timed out",
                execution_time=self.timeout
            )
        except Exception as e:
            return ValidationResult(
                success=False,
                message=f"Validation error: {str(e)}",
                execution_time=time.time() - start_time
            )

    def validate_python_code(self, code: str) -> ValidationResult:
        """Validate Python code syntax and basic execution."""
        start_time = time.time()

        try:
            # Check syntax
            ast.parse(code)

            # Create temporary file and execute
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name

            try:
                result = subprocess.run(
                    ['python', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )

                execution_time = time.time() - start_time

                if result.returncode == 0:
                    return ValidationResult(
                        success=True,
                        message="Python code executed successfully",
                        output=result.stdout,
                        execution_time=execution_time
                    )
                else:
                    return ValidationResult(
                        success=False,
                        message=f"Python code execution failed",
                        error=result.stderr,
                        execution_time=execution_time
                    )

            finally:
                os.unlink(temp_file)

        except SyntaxError as e:
            return ValidationResult(
                success=False,
                message=f"Python syntax error: {str(e)}",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ValidationResult(
                success=False,
                message=f"Python validation error: {str(e)}",
                execution_time=time.time() - start_time
            )

    def validate_file_exists(self, filepath: str) -> ValidationResult:
        """Validate that a file exists."""
        start_time = time.time()

        if os.path.exists(filepath):
            return ValidationResult(
                success=True,
                message=f"File {filepath} exists",
                execution_time=time.time() - start_time
            )
        else:
            return ValidationResult(
                success=False,
                message=f"File {filepath} does not exist",
                execution_time=time.time() - start_time
            )

    def validate_import(self, module_name: str) -> ValidationResult:
        """Validate that a Python module can be imported."""
        start_time = time.time()

        try:
            __import__(module_name)
            return ValidationResult(
                success=True,
                message=f"Module {module_name} imported successfully",
                execution_time=time.time() - start_time
            )
        except ImportError as e:
            return ValidationResult(
                success=False,
                message=f"Failed to import {module_name}: {str(e)}",
                execution_time=time.time() - start_time
            )


class TutorialValidator:
    """Validates complete tutorials."""

    def __init__(self):
        self.step_validator = StepValidator()

    def validate_tutorial(self, tutorial: 'Tutorial') -> ValidationReport:
        """Validate a complete tutorial."""
        start_time = time.time()
        results = []

        # Validate metadata
        metadata_result = self._validate_metadata(tutorial.metadata)
        results.append(metadata_result)

        # Validate steps
        for step in tutorial.steps:
            step_results = self._validate_step(step)
            results.extend(step_results)

        # Validate step dependencies
        dependency_result = self._validate_step_dependencies(tutorial.steps)
        results.append(dependency_result)

        # Calculate overall results
        passed = sum(1 for r in results if r.success)
        failed = len(results) - passed
        overall_success = failed == 0

        return ValidationReport(
            tutorial_id=tutorial.metadata.tutorial_id,
            overall_success=overall_success,
            total_validations=len(results),
            passed_validations=passed,
            failed_validations=failed,
            results=results,
            execution_time=time.time() - start_time
        )

    def _validate_metadata(self, metadata: 'TutorialMetadata') -> ValidationResult:
        """Validate tutorial metadata."""
        errors = []

        if not metadata.tutorial_id:
            errors.append("Missing tutorial_id")

        if not metadata.title:
            errors.append("Missing title")

        if not metadata.description:
            errors.append("Missing description")

        if metadata.estimated_time <= 0:
            errors.append("Invalid estimated_time")

        if not metadata.learning_objectives:
            errors.append("Missing learning_objectives")

        if errors:
            return ValidationResult(
                success=False,
                message="Metadata validation failed",
                details={"errors": errors}
            )

        return ValidationResult(
            success=True,
            message="Metadata validation passed"
        )

    def _validate_step(self, step: 'TutorialStep') -> List[ValidationResult]:
        """Validate a single tutorial step."""
        results = []

        # Validate basic step structure
        if not step.step_id:
            results.append(ValidationResult(
                success=False,
                message="Step missing step_id"
            ))

        if not step.title:
            results.append(ValidationResult(
                success=False,
                message=f"Step {step.step_id} missing title"
            ))

        if not step.instructions:
            results.append(ValidationResult(
                success=False,
                message=f"Step {step.step_id} missing instructions"
            ))

        # Validate code examples
        for i, code_example in enumerate(step.code_examples):
            if code_example.strip():
                result = self.step_validator.validate_python_code(code_example)
                result.message = f"Step {step.step_id} code example {i+1}: {result.message}"
                results.append(result)

        # Validate command if present
        if step.validation_command:
            result = self.step_validator.validate_command(
                step.validation_command,
                step.expected_output
            )
            result.message = f"Step {step.step_id} validation command: {result.message}"
            results.append(result)

        # If no validation issues found, add success result
        if not results:
            results.append(ValidationResult(
                success=True,
                message=f"Step {step.step_id} validation passed"
            ))

        return results

    def _validate_step_dependencies(self, steps: List['TutorialStep']) -> ValidationResult:
        """Validate step dependency graph."""
        step_ids = {step.step_id for step in steps}

        for step in steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    return ValidationResult(
                        success=False,
                        message=f"Step {step.step_id} has invalid dependency: {dep}"
                    )

        # Check for circular dependencies
        if self._has_circular_dependencies(steps):
            return ValidationResult(
                success=False,
                message="Circular dependencies detected in tutorial steps"
            )

        return ValidationResult(
            success=True,
            message="Step dependencies validation passed"
        )

    def _has_circular_dependencies(self, steps: List['TutorialStep']) -> bool:
        """Check for circular dependencies in steps."""
        # Create dependency graph
        dependencies = {step.step_id: step.dependencies for step in steps}

        # Use DFS to detect cycles
        visited = set()
        rec_stack = set()

        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in dependencies.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for step_id in dependencies:
            if step_id not in visited:
                if has_cycle(step_id):
                    return True

        return False


class TutorialTestRunner:
    """Runs automated tests for tutorial validation."""

    def __init__(self):
        self.validator = TutorialValidator()

    def run_validation_suite(self, tutorial_manager: 'TutorialManager') -> Dict[str, ValidationReport]:
        """Run validation suite for all tutorials."""
        reports = {}

        for tutorial_id, tutorial in tutorial_manager.tutorials.items():
            print(f"🔍 Validating tutorial: {tutorial.metadata.title}")
            report = self.validator.validate_tutorial(tutorial)
            reports[tutorial_id] = report

            if report.overall_success:
                print(f"  ✅ {report.success_rate:.1f}% success rate")
            else:
                print(f"  ❌ {report.success_rate:.1f}% success rate ({report.failed_validations} failures)")

        return reports

    def generate_validation_report(self, reports: Dict[str, ValidationReport]) -> str:
        """Generate comprehensive validation report."""
        total_tutorials = len(reports)
        successful_tutorials = sum(1 for r in reports.values() if r.overall_success)

        report = []
        report.append("# Tutorial Validation Report")
        report.append("=" * 50)
        report.append(f"Total tutorials: {total_tutorials}")
        report.append(f"Successful tutorials: {successful_tutorials}")
        report.append(f"Failed tutorials: {total_tutorials - successful_tutorials}")

        if total_tutorials > 0:
            report.append(f"Overall success rate: {(successful_tutorials / total_tutorials) * 100:.1f}%")
        else:
            report.append("Overall success rate: N/A (no tutorials found)")
        report.append("")

        for tutorial_id, validation_report in reports.items():
            report.append(f"## Tutorial: {tutorial_id}")
            report.append(f"- Success rate: {validation_report.success_rate:.1f}%")
            report.append(f"- Validations: {validation_report.passed_validations}/{validation_report.total_validations}")
            report.append(f"- Execution time: {validation_report.execution_time:.2f}s")

            if not validation_report.overall_success:
                report.append("### Failures:")
                for result in validation_report.results:
                    if not result.success:
                        report.append(f"  - {result.message}")

            report.append("")

        return "\n".join(report)

    def save_validation_report(self, reports: Dict[str, ValidationReport], output_file: str):
        """Save validation report to file."""
        report_text = self.generate_validation_report(reports)

        with open(output_file, 'w') as f:
            f.write(report_text)

        print(f"📋 Validation report saved to: {output_file}")


# CLI integration for validation
def run_validation_cli():
    """Run validation from command line."""
    import sys
    from pathlib import Path

    # Add tutorial framework to path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from framework.tutorial_manager import TutorialManager

    # Initialize components
    tutorial_manager = TutorialManager(tutorial_path=".")
    test_runner = TutorialTestRunner()

    # Run validation
    print("🚀 Starting tutorial validation suite...")
    reports = test_runner.run_validation_suite(tutorial_manager)

    # Generate and save report
    output_file = "tutorial_validation_report.md"
    test_runner.save_validation_report(reports, output_file)

    # Print summary
    total_tutorials = len(reports)
    successful_tutorials = sum(1 for r in reports.values() if r.overall_success)

    print(f"\n📊 Validation Summary:")
    print(f"Successful tutorials: {successful_tutorials}/{total_tutorials}")

    if total_tutorials > 0:
        print(f"Overall success rate: {(successful_tutorials / total_tutorials) * 100:.1f}%")

        if successful_tutorials == total_tutorials:
            print("🎉 All tutorials validated successfully!")
            return 0
        else:
            print("❌ Some tutorials failed validation. Check the report for details.")
            return 1
    else:
        print("❌ No tutorials found to validate!")
        return 1


if __name__ == '__main__':
    import sys
    exit_code = run_validation_cli()
    sys.exit(exit_code)
