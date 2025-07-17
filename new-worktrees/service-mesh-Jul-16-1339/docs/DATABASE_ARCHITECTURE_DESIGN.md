# LeanVibe Agent Hive - Consolidated Database Architecture

## Overview
Single SQLite database file (`agent_hive.db`) consolidating all system features for improved performance, consistency, and management.

## Database Schema Design

### Core Agent Management
```sql
-- Agent instances and their state
CREATE TABLE agents (
    agent_id TEXT PRIMARY KEY,
    agent_type TEXT NOT NULL,
    status TEXT NOT NULL, -- 'active', 'idle', 'crashed', 'sleeping'
    worktree_path TEXT,
    branch_name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
    configuration JSON,
    INDEX idx_agents_status (status),
    INDEX idx_agents_type (agent_type)
);

-- Agent communication and coordination
CREATE TABLE agent_messages (
    message_id TEXT PRIMARY KEY,
    from_agent TEXT,
    to_agent TEXT,
    message_type TEXT, -- 'command', 'status', 'urgent', 'coordination'
    content TEXT,
    priority INTEGER DEFAULT 5,
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    delivered_at DATETIME,
    acknowledged_at DATETIME,
    FOREIGN KEY (from_agent) REFERENCES agents(agent_id),
    FOREIGN KEY (to_agent) REFERENCES agents(agent_id),
    INDEX idx_messages_recipient (to_agent, delivered_at),
    INDEX idx_messages_priority (priority, sent_at)
);
```

### Task and Project Management
```sql
-- Task management system
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    agent_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL, -- 'pending', 'in_progress', 'completed', 'failed'
    priority TEXT NOT NULL, -- 'high', 'medium', 'low'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    estimated_duration INTEGER, -- minutes
    actual_duration INTEGER, -- minutes
    confidence_score REAL,
    parent_task_id TEXT,
    tags JSON,
    metadata JSON,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (parent_task_id) REFERENCES tasks(task_id),
    INDEX idx_tasks_status (status),
    INDEX idx_tasks_agent (agent_id, status),
    INDEX idx_tasks_priority (priority, created_at)
);

-- Project and epic management
CREATE TABLE projects (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL, -- 'planning', 'active', 'completed', 'paused'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    target_completion DATETIME,
    metadata JSON,
    INDEX idx_projects_status (status)
);

-- Link tasks to projects
CREATE TABLE project_tasks (
    project_id TEXT,
    task_id TEXT,
    PRIMARY KEY (project_id, task_id),
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);
```

### Context and Memory Management
```sql
-- Context sessions for each agent
CREATE TABLE context_sessions (
    session_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    context_data JSON,
    usage_percent REAL DEFAULT 0.0,
    token_count INTEGER DEFAULT 0,
    max_tokens INTEGER DEFAULT 200000,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    INDEX idx_sessions_agent (agent_id, is_active),
    INDEX idx_sessions_usage (usage_percent)
);

-- Memory snapshots and consolidation
CREATE TABLE memory_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    memory_type TEXT NOT NULL, -- 'working', 'consolidated', 'archived', 'critical'
    content JSON NOT NULL,
    content_hash TEXT, -- For deduplication
    compression_ratio REAL,
    importance_score REAL DEFAULT 0.5,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    tags JSON,
    FOREIGN KEY (session_id) REFERENCES context_sessions(session_id),
    INDEX idx_snapshots_session (session_id, memory_type),
    INDEX idx_snapshots_importance (importance_score),
    INDEX idx_snapshots_hash (content_hash)
);

-- Context consolidation events
CREATE TABLE context_events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL, -- 'consolidation', 'compression', 'overflow_warning', 'sleep', 'wake'
    details JSON,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES context_sessions(session_id),
    INDEX idx_events_session (session_id, timestamp),
    INDEX idx_events_type (event_type, timestamp)
);
```

### Performance and Quality Metrics
```sql
-- Performance tracking
CREATE TABLE performance_metrics (
    metric_id TEXT PRIMARY KEY,
    agent_id TEXT,
    task_id TEXT,
    metric_type TEXT NOT NULL, -- 'duration', 'confidence', 'quality', 'efficiency'
    value REAL NOT NULL,
    unit TEXT, -- 'seconds', 'percentage', 'lines_of_code', etc.
    context JSON,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (task_id) REFERENCES tasks(task_id),
    INDEX idx_metrics_agent (agent_id, metric_type),
    INDEX idx_metrics_task (task_id, metric_type),
    INDEX idx_metrics_time (recorded_at)
);

-- Quality gates and checkpoints
CREATE TABLE checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    project_id TEXT,
    name TEXT NOT NULL,
    git_tag TEXT,
    metrics JSON,
    quality_score REAL,
    passed BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    validated_at DATETIME,
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    INDEX idx_checkpoints_project (project_id, created_at)
);
```

### Code and Repository Management
```sql
-- Git repository state
CREATE TABLE git_state (
    state_id TEXT PRIMARY KEY,
    agent_id TEXT,
    branch_name TEXT NOT NULL,
    commit_hash TEXT,
    pr_number INTEGER,
    pr_status TEXT, -- 'draft', 'open', 'merged', 'closed'
    lines_added INTEGER DEFAULT 0,
    lines_removed INTEGER DEFAULT 0,
    files_changed INTEGER DEFAULT 0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    INDEX idx_git_agent (agent_id, updated_at),
    INDEX idx_git_pr (pr_number, pr_status)
);

-- Pull request tracking
CREATE TABLE pull_requests (
    pr_id TEXT PRIMARY KEY,
    pr_number INTEGER UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    author_agent TEXT,
    status TEXT NOT NULL, -- 'draft', 'open', 'merged', 'closed'
    size_lines INTEGER,
    test_coverage REAL,
    quality_score REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    merged_at DATETIME,
    conflicts_resolved_at DATETIME,
    FOREIGN KEY (author_agent) REFERENCES agents(agent_id),
    INDEX idx_pr_status (status, created_at),
    INDEX idx_pr_size (size_lines)
);
```

### Configuration and Settings
```sql
-- System configuration
CREATE TABLE configurations (
    config_id TEXT PRIMARY KEY,
    agent_id TEXT, -- NULL for global config
    category TEXT NOT NULL, -- 'system', 'agent', 'project', 'quality_gates'
    key TEXT NOT NULL,
    value JSON NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    UNIQUE (agent_id, category, key),
    INDEX idx_config_category (category, key)
);

-- Event logging
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    agent_id TEXT,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL, -- 'debug', 'info', 'warning', 'error', 'critical'
    message TEXT NOT NULL,
    details JSON,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    correlation_id TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    INDEX idx_events_agent (agent_id, timestamp),
    INDEX idx_events_type (event_type, timestamp),
    INDEX idx_events_severity (severity, timestamp)
);
```

## Key Design Principles

### 1. Single Database File
- **File:** `agent_hive.db` in `.claude/` directory
- **Benefits:** Atomic transactions, consistency, simplified backup
- **Performance:** SQLite handles concurrent access well for our use case

### 2. Proper Relationships
- Foreign keys ensure data integrity
- Cascading deletes for cleanup
- Proper indexing for query performance

### 3. JSON Flexibility
- Use JSON columns for flexible metadata and configuration
- Allows schema evolution without migrations
- Efficient for nested data structures

### 4. Performance Optimization
- Strategic indexes on common query patterns
- Partitioning by agent_id and timestamp
- Efficient text search capabilities

### 5. Future Extensibility
- Flexible metadata columns
- Versioning support
- Plugin architecture ready

## Migration Strategy

### Phase 1: Database Creation
1. Create new consolidated database schema
2. Implement database manager class
3. Add connection pooling and error handling

### Phase 2: Data Migration
1. Migrate existing state.db data
2. Import file-based memory snapshots
3. Convert configuration files to database

### Phase 3: System Integration
1. Update all agents to use new database
2. Implement real-time context monitoring
3. Add performance dashboards

### Phase 4: Optimization
1. Query performance tuning
2. Implement caching strategies
3. Add monitoring and alerting

## Benefits

### Immediate
- **Consistency:** Single source of truth
- **Performance:** Better query performance with proper indexing
- **Reliability:** ACID transactions, better error handling
- **Backup:** Single file backup/restore

### Long-term
- **Scalability:** Better handling of large datasets
- **Analytics:** Complex queries across all data
- **Integration:** Easier integration with monitoring tools
- **Evolution:** Schema can evolve without breaking changes