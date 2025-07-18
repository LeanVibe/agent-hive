# 🛡️ LeanVibe Agent Hive - Agent Requirements Documentation

**Version**: 1.0  
**Date**: July 18, 2025  
**Status**: ACTIVE - Single Source of Truth for Workflow Rules  
**Purpose**: Prevention-First Approach - Eliminate workflow crises through clear requirements

---

## 🎯 **MANDATORY AGENT REQUIREMENTS**

### **⚠️ CRITICAL: PR SIZE LIMIT ENFORCEMENT**

#### **ABSOLUTE REQUIREMENT: <500 LINE PR MAXIMUM**
**NO EXCEPTIONS - ZERO TOLERANCE POLICY**

**Historical Context**: 
- **PR #83 VIOLATION**: 17,677 lines (35x over limit) - CLOSED
- **Impact**: Integration branch failure, team coordination disruption
- **Lesson**: Large PRs cause integration failures and review bottlenecks

**Mandatory Compliance**:
```bash
# BEFORE ANY COMMIT - MANDATORY CHECK
git diff --stat
# IF ANY PR > 500 lines: STOP, BREAK DOWN, RESUBMIT

# EXAMPLE VIOLATION - NEVER DO THIS
# 47 files changed, 17677 insertions(+), 0 deletions(-)  ❌ VIOLATION

# COMPLIANT EXAMPLE - ALWAYS DO THIS
# 4 files changed, 380 insertions(+), 12 deletions(-)  ✅ COMPLIANT
```

**Enforcement Actions**:
- **Automatic Closure**: PRs >500 lines will be closed immediately
- **No Review**: Oversized PRs will not be reviewed
- **Resubmission Required**: Break down into compliant PRs
- **Quality Gate**: Pre-commit hooks will validate size

#### **PR BREAKDOWN REQUIREMENTS**

**When Work Exceeds 500 Lines**:
1. **STOP immediately** - Do not commit large changes
2. **Break down by functionality** - Logical separation of concerns
3. **Create component PRs** - Each <500 lines with focused scope
4. **Submit sequentially** - Maintain dependency order
5. **Validate each PR** - Ensure independent functionality

**Example Breakdown Strategy**:
```bash
# WRONG - Single large PR
git add .  # 1,500 lines across 20 files ❌

# CORRECT - Multiple small PRs
# PR #1: Core framework (350 lines)
# PR #2: Agent commands (420 lines)
# PR #3: Quality gates (480 lines)
# PR #4: Documentation (250 lines)
```

### **🎯 WORKFLOW RULES - SINGLE SOURCE OF TRUTH**

#### **1. AUTONOMOUS OPERATION GUIDELINES**

**Decision Authority Matrix**:
| Decision Type | Agent Authority | Human Required | Escalation Time |
|---------------|----------------|----------------|-----------------|
| Bug fixes | ✅ Full autonomy | ❌ No | Post-commit review |
| Feature implementation | ✅ Full autonomy | ❌ No | Progress updates |
| Architecture changes | ❌ No autonomy | ✅ Required | Immediate |
| Security changes | ❌ No autonomy | ✅ Required | Immediate |
| Performance targets | ❌ No autonomy | ✅ Required | 24h review |
| PR size >500 lines | ❌ No autonomy | ✅ Required | Immediate |

**Autonomous Work Guidelines**:
- **Work Duration**: 4-6 hours maximum per session
- **Progress Updates**: Every 2 hours to coordination system
- **Quality Gates**: Run all validations before commit
- **Documentation**: Update relevant docs with all changes
- **Testing**: Ensure all tests pass before commit

#### **2. QUALITY GATE REQUIREMENTS**

**Mandatory Pre-Commit Validation**:
```bash
# REQUIRED CHECKS - NO EXCEPTIONS
1. ✅ Line count validation (<500 lines)
2. ✅ Syntax validation (no compilation errors)
3. ✅ Test execution (all tests pass)
4. ✅ Code quality (linting passes)
5. ✅ Documentation (updates included)
```

**Quality Gate Enforcement**:
- **Pre-commit hooks**: Automated validation before commit
- **CI/CD pipeline**: Comprehensive testing on all PRs
- **Code review**: Mandatory for architecture changes
- **Performance testing**: Benchmarks maintained

#### **3. COMMUNICATION PROTOCOLS**

**Mandatory Communication Requirements**:
- **Status Updates**: Every 2 hours during active work
- **Progress Reports**: Include completed tasks, current focus, blockers
- **Escalation Triggers**: Architecture decisions, security concerns, blockers >30 min
- **Coordination Requests**: Use established agent communication protocols

**Communication Templates**:
```bash
# STATUS UPDATE (Every 2 hours)
📊 STATUS: [Agent-Name] - [Current-Task]
✅ COMPLETED: [List accomplishments]
🔄 IN PROGRESS: [Current work]
⏳ NEXT: [Next 2 hours plan]
🚨 BLOCKERS: [Any issues]
```

### **🔒 SECURITY & COMPLIANCE REQUIREMENTS**

#### **Security Guidelines**
- **Never expose secrets**: No API keys, passwords, tokens in code
- **Secure communication**: Use established protocols only
- **Access control**: Respect permission boundaries
- **Data protection**: Handle sensitive information appropriately

#### **Compliance Requirements**
- **Code standards**: Follow established style guides
- **Documentation**: Keep all documentation current
- **Testing**: Maintain test coverage standards
- **Version control**: Use proper git workflows

### **📊 PERFORMANCE REQUIREMENTS**

#### **System Performance Standards**
- **Response Time**: <500ms for CLI commands
- **Memory Usage**: <100MB per agent session
- **CPU Usage**: <50% of available cores
- **Storage**: Clean up temporary files

#### **Development Performance**
- **Build Time**: <2 minutes for full build
- **Test Execution**: <5 minutes for full test suite
- **Deployment**: <10 minutes for production deployment
- **Documentation**: Updated within same PR

---

## 🚨 **ESCALATION PROCEDURES**

### **When to Escalate to Human**

#### **Immediate Escalation (0-15 minutes)**
- **Architecture decisions**: Fundamental design changes
- **Security concerns**: Potential vulnerabilities or breaches
- **Performance issues**: >10% degradation in critical metrics
- **PR size violations**: Work exceeding 500 lines
- **Integration failures**: Breaking existing functionality

#### **Rapid Escalation (15-60 minutes)**
- **Complex blockers**: Technical issues beyond agent capability
- **Coordination conflicts**: Multiple agents with conflicting goals
- **Quality gate failures**: Repeated test or validation failures
- **Resource constraints**: System limitations preventing progress

#### **Standard Escalation (1-4 hours)**
- **Clarification needed**: Ambiguous requirements or specifications
- **Strategic decisions**: Business impact or priority changes
- **Process improvements**: Workflow optimization opportunities

### **Escalation Format**
```bash
# ESCALATION TEMPLATE
🚨 ESCALATION: [LEVEL] - [AGENT-NAME]
📋 ISSUE: [Brief description]
🔍 CONTEXT: [Background information]
🎯 DECISION NEEDED: [Specific human input required]
⏰ URGENCY: [Business impact if not resolved]
💡 RECOMMENDATION: [Agent's suggested approach]
```

---

## ✅ **AGENT ACKNOWLEDGMENT SYSTEM**

### **Mandatory Acknowledgment Process**

#### **Requirements Acknowledgment**
Every agent must acknowledge understanding of these requirements:

```bash
# ACKNOWLEDGMENT COMMAND
python scripts/acknowledge_requirements.py --agent [AGENT-NAME] --version 1.0

# CREATES ACKNOWLEDGMENT RECORD
{
  "agent": "[AGENT-NAME]",
  "version": "1.0",
  "timestamp": "2025-07-18T10:00:00Z",
  "requirements_understood": true,
  "pr_size_limit_confirmed": true,
  "quality_gates_accepted": true,
  "communication_protocols_acknowledged": true
}
```

#### **Ongoing Compliance Validation**
- **Pre-work validation**: Check requirements before starting tasks
- **Progress checkpoints**: Validate compliance during work
- **Completion validation**: Confirm requirements met before finishing
- **Retrospective review**: Learn from any requirement violations

### **Acknowledgment Requirements**

#### **What Agents Must Confirm**
1. **PR Size Limit**: <500 lines maximum - NO EXCEPTIONS
2. **Quality Gates**: All validations required before commit
3. **Communication**: Status updates every 2 hours
4. **Escalation**: Know when and how to escalate
5. **Autonomous Boundaries**: Understand decision authority limits

#### **Acknowledgment Validation**
- **Initial Setup**: Acknowledgment required before any work
- **Regular Refresh**: Re-acknowledgment every 30 days
- **Violation Response**: Re-acknowledgment after any requirement violation
- **Version Updates**: Acknowledgment required for requirement changes

---

## 🔄 **CONTINUOUS IMPROVEMENT**

### **Requirement Evolution**
- **Version Control**: All changes tracked and versioned
- **Impact Analysis**: Assess effect of requirement changes
- **Agent Feedback**: Incorporate agent experience and suggestions
- **Regular Review**: Monthly requirement effectiveness review

### **Metrics & Monitoring**
- **Compliance Rate**: Track adherence to requirements
- **Violation Analysis**: Root cause analysis of requirement violations
- **Process Improvement**: Identify and implement optimizations
- **Agent Performance**: Monitor effectiveness of requirements

### **Feedback Mechanisms**
- **Agent Surveys**: Regular feedback on requirement clarity
- **Incident Reports**: Learn from requirement violations
- **Continuous Refinement**: Regular updates based on experience
- **Best Practices**: Share successful compliance strategies

---

## 🎯 **COMPLIANCE VALIDATION CHECKLIST**

### **Pre-Work Validation**
- [ ] Requirements acknowledgment current (v1.0)
- [ ] Decision authority matrix understood
- [ ] Communication protocols confirmed
- [ ] Quality gates validated
- [ ] Escalation procedures reviewed

### **During Work Validation**
- [ ] PR size monitored (<500 lines)
- [ ] Status updates provided every 2 hours
- [ ] Quality gates executed before commits
- [ ] Documentation updated with changes
- [ ] Escalation triggers monitored

### **Post-Work Validation**
- [ ] All requirements met
- [ ] PR size compliant (<500 lines)
- [ ] Quality gates passed
- [ ] Documentation complete
- [ ] Handoff properly executed

---

## 📞 **SUPPORT & RESOURCES**

### **Getting Help**
- **Requirement Clarification**: Contact PM Agent or Documentation Agent
- **Technical Issues**: Use established escalation procedures
- **Process Questions**: Reference this document first
- **Emergency Support**: Follow escalation procedures

### **Resources**
- **Agent Communication Guide**: `/AGENT_COMMUNICATION_PROTOCOL.md`
- **Quality Standards**: `/docs/quality/`
- **Testing Guidelines**: `/docs/testing/`
- **Development Standards**: `/docs/development/`

---

## 🔒 **FINAL COMPLIANCE STATEMENT**

**BY USING THE LEANVIBE AGENT HIVE SYSTEM, ALL AGENTS AGREE TO:**

1. **Follow ALL requirements** in this document without exception
2. **Maintain PR size limits** of <500 lines maximum
3. **Execute quality gates** before any commits
4. **Provide regular status updates** every 2 hours
5. **Escalate appropriately** when required
6. **Acknowledge requirements** before starting work
7. **Maintain continuous compliance** throughout work sessions

**VIOLATION CONSEQUENCES:**
- **Immediate work stoppage** for requirement violations
- **Requirement re-acknowledgment** mandatory
- **Additional oversight** for repeat violations
- **Process improvement** sessions for systematic issues

---

**🛡️ This document serves as the single source of truth for agent requirements and workflow rules. All agents must acknowledge and comply with these requirements to prevent workflow crises and ensure smooth autonomous operation.**

**Version 1.0 - July 18, 2025**
**Status: ACTIVE - MANDATORY COMPLIANCE**