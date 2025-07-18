# Immediate Action Plan - Agent Hive Production Readiness
## Ready-to-Execute Implementation Guide

### Priority: **URGENT** - Production Blocking Issues
### Timeline: **2 Weeks to Production Ready**
### Approach: **Pareto-Optimized (80/20 Strategy)**

---

## 🚨 CRITICAL BLOCKERS (Start Immediately)

### **Day 1-2: Message Protocol Implementation** 
**Blocking**: All agent communication broken

#### **Immediate Actions**:
```bash
# 1. Create missing classes in message_bus/message_protocol.py
cd message_bus
```

**Add to message_protocol.py**:
```python
from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any, Optional

class MessagePriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class MessageDeliveryStatus(Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"

class AgentMessage(BaseModel):
    version: int = 1  # For backward compatibility
    message_id: str
    from_agent: str
    to_agent: str
    message_type: str
    priority: MessagePriority
    timestamp: datetime
    ttl: int
    body: Dict[str, Any]
    delivery_options: Optional[Dict[str, Any]] = None
```

#### **Validation**:
```bash
# Test imports work
python -c "from message_bus.message_protocol import AgentMessage, MessageDeliveryStatus, MessagePriority; print('✅ Import successful')"

# Run message bus tests
pytest tests/message_bus/ -v
```

### **Day 3: Database Discovery & Analysis**
**Critical**: Understand current 15 SQLite databases before migration

#### **Database Analysis Script**:
```bash
# Create analysis script
cat > scratchpad/analyze_sqlite_databases.py << 'EOF'
#!/usr/bin/env python3
"""Analyze all SQLite databases for migration planning"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List

def analyze_database(db_path: str) -> Dict:
    """Analyze SQLite database schema and data"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get table schemas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    schema_info = {}
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        
        schema_info[table_name] = {
            "columns": columns,
            "row_count": row_count
        }
    
    conn.close()
    return schema_info

# Analyze all .db files
db_files = list(Path('.').glob('*.db'))
analysis = {}

for db_file in db_files:
    print(f"Analyzing {db_file}...")
    try:
        analysis[str(db_file)] = analyze_database(str(db_file))
    except Exception as e:
        print(f"Error analyzing {db_file}: {e}")

# Save analysis
with open('scratchpad/sqlite_analysis.json', 'w') as f:
    json.dump(analysis, f, indent=2, default=str)

print(f"✅ Analysis complete. Found {len(db_files)} databases")
print("📄 Results saved to scratchpad/sqlite_analysis.json")
EOF

python scratchpad/analyze_sqlite_databases.py
```

### **Day 4-5: PostgreSQL Migration Script**
**Critical**: Consolidate 15 SQLite databases

#### **Migration Strategy**:
```sql
-- Create consolidated PostgreSQL schema
-- Save as scratchpad/postgresql_schema.sql

-- Agent Metrics (consolidates monitoring.db, baseline_metrics.db, etc.)
CREATE TABLE agent_metrics (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(255) NOT NULL,
    metric_type VARCHAR(100) NOT NULL,
    value DECIMAL(10,4) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB,
    source_database VARCHAR(100) -- Track original source
);

-- Agent Capabilities (from agent_capabilities.db)
CREATE TABLE agent_capabilities (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(255) NOT NULL,
    capability VARCHAR(255) NOT NULL,
    proficiency_level INTEGER DEFAULT 5,
    description TEXT,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(agent_name, capability)
);

-- Security Events (consolidates security_audit.db, security_metrics.db)
CREATE TABLE security_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    description TEXT,
    metadata JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Conversation History (from agent_conversations.db)
CREATE TABLE agent_conversations (
    id SERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL,
    from_agent VARCHAR(255) NOT NULL,
    to_agent VARCHAR(255) NOT NULL,
    message_type VARCHAR(100),
    content TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Trail (from audit_log.db)
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    action VARCHAR(255) NOT NULL,
    actor VARCHAR(255) NOT NULL,
    target VARCHAR(255),
    details JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX idx_agent_metrics_timestamp ON agent_metrics(timestamp);
CREATE INDEX idx_agent_metrics_agent ON agent_metrics(agent_name);
CREATE INDEX idx_security_events_timestamp ON security_events(timestamp);
CREATE INDEX idx_conversations_timestamp ON agent_conversations(timestamp);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
```

#### **Migration Script Template**:
```python
# Save as scratchpad/migrate_to_postgresql.py
#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script
IMPORTANT: Test thoroughly before production use
"""

import asyncio
import asyncpg
import sqlite3
import json
from pathlib import Path
from typing import Dict, List

class DatabaseMigrator:
    def __init__(self, postgres_url: str):
        self.postgres_url = postgres_url
        self.migration_log = []
    
    async def migrate_database(self, sqlite_path: str, table_mapping: Dict):
        """Migrate one SQLite database to PostgreSQL"""
        print(f"🔄 Migrating {sqlite_path}...")
        
        # Connect to both databases
        sqlite_conn = sqlite3.connect(sqlite_path)
        postgres_conn = await asyncpg.connect(self.postgres_url)
        
        try:
            for sqlite_table, postgres_table in table_mapping.items():
                await self.migrate_table(sqlite_conn, postgres_conn, 
                                       sqlite_table, postgres_table)
        finally:
            sqlite_conn.close()
            await postgres_conn.close()
    
    async def migrate_table(self, sqlite_conn, postgres_conn, 
                          sqlite_table: str, postgres_table: str):
        """Migrate one table with data validation"""
        cursor = sqlite_conn.cursor()
        
        # Get data from SQLite
        cursor.execute(f"SELECT * FROM {sqlite_table}")
        rows = cursor.fetchall()
        
        # Get column names
        cursor.execute(f"PRAGMA table_info({sqlite_table})")
        columns = [col[1] for col in cursor.fetchall()]
        
        print(f"  📊 Migrating {len(rows)} rows from {sqlite_table} to {postgres_table}")
        
        # Insert into PostgreSQL (implement based on schema)
        # This is a template - needs specific implementation per table
        
        self.migration_log.append({
            "source": f"{sqlite_table}",
            "target": postgres_table,
            "rows_migrated": len(rows),
            "columns": columns
        })

# Example usage (customize based on analysis results)
async def main():
    migrator = DatabaseMigrator("postgresql://user:pass@localhost/agent_hive")
    
    # Define table mappings based on sqlite_analysis.json
    # This needs to be customized after database analysis
    table_mappings = {
        "monitoring.db": {
            "metrics": "agent_metrics"
        },
        "agent_capabilities.db": {
            "agent_capabilities": "agent_capabilities"
        }
        # Add more mappings based on analysis
    }
    
    for db_file, mapping in table_mappings.items():
        if Path(db_file).exists():
            await migrator.migrate_database(db_file, mapping)
    
    # Save migration log
    with open('scratchpad/migration_log.json', 'w') as f:
        json.dump(migrator.migration_log, f, indent=2)
    
    print("✅ Migration complete")

if __name__ == "__main__":
    asyncio.run(main())
```

### **Day 6-7: Repository Pattern Implementation**
**Enhancement**: Database-agnostic abstraction layer

#### **Repository Interface**:
```python
# Save as advanced_orchestration/repositories.py
"""Database abstraction layer for production scalability"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncpg
import redis.asyncio as redis

class AgentMetricsRepository(ABC):
    """Abstract repository for agent metrics"""
    
    @abstractmethod
    async def save_metric(self, agent_name: str, metric_type: str, 
                         value: float, metadata: Dict[str, Any] = None) -> bool:
        pass
    
    @abstractmethod
    async def get_agent_metrics(self, agent_name: str, 
                               metric_type: str = None, 
                               limit: int = 100) -> List[Dict]:
        pass

class PostgreSQLAgentMetricsRepository(AgentMetricsRepository):
    """PostgreSQL implementation of metrics repository"""
    
    def __init__(self, connection_pool: asyncpg.Pool):
        self.pool = connection_pool
    
    async def save_metric(self, agent_name: str, metric_type: str, 
                         value: float, metadata: Dict[str, Any] = None) -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO agent_metrics (agent_name, metric_type, value, metadata)
                VALUES ($1, $2, $3, $4)
            """, agent_name, metric_type, value, metadata or {})
        return True
    
    async def get_agent_metrics(self, agent_name: str, 
                               metric_type: str = None, 
                               limit: int = 100) -> List[Dict]:
        async with self.pool.acquire() as conn:
            if metric_type:
                rows = await conn.fetch("""
                    SELECT * FROM agent_metrics 
                    WHERE agent_name = $1 AND metric_type = $2
                    ORDER BY timestamp DESC LIMIT $3
                """, agent_name, metric_type, limit)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM agent_metrics 
                    WHERE agent_name = $1
                    ORDER BY timestamp DESC LIMIT $2
                """, agent_name, limit)
        
        return [dict(row) for row in rows]

# Factory for repository creation
class RepositoryFactory:
    @staticmethod
    async def create_metrics_repository(config: Dict) -> AgentMetricsRepository:
        if config['type'] == 'postgresql':
            pool = await asyncpg.create_pool(config['url'])
            return PostgreSQLAgentMetricsRepository(pool)
        else:
            raise ValueError(f"Unsupported repository type: {config['type']}")
```

### **Day 8-10: Messaging Consolidation**
**Critical**: Remove file-based protocol, Redis-only

#### **Cleanup Actions**:
```bash
# 1. Find all file-based message usage
grep -r "file.*message\|message.*file" . --exclude-dir=.git --exclude-dir=.venv > scratchpad/file_message_usage.txt

# 2. Remove file-based message components
# (After verifying no critical dependencies)

# 3. Update message_bus/__init__.py to export only Redis classes
cat > message_bus/__init__.py << 'EOF'
"""Message Bus - Redis-based agent communication"""

from .message_bus import MessageBus, MessageBusConfig
from .message_protocol import AgentMessage, MessageDeliveryStatus, MessagePriority

__all__ = ['MessageBus', 'MessageBusConfig', 'AgentMessage', 'MessageDeliveryStatus', 'MessagePriority']
EOF

# 4. Validate Redis-only messaging works
pytest tests/message_bus/ -v
```

---

## 📋 Daily Execution Checklist

### **Day 1: Message Protocol**
- [ ] Implement missing classes in message_protocol.py
- [ ] Add message versioning for backward compatibility  
- [ ] Test imports and basic functionality
- [ ] Run message bus test suite
- [ ] **Success Criteria**: All imports work, tests pass

### **Day 2: Message Protocol Completion**
- [ ] Integration testing with existing Redis message bus
- [ ] Update documentation for new protocol
- [ ] Validate agent communication works end-to-end
- [ ] **Success Criteria**: Agents can communicate via Redis

### **Day 3: Database Analysis**
- [ ] Run SQLite analysis script on all .db files
- [ ] Review analysis results for schema mapping
- [ ] Design PostgreSQL consolidated schema
- [ ] Create migration strategy document
- [ ] **Success Criteria**: Complete understanding of data migration scope

### **Day 4-5: PostgreSQL Migration**
- [ ] Set up PostgreSQL development environment
- [ ] Create consolidated schema in PostgreSQL
- [ ] Develop and test migration script
- [ ] Migrate data with validation checks
- [ ] **Success Criteria**: All SQLite data successfully migrated

### **Day 6-7: Repository Pattern**
- [ ] Implement repository interfaces
- [ ] Create PostgreSQL repository implementations
- [ ] Update application code to use repositories
- [ ] Test database abstraction layer
- [ ] **Success Criteria**: Database-agnostic data access working

### **Day 8-10: Messaging Consolidation**
- [ ] Identify and remove file-based message code
- [ ] Update imports and dependencies
- [ ] Test Redis-only messaging thoroughly
- [ ] Performance validation (1000+ msgs/sec)
- [ ] **Success Criteria**: Single messaging protocol, performance targets met

---

## 🎯 Success Validation Commands

```bash
# Test message protocol
python -c "from message_bus.message_protocol import AgentMessage; print('✅ Protocol working')"

# Test database performance
python -c "
import asyncio
import time
from advanced_orchestration.repositories import RepositoryFactory

async def test_performance():
    repo = await RepositoryFactory.create_metrics_repository({'type': 'postgresql', 'url': 'postgresql://...'})
    start = time.time()
    await repo.save_metric('test-agent', 'cpu_usage', 75.5)
    latency = (time.time() - start) * 1000
    print(f'Write latency: {latency:.2f}ms ({'✅' if latency < 50 else '❌'})')

asyncio.run(test_performance())
"

# Test messaging throughput
python -c "
import asyncio
import time
from message_bus import MessageBus

async def test_throughput():
    bus = MessageBus()
    start = time.time()
    for i in range(1000):
        await bus.publish('test-channel', {'test': i})
    duration = time.time() - start
    throughput = 1000 / duration
    print(f'Throughput: {throughput:.0f} msgs/sec ({'✅' if throughput >= 1000 else '❌'})')

asyncio.run(test_throughput())
"
```

---

## 🚨 Emergency Rollback Plan

If any step fails critically:

```bash
# Rollback to current working state
git stash push -m "Emergency rollback - production blocker fix attempt"
git reset --hard HEAD

# Restore SQLite if migration fails
cp *.db.backup *.db  # If backups were made

# Restore file-based messaging if needed
git checkout HEAD -- message_bus/  # Restore original implementation
```

---

## 📞 Escalation Criteria

**Immediately escalate to human if**:
- Database migration shows data loss or corruption
- Message protocol changes break existing functionality
- Performance degrades below current levels
- Any component shows instability after changes

---

**This plan provides immediate, executable steps to resolve the 3 critical production blockers within 2 weeks, leveraging existing infrastructure and following expert AI recommendations for enhanced robustness.**