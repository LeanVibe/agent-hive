# Quality Gates Framework

Foundation Epic Phase 1: Security and compliance enforcement framework for automated quality validation and deployment readiness checks.

## Overview

The Quality Gates Framework provides automated validation of code quality, security, and deployment readiness with configurable enforcement levels and comprehensive security analysis.

## Features

### Core Quality Gates
- **PR Size Limit**: Enforces maximum pull request size (default: 1000 lines)
- **Test Coverage**: Validates minimum test coverage (default: 85%)
- **Security Scan**: Ensures no critical security vulnerabilities (default: 0 critical issues)
- **Code Quality**: Validates code quality score (default: 8.0/10)
- **Performance Check**: Validates performance metrics (default: 70% baseline)

### Security Framework
- **Security Levels**: HIGH, MEDIUM, LOW risk classification
- **Enforcement Levels**: STRICT, WARNING, PERMISSIVE modes
- **Security Implications**: Detailed analysis of security risks for each failure
- **Security Score**: Weighted scoring based on security risk levels

### Deployment Readiness
- **Automated Blocking**: Prevents deployment when quality gates fail
- **Compliance Reporting**: Comprehensive reports with security analysis
- **Configuration**: JSON-based configuration with environment-specific settings

## Usage

### Basic Validation
```python
from quality_gates_framework import validate_deployment_readiness

metrics = {
    "pr_size": 850,
    "test_coverage": 88.5,
    "security_critical_issues": 0,
    "code_quality_score": 8.2,
    "performance_score": 75.0
}

report = validate_deployment_readiness(metrics)
print(f"Deployment Ready: {report['deployment_ready']}")
print(f"Security Score: {report['security_summary']['security_score']}")
```

### Security Compliance Check
```python
from quality_gates_framework import check_security_compliance

security_summary = check_security_compliance(metrics)
if security_summary['deployment_blocked']:
    print("Deployment blocked due to security issues:")
    for issue in security_summary['security_issues']:
        print(f"- {issue}")
```

### Configuration
Quality gates can be configured via `.quality-gates.json`:

```json
{
  "quality_gates": {
    "max_pr_size": 1000,
    "min_coverage": 85,
    "required_tests": true,
    "required_security_review": true,
    "required_performance_check": true
  },
  "enforcement_level": "strict"
}
```

## Security Framework Details

### Security Levels
- **HIGH**: Critical security requirements (test coverage, security scans)
- **MEDIUM**: Important security practices (PR size, code quality)
- **LOW**: Performance and monitoring (performance checks)

### Enforcement Levels
- **STRICT**: All failures block deployment
- **WARNING**: Only HIGH security level failures block deployment
- **PERMISSIVE**: No automatic blocking (warnings only)

### Security Implications
Each quality gate failure includes specific security implications:

- **Large PRs**: Harder to review, increased vulnerability risk
- **Low Test Coverage**: Untested code paths may contain vulnerabilities
- **Security Issues**: Direct security vulnerabilities detected
- **Poor Code Quality**: Maintainability affects security updates
- **Performance Issues**: May indicate security problems or attack vectors

## Testing

Run the comprehensive test suite:
```bash
python -m pytest test_quality_gates.py -v
```

Test coverage:
```bash
python -m pytest test_quality_gates.py --cov=quality_gates_framework --cov-report=html
```

## API Reference

### QualityGatesFramework Class
Main framework class for quality gate validation.

#### Methods
- `validate_pr_size(line_count: int) -> ValidationResult`
- `validate_test_coverage(coverage_percent: float) -> ValidationResult`
- `validate_security_scan(critical_issues: int) -> ValidationResult`
- `validate_code_quality(quality_score: float) -> ValidationResult`
- `validate_performance(performance_score: float) -> ValidationResult`
- `validate_all_gates(metrics: Dict[str, Any]) -> Dict[str, ValidationResult]`
- `should_block_deployment(validation_results: Dict[str, ValidationResult]) -> bool`
- `generate_compliance_report(validation_results: Dict[str, ValidationResult]) -> Dict[str, Any]`

### ValidationResult Class
Represents the result of a quality gate validation.

#### Properties
- `gate_name: str` - Name of the quality gate
- `passed: bool` - Whether validation passed
- `value: float` - Actual measured value
- `threshold: float` - Required threshold value
- `message: str` - Human-readable validation message
- `security_implications: List[str]` - Security risks if validation failed

### API Functions
- `validate_deployment_readiness(metrics: Dict[str, Any]) -> Dict[str, Any]`
- `check_security_compliance(metrics: Dict[str, Any]) -> Dict[str, Any]`

## Integration

### CI/CD Pipeline Integration
```bash
# Example GitHub Actions integration
python quality_gates_framework.py --metrics-file metrics.json --output compliance-report.json
if [ $? -eq 0 ]; then
  echo "Quality gates passed - proceeding with deployment"
else
  echo "Quality gates failed - blocking deployment"
  exit 1
fi
```

### Pre-commit Hooks
```bash
# Add to .pre-commit-config.yaml
- repo: local
  hooks:
    - id: quality-gates
      name: Quality Gates Validation
      entry: python quality_gates_framework.py
      language: system
      pass_filenames: false
```

## Examples

### Example 1: All Gates Pass
```python
metrics = {
    "pr_size": 750,
    "test_coverage": 92.0,
    "security_critical_issues": 0,
    "code_quality_score": 8.8,
    "performance_score": 82.0
}
# Result: deployment_ready = True, security_score = 100.0
```

### Example 2: Security Issues Block Deployment
```python
metrics = {
    "pr_size": 500,
    "test_coverage": 75.0,  # Below 85% threshold
    "security_critical_issues": 2,  # Critical vulnerabilities
    "code_quality_score": 8.5,
    "performance_score": 80.0
}
# Result: deployment_ready = False, high security risk
```

### Example 3: Warning Level Issues
```python
metrics = {
    "pr_size": 800,
    "test_coverage": 88.0,
    "security_critical_issues": 0,
    "code_quality_score": 7.5,  # Below 8.0 but warning level
    "performance_score": 65.0   # Below 70% but warning level
}
# Result: deployment_ready = True (no HIGH security failures)
```

## Contributing

1. Add new quality gates by extending the `QualityGatesFramework` class
2. Include comprehensive security implication analysis
3. Add corresponding test cases in `test_quality_gates.py`
4. Update documentation and examples
5. Ensure proper security level classification

## License

Foundation Epic Phase 1 - Internal LeanVibe implementation.