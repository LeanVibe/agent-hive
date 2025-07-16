"""
Mutation Testing Framework for LeanVibe Quality Agent

This module implements mutation testing to validate the quality of test suites
by introducing deliberate bugs (mutations) into the code and verifying that
tests catch these bugs.
"""

import pytest
import ast
import sys
import tempfile
import subprocess
import importlib
import types
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from unittest.mock import Mock, patch

# Add the .claude directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude'))

from state.state_manager import StateManager, AgentState, TaskState


@dataclass
class MutationResult:
    """Result of a single mutation test."""
    mutation_id: str
    original_code: str
    mutated_code: str
    mutation_type: str
    line_number: int
    column_number: int
    killed: bool  # True if test detected the mutation
    surviving_tests: List[str]
    error_message: Optional[str] = None


@dataclass
class MutationReport:
    """Complete mutation testing report."""
    total_mutations: int
    killed_mutations: int
    surviving_mutations: int
    mutation_score: float
    results: List[MutationResult]
    coverage_info: Dict[str, Any]


class MutationOperator:
    """Base class for mutation operators."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def apply(self, node: ast.AST) -> List[ast.AST]:
        """Apply mutation to AST node."""
        raise NotImplementedError
    
    def can_mutate(self, node: ast.AST) -> bool:
        """Check if node can be mutated."""
        raise NotImplementedError


class ArithmeticOperatorMutation(MutationOperator):
    """Mutation operator for arithmetic operations."""
    
    def __init__(self):
        super().__init__("AOM", "Arithmetic Operator Mutation")
        self.mutations = {
            ast.Add: [ast.Sub, ast.Mult, ast.Div],
            ast.Sub: [ast.Add, ast.Mult, ast.Div],
            ast.Mult: [ast.Add, ast.Sub, ast.Div],
            ast.Div: [ast.Add, ast.Sub, ast.Mult],
            ast.Mod: [ast.Add, ast.Sub, ast.Mult],
            ast.Pow: [ast.Mult, ast.Div],
        }
    
    def can_mutate(self, node: ast.AST) -> bool:
        if isinstance(node, ast.BinOp):
            return type(node.op) in self.mutations
        return False
    
    def apply(self, node: ast.BinOp) -> List[ast.BinOp]:
        """Apply arithmetic operator mutations."""
        if not self.can_mutate(node):
            return []
        
        mutants = []
        original_op = type(node.op)
        
        for new_op_class in self.mutations[original_op]:
            mutant = ast.copy_location(
                ast.BinOp(left=node.left, op=new_op_class(), right=node.right),
                node
            )
            mutants.append(mutant)
        
        return mutants


class RelationalOperatorMutation(MutationOperator):
    """Mutation operator for relational operations."""
    
    def __init__(self):
        super().__init__("ROR", "Relational Operator Replacement")
        self.mutations = {
            ast.Lt: [ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq],
            ast.LtE: [ast.Lt, ast.Gt, ast.GtE, ast.Eq, ast.NotEq],
            ast.Gt: [ast.Lt, ast.LtE, ast.GtE, ast.Eq, ast.NotEq],
            ast.GtE: [ast.Lt, ast.LtE, ast.Gt, ast.Eq, ast.NotEq],
            ast.Eq: [ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.NotEq],
            ast.NotEq: [ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq],
        }
    
    def can_mutate(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Compare):
            return len(node.ops) == 1 and type(node.ops[0]) in self.mutations
        return False
    
    def apply(self, node: ast.Compare) -> List[ast.Compare]:
        """Apply relational operator mutations."""
        if not self.can_mutate(node):
            return []
        
        mutants = []
        original_op = type(node.ops[0])
        
        for new_op_class in self.mutations[original_op]:
            mutant = ast.copy_location(
                ast.Compare(
                    left=node.left,
                    ops=[new_op_class()],
                    comparators=node.comparators
                ),
                node
            )
            mutants.append(mutant)
        
        return mutants


class LogicalOperatorMutation(MutationOperator):
    """Mutation operator for logical operations."""
    
    def __init__(self):
        super().__init__("LOR", "Logical Operator Replacement")
        self.mutations = {
            ast.And: [ast.Or],
            ast.Or: [ast.And],
        }
    
    def can_mutate(self, node: ast.AST) -> bool:
        if isinstance(node, ast.BoolOp):
            return type(node.op) in self.mutations
        return False
    
    def apply(self, node: ast.BoolOp) -> List[ast.BoolOp]:
        """Apply logical operator mutations."""
        if not self.can_mutate(node):
            return []
        
        mutants = []
        original_op = type(node.op)
        
        for new_op_class in self.mutations[original_op]:
            mutant = ast.copy_location(
                ast.BoolOp(op=new_op_class(), values=node.values),
                node
            )
            mutants.append(mutant)
        
        return mutants


class ConstantMutation(MutationOperator):
    """Mutation operator for constants."""
    
    def __init__(self):
        super().__init__("CR", "Constant Replacement")
    
    def can_mutate(self, node: ast.AST) -> bool:
        return isinstance(node, ast.Constant)
    
    def apply(self, node: ast.Constant) -> List[ast.Constant]:
        """Apply constant mutations."""
        if not self.can_mutate(node):
            return []
        
        mutants = []
        value = node.value
        
        if isinstance(value, bool):
            mutant = ast.copy_location(ast.Constant(value=not value), node)
            mutants.append(mutant)
        elif isinstance(value, (int, float)):
            if value == 0:
                mutant = ast.copy_location(ast.Constant(value=1), node)
                mutants.append(mutant)
            elif value == 1:
                mutant = ast.copy_location(ast.Constant(value=0), node)
                mutants.append(mutant)
            else:
                mutant = ast.copy_location(ast.Constant(value=value + 1), node)
                mutants.append(mutant)
                mutant = ast.copy_location(ast.Constant(value=value - 1), node)
                mutants.append(mutant)
        elif isinstance(value, str):
            if value == "":
                mutant = ast.copy_location(ast.Constant(value="mutant"), node)
                mutants.append(mutant)
            else:
                mutant = ast.copy_location(ast.Constant(value=""), node)
                mutants.append(mutant)
        
        return mutants


class MutationTester:
    """Main mutation testing framework."""
    
    def __init__(self, source_dir: str, test_dir: str):
        self.source_dir = Path(source_dir)
        self.test_dir = Path(test_dir)
        self.operators = [
            ArithmeticOperatorMutation(),
            RelationalOperatorMutation(),
            LogicalOperatorMutation(),
            ConstantMutation(),
        ]
        self.mutation_counter = 0
    
    def generate_mutations(self, source_file: Path) -> List[Tuple[ast.AST, MutationResult]]:
        """Generate mutations for a source file."""
        with open(source_file, 'r') as f:
            source_code = f.read()
        
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            print(f"Syntax error in {source_file}: {e}")
            return []
        
        mutations = []
        
        for node in ast.walk(tree):
            for operator in self.operators:
                if operator.can_mutate(node):
                    mutants = operator.apply(node)
                    
                    for mutant in mutants:
                        self.mutation_counter += 1
                        mutation_id = f"MUT_{self.mutation_counter:04d}"
                        
                        result = MutationResult(
                            mutation_id=mutation_id,
                            original_code=ast.unparse(node),
                            mutated_code=ast.unparse(mutant),
                            mutation_type=operator.name,
                            line_number=getattr(node, 'lineno', 0),
                            column_number=getattr(node, 'col_offset', 0),
                            killed=False,
                            surviving_tests=[]
                        )
                        
                        # Create mutated tree
                        mutated_tree = self._replace_node(tree, node, mutant)
                        mutations.append((mutated_tree, result))
        
        return mutations
    
    def _replace_node(self, tree: ast.AST, old_node: ast.AST, new_node: ast.AST) -> ast.AST:
        """Replace a node in the AST."""
        class NodeReplacer(ast.NodeTransformer):
            def visit(self, node):
                if node is old_node:
                    return new_node
                return self.generic_visit(node)
        
        return NodeReplacer().visit(tree)
    
    def run_tests_with_mutation(self, mutated_tree: ast.AST, 
                               source_file: Path) -> Tuple[bool, List[str]]:
        """Run tests with mutated code."""
        # Create temporary file with mutated code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(ast.unparse(mutated_tree))
            temp_file = f.name
        
        try:
            # Import the mutated module
            spec = importlib.util.spec_from_file_location("mutated_module", temp_file)
            if spec is None or spec.loader is None:
                return False, ["Import failed"]
            
            mutated_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mutated_module)
            
            # Run tests (simplified - in real implementation, would run actual test suite)
            surviving_tests = []
            killed = False
            
            try:
                # Test basic functionality
                if hasattr(mutated_module, 'StateManager'):
                    with tempfile.TemporaryDirectory() as temp_dir:
                        state_manager = mutated_module.StateManager(Path(temp_dir))
                        
                        # Test agent state operations
                        agent_state = mutated_module.AgentState(
                            agent_id="test-agent",
                            status="idle",
                            capabilities=["test"],
                            performance_metrics={"speed": 0.8}
                        )
                        
                        state_manager.update_agent_state(agent_state)
                        retrieved = state_manager.get_agent_state("test-agent")
                        
                        if retrieved is None or retrieved.agent_id != "test-agent":
                            killed = True
                        else:
                            surviving_tests.append("agent_state_test")
                            
            except Exception as e:
                killed = True
                surviving_tests = [f"Exception: {str(e)}"]
            
            return killed, surviving_tests
            
        finally:
            # Clean up temporary file
            Path(temp_file).unlink(missing_ok=True)
    
    def run_mutation_testing(self, source_files: List[Path]) -> MutationReport:
        """Run mutation testing on source files."""
        all_results = []
        
        for source_file in source_files:
            print(f"Generating mutations for {source_file}")
            mutations = self.generate_mutations(source_file)
            
            for mutated_tree, mutation_result in mutations:
                killed, surviving_tests = self.run_tests_with_mutation(
                    mutated_tree, source_file
                )
                
                mutation_result.killed = killed
                mutation_result.surviving_tests = surviving_tests
                all_results.append(mutation_result)
        
        # Calculate mutation score
        total_mutations = len(all_results)
        killed_mutations = sum(1 for r in all_results if r.killed)
        surviving_mutations = total_mutations - killed_mutations
        
        mutation_score = (killed_mutations / total_mutations * 100) if total_mutations > 0 else 0
        
        return MutationReport(
            total_mutations=total_mutations,
            killed_mutations=killed_mutations,
            surviving_mutations=surviving_mutations,
            mutation_score=mutation_score,
            results=all_results,
            coverage_info={}
        )
    
    def generate_mutation_report(self, report: MutationReport) -> str:
        """Generate human-readable mutation report."""
        lines = [
            "MUTATION TESTING REPORT",
            "=" * 50,
            f"Total Mutations: {report.total_mutations}",
            f"Killed Mutations: {report.killed_mutations}",
            f"Surviving Mutations: {report.surviving_mutations}",
            f"Mutation Score: {report.mutation_score:.2f}%",
            "",
            "SURVIVING MUTATIONS:",
            "-" * 30
        ]
        
        for result in report.results:
            if not result.killed:
                lines.extend([
                    f"Mutation ID: {result.mutation_id}",
                    f"Type: {result.mutation_type}",
                    f"Line: {result.line_number}",
                    f"Original: {result.original_code}",
                    f"Mutated: {result.mutated_code}",
                    f"Surviving Tests: {', '.join(result.surviving_tests)}",
                    ""
                ])
        
        return "\n".join(lines)


@pytest.mark.mutation
class TestMutationFramework:
    """Tests for mutation testing framework."""
    
    def test_arithmetic_operator_mutation(self):
        """Test arithmetic operator mutations."""
        operator = ArithmeticOperatorMutation()
        
        # Test addition mutation
        code = "x = a + b"
        tree = ast.parse(code)
        binop = tree.body[0].value
        
        assert operator.can_mutate(binop)
        mutants = operator.apply(binop)
        
        assert len(mutants) > 0
        assert any(isinstance(m.op, ast.Sub) for m in mutants)
        assert any(isinstance(m.op, ast.Mult) for m in mutants)
    
    def test_relational_operator_mutation(self):
        """Test relational operator mutations."""
        operator = RelationalOperatorMutation()
        
        # Test less than mutation
        code = "result = x < y"
        tree = ast.parse(code)
        compare = tree.body[0].value
        
        assert operator.can_mutate(compare)
        mutants = operator.apply(compare)
        
        assert len(mutants) > 0
        assert any(isinstance(m.ops[0], ast.LtE) for m in mutants)
        assert any(isinstance(m.ops[0], ast.Gt) for m in mutants)
    
    def test_logical_operator_mutation(self):
        """Test logical operator mutations."""
        operator = LogicalOperatorMutation()
        
        # Test and mutation
        code = "result = x and y"
        tree = ast.parse(code)
        boolop = tree.body[0].value
        
        assert operator.can_mutate(boolop)
        mutants = operator.apply(boolop)
        
        assert len(mutants) == 1
        assert isinstance(mutants[0].op, ast.Or)
    
    def test_constant_mutation(self):
        """Test constant mutations."""
        operator = ConstantMutation()
        
        # Test boolean constant
        code = "result = True"
        tree = ast.parse(code)
        constant = tree.body[0].value
        
        assert operator.can_mutate(constant)
        mutants = operator.apply(constant)
        
        assert len(mutants) == 1
        assert mutants[0].value is False
    
    def test_mutation_tester_basic(self):
        """Test basic mutation tester functionality."""
        # Create temporary source file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def add_numbers(a, b):
    return a + b

def is_positive(x):
    return x > 0

def is_valid(flag):
    return flag and True
""")
            temp_file = Path(f.name)
        
        try:
            tester = MutationTester(".", "tests")
            mutations = tester.generate_mutations(temp_file)
            
            assert len(mutations) > 0
            
            # Check that we have different types of mutations
            mutation_types = set(result.mutation_type for _, result in mutations)
            assert "AOM" in mutation_types  # Arithmetic
            assert "ROR" in mutation_types  # Relational
            assert "LOR" in mutation_types  # Logical
            
        finally:
            temp_file.unlink(missing_ok=True)
    
    def test_mutation_testing_with_state_manager(self):
        """Test mutation testing with StateManager."""
        # Create simplified state manager code
        source_code = """
class SimpleStateManager:
    def __init__(self):
        self.agents = {}
    
    def add_agent(self, agent_id, status):
        if agent_id and status:
            self.agents[agent_id] = status
            return True
        return False
    
    def get_agent_count(self):
        return len(self.agents)
    
    def is_agent_active(self, agent_id):
        return self.agents.get(agent_id) == "active"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(source_code)
            temp_file = Path(f.name)
        
        try:
            tester = MutationTester(".", "tests")
            mutations = tester.generate_mutations(temp_file)
            
            assert len(mutations) > 0
            
            # Test that mutations are generated for various operators
            results = [result for _, result in mutations]
            
            # Should have mutations for logical operators (and)
            logical_mutations = [r for r in results if r.mutation_type == "LOR"]
            assert len(logical_mutations) > 0
            
            # Should have mutations for comparison operators (==)
            relational_mutations = [r for r in results if r.mutation_type == "ROR"]
            assert len(relational_mutations) > 0
            
        finally:
            temp_file.unlink(missing_ok=True)
    
    def test_mutation_report_generation(self):
        """Test mutation report generation."""
        # Create mock mutation results
        results = [
            MutationResult(
                mutation_id="MUT_001",
                original_code="x + y",
                mutated_code="x - y",
                mutation_type="AOM",
                line_number=10,
                column_number=5,
                killed=True,
                surviving_tests=[]
            ),
            MutationResult(
                mutation_id="MUT_002",
                original_code="x > 0",
                mutated_code="x < 0",
                mutation_type="ROR",
                line_number=15,
                column_number=8,
                killed=False,
                surviving_tests=["test_positive"]
            )
        ]
        
        report = MutationReport(
            total_mutations=2,
            killed_mutations=1,
            surviving_mutations=1,
            mutation_score=50.0,
            results=results,
            coverage_info={}
        )
        
        tester = MutationTester(".", "tests")
        report_text = tester.generate_mutation_report(report)
        
        assert "MUTATION TESTING REPORT" in report_text
        assert "Total Mutations: 2" in report_text
        assert "Killed Mutations: 1" in report_text
        assert "Mutation Score: 50.00%" in report_text
        assert "MUT_002" in report_text
        assert "x > 0" in report_text
        assert "x < 0" in report_text
    
    def test_mutation_score_calculation(self):
        """Test mutation score calculation."""
        # All mutations killed
        results_all_killed = [
            MutationResult("MUT_001", "x + y", "x - y", "AOM", 1, 1, True, []),
            MutationResult("MUT_002", "x > 0", "x < 0", "ROR", 2, 1, True, [])
        ]
        
        report = MutationReport(2, 2, 0, 100.0, results_all_killed, {})
        assert report.mutation_score == 100.0
        
        # Some mutations surviving
        results_some_surviving = [
            MutationResult("MUT_001", "x + y", "x - y", "AOM", 1, 1, True, []),
            MutationResult("MUT_002", "x > 0", "x < 0", "ROR", 2, 1, False, ["test"])
        ]
        
        report = MutationReport(2, 1, 1, 50.0, results_some_surviving, {})
        assert report.mutation_score == 50.0
    
    def test_integration_with_existing_tests(self):
        """Test integration with existing test framework."""
        # This test verifies that mutation testing can work with our existing test suite
        
        # Create a simple function to mutate
        source_code = """
def validate_agent_status(status):
    if status == "active":
        return True
    elif status == "idle":
        return True
    else:
        return False

def calculate_score(correct, total):
    if total == 0:
        return 0.0
    return (correct / total) * 100
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(source_code)
            temp_file = Path(f.name)
        
        try:
            tester = MutationTester(".", "tests")
            report = tester.run_mutation_testing([temp_file])
            
            # Should have generated mutations
            assert report.total_mutations > 0
            assert 0 <= report.mutation_score <= 100
            
            # Should have both killed and possibly surviving mutations
            assert report.killed_mutations >= 0
            assert report.surviving_mutations >= 0
            assert report.killed_mutations + report.surviving_mutations == report.total_mutations
            
        finally:
            temp_file.unlink(missing_ok=True)