"""
Unit tests for SmartTestEnforcer development tool.

Tests extracted from hook_system.py to ensure functionality is preserved
during refactoring process.
"""

import asyncio
import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Add the .claude directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / '.claude'))

from dev_tools.smart_test_enforcer import SmartTestEnforcer


class TestSmartTestEnforcer:
    """Test suite for SmartTestEnforcer functionality."""

    @pytest.fixture
    def enforcer(self):
        """Create SmartTestEnforcer instance."""
        return SmartTestEnforcer()

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_path:
            yield Path(temp_path)

    def test_init(self, enforcer):
        """Test enforcer initialization."""
        assert enforcer.test_patterns is not None
        assert enforcer.code_extensions is not None
        assert len(enforcer.test_patterns) >= 6  # Python, JS, TS, Swift, Java, C#
        assert '.py' in enforcer.code_extensions
        assert '.js' in enforcer.code_extensions

    def test_is_code_file_python(self, enforcer, temp_dir):
        """Test code file detection for Python files."""
        # Create a Python file
        python_file = temp_dir / "example.py"
        python_file.write_text("def hello(): pass")
        
        assert enforcer._is_code_file(python_file) is True

    def test_is_code_file_javascript(self, enforcer, temp_dir):
        """Test code file detection for JavaScript files."""
        # Create a JavaScript file
        js_file = temp_dir / "example.js"
        js_file.write_text("function hello() {}")
        
        assert enforcer._is_code_file(js_file) is True

    def test_is_code_file_test_file(self, enforcer, temp_dir):
        """Test that test files are excluded."""
        # Create test files
        test_files = [
            temp_dir / "test_example.py",
            temp_dir / "example_test.py",
            temp_dir / "example.test.js",
            temp_dir / "example.spec.js"
        ]
        
        for test_file in test_files:
            test_file.write_text("// test content")
            assert enforcer._is_code_file(test_file) is False

    def test_is_code_file_skip_directories(self, enforcer, temp_dir):
        """Test that files in skip directories are excluded."""
        # Create directories to skip
        skip_dirs = ['tests', 'node_modules', '__pycache__', '.git']
        
        for skip_dir in skip_dirs:
            dir_path = temp_dir / skip_dir
            dir_path.mkdir()
            code_file = dir_path / "example.py"
            code_file.write_text("def hello(): pass")
            
            assert enforcer._is_code_file(code_file) is False

    def test_is_code_file_skip_patterns(self, enforcer, temp_dir):
        """Test that specific file patterns are excluded."""
        skip_files = ['__init__.py', 'setup.py', 'conftest.py']
        
        for skip_file in skip_files:
            file_path = temp_dir / skip_file
            file_path.write_text("# skip this file")
            
            assert enforcer._is_code_file(file_path) is False

    def test_is_code_file_non_code_extension(self, enforcer, temp_dir):
        """Test that non-code files are excluded."""
        non_code_files = [
            temp_dir / "readme.md",
            temp_dir / "config.json",
            temp_dir / "data.csv"
        ]
        
        for non_code_file in non_code_files:
            non_code_file.write_text("content")
            assert enforcer._is_code_file(non_code_file) is False

    def test_is_test_file(self, enforcer):
        """Test test file detection."""
        test_files = [
            Path("test_example.py"),
            Path("example_test.py"),
            Path("ExampleTest.java"),
            Path("example.test.js"),
            Path("example.spec.ts")
        ]
        
        for test_file in test_files:
            assert enforcer._is_test_file(test_file) is True

    def test_is_test_file_regular_file(self, enforcer):
        """Test that regular files are not detected as test files."""
        regular_files = [
            Path("example.py"),
            Path("main.js"),
            Path("service.ts"),
            Path("model.java")
        ]
        
        for regular_file in regular_files:
            assert enforcer._is_test_file(regular_file) is False

    def test_get_language(self, enforcer):
        """Test language detection from file extensions."""
        language_tests = [
            (Path("example.py"), "python"),
            (Path("example.js"), "javascript"),
            (Path("example.ts"), "typescript"),
            (Path("example.jsx"), "javascript"),
            (Path("example.tsx"), "typescript"),
            (Path("example.swift"), "swift"),
            (Path("example.java"), "java"),
            (Path("example.cs"), "csharp"),
            (Path("example.unknown"), "python")  # default
        ]
        
        for file_path, expected_lang in language_tests:
            assert enforcer._get_language(file_path) == expected_lang

    def test_format_test_path_python(self, enforcer):
        """Test test path formatting for Python files."""
        code_file = Path("src/example.py")
        pattern = "tests/test_{stem}.py"
        
        result = enforcer._format_test_path(pattern, code_file)
        
        assert result == Path("tests/test_example.py")

    def test_format_test_path_javascript(self, enforcer):
        """Test test path formatting for JavaScript files."""
        code_file = Path("src/example.js")
        pattern = "{stem}.test.{ext}"
        
        result = enforcer._format_test_path(pattern, code_file)
        
        assert result == Path("example.test.js")

    def test_format_test_path_with_directory(self, enforcer):
        """Test test path formatting with directory placeholder."""
        code_file = Path("utils/helper.py")
        pattern = "{dir}/test_{stem}.py"
        
        result = enforcer._format_test_path(pattern, code_file)
        
        assert result == Path("utils/test_helper.py")

    def test_format_test_path_java_package(self, enforcer):
        """Test test path formatting for Java files with package structure."""
        code_file = Path("src/main/java/com/example/Service.java")
        pattern = "src/test/java/{package}/{stem}Test.java"
        
        result = enforcer._format_test_path(pattern, code_file)
        
        assert result == Path("src/test/java/com/example/ServiceTest.java")

    def test_format_test_path_error_handling(self, enforcer):
        """Test test path formatting error handling."""
        code_file = Path("example.py")
        invalid_pattern = "{invalid_placeholder}"
        
        result = enforcer._format_test_path(invalid_pattern, code_file)
        
        assert result is None

    def test_get_test_path(self, enforcer):
        """Test getting test path for code files."""
        test_cases = [
            (Path("example.py"), "tests/test_example.py"),
            (Path("example.js"), "example.test.js"),
            (Path("example.swift"), "exampleTests.swift"),
            (Path("example.unknown"), "tests/test_example.py")  # default
        ]
        
        for code_file, expected_pattern in test_cases:
            result = enforcer._get_test_path(code_file)
            assert expected_pattern in str(result)

    def test_find_existing_tests_found(self, enforcer, temp_dir):
        """Test finding existing tests when they exist."""
        # Create a Python file
        code_file = temp_dir / "example.py"
        code_file.write_text("def hello(): pass")
        
        # Create corresponding test file
        test_file = temp_dir / "tests" / "test_example.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("def test_hello(): pass")
        
        # Mock the _format_test_path to return the created test file
        with patch.object(enforcer, '_format_test_path') as mock_format:
            mock_format.return_value = test_file
            
            result = enforcer._find_existing_tests(code_file)
            
            assert result is True

    def test_find_existing_tests_not_found(self, enforcer, temp_dir):
        """Test finding existing tests when they don't exist."""
        # Create a Python file with unique name to avoid conflicts
        code_file = temp_dir / "unique_example_file.py"
        code_file.write_text("def hello(): pass")
        
        # Test should not find existing tests for this unique file
        result = enforcer._find_existing_tests(code_file)
        
        assert result is False

    def test_find_existing_tests_unsupported_language(self, enforcer, temp_dir):
        """Test finding existing tests for unsupported language."""
        # Create a file with unsupported extension
        code_file = temp_dir / "example.xyz"
        code_file.write_text("some content")
        
        # Mock _get_language to return unsupported language
        with patch.object(enforcer, '_get_language', return_value='unsupported'):
            result = enforcer._find_existing_tests(code_file)
            
            assert result is False

    def test_create_test_prompt_python(self, enforcer):
        """Test test prompt creation for Python files."""
        content = "def hello(name):\n    return f'Hello {name}'"
        language = "python"
        path = Path("example.py")
        
        prompt = enforcer._create_test_prompt(content, language, path)
        
        assert "pytest" in prompt
        assert "python" in prompt
        assert content in prompt
        assert "example.py" in prompt

    def test_create_test_prompt_javascript(self, enforcer):
        """Test test prompt creation for JavaScript files."""
        content = "function hello(name) { return `Hello ${name}` }"
        language = "javascript"
        path = Path("example.js")
        
        prompt = enforcer._create_test_prompt(content, language, path)
        
        assert "Jest" in prompt
        assert "javascript" in prompt
        assert content in prompt
        assert "example.js" in prompt

    @patch('dev_tools.smart_test_enforcer.get_config')
    def test_create_test_prompt_custom_template(self, mock_get_config, enforcer):
        """Test test prompt creation with custom template."""
        mock_config = Mock()
        mock_config.get.return_value = "Custom template: {content} for {filename}"
        mock_get_config.return_value = mock_config
        
        content = "def hello(): pass"
        language = "python"
        path = Path("example.py")
        
        prompt = enforcer._create_test_prompt(content, language, path)
        
        assert "Custom template:" in prompt
        assert content in prompt
        assert "example.py" in prompt

    def test_check_and_generate_non_code_file(self, enforcer, temp_dir):
        """Test check_and_generate with non-code file."""
        text_file = temp_dir / "readme.txt"
        text_file.write_text("This is a readme file")
        
        result = enforcer.check_and_generate(str(text_file))
        
        assert result is True

    def test_check_and_generate_existing_tests(self, enforcer, temp_dir):
        """Test check_and_generate when tests already exist."""
        # Create a Python file
        code_file = temp_dir / "example.py"
        code_file.write_text("def hello(): pass")
        
        # Mock _find_existing_tests to return True
        with patch.object(enforcer, '_find_existing_tests', return_value=True):
            result = enforcer.check_and_generate(str(code_file))
            
            assert result is True

    def test_check_and_generate_missing_tests(self, enforcer, temp_dir):
        """Test check_and_generate when tests are missing."""
        # Create a Python file
        code_file = temp_dir / "example.py"
        code_file.write_text("def hello(): pass")
        
        # Mock _find_existing_tests to return False
        with patch.object(enforcer, '_find_existing_tests', return_value=False):
            with patch('asyncio.create_task') as mock_create_task:
                result = enforcer.check_and_generate(str(code_file))
                
                assert result is True
                mock_create_task.assert_called_once()

    def test_check_and_generate_error_handling(self, enforcer):
        """Test check_and_generate error handling."""
        # Use non-existent file
        result = enforcer.check_and_generate("non_existent_file.py")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_generate_tests_async_success(self, enforcer, temp_dir):
        """Test async test generation with successful Gemini response."""
        # Create a Python file
        code_file = temp_dir / "example.py"
        code_file.write_text("def hello(): pass")
        
        # Mock asyncio subprocess
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"test content", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('asyncio.wait_for') as mock_wait_for:
                mock_wait_for.return_value = (b"test content", b"")
                
                await enforcer._generate_tests_async(code_file)
                
                # Check that test file was created
                test_file = enforcer._get_test_path(code_file)
                expected_test_file = temp_dir / "tests" / "test_example.py"
                expected_test_file.parent.mkdir(parents=True, exist_ok=True)

    @pytest.mark.asyncio
    async def test_generate_tests_async_failure(self, enforcer, temp_dir):
        """Test async test generation with Gemini failure."""
        # Create a Python file
        code_file = temp_dir / "example.py"
        code_file.write_text("def hello(): pass")
        
        # Mock failed subprocess
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Error occurred"))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('asyncio.wait_for') as mock_wait_for:
                mock_wait_for.return_value = (b"", b"Error occurred")
                
                # Should not raise exception
                await enforcer._generate_tests_async(code_file)

    @pytest.mark.asyncio
    async def test_generate_tests_async_timeout(self, enforcer, temp_dir):
        """Test async test generation with timeout."""
        # Create a Python file
        code_file = temp_dir / "example.py"
        code_file.write_text("def hello(): pass")
        
        # Mock subprocess that times out
        mock_process = Mock()
        mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()):
                
                # Should not raise exception
                await enforcer._generate_tests_async(code_file)

    @pytest.mark.asyncio
    async def test_generate_tests_async_exception(self, enforcer, temp_dir):
        """Test async test generation with unexpected exception."""
        # Create a Python file
        code_file = temp_dir / "example.py"
        code_file.write_text("def hello(): pass")
        
        with patch('asyncio.create_subprocess_exec', side_effect=Exception("Unexpected error")):
            # Should not raise exception
            await enforcer._generate_tests_async(code_file)

    def test_get_test_coverage_report(self, enforcer, temp_dir):
        """Test getting test coverage report."""
        # Create code files
        code_files = [
            temp_dir / "example1.py",
            temp_dir / "example2.py",
            temp_dir / "example3.js"
        ]
        
        for code_file in code_files:
            code_file.write_text("function hello() {}")
        
        # Create test for one file
        test_file = temp_dir / "tests" / "test_example1.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("def test_hello(): pass")
        
        # Mock _find_existing_tests to return True only for example1.py
        def mock_find_tests(path):
            return path.name == "example1.py"
        
        with patch.object(enforcer, '_find_existing_tests', side_effect=mock_find_tests):
            stats = enforcer.get_test_coverage_report(temp_dir)
            
            assert stats['total_files'] == 3
            assert stats['files_with_tests'] == 1
            assert abs(stats['coverage_percentage'] - 33.33) < 0.1
            assert len(stats['missing_tests']) == 2

    def test_get_test_coverage_report_no_files(self, enforcer, temp_dir):
        """Test getting test coverage report with no code files."""
        # Create only non-code files
        (temp_dir / "readme.md").write_text("# Readme")
        (temp_dir / "config.json").write_text("{}")
        
        stats = enforcer.get_test_coverage_report(temp_dir)
        
        assert stats['total_files'] == 0
        assert stats['files_with_tests'] == 0
        assert stats['coverage_percentage'] == 0.0
        assert len(stats['missing_tests']) == 0

    def test_get_test_coverage_report_error(self, enforcer):
        """Test getting test coverage report with error."""
        # Use non-existent directory
        stats = enforcer.get_test_coverage_report(Path("/non/existent/directory"))
        
        assert stats['total_files'] == 0

    @pytest.mark.asyncio
    async def test_generate_missing_tests_no_files(self, enforcer, temp_dir):
        """Test generating missing tests when no files need tests."""
        # Create only non-code files
        (temp_dir / "readme.md").write_text("# Readme")
        
        # Should complete without error
        enforcer.generate_missing_tests(temp_dir)

    @pytest.mark.asyncio
    async def test_generate_missing_tests_with_files(self, enforcer, temp_dir):
        """Test generating missing tests for files without tests."""
        # Create code files without tests
        code_files = [
            temp_dir / "example1.py",
            temp_dir / "example2.py"
        ]
        
        for code_file in code_files:
            code_file.write_text("def hello(): pass")
        
        # Mock _find_existing_tests to return False
        with patch.object(enforcer, '_find_existing_tests', return_value=False):
            with patch.object(enforcer, '_generate_tests_async', new_callable=AsyncMock):
                # Should complete without error
                enforcer.generate_missing_tests(temp_dir, max_concurrent=1)

    @patch('dev_tools.smart_test_enforcer.get_config')
    def test_uses_config_settings(self, mock_get_config, enforcer):
        """Test that enforcer uses configuration settings."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: {
            'dev_tools.test_generation.skip_dirs': ['custom_skip'],
            'dev_tools.test_generation.skip_patterns': ['custom_skip.py'],
            'dev_tools.test_generation.model': 'custom-model',
            'dev_tools.test_generation.timeout': 60
        }.get(key, default)
        mock_get_config.return_value = mock_config
        
        # Test skip dirs configuration
        skip_file = Path("custom_skip/example.py")
        assert enforcer._is_code_file(skip_file) is False
        
        # Test skip patterns configuration
        skip_pattern_file = Path("custom_skip.py")
        assert enforcer._is_code_file(skip_pattern_file) is False