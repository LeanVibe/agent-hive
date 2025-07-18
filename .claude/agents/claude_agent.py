# .claude/agents/claude_agent.py
"""ClaudeAgent implementation for LeanVibe orchestration system."""

import asyncio
import json
import signal
import time
from typing import Any, Dict, List

import psutil
from agents.base_agent import AgentInfo, AgentStatus, BaseAgent, Result, Task
from config.config_loader import get_config
from utils.logging_config import (
    get_logger,
    log_error,
    log_performance,
    set_task_context,
)

logger = get_logger('claude_agent')


class CLIError(Exception):
    """Exception raised when CLI command fails."""


class CLITimeout(Exception):
    """Exception raised when CLI command times out."""


class CircuitBreaker:
    """Circuit breaker pattern for external CLI calls."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == 'CLOSED':
            return True
        elif self.state == 'OPEN':
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = 'HALF_OPEN'
                return True
            return False
        elif self.state == 'HALF_OPEN':
            return True
        return False

    def record_success(self):
        """Record successful execution."""
        self.failure_count = 0
        self.state = 'CLOSED'

    def record_failure(self):
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(
    f"Circuit breaker opened after {
        self.failure_count} failures")


class CLIManager:
    """Manager for CLI subprocess operations."""

    def __init__(self, cli_path: str, timeout: int = 300):
        self.cli_path = cli_path
        self.timeout = timeout
        self.circuit_breaker = CircuitBreaker()

    async def execute_command(
        self, args: List[str], input_data: str = None) -> Dict[str, Any]:
        """Execute CLI command with proper error handling.

        Args:
            args: Command arguments
            input_data: Optional input data

        Returns:
            Command result dictionary

        Raises:
            CLIError: If command fails
            CLITimeout: If command times out
        """
        if not self.circuit_breaker.can_execute():
            raise CLIError("Circuit breaker is open")

        start_time = time.time()
        process = None

        try:
            # Prepare command
            cmd = [self.cli_path] + args
            logger.debug(f"Executing command: {' '.join(cmd)}")

            # Start subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=lambda: signal.signal(
                    signal.SIGPIPE, signal.SIG_DFL)
            )

            # Execute with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(
    input=input_data.encode() if input_data else None),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                # Kill process and children
                await self._kill_process_tree(process)
                raise CLITimeout(f"Command timed out after {self.timeout}s")

            # Parse result
            result = self._parse_command_result(
                process.returncode,
                stdout.decode(),
                stderr.decode()
            )

            # Record metrics
            duration = time.time() - start_time
            log_performance("cli_command", duration, {
                'command': ' '.join(cmd),
                'return_code': process.returncode,
                'stdout_size': len(stdout),
                'stderr_size': len(stderr)
            })

            self.circuit_breaker.record_success()
            return result

        except Exception as e:
            duration = time.time() - start_time
            self.circuit_breaker.record_failure()

            # Clean up process
            if process and process.returncode is None:
                await self._kill_process_tree(process)

            log_error(e, "CLI command execution", {
                'command': ' '.join(cmd) if 'cmd' in locals() else 'unknown',
                'duration': duration
            })

            if isinstance(e, (CLIError, CLITimeout)):
                raise
            else:
                raise CLIError(f"Command execution failed: {e}")

    async def _kill_process_tree(self, process: asyncio.subprocess.Process):
        """Kill process and all its children."""
        try:
            if process.pid:
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)

                # Kill children first
                for child in children:
                    try:
                        child.terminate()
                    except psutil.NoSuchProcess:
                        pass

                # Kill parent
                try:
                    parent.terminate()
                except psutil.NoSuchProcess:
                    pass

                # Wait for termination
                await asyncio.sleep(0.1)

                # Force kill if still alive
                for child in children:
                    try:
                        if child.is_running():
                            child.kill()
                    except psutil.NoSuchProcess:
                        pass

                try:
                    if parent.is_running():
                        parent.kill()
                except psutil.NoSuchProcess:
                    pass

        except Exception as e:
            logger.warning(f"Error killing process tree: {e}")

    def _parse_command_result(self, return_code: int,
                              stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse command result from stdout/stderr.

        Args:
            return_code: Process return code
            stdout: Standard output
            stderr: Standard error

        Returns:
            Parsed result dictionary
        """
        # Try to parse JSON output
        try:
            if stdout.strip():
                result = json.loads(stdout)
                if isinstance(result, dict):
                    return result
        except json.JSONDecodeError:
            pass

        # Fallback to simple parsing
        if return_code == 0:
            return {
                'status': 'success',
                'output': stdout,
                'error': stderr if stderr else None
            }
        else:
            return {
                'status': 'error',
                'output': stdout if stdout else None,
                'error': stderr if stderr else 'Unknown error',
                'return_code': return_code
            }


class ClaudeAgent(BaseAgent):
    """Claude Code CLI agent implementation."""

    def __init__(self, agent_id: str = "claude-agent"):
        config = get_config()
        agent_config = config.get_agent_config('claude')

        super().__init__(
            agent_id=agent_id,
            capabilities=agent_config.get('capabilities', ['code_generation'])
        )

        # Initialize CLI manager
        cli_path = config.get_cli_path('claude')
        timeout = agent_config.get('timeout', 300)
        self.cli_manager = CLIManager(cli_path, timeout)

        # Configuration
        self.max_retries = agent_config.get('max_retries', 3)
        self.resource_limits = agent_config.get('resource_limits', {})

        # State tracking
        self.tasks_completed = 0
        self.total_execution_time = 0.0
        self.last_error = None

        logger.info(f"ClaudeAgent initialized with CLI path: {cli_path}")
        self.update_status(AgentStatus.IDLE)

    async def execute_task(self, task: Task) -> Result:
        """Execute a task using Claude Code CLI.

        Args:
            task: Task to execute

        Returns:
            Result object with execution details
        """
        set_task_context(task.id, self.agent_id)
        logger.info(f"Executing task: {task.id} ({task.type})")

        start_time = time.time()
        self.start_task(task)

        try:
            # Validate task
            if not self.can_handle_task(task):
                raise ValueError(f"Cannot handle task type: {task.type}")

            # Execute task with retries
            result = await self._execute_with_retries(task)

            # Update metrics
            execution_time = time.time() - start_time
            self.tasks_completed += 1
            self.total_execution_time += execution_time

            self.complete_task()

            logger.info(
    f"Task {
        task.id} completed successfully in {
            execution_time:.2f}s")
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self.last_error = str(e)
            self.update_status(AgentStatus.ERROR, str(e))

            log_error(e, f"Task execution failed: {task.id}")

            return Result(
                task_id=task.id,
                status="failure",
                data={},
                error=str(e),
                execution_time=execution_time,
                confidence=0.0
            )

    async def _execute_with_retries(self, task: Task) -> Result:
        """Execute task with retry logic.

        Args:
            task: Task to execute

        Returns:
            Result object
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return await self._execute_single_task(task)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
    f"Task {
        task.id} failed (attempt {
            attempt +
             1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
    f"Task {
        task.id} failed after {
            self.max_retries} attempts: {e}")

        raise last_error

    async def _execute_single_task(self, task: Task) -> Result:
        """Execute a single task attempt.

        Args:
            task: Task to execute

        Returns:
            Result object
        """
        # Prepare command arguments based on task type
        args = self._prepare_command_args(task)

        # Execute command
        cli_result = await self.cli_manager.execute_command(args)

        # Parse result
        return self._parse_task_result(task, cli_result)

    def _prepare_command_args(self, task: Task) -> List[str]:
        """Prepare command arguments for CLI execution.

        Args:
            task: Task to execute

        Returns:
            List of command arguments
        """
        args = []

        # Add prompt
        if 'prompt' in task.data:
            args.extend(['-p', task.data['prompt']])

        # Add task-specific arguments
        if task.type == 'code_generation':
            if 'language' in task.data:
                args.extend(['--language', task.data['language']])
        elif task.type == 'code_review':
            if 'file_path' in task.data:
                args.extend(['--file', task.data['file_path']])

        # Add common arguments
        args.extend(['--format', 'json'])

        return args

    def _parse_task_result(
        self, task: Task, cli_result: Dict[str, Any]) -> Result:
        """Parse CLI result into Task result.

        Args:
            task: Original task
            cli_result: CLI execution result

        Returns:
            Result object
        """
        if cli_result.get('status') == 'success':
            return Result(
                task_id=task.id,
                status="success",
                data=cli_result,
                confidence=cli_result.get('confidence', 0.8)
            )
        else:
            return Result(
                task_id=task.id,
                status="failure",
                data=cli_result,
                error=cli_result.get('error', 'Unknown error'),
                confidence=0.0
            )

    async def get_status(self) -> AgentInfo:
        """Get current agent status.

        Returns:
            AgentInfo object with current status
        """
        # Update resource usage
        try:
            import psutil
            process = psutil.Process()
            self.resource_usage = {
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(),
                'tasks_completed': self.tasks_completed,
                'total_execution_time': self.total_execution_time,
                'average_task_time': (
                    self.total_execution_time / self.tasks_completed
                    if self.tasks_completed > 0 else 0
                )
            }
        except ImportError:
            pass

        return self.get_basic_info()

    def get_capabilities(self) -> List[str]:
        """Return agent capabilities.

        Returns:
            List of capability strings
        """
        return self.capabilities

    async def health_check(self) -> bool:
        """Check if agent is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Test CLI availability
            test_args = ['--version']
            await self.cli_manager.execute_command(test_args)

            # Check circuit breaker state
            if self.cli_manager.circuit_breaker.state == 'OPEN':
                logger.warning("Health check failed: circuit breaker is open")
                return False

            # Check resource usage
            if self.resource_usage:
                memory_mb = self.resource_usage.get('memory_mb', 0)
                cpu_percent = self.resource_usage.get('cpu_percent', 0)

                max_memory = self.resource_limits.get('max_memory_mb', 1024)
                max_cpu = self.resource_limits.get('max_cpu_percent', 90)

                if memory_mb > max_memory:
                    logger.warning(
    f"High memory usage: {memory_mb}MB > {max_memory}MB")
                    return False

                if cpu_percent > max_cpu:
                    logger.warning(
    f"High CPU usage: {cpu_percent}% > {max_cpu}%")
                    return False

            return True

        except Exception as e:
            log_error(e, "Health check failed")
            return False

    async def shutdown(self) -> None:
        """Gracefully shutdown the agent."""
        logger.info(f"Shutting down ClaudeAgent {self.agent_id}")

        # Cancel current task if any
        if self.current_task:
            logger.info(f"Cancelling current task: {self.current_task.id}")
            self.current_task = None

        # Update status
        self.update_status(AgentStatus.SHUTDOWN)

        # Log final metrics
        logger.info(f"Agent shutdown complete - Tasks completed: {self.tasks_completed}, "
                   f"Total execution time: {self.total_execution_time:.2f}s")
