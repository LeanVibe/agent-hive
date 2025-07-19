-- LeanVibe Agent Hive Database Initialization
-- PostgreSQL setup for production environment

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create application database if not exists
-- Note: POSTGRES_DB environment variable should handle this, but explicit creation for safety
-- CREATE DATABASE agent_hive;

-- Create application user with restricted permissions
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'agent_hive_app') THEN
        CREATE ROLE agent_hive_app WITH LOGIN PASSWORD 'secure_app_password';
    END IF;
END
$$;

-- Grant necessary permissions
GRANT CONNECT ON DATABASE agent_hive TO agent_hive_app;
GRANT USAGE ON SCHEMA public TO agent_hive_app;
GRANT CREATE ON SCHEMA public TO agent_hive_app;

-- Create core tables for agent coordination
CREATE TABLE IF NOT EXISTS agent_sessions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    session_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    session_end TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS task_queue (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL UNIQUE,
    agent_id VARCHAR(255),
    priority INTEGER DEFAULT 5,
    status VARCHAR(50) DEFAULT 'pending',
    task_data JSONB NOT NULL,
    assigned_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    metric_name VARCHAR(255) NOT NULL,
    metric_value NUMERIC NOT NULL,
    metric_unit VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS coordination_events (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    source_agent VARCHAR(255),
    target_agent VARCHAR(255),
    event_data JSONB NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_agent_sessions_agent_id ON agent_sessions(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_status ON agent_sessions(status);
CREATE INDEX IF NOT EXISTS idx_task_queue_status ON task_queue(status);
CREATE INDEX IF NOT EXISTS idx_task_queue_priority ON task_queue(priority);
CREATE INDEX IF NOT EXISTS idx_task_queue_agent_id ON task_queue(agent_id);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_agent_id ON performance_metrics(agent_id);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON performance_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_coordination_events_timestamp ON coordination_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_coordination_events_type ON coordination_events(event_type);

-- Create function to update timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_agent_sessions_updated_at BEFORE UPDATE ON agent_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_task_queue_updated_at BEFORE UPDATE ON task_queue 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions on tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO agent_hive_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO agent_hive_app;

-- Insert initial system data
INSERT INTO coordination_events (event_type, event_data) 
VALUES ('system_initialization', '{"message": "Database initialized successfully", "version": "1.0.0"}')
ON CONFLICT DO NOTHING;

-- Database tuning for production
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET track_activity_query_size = 2048;
ALTER SYSTEM SET pg_stat_statements.track = 'all';