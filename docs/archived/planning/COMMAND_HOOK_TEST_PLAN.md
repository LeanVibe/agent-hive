# LeanVibe Agent Hive - Command and Hook Test Plan

**Date**: 2025-07-14  
**Analysis Type**: Comprehensive Test Strategy for Commands and Hooks  
**Status**: Complete - Test Requirements Defined  
**Target Coverage**: 95%+ for all custom commands and hooks

## 🎯 Executive Summary

This document defines a comprehensive testing strategy for LeanVibe Agent Hive's custom command system and hook infrastructure. Since these systems are currently **not implemented**, this plan serves as both a **test-driven development guide** and **validation framework** for future implementation.

### Current Test Status
- **Custom Commands**: 0% coverage (not implemented)
- **Hook System**: 0% coverage (not functional)  
- **CLI Integration**: 0% coverage (no CLI exists)
- **End-to-End Workflows**: 10% coverage (basic unit tests only)

### Target Test Architecture
```
tests/
├── commands/              # Command-specific tests (NEW)
│   ├── test_orchestrate.py
│   ├── test_spawn.py  
│   ├── test_monitor.py
│   └── test_command_base.py
├── hooks/                # Hook system tests (NEW)
│   ├── test_pre_commit.py
│   ├── test_quality_gate.py
│   └── test_hook_integration.py
├── cli/                  # CLI interface tests (NEW)
│   ├── test_cli_parser.py
│   ├── test_cli_integration.py
│   └── test_cli_errors.py
└── workflows/            # End-to-end workflow tests (EXPAND)
    ├── test_full_orchestration.py
    └── test_parallel_execution.py
```

## 🔧 Custom Command Test Plans

### 1. `/orchestrate` Command Tests

#### **File**: `tests/commands/test_orchestrate.py`

#### Test Categories

##### **Unit Tests** - `test_orchestrate_unit.py`
```python
class TestOrchestrateCommand:
    """Test orchestrate command parsing and validation"""
    
    @pytest.mark.unit
    def test_orchestrate_basic_workflow():
        """Test basic workflow orchestration"""
        # Test: /orchestrate --workflow "feature-dev" --validate
        
    @pytest.mark.unit  
    def test_orchestrate_parameter_validation():
        """Test parameter validation and error handling"""
        # Test: Invalid workflow names, missing parameters
        
    @pytest.mark.unit
    def test_orchestrate_complexity_estimation():
        """Test adaptive depth selection (simple vs complex)"""
        # Test: Complexity analysis for depth selection
        
    @pytest.mark.unit
    def test_orchestrate_prompt_compression():
        """Test prompt compression for >10k tokens"""
        # Test: Token counting and compression logic
```

##### **Integration Tests** - `test_orchestrate_integration.py`
```python
class TestOrchestrateIntegration:
    """Test orchestrate command with real components"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_orchestrate_agent_distribution():
        """Test distribution to agents via capabilities"""
        # Test: Agent capability matching and task distribution
        
    @pytest.mark.integration
    async def test_orchestrate_progress_monitoring():
        """Test progress monitoring with auto-checkpoints"""
        # Test: Progress tracking and checkpoint creation
        
    @pytest.mark.integration  
    async def test_orchestrate_gemini_validation():
        """Test output validation via Gemini CLI"""
        # Test: Gemini integration for result validation
```

##### **Performance Tests** - `test_orchestrate_performance.py`
```python
class TestOrchestratePerformance:
    """Test orchestrate command performance characteristics"""
    
    @pytest.mark.performance
    def test_orchestrate_response_time():
        """Test command response time under load"""
        # Target: <2s for simple workflows, <10s for complex
        
    @pytest.mark.performance
    def test_orchestrate_memory_usage():
        """Test memory consumption during orchestration"""
        # Target: <500MB peak memory usage
```

### 2. `/spawn` Command Tests

#### **File**: `tests/commands/test_spawn.py`

##### **Unit Tests**
```python
class TestSpawnCommand:
    """Test spawn command functionality"""
    
    @pytest.mark.unit
    def test_spawn_worktree_creation():
        """Test temporary worktree creation"""
        # Test: Git worktree creation and cleanup
        
    @pytest.mark.unit
    def test_spawn_persona_loading():
        """Test sub-persona loading (e.g., Debugger)"""
        # Test: Persona file loading and validation
        
    @pytest.mark.unit
    def test_spawn_task_compression():
        """Test task description compression"""
        # Test: Compression logic for ultrathink tasks
```

##### **Integration Tests**
```python
class TestSpawnIntegration:
    """Test spawn command integration"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_spawn_parallel_execution():
        """Test parallel task execution"""
        # Test: Multiple spawned agents working simultaneously
        
    @pytest.mark.integration
    async def test_spawn_result_merging():
        """Test result merging back to main process"""
        # Test: Result aggregation and conflict resolution
```

### 3. `/monitor` Command Tests

#### **File**: `tests/commands/test_monitor.py`

##### **Unit Tests**
```python
class TestMonitorCommand:
    """Test monitor command functionality"""
    
    @pytest.mark.unit
    def test_monitor_state_db_query():
        """Test state database querying"""
        # Test: SQLite queries for confidence and tasks
        
    @pytest.mark.unit
    def test_monitor_git_log_analysis():
        """Test Git log analysis for recent commits"""
        # Test: Git history parsing and analysis
        
    @pytest.mark.unit
    def test_monitor_agent_health_check():
        """Test agent health assessment"""
        # Test: Context usage and stuck detection algorithms
```

##### **Integration Tests**
```python
class TestMonitorIntegration:
    """Test monitor command with live system"""
    
    @pytest.mark.integration
    def test_monitor_real_time_metrics():
        """Test real-time metrics collection"""
        # Test: Live metric gathering and aggregation
        
    @pytest.mark.integration
    def test_monitor_auto_redistribution():
        """Test automatic task redistribution"""
        # Test: Unhealthy agent detection and task rebalancing
```

## 🪝 Hook System Test Plans

### 1. Pre-Commit Hook Tests

#### **File**: `tests/hooks/test_pre_commit.py`

##### **Unit Tests**
```python
class TestPreCommitHook:
    """Test pre-commit hook functionality"""
    
    @pytest.mark.unit
    def test_pre_commit_test_enforcement():
        """Test ensure_tests.py execution"""
        # Test: Test requirement validation before commit
        
    @pytest.mark.unit
    def test_pre_commit_gemini_review():
        """Test Gemini review integration"""
        # Test: Automated code review via Gemini CLI
        
    @pytest.mark.unit
    def test_pre_commit_quality_gate():
        """Test quality gate validation"""
        # Test: Quality standards enforcement
```

##### **Integration Tests**
```python
class TestPreCommitIntegration:
    """Test pre-commit hook with Git"""
    
    @pytest.mark.integration
    def test_pre_commit_git_integration():
        """Test Git hook installation and triggering"""
        # Test: Actual Git commit process with hook
        
    @pytest.mark.integration
    def test_pre_commit_failure_blocking():
        """Test commit blocking on failures"""
        # Test: Failed tests/quality gates block commits
```

### 2. Quality Gate Tests

#### **File**: `tests/hooks/test_quality_gate.py`

##### **Implementation Tests**
```python
class TestQualityGate:
    """Test quality gate enforcement"""
    
    @pytest.mark.unit
    def test_quality_gate_metrics():
        """Test quality metric calculation"""
        # Test: Code coverage, complexity, style metrics
        
    @pytest.mark.unit
    def test_quality_gate_thresholds():
        """Test quality threshold enforcement"""
        # Test: Pass/fail decisions based on thresholds
        
    @pytest.mark.integration
    def test_quality_gate_blocking():
        """Test quality gate blocking functionality"""
        # Test: Process blocking when quality fails
```

### 3. Hook Integration Tests

#### **File**: `tests/hooks/test_hook_integration.py`

##### **System Tests**
```python
class TestHookSystem:
    """Test complete hook system integration"""
    
    @pytest.mark.integration
    def test_hook_installation():
        """Test hook installation process"""
        # Test: setup.sh script hook installation
        
    @pytest.mark.integration
    def test_hook_triggering():
        """Test hook triggering mechanisms"""
        # Test: Git events triggering appropriate hooks
        
    @pytest.mark.integration
    def test_hook_failure_recovery():
        """Test hook failure recovery"""
        # Test: Graceful handling of hook failures
```

## 🖥️ CLI Interface Test Plans

### 1. CLI Parser Tests

#### **File**: `tests/cli/test_cli_parser.py`

##### **Parser Tests**
```python
class TestCLIParser:
    """Test command-line interface parsing"""
    
    @pytest.mark.unit
    def test_cli_command_parsing():
        """Test parsing of all supported commands"""
        # Test: /orchestrate, /spawn, /monitor parsing
        
    @pytest.mark.unit
    def test_cli_parameter_validation():
        """Test parameter validation and type checking"""
        # Test: Required/optional parameters, type validation
        
    @pytest.mark.unit
    def test_cli_error_handling():
        """Test error handling and user feedback"""
        # Test: Clear error messages for invalid input
```

### 2. CLI Integration Tests

#### **File**: `tests/cli/test_cli_integration.py`

##### **End-to-End Tests**
```python
class TestCLIIntegration:
    """Test CLI with actual command execution"""
    
    @pytest.mark.integration
    def test_cli_command_execution():
        """Test actual command execution via CLI"""
        # Test: Commands execute correctly from CLI
        
    @pytest.mark.integration  
    def test_cli_output_formatting():
        """Test CLI output formatting and display"""
        # Test: Proper table formatting, color coding
        
    @pytest.mark.integration
    def test_cli_interactive_mode():
        """Test interactive CLI features"""
        # Test: Interactive prompts and user input
```

## 🔄 Workflow Integration Test Plans

### 1. Full Orchestration Tests

#### **File**: `tests/workflows/test_full_orchestration.py`

##### **End-to-End Workflow Tests**
```python
class TestFullOrchestration:
    """Test complete orchestration workflows"""
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_feature_development_workflow():
        """Test complete feature development orchestration"""
        # Test: Full /orchestrate -> /spawn -> /monitor cycle
        
    @pytest.mark.integration
    async def test_bug_fix_workflow():
        """Test bug fix orchestration workflow"""
        # Test: Debug workflow with specialized agents
        
    @pytest.mark.performance
    async def test_workflow_performance():
        """Test workflow performance characteristics"""
        # Test: End-to-end timing and resource usage
```

## 📊 Test Infrastructure Requirements

### Test Environment Setup

#### **Mock Services Required**
```python
# tests/conftest.py additions needed:

@pytest.fixture
def mock_claude_cli():
    """Mock Claude CLI for testing"""
    # Mock CLI responses and behavior
    
@pytest.fixture  
def mock_gemini_cli():
    """Mock Gemini CLI for testing"""
    # Mock Gemini review responses
    
@pytest.fixture
def mock_git_environment():
    """Mock Git environment for hook testing"""
    # Temporary Git repo for testing hooks
    
@pytest.fixture
def mock_state_db():
    """Mock state database for testing"""
    # In-memory SQLite for testing state operations
```

#### **Test Data Requirements**
```
tests/fixtures/
├── commands/
│   ├── orchestrate_workflows.json
│   ├── spawn_tasks.json
│   └── monitor_outputs.json
├── hooks/
│   ├── git_commits.json
│   └── quality_reports.json
└── workflows/
    ├── feature_scenarios.json
    └── bug_fix_scenarios.json
```

### Performance Test Targets

| Component | Target | Measurement |
|-----------|---------|-------------|
| `/orchestrate` | <2s simple, <10s complex | Response time |
| `/spawn` | <5s per agent | Spawn time |
| `/monitor` | <1s refresh | Data collection |
| CLI startup | <500ms | Import time |
| Hook execution | <2s total | Git hook time |

### Coverage Requirements

| Test Type | Target Coverage | Priority |
|-----------|----------------|----------|
| Command Unit Tests | 95% | Critical |
| Hook Unit Tests | 90% | Critical |
| CLI Integration | 85% | High |
| Workflow E2E | 75% | High |
| Performance Tests | 100% scenarios | Medium |

## 🚀 Implementation Strategy

### Phase 1: Foundation (Week 1)
1. **Create test structure** - Set up all test directories
2. **Mock infrastructure** - Implement CLI mocks and fixtures
3. **Basic unit tests** - Write tests for non-existent commands (TDD)

### Phase 2: Command Tests (Week 2)
1. **Command unit tests** - Complete all command test suites
2. **CLI parser tests** - Test command-line interface parsing
3. **Basic integration** - Simple command execution tests

### Phase 3: Integration (Week 3)
1. **Hook system tests** - Complete hook testing infrastructure
2. **Workflow tests** - End-to-end orchestration testing
3. **Performance tests** - Benchmarking and performance validation

### Phase 4: Validation (Week 4)
1. **Coverage analysis** - Ensure coverage targets met
2. **Performance validation** - Verify performance targets
3. **Documentation** - Complete test documentation

## ✅ Success Criteria

### Test Quality Gates
- [ ] 95%+ coverage for command implementations
- [ ] 90%+ coverage for hook system
- [ ] All performance targets met
- [ ] Zero test failures in CI/CD
- [ ] Complete mock infrastructure functional

### Functional Validation
- [ ] All documented commands testable
- [ ] All hooks validated before implementation
- [ ] CLI interface fully tested
- [ ] End-to-end workflows validated

### Automation Integration
- [ ] Tests run automatically on commit
- [ ] Performance regression detection
- [ ] Quality gate enforcement
- [ ] Automated test reporting

---

*This test plan provides comprehensive coverage for all command and hook functionality, enabling test-driven development of the currently missing features.*