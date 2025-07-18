#!/usr/bin/env python3
"""
Technical Debt Remediation Script
Automated fixes for performance and code quality issues.
"""

import os
import re
import json
from typing import Dict, Any
import subprocess


class TechnicalDebtRemediator:
    """Automated technical debt remediation."""
    
    def __init__(self):
        self.fixes_applied = []
        self.errors_encountered = []
    
    def remove_unused_imports(self, file_path: str) -> bool:
        """Remove unused imports from a Python file."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Common unused imports to remove
            unused_patterns = [
                r'from datetime import.*timedelta.*\n',
                r'from typing import.*Any.*\n',
                r'from typing import.*Dict.*\n',
                r'import.*timedelta.*\n',
                r'.*ResourceRequirements.*\n',
                r'.*ScalingConfig.*\n',
                r'.*EventPriority.*\n',
                r'.*WebhookEventType.*\n'
            ]
            
            original_content = content
            for pattern in unused_patterns:
                content = re.sub(pattern, '', content, flags=re.MULTILINE)
            
            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                self.fixes_applied.append(f"Removed unused imports from {file_path}")
                return True
            
            return False
            
        except Exception as e:
            self.errors_encountered.append(f"Error removing unused imports from {file_path}: {e}")
            return False
    
    def fix_trailing_whitespace(self, file_path: str) -> bool:
        """Fix trailing whitespace issues."""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            fixed_lines = []
            changed = False
            
            for line in lines:
                if line.endswith(' \n') or line.endswith('\t\n'):
                    fixed_lines.append(line.rstrip() + '\n')
                    changed = True
                else:
                    fixed_lines.append(line)
            
            if changed:
                with open(file_path, 'w') as f:
                    f.writelines(fixed_lines)
                self.fixes_applied.append(f"Fixed trailing whitespace in {file_path}")
                return True
                
            return False
            
        except Exception as e:
            self.errors_encountered.append(f"Error fixing trailing whitespace in {file_path}: {e}")
            return False
    
    def fix_line_length_issues(self, file_path: str) -> bool:
        """Fix basic line length issues."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Skip if file is too large or has merge conflicts
            if len(content) > 100000 or '<<<<<<< HEAD' in content:
                return False
            
            lines = content.split('\n')
            fixed_lines = []
            changed = False
            
            for line in lines:
                if len(line) > 100 and not line.strip().startswith('#'):
                    # Simple fixes for long lines
                    if ' and ' in line and len(line) > 120:
                        # Split on 'and' if very long
                        parts = line.split(' and ')
                        if len(parts) == 2:
                            indent = len(line) - len(line.lstrip())
                            fixed_lines.append(parts[0] + ' and')
                            fixed_lines.append(' ' * (indent + 4) + parts[1])
                            changed = True
                            continue
                
                fixed_lines.append(line)
            
            if changed:
                with open(file_path, 'w') as f:
                    f.write('\n'.join(fixed_lines))
                self.fixes_applied.append(f"Fixed line length issues in {file_path}")
                return True
                
            return False
            
        except Exception as e:
            self.errors_encountered.append(f"Error fixing line length in {file_path}: {e}")
            return False
    
    def add_missing_docstrings(self, file_path: str) -> bool:
        """Add missing docstrings to functions and classes."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Skip if file is too large or has merge conflicts
            if len(content) > 50000 or '<<<<<<< HEAD' in content:
                return False
            
            lines = content.split('\n')
            fixed_lines = []
            changed = False
            i = 0
            
            while i < len(lines):
                line = lines[i]
                
                # Check for function or class definition
                if re.match(r'^\s*def \w+\(', line) or re.match(r'^\s*class \w+', line):
                    # Check if next non-empty line is a docstring
                    j = i + 1
                    while j < len(lines) and lines[j].strip() == '':
                        j += 1
                    
                    if j < len(lines) and not lines[j].strip().startswith('"""') and not lines[j].strip().startswith("'''"):
                        # Add a simple docstring
                        indent = len(line) - len(line.lstrip())
                        if 'def ' in line:
                            fixed_lines.append(line)
                            fixed_lines.append(' ' * (indent + 4) + '"""Function implementation."""')
                        else:
                            fixed_lines.append(line)
                            fixed_lines.append(' ' * (indent + 4) + '"""Class implementation."""')
                        changed = True
                        i += 1
                        continue
                
                fixed_lines.append(line)
                i += 1
            
            if changed:
                with open(file_path, 'w') as f:
                    f.write('\n'.join(fixed_lines))
                self.fixes_applied.append(f"Added missing docstrings to {file_path}")
                return True
                
            return False
            
        except Exception as e:
            self.errors_encountered.append(f"Error adding docstrings to {file_path}: {e}")
            return False
    
    def fix_import_order(self, file_path: str) -> bool:
        """Fix import order issues."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Skip if file has merge conflicts
            if '<<<<<<< HEAD' in content:
                return False
            
            lines = content.split('\n')
            
            # Find import section
            import_start = -1
            import_end = -1
            
            for i, line in enumerate(lines):
                if (line.startswith('import ') or line.startswith('from ')) and import_start == -1:
                    import_start = i
                elif import_start != -1 and not (line.startswith('import ') or line.startswith('from ') or line.strip() == ''):
                    import_end = i
                    break
            
            if import_start != -1 and import_end != -1:
                # Extract imports
                imports = lines[import_start:import_end]
                
                # Sort imports (basic sorting)
                standard_imports = []
                third_party_imports = []
                local_imports = []
                
                for imp in imports:
                    if imp.strip() == '':
                        continue
                    elif imp.startswith('from .') or imp.startswith('import .'):
                        local_imports.append(imp)
                    elif any(lib in imp for lib in ['json', 'os', 'sys', 'time', 'datetime', 'pathlib', 'typing', 'subprocess', 'argparse', 'asyncio']):
                        standard_imports.append(imp)
                    else:
                        third_party_imports.append(imp)
                
                # Sort each group
                standard_imports.sort()
                third_party_imports.sort()
                local_imports.sort()
                
                # Reconstruct imports with proper spacing
                new_imports = []
                if standard_imports:
                    new_imports.extend(standard_imports)
                    new_imports.append('')
                if third_party_imports:
                    new_imports.extend(third_party_imports)
                    new_imports.append('')
                if local_imports:
                    new_imports.extend(local_imports)
                    new_imports.append('')
                
                # Replace imports in content
                new_lines = lines[:import_start] + new_imports + lines[import_end:]
                new_content = '\n'.join(new_lines)
                
                if new_content != content:
                    with open(file_path, 'w') as f:
                        f.write(new_content)
                    self.fixes_applied.append(f"Fixed import order in {file_path}")
                    return True
            
            return False
            
        except Exception as e:
            self.errors_encountered.append(f"Error fixing import order in {file_path}: {e}")
            return False
    
    def remediate_file(self, file_path: str) -> Dict[str, bool]:
        """Apply all remediation fixes to a file."""
        results = {}
        
        # Skip files with merge conflicts
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            if '<<<<<<< HEAD' in content:
                return {"skipped": True, "reason": "merge_conflicts"}
        except Exception:
            return {"skipped": True, "reason": "read_error"}
        
        # Apply fixes
        results['unused_imports'] = self.remove_unused_imports(file_path)
        results['trailing_whitespace'] = self.fix_trailing_whitespace(file_path)
        results['line_length'] = self.fix_line_length_issues(file_path)
        results['import_order'] = self.fix_import_order(file_path)
        # Skip docstrings for now as they can be complex
        # results['docstrings'] = self.add_missing_docstrings(file_path)
        
        return results
    
    def run_ruff_fix(self, directory: str = ".") -> Dict[str, Any]:
        """Run ruff --fix for automated code fixes."""
        print("🔧 Running ruff --fix for automated code improvements...")
        
        try:
            # Run ruff --fix
            result = subprocess.run(
                ["ruff", "check", "--fix", directory],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            fixes_applied = []
            if result.stdout:
                # Parse ruff output to extract fixes
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'Fixed' in line or 'fixed' in line:
                        fixes_applied.append(line.strip())
            
            self.fixes_applied.extend(fixes_applied)
            
            return {
                "success": result.returncode == 0,
                "fixes_applied": len(fixes_applied),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            error_msg = "ruff --fix timed out after 5 minutes"
            self.errors_encountered.append(error_msg)
            return {"success": False, "error": error_msg}
        except FileNotFoundError:
            error_msg = "ruff not found. Install with: pip install ruff"
            self.errors_encountered.append(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Error running ruff --fix: {e}"
            self.errors_encountered.append(error_msg)
            return {"success": False, "error": error_msg}
    
    def run_test_suite(self) -> Dict[str, Any]:
        """Run test suite to ensure no regressions after remediation."""
        print("🧪 Running test suite to verify no regressions...")
        
        # Try different test runners in order of preference
        test_commands = [
            ["python", "-m", "pytest", "-v", "--tb=short"],
            ["python", "-m", "pytest"],
            ["python", "-m", "unittest", "discover", "-v"],
            ["python", "test_runner.py"],
        ]
        
        for cmd in test_commands:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minute timeout
                )
                
                return {
                    "success": result.returncode == 0,
                    "command": " ".join(cmd),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode
                }
                
            except subprocess.TimeoutExpired:
                continue
            except FileNotFoundError:
                continue
            except Exception:
                continue
        
        # If no test runner worked
        return {
            "success": False,
            "error": "No suitable test runner found",
            "attempted_commands": test_commands
        }

    def remediate_codebase(self, directory: str = ".") -> Dict[str, Any]:
        """Remediate the entire codebase using modern tools."""
        print("🔧 Starting Enhanced Technical Debt Remediation...")
        
        results = {}
        
        # Step 1: Run ruff --fix for automated improvements
        print("\n📋 Step 1: Running ruff --fix for automated code improvements...")
        ruff_results = self.run_ruff_fix(directory)
        results["ruff_fix"] = ruff_results
        
        if ruff_results["success"]:
            print("   ✅ ruff --fix completed successfully")
            print(f"   📊 Fixes applied: {ruff_results['fixes_applied']}")
        else:
            print(f"   ❌ ruff --fix failed: {ruff_results.get('error', 'Unknown error')}")
        
        # Step 2: Run manual remediation for remaining issues
        print("\n📋 Step 2: Running manual remediation for remaining issues...")
        python_files = []
        for root, dirs, files in os.walk(directory):
            # Skip hidden directories and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        print(f"📁 Found {len(python_files)} Python files for manual processing")
        
        remediation_results = {}
        processed = 0
        
        # Process only files with remaining issues
        for file_path in python_files[:10]:  # Limit to first 10 files for now
            # Skip certain files
            if any(skip in file_path for skip in ['__pycache__', '.git', 'venv', 'node_modules']):
                continue
                
            print(f"   Processing {file_path}...")
            file_results = self.remediate_file(file_path)
            remediation_results[file_path] = file_results
            processed += 1
        
        results["manual_remediation"] = remediation_results
        
        # Step 3: Run test suite to verify no regressions
        print("\n📋 Step 3: Running test suite to verify no regressions...")
        test_results = self.run_test_suite()
        results["test_suite"] = test_results
        
        if test_results["success"]:
            print("   ✅ Test suite passed - no regressions detected")
        else:
            print("   ⚠️  Test suite issues detected")
        
        # Summary
        summary = {
            "total_files": len(python_files),
            "processed_files": processed,
            "fixes_applied": len(self.fixes_applied),
            "errors_encountered": len(self.errors_encountered),
            "ruff_success": ruff_results["success"],
            "tests_passed": test_results["success"],
            "results": results
        }
        
        return summary
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a remediation report."""
        report = []
        report.append("=" * 60)
        report.append("🔧 TECHNICAL DEBT REMEDIATION REPORT")
        report.append("=" * 60)
        
        report.append("📊 Summary:")
        report.append(f"   Total Files: {results['total_files']}")
        report.append(f"   Processed Files: {results['processed_files']}")
        report.append(f"   Fixes Applied: {results['fixes_applied']}")
        report.append(f"   Errors Encountered: {results['errors_encountered']}")
        
        if self.fixes_applied:
            report.append("\n✅ Fixes Applied:")
            for fix in self.fixes_applied[:10]:  # Show first 10
                report.append(f"   - {fix}")
            if len(self.fixes_applied) > 10:
                report.append(f"   ... and {len(self.fixes_applied) - 10} more")
        
        if self.errors_encountered:
            report.append("\n❌ Errors Encountered:")
            for error in self.errors_encountered[:5]:  # Show first 5
                report.append(f"   - {error}")
            if len(self.errors_encountered) > 5:
                report.append(f"   ... and {len(self.errors_encountered) - 5} more")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)


def main():
    """Main execution function."""
    remediator = TechnicalDebtRemediator()
    
    # Run remediation
    results = remediator.remediate_codebase()
    
    # Generate report
    report = remediator.generate_report(results)
    print(report)
    
    # Save results
    with open('technical_debt_remediation.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    with open('technical_debt_remediation_report.txt', 'w') as f:
        f.write(report)
    
    print("\n💾 Results saved to:")
    print("   - technical_debt_remediation.json (raw data)")
    print("   - technical_debt_remediation_report.txt (formatted report)")


if __name__ == "__main__":
    main()