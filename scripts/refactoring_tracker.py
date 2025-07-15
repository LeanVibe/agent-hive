#!/usr/bin/env python3
"""
Refactoring Tracker - XP Methodology Enforcement
Part of PM/XP Methodology Enforcer

This module tracks refactoring activities, measures code quality improvements,
and ensures continuous improvement practices for XP methodology compliance.
"""

import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import re
import ast
import hashlib


@dataclass
class RefactoringSession:
    """Represents a refactoring session."""
    session_id: str
    author: str
    start_time: str
    end_time: Optional[str]
    duration_minutes: Optional[float]
    
    # Refactoring scope
    files_affected: List[str]
    functions_refactored: List[str]
    classes_refactored: List[str]
    
    # Code quality metrics
    before_complexity: float
    after_complexity: float
    complexity_reduction: float
    
    # Code metrics
    lines_before: int
    lines_after: int
    lines_removed: int
    duplicated_code_removed: int
    
    # Quality improvements
    code_smells_fixed: int
    test_coverage_change: float
    performance_improvement: float
    
    # XP compliance
    refactoring_type: str  # 'rename', 'extract', 'inline', 'move', 'simplify', 'performance'
    safety_score: float  # how safe the refactoring was
    continuous_improvement_score: float
    
    # Metadata
    description: str
    tools_used: List[str]
    tests_maintained: bool
    backward_compatible: bool


@dataclass
class RefactoringMetrics:
    """Comprehensive refactoring metrics."""
    period_id: str
    start_date: str
    end_date: str
    
    # Volume metrics
    total_sessions: int
    total_hours: float
    files_refactored: int
    functions_refactored: int
    
    # Quality metrics
    avg_complexity_reduction: float
    avg_lines_reduction: float
    avg_safety_score: float
    code_smells_fixed: int
    
    # XP compliance
    continuous_improvement_frequency: float  # sessions per week
    refactoring_coverage: float  # % of codebase touched
    quality_trend: str  # 'improving', 'stable', 'degrading'
    
    # Impact metrics
    performance_improvements: float
    test_coverage_improvements: float
    maintainability_score: float
    
    # Safety metrics
    breaking_changes: int
    rollbacks_required: int
    safety_percentage: float


class RefactoringTracker:
    """Advanced refactoring tracking and analysis system."""
    
    def __init__(self, db_path: str = "refactoring_data.db"):
        self.db_path = db_path
        self.init_database()
        
        # Configuration
        self.target_frequency = 2.0  # sessions per week
        self.complexity_threshold = 10.0  # cyclomatic complexity
        self.safety_threshold = 0.8
        
        # Refactoring patterns
        self.refactoring_patterns = {
            'rename': ['rename', 'renamed', 'renaming'],
            'extract': ['extract', 'extracted', 'extracting', 'pull out'],
            'inline': ['inline', 'inlined', 'inlining'],
            'move': ['move', 'moved', 'moving', 'relocate'],
            'simplify': ['simplify', 'simplified', 'cleanup', 'clean up'],
            'performance': ['optimize', 'optimized', 'performance', 'speed up']
        }
    
    def init_database(self):
        """Initialize SQLite database for refactoring tracking."""
        with sqlite3.connect(self.db_path) as conn:
            # Refactoring sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS refactoring_sessions (
                    session_id TEXT PRIMARY KEY,
                    author TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_minutes REAL,
                    files_affected TEXT NOT NULL,
                    functions_refactored TEXT NOT NULL,
                    classes_refactored TEXT NOT NULL,
                    before_complexity REAL NOT NULL,
                    after_complexity REAL NOT NULL,
                    complexity_reduction REAL NOT NULL,
                    lines_before INTEGER NOT NULL,
                    lines_after INTEGER NOT NULL,
                    lines_removed INTEGER NOT NULL,
                    duplicated_code_removed INTEGER NOT NULL,
                    code_smells_fixed INTEGER NOT NULL,
                    test_coverage_change REAL NOT NULL,
                    performance_improvement REAL NOT NULL,
                    refactoring_type TEXT NOT NULL,
                    safety_score REAL NOT NULL,
                    continuous_improvement_score REAL NOT NULL,
                    description TEXT NOT NULL,
                    tools_used TEXT NOT NULL,
                    tests_maintained BOOLEAN NOT NULL,
                    backward_compatible BOOLEAN NOT NULL
                )
            """)
            
            # Code quality snapshots
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quality_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    complexity_score REAL NOT NULL,
                    lines_of_code INTEGER NOT NULL,
                    duplication_score REAL NOT NULL,
                    maintainability_index REAL NOT NULL,
                    test_coverage REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES refactoring_sessions (session_id)
                )
            """)
            
            # Refactoring metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS refactoring_metrics (
                    period_id TEXT PRIMARY KEY,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    total_sessions INTEGER NOT NULL,
                    total_hours REAL NOT NULL,
                    files_refactored INTEGER NOT NULL,
                    functions_refactored INTEGER NOT NULL,
                    avg_complexity_reduction REAL NOT NULL,
                    avg_lines_reduction REAL NOT NULL,
                    avg_safety_score REAL NOT NULL,
                    code_smells_fixed INTEGER NOT NULL,
                    continuous_improvement_frequency REAL NOT NULL,
                    refactoring_coverage REAL NOT NULL,
                    quality_trend TEXT NOT NULL,
                    performance_improvements REAL NOT NULL,
                    test_coverage_improvements REAL NOT NULL,
                    maintainability_score REAL NOT NULL,
                    breaking_changes INTEGER NOT NULL,
                    rollbacks_required INTEGER NOT NULL,
                    safety_percentage REAL NOT NULL,
                    recorded_at TEXT NOT NULL
                )
            """)
            
            # Code complexity tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS complexity_tracking (
                    tracking_id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    function_name TEXT NOT NULL,
                    complexity_score REAL NOT NULL,
                    lines_of_code INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    commit_hash TEXT NOT NULL
                )
            """)
            
            conn.commit()
    
    def analyze_code_complexity(self, file_path: str) -> Dict:
        """Analyze code complexity for a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            complexity_data = {
                'file_path': file_path,
                'functions': [],
                'classes': [],
                'total_complexity': 0,
                'lines_of_code': len(content.splitlines()),
                'maintainability_index': 0.0
            }
            
            # Analyze functions and classes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_complexity = self.calculate_cyclomatic_complexity(node)
                    complexity_data['functions'].append({
                        'name': node.name,
                        'complexity': func_complexity,
                        'lines': node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                    })
                    complexity_data['total_complexity'] += func_complexity
                
                elif isinstance(node, ast.ClassDef):
                    class_complexity = 0
                    methods = []
                    
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_complexity = self.calculate_cyclomatic_complexity(item)
                            methods.append({
                                'name': item.name,
                                'complexity': method_complexity
                            })
                            class_complexity += method_complexity
                    
                    complexity_data['classes'].append({
                        'name': node.name,
                        'complexity': class_complexity,
                        'methods': methods
                    })
                    complexity_data['total_complexity'] += class_complexity
            
            # Calculate maintainability index (simplified)
            complexity_data['maintainability_index'] = self.calculate_maintainability_index(
                complexity_data['total_complexity'],
                complexity_data['lines_of_code']
            )
            
            return complexity_data
            
        except Exception as e:
            print(f"Error analyzing complexity for {file_path}: {e}")
            return {
                'file_path': file_path,
                'functions': [],
                'classes': [],
                'total_complexity': 0,
                'lines_of_code': 0,
                'maintainability_index': 0.0
            }
    
    def calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity for an AST node."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Count decision points
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With, ast.AsyncWith):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
        
        return complexity
    
    def calculate_maintainability_index(self, complexity: float, lines: int) -> float:
        """Calculate maintainability index (simplified version)."""
        if lines == 0:
            return 100.0
        
        # Simplified maintainability index calculation
        # Real formula is more complex and includes Halstead metrics
        base_score = 100.0
        complexity_penalty = min(complexity * 2, 50)  # Max 50 point penalty
        size_penalty = min(lines / 100, 20)  # Max 20 point penalty
        
        return max(0, base_score - complexity_penalty - size_penalty)
    
    def detect_refactoring_opportunity(self, file_path: str) -> List[Dict]:
        """Detect refactoring opportunities in a file."""
        opportunities = []
        
        try:
            complexity_data = self.analyze_code_complexity(file_path)
            
            # Check for high complexity functions
            for func in complexity_data['functions']:
                if func['complexity'] > self.complexity_threshold:
                    opportunities.append({
                        'type': 'high_complexity',
                        'target': func['name'],
                        'file': file_path,
                        'severity': 'high',
                        'description': f"Function {func['name']} has complexity {func['complexity']} > {self.complexity_threshold}",
                        'suggested_refactoring': 'extract_method'
                    })
            
            # Check for long functions
            for func in complexity_data['functions']:
                if func['lines'] > 50:
                    opportunities.append({
                        'type': 'long_function',
                        'target': func['name'],
                        'file': file_path,
                        'severity': 'medium',
                        'description': f"Function {func['name']} has {func['lines']} lines",
                        'suggested_refactoring': 'extract_method'
                    })
            
            # Check for large classes
            for cls in complexity_data['classes']:
                if len(cls['methods']) > 20:
                    opportunities.append({
                        'type': 'large_class',
                        'target': cls['name'],
                        'file': file_path,
                        'severity': 'medium',
                        'description': f"Class {cls['name']} has {len(cls['methods'])} methods",
                        'suggested_refactoring': 'extract_class'
                    })
            
            # Check overall maintainability
            if complexity_data['maintainability_index'] < 40:
                opportunities.append({
                    'type': 'low_maintainability',
                    'target': file_path,
                    'file': file_path,
                    'severity': 'high',
                    'description': f"File maintainability index is {complexity_data['maintainability_index']:.1f}",
                    'suggested_refactoring': 'general_cleanup'
                })
            
        except Exception as e:
            print(f"Error detecting refactoring opportunities: {e}")
        
        return opportunities
    
    def start_refactoring_session(self, author: str, description: str, 
                                 files: List[str] = None) -> str:
        """Start a new refactoring session."""
        session_id = f"refactor-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if files is None:
            files = []
        
        # Take baseline measurements
        baseline_data = {}
        for file_path in files:
            if file_path.endswith('.py') and os.path.exists(file_path):
                baseline_data[file_path] = self.analyze_code_complexity(file_path)
        
        # Store session start
        session_data = {
            'session_id': session_id,
            'author': author,
            'description': description,
            'files': files,
            'start_time': datetime.now().isoformat(),
            'baseline_data': baseline_data
        }
        
        # Save to temporary storage (would be database in production)
        temp_file = f"/tmp/refactoring_session_{session_id}.json"
        with open(temp_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        print(f"✅ Started refactoring session: {session_id}")
        print(f"Author: {author}")
        print(f"Description: {description}")
        print(f"Files: {', '.join(files) if files else 'None specified'}")
        
        return session_id
    
    def end_refactoring_session(self, session_id: str) -> Optional[RefactoringSession]:
        """End a refactoring session and calculate metrics."""
        try:
            # Load session data
            temp_file = f"/tmp/refactoring_session_{session_id}.json"
            if not os.path.exists(temp_file):
                print(f"❌ Session {session_id} not found")
                return None
            
            with open(temp_file, 'r') as f:
                session_data = json.load(f)
            
            # Calculate end measurements
            end_time = datetime.now().isoformat()
            start_time = session_data['start_time']
            
            start_dt = datetime.fromisoformat(start_time)
            end_dt = datetime.fromisoformat(end_time)
            duration_minutes = (end_dt - start_dt).total_seconds() / 60.0
            
            # Analyze changes
            changes = self.analyze_refactoring_changes(session_data)
            
            # Determine refactoring type
            refactoring_type = self.classify_refactoring_type(session_data['description'])
            
            # Calculate safety score
            safety_score = self.calculate_safety_score(changes)
            
            # Create refactoring session
            session = RefactoringSession(
                session_id=session_id,
                author=session_data['author'],
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration_minutes,
                files_affected=session_data['files'],
                functions_refactored=changes.get('functions_refactored', []),
                classes_refactored=changes.get('classes_refactored', []),
                before_complexity=changes.get('before_complexity', 0.0),
                after_complexity=changes.get('after_complexity', 0.0),
                complexity_reduction=changes.get('complexity_reduction', 0.0),
                lines_before=changes.get('lines_before', 0),
                lines_after=changes.get('lines_after', 0),
                lines_removed=changes.get('lines_removed', 0),
                duplicated_code_removed=changes.get('duplicated_code_removed', 0),
                code_smells_fixed=changes.get('code_smells_fixed', 0),
                test_coverage_change=changes.get('test_coverage_change', 0.0),
                performance_improvement=changes.get('performance_improvement', 0.0),
                refactoring_type=refactoring_type,
                safety_score=safety_score,
                continuous_improvement_score=self.calculate_improvement_score(changes),
                description=session_data['description'],
                tools_used=["manual"],  # Default
                tests_maintained=changes.get('tests_maintained', True),
                backward_compatible=changes.get('backward_compatible', True)
            )
            
            # Save session
            self.save_refactoring_session(session)
            
            # Cleanup temporary file
            os.remove(temp_file)
            
            print(f"✅ Ended refactoring session: {session_id}")
            print(f"Duration: {duration_minutes:.1f} minutes")
            print(f"Complexity reduction: {session.complexity_reduction:.1f}")
            print(f"Safety score: {session.safety_score:.2f}")
            
            return session
            
        except Exception as e:
            print(f"Error ending refactoring session: {e}")
            return None
    
    def analyze_refactoring_changes(self, session_data: Dict) -> Dict:
        """Analyze changes made during refactoring session."""
        changes = {
            'functions_refactored': [],
            'classes_refactored': [],
            'before_complexity': 0.0,
            'after_complexity': 0.0,
            'complexity_reduction': 0.0,
            'lines_before': 0,
            'lines_after': 0,
            'lines_removed': 0,
            'duplicated_code_removed': 0,
            'code_smells_fixed': 0,
            'test_coverage_change': 0.0,
            'performance_improvement': 0.0,
            'tests_maintained': True,
            'backward_compatible': True
        }
        
        # Compare baseline with current state
        baseline_data = session_data.get('baseline_data', {})
        
        for file_path in session_data['files']:
            if file_path.endswith('.py') and os.path.exists(file_path):
                baseline = baseline_data.get(file_path, {})
                current = self.analyze_code_complexity(file_path)
                
                # Calculate complexity changes
                baseline_complexity = baseline.get('total_complexity', 0)
                current_complexity = current.get('total_complexity', 0)
                
                changes['before_complexity'] += baseline_complexity
                changes['after_complexity'] += current_complexity
                
                # Calculate line changes
                baseline_lines = baseline.get('lines_of_code', 0)
                current_lines = current.get('lines_of_code', 0)
                
                changes['lines_before'] += baseline_lines
                changes['lines_after'] += current_lines
                
                if baseline_lines > current_lines:
                    changes['lines_removed'] += baseline_lines - current_lines
                
                # Track refactored functions and classes
                baseline_functions = {f['name'] for f in baseline.get('functions', [])}
                current_functions = {f['name'] for f in current.get('functions', [])}
                
                baseline_classes = {c['name'] for c in baseline.get('classes', [])}
                current_classes = {c['name'] for c in current.get('classes', [])}
                
                changes['functions_refactored'].extend(list(baseline_functions | current_functions))
                changes['classes_refactored'].extend(list(baseline_classes | current_classes))
        
        # Calculate overall complexity reduction
        changes['complexity_reduction'] = changes['before_complexity'] - changes['after_complexity']
        
        # Estimate other improvements (simplified)
        if changes['complexity_reduction'] > 0:
            changes['code_smells_fixed'] = max(1, int(changes['complexity_reduction'] / 3))
            changes['performance_improvement'] = changes['complexity_reduction'] * 0.5
        
        return changes
    
    def classify_refactoring_type(self, description: str) -> str:
        """Classify the type of refactoring based on description."""
        description_lower = description.lower()
        
        for refactoring_type, keywords in self.refactoring_patterns.items():
            if any(keyword in description_lower for keyword in keywords):
                return refactoring_type
        
        return 'general'  # Default
    
    def calculate_safety_score(self, changes: Dict) -> float:
        """Calculate safety score for refactoring session."""
        safety_score = 1.0
        
        # Penalize for large changes
        if changes['lines_removed'] > 100:
            safety_score -= 0.2
        
        # Penalize for high complexity reduction (might indicate risky changes)
        if changes['complexity_reduction'] > 50:
            safety_score -= 0.1
        
        # Bonus for maintaining tests
        if changes['tests_maintained']:
            safety_score += 0.1
        
        # Bonus for backward compatibility
        if changes['backward_compatible']:
            safety_score += 0.1
        
        return max(0.0, min(1.0, safety_score))
    
    def calculate_improvement_score(self, changes: Dict) -> float:
        """Calculate continuous improvement score."""
        score = 0.0
        
        # Complexity improvements
        if changes['complexity_reduction'] > 0:
            score += min(0.4, changes['complexity_reduction'] / 50)
        
        # Code reduction
        if changes['lines_removed'] > 0:
            score += min(0.3, changes['lines_removed'] / 100)
        
        # Quality improvements
        if changes['code_smells_fixed'] > 0:
            score += min(0.2, changes['code_smells_fixed'] / 10)
        
        # Performance improvements
        if changes['performance_improvement'] > 0:
            score += min(0.1, changes['performance_improvement'] / 20)
        
        return min(1.0, score)
    
    def save_refactoring_session(self, session: RefactoringSession):
        """Save refactoring session to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO refactoring_sessions
                (session_id, author, start_time, end_time, duration_minutes,
                 files_affected, functions_refactored, classes_refactored,
                 before_complexity, after_complexity, complexity_reduction,
                 lines_before, lines_after, lines_removed, duplicated_code_removed,
                 code_smells_fixed, test_coverage_change, performance_improvement,
                 refactoring_type, safety_score, continuous_improvement_score,
                 description, tools_used, tests_maintained, backward_compatible)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id, session.author, session.start_time,
                session.end_time, session.duration_minutes,
                json.dumps(session.files_affected),
                json.dumps(session.functions_refactored),
                json.dumps(session.classes_refactored),
                session.before_complexity, session.after_complexity,
                session.complexity_reduction, session.lines_before,
                session.lines_after, session.lines_removed,
                session.duplicated_code_removed, session.code_smells_fixed,
                session.test_coverage_change, session.performance_improvement,
                session.refactoring_type, session.safety_score,
                session.continuous_improvement_score, session.description,
                json.dumps(session.tools_used), session.tests_maintained,
                session.backward_compatible
            ))
            conn.commit()
    
    def calculate_refactoring_metrics(self, days: int = 7) -> RefactoringMetrics:
        """Calculate comprehensive refactoring metrics."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Volume metrics
            cursor.execute("""
                SELECT COUNT(*), SUM(duration_minutes), COUNT(DISTINCT files_affected)
                FROM refactoring_sessions
                WHERE start_time >= ? AND start_time <= ?
            """, (start_date.isoformat(), end_date.isoformat()))
            
            volume_data = cursor.fetchone()
            total_sessions = volume_data[0] if volume_data[0] else 0
            total_minutes = volume_data[1] if volume_data[1] else 0.0
            
            # Quality metrics
            cursor.execute("""
                SELECT AVG(complexity_reduction), AVG(lines_removed),
                       AVG(safety_score), SUM(code_smells_fixed),
                       AVG(performance_improvement), AVG(test_coverage_change)
                FROM refactoring_sessions
                WHERE start_time >= ? AND start_time <= ?
            """, (start_date.isoformat(), end_date.isoformat()))
            
            quality_data = cursor.fetchone()
            avg_complexity_reduction = quality_data[0] if quality_data[0] else 0.0
            avg_lines_reduction = quality_data[1] if quality_data[1] else 0.0
            avg_safety_score = quality_data[2] if quality_data[2] else 0.0
            code_smells_fixed = quality_data[3] if quality_data[3] else 0
            performance_improvements = quality_data[4] if quality_data[4] else 0.0
            test_coverage_improvements = quality_data[5] if quality_data[5] else 0.0
            
            # Function/class counts
            cursor.execute("""
                SELECT functions_refactored, classes_refactored
                FROM refactoring_sessions
                WHERE start_time >= ? AND start_time <= ?
            """, (start_date.isoformat(), end_date.isoformat()))
            
            refactoring_data = cursor.fetchall()
        
        # Calculate derived metrics
        total_hours = total_minutes / 60.0
        frequency = (total_sessions / days) * 7 if days > 0 else 0  # sessions per week
        
        functions_refactored = 0
        files_set = set()
        
        for functions_json, classes_json in refactoring_data:
            try:
                functions = json.loads(functions_json) if functions_json else []
                functions_refactored += len(functions)
            except json.JSONDecodeError:
                pass
        
        # Calculate other metrics
        refactoring_coverage = min(100.0, (total_sessions / max(1, days)) * 30)  # Estimated
        quality_trend = "improving" if avg_complexity_reduction > 0 else "stable"
        maintainability_score = min(100.0, (avg_complexity_reduction * 2) + 60)
        
        return RefactoringMetrics(
            period_id=f"refactor-metrics-{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}",
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            total_sessions=total_sessions,
            total_hours=total_hours,
            files_refactored=len(files_set),
            functions_refactored=functions_refactored,
            avg_complexity_reduction=avg_complexity_reduction,
            avg_lines_reduction=avg_lines_reduction,
            avg_safety_score=avg_safety_score,
            code_smells_fixed=code_smells_fixed,
            continuous_improvement_frequency=frequency,
            refactoring_coverage=refactoring_coverage,
            quality_trend=quality_trend,
            performance_improvements=performance_improvements,
            test_coverage_improvements=test_coverage_improvements,
            maintainability_score=maintainability_score,
            breaking_changes=0,  # Placeholder
            rollbacks_required=0,  # Placeholder
            safety_percentage=avg_safety_score * 100
        )
    
    def generate_refactoring_report(self, days: int = 7) -> str:
        """Generate comprehensive refactoring report."""
        metrics = self.calculate_refactoring_metrics(days)
        
        # Get refactoring opportunities
        opportunities = []
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    opportunities.extend(self.detect_refactoring_opportunity(file_path))
        
        # Get recent sessions
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT session_id, author, description, refactoring_type,
                       complexity_reduction, safety_score, duration_minutes
                FROM refactoring_sessions
                WHERE start_time >= datetime('now', '-{} days')
                ORDER BY start_time DESC
                LIMIT 10
            """.format(days))
            
            recent_sessions = cursor.fetchall()
        
        report = f"""
# Refactoring Report - XP Methodology Continuous Improvement

## 📊 Period: {metrics.start_date} to {metrics.end_date} ({days} days)

### 🔧 Refactoring Activity
- **Total Sessions**: {metrics.total_sessions}
- **Total Hours**: {metrics.total_hours:.1f}
- **Files Refactored**: {metrics.files_refactored}
- **Functions Refactored**: {metrics.functions_refactored}

### 📈 Quality Improvements
- **Average Complexity Reduction**: {metrics.avg_complexity_reduction:.1f}
- **Average Lines Reduction**: {metrics.avg_lines_reduction:.1f}
- **Code Smells Fixed**: {metrics.code_smells_fixed}
- **Performance Improvements**: {metrics.performance_improvements:.1f}%

### 🎯 XP Methodology Compliance
- **Continuous Improvement Frequency**: {metrics.continuous_improvement_frequency:.1f} sessions/week
- **Refactoring Coverage**: {metrics.refactoring_coverage:.1f}%
- **Quality Trend**: {metrics.quality_trend.title()}
- **Maintainability Score**: {metrics.maintainability_score:.1f}/100

### 🛡️ Safety Metrics
- **Average Safety Score**: {metrics.avg_safety_score:.2f}/1.0
- **Safety Percentage**: {metrics.safety_percentage:.1f}%
- **Breaking Changes**: {metrics.breaking_changes}
- **Rollbacks Required**: {metrics.rollbacks_required}

### 📋 Recent Refactoring Sessions
"""
        
        for session_data in recent_sessions:
            session_id, author, description, refactoring_type, complexity_reduction, safety_score, duration = session_data
            report += f"- **{session_id}**: {description} by {author}\n"
            report += f"  Type: {refactoring_type} | Complexity: -{complexity_reduction:.1f} | Safety: {safety_score:.2f} | Duration: {duration:.0f}min\n"
        
        if not recent_sessions:
            report += "No recent refactoring sessions found.\n"
        
        # Add refactoring opportunities
        report += f"""
### 🔍 Refactoring Opportunities ({len(opportunities)} found)
"""
        
        # Group by severity
        high_severity = [o for o in opportunities if o['severity'] == 'high']
        medium_severity = [o for o in opportunities if o['severity'] == 'medium']
        
        if high_severity:
            report += f"""
#### 🚨 High Priority ({len(high_severity)} issues)
"""
            for opp in high_severity[:5]:  # Show top 5
                report += f"- **{opp['target']}** in {opp['file']}: {opp['description']}\n"
                report += f"  Suggested: {opp['suggested_refactoring']}\n"
        
        if medium_severity:
            report += f"""
#### ⚠️ Medium Priority ({len(medium_severity)} issues)
"""
            for opp in medium_severity[:3]:  # Show top 3
                report += f"- **{opp['target']}** in {opp['file']}: {opp['description']}\n"
                report += f"  Suggested: {opp['suggested_refactoring']}\n"
        
        if not opportunities:
            report += "✅ No significant refactoring opportunities detected.\n"
        
        # XP compliance assessment
        compliance_score = (
            (metrics.continuous_improvement_frequency / self.target_frequency) * 0.4 +
            (metrics.avg_safety_score) * 0.3 +
            (metrics.refactoring_coverage / 100) * 0.3
        ) * 100
        
        report += f"""
### 🔄 XP Continuous Improvement Assessment
- **Overall Compliance**: {compliance_score:.1f}%
- **Target Frequency**: {self.target_frequency} sessions/week (Current: {metrics.continuous_improvement_frequency:.1f})
- **Safety Standard**: {'✅ Excellent' if metrics.avg_safety_score > 0.8 else '⚠️ Needs improvement'}
- **Quality Trend**: {'✅ Improving' if metrics.quality_trend == 'improving' else '⚠️ Stable'}
- **Maintainability**: {'✅ Good' if metrics.maintainability_score > 70 else '⚠️ Needs attention'}

### 💡 Recommendations
"""
        
        recommendations = []
        
        if metrics.continuous_improvement_frequency < self.target_frequency:
            recommendations.append(f"Increase refactoring frequency from {metrics.continuous_improvement_frequency:.1f} to {self.target_frequency} sessions/week")
        
        if metrics.avg_safety_score < self.safety_threshold:
            recommendations.append("Improve refactoring safety practices - ensure tests are maintained")
        
        if len(high_severity) > 0:
            recommendations.append(f"Address {len(high_severity)} high-priority refactoring opportunities")
        
        if metrics.quality_trend == "stable":
            recommendations.append("Focus on more impactful refactoring to improve quality trend")
        
        if not recommendations:
            recommendations.append("Excellent continuous improvement practices - maintain current approach")
        
        for i, rec in enumerate(recommendations, 1):
            report += f"{i}. {rec}\n"
        
        report += f"""
### 🎯 XP Methodology Benefits
- **Simple Design**: {'✅' if metrics.avg_complexity_reduction > 0 else '⚠️'} Continuous complexity reduction
- **Code Quality**: {'✅' if metrics.code_smells_fixed > 0 else '⚠️'} Active code smell elimination
- **Maintainability**: {'✅' if metrics.maintainability_score > 70 else '⚠️'} Improved code maintainability
- **Safety**: {'✅' if metrics.avg_safety_score > 0.8 else '⚠️'} Safe refactoring practices
- **Continuous Improvement**: {'✅' if metrics.continuous_improvement_frequency > 1 else '⚠️'} Regular improvement cycles

### 📊 Target Benchmarks
- **Frequency Target**: ≥{self.target_frequency} sessions/week
- **Safety Target**: ≥{self.safety_threshold} safety score
- **Complexity Target**: <{self.complexity_threshold} average complexity
- **Coverage Target**: ≥50% of codebase touched quarterly
- **Quality Target**: ≥70 maintainability score

---
Generated by PM/XP Methodology Enforcer Agent
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Sessions Analyzed: {metrics.total_sessions}
Opportunities Found: {len(opportunities)}
"""
        
        return report


def main():
    """Main CLI interface for refactoring tracking."""
    if len(sys.argv) < 2:
        print("Usage: python refactoring_tracker.py <command> [options]")
        print("Commands:")
        print("  start <author> <description> [files...]  - Start refactoring session")
        print("  end <session_id>                         - End refactoring session")
        print("  analyze <file_path>                      - Analyze code complexity")
        print("  opportunities [directory]                - Find refactoring opportunities")
        print("  report [days]                            - Generate refactoring report")
        print("  metrics [days]                           - Show refactoring metrics")
        print("  sessions [limit]                         - Show recent sessions")
        sys.exit(1)
    
    tracker = RefactoringTracker()
    command = sys.argv[1]
    
    if command == "start":
        if len(sys.argv) < 4:
            print("Usage: python refactoring_tracker.py start <author> <description> [files...]")
            sys.exit(1)
        
        author = sys.argv[2]
        description = sys.argv[3]
        files = sys.argv[4:] if len(sys.argv) > 4 else []
        
        session_id = tracker.start_refactoring_session(author, description, files)
        print(f"Session ID: {session_id}")
    
    elif command == "end":
        if len(sys.argv) < 3:
            print("Usage: python refactoring_tracker.py end <session_id>")
            sys.exit(1)
        
        session_id = sys.argv[2]
        session = tracker.end_refactoring_session(session_id)
        
        if session:
            print(f"✅ Refactoring session completed successfully")
    
    elif command == "analyze":
        if len(sys.argv) < 3:
            print("Usage: python refactoring_tracker.py analyze <file_path>")
            sys.exit(1)
        
        file_path = sys.argv[2]
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            sys.exit(1)
        
        complexity_data = tracker.analyze_code_complexity(file_path)
        
        print(f"Code Complexity Analysis: {file_path}")
        print(f"Total Complexity: {complexity_data['total_complexity']}")
        print(f"Lines of Code: {complexity_data['lines_of_code']}")
        print(f"Maintainability Index: {complexity_data['maintainability_index']:.1f}")
        print(f"Functions: {len(complexity_data['functions'])}")
        print(f"Classes: {len(complexity_data['classes'])}")
    
    elif command == "opportunities":
        directory = sys.argv[2] if len(sys.argv) > 2 else "."
        
        print(f"🔍 Finding refactoring opportunities in: {directory}")
        opportunities = []
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    opportunities.extend(tracker.detect_refactoring_opportunity(file_path))
        
        if opportunities:
            print(f"Found {len(opportunities)} refactoring opportunities:")
            
            # Group by severity
            high_severity = [o for o in opportunities if o['severity'] == 'high']
            medium_severity = [o for o in opportunities if o['severity'] == 'medium']
            
            if high_severity:
                print(f"\n🚨 High Priority ({len(high_severity)}):")
                for opp in high_severity:
                    print(f"  - {opp['target']} in {opp['file']}: {opp['description']}")
            
            if medium_severity:
                print(f"\n⚠️ Medium Priority ({len(medium_severity)}):")
                for opp in medium_severity:
                    print(f"  - {opp['target']} in {opp['file']}: {opp['description']}")
        else:
            print("✅ No significant refactoring opportunities found")
    
    elif command == "report":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        report = tracker.generate_refactoring_report(days)
        
        # Save report
        filename = f"refactoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(filename, 'w') as f:
            f.write(report)
        
        print(report)
        print(f"\nReport saved to: {filename}")
    
    elif command == "metrics":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        metrics = tracker.calculate_refactoring_metrics(days)
        
        print(f"Refactoring Metrics ({days} days):")
        print(f"  Total Sessions: {metrics.total_sessions}")
        print(f"  Total Hours: {metrics.total_hours:.1f}")
        print(f"  Complexity Reduction: {metrics.avg_complexity_reduction:.1f}")
        print(f"  Safety Score: {metrics.avg_safety_score:.2f}")
        print(f"  Frequency: {metrics.continuous_improvement_frequency:.1f} sessions/week")
        print(f"  Quality Trend: {metrics.quality_trend}")
    
    elif command == "sessions":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        
        with sqlite3.connect(tracker.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT session_id, author, description, refactoring_type,
                       complexity_reduction, safety_score, start_time, duration_minutes
                FROM refactoring_sessions
                ORDER BY start_time DESC
                LIMIT ?
            """, (limit,))
            
            sessions = cursor.fetchall()
        
        if sessions:
            print(f"Recent Refactoring Sessions (last {limit}):")
            for session_data in sessions:
                session_id, author, description, refactoring_type, complexity_reduction, safety_score, start_time, duration = session_data
                start_dt = datetime.fromisoformat(start_time)
                print(f"  {session_id}: {description} by {author}")
                print(f"    Date: {start_dt.strftime('%Y-%m-%d %H:%M')} | Type: {refactoring_type}")
                print(f"    Complexity: -{complexity_reduction:.1f} | Safety: {safety_score:.2f} | Duration: {duration:.0f}min")
        else:
            print("No refactoring sessions found")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()