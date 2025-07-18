# Database Migration Plan - File-based to Database-backed System

## Overview
Migration strategy from current file-based memory management to consolidated database-backed system, incorporating Gemini expert recommendations.

## Migration Strategy

### Phase 1: Enhanced SQLite Foundation (Week 1)
**Goal:** Immediate improvements to current system while preparing for PostgreSQL migration

#### 1.1 Critical Index Addition
```sql
-- Add missing foreign key indexes (CRITICAL)
CREATE INDEX IF NOT EXISTS idx_tasks_agent_id ON tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_parent_task_id ON tasks(parent_task_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_from_agent ON agent_messages(from_agent);
CREATE INDEX IF NOT EXISTS idx_agent_messages_to_agent ON agent_messages(to_agent);
CREATE INDEX IF NOT EXISTS idx_memory_snapshots_session_id ON memory_snapshots(session_id);
CREATE INDEX IF NOT EXISTS idx_context_sessions_agent_id ON context_sessions(agent_id);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_agent_id ON performance_metrics(agent_id);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_task_id ON performance_metrics(task_id);
CREATE INDEX IF NOT EXISTS idx_git_state_agent_id ON git_state(agent_id);
CREATE INDEX IF NOT EXISTS idx_pull_requests_author_agent ON pull_requests(author_agent);
CREATE INDEX IF NOT EXISTS idx_configurations_agent_id ON configurations(agent_id);
CREATE INDEX IF NOT EXISTS idx_events_agent_id ON events(agent_id);
CREATE INDEX IF NOT EXISTS idx_project_tasks_project_id ON project_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_project_tasks_task_id ON project_tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_project_id ON checkpoints(project_id);
```

#### 1.2 Filesystem Storage Implementation
```python
# Memory snapshot storage strategy
class MemorySnapshotManager:
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path / "memory_snapshots"
        self.storage_path.mkdir(exist_ok=True)
    
    def save_snapshot(self, snapshot_id: str, content: dict) -> str:
        """Save content to filesystem, return file path"""
        file_path = self.storage_path / f"{snapshot_id}.json"
        with open(file_path, 'w') as f:
            json.dump(content, f)
        return str(file_path.relative_to(self.storage_path.parent))
    
    def load_snapshot(self, file_path: str) -> dict:
        """Load content from filesystem"""
        full_path = self.storage_path.parent / file_path
        with open(full_path, 'r') as f:
            return json.load(f)
```

#### 1.3 Migration Framework Setup
```python
# Schema migration system
class SchemaMigration:
    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path)
        self.db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)")
    
    def get_current_version(self) -> int:
        cursor = self.db.execute("SELECT MAX(version) FROM schema_migrations")
        result = cursor.fetchone()[0]
        return result if result is not None else 0
    
    def apply_migration(self, version: int, sql_commands: List[str]):
        """Apply migration if not already applied"""
        current = self.get_current_version()
        if version <= current:
            return
        
        with self.db:
            for sql in sql_commands:
                self.db.execute(sql)
            self.db.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
```

### Phase 2: Data Migration (Week 2)
**Goal:** Migrate existing file-based data to database structure

#### 2.1 Current Data Assessment
```bash
# Inventory current data structures
find .claude -name "*.json" -o -name "*.md" | head -20
du -sh .claude/logs/*
ls -la .claude/context/
```

#### 2.2 Migration Scripts
```python
class DataMigrator:
    def migrate_context_files(self):
        """Migrate .claude/context/* to context_sessions table"""
        pass
    
    def migrate_log_files(self):
        """Migrate .claude/logs/* to events table"""
        pass
    
    def migrate_config_files(self):
        """Migrate .claude/config/* to configurations table"""
        pass
    
    def migrate_existing_state_db(self):
        """Import existing state.db data"""
        pass
```

### Phase 3: PostgreSQL Migration (Week 3-4)
**Goal:** Transition to PostgreSQL for production scalability

#### 3.1 PostgreSQL Schema Creation
```sql
-- Enhanced schema with PostgreSQL features
CREATE TABLE agents (
    agent_id TEXT PRIMARY KEY,
    agent_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'idle', 'crashed', 'sleeping')),
    worktree_path TEXT,
    branch_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    configuration JSONB, -- Use JSONB for better performance
    CONSTRAINT valid_agent_type CHECK (agent_type IN ('service-mesh', 'integration', 'pm', 'frontend'))
);

-- Add PostgreSQL-specific indexes
CREATE INDEX idx_agents_configuration_gin ON agents USING GIN (configuration);
CREATE INDEX idx_agents_status_activity ON agents (status, last_activity);
```

#### 3.2 Data Migration Pipeline
```python
class PostgreSQLMigrator:
    def __init__(self, sqlite_path: str, postgres_url: str):
        self.sqlite_conn = sqlite3.connect(sqlite_path)
        self.postgres_conn = psycopg2.connect(postgres_url)
    
    def migrate_table(self, table_name: str, batch_size: int = 1000):
        """Migrate table data in batches"""
        pass
    
    def validate_migration(self, table_name: str) -> bool:
        """Validate data integrity after migration"""
        pass
```

### Phase 4: System Integration (Week 5)
**Goal:** Update all system components to use new database

#### 4.1 Agent Updates
- Update agent initialization to use new database
- Implement connection pooling
- Add error handling and retry logic

#### 4.2 Context Management Integration
- Replace file-based memory with database storage
- Implement context consolidation triggers
- Add performance monitoring

## Migration Checklist

### Pre-Migration
- [ ] Backup all current data files
- [ ] Set up PostgreSQL development instance
- [ ] Create migration test environment
- [ ] Document current data schema

### SQLite Enhancement (Phase 1)
- [ ] Add all missing foreign key indexes
- [ ] Implement filesystem storage for large JSON
- [ ] Set up migration framework
- [ ] Test with current system

### Data Migration (Phase 2)
- [ ] Create data migration scripts
- [ ] Test migration on copy of production data
- [ ] Validate data integrity
- [ ] Performance test with migrated data

### PostgreSQL Migration (Phase 3)
- [ ] Set up PostgreSQL production instance
- [ ] Create enhanced schema with JSONB
- [ ] Implement connection pooling
- [ ] Migrate data with validation

### System Integration (Phase 4)
- [ ] Update all agent code
- [ ] Test multi-agent concurrency
- [ ] Performance benchmark vs. old system
- [ ] Monitor for issues in production

## Risk Mitigation

### Data Loss Prevention
1. **Multiple Backups:** Before each migration phase
2. **Incremental Migration:** Migrate non-critical data first
3. **Rollback Plan:** Keep old system operational during transition
4. **Validation Scripts:** Verify data integrity at each step

### Performance Monitoring
1. **Baseline Metrics:** Measure current system performance
2. **Migration Metrics:** Track performance during migration
3. **Post-Migration Monitoring:** Continuous performance monitoring

### Compatibility
1. **Backward Compatibility:** Maintain old interfaces during transition
2. **Gradual Rollout:** Update agents one at a time
3. **Feature Flags:** Enable/disable new database features

## Success Metrics

### Performance Improvements
- **Query Response Time:** < 100ms for typical queries
- **Concurrent Operations:** 10+ agents without blocking
- **Memory Usage:** < 500MB total database memory

### Reliability Improvements
- **Data Consistency:** Zero data integrity violations
- **Availability:** 99.9% database uptime
- **Recovery Time:** < 5 minutes from any failure

### Developer Experience
- **Migration Ease:** Schema changes deployable without downtime
- **Debugging:** Rich query capabilities for troubleshooting
- **Monitoring:** Real-time performance dashboards