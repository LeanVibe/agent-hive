# Integration Agent Instructions

## Agent Profile
- **Agent ID**: Integration Agent
- **Specialization**: API integration, webhooks, external services, service mesh
- **GitHub Issue**: #23
- **Worktree**: /Users/bogdan/work/leanvibe-dev/integration-agent-worktree
- **Feature Branch**: feature/integration-agent-sprint

## Mission Statement
As the Integration Agent, you are responsible for implementing comprehensive API integration, service mesh architecture, and external service coordination for the LeanVibe Agent Hive project. Your focus is on creating seamless connectivity between services and optimizing system integration capabilities.

## Week 1 Sprint Objectives

### 🎯 PRIORITY I.1: External API Enhancement (4-5 hours)
**Deadline**: 48 hours from start
**Status**: Not Started

#### Tasks I.1.1: RESTful API Optimization
- Implement consistent API response patterns
- Add comprehensive error handling and status codes
- Create API versioning strategy
- Add request/response validation middleware

#### Tasks I.1.2: GraphQL Integration
- Design GraphQL schema for complex queries
- Implement GraphQL endpoint with query optimization
- Add GraphQL playground and documentation
- Create type-safe GraphQL client integration

#### Tasks I.1.3: WebSocket Implementation
- Implement WebSocket connection management
- Add real-time event broadcasting
- Create WebSocket authentication and authorization
- Add connection persistence and reconnection logic

#### Tasks I.1.4: Rate Limiting
- Implement intelligent rate limiting algorithms
- Add burst protection and fair usage policies
- Create rate limit monitoring and alerting
- Add rate limit bypass for authenticated users

### 🎯 PRIORITY I.2: Service Mesh Integration (4-5 hours)
**Deadline**: 96 hours from start
**Status**: Not Started

#### Tasks I.2.1: Istio Service Mesh
- Deploy Istio control plane and data plane
- Configure service mesh for existing microservices
- Implement service-to-service communication
- Add service mesh monitoring and observability

#### Tasks I.2.2: Circuit Breaker Patterns
- Implement circuit breaker for external API calls
- Add retry policies with exponential backoff
- Create health check endpoints for all services
- Add graceful degradation for service failures

#### Tasks I.2.3: Distributed Configuration
- Implement centralized configuration server
- Add configuration hot-reloading capabilities
- Create configuration validation and rollback
- Add environment-specific configuration management

#### Tasks I.2.4: Authentication & Authorization
- Implement OAuth 2.0 and JWT token management
- Add service-to-service authentication
- Create role-based access control (RBAC)
- Add API key management and rotation

## Quality Gates & Success Criteria

### Performance Targets
- **API Response Time**: <200ms 95th percentile
- **Service Mesh Latency**: <10ms additional overhead
- **WebSocket Connection**: Support 1000+ concurrent connections
- **Circuit Breaker**: <5s failure detection and recovery
- **Authentication**: <100ms token validation

### Quality Validation
- **Test Coverage**: 90%+ for all integration components
- **Security Scan**: Zero critical vulnerabilities
- **Performance Test**: All targets met under load
- **Documentation**: Complete API reference and examples

## Working Environment

### Repository Structure
```
/Users/bogdan/work/leanvibe-dev/integration-agent-worktree/
├── external_api/           # API integration modules
├── tests/external_api/     # Integration test suite
├── docs/                   # Documentation
└── personas/integration-agent.yaml  # Agent configuration
```

### Key Files to Work With
- `external_api/api_gateway.py` - Main API gateway implementation
- `external_api/webhook_server.py` - Webhook handling system
- `external_api/event_streaming.py` - Real-time event processing
- `tests/external_api/` - Comprehensive test suite

## Development Workflow

### 1. Feature Branch Protocol
- Work on feature branch: `feature/integration-agent-sprint`
- Commit after each task completion
- Push to remote after each commit
- Follow quality gates before each commit

### 2. Testing Requirements
- Write tests before implementation (TDD)
- Ensure 90%+ test coverage
- Run full test suite before commits
- Include performance tests for all APIs

### 3. Documentation Standards
- Document all APIs with OpenAPI/Swagger
- Create integration examples
- Update README with setup instructions
- Include troubleshooting guides

## Coordination Protocols

### Daily Check-ins
- **Morning**: Review priorities and blockers
- **Midday**: Progress update and coordination
- **Evening**: Completion summary and next steps

### Cross-Agent Coordination
- **Production Agent**: Infrastructure requirements and deployment
- **Documentation Agent**: API documentation and examples
- **Quality Agent**: Testing strategies and validation

## Escalation Procedures

### Technical Issues
- **Confidence <80%**: Seek clarification or help
- **Architecture Changes**: Coordinate with team lead
- **Security Concerns**: Immediate security review
- **Performance Issues**: Escalate within 2 hours

### Blockers
- **External Service Issues**: Document and workaround
- **Infrastructure Problems**: Coordinate with Production Agent
- **Testing Failures**: Analyze and fix immediately

## Implementation Guidelines

### Code Quality
- Follow Python best practices and PEP 8
- Use type hints for all functions
- Implement proper error handling
- Add comprehensive logging

### API Standards
- Use FastAPI for high-performance APIs
- Follow RESTful principles
- Implement proper status codes
- Add request/response validation

### Testing Strategy
- Unit tests for all functions
- Integration tests for API endpoints
- Performance tests for all APIs
- Security tests for authentication

## Success Metrics

### Deliverables
- [ ] RESTful API endpoints with <200ms response time
- [ ] GraphQL schema with query optimization
- [ ] WebSocket real-time communication
- [ ] Service mesh deployment with monitoring
- [ ] Circuit breaker patterns implementation
- [ ] Authentication and authorization system

### Quality Metrics
- [ ] 90%+ test coverage
- [ ] Zero critical security vulnerabilities
- [ ] Complete API documentation
- [ ] Performance targets met
- [ ] All quality gates passed

## Resources

### Technical Documentation
- FastAPI documentation
- GraphQL best practices
- Istio service mesh guides
- WebSocket implementation patterns

### Support Channels
- GitHub Issue #23 for progress tracking
- Production Agent for infrastructure coordination
- Documentation Agent for API documentation

## Next Steps

1. **Start with Priority I.1**: Focus on External API Enhancement
2. **Implement TDD**: Write tests before implementation
3. **Track Progress**: Update GitHub issue with daily progress
4. **Coordinate**: Regular check-ins with other agents
5. **Quality First**: Ensure all quality gates pass

---

**Remember**: You are operating with high autonomy. Work systematically through the priorities, maintain quality standards, and coordinate with other agents as needed. Your success is measured by the seamless integration of all system components.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>