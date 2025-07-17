#!/usr/bin/env python3
"""
LeanVibe Agent Hive - Link Validation and Cross-Reference Checker

Comprehensive validation of internal links, cross-references, and documentation consistency.

Usage:
    python scripts/validate_links.py --all
    python scripts/validate_links.py --internal-links
    python scripts/validate_links.py --cross-references
    python scripts/validate_links.py --file-existence
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import urllib.parse

@dataclass
class LinkValidationResult:
    """Result of link validation check."""
    source_file: str
    link_type: str  # "internal", "cross_ref", "file_ref", "anchor"
    target: str
    status: str  # "valid", "broken", "warning"
    message: str
    line_number: Optional[int] = None
    context: Optional[str] = None

class LinkValidator:
    """Comprehensive link and cross-reference validation."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: List[LinkValidationResult] = []
        self.all_files: Set[Path] = set()
        self.markdown_files: List[Path] = []
        self.anchor_map: Dict[str, Set[str]] = {}  # file -> set of anchors
        
    def scan_project_files(self):
        """Scan project for all files and build file index."""
        print("📂 Scanning project files...")
        
        # Find all files (excluding common ignore patterns)
        ignore_patterns = {
            '.git', '__pycache__', '.pytest_cache', '.coverage', 'htmlcov',
            '.venv', 'node_modules', '.DS_Store', 'temp_test_'
        }
        
        for file_path in self.project_root.rglob('*'):
            if file_path.is_file():
                # Skip ignored files
                if any(ignore in str(file_path) for ignore in ignore_patterns):
                    continue
                
                self.all_files.add(file_path)
                
                # Track markdown files separately
                if file_path.suffix.lower() in {'.md', '.markdown'}:
                    self.markdown_files.append(file_path)
        
        print(f"   Found {len(self.all_files)} total files")
        print(f"   Found {len(self.markdown_files)} markdown files")
    
    def extract_anchors(self, file_path: Path) -> Set[str]:
        """Extract all anchor points (headers) from a markdown file."""
        if not file_path.exists():
            return set()
        
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        anchors = set()
        
        # Find all headers (# ## ### etc.)
        header_pattern = r'^#+\s+(.+)$'
        for match in re.finditer(header_pattern, content, re.MULTILINE):
            header_text = match.group(1).strip()
            
            # Convert to anchor format (GitHub style)
            anchor = self.text_to_anchor(header_text)
            anchors.add(anchor)
        
        # Find explicit anchor tags
        anchor_pattern = r'<a\s+(?:name|id)="([^"]+)"'
        for match in re.finditer(anchor_pattern, content, re.IGNORECASE):
            anchors.add(match.group(1))
        
        return anchors
    
    def text_to_anchor(self, text: str) -> str:
        """Convert text to GitHub-style anchor."""
        # Convert to lowercase
        anchor = text.lower()
        
        # Replace spaces and special chars with hyphens
        anchor = re.sub(r'[^a-z0-9\s-]', '', anchor)
        anchor = re.sub(r'\s+', '-', anchor)
        anchor = re.sub(r'-+', '-', anchor)
        anchor = anchor.strip('-')
        
        return anchor
    
    def build_anchor_map(self):
        """Build map of all anchors in all markdown files."""
        print("⚓ Building anchor map...")
        
        for file_path in self.markdown_files:
            rel_path = str(file_path.relative_to(self.project_root))
            anchors = self.extract_anchors(file_path)
            self.anchor_map[rel_path] = anchors
            
        total_anchors = sum(len(anchors) for anchors in self.anchor_map.values())
        print(f"   Found {total_anchors} total anchors")
    
    def validate_internal_links(self) -> List[LinkValidationResult]:
        """Validate internal markdown links."""
        results = []
        
        print("🔗 Validating internal links...")
        
        for file_path in self.markdown_files:
            rel_path = str(file_path.relative_to(self.project_root))
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\\n')
            
            # Find all markdown links
            link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
            
            for line_num, line in enumerate(lines, 1):
                for match in re.finditer(link_pattern, line):
                    link_text = match.group(1)
                    link_target = match.group(2)
                    
                    # Skip external links
                    if link_target.startswith(('http://', 'https://', 'mailto:')):
                        continue
                    
                    # Skip images (alt text)
                    if match.start() > 0 and line[match.start()-1] == '!':
                        continue
                    
                    # Validate internal link
                    result = self.validate_single_link(
                        rel_path, link_target, link_text, line_num, line.strip()
                    )
                    results.append(result)
        
        return results
    
    def validate_single_link(self, source_file: str, target: str, link_text: str, 
                           line_num: int, context: str) -> LinkValidationResult:
        """Validate a single internal link."""
        
        # Parse the target
        if '#' in target:
            file_part, anchor_part = target.split('#', 1)
        else:
            file_part, anchor_part = target, None
        
        # Resolve relative path
        source_path = self.project_root / source_file
        
        if file_part:
            # File reference
            if file_part.startswith('/'):
                # Absolute path from project root
                target_path = self.project_root / file_part.lstrip('/')
            else:
                # Relative path
                target_path = source_path.parent / file_part
            
            # Normalize path
            try:
                target_path = target_path.resolve()
                target_rel = target_path.relative_to(self.project_root)
            except (ValueError, OSError):
                return LinkValidationResult(
                    source_file=source_file,
                    link_type="file_ref",
                    target=target,
                    status="broken",
                    message=f"❌ Invalid file path: {target}",
                    line_number=line_num,
                    context=context
                )
            
            # Check if file exists
            if not target_path.exists():
                return LinkValidationResult(
                    source_file=source_file,
                    link_type="file_ref",
                    target=target,
                    status="broken",
                    message=f"❌ File not found: {file_part}",
                    line_number=line_num,
                    context=context
                )
            
            # If there's an anchor, validate it
            if anchor_part:
                target_rel_str = str(target_rel)
                if target_rel_str in self.anchor_map:
                    if anchor_part not in self.anchor_map[target_rel_str]:
                        return LinkValidationResult(
                            source_file=source_file,
                            link_type="anchor",
                            target=target,
                            status="broken",
                            message=f"❌ Anchor not found: #{anchor_part} in {file_part}",
                            line_number=line_num,
                            context=context
                        )
                else:
                    # File exists but no anchors mapped (not markdown?)
                    return LinkValidationResult(
                        source_file=source_file,
                        link_type="anchor",
                        target=target,
                        status="warning",
                        message=f"⚠️ Cannot validate anchor in non-markdown file: {file_part}",
                        line_number=line_num,
                        context=context
                    )
        else:
            # Anchor-only reference (same file)
            if anchor_part:
                current_file = source_file
                if current_file in self.anchor_map:
                    if anchor_part not in self.anchor_map[current_file]:
                        return LinkValidationResult(
                            source_file=source_file,
                            link_type="anchor",
                            target=target,
                            status="broken",
                            message=f"❌ Anchor not found in current file: #{anchor_part}",
                            line_number=line_num,
                            context=context
                        )
        
        # If we get here, the link is valid
        return LinkValidationResult(
            source_file=source_file,
            link_type="internal",
            target=target,
            status="valid",
            message=f"✅ Valid link: {target}",
            line_number=line_num,
            context=context
        )
    
    def validate_cross_references(self) -> List[LinkValidationResult]:
        """Validate cross-references between documentation files."""
        results = []
        
        print("🔄 Validating cross-references...")
        
        # Common cross-reference patterns
        ref_patterns = [
            (r'see\s+\[([^\]]+)\]\(([^)]+)\)', "see_reference"),
            (r'refer\s+to\s+\[([^\]]+)\]\(([^)]+)\)', "refer_reference"),
            (r'documented\s+in\s+\[([^\]]+)\]\(([^)]+)\)', "documentation_reference"),
            (r'\*\*\[([^\]]+)\]\(([^)]+)\)\*\*', "important_reference"),
        ]
        
        for file_path in self.markdown_files:
            rel_path = str(file_path.relative_to(self.project_root))
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\\n')
            
            for line_num, line in enumerate(lines, 1):
                for pattern, ref_type in ref_patterns:
                    for match in re.finditer(pattern, line, re.IGNORECASE):
                        link_text = match.group(1)
                        link_target = match.group(2)
                        
                        # Skip external links
                        if link_target.startswith(('http://', 'https://')):
                            continue
                        
                        # Validate the cross-reference
                        result = self.validate_single_link(
                            rel_path, link_target, link_text, line_num, line.strip()
                        )
                        result.link_type = ref_type
                        results.append(result)
        
        return results
    
    def validate_file_references(self) -> List[LinkValidationResult]:
        """Validate file path references in documentation."""
        results = []
        
        print("📁 Validating file references...")
        
        # Patterns for file references
        file_patterns = [
            (r'`([^`]+\.(py|md|yaml|yml|json|txt|sh|js|ts))`', "inline_file"),
            (r'\*\*([^*]+\.(py|md|yaml|yml|json|txt|sh|js|ts))\*\*', "bold_file"),
            (r'`([^`]*/)([^/`]+)`', "path_reference"),
        ]
        
        for file_path in self.markdown_files:
            rel_path = str(file_path.relative_to(self.project_root))
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\\n')
            
            for line_num, line in enumerate(lines, 1):
                for pattern, ref_type in file_patterns:
                    for match in re.finditer(pattern, line):
                        if ref_type == "path_reference":
                            file_ref = match.group(1) + match.group(2)
                        else:
                            file_ref = match.group(1)
                        
                        # Skip obvious non-file references
                        if any(skip in file_ref.lower() for skip in [
                            'example', 'placeholder', 'your-', '<', '>', 'https://', 'http://'
                        ]):
                            continue
                        
                        # Try to find the file
                        found = False
                        for project_file in self.all_files:
                            if str(project_file).endswith(file_ref) or file_ref in str(project_file):
                                found = True
                                break
                        
                        if found:
                            results.append(LinkValidationResult(
                                source_file=rel_path,
                                link_type=ref_type,
                                target=file_ref,
                                status="valid",
                                message=f"✅ File reference found: {file_ref}",
                                line_number=line_num,
                                context=line.strip()
                            ))
                        else:
                            # Check if it might be a planned/future file
                            if any(future_indicator in line.lower() for future_indicator in [
                                'planned', 'future', 'todo', 'not yet', 'will be', 'coming'
                            ]):
                                results.append(LinkValidationResult(
                                    source_file=rel_path,
                                    link_type=ref_type,
                                    target=file_ref,
                                    status="warning",
                                    message=f"⚠️ Future file reference: {file_ref}",
                                    line_number=line_num,
                                    context=line.strip()
                                ))
                            else:
                                results.append(LinkValidationResult(
                                    source_file=rel_path,
                                    link_type=ref_type,
                                    target=file_ref,
                                    status="broken",
                                    message=f"❌ File reference not found: {file_ref}",
                                    line_number=line_num,
                                    context=line.strip()
                                ))
        
        return results
    
    def validate_all_links(self) -> List[LinkValidationResult]:
        """Run all link validation checks."""
        all_results = []
        
        # Prepare
        self.scan_project_files()
        self.build_anchor_map()
        
        # Run validations
        all_results.extend(self.validate_internal_links())
        all_results.extend(self.validate_cross_references())
        all_results.extend(self.validate_file_references())
        
        self.results = all_results
        return all_results
    
    def generate_report(self) -> str:
        """Generate comprehensive link validation report."""
        if not self.results:
            return "No link validation results available."
        
        # Count results by status and type
        status_counts = {"valid": 0, "broken": 0, "warning": 0}
        type_counts = {}
        
        for result in self.results:
            status_counts[result.status] += 1
            if result.link_type not in type_counts:
                type_counts[result.link_type] = {"valid": 0, "broken": 0, "warning": 0}
            type_counts[result.link_type][result.status] += 1
        
        # Calculate statistics
        total_links = len(self.results)
        validity_rate = (status_counts["valid"] / total_links * 100) if total_links > 0 else 0
        
        # Generate report
        report = []
        report.append("=" * 80)
        report.append("🔗 LEANVIBE AGENT HIVE - LINK VALIDATION REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary
        report.append(f"📊 VALIDATION SUMMARY:")
        report.append(f"   Total Links Checked: {total_links}")
        report.append(f"   ✅ Valid: {status_counts['valid']} ({validity_rate:.1f}%)")
        report.append(f"   ❌ Broken: {status_counts['broken']}")
        report.append(f"   ⚠️ Warnings: {status_counts['warning']}")
        report.append("")
        
        # Breakdown by type
        report.append(f"📋 BREAKDOWN BY LINK TYPE:")
        for link_type, counts in sorted(type_counts.items()):
            total_type = sum(counts.values())
            type_validity = (counts["valid"] / total_type * 100) if total_type > 0 else 0
            report.append(f"   {link_type}: {counts['valid']}/{total_type} valid ({type_validity:.1f}%)")
            if counts["broken"] > 0:
                report.append(f"      ❌ {counts['broken']} broken")
            if counts["warning"] > 0:
                report.append(f"      ⚠️ {counts['warning']} warnings")
        report.append("")
        
        # Overall status
        if status_counts["broken"] == 0:
            report.append("🎉 OVERALL STATUS: EXCELLENT - All links are valid!")
        elif status_counts["broken"] <= 3:
            report.append("✅ OVERALL STATUS: GOOD - Minor link issues to fix")
        elif status_counts["broken"] <= 10:
            report.append("⚠️ OVERALL STATUS: NEEDS ATTENTION - Several broken links")
        else:
            report.append("❌ OVERALL STATUS: CRITICAL - Many broken links found")
        
        report.append("")
        
        # Detailed broken links
        broken_links = [r for r in self.results if r.status == "broken"]
        if broken_links:
            report.append(f"❌ BROKEN LINKS ({len(broken_links)}):")
            
            # Group by file
            broken_by_file: dict[str, list[LinkValidationResult]] = {}
            for result in broken_links:
                if result.source_file not in broken_by_file:
                    broken_by_file[result.source_file] = []
                broken_by_file[result.source_file].append(result)
            
            for file_name, file_broken in sorted(broken_by_file.items()):
                report.append(f"   📄 {file_name}:")
                for result in file_broken:
                    line_info = f" (line {result.line_number})" if result.line_number else ""
                    report.append(f"      {result.message}{line_info}")
                    if result.context:
                        report.append(f"         Context: {result.context[:80]}...")
            report.append("")
        
        # Warnings
        warnings = [r for r in self.results if r.status == "warning"]
        if warnings:
            report.append(f"⚠️ WARNINGS ({len(warnings)}):")
            for result in warnings[:10]:  # Show first 10
                line_info = f" (line {result.line_number})" if result.line_number else ""
                report.append(f"   {result.message}{line_info}")
            
            if len(warnings) > 10:
                report.append(f"   ... and {len(warnings) - 10} more warnings")
            report.append("")
        
        # Recommendations
        report.append("💡 RECOMMENDATIONS:")
        if status_counts["broken"] > 0:
            report.append("   1. Fix all broken internal links immediately")
            report.append("   2. Update file references to match actual project structure")
        if status_counts["warning"] > 0:
            report.append("   3. Review warnings for potential issues")
        report.append("   4. Add this validation to pre-commit hooks")
        report.append("   5. Consider using relative paths for better portability")
        
        return "\\n".join(report)

def main():
    """Main link validation entry point."""
    parser = argparse.ArgumentParser(description="Validate LeanVibe Agent Hive links and references")
    parser.add_argument("--all", action="store_true", help="Run all link validation checks")
    parser.add_argument("--internal-links", action="store_true", help="Validate internal markdown links")
    parser.add_argument("--cross-references", action="store_true", help="Validate cross-references")
    parser.add_argument("--file-existence", action="store_true", help="Validate file references")
    parser.add_argument("--output", type=str, help="Output file for validation report")
    
    args = parser.parse_args()
    
    # Determine project root
    project_root = Path(__file__).parent.parent
    if not (project_root / "README.md").exists():
        print("❌ Cannot find project root (README.md not found)")
        sys.exit(1)
    
    # Create validator
    validator = LinkValidator(project_root)
    
    # Run validation
    if args.all or not any([args.internal_links, args.cross_references, args.file_existence]):
        results = validator.validate_all_links()
    else:
        results = []
        validator.scan_project_files()
        validator.build_anchor_map()
        
        if args.internal_links:
            results.extend(validator.validate_internal_links())
        if args.cross_references:
            results.extend(validator.validate_cross_references())
        if args.file_existence:
            results.extend(validator.validate_file_references())
    
    # Generate and display report
    report = validator.generate_report()
    print(report)
    
    # Save report if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"\\n📄 Report saved to: {args.output}")
    
    # Exit with appropriate code
    broken_links = sum(1 for r in results if r.status == "broken")
    if broken_links > 0:
        print(f"\\n❌ Link validation failed with {broken_links} broken links")
        sys.exit(1)
    else:
        print(f"\\n✅ All links validated successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()