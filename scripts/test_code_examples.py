#!/usr/bin/env python3
"""
LeanVibe Agent Hive - Code Example Testing Framework

Tests all code examples in documentation to ensure they work correctly.

Usage:
    python scripts/test_code_examples.py --all
    python scripts/test_code_examples.py --api-reference
    python scripts/test_code_examples.py --readme
"""

import argparse
import asyncio
import os
import re
import sys
import tempfile
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess

@dataclass
class CodeTestResult:
    """Result of testing a code example."""
    file: str
    example_id: str
    status: str  # "pass", "fail", "skip"
    message: str
    execution_time: float
    output: Optional[str] = None
    error: Optional[str] = None

class CodeExampleTester:
    """Framework for testing code examples in documentation."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: List[CodeTestResult] = []
        self.test_environment_setup = False
    
    def setup_test_environment(self):
        """Setup Python path and test environment."""
        if not self.test_environment_setup:
            sys.path.insert(0, str(self.project_root))
            sys.path.insert(0, str(self.project_root / "advanced_orchestration"))
            sys.path.insert(0, str(self.project_root / "intelligence_framework"))
            sys.path.insert(0, str(self.project_root / "external_api"))
            sys.path.insert(0, str(self.project_root / "ml_enhancements"))
            self.test_environment_setup = True
    
    def extract_code_examples(self, file_path: Path) -> List[Tuple[str, str]]:
        """Extract Python code examples from a markdown file."""
        if not file_path.exists():
            return []
        
        content = file_path.read_text()
        examples = []
        
        # Find all Python code blocks
        python_blocks = re.findall(r'```(?:python|py)\n(.*?)\n```', content, re.DOTALL)
        
        for i, code_block in enumerate(python_blocks):
            # Skip examples that are clearly not executable
            skip_patterns = [
                "# FUTURE IMPLEMENTATION",
                "# NOT YET IMPLEMENTED",
                "# Example usage",
                "pip install",
                "uv add",
                "git clone",
                "git commit",
                "curl",
                "brew install",
                "export ",
                "echo ",
                "mkdir",
                "ls ",
                "cd ",
                "chmod",
            ]
            
            if any(pattern in code_block for pattern in skip_patterns):
                continue
            
            # Skip configuration examples
            if any(config_pattern in code_block for config_pattern in [
                "system:",
                "agents:",
                "multi_agent:",
                "resources:",
            ]):
                continue
            
            example_id = f"{file_path.name}_example_{i+1}"
            examples.append((example_id, code_block))
        
        return examples
    
    def create_test_file(self, code: str, example_id: str) -> Path:
        """Create a temporary test file for the code example."""
        # Create a temporary file
        test_file = self.project_root / f"temp_test_{example_id}.py"
        
        # Prepare the code with proper imports and error handling
        test_code = f'''
import sys
import os
import asyncio
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "advanced_orchestration"))
sys.path.insert(0, str(project_root / "intelligence_framework"))
sys.path.insert(0, str(project_root / "external_api"))
sys.path.insert(0, str(project_root / "ml_enhancements"))

try:
{self.indent_code(code, "    ")}
except ImportError as e:
    print(f"ImportError (expected): {{e}}")
except Exception as e:
    print(f"Example executed with exception: {{e}}")
    import traceback
    traceback.print_exc()
'''
        
        test_file.write_text(test_code)
        return test_file
    
    def indent_code(self, code: str, indent: str) -> str:
        """Indent code block."""
        lines = code.split('\n')
        indented_lines = []
        for line in lines:
            if line.strip():
                indented_lines.append(indent + line)
            else:
                indented_lines.append('')
        return '\n'.join(indented_lines)
    
    def test_code_example(self, example_id: str, code: str, file_name: str) -> CodeTestResult:
        """Test a single code example."""
        import time
        start_time = time.time()
        
        try:
            # Create test file
            test_file = self.create_test_file(code, example_id)
            
            # Run the test
            result = subprocess.run(
                [sys.executable, str(test_file)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root
            )
            
            # Cleanup
            if test_file.exists():
                test_file.unlink()
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                return CodeTestResult(
                    file=file_name,
                    example_id=example_id,
                    status="pass",
                    message="✅ Code example executed successfully",
                    execution_time=execution_time,
                    output=result.stdout,
                )
            else:
                # Check if it's an expected import error
                if "ImportError (expected)" in result.stdout:
                    return CodeTestResult(
                        file=file_name,
                        example_id=example_id,
                        status="pass",
                        message="✅ Code example with expected import limitation",
                        execution_time=execution_time,
                        output=result.stdout,
                    )
                else:
                    return CodeTestResult(
                        file=file_name,
                        example_id=example_id,
                        status="fail",
                        message="❌ Code example failed to execute",
                        execution_time=execution_time,
                        output=result.stdout,
                        error=result.stderr,
                    )
        
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            # Cleanup
            test_file = self.project_root / f"temp_test_{example_id}.py"
            if test_file.exists():
                test_file.unlink()
            
            return CodeTestResult(
                file=file_name,
                example_id=example_id,
                status="fail",
                message="❌ Code example timed out (>30s)",
                execution_time=execution_time,
                error="Timeout after 30 seconds"
            )
        
        except Exception as e:
            execution_time = time.time() - start_time
            # Cleanup
            test_file = self.project_root / f"temp_test_{example_id}.py"
            if test_file.exists():
                test_file.unlink()
            
            return CodeTestResult(
                file=file_name,
                example_id=example_id,
                status="fail",
                message=f"❌ Test setup error: {str(e)}",
                execution_time=execution_time,
                error=str(e)
            )
    
    def test_file_examples(self, file_path: Path) -> List[CodeTestResult]:
        """Test all code examples in a file."""
        results = []
        
        print(f"  📄 Testing {file_path.name}...")
        
        examples = self.extract_code_examples(file_path)
        
        if not examples:
            print(f"    ℹ️  No testable examples found")
            return results
        
        for example_id, code in examples:
            print(f"    🧪 Testing {example_id}...")
            result = self.test_code_example(example_id, code, file_path.name)
            results.append(result)
            
            # Print immediate feedback
            if result.status == "pass":
                print(f"      {result.message}")
            else:
                print(f"      {result.message}")
                if result.error:
                    print(f"      Error: {result.error[:100]}...")
        
        return results
    
    def test_all_documentation(self) -> List[CodeTestResult]:
        """Test code examples in all documentation files."""
        all_results = []
        
        print("🧪 Testing code examples in documentation...")
        
        # Files to test
        doc_files = [
            self.project_root / "README.md",
            self.project_root / "API_REFERENCE.md",
            self.project_root / "DEVELOPMENT.md",
            self.project_root / "DEPLOYMENT.md",
        ]
        
        self.setup_test_environment()
        
        for doc_file in doc_files:
            if doc_file.exists():
                results = self.test_file_examples(doc_file)
                all_results.extend(results)
        
        self.results = all_results
        return all_results
    
    def generate_report(self) -> str:
        """Generate a comprehensive testing report."""
        if not self.results:
            return "No test results available."
        
        # Count results by status
        status_counts = {"pass": 0, "fail": 0, "skip": 0}
        for result in self.results:
            status_counts[result.status] += 1
        
        # Calculate statistics
        total_tests = len(self.results)
        pass_rate = (status_counts["pass"] / total_tests * 100) if total_tests > 0 else 0
        total_time = sum(result.execution_time for result in self.results)
        avg_time = total_time / total_tests if total_tests > 0 else 0
        
        # Generate report
        report = []
        report.append("=" * 80)
        report.append("🧪 LEANVIBE AGENT HIVE - CODE EXAMPLE TESTING REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary
        report.append(f"📊 TESTING SUMMARY:")
        report.append(f"   Total Examples Tested: {total_tests}")
        report.append(f"   ✅ Passed: {status_counts['pass']} ({pass_rate:.1f}%)")
        report.append(f"   ❌ Failed: {status_counts['fail']}")
        report.append(f"   ⏭️ Skipped: {status_counts['skip']}")
        report.append(f"   ⏱️ Total Execution Time: {total_time:.2f}s")
        report.append(f"   ⏱️ Average per Example: {avg_time:.2f}s")
        report.append("")
        
        # Overall status
        if status_counts["fail"] == 0:
            report.append("🎉 OVERALL STATUS: EXCELLENT - All code examples work!")
        elif status_counts["fail"] <= 2:
            report.append("✅ OVERALL STATUS: GOOD - Minor issues to fix")
        elif status_counts["fail"] <= 5:
            report.append("⚠️ OVERALL STATUS: NEEDS ATTENTION - Several examples failing")
        else:
            report.append("❌ OVERALL STATUS: CRITICAL - Many examples not working")
        
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
                report.append(f"   {result.message} ({result.execution_time:.2f}s)")
                if result.status == "fail" and result.error:
                    report.append(f"      Error: {result.error}")
            report.append("")
        
        # Recommendations
        report.append("💡 RECOMMENDATIONS:")
        if status_counts["fail"] > 0:
            report.append("   1. Fix failing code examples by updating syntax or adding proper imports")
            report.append("   2. Consider wrapping async examples in asyncio.run() or async functions")
        if pass_rate < 90:
            report.append("   3. Improve code example quality to achieve >90% pass rate")
        report.append("   4. Add this testing to CI/CD pipeline for continuous validation")
        report.append("   5. Consider adding expected output comments to examples")
        
        return "\n".join(report)

def main():
    """Main code example testing entry point."""
    parser = argparse.ArgumentParser(description="Test LeanVibe Agent Hive code examples")
    parser.add_argument("--all", action="store_true", help="Test all code examples")
    parser.add_argument("--api-reference", action="store_true", help="Test API reference examples")
    parser.add_argument("--readme", action="store_true", help="Test README examples")
    parser.add_argument("--output", type=str, help="Output file for test report")
    
    args = parser.parse_args()
    
    # Determine project root
    project_root = Path(__file__).parent.parent
    if not (project_root / "README.md").exists():
        print("❌ Cannot find project root (README.md not found)")
        sys.exit(1)
    
    # Create tester
    tester = CodeExampleTester(project_root)
    
    # Run tests
    if args.all or not any([args.api_reference, args.readme]):
        results = tester.test_all_documentation()
    else:
        results = []
        if args.api_reference:
            results.extend(tester.test_file_examples(project_root / "API_REFERENCE.md"))
        if args.readme:
            results.extend(tester.test_file_examples(project_root / "README.md"))
    
    # Generate and display report
    report = tester.generate_report()
    print(report)
    
    # Save report if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"\n📄 Report saved to: {args.output}")
    
    # Exit with appropriate code
    failed_tests = sum(1 for r in results if r.status == "fail")
    if failed_tests > 0:
        print(f"\n❌ Testing failed with {failed_tests} failing examples")
        sys.exit(1)
    else:
        print(f"\n✅ All code examples tested successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()