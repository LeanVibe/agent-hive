# 📋 Agent Requirements - Single Source of Truth

## 🚨 CRITICAL WORKFLOW DISCIPLINE REQUIREMENTS

### **PR Size Limits - NON-NEGOTIABLE**
- **Maximum PR size**: 500 lines (additions + deletions)
- **Violation consequences**: Immediate PR closure
- **Enforcement**: Automated pre-commit hooks + GitHub Actions
- **No exceptions**: Breaking changes must be incremental

### **Quality Gate Requirements**
- **Pre-commit validation**: Must pass all checks
- **Test coverage**: Minimum 80% for new code
- **Code review**: Required before merge
- **Documentation**: Update docs for new features

### **Agent Coordination Protocol**
- **Communication**: Use GitHub issues for coordination
- **Status updates**: Every 2 hours for active work
- **Escalation**: Tag @pm-agent for blockers
- **Compliance**: Acknowledge workflow discipline

## 🎯 AGENT-SPECIFIC REQUIREMENTS

### **Security Agent**
- **Current Status**: Under workflow discipline enforcement
- **Required Action**: Respond to Issue #92 before proceeding
- **PR Approach**: Break down auth/JWT work into <500 line PRs
- **Compliance**: Must acknowledge prevention-first approach

### **Frontend Agent**
- **Current Status**: Commands audit complete (64-script ecosystem)
- **Phase 2 Role**: Implement compound-effect improvements
- **Delivery**: Incremental implementation with quality gates
- **Focus**: UI/UX optimization in manageable chunks

### **Performance Agent**
- **Current Status**: Ready for method refactoring
- **Phase 2 Role**: ML-driven performance prediction
- **Delivery**: <500 line incremental PRs with automated testing
- **Focus**: Performance optimization with continuous validation

### **Integration Agent**
- **Current Status**: Foundation Epic Phase 1 complete
- **Phase 2 Role**: External service integration
- **Delivery**: API integrations in small, testable increments
- **Focus**: GitHub Actions, Slack, webhooks

### **Infrastructure Agent**
- **Current Status**: Monitoring and deployment ready
- **Phase 2 Role**: Container orchestration and scaling
- **Delivery**: Infrastructure as code in small modules
- **Focus**: Kubernetes, Docker, observability

## 🔧 TECHNICAL STANDARDS

### **Code Quality Requirements**
- **Linting**: Must pass project linting rules
- **Type checking**: Type annotations required
- **Security**: No hardcoded secrets or credentials
- **Performance**: No regression in critical paths

### **Documentation Requirements**
- **API changes**: Update API documentation
- **New features**: Include usage examples
- **Breaking changes**: Migration guide required
- **Architecture**: Update architecture diagrams

### **Testing Requirements**
- **Unit tests**: 80% coverage minimum
- **Integration tests**: Cover critical paths
- **Performance tests**: Benchmark critical operations
- **Security tests**: Validate security measures

## 🚨 PREVENTION SYSTEM COMPONENTS

### **Pre-commit Hooks**
- **PR size validation**: Automatic rejection >500 lines
- **Code quality**: Linting and type checking
- **Security scanning**: Detect secrets and vulnerabilities
- **Test execution**: Run relevant tests before commit

### **GitHub Actions**
- **PR validation**: Automated size and quality checks
- **Continuous integration**: Build and test on all PRs
- **Security scanning**: Automated vulnerability detection
- **Deployment**: Automated deployment for approved PRs

### **Monitoring Systems**
- **PM agent health**: Automated health checks
- **Quality metrics**: Track compliance and violations
- **Performance monitoring**: System performance tracking
- **Alert systems**: Proactive issue detection

## 🎯 COMPLIANCE VERIFICATION

### **Daily Checklist**
- [ ] All PRs under 500 lines
- [ ] Pre-commit hooks operational
- [ ] GitHub Actions passing
- [ ] Agent communication active
- [ ] Quality gates enforced

### **Weekly Review**
- [ ] Prevention system effectiveness
- [ ] Agent compliance rates
- [ ] Quality metric trends
- [ ] System performance validation
- [ ] Process improvement opportunities

## 🚀 PHASE 2 COORDINATION

### **Prevention-First Approach**
- **Days 1-2**: Prevention system implementation
- **Validation**: All systems operational before feature work
- **Monitoring**: Continuous compliance tracking
- **Improvement**: Iterative prevention system enhancement

### **Feature Work Guidelines**
- **No new features**: Until prevention systems validated
- **Incremental delivery**: <500 line PRs only
- **Quality focus**: Prevention over speed
- **Collaboration**: Coordinate with PM agent

---

**🎯 MISSION**: Prevent workflow crises through proactive systems
**🚀 VISION**: Zero-violation workflow discipline maintained
**⚖️ AUTHORITY**: PM Agent technical delegation active

*This document is the single source of truth for all agent requirements.*
