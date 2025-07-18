# Gemini Technical Query Templates

## Query 1: Schema Relationship Analysis
```
Please analyze this SQLite database schema for a multi-agent AI coordination system. Focus on:

1. Table relationship design - are foreign keys and indexes optimal?
2. Normalization level - appropriate for the use case?
3. Potential performance bottlenecks in the relationship structure

[Include the full schema from DATABASE_ARCHITECTURE_DESIGN.md]

Specific concerns:
- agent_messages table with from_agent/to_agent relationships
- tasks table with parent_task_id self-reference
- memory_snapshots with JSON content storage
```

## Query 2: Index Optimization Review
```
Review these SQLite indexes for an agent coordination system handling:
- 1000+ concurrent tasks
- 50+ active agents
- High-frequency message routing
- Complex analytics queries

Current indexes:
[Copy all INDEX statements from schema]

Questions:
1. Are composite index column orders optimal for query patterns?
2. Should we add covering indexes for specific queries?
3. How will JSON column queries perform with these indexes?
4. What indexes are missing for typical agent coordination queries?
```

## Query 3: SQLite vs PostgreSQL Decision
```
Compare SQLite vs PostgreSQL for this multi-agent system:

Requirements:
- 24/7 operation with multiple concurrent agents
- Mix of real-time queries and analytics
- JSON-heavy configuration and metadata storage
- Need for ACID transactions across agent operations
- Single-server deployment preferred

Schema characteristics:
- 12 core tables with foreign key relationships
- Heavy use of JSON columns for flexibility
- Time-series data (events, metrics, messages)
- Complex queries for agent coordination

Provide specific recommendations with pros/cons for each option.
```

## Query 4: Performance Optimization Analysis
```
Analyze potential performance issues in this agent coordination database:

High-frequency operations:
1. Agent status updates (agents table)
2. Message routing (agent_messages table) 
3. Event logging (events table)
4. Context usage tracking (context_sessions table)

Typical query patterns:
- Find all pending tasks for specific agent
- Route messages by priority and recipient
- Track agent performance metrics over time
- Consolidate memory snapshots by importance

What optimizations would you recommend for these patterns?
```

## Query 5: Data Integrity and Constraints
```
Review data integrity design for this agent coordination system:

Current constraints:
- Foreign keys for referential integrity
- Unique constraints on natural keys
- Default values and NOT NULL constraints

Missing considerations:
1. Should agent status transitions be constrained?
2. How to ensure message delivery consistency?
3. Task status workflow validation
4. JSON schema validation for configuration data

What additional constraints or patterns would improve data integrity?
```

## Query 6: Memory Management Architecture Review
```
Evaluate this memory management design for AI agents:

Design:
- context_sessions: track token usage and context state
- memory_snapshots: store consolidated memory with importance scoring
- Automatic consolidation when usage_percent > 85%

Key questions:
1. Is importance_score-based pruning effective for AI memory?
2. Should different memory types (working, consolidated, critical) be in separate tables?
3. How to optimize JSON storage vs compression for large context data?
4. Best practices for AI agent memory persistence?
```

## Query 7: Event Logging and Observability
```
Review event logging architecture for multi-agent system observability:

Current design:
- Single events table with severity levels
- JSON details column for flexible event data
- Correlation_id for distributed tracing

Scale requirements:
- Potentially high-volume event generation
- Need for real-time monitoring
- Complex queries for system analysis

Questions:
1. Should high-frequency events be separated from system events?
2. Optimal indexing strategy for log analysis?
3. Event retention and archival strategies?
4. Integration with monitoring/alerting systems?
```

## Query 8: Schema Evolution Strategy
```
Design a schema evolution strategy for this agent coordination system:

Current flexibility:
- JSON columns for extensible metadata
- Configuration table for runtime changes
- Flexible tagging systems

Future considerations:
- Schema migrations in production agent systems
- Backward compatibility requirements
- Versioning strategy for breaking changes

What patterns and tools would you recommend for managing schema evolution in this context?
```

## How to Use These Templates

1. Copy any specific query template
2. Include the relevant schema sections from DATABASE_ARCHITECTURE_DESIGN.md
3. Submit to Gemini for detailed technical analysis
4. Use responses to guide implementation decisions

## Example Usage
```
"I'm designing a database for a multi-agent AI coordination system. [Insert Query 1 template with schema]. Please provide specific recommendations for optimization."
```