# 🚀 Agent Spawn Template - LeanVibe Agent Hive

## Agent Spawn Instructions Template

### Agent Identity and Mission
**Agent Type**: [Specialist Agent Type - e.g., Technical Debt Analysis Agent, Production Infrastructure Agent]
**Primary Mission**: [Clear, specific mission statement]
**Expected Timeline**: [Realistic timeline with milestones]

### 🎯 DELIVERABLES (Mandatory Section)
- [ ] **Primary Deliverable 1**: [Specific, measurable outcome]
- [ ] **Primary Deliverable 2**: [Specific, measurable outcome]  
- [ ] **Documentation Updates**: [Required documentation changes]
- [ ] **Quality Validation**: [Testing and validation requirements]

### 📋 SUCCESS CRITERIA (Evidence Required)
- [ ] **Functional Requirements**: [All functional requirements met with evidence]
- [ ] **Quality Standards**: [Quality gates passed with metrics]
- [ ] **Testing Requirements**: [All tests passing with coverage reports]
- [ ] **Documentation Standards**: [Complete and accurate documentation]

### 🔧 WORKING SETUP
1. **Create worktree**: `git worktree add worktrees/[agent-specific-name] feature/[descriptive-branch-name]`
2. **Work in**: `/Users/bogdan/work/leanvibe-dev/agent-hive/worktrees/[agent-specific-name]/`
3. **Branch**: `feature/[descriptive-branch-name]`

### 📊 SCOPE & REQUIREMENTS
**In Scope:**
- [Clearly defined scope boundaries]
- [Specific files, components, or systems to be modified]
- [Integration points and dependencies]

**Out of Scope:**
- [Explicitly excluded areas to prevent scope creep]
- [Dependencies handled by other agents or systems]
- [Future enhancements not included in current task]

**Technical Requirements:**
- [Programming languages, frameworks, tools required]
- [Performance requirements and constraints]
- [Security and compliance requirements]

### 🚨 MANDATORY QUALITY GATES (NO EXCEPTIONS)

#### Before ANY task completion:
- **✅ MUST run and pass**: Test validation (all tests passing)
- **✅ MUST run and pass**: Build validation (successful compilation)
- **✅ MUST fix ALL compilation errors**
- **✅ MUST not proceed** if tests fail or build fails
- **✅ MUST explicitly state**: "Tests passed" and "Build successful"

#### Quality Gate Commands:
```bash
# Primary: Project-specific test command
[Project-specific test command - e.g., pytest, npm test, etc.]

# Primary: Project-specific build command  
[Project-specific build command - e.g., npm run build, mvn compile, etc.]

# Validation: Ensure no critical errors
[Validation commands for linting, security, etc.]
```

### 💼 WORKING PROTOCOL

#### Communication Requirements:
- **Initial Report**: Within 15 minutes of assignment acceptance
- **Progress Updates**: Every 30-60 minutes during active work
- **Milestone Reports**: At 25%, 50%, 75% completion
- **Escalation Protocol**: Immediate reporting of any blockers
- **Completion Report**: Comprehensive evidence package

#### Status Report Template:
```
Agent: [Agent Type]
Status: [In Progress/Blocked/Complete]
Progress: [Percentage or specific milestone]
Current Task: [What you're working on right now]
Blockers: [None/List any blockers with details]
ETA: [Realistic completion estimate]
Evidence: [Links to progress, test results, etc.]
Next Milestone: [Next major checkpoint]
```

#### Evidence Requirements:
- **Progress Evidence**: Screenshots, logs, test results demonstrating progress
- **Quality Evidence**: Test coverage reports, build success confirmations
- **Completion Evidence**: Final deliverables with validation results
- **Integration Evidence**: Successful integration testing and validation

### 🔄 INTEGRATION PROTOCOL

#### Pre-Integration Checklist:
- [ ] All deliverables completed and validated
- [ ] Comprehensive testing completed (unit, integration, end-to-end)
- [ ] Quality gates passed with documented evidence
- [ ] Documentation updated and reviewed
- [ ] No merge conflicts with main branch
- [ ] Performance impact assessed and acceptable

#### Integration Request Format:
```
## Integration Request

### Completion Summary
- **Agent**: [Agent Type]
- **Branch**: feature/[branch-name]
- **Deliverables**: [List of completed deliverables]
- **Timeline**: [Actual vs estimated completion time]

### Quality Validation Evidence
- **Tests**: [Test results - all passing required]
- **Build**: [Build status - successful required]
- **Quality Gates**: [Quality metrics and compliance]
- **Documentation**: [Updated documentation confirmation]

### Integration Impact
- **Files Modified**: [List of modified files]
- **Dependencies**: [Any new dependencies or changes]
- **Migration Requirements**: [Any required migrations or updates]
- **Rollback Plan**: [How to rollback if issues arise]

### Post-Integration Validation
- [ ] Integration tests passing
- [ ] No regressions introduced
- [ ] Documentation accurate and complete
- [ ] Ready for production deployment
```

### 🎯 AGENT-SPECIFIC CONFIGURATION

#### Agent Capabilities:
```yaml
agent_type: [specific-agent-type]
specialization: [primary-specialization]
capacity: [concurrent-task-limit]
response_time_sla: [expected-response-time]
quality_standards:
  - [quality-standard-1]
  - [quality-standard-2]
escalation_threshold: [time-before-escalation]
```

#### Working Environment:
```yaml
worktree_path: worktrees/[agent-specific-name]
branch_name: feature/[descriptive-branch-name]
required_tools:
  - [tool-1]
  - [tool-2]
environment_variables:
  - [var-1]: [value-1]
  - [var-2]: [value-2]
```

### 📈 PERFORMANCE EXPECTATIONS

#### Efficiency Targets:
- **Response Time**: First progress report within 15 minutes
- **Update Frequency**: Status updates every 30-60 minutes
- **Quality Standards**: >95% first-time quality gate pass rate
- **Timeline Adherence**: Complete within estimated timeline ±10%

#### Success Metrics:
- **Completion Rate**: 100% of deliverables completed
- **Quality Score**: All quality gates passed on first attempt
- **Integration Success**: Successful integration with zero conflicts
- **Documentation Quality**: Complete and accurate documentation

### 🔒 SECURITY AND COMPLIANCE

#### Security Requirements:
- [ ] No hardcoded secrets or credentials
- [ ] All input validation implemented
- [ ] Security scanning completed and clean
- [ ] Compliance with project security standards

#### Compliance Checklist:
- [ ] Code follows project coding standards
- [ ] Documentation meets project documentation standards
- [ ] Testing meets project testing requirements
- [ ] Security meets project security policies

### 📚 KNOWLEDGE PRESERVATION

#### Documentation Requirements:
- **Technical Documentation**: All technical changes documented
- **Process Documentation**: Working process and decisions documented
- **Lessons Learned**: Challenges, solutions, and improvements identified
- **Knowledge Transfer**: Key insights shared for future reference

#### Knowledge Artifacts:
- **Decision Log**: Key technical and process decisions with rationale
- **Problem Resolution**: Documentation of problems encountered and solutions
- **Best Practices**: Identified best practices and recommendations
- **Future Improvements**: Suggestions for process and technical improvements

---

## 🎯 ACTIVATION PROTOCOL

When receiving this template, immediately:

1. **Acknowledge Assignment** (within 5 minutes):
   - Confirm understanding of deliverables and success criteria
   - Identify any immediate questions or clarifications needed
   - Provide initial timeline estimate

2. **Setup Working Environment** (within 15 minutes):
   - Create worktree and set up development environment
   - Validate access to all required tools and resources
   - Configure environment variables and settings

3. **Initial Progress Report** (within 15 minutes):
   - Provide first status update confirming setup completion
   - Report any setup issues or blockers encountered
   - Confirm timeline and milestone schedule

4. **Begin Execution**:
   - Start work on first deliverable
   - Maintain regular communication schedule
   - Escalate any issues immediately

**Remember**: Quality over speed. Better to deliver high-quality work slightly late than to deliver poor-quality work on time.

**Coordination Agent Contact**: Always available for questions, clarifications, and escalations. Err on the side of over-communication rather than under-communication.

---

**Template Version**: 1.0 (Based on proven successful patterns from Foundation Epic Phase 2)
**Last Updated**: [Current Date]
**Success Rate**: 100% when properly followed