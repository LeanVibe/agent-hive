#!/usr/bin/env python3
"""
Tutorial Content Validation Script

This script validates tutorial content without executing code examples,
focusing on syntax, structure, and completeness.
"""

import sys
import json
import ast
from pathlib import Path
from typing import Dict, List, Any

# Add framework to path
sys.path.insert(0, str(Path(__file__).parent))

from framework.tutorial_manager import TutorialManager, Tutorial

def _looks_like_python_code(code: str) -> bool:
    """Heuristic to determine if code looks like Python."""
    code = code.strip()

    # Common Python indicators
    python_indicators = [
        'import ', 'from ', 'def ', 'class ', 'if __name__',
        'print(', 'async def', 'await ', 'return ', 'yield ',
        'with ', 'try:', 'except:', 'finally:', 'raise ',
        'lambda ', '@', 'self.', '__init__'
    ]

    # Shell command indicators
    shell_indicators = [
        'git ', 'cd ', 'ls ', 'mkdir ', 'rm ', 'cp ', 'mv ',
        'pip ', 'npm ', 'yarn ', 'docker ', 'curl ', 'wget ',
        'python -', 'python3 -', 'uv ', 'pipenv ', 'poetry '
    ]

    # Check for Python indicators
    for indicator in python_indicators:
        if indicator in code:
            return True

    # Check for shell indicators (if found, likely not Python)
    for indicator in shell_indicators:
        if indicator in code:
            return False

    # If it has typical Python syntax patterns
    if ('=' in code and '(' in code and ')' in code) or \
       (code.startswith('from ') or code.startswith('import ')) or \
       ('def ' in code or 'class ' in code):
        return True

    return False

def validate_tutorial_content(tutorial: Tutorial) -> Dict[str, Any]:
    """Validate tutorial content comprehensively."""
    validation_results = {
        'tutorial_id': tutorial.metadata.tutorial_id,
        'title': tutorial.metadata.title,
        'issues': [],
        'warnings': [],
        'success': True
    }

    # Validate metadata
    if not tutorial.metadata.tutorial_id:
        validation_results['issues'].append("Missing tutorial_id")
        validation_results['success'] = False

    if not tutorial.metadata.title:
        validation_results['issues'].append("Missing title")
        validation_results['success'] = False

    if not tutorial.metadata.description:
        validation_results['issues'].append("Missing description")
        validation_results['success'] = False

    if tutorial.metadata.estimated_time <= 0:
        validation_results['issues'].append("Invalid estimated_time")
        validation_results['success'] = False

    if not tutorial.metadata.learning_objectives:
        validation_results['issues'].append("Missing learning_objectives")
        validation_results['success'] = False

    if not tutorial.steps:
        validation_results['issues'].append("No tutorial steps defined")
        validation_results['success'] = False
        return validation_results

    # Validate steps
    step_ids = set()
    for step in tutorial.steps:
        # Check for duplicate step IDs
        if step.step_id in step_ids:
            validation_results['issues'].append(f"Duplicate step_id: {step.step_id}")
            validation_results['success'] = False
        else:
            step_ids.add(step.step_id)

        # Validate step structure
        if not step.step_id:
            validation_results['issues'].append("Step missing step_id")
            validation_results['success'] = False

        if not step.title:
            validation_results['issues'].append(f"Step {step.step_id} missing title")
            validation_results['success'] = False

        if not step.instructions:
            validation_results['issues'].append(f"Step {step.step_id} missing instructions")
            validation_results['success'] = False

        # Validate code examples syntax (without execution)
        for i, code_example in enumerate(step.code_examples):
            if code_example.strip():
                # Check if it's a Python code example
                if _looks_like_python_code(code_example):
                    try:
                        ast.parse(code_example)
                    except SyntaxError as e:
                        validation_results['issues'].append(
                            f"Step {step.step_id} code example {i+1} Python syntax error: {e}"
                        )
                        validation_results['success'] = False
                    except Exception as e:
                        validation_results['warnings'].append(
                            f"Step {step.step_id} code example {i+1} Python parsing warning: {e}"
                        )
                else:
                    # For non-Python code (shell commands, etc.), just check it's not empty
                    if not code_example.strip():
                        validation_results['issues'].append(
                            f"Step {step.step_id} code example {i+1} is empty"
                        )
                        validation_results['success'] = False

        # Validate dependencies
        for dep in step.dependencies:
            if dep not in step_ids:
                validation_results['issues'].append(
                    f"Step {step.step_id} has invalid dependency: {dep}"
                )
                validation_results['success'] = False

    # Check for circular dependencies
    if _has_circular_dependencies(tutorial.steps):
        validation_results['issues'].append("Circular dependencies detected")
        validation_results['success'] = False

    return validation_results

def _has_circular_dependencies(steps: List) -> bool:
    """Check for circular dependencies in tutorial steps."""
    dependencies = {step.step_id: step.dependencies for step in steps}

    visited = set()
    rec_stack = set()

    def has_cycle(node):
        if node in rec_stack:
            return True
        if node in visited:
            return False

        visited.add(node)
        rec_stack.add(node)

        for neighbor in dependencies.get(node, []):
            if has_cycle(neighbor):
                return True

        rec_stack.remove(node)
        return False

    for step_id in dependencies:
        if step_id not in visited:
            if has_cycle(step_id):
                return True

    return False

def main():
    """Main validation function."""
    print("🚀 Starting comprehensive tutorial content validation...\n")

    # Initialize tutorial manager
    tutorial_manager = TutorialManager(tutorial_path=".")

    if not tutorial_manager.tutorials:
        print("❌ No tutorials found to validate!")
        return 1

    all_results = []
    overall_success = True

    # Validate each tutorial
    for tutorial_id, tutorial in tutorial_manager.tutorials.items():
        print(f"🔍 Validating: {tutorial.metadata.title}")

        results = validate_tutorial_content(tutorial)
        all_results.append(results)

        if results['success']:
            print("  ✅ Validation passed")
        else:
            print(f"  ❌ Validation failed ({len(results['issues'])} issues)")
            overall_success = False
            for issue in results['issues']:
                print(f"    - {issue}")

        if results['warnings']:
            print(f"  ⚠️  {len(results['warnings'])} warnings")
            for warning in results['warnings']:
                print(f"    - {warning}")

        print()

    # Generate summary report
    total_tutorials = len(all_results)
    successful_tutorials = sum(1 for r in all_results if r['success'])

    print("📊 Validation Summary:")
    print("=" * 50)
    print(f"Total tutorials: {total_tutorials}")
    print(f"Successful tutorials: {successful_tutorials}")
    print(f"Failed tutorials: {total_tutorials - successful_tutorials}")
    print(f"Overall success rate: {(successful_tutorials / total_tutorials) * 100:.1f}%")

    # Save detailed report
    report_path = "tutorial_content_validation_report.json"
    with open(report_path, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\n📋 Detailed validation report saved to: {report_path}")

    if overall_success:
        print("🎉 All tutorials validated successfully!")
        return 0
    else:
        print("❌ Some tutorials have validation issues. Check the report for details.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
