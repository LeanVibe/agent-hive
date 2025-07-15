#!/usr/bin/env python3
"""
LeanVibe Agent Hive - Documentation Issue Auto-Fix

Automatically fixes common documentation issues identified by validation.

Usage:
    python scripts/fix_documentation_issues.py --all
    python scripts/fix_documentation_issues.py --async-examples
    python scripts/fix_documentation_issues.py --yaml-syntax
"""

import argparse
import re
from pathlib import Path
from typing import List, Tuple

class DocumentationFixer:
    """Automatic documentation issue fixer."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.fixes_applied = []
    
    def fix_async_code_examples(self) -> List[str]:
        """Fix async code examples by wrapping them in async functions."""
        fixes = []
        
        doc_files = [
            self.project_root / "API_REFERENCE.md",
            self.project_root / "DEVELOPMENT.md",
            self.project_root / "README.md",
        ]
        
        for doc_file in doc_files:
            if not doc_file.exists():
                continue
            
            content = doc_file.read_text()
            original_content = content
            
            # Find Python code blocks with await statements
            def fix_async_block(match):
                code_block = match.group(1)
                
                # Check if it contains await but isn't already in an async function
                if 'await ' in code_block and 'async def' not in code_block and 'asyncio.run' not in code_block:
                    # Wrap in async function
                    lines = code_block.split('\n')
                    
                    # Add proper async wrapper
                    wrapped_lines = [
                        'import asyncio',
                        '',
                        'async def main():',
                    ]
                    
                    # Indent existing lines
                    for line in lines:
                        if line.strip():
                            wrapped_lines.append('    ' + line)
                        else:
                            wrapped_lines.append('')
                    
                    wrapped_lines.extend([
                        '',
                        'if __name__ == "__main__":',
                        '    asyncio.run(main())'
                    ])
                    
                    return f"```python\n{chr(10).join(wrapped_lines)}\n```"
                
                return match.group(0)
            
            # Apply fix to Python code blocks
            content = re.sub(
                r'```(?:python|py)\n(.*?)\n```',
                fix_async_block,
                content,
                flags=re.DOTALL
            )
            
            if content != original_content:
                doc_file.write_text(content)
                fixes.append(f"Fixed async examples in {doc_file.name}")
        
        return fixes
    
    def fix_yaml_multi_document_issues(self) -> List[str]:
        """Fix YAML multi-document syntax issues."""
        fixes = []
        
        deployment_file = self.project_root / "DEPLOYMENT.md"
        if not deployment_file.exists():
            return fixes
        
        content = deployment_file.read_text()
        original_content = content
        
        # Fix YAML blocks with multi-document issues
        def fix_yaml_block(match):
            yaml_content = match.group(1)
            
            # If it has multiple documents without proper separation, fix it
            if yaml_content.count('apiVersion:') > 1 and '---' not in yaml_content:
                # Split by apiVersion and rejoin with proper separators
                parts = yaml_content.split('apiVersion:')
                if len(parts) > 2:
                    fixed_parts = [parts[0]]  # Keep any comments at the start
                    for i, part in enumerate(parts[1:], 1):
                        if i > 1:
                            fixed_parts.append('---\n')
                        fixed_parts.append('apiVersion:' + part)
                    
                    return f"```yaml\n{''.join(fixed_parts)}\n```"
            
            return match.group(0)
        
        # Apply fix to YAML code blocks
        content = re.sub(
            r'```(?:yaml|yml)\n(.*?)\n```',
            fix_yaml_block,
            content,
            flags=re.DOTALL
        )
        
        if content != original_content:
            deployment_file.write_text(content)
            fixes.append(f"Fixed YAML syntax in {deployment_file.name}")
        
        return fixes
    
    def fix_function_signature_syntax(self) -> List[str]:
        """Fix function signature syntax issues."""
        fixes = []
        
        doc_files = [
            self.project_root / "DEVELOPMENT.md",
            self.project_root / "API_REFERENCE.md",
        ]
        
        for doc_file in doc_files:
            if not doc_file.exists():
                continue
            
            content = doc_file.read_text()
            original_content = content
            
            # Fix function signatures without colons
            def fix_function_signature(match):
                code_block = match.group(1)
                
                # Fix function signatures that are missing colons
                lines = code_block.split('\n')
                fixed_lines = []
                
                for line in lines:
                    # If it looks like a function signature without a colon, add one
                    if (line.strip().startswith('async def ') or line.strip().startswith('def ')) and '->' in line and not line.strip().endswith(':'):
                        line = line.rstrip() + ':'
                    fixed_lines.append(line)
                
                return f"```python\n{chr(10).join(fixed_lines)}\n```"
            
            # Apply fix to Python code blocks
            content = re.sub(
                r'```(?:python|py)\n(.*?)\n```',
                fix_function_signature,
                content,
                flags=re.DOTALL
            )
            
            if content != original_content:
                doc_file.write_text(content)
                fixes.append(f"Fixed function signatures in {doc_file.name}")
        
        return fixes
    
    def fix_all_issues(self) -> List[str]:
        """Fix all documentation issues."""
        all_fixes = []
        
        print("🔧 Fixing async code examples...")
        all_fixes.extend(self.fix_async_code_examples())
        
        print("🔧 Fixing YAML syntax issues...")
        all_fixes.extend(self.fix_yaml_multi_document_issues())
        
        print("🔧 Fixing function signature syntax...")
        all_fixes.extend(self.fix_function_signature_syntax())
        
        self.fixes_applied = all_fixes
        return all_fixes

def main():
    """Main documentation fixer entry point."""
    parser = argparse.ArgumentParser(description="Fix LeanVibe Agent Hive documentation issues")
    parser.add_argument("--all", action="store_true", help="Fix all documentation issues")
    parser.add_argument("--async-examples", action="store_true", help="Fix async code examples")
    parser.add_argument("--yaml-syntax", action="store_true", help="Fix YAML syntax issues")
    
    args = parser.parse_args()
    
    # Determine project root
    project_root = Path(__file__).parent.parent
    if not (project_root / "README.md").exists():
        print("❌ Cannot find project root (README.md not found)")
        return 1
    
    # Create fixer
    fixer = DocumentationFixer(project_root)
    
    # Apply fixes
    if args.all or not any([args.async_examples, args.yaml_syntax]):
        fixes = fixer.fix_all_issues()
    else:
        fixes = []
        if args.async_examples:
            fixes.extend(fixer.fix_async_code_examples())
        if args.yaml_syntax:
            fixes.extend(fixer.fix_yaml_multi_document_issues())
    
    # Report results
    if fixes:
        print(f"\n✅ Applied {len(fixes)} fixes:")
        for fix in fixes:
            print(f"   {fix}")
        print(f"\n💡 Run validation again to verify fixes: python scripts/validate_documentation.py --all")
    else:
        print(f"\n ℹ️ No fixes needed or applied.")
    
    return 0

if __name__ == "__main__":
    exit(main())