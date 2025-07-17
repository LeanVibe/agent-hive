#!/usr/bin/env python3
"""
Automated Feature Extraction Tool for Integration Pipeline.

This tool automatically analyzes worktrees and extracts unique features,
dependencies, and integration points for automated integration processing.
"""

import os
import re
import ast
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import importlib.util

logger = logging.getLogger(__name__)


@dataclass
class ExtractedFeature:
    """Represents an extracted feature from a worktree."""
    name: str
    type: str  # class, function, module, configuration
    file_path: str
    line_number: int
    description: str
    dependencies: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    signature: Optional[str] = None
    docstring: Optional[str] = None
    complexity_score: float = 0.0
    risk_level: str = "low"  # low, medium, high, critical
    integration_points: List[str] = field(default_factory=list)


@dataclass
class WorktreeAnalysis:
    """Complete analysis of a worktree."""
    worktree_path: str
    worktree_name: str
    analysis_timestamp: datetime
    total_files: int
    python_files: int
    unique_features: List[ExtractedFeature] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    integration_points: List[str] = field(default_factory=list)
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    feature_fingerprint: str = ""
    compatibility_profile: Dict[str, Any] = field(default_factory=dict)


class AutomatedFeatureExtractor:
    """Automated feature extraction and analysis system."""
    
    def __init__(self, base_path: str = "new-worktrees"):
        self.base_path = Path(base_path)
        self.logger = logging.getLogger(__name__)
        
        # Analysis results
        self.worktree_analyses: Dict[str, WorktreeAnalysis] = {}
        self.feature_database: Dict[str, ExtractedFeature] = {}
        
        # Feature patterns for extraction
        self.feature_patterns = {
            'class': r'class\s+(\w+).*?:',
            'function': r'def\s+(\w+)\s*\(',
            'async_function': r'async\s+def\s+(\w+)\s*\(',
            'variable': r'^(\w+)\s*=',
            'import': r'(?:from\s+[\w\.]+\s+)?import\s+([\w\.,\s]+)',
            'decorator': r'@(\w+)',
            'config': r'(\w+)_CONFIG\s*=',
            'endpoint': r'@app\.route\(.*?\)\s*\ndef\s+(\w+)',
            'api_endpoint': r'@.*?\.(?:get|post|put|delete|patch)\(.*?\)\s*\ndef\s+(\w+)',
        }
        
        # Integration point patterns
        self.integration_patterns = {
            'database': r'(?:db\.|Session|engine|connection)',
            'redis': r'(?:redis|cache|Redis)',
            'api': r'(?:FastAPI|Flask|app\.|route|endpoint)',
            'messaging': r'(?:queue|message|publish|subscribe)',
            'security': r'(?:auth|security|jwt|token|rbac)',
            'monitoring': r'(?:monitor|metrics|logging|trace)',
            'coordination': r'(?:coordination|orchestration|workflow)',
        }
        
        # Quality thresholds
        self.quality_thresholds = {
            'min_docstring_coverage': 0.7,
            'max_complexity_score': 10.0,
            'min_test_coverage': 0.8,
            'max_function_length': 50,
            'max_class_complexity': 20
        }
        
        self.logger.info(f"FeatureExtractor initialized with base path: {self.base_path}")
    
    def extract_all_worktrees(self) -> Dict[str, WorktreeAnalysis]:
        """Extract features from all worktrees."""
        self.logger.info("Starting feature extraction from all worktrees")
        
        if not self.base_path.exists():
            self.logger.error(f"Base path does not exist: {self.base_path}")
            return {}
        
        # Get all worktree directories
        worktree_dirs = [d for d in self.base_path.iterdir() if d.is_dir()]
        
        for worktree_dir in worktree_dirs:
            try:
                analysis = self.extract_worktree_features(worktree_dir)
                self.worktree_analyses[analysis.worktree_name] = analysis
                self.logger.info(f"Extracted {len(analysis.unique_features)} features from {analysis.worktree_name}")
            except Exception as e:
                self.logger.error(f"Error extracting features from {worktree_dir}: {e}")
        
        self.logger.info(f"Feature extraction completed for {len(self.worktree_analyses)} worktrees")
        return self.worktree_analyses
    
    def extract_worktree_features(self, worktree_path: Path) -> WorktreeAnalysis:
        """Extract features from a specific worktree."""
        analysis = WorktreeAnalysis(
            worktree_path=str(worktree_path),
            worktree_name=worktree_path.name,
            analysis_timestamp=datetime.now(),
            total_files=0,
            python_files=0
        )
        
        # Collect all files
        all_files = list(worktree_path.rglob('*'))
        analysis.total_files = len([f for f in all_files if f.is_file()])
        
        # Process Python files
        python_files = list(worktree_path.rglob('*.py'))
        analysis.python_files = len(python_files)
        
        for py_file in python_files:
            try:
                features = self._extract_file_features(py_file, worktree_path)
                analysis.unique_features.extend(features)
            except Exception as e:
                self.logger.warning(f"Error processing {py_file}: {e}")
        
        # Extract dependencies and integration points
        analysis.dependencies = self._extract_dependencies(analysis.unique_features)
        analysis.integration_points = self._extract_integration_points(analysis.unique_features)
        
        # Calculate quality metrics
        analysis.quality_metrics = self._calculate_quality_metrics(analysis.unique_features)
        
        # Generate feature fingerprint
        analysis.feature_fingerprint = self._generate_feature_fingerprint(analysis.unique_features)
        
        # Create compatibility profile
        analysis.compatibility_profile = self._create_compatibility_profile(analysis)
        
        return analysis
    
    def _extract_file_features(self, file_path: Path, worktree_path: Path) -> List[ExtractedFeature]:
        """Extract features from a single Python file."""
        features = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.logger.warning(f"Could not read file {file_path}: {e}")
            return features
        
        # Parse AST for more accurate analysis
        try:
            tree = ast.parse(content)
            features.extend(self._extract_ast_features(tree, file_path, worktree_path))
        except SyntaxError as e:
            self.logger.warning(f"Syntax error in {file_path}: {e}")
        
        # Extract regex-based features
        features.extend(self._extract_regex_features(content, file_path, worktree_path))
        
        return features
    
    def _extract_ast_features(self, tree: ast.AST, file_path: Path, worktree_path: Path) -> List[ExtractedFeature]:
        """Extract features using AST analysis."""
        features = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                feature = ExtractedFeature(
                    name=node.name,
                    type="class",
                    file_path=str(file_path.relative_to(worktree_path)),
                    line_number=node.lineno,
                    description=self._get_docstring(node),
                    docstring=self._get_docstring(node),
                    complexity_score=self._calculate_complexity(node),
                    imports=self._extract_imports_from_node(node),
                    exports=[node.name]
                )
                features.append(feature)
            
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                feature = ExtractedFeature(
                    name=node.name,
                    type="async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
                    file_path=str(file_path.relative_to(worktree_path)),
                    line_number=node.lineno,
                    description=self._get_docstring(node),
                    docstring=self._get_docstring(node),
                    signature=self._get_function_signature(node),
                    complexity_score=self._calculate_complexity(node),
                    exports=[node.name]
                )
                features.append(feature)
            
            elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                imports = self._extract_imports_from_import_node(node)
                for imp in imports:
                    feature = ExtractedFeature(
                        name=imp,
                        type="import",
                        file_path=str(file_path.relative_to(worktree_path)),
                        line_number=node.lineno,
                        description=f"Import: {imp}",
                        imports=[imp]
                    )
                    features.append(feature)
        
        return features
    
    def _extract_regex_features(self, content: str, file_path: Path, worktree_path: Path) -> List[ExtractedFeature]:
        """Extract features using regex patterns."""
        features = []
        lines = content.split('\n')
        
        for pattern_type, pattern in self.feature_patterns.items():
            if pattern_type in ['class', 'function', 'async_function']:
                continue  # Already handled by AST
            
            for line_num, line in enumerate(lines, 1):
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    feature = ExtractedFeature(
                        name=match.group(1),
                        type=pattern_type,
                        file_path=str(file_path.relative_to(worktree_path)),
                        line_number=line_num,
                        description=f"{pattern_type}: {match.group(1)}",
                        exports=[match.group(1)] if pattern_type != 'import' else [],
                        imports=[match.group(1)] if pattern_type == 'import' else []
                    )
                    features.append(feature)
        
        # Extract integration points
        for integration_type, pattern in self.integration_patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                feature = ExtractedFeature(
                    name=f"{integration_type}_integration",
                    type="integration_point",
                    file_path=str(file_path.relative_to(worktree_path)),
                    line_number=1,
                    description=f"Integration point: {integration_type}",
                    integration_points=[integration_type]
                )
                features.append(feature)
        
        return features
    
    def _get_docstring(self, node: ast.AST) -> str:
        """Extract docstring from AST node."""
        if (hasattr(node, 'body') and node.body and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            return node.body[0].value.value
        return ""
    
    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        """Get function signature from AST node."""
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        return f"{node.name}({', '.join(args)})"
    
    def _calculate_complexity(self, node: ast.AST) -> float:
        """Calculate cyclomatic complexity of AST node."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.Try):
                complexity += len(child.handlers)
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return float(complexity)
    
    def _extract_imports_from_node(self, node: ast.AST) -> List[str]:
        """Extract imports from AST node."""
        imports = []
        for child in ast.walk(node):
            if isinstance(child, ast.Import):
                imports.extend(self._extract_imports_from_import_node(child))
            elif isinstance(child, ast.ImportFrom):
                imports.extend(self._extract_imports_from_import_node(child))
        return imports
    
    def _extract_imports_from_import_node(self, node: ast.Import) -> List[str]:
        """Extract imports from import node."""
        imports = []
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    imports.append(f"{node.module}.{alias.name}")
            else:
                for alias in node.names:
                    imports.append(alias.name)
        return imports
    
    def _extract_dependencies(self, features: List[ExtractedFeature]) -> Dict[str, List[str]]:
        """Extract dependencies from features."""
        dependencies = defaultdict(list)
        
        for feature in features:
            if feature.imports:
                dependencies[feature.name].extend(feature.imports)
        
        return dict(dependencies)
    
    def _extract_integration_points(self, features: List[ExtractedFeature]) -> List[str]:
        """Extract integration points from features."""
        integration_points = set()
        
        for feature in features:
            if feature.integration_points:
                integration_points.update(feature.integration_points)
        
        return list(integration_points)
    
    def _calculate_quality_metrics(self, features: List[ExtractedFeature]) -> Dict[str, float]:
        """Calculate quality metrics for features."""
        if not features:
            return {}
        
        # Calculate docstring coverage
        documented_features = sum(1 for f in features if f.docstring and f.docstring.strip())
        docstring_coverage = documented_features / len(features) if features else 0
        
        # Calculate average complexity
        complexity_scores = [f.complexity_score for f in features if f.complexity_score > 0]
        avg_complexity = sum(complexity_scores) / len(complexity_scores) if complexity_scores else 0
        
        # Calculate feature distribution
        feature_types = defaultdict(int)
        for feature in features:
            feature_types[feature.type] += 1
        
        return {
            'docstring_coverage': docstring_coverage,
            'average_complexity': avg_complexity,
            'max_complexity': max(complexity_scores) if complexity_scores else 0,
            'total_features': len(features),
            'feature_types': dict(feature_types),
            'quality_score': min(1.0, docstring_coverage * 0.4 + (1 - min(avg_complexity / 10, 1)) * 0.6)
        }
    
    def _generate_feature_fingerprint(self, features: List[ExtractedFeature]) -> str:
        """Generate unique fingerprint for feature set."""
        feature_signatures = []
        
        for feature in sorted(features, key=lambda x: x.name):
            signature = f"{feature.type}:{feature.name}:{feature.signature or ''}"
            feature_signatures.append(signature)
        
        combined_signature = "|".join(feature_signatures)
        return hashlib.md5(combined_signature.encode()).hexdigest()
    
    def _create_compatibility_profile(self, analysis: WorktreeAnalysis) -> Dict[str, Any]:
        """Create compatibility profile for integration assessment."""
        profile = {
            'feature_count': len(analysis.unique_features),
            'integration_points': analysis.integration_points,
            'quality_score': analysis.quality_metrics.get('quality_score', 0),
            'complexity_score': analysis.quality_metrics.get('average_complexity', 0),
            'risk_factors': [],
            'compatibility_score': 0.0
        }
        
        # Assess risk factors
        if analysis.quality_metrics.get('average_complexity', 0) > self.quality_thresholds['max_complexity_score']:
            profile['risk_factors'].append('high_complexity')
        
        if analysis.quality_metrics.get('docstring_coverage', 0) < self.quality_thresholds['min_docstring_coverage']:
            profile['risk_factors'].append('low_documentation')
        
        if len(analysis.integration_points) > 5:
            profile['risk_factors'].append('high_integration_complexity')
        
        # Calculate compatibility score
        quality_factor = analysis.quality_metrics.get('quality_score', 0)
        complexity_factor = 1 - min(analysis.quality_metrics.get('average_complexity', 0) / 10, 1)
        risk_factor = 1 - (len(profile['risk_factors']) * 0.2)
        
        profile['compatibility_score'] = (quality_factor * 0.4 + complexity_factor * 0.4 + risk_factor * 0.2)
        
        return profile
    
    def find_unique_features(self, worktree_name: str, reference_worktrees: List[str] = None) -> List[ExtractedFeature]:
        """Find features unique to a specific worktree."""
        if worktree_name not in self.worktree_analyses:
            self.logger.error(f"Worktree {worktree_name} not found in analyses")
            return []
        
        target_analysis = self.worktree_analyses[worktree_name]
        
        # If no reference worktrees specified, use all others
        if reference_worktrees is None:
            reference_worktrees = [name for name in self.worktree_analyses.keys() if name != worktree_name]
        
        # Collect all features from reference worktrees
        reference_features = set()
        for ref_worktree in reference_worktrees:
            if ref_worktree in self.worktree_analyses:
                ref_analysis = self.worktree_analyses[ref_worktree]
                for feature in ref_analysis.unique_features:
                    reference_features.add(f"{feature.type}:{feature.name}")
        
        # Find unique features
        unique_features = []
        for feature in target_analysis.unique_features:
            feature_signature = f"{feature.type}:{feature.name}"
            if feature_signature not in reference_features:
                unique_features.append(feature)
        
        return unique_features
    
    def generate_feature_report(self, worktree_name: str = None) -> Dict[str, Any]:
        """Generate comprehensive feature report."""
        if worktree_name and worktree_name not in self.worktree_analyses:
            return {"error": f"Worktree {worktree_name} not found"}
        
        if worktree_name:
            # Single worktree report
            analysis = self.worktree_analyses[worktree_name]
            unique_features = self.find_unique_features(worktree_name)
            
            return {
                "worktree_name": worktree_name,
                "analysis_timestamp": analysis.analysis_timestamp.isoformat(),
                "total_features": len(analysis.unique_features),
                "unique_features": len(unique_features),
                "quality_metrics": analysis.quality_metrics,
                "integration_points": analysis.integration_points,
                "compatibility_profile": analysis.compatibility_profile,
                "feature_fingerprint": analysis.feature_fingerprint,
                "features": [
                    {
                        "name": f.name,
                        "type": f.type,
                        "file_path": f.file_path,
                        "line_number": f.line_number,
                        "complexity_score": f.complexity_score,
                        "risk_level": f.risk_level,
                        "description": f.description
                    }
                    for f in unique_features
                ]
            }
        else:
            # Summary report for all worktrees
            summary = {
                "total_worktrees": len(self.worktree_analyses),
                "analysis_timestamp": datetime.now().isoformat(),
                "worktree_summaries": {}
            }
            
            for name, analysis in self.worktree_analyses.items():
                unique_features = self.find_unique_features(name)
                summary["worktree_summaries"][name] = {
                    "total_features": len(analysis.unique_features),
                    "unique_features": len(unique_features),
                    "quality_score": analysis.quality_metrics.get('quality_score', 0),
                    "compatibility_score": analysis.compatibility_profile.get('compatibility_score', 0),
                    "integration_points": analysis.integration_points,
                    "risk_factors": analysis.compatibility_profile.get('risk_factors', [])
                }
            
            return summary
    
    def save_analysis_results(self, output_path: str = "integration_automation/feature_analysis.json"):
        """Save analysis results to file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert analyses to JSON-serializable format
        serializable_data = {}
        for name, analysis in self.worktree_analyses.items():
            serializable_data[name] = {
                "worktree_path": analysis.worktree_path,
                "worktree_name": analysis.worktree_name,
                "analysis_timestamp": analysis.analysis_timestamp.isoformat(),
                "total_files": analysis.total_files,
                "python_files": analysis.python_files,
                "unique_features": [
                    {
                        "name": f.name,
                        "type": f.type,
                        "file_path": f.file_path,
                        "line_number": f.line_number,
                        "description": f.description,
                        "dependencies": f.dependencies,
                        "imports": f.imports,
                        "exports": f.exports,
                        "signature": f.signature,
                        "complexity_score": f.complexity_score,
                        "risk_level": f.risk_level,
                        "integration_points": f.integration_points
                    }
                    for f in analysis.unique_features
                ],
                "dependencies": analysis.dependencies,
                "integration_points": analysis.integration_points,
                "quality_metrics": analysis.quality_metrics,
                "feature_fingerprint": analysis.feature_fingerprint,
                "compatibility_profile": analysis.compatibility_profile
            }
        
        with open(output_file, 'w') as f:
            json.dump(serializable_data, f, indent=2)
        
        self.logger.info(f"Analysis results saved to {output_file}")


def main():
    """Main execution function."""
    logging.basicConfig(level=logging.INFO)
    
    # Initialize feature extractor
    extractor = AutomatedFeatureExtractor()
    
    # Extract features from all worktrees
    analyses = extractor.extract_all_worktrees()
    
    # Generate comprehensive report
    report = extractor.generate_feature_report()
    
    # Save results
    extractor.save_analysis_results()
    
    # Print summary
    print(f"\n🔍 FEATURE EXTRACTION COMPLETED")
    print(f"📊 Total worktrees analyzed: {report['total_worktrees']}")
    print(f"📋 Analysis timestamp: {report['analysis_timestamp']}")
    print(f"\n📈 WORKTREE SUMMARIES:")
    print("-" * 60)
    
    for name, summary in report['worktree_summaries'].items():
        print(f"🏗️  {name}:")
        print(f"   • Total features: {summary['total_features']}")
        print(f"   • Unique features: {summary['unique_features']}")
        print(f"   • Quality score: {summary['quality_score']:.2f}")
        print(f"   • Compatibility: {summary['compatibility_score']:.2f}")
        print(f"   • Integration points: {len(summary['integration_points'])}")
        if summary['risk_factors']:
            print(f"   • Risk factors: {', '.join(summary['risk_factors'])}")
        print()


if __name__ == "__main__":
    main()