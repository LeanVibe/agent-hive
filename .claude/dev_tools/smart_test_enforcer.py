"""
SmartTestEnforcer - Intelligent test generation system.

Extracted from hook_system.py as part of legacy refactoring.
Ensures tests exist without blocking development by generating them asynchronously.
"""

import asyncio
from pathlib import Path
from typing import Dict, Optional

from config.config_loader import get_config
from utils.logging_config import get_logger

logger = get_logger('smart_test_enforcer')


class SmartTestEnforcer:
    """Ensures tests exist without blocking development.

    This system automatically detects when tests are missing for code files
    and generates them asynchronously using Gemini CLI without blocking the
    development workflow.
    """

    def __init__(self):
        """Initialize the test enforcer with language-specific patterns."""
        self.test_patterns = {
            "python": [
                "tests/test_{stem}.py",
                "tests/{stem}_test.py",
                "{dir}/test_{stem}.py",
            ],
            "javascript": [
                "{stem}.test.{ext}",
                "{stem}.spec.{ext}",
                "__tests__/{stem}.test.{ext}",
            ],
            "typescript": [
                "{stem}.test.{ext}",
                "{stem}.spec.{ext}",
                "__tests__/{stem}.test.{ext}",
            ],
            "swift": [
                "{stem}Tests.swift",
                "Tests/{stem}Tests.swift",
            ],
            "java": [
                "src/test/java/{package}/{stem}Test.java",
                "test/{stem}Test.java",
            ],
            "csharp": [
                "{stem}Tests.cs",
                "Tests/{stem}Tests.cs",
            ]
        }

        self.code_extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.swift': 'swift',
            '.java': 'java',
            '.cs': 'csharp',
        }

        logger.info("SmartTestEnforcer initialized with multi-language support")

    def check_and_generate(self, file_path: str) -> bool:
        """Check for tests, generate if missing.

        Args:
            file_path: Path to the code file to check

        Returns:
            True if tests exist or generation was initiated, False on error
        """
        try:
            path = Path(file_path)

            # Skip non-code files
            if not self._is_code_file(path):
                logger.debug(f"Skipping non-code file: {file_path}")
                return True

            # Check if tests exist
            if self._find_existing_tests(path):
                logger.debug(f"Tests already exist for: {file_path}")
                return True

            # Generate tests asynchronously
            asyncio.create_task(self._generate_tests_async(path))

            # Don't block development
            logger.info(f"Generating tests for {file_path} in background...")
            return True

        except Exception as e:
            logger.error(
    f"Error checking/generating tests for {file_path}: {e}")
            return False

    async def _generate_tests_async(self, path: Path) -> None:
        """Generate tests using Gemini without blocking development.

        Args:
            path: Path to the code file for which to generate tests
        """
        try:
            content = path.read_text(encoding='utf-8')

            # Create language-specific prompt
            language = self._get_language(path)
            prompt = self._create_test_prompt(content, language, path)

            # Call Gemini CLI
            config = get_config()
            gemini_model = config.get(
    'dev_tools.test_generation.model',
     'gemini-1.5-flash')
            timeout = config.get('dev_tools.test_generation.timeout', 120)

            result = await asyncio.create_subprocess_exec(
                "gemini",
                "--model", gemini_model,
                "--quiet",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                result.communicate(input=prompt.encode('utf-8')),
                timeout=timeout
            )

            if result.returncode == 0:
                test_path = self._get_test_path(path)
                test_path.parent.mkdir(parents=True, exist_ok=True)
                test_path.write_text(stdout.decode('utf-8'), encoding='utf-8')
                logger.info(f"✅ Tests generated: {test_path}")
            else:
                error_msg = stderr.decode('utf-8')
                logger.error(
    f"Failed to generate tests for {path}: {error_msg}")

        except asyncio.TimeoutError:
            logger.warning(f"Test generation timed out for {path}")
        except Exception as e:
            logger.error(f"Error generating tests for {path}: {e}")

    def _is_code_file(self, path: Path) -> bool:
        """Check if the file is a code file that should have tests.

        Args:
            path: Path to check

        Returns:
            True if it's a code file, False otherwise
        """
        # Check file extension
        if path.suffix not in self.code_extensions:
            return False

        # Skip test files themselves
        if self._is_test_file(path):
            return False

        # Skip certain directories
        config = get_config()
        skip_dirs = config.get('dev_tools.test_generation.skip_dirs', [
            'tests', 'test', '__pycache__', '.git', 'node_modules',
            'venv', '.venv', 'build', 'dist', 'target'
        ])

        for skip_dir in skip_dirs:
            if skip_dir in path.parts:
                return False

        # Skip certain file patterns
        skip_patterns = config.get('dev_tools.test_generation.skip_patterns', [
            '__init__.py', 'setup.py', 'conftest.py'
        ])

        if path.name in skip_patterns:
            return False

        return True

    def _is_test_file(self, path: Path) -> bool:
        """Check if the file is already a test file.

        Args:
            path: Path to check

        Returns:
            True if it's a test file, False otherwise
        """
        test_indicators = [
            'test_', '_test', 'Test', 'Tests', '.test.', '.spec.'
        ]

        return any(indicator in path.name for indicator in test_indicators)

    def _find_existing_tests(self, path: Path) -> bool:
        """Find existing tests for the given code file.

        Args:
            path: Path to the code file

        Returns:
            True if tests exist, False otherwise
        """
        language = self._get_language(path)
        if language not in self.test_patterns:
            return False

        patterns = self.test_patterns[language]

        for pattern in patterns:
            test_path = self._format_test_path(pattern, path)
            if test_path and test_path.exists():
                logger.debug(f"Found existing test: {test_path}")
                return True

        return False

    def _get_test_path(self, path: Path) -> Path:
        """Get the path where tests should be generated.

        Args:
            path: Path to the code file

        Returns:
            Path where tests should be created
        """
        language = self._get_language(path)
        if language not in self.test_patterns:
            # Default to Python pattern
            pattern = "tests/test_{stem}.py"
        else:
            pattern = self.test_patterns[language][0]  # Use first pattern

        test_path = self._format_test_path(pattern, path)
        return test_path if test_path else Path(f"tests/test_{path.stem}.py")

    def _format_test_path(self, pattern: str, path: Path) -> Optional[Path]:
        """Format a test path pattern with actual values.

        Args:
            pattern: Test path pattern with placeholders
            path: Original code file path

        Returns:
            Formatted test path or None if formatting failed
        """
        try:
            # Extract components
            stem = path.stem
            ext = path.suffix
            dir_name = path.parent.name if path.parent.name != '.' else ''

            # Handle package path for Java
            package_parts = []
            if path.suffix == '.java':
                # Extract package from path
                parts = path.parts
                if 'src' in parts:
                    src_index = parts.index('src')
                    if src_index + \
                        1 < len(parts) and parts[src_index + 1] == 'main':
                        if src_index + \
                            2 < len(parts) and parts[src_index + 2] == 'java':
                            package_parts = parts[src_index + 3:-1]

            package = '/'.join(package_parts) if package_parts else ''

            # Format the pattern
            formatted = pattern.format(
                stem=stem,
                ext=ext.lstrip('.'),
                dir=dir_name,
                package=package
            )

            return Path(formatted)

        except Exception as e:
            logger.warning(
    f"Failed to format test path pattern {pattern}: {e}")
            return None

    def _get_language(self, path: Path) -> str:
        """Get the programming language for the file.

        Args:
            path: Path to the code file

        Returns:
            Language identifier
        """
        return self.code_extensions.get(path.suffix, 'python')

    def _create_test_prompt(
        self, content: str, language: str, path: Path) -> str:
        """Create a language-specific test generation prompt.

        Args:
            content: Source code content
            language: Programming language
            path: Path to the source file

        Returns:
            Formatted prompt for test generation
        """
        config = get_config()

        # Language-specific test frameworks
        frameworks = {
            'python': 'pytest',
            'javascript': 'Jest',
            'typescript': 'Jest',
            'swift': 'XCTest',
            'java': 'JUnit',
            'csharp': 'NUnit'
        }

        framework = frameworks.get(language, 'pytest')

        # Get custom prompt template if available
        custom_prompt = config.get(
    f'dev_tools.test_generation.prompts.{language}')
        if custom_prompt:
            return custom_prompt.format(
                content=content,
                framework=framework,
                filename=path.name
            )

        # Default prompt
        return f"""Generate comprehensive {framework} tests for this {language} code:

File: {path.name}
```{language}
{content}
```

Requirements:
- Use {framework} testing framework
- Include edge cases and error handling
- Test both success and failure paths
- Mock external dependencies
- Follow {language} testing best practices
- Ensure good test coverage

Output only the test code, no explanations or markdown."""

    def get_test_coverage_report(self, directory: Path = None) -> Dict:
        """Get a report of test coverage for code files.

        Args:
            directory: Directory to analyze (defaults to current directory)

        Returns:
            Dictionary with coverage statistics
        """
        if directory is None:
            directory = Path.cwd()

        stats = {
            'total_files': 0,
            'files_with_tests': 0,
            'coverage_percentage': 0.0,
            'missing_tests': []
        }

        try:
            # Find all code files
            for path in directory.rglob('*'):
                if self._is_code_file(path):
                    stats['total_files'] += 1

                    if self._find_existing_tests(path):
                        stats['files_with_tests'] += 1
                    else:
                        stats['missing_tests'].append(str(path))

            # Calculate coverage
            if stats['total_files'] > 0:
                stats['coverage_percentage'] = (
                    stats['files_with_tests'] / stats['total_files'] * 100
                )

            logger.info(f"Test coverage: {stats['coverage_percentage']:.1f}% "
                       f"({stats['files_with_tests']}/{stats['total_files']} files)")

        except Exception as e:
            logger.error(f"Error generating test coverage report: {e}")

        return stats

    def generate_missing_tests(self, directory: Path = None,
                             max_concurrent: int = 3) -> None:
        """Generate tests for all files missing them.

        Args:
            directory: Directory to analyze (defaults to current directory)
            max_concurrent: Maximum number of concurrent test generations
        """
        if directory is None:
            directory = Path.cwd()

        # Find files without tests
        files_without_tests = []
        for path in directory.rglob('*'):
            if self._is_code_file(
                path) and not self._find_existing_tests(path):
                files_without_tests.append(path)

        if not files_without_tests:
            logger.info("All code files have tests!")
            return

        logger.info(
    f"Generating tests for {
        len(files_without_tests)} files...")

        # Generate tests with concurrency limit
        async def generate_batch():
            semaphore = asyncio.Semaphore(max_concurrent)

            async def generate_with_semaphore(path):
                async with semaphore:
                    await self._generate_tests_async(path)

            tasks = [generate_with_semaphore(path)
                                             for path in files_without_tests]
            await asyncio.gather(*tasks, return_exceptions=True)

        # Run the batch generation - handle event loop properly
        try:
            asyncio.get_running_loop()
            # If we're in a running event loop, schedule the task
            asyncio.create_task(generate_batch())
        except RuntimeError:
            # No running event loop, safe to use asyncio.run
            asyncio.run(generate_batch())
