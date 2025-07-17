"""
Advanced Request Validation Middleware
====================================

Comprehensive request validation with security checks, payload analysis,
input sanitization, and threat detection.
"""

import re
import json
import time
import base64
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import ipaddress
import urllib.parse
from pathlib import Path

from pydantic import BaseModel, validator
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class ValidationResult(Enum):
    """Validation result types"""
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"
    SANITIZE = "sanitize"


class ThreatType(Enum):
    """Security threat types"""
    XSS = "xss"
    SQL_INJECTION = "sql_injection"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    XXSS = "xxss"
    CSRF = "csrf"
    MALFORMED_JSON = "malformed_json"
    OVERSIZED_PAYLOAD = "oversized_payload"
    SUSPICIOUS_HEADERS = "suspicious_headers"
    MALICIOUS_FILE = "malicious_file"


@dataclass
class ValidationRule:
    """Validation rule configuration"""
    name: str
    pattern: str
    threat_type: ThreatType
    action: ValidationResult
    severity: int  # 1-10
    description: str
    enabled: bool = True


class SecurityValidationResult(BaseModel):
    """Result of security validation"""
    passed: bool
    action: ValidationResult
    threats_detected: List[ThreatType] = []
    sanitized_data: Optional[Dict[str, Any]] = None
    security_score: float = 0.0
    warnings: List[str] = []
    blocked_reason: Optional[str] = None
    processing_time: float = 0.0


class RequestValidationEngine:
    """Advanced request validation engine"""
    
    def __init__(self, redis_client: redis.Redis, config: Dict[str, Any]):
        self.redis = redis_client
        self.config = config
        self.validation_rules = self._load_validation_rules()
        self.blocked_patterns = self._load_blocked_patterns()
        self.file_type_validators = self._load_file_validators()
        
        # Configuration
        self.max_payload_size = config.get('max_payload_size', 10 * 1024 * 1024)  # 10MB
        self.max_header_size = config.get('max_header_size', 8192)  # 8KB
        self.max_url_length = config.get('max_url_length', 2048)
        self.enable_sanitization = config.get('enable_sanitization', True)
        self.strict_mode = config.get('strict_mode', False)
        
    def _load_validation_rules(self) -> List[ValidationRule]:
        """Load validation rules for different threat types"""
        return [
            # XSS patterns
            ValidationRule(
                name="xss_script_tags",
                pattern=r'<script[^>]*>.*?</script>',
                threat_type=ThreatType.XSS,
                action=ValidationResult.BLOCK,
                severity=9,
                description="Script tag injection attempt"
            ),
            ValidationRule(
                name="xss_javascript_protocol",
                pattern=r'javascript\s*:',
                threat_type=ThreatType.XSS,
                action=ValidationResult.BLOCK,
                severity=8,
                description="JavaScript protocol in URL"
            ),
            ValidationRule(
                name="xss_event_handlers",
                pattern=r'on\w+\s*=',
                threat_type=ThreatType.XSS,
                action=ValidationResult.SANITIZE,
                severity=7,
                description="HTML event handler attributes"
            ),
            
            # SQL Injection patterns
            ValidationRule(
                name="sql_union_select",
                pattern=r'union\s+select',
                threat_type=ThreatType.SQL_INJECTION,
                action=ValidationResult.BLOCK,
                severity=9,
                description="SQL UNION SELECT injection"
            ),
            ValidationRule(
                name="sql_drop_table",
                pattern=r'drop\s+table',
                threat_type=ThreatType.SQL_INJECTION,
                action=ValidationResult.BLOCK,
                severity=10,
                description="SQL DROP TABLE command"
            ),
            ValidationRule(
                name="sql_comments",
                pattern=r'(/\*|\*/|--|\#)',
                threat_type=ThreatType.SQL_INJECTION,
                action=ValidationResult.WARN,
                severity=6,
                description="SQL comment syntax"
            ),
            
            # Command Injection patterns
            ValidationRule(
                name="command_injection_pipes",
                pattern=r'[|&;`]',
                threat_type=ThreatType.COMMAND_INJECTION,
                action=ValidationResult.WARN,
                severity=7,
                description="Command injection pipe characters"
            ),
            ValidationRule(
                name="command_injection_backticks",
                pattern=r'`[^`]*`',
                threat_type=ThreatType.COMMAND_INJECTION,
                action=ValidationResult.BLOCK,
                severity=8,
                description="Command substitution backticks"
            ),
            
            # Path Traversal patterns
            ValidationRule(
                name="path_traversal_dotdot",
                pattern=r'\.\./',
                threat_type=ThreatType.PATH_TRAVERSAL,
                action=ValidationResult.BLOCK,
                severity=8,
                description="Directory traversal attempt"
            ),
            ValidationRule(
                name="path_traversal_absolute",
                pattern=r'(/etc/|/var/|/usr/|/bin/|/sbin/)',
                threat_type=ThreatType.PATH_TRAVERSAL,
                action=ValidationResult.BLOCK,
                severity=9,
                description="Absolute system path access"
            ),
            
            # File inclusion patterns
            ValidationRule(
                name="file_inclusion_php",
                pattern=r'(include|require)(_once)?\s*\(',
                threat_type=ThreatType.COMMAND_INJECTION,
                action=ValidationResult.BLOCK,
                severity=8,
                description="PHP file inclusion"
            ),
        ]
    
    def _load_blocked_patterns(self) -> Dict[str, List[str]]:
        """Load blocked patterns for different categories"""
        return {
            'user_agents': [
                'sqlmap', 'nikto', 'w3af', 'burp', 'nessus', 'openvas',
                'nmap', 'masscan', 'zap', 'acunetix', 'qualys'
            ],
            'suspicious_headers': [
                'X-Forwarded-For: 127.0.0.1',
                'X-Real-IP: localhost',
                'X-Originating-IP: 127.0.0.1'
            ],
            'malicious_extensions': [
                '.php', '.asp', '.aspx', '.jsp', '.exe', '.bat', '.sh',
                '.ps1', '.vbs', '.scr', '.com', '.pif'
            ],
            'sensitive_files': [
                '/etc/passwd', '/etc/shadow', '/etc/hosts', '/proc/',
                'web.config', '.htaccess', '.env', 'database.yml'
            ]
        }
    
    def _load_file_validators(self) -> Dict[str, callable]:
        """Load file type validators"""
        return {
            'image': self._validate_image_file,
            'document': self._validate_document_file,
            'archive': self._validate_archive_file,
            'executable': self._validate_executable_file
        }
    
    async def validate_request(self, request_data: Dict[str, Any]) -> SecurityValidationResult:
        """Comprehensive request validation"""
        start_time = time.time()
        
        result = SecurityValidationResult(
            passed=True,
            action=ValidationResult.PASS,
            security_score=100.0
        )
        
        try:
            # Size validation
            size_result = await self._validate_request_size(request_data)
            if not size_result.passed:
                return size_result
            
            # Header validation
            header_result = await self._validate_headers(request_data.get('headers', {}))
            self._merge_results(result, header_result)
            
            # URL validation
            url_result = await self._validate_url(request_data.get('url', ''))
            self._merge_results(result, url_result)
            
            # Body validation
            if 'body' in request_data:
                body_result = await self._validate_body(request_data['body'])
                self._merge_results(result, body_result)
            
            # File validation
            if 'files' in request_data:
                file_result = await self._validate_files(request_data['files'])
                self._merge_results(result, file_result)
            
            # Pattern matching validation
            pattern_result = await self._validate_patterns(request_data)
            self._merge_results(result, pattern_result)
            
            # Behavioral validation
            behavior_result = await self._validate_behavior(request_data)
            self._merge_results(result, behavior_result)
            
            # Final decision
            result.passed = result.action != ValidationResult.BLOCK
            result.processing_time = time.time() - start_time
            
            # Log validation result
            await self._log_validation_result(request_data, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Request validation failed: {e}")
            result.passed = False
            result.action = ValidationResult.BLOCK
            result.blocked_reason = "Validation error"
            result.processing_time = time.time() - start_time
            return result
    
    async def _validate_request_size(self, request_data: Dict[str, Any]) -> SecurityValidationResult:
        """Validate request size limits"""
        result = SecurityValidationResult(passed=True, action=ValidationResult.PASS)
        
        # Check payload size
        payload_size = len(json.dumps(request_data).encode('utf-8'))
        if payload_size > self.max_payload_size:
            result.passed = False
            result.action = ValidationResult.BLOCK
            result.blocked_reason = f"Payload size {payload_size} exceeds limit {self.max_payload_size}"
            result.threats_detected.append(ThreatType.OVERSIZED_PAYLOAD)
            result.security_score = 0.0
            return result
        
        # Check URL length
        url = request_data.get('url', '')
        if len(url) > self.max_url_length:
            result.passed = False
            result.action = ValidationResult.BLOCK
            result.blocked_reason = f"URL length {len(url)} exceeds limit {self.max_url_length}"
            result.security_score = 0.0
            return result
        
        return result
    
    async def _validate_headers(self, headers: Dict[str, str]) -> SecurityValidationResult:
        """Validate HTTP headers"""
        result = SecurityValidationResult(passed=True, action=ValidationResult.PASS)
        
        # Check header size
        headers_size = sum(len(k) + len(v) for k, v in headers.items())
        if headers_size > self.max_header_size:
            result.action = ValidationResult.BLOCK
            result.blocked_reason = f"Headers size {headers_size} exceeds limit"
            result.security_score = 0.0
            return result
        
        # Check for suspicious headers
        for header, value in headers.items():
            header_lower = header.lower()
            value_lower = value.lower()
            
            # Check for suspicious user agents
            if header_lower == 'user-agent':
                for blocked_ua in self.blocked_patterns['user_agents']:
                    if blocked_ua in value_lower:
                        result.action = ValidationResult.BLOCK
                        result.blocked_reason = f"Suspicious user agent: {value}"
                        result.threats_detected.append(ThreatType.SUSPICIOUS_HEADERS)
                        result.security_score = 0.0
                        return result
            
            # Check for header injection
            if '\n' in value or '\r' in value:
                result.action = ValidationResult.BLOCK
                result.blocked_reason = "Header injection detected"
                result.threats_detected.append(ThreatType.SUSPICIOUS_HEADERS)
                result.security_score = 0.0
                return result
            
            # Check for suspicious forwarded headers
            if header_lower in ['x-forwarded-for', 'x-real-ip', 'x-originating-ip']:
                if 'localhost' in value_lower or '127.0.0.1' in value_lower:
                    result.action = ValidationResult.WARN
                    result.warnings.append(f"Suspicious {header}: {value}")
                    result.security_score -= 10
        
        return result
    
    async def _validate_url(self, url: str) -> SecurityValidationResult:
        """Validate URL structure and content"""
        result = SecurityValidationResult(passed=True, action=ValidationResult.PASS)
        
        if not url:
            return result
        
        # Parse URL
        try:
            parsed = urllib.parse.urlparse(url)
        except Exception:
            result.action = ValidationResult.BLOCK
            result.blocked_reason = "Malformed URL"
            result.security_score = 0.0
            return result
        
        # Check for path traversal
        if '..' in parsed.path:
            result.action = ValidationResult.BLOCK
            result.blocked_reason = "Path traversal in URL"
            result.threats_detected.append(ThreatType.PATH_TRAVERSAL)
            result.security_score = 0.0
            return result
        
        # Check for sensitive files
        for sensitive_file in self.blocked_patterns['sensitive_files']:
            if sensitive_file in parsed.path:
                result.action = ValidationResult.BLOCK
                result.blocked_reason = f"Access to sensitive file: {sensitive_file}"
                result.threats_detected.append(ThreatType.PATH_TRAVERSAL)
                result.security_score = 0.0
                return result
        
        # Check query parameters
        if parsed.query:
            query_params = urllib.parse.parse_qs(parsed.query)
            for param, values in query_params.items():
                for value in values:
                    param_result = await self._validate_string_content(value)
                    if not param_result.passed:
                        result.action = param_result.action
                        result.blocked_reason = f"Malicious content in query param {param}"
                        result.threats_detected.extend(param_result.threats_detected)
                        result.security_score = min(result.security_score, param_result.security_score)
        
        return result
    
    async def _validate_body(self, body: Any) -> SecurityValidationResult:
        """Validate request body content"""
        result = SecurityValidationResult(passed=True, action=ValidationResult.PASS)
        
        if not body:
            return result
        
        # Convert body to string for analysis
        if isinstance(body, dict):
            body_str = json.dumps(body)
        elif isinstance(body, bytes):
            try:
                body_str = body.decode('utf-8')
            except UnicodeDecodeError:
                result.action = ValidationResult.WARN
                result.warnings.append("Binary content detected")
                result.security_score -= 5
                return result
        else:
            body_str = str(body)
        
        # Validate JSON structure
        if isinstance(body, str):
            try:
                json.loads(body)
            except json.JSONDecodeError:
                # Not JSON, check if it's form data or other format
                if 'application/json' in str(body):
                    result.action = ValidationResult.BLOCK
                    result.blocked_reason = "Malformed JSON"
                    result.threats_detected.append(ThreatType.MALFORMED_JSON)
                    result.security_score = 0.0
                    return result
        
        # Content validation
        content_result = await self._validate_string_content(body_str)
        self._merge_results(result, content_result)
        
        return result
    
    async def _validate_files(self, files: List[Dict[str, Any]]) -> SecurityValidationResult:
        """Validate uploaded files"""
        result = SecurityValidationResult(passed=True, action=ValidationResult.PASS)
        
        for file_data in files:
            filename = file_data.get('filename', '')
            content = file_data.get('content', b'')
            content_type = file_data.get('content_type', '')
            
            # Check file extension
            file_ext = Path(filename).suffix.lower()
            if file_ext in self.blocked_patterns['malicious_extensions']:
                result.action = ValidationResult.BLOCK
                result.blocked_reason = f"Blocked file extension: {file_ext}"
                result.threats_detected.append(ThreatType.MALICIOUS_FILE)
                result.security_score = 0.0
                return result
            
            # Check file content
            if isinstance(content, bytes):
                # Check for executable signatures
                if content.startswith(b'MZ') or content.startswith(b'\x7fELF'):
                    result.action = ValidationResult.BLOCK
                    result.blocked_reason = "Executable file detected"
                    result.threats_detected.append(ThreatType.MALICIOUS_FILE)
                    result.security_score = 0.0
                    return result
                
                # Check for script content in images
                if content_type.startswith('image/'):
                    if b'<script' in content or b'javascript:' in content:
                        result.action = ValidationResult.BLOCK
                        result.blocked_reason = "Script content in image file"
                        result.threats_detected.append(ThreatType.XSS)
                        result.security_score = 0.0
                        return result
        
        return result
    
    async def _validate_patterns(self, request_data: Dict[str, Any]) -> SecurityValidationResult:
        """Validate against known attack patterns"""
        result = SecurityValidationResult(passed=True, action=ValidationResult.PASS)
        
        # Convert entire request to string for pattern matching
        request_str = json.dumps(request_data, default=str).lower()
        
        for rule in self.validation_rules:
            if not rule.enabled:
                continue
            
            if re.search(rule.pattern, request_str, re.IGNORECASE):
                result.threats_detected.append(rule.threat_type)
                result.security_score -= rule.severity * 5
                
                if rule.action == ValidationResult.BLOCK:
                    result.action = ValidationResult.BLOCK
                    result.blocked_reason = f"Pattern matched: {rule.description}"
                    result.security_score = 0.0
                    return result
                elif rule.action == ValidationResult.WARN:
                    result.warnings.append(f"Suspicious pattern: {rule.description}")
                elif rule.action == ValidationResult.SANITIZE:
                    result.action = ValidationResult.SANITIZE
                    result.warnings.append(f"Content sanitized: {rule.description}")
        
        return result
    
    async def _validate_behavior(self, request_data: Dict[str, Any]) -> SecurityValidationResult:
        """Validate behavioral patterns"""
        result = SecurityValidationResult(passed=True, action=ValidationResult.PASS)
        
        # Check for rapid successive requests from same IP
        ip = request_data.get('ip')
        if ip:
            request_count = await self.redis.incr(f"request_count:{ip}")
            await self.redis.expire(f"request_count:{ip}", 60)
            
            if request_count > 100:  # 100 requests per minute
                result.action = ValidationResult.WARN
                result.warnings.append("High request rate detected")
                result.security_score -= 20
        
        return result
    
    async def _validate_string_content(self, content: str) -> SecurityValidationResult:
        """Validate string content against attack patterns"""
        result = SecurityValidationResult(passed=True, action=ValidationResult.PASS)
        
        for rule in self.validation_rules:
            if not rule.enabled:
                continue
            
            if re.search(rule.pattern, content, re.IGNORECASE):
                result.threats_detected.append(rule.threat_type)
                result.security_score -= rule.severity * 5
                
                if rule.action == ValidationResult.BLOCK:
                    result.action = ValidationResult.BLOCK
                    result.blocked_reason = f"Pattern matched: {rule.description}"
                    result.security_score = 0.0
                    return result
                elif rule.action == ValidationResult.WARN:
                    result.warnings.append(f"Suspicious pattern: {rule.description}")
                elif rule.action == ValidationResult.SANITIZE:
                    result.action = ValidationResult.SANITIZE
                    result.warnings.append(f"Content sanitized: {rule.description}")
        
        return result
    
    def _merge_results(self, main_result: SecurityValidationResult, 
                      sub_result: SecurityValidationResult):
        """Merge validation results"""
        if sub_result.action == ValidationResult.BLOCK:
            main_result.action = ValidationResult.BLOCK
            main_result.blocked_reason = sub_result.blocked_reason
            main_result.security_score = 0.0
        elif sub_result.action == ValidationResult.SANITIZE and main_result.action == ValidationResult.PASS:
            main_result.action = ValidationResult.SANITIZE
        
        main_result.threats_detected.extend(sub_result.threats_detected)
        main_result.warnings.extend(sub_result.warnings)
        main_result.security_score = min(main_result.security_score, sub_result.security_score)
    
    async def _log_validation_result(self, request_data: Dict[str, Any], 
                                   result: SecurityValidationResult):
        """Log validation results for monitoring"""
        log_entry = {
            'timestamp': time.time(),
            'ip': request_data.get('ip'),
            'url': request_data.get('url'),
            'method': request_data.get('method'),
            'result': result.action.value,
            'threats': [t.value for t in result.threats_detected],
            'security_score': result.security_score,
            'processing_time': result.processing_time
        }
        
        await self.redis.lpush("validation_log", json.dumps(log_entry))
        await self.redis.ltrim("validation_log", 0, 9999)  # Keep last 10k entries
    
    async def sanitize_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize request data"""
        if not self.enable_sanitization:
            return request_data
        
        sanitized = request_data.copy()
        
        # Sanitize string values
        def sanitize_value(value):
            if isinstance(value, str):
                # Remove script tags
                value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE)
                # Remove event handlers
                value = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', value, flags=re.IGNORECASE)
                # Remove javascript: protocol
                value = re.sub(r'javascript\s*:', '', value, flags=re.IGNORECASE)
                # HTML encode dangerous characters
                value = value.replace('<', '&lt;').replace('>', '&gt;')
                return value
            elif isinstance(value, dict):
                return {k: sanitize_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [sanitize_value(item) for item in value]
            else:
                return value
        
        sanitized = sanitize_value(sanitized)
        return sanitized
    
    async def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        try:
            # Get recent validation logs
            logs = await self.redis.lrange("validation_log", 0, 999)
            
            if not logs:
                return {'total_requests': 0, 'blocked_requests': 0, 'threat_types': {}}
            
            parsed_logs = [json.loads(log) for log in logs]
            
            total_requests = len(parsed_logs)
            blocked_requests = sum(1 for log in parsed_logs if log['result'] == 'block')
            
            # Count threat types
            threat_counts = {}
            for log in parsed_logs:
                for threat in log['threats']:
                    threat_counts[threat] = threat_counts.get(threat, 0) + 1
            
            # Calculate average security score
            avg_security_score = sum(log['security_score'] for log in parsed_logs) / total_requests
            
            return {
                'total_requests': total_requests,
                'blocked_requests': blocked_requests,
                'block_rate': blocked_requests / total_requests if total_requests > 0 else 0,
                'threat_types': threat_counts,
                'average_security_score': avg_security_score,
                'average_processing_time': sum(log['processing_time'] for log in parsed_logs) / total_requests
            }
            
        except Exception as e:
            logger.error(f"Failed to get validation stats: {e}")
            return {'error': str(e)}
    
    # File validation methods
    async def _validate_image_file(self, content: bytes) -> bool:
        """Validate image file"""
        # Check for common image signatures
        image_signatures = [
            b'\xff\xd8\xff',  # JPEG
            b'\x89PNG\r\n\x1a\n',  # PNG
            b'GIF87a',  # GIF87a
            b'GIF89a',  # GIF89a
            b'BM',  # BMP
        ]
        
        return any(content.startswith(sig) for sig in image_signatures)
    
    async def _validate_document_file(self, content: bytes) -> bool:
        """Validate document file"""
        # Check for document signatures
        doc_signatures = [
            b'%PDF',  # PDF
            b'PK\x03\x04',  # ZIP/Office formats
            b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',  # Old Office formats
        ]
        
        return any(content.startswith(sig) for sig in doc_signatures)
    
    async def _validate_archive_file(self, content: bytes) -> bool:
        """Validate archive file"""
        # Check for archive signatures
        archive_signatures = [
            b'PK\x03\x04',  # ZIP
            b'Rar!\x1a\x07\x00',  # RAR
            b'\x1f\x8b\x08',  # GZIP
            b'BZh',  # BZIP2
        ]
        
        return any(content.startswith(sig) for sig in archive_signatures)
    
    async def _validate_executable_file(self, content: bytes) -> bool:
        """Validate executable file (should be blocked)"""
        # Check for executable signatures
        exe_signatures = [
            b'MZ',  # Windows PE
            b'\x7fELF',  # Linux ELF
            b'\xfe\xed\xfa\xce',  # macOS Mach-O
        ]
        
        return any(content.startswith(sig) for sig in exe_signatures)


# Example configuration
DEFAULT_VALIDATION_CONFIG = {
    'max_payload_size': 10 * 1024 * 1024,  # 10MB
    'max_header_size': 8192,  # 8KB
    'max_url_length': 2048,
    'enable_sanitization': True,
    'strict_mode': False,
    'log_all_requests': False,
    'alert_on_threats': True
}