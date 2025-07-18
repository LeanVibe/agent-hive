# PostgreSQL Staging Environment Setup Guide
## Agent Hive Production Readiness - Tooling & Infrastructure Agent

### 🎯 **Objective**
Set up clean PostgreSQL staging environment for Agent Hive database migration testing and validation.

---

## 📋 **Setup Options**

### **Option 1: Docker (Recommended for Local Development)**
```bash
# Pull and run PostgreSQL 15 with persistent storage
docker run --name agent-hive-postgres \
  -e POSTGRES_DB=agent_hive \
  -e POSTGRES_USER=agent_hive_user \
  -e POSTGRES_PASSWORD=staging_password_123 \
  -p 5432:5432 \
  -v agent_hive_data:/var/lib/postgresql/data \
  -d postgres:15

# Verify connection
docker exec -it agent-hive-postgres psql -U agent_hive_user -d agent_hive -c "SELECT version();"
```

### **Option 2: Local PostgreSQL Installation**
```bash
# macOS with Homebrew
brew install postgresql@15
brew services start postgresql@15

# Create database and user
createdb agent_hive
createuser agent_hive_user --createdb --login
psql -c "ALTER USER agent_hive_user PASSWORD 'staging_password_123';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE agent_hive TO agent_hive_user;"
```

### **Option 3: Cloud Staging (Production-Like)**
```bash
# Example with DigitalOcean Managed Database
# Or use AWS RDS, Google Cloud SQL, etc.
# Connection string format:
# postgresql://username:password@host:port/database
```

---

## 🔧 **Configuration & Validation**

### **Connection String**
```
postgresql://agent_hive_user:staging_password_123@localhost:5432/agent_hive
```

### **Validation Commands**
```bash
# Test connection with psql
psql "postgresql://agent_hive_user:staging_password_123@localhost:5432/agent_hive" -c "SELECT current_database();"

# Test connection with Python (for migration scripts)
python3 -c "
import psycopg2
conn = psycopg2.connect('postgresql://agent_hive_user:staging_password_123@localhost:5432/agent_hive')
cursor = conn.cursor()
cursor.execute('SELECT version();')
print('✅ PostgreSQL connection successful:', cursor.fetchone()[0])
conn.close()
"
```

### **Required PostgreSQL Extensions**
```sql
-- Connect to agent_hive database and enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- For UUID generation
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";  -- For performance monitoring
```

---

## 📊 **Performance Configuration for Staging**

### **postgresql.conf Optimizations**
```ini
# Memory settings for staging workload
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB
maintenance_work_mem = 64MB

# Connection settings
max_connections = 100
listen_addresses = 'localhost'

# Logging for debugging
log_statement = 'all'
log_duration = on
log_min_duration_statement = 100ms

# Enable performance monitoring
shared_preload_libraries = 'pg_stat_statements'
track_activity_query_size = 2048
```

---

## 🧪 **Migration Testing Workflow**

### **1. Schema Deployment Test**
```bash
# Deploy schema to staging
cd /Users/bogdan/work/leanvibe-dev/agent-hive
python3 -c "
import psycopg2
conn = psycopg2.connect('postgresql://agent_hive_user:staging_password_123@localhost:5432/agent_hive')
cursor = conn.cursor()
with open('scratchpad/postgresql_schema_design.sql', 'r') as f:
    schema_sql = f.read()
    statements = [s.strip() for s in schema_sql.split(';') if s.strip() and not s.strip().startswith('--')]
    for stmt in statements:
        if stmt and not stmt.startswith('/*'):
            try:
                cursor.execute(stmt)
            except Exception as e:
                if 'already exists' not in str(e):
                    print(f'⚠️  {e}')
conn.commit()
print('✅ Schema deployed to staging')
conn.close()
"
```

### **2. Migration Test Run**
```bash
# Run migration scripts against staging
python3 scratchpad/migration_scripts.py "postgresql://agent_hive_user:staging_password_123@localhost:5432/agent_hive"
```

### **3. Data Validation**
```sql
-- Verify schema structure
SELECT schemaname, tablename, tableowner 
FROM pg_tables 
WHERE schemaname IN ('security', 'agents', 'monitoring', 'optimization')
ORDER BY schemaname, tablename;

-- Verify row counts after migration
SELECT 
    schemaname,
    tablename,
    n_tup_ins AS rows_inserted,
    n_tup_upd AS rows_updated
FROM pg_stat_user_tables
WHERE schemaname IN ('security', 'agents', 'monitoring', 'optimization');

-- Test unified views
SELECT domain, COUNT(*) as metric_count 
FROM unified_metrics 
GROUP BY domain;
```

---

## 🚀 **Ready State Checklist**

### **Environment Ready When:**
- ✅ PostgreSQL 15+ running and accessible
- ✅ `agent_hive` database created with correct permissions
- ✅ Connection string tested and working
- ✅ Required extensions installed
- ✅ Schema deployment tested successfully
- ✅ Migration scripts can connect and execute
- ✅ Performance monitoring enabled

### **Handoff to Database Migration Agent**
```bash
# Signal readiness
echo "✅ PostgreSQL staging environment ready" > scratchpad/staging_ready.signal
echo "Connection: postgresql://agent_hive_user:staging_password_123@localhost:5432/agent_hive" >> scratchpad/staging_ready.signal
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> scratchpad/staging_ready.signal
```

---

## 🔧 **Troubleshooting**

### **Common Issues**
1. **Connection Refused**: Check PostgreSQL is running (`brew services list | grep postgres`)
2. **Authentication Failed**: Verify username/password and pg_hba.conf settings
3. **Database Not Found**: Ensure `agent_hive` database was created successfully
4. **Permission Denied**: Check user privileges on database

### **Docker-Specific Issues**
```bash
# Check container status
docker ps -a | grep agent-hive-postgres

# View logs
docker logs agent-hive-postgres

# Restart container
docker restart agent-hive-postgres

# Clean restart (removes existing data)
docker stop agent-hive-postgres
docker rm agent-hive-postgres
docker volume rm agent_hive_data
# Then re-run initial docker run command
```

### **Performance Validation**
```sql
-- Check active connections
SELECT count(*) as active_connections FROM pg_stat_activity;

-- Monitor query performance
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
```

---

## 📈 **Success Metrics**
- **Connection Latency**: <10ms to localhost PostgreSQL
- **Schema Deployment**: <30 seconds for full schema
- **Migration Execution**: <5 minutes for 113 rows
- **Query Performance**: <1ms for simple selects

**🎯 Target: Staging environment ready within 1 hour of setup initiation**