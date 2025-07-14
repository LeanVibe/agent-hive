# LeanVibe System Development Plan

## Overview
This document outlines the development plan for the LeanVibe AI orchestration system, based on comprehensive analysis and Gemini CLI feedback. The plan follows Extreme Programming principles with continuous review and iteration.

## Critical Discovery
The project has a substantial existing codebase that was initially missed. Gemini CLI analysis revealed:
- Core orchestrator framework with async execution
- State management with SQLite + Git integration
- Complete directory structure with personas, commands, hooks
- Git worktree architecture already configured
- Agent configuration with specific capabilities

## Current State Analysis

### What Already Exists ✅
1. **Orchestrator Framework**: Async main loop with confidence-based decision making
2. **State Management**: SQLite database with Git checkpoint integration
3. **Agent Configuration**: YAML-based personas for backend, frontend, iOS, infra
4. **Hook System**: Pre-commit hooks, test enforcement, quality gates
5. **Monitoring Infrastructure**: Health checks, smart context management
6. **Dashboard Components**: HTML dashboard and unified views

### Critical Issues Identified ⚠️
1. **File Name Typos**: `task_disctributor.py`, `swuft_quality,py`, `dashboad.html`
2. **Missing Dependencies**: No `requirements.txt` or `pyproject.toml`
3. **No Documentation**: Missing README.md and setup instructions
4. **Incomplete Implementation**: Many classes referenced but not implemented
5. **No Tests**: Testing infrastructure missing despite test hooks

## Development Phases

### Phase 0: Foundation Audit & Fix (Week 1) 🔧 ✅ COMPLETED
**Priority: Critical**

#### File System Fixes
- [x] Rename `task_disctributor.py` → `task_distributor.py`
- [x] Fix `swuft_quality,py` → `swift_quality.py`
- [x] Fix `dashboad.html` → `dashboard.html`
- [x] Remove duplicate files and consolidate

#### Dependencies & Environment
- [x] Create `pyproject.toml` with uv dependency management
- [x] Set up virtual environment with uv
- [x] Test installation process
- [x] Create comprehensive `.gitignore` file

#### Missing Class Implementation
- [x] Implement `IntelligentStateManager` (skeletal)
- [x] Implement `SmartContextManager` (skeletal)
- [x] Implement `ConfidenceOptimizer` (skeletal)
- [x] Implement `UnifiedDashboard` (skeletal)
- [x] Implement `SmartXPEnforcer` (skeletal)

#### Documentation
- [x] Create comprehensive `README.md`
- [x] Add MIT license
- [x] Set up GitHub repository under LeanVibe org
- [x] Create basic testing framework

#### Success Criteria ✅
- [x] All file naming issues resolved
- [x] Project installs via `uv sync --dev`
- [x] orchestrator.py imports without errors
- [x] Basic documentation in place
- [x] All import statements resolve correctly
- [x] Tests pass successfully 
### Phase 1: Core System Completion (3-4 Weeks) 🚀 
**Priority: High - IN PROGRESS**
**Updated Timeline**: Based on Gemini review, extended to 3-4 weeks for quality implementation

#### Gemini Review Key Recommendations ⭐
1. **Vertical Slice Approach**: Implement one agent type (ClaudeAgent) fully before adding complexity
2. **External Dependency Resilience**: Add health checks, circuit breakers, and version pinning for CLIs
3. **State Management Performance**: Use hybrid approach (fast checkpoints + Git milestones)
4. **BaseAgent Enhancement**: Add `async def shutdown()` method for graceful cleanup
5. **Mock CLI Testing**: Create mock scripts for reliable, fast integration testing
6. **Configuration Management**: Add `config.yaml` for external settings
7. **Structured Logging**: Replace print statements with proper logging infrastructure

#### Revised Implementation Strategy
- **Week 1**: BaseAgent interface + Task Queue + Mock CLI setup
- **Week 2**: ClaudeAgent integration (focus exclusively on this)
- **Week 3**: Checkpoint/Rollback system + Testing infrastructure
- **Week 4**: GeminiAgent + Multi-agent coordination

#### Orchestrator Implementation
- [ ] Complete missing async methods in orchestrator
  - [ ] Implement `get_next_priority()` with actual task queue
  - [ ] Add proper `execute_autonomously()` with Claude Code CLI integration
  - [ ] Create `request_human_guidance()` with notification system
  - [ ] Implement `plan_with_gemini()` for task planning
  - [ ] Add `smart_distribute()` for task distribution
  - [ ] Create `execute_on_agent()` for agent execution
  - [ ] Implement `monitor_execution()` for real-time monitoring

#### Agent Interface Abstraction (Gemini's Key Recommendation)
- [ ] Create `BaseAgent` abstract class
  - [ ] Define `execute_task(task: Task) -> Result` interface
  - [ ] Define `get_status() -> AgentStatus` interface
  - [ ] Add `get_capabilities()` method
  - [ ] Create `health_check()` method
- [ ] Implement `ClaudeAgent` for Claude Code CLI
  - [ ] Subprocess management for Claude Code CLI
  - [ ] Task serialization/deserialization
  - [ ] Output parsing and error handling
  - [ ] Context management and overflow handling
- [ ] Implement `GeminiAgent` for Gemini CLI
  - [ ] Gemini CLI integration for reviews
  - [ ] Review request formatting
  - [ ] Response parsing and feedback integration
- [ ] Create agent factory pattern
  - [ ] Agent registry system
  - [ ] Configuration-based agent creation
  - [ ] Agent lifecycle management

#### State Management Completion
- [ ] Implement checkpoint/rollback system
  - [ ] Automatic checkpoint triggers
  - [ ] Git tag-based checkpoints
  - [ ] State restoration mechanisms
  - [ ] Rollback on failure scenarios
- [ ] Add performance metrics tracking
  - [ ] Task execution time tracking
  - [ ] Success/failure rate monitoring
  - [ ] Agent performance analytics
  - [ ] Confidence score evolution
- [ ] Create state synchronization
  - [ ] Multi-agent state consistency
  - [ ] Conflict resolution algorithms
  - [ ] State merge strategies
- [ ] Add data validation and integrity checks
  - [ ] Task validation schemas
  - [ ] State consistency checks
  - [ ] Error detection and correction

#### Enhanced Testing Infrastructure
- [ ] Unit tests for all components
  - [ ] Test each agent interface implementation
  - [ ] Test orchestrator methods independently
  - [ ] Test state management operations
  - [ ] Test confidence learning algorithms
- [ ] Integration tests for agent communication
  - [ ] Test Claude Code CLI integration
  - [ ] Test Gemini CLI integration
  - [ ] Test multi-agent coordination
  - [ ] Test error handling scenarios
- [ ] Performance benchmarks
  - [ ] Task execution time benchmarks
  - [ ] Memory usage monitoring
  - [ ] Context efficiency measurements
  - [ ] Scalability testing

#### Success Criteria ✅ WEEK 2 COMPLETED
- [x] All orchestrator methods implemented and functional
- [x] Claude Code CLI integration working (with mock CLI)
- [x] Agent interface abstraction completed (BaseAgent)
- [x] ClaudeAgent fully implemented with subprocess management
- [x] Circuit breaker and retry logic implemented
- [x] Structured logging with correlation tracking
- [x] Performance metrics are tracked and reported
- [x] System can execute simple tasks autonomously

#### Week 2 Gemini Review Results ⭐
**Strengths:**
- ✅ Excellent architecture with clean separation of concerns
- ✅ Robust error handling with circuit breaker pattern
- ✅ Successful vertical slice implementation
- ✅ Superb structured logging with correlation tracking
- ✅ Proper configuration management

**Critical Areas for Week 3:**
- 🔧 Create formal pytest test suite
- 🔧 Remove/refactor legacy components (task_distributor, old state_manager)
- 🔧 Clean up orchestrator duplicate methods
- 🔧 Implement checkpoint/rollback system

### Phase 1 Week 3: Quality Foundation & State Management 🧪
**Priority: High - Based on Gemini Review Feedback**

#### Critical Fixes (Gemini Priority 1)
- [ ] **Formal Test Suite Creation** (Updated based on Gemini feedback)
  - [ ] Set up pytest framework and basic structure
  - [ ] **Priority: Unit tests for core independent components**
    - [ ] CLIManager circuit breaker and retry logic
    - [ ] TaskQueue priority ordering and dependencies  
    - [ ] CircuitBreaker state transitions and timing
    - [ ] ConfigLoader environment variable overrides
  - [ ] **Pragmatic Integration Tests** (start with key happy paths)
    - [ ] Basic orchestrator workflow with mock agent
    - [ ] Task assignment and completion flow
    - [ ] Agent health check integration
  - [ ] Target: >80% unit test coverage, selective integration tests
  
- [ ] **Legacy Code Cleanup** (Gemini: After unit tests for safety)
  - [ ] **FIRST**: Create unit tests for components dependent on legacy code
  - [ ] Remove/refactor old task_distributor.py 
  - [ ] Update/remove legacy state_manager.py
  - [ ] Clean up duplicate orchestrator methods (Phase 0 placeholders)  
  - [ ] Reconcile hook_system.py role (dev tool vs runtime)
  - [ ] **NEW**: Create centralized config.yaml for all configurable parameters

#### State Management System (Phase 1 Core)
- [ ] **Checkpoint/Rollback Implementation** (Gemini: Define milestones clearly)
  - [ ] **Step 1**: Implement JSON checkpoint creation
  - [ ] **Step 2**: Implement JSON checkpoint restoration  
  - [ ] **Step 3**: Implement Git milestone creation (define: successful complex tasks)
  - [ ] **Step 4**: Implement Git milestone restoration
  - [ ] **Step 5**: Implement automatic checkpoint triggers
  - [ ] **NEW**: Add state validation mechanism for checkpoint integrity
  
- [ ] **Enhanced Performance Monitoring**
  - [ ] Comprehensive metrics collection
  - [ ] Performance baseline establishment
  - [ ] Resource usage tracking
  - [ ] Bottleneck identification
  - [ ] Performance regression detection

#### Testing Infrastructure Enhancement
- [ ] **Comprehensive Test Coverage**
  - [ ] Unit tests for all core components
  - [ ] Integration tests for end-to-end workflows
  - [ ] Mock CLI scenario testing
  - [ ] Error handling and recovery tests
  - [ ] Performance and load testing
  
- [ ] **CI/CD Pipeline Preparation**
  - [ ] Automated test execution
  - [ ] Code quality gates
  - [ ] Performance benchmarking
  - [ ] Test reporting and metrics

### Phase 3: Production Features (Week 4) 🔥
**Priority: Medium**

#### Dashboard Enhancement
- [ ] Real-time monitoring interface
- [ ] Human intervention queue
- [ ] Performance analytics dashboard
- [ ] Agent health status display

#### Robustness Features
- [ ] Graceful error recovery
- [ ] Agent health monitoring
- [ ] Automatic system healing
- [ ] Circuit breaker patterns

## Key Recommendations from Gemini Integration

### 1. Start with Code Audit (Critical)
Before implementing new features, thoroughly audit and fix existing code:
- Fix file naming issues
- Resolve import dependencies
- Complete partial implementations

### 2. Abstract Agent Interface (Architecture)
Create a generic agent interface to make integration seamless:
```python
class BaseAgent:
    async def execute_task(self, task: Task) -> Result:
        pass
    
    async def get_status(self) -> AgentStatus:
        pass

class ClaudeAgent(BaseAgent):
    # Implementation for Claude Code CLI

class GeminiAgent(BaseAgent):
    # Implementation for Gemini CLI
```

### 3. Robust Communication (Scalability)
Move away from file-based communication to prevent race conditions:
- Use message queues (ZeroMQ or Redis)
- Implement proper task acknowledgment
- Add retry mechanisms

### 4. Error Handling Strategy (Reliability)
Implement comprehensive error handling:
- Automatic retry policies
- Circuit breaker patterns
- Graceful degradation

## Development Workflow (XP-Inspired)

### Phase Planning Process
1. **Pre-Phase Review**: Review phase plan with Gemini CLI
2. **Implementation**: Execute phase with TDD approach
3. **Post-Phase Review**: Get Gemini review of implementation
4. **Iteration**: Incorporate feedback and refine

### Continuous Integration
- All changes committed to feature branches
- Automated testing on each commit
- Code review by Gemini CLI before merge
- Performance benchmarking on key changes

### Quality Gates
- All tests must pass
- Code coverage > 80%
- Performance benchmarks maintained
- Documentation updated

## Success Metrics (Adjusted for Reality)

Based on existing codebase foundation:
- **85% autonomy**: Achievable with proper confidence learning
- **<5% bug rate**: Requires robust testing infrastructure
- **<20% human intervention**: Needs excellent error recovery
- **5-10 features/week**: Realistic with proper agent coordination

## Risk Assessment

### High Risk
- **Integration Complexity**: Claude Code CLI subprocess management
- **State Synchronization**: SQLite + Git hybrid consistency
- **Performance**: File-based communication bottlenecks

### Medium Risk
- **Learning System**: Confidence threshold optimization complexity
- **Error Recovery**: Comprehensive error handling scenarios
- **Scalability**: Multi-agent coordination at scale

### Low Risk
- **Documentation**: Straightforward but time-consuming
- **Testing**: Standard approaches apply
- **Dashboard**: Well-understood web technologies

## Next Immediate Steps

1. **Run comprehensive code audit** on existing Python files
2. **Create requirements.txt** and test installation
3. **Fix critical file naming issues**
4. **Write comprehensive README.md**
5. **Implement missing orchestrator methods**

### Week 3 Gemini Review Results ⭐ (Latest)
**Strengths:**
- ✅ Solid and comprehensive plan incorporating previous feedback effectively
- ✅ Correct priority on critical fixes (test suite + legacy cleanup)
- ✅ Sound hybrid state management architecture design
- ✅ Well-ordered priorities focusing on quality before features

**Specific Recommendations Incorporated:**
1. **Testing Strategy**: Prioritize unit tests for independent components, start with happy-path integration tests
2. **State Management**: Define Git milestones as "successful complex tasks", add state validation mechanism
3. **Risk Mitigation**: Create unit tests before legacy cleanup, centralize configuration management
4. **Task Breakdown**: Split checkpoint implementation into 5 verifiable steps

**Implementation Approach:**
- Interleave tasks to maintain momentum
- Create small, verifiable steps for all major components
- Safety-first approach: test before cleanup

## Notes
- The foundation is much stronger than initially thought
- Significant cleanup and completion work needed before new features
- Gemini CLI integration provides excellent review capabilities
- XP workflow ensures continuous quality and feedback
- Week 3 plan refined based on detailed Gemini architectural review