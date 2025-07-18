-- Agent Hive Unified PostgreSQL Schema Design
-- Consolidates 12 SQLite databases into 4 logical domains
-- Migration target for production readiness

-- =============================================================================
-- SECURITY & AUDIT DOMAIN
-- Consolidates: security_metrics.db, security_audit.db, unified_security_metrics.db, 
--               auth_pipeline_metrics.db, audit_log.db
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS security;

-- Unified security metrics table
CREATE TABLE security.metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(255) NOT NULL,
    metric_type VARCHAR(100) NOT NULL, -- 'security', 'auth_pipeline', 'unified'
    value NUMERIC NOT NULL,
    unit VARCHAR(50),
    source_system VARCHAR(100),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB,
    
    CONSTRAINT unique_metric_timestamp UNIQUE (metric_name, metric_type, timestamp)
);

-- Security audit events
CREATE TABLE security.audit_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    event_source VARCHAR(100) NOT NULL,
    event_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    agent_id VARCHAR(100),
    resource_accessed VARCHAR(255),
    action_performed VARCHAR(100),
    result VARCHAR(50), -- 'success', 'failure', 'blocked'
    details JSONB,
    severity VARCHAR(20) DEFAULT 'info', -- 'critical', 'high', 'medium', 'low', 'info'
    
    INDEX idx_audit_timestamp (event_timestamp),
    INDEX idx_audit_agent (agent_id),
    INDEX idx_audit_severity (severity)
);

-- =============================================================================
-- AGENT MANAGEMENT DOMAIN  
-- Consolidates: agent_capabilities.db, agent_conversations.db
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS agents;

-- Agent capabilities and metadata
CREATE TABLE agents.capabilities (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) UNIQUE NOT NULL,
    agent_type VARCHAR(100) NOT NULL,
    capabilities JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'inactive', 'maintenance'
    version VARCHAR(50),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB,
    
    INDEX idx_agent_status (status),
    INDEX idx_agent_type (agent_type)
);

-- Agent conversation history and context
CREATE TABLE agents.conversations (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(100) NOT NULL,
    agent_id VARCHAR(100) NOT NULL,
    message_id VARCHAR(100),
    message_type VARCHAR(50), -- 'request', 'response', 'system', 'error'
    content TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    context JSONB,
    parent_message_id VARCHAR(100), -- For conversation threading
    
    FOREIGN KEY (agent_id) REFERENCES agents.capabilities(agent_id),
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_conversation_timestamp (timestamp),
    INDEX idx_agent_conversations (agent_id)
);

-- =============================================================================
-- MONITORING & ANALYTICS DOMAIN
-- Consolidates: predictive_analytics.db, baseline_metrics.db, monitoring.db
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS monitoring;

-- Unified metrics collection (baseline + monitoring)
CREATE TABLE monitoring.metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(255) NOT NULL,
    metric_category VARCHAR(100) NOT NULL, -- 'baseline', 'realtime', 'predictive'
    value NUMERIC NOT NULL,
    unit VARCHAR(50) NOT NULL,
    source VARCHAR(100),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tags JSONB, -- For flexible tagging and filtering
    
    CONSTRAINT unique_metric_time UNIQUE (metric_name, metric_category, timestamp),
    INDEX idx_metrics_category (metric_category),
    INDEX idx_metrics_timestamp (timestamp),
    INDEX idx_metrics_source (source)
);

-- Predictive analytics models and results
CREATE TABLE monitoring.predictive_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(255) NOT NULL,
    model_type VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    training_data_size INTEGER,
    accuracy_score NUMERIC(5,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'deprecated', 'training'
    parameters JSONB,
    
    CONSTRAINT unique_model_version UNIQUE (model_name, version)
);

CREATE TABLE monitoring.predictions (
    id SERIAL PRIMARY KEY,
    model_id INTEGER NOT NULL,
    prediction_type VARCHAR(100) NOT NULL,
    input_data JSONB NOT NULL,
    prediction_result JSONB NOT NULL,
    confidence_score NUMERIC(5,4),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    actual_outcome JSONB, -- Filled in later for model validation
    
    FOREIGN KEY (model_id) REFERENCES monitoring.predictive_models(id),
    INDEX idx_predictions_type (prediction_type),
    INDEX idx_predictions_timestamp (timestamp)
);

-- =============================================================================
-- LEARNING & OPTIMIZATION DOMAIN
-- Consolidates: adaptive_learning.db, pattern_optimizer.db
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS optimization;

-- Adaptive learning patterns and insights
CREATE TABLE optimization.learning_patterns (
    id SERIAL PRIMARY KEY,
    pattern_name VARCHAR(255) NOT NULL,
    pattern_type VARCHAR(100) NOT NULL, -- 'behavioral', 'performance', 'optimization'
    agent_id VARCHAR(100),
    pattern_data JSONB NOT NULL,
    confidence_level NUMERIC(5,4),
    frequency_observed INTEGER DEFAULT 1,
    first_observed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_observed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'deprecated', 'investigating'
    
    FOREIGN KEY (agent_id) REFERENCES agents.capabilities(agent_id),
    INDEX idx_learning_agent (agent_id),
    INDEX idx_learning_type (pattern_type),
    INDEX idx_learning_confidence (confidence_level)
);

-- Pattern-based optimizations and their results
CREATE TABLE optimization.optimizations (
    id SERIAL PRIMARY KEY,
    optimization_name VARCHAR(255) NOT NULL,
    target_system VARCHAR(100) NOT NULL,
    optimization_type VARCHAR(100) NOT NULL, -- 'performance', 'resource', 'algorithm'
    pattern_id INTEGER,
    baseline_metrics JSONB,
    optimization_config JSONB NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    result_metrics JSONB,
    improvement_percentage NUMERIC(5,2),
    status VARCHAR(50) DEFAULT 'applied', -- 'applied', 'rolled_back', 'testing'
    
    FOREIGN KEY (pattern_id) REFERENCES optimization.learning_patterns(id),
    INDEX idx_optimization_system (target_system),
    INDEX idx_optimization_type (optimization_type),
    INDEX idx_optimization_improvement (improvement_percentage)
);

-- =============================================================================
-- CROSS-DOMAIN VIEWS FOR UNIFIED ACCESS
-- =============================================================================

-- Unified metrics view across all domains
CREATE VIEW unified_metrics AS
SELECT 
    'security' as domain,
    metric_name,
    metric_type as category,
    value,
    unit,
    timestamp,
    source_system as source,
    metadata as additional_data
FROM security.metrics
UNION ALL
SELECT 
    'monitoring' as domain,
    metric_name,
    metric_category as category,
    value,
    unit,
    timestamp,
    source,
    tags as additional_data
FROM monitoring.metrics;

-- Agent activity overview
CREATE VIEW agent_activity AS
SELECT 
    c.agent_id,
    c.agent_type,
    c.status,
    COUNT(conv.id) as message_count,
    MAX(conv.timestamp) as last_activity,
    COUNT(lp.id) as patterns_learned
FROM agents.capabilities c
LEFT JOIN agents.conversations conv ON c.agent_id = conv.agent_id
LEFT JOIN optimization.learning_patterns lp ON c.agent_id = lp.agent_id
GROUP BY c.agent_id, c.agent_type, c.status;

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Time-based partitioning for high-volume tables (implement if needed)
-- CREATE INDEX CONCURRENTLY idx_security_metrics_time_hash ON security.metrics USING HASH (date_trunc('day', timestamp));
-- CREATE INDEX CONCURRENTLY idx_monitoring_metrics_time_hash ON monitoring.metrics USING HASH (date_trunc('day', timestamp));

-- Composite indexes for common query patterns
CREATE INDEX CONCURRENTLY idx_security_metrics_name_time ON security.metrics (metric_name, timestamp);
CREATE INDEX CONCURRENTLY idx_monitoring_metrics_category_time ON monitoring.metrics (metric_category, timestamp);
CREATE INDEX CONCURRENTLY idx_agent_conv_id_time ON agents.conversations (conversation_id, timestamp);

-- =============================================================================
-- DATA MIGRATION NOTES
-- =============================================================================

/*
Migration Strategy:
1. baseline_metrics.db → monitoring.metrics (category='baseline')
2. adaptive_learning.db → optimization.learning_patterns  
3. security_metrics.db → security.metrics (metric_type='security')
4. agent_capabilities.db → agents.capabilities
5. agent_conversations.db → agents.conversations
6. predictive_analytics.db → monitoring.predictive_models + monitoring.predictions
7. audit_log.db → security.audit_events
8. pattern_optimizer.db → optimization.optimizations
9. auth_pipeline_metrics.db → security.metrics (metric_type='auth_pipeline')
10. security_audit.db → security.audit_events
11. monitoring.db → monitoring.metrics (category='realtime')
12. unified_security_metrics.db → security.metrics (metric_type='unified')

Data Volume: 113 rows total across 26 tables → Consolidated into 4 schemas, 10 core tables
Migration Time Estimate: <5 minutes (due to small data size)
*/