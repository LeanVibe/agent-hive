# Hybrid Communication Protocol - Standard Operating Procedure

## Overview
This document defines the standard communication protocol for multi-agent coordination in the LeanVibe Agent Hive system. This protocol ensures efficient, reliable, and timely communication between agents during development operations.

## 1. Response Rules

### 1.1 Ping Response Requirement
- **Rule**: All agents MUST respond to main agent pings within **2 minutes maximum**
- **Purpose**: Ensure agent availability and prevent coordination timeouts
- **Implementation**: Agents monitor for incoming ping messages and acknowledge immediately
- **Format**: `ACK - [Agent Type] - Status: [OPERATIONAL/BUSY/BLOCKED]`

### 1.2 Immediate Urgent Push
- **Rule**: Urgent updates MUST be pushed immediately without waiting for ping
- **Purpose**: Critical event notification for time-sensitive coordination
- **Trigger**: Any urgent category event occurs
- **Response Time**: <30 seconds from event occurrence

## 2. Message Formats

### 2.1 Format Structure
All messages follow the pattern: `[PRIORITY] - [Description] - [Evidence/Context]`

### 2.2 Priority Levels

#### **[URGENT]** - Critical/Time-Sensitive
```
Format: [URGENT] - [Action/Event] - [Evidence/Status]
Examples:
- [URGENT] - Service discovery implementation complete - All 25 tests passing, ready for PR creation
- [URGENT] - Critical test failure detected - 15/20 tests failing, requires immediate attention
- [URGENT] - PR #58 ready for review - 1000 lines, all quality gates passed
```

#### **[NORMAL]** - Standard Updates
```
Format: [NORMAL] - [Progress/Status] - [Details]
Examples:
- [NORMAL] - EventStreaming implementation 80% complete - 20/24 tests passing
- [NORMAL] - API Gateway integration in progress - CORS support added
- [NORMAL] - Code review feedback addressed - 3/5 items resolved
```

#### **[INFO]** - General Information
```
Format: [INFO] - [Information/Context] - [Additional Details]
Examples:
- [INFO] - Development environment configured - Python 3.13, pytest ready
- [INFO] - Branch created for feature work - feat/service-discovery-api
- [INFO] - Documentation updated - API reference complete
```

## 3. Urgent Categories

### 3.1 Task Completion Events
**Trigger**: Major development milestone reached
**Examples**:
- Component implementation complete with passing tests
- PR ready for creation/review
- Quality gates passed
- Integration testing complete

### 3.2 Critical Blockers
**Trigger**: Development progress halted by technical issues
**Examples**:
- Build failures preventing development
- Test infrastructure failures
- Missing dependencies or configuration issues
- Merge conflicts requiring human intervention

### 3.3 Test Failures
**Trigger**: Significant test suite degradation
**Examples**:
- >20% test failure rate
- Critical functionality tests failing
- Performance regression detected
- Integration test failures

### 3.4 PR Ready Events
**Trigger**: Code ready for review and merge
**Examples**:
- All quality gates passed
- Test coverage maintained
- Documentation complete
- Compliance validation successful

## 4. Integration with Agent Spawning

### 4.1 New Agent Initialization
```bash
# Protocol activation on spawn
1. Agent receives INSTRUCTIONS.txt with communication protocol reference
2. Agent acknowledges protocol understanding: [INFO] - Protocol activated - Ready for coordination
3. Agent registers with coordination system
4. Main agent confirms agent operational status
```

### 4.2 Agent Handoff Protocol
```bash
# When transferring work between agents
1. Current agent: [URGENT] - Task handoff ready - [Component] implementation at [status]
2. New agent: [INFO] - Task handoff acknowledged - Reviewing [component] status
3. New agent: [NORMAL] - Task continuation initiated - [specific action plan]
```

### 4.3 Spawning Integration Commands
```bash
# Enhanced spawning with protocol integration
python scripts/enhanced_agent_spawner.py \
  --agent-type infrastructure-specialist \
  --priority 1.1 \
  --task "Service discovery integration" \
  --communication-protocol hybrid \
  --response-timeout 120  # 2 minutes
```

## 5. Protocol Implementation

### 5.1 Agent Requirements
- Monitor for ping messages every 30 seconds
- Maintain message queue for urgent events
- Implement automatic acknowledgment system
- Log all communication events for debugging

### 5.2 Main Agent Coordination
- Send ping requests to verify agent availability
- Monitor for urgent updates from all active agents
- Coordinate task distribution based on agent status
- Escalate blocked agents to human intervention

### 5.3 Error Handling
- **Ping Timeout**: If agent doesn't respond within 2 minutes, mark as potentially unresponsive
- **Urgent Failure**: If urgent message fails to deliver, retry 3 times, then escalate
- **Protocol Violation**: Log violations and request protocol compliance confirmation

## 6. Quality Assurance

### 6.1 Message Validation
- Verify correct format usage
- Validate priority level appropriateness
- Ensure evidence/context provided
- Check response timing compliance

### 6.2 Protocol Monitoring
- Track average response times
- Monitor urgent event frequency
- Measure coordination efficiency
- Generate protocol compliance reports

## 7. Examples and Best Practices

### 7.1 Complete Workflow Example
```
Main Agent: "Ping - Status check for infrastructure work"
Infrastructure Agent: "ACK - Infrastructure Agent - Status: OPERATIONAL"

Infrastructure Agent: "[URGENT] - EventStreaming tests fixed - 23/24 tests passing, JSON serialization resolved"
Main Agent: "Acknowledged - Proceeding with PR creation workflow"

Infrastructure Agent: "[URGENT] - PR #64 created - EventStreaming component, 1016 lines, ready for review"
Main Agent: "PR received - Adding to review queue"
```

### 7.2 Best Practices
- **Be Specific**: Include concrete evidence and metrics
- **Be Timely**: Don't delay urgent notifications
- **Be Accurate**: Verify status before reporting
- **Be Consistent**: Use standard format patterns
- **Be Proactive**: Report progress regularly, not just at completion

## 8. Protocol Compliance

### 8.1 Mandatory Requirements
- ✅ 2-minute maximum ping response
- ✅ Immediate urgent event notification
- ✅ Correct message format usage
- ✅ Appropriate priority level selection
- ✅ Evidence/context inclusion

### 8.2 Success Metrics
- Response time: <2 minutes for pings, <30 seconds for urgent
- Format compliance: 100% correct usage
- Event coverage: All urgent categories captured
- Coordination efficiency: Reduced blocking time between agents

---

**Status**: Active Standard Operating Procedure  
**Version**: 1.0  
**Last Updated**: 2025-07-16  
**Applies To**: All LeanVibe Agent Hive agents  
**Compliance**: Mandatory