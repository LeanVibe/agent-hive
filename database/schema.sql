-- LeanVibe Agent Hive - BACKLOG.md Analytics Database Schema
-- Single source of truth: BACKLOG.md (this database provides analytics layer)

-- Table: backlog_items
-- Stores individual backlog items with metadata for analytics
CREATE TABLE IF NOT EXISTS backlog_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT NOT NULL CHECK (priority IN ('P0', 'P1', 'P2', 'P3')),
    status TEXT NOT NULL CHECK (status IN ('pending', 'completed')) DEFAULT 'pending',
    estimate TEXT,  -- Original estimate string (e.g., "2hr", "30min")
    estimate_hours REAL,  -- Parsed estimate in hours for analytics
    github_issue INTEGER,  -- GitHub issue reference
    created_date TEXT NOT NULL,  -- ISO timestamp when first detected
    completed_date TEXT,  -- ISO timestamp when marked complete
    last_updated TEXT NOT NULL,  -- ISO timestamp of last sync
    raw_line TEXT,  -- Original line from BACKLOG.md for debugging
    section TEXT,  -- Section name (e.g., "Foundation Epic Phase 2 Launch")
    
    -- Unique constraint to prevent duplicates
    UNIQUE(title, priority, section)
);

-- Table: item_history
-- Tracks all changes to backlog items for trend analysis
CREATE TABLE IF NOT EXISTS item_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    change_date TEXT NOT NULL,  -- ISO timestamp
    change_type TEXT NOT NULL CHECK (change_type IN (
        'created', 'completed', 'priority_changed', 'title_changed', 
        'description_changed', 'estimate_changed', 'status_changed'
    )),
    old_value TEXT,  -- Previous value
    new_value TEXT,  -- New value
    sync_batch_id TEXT,  -- UUID for grouping related changes
    
    FOREIGN KEY (item_id) REFERENCES backlog_items(id) ON DELETE CASCADE
);

-- Table: sprint_metrics
-- Aggregated metrics for sprint retrospectives and velocity tracking
CREATE TABLE IF NOT EXISTS sprint_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sprint_date TEXT NOT NULL,  -- Date of sprint (YYYY-MM-DD)
    total_items INTEGER NOT NULL DEFAULT 0,
    completed_items INTEGER NOT NULL DEFAULT 0,
    p0_items INTEGER NOT NULL DEFAULT 0,
    p1_items INTEGER NOT NULL DEFAULT 0,
    p2_items INTEGER NOT NULL DEFAULT 0,
    p3_items INTEGER NOT NULL DEFAULT 0,
    p0_completed INTEGER NOT NULL DEFAULT 0,
    p1_completed INTEGER NOT NULL DEFAULT 0,
    p2_completed INTEGER NOT NULL DEFAULT 0,
    p3_completed INTEGER NOT NULL DEFAULT 0,
    total_estimate_hours REAL DEFAULT 0,
    completed_estimate_hours REAL DEFAULT 0,
    velocity_score REAL DEFAULT 0,  -- Completion rate weighted by priority
    last_updated TEXT NOT NULL,
    
    UNIQUE(sprint_date)
);

-- Table: sync_log
-- Tracks sync operations for debugging and audit
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_date TEXT NOT NULL,
    batch_id TEXT NOT NULL,  -- UUID for grouping sync operations
    items_processed INTEGER NOT NULL DEFAULT 0,
    items_created INTEGER NOT NULL DEFAULT 0,
    items_updated INTEGER NOT NULL DEFAULT 0,
    items_completed INTEGER NOT NULL DEFAULT 0,
    errors TEXT,  -- JSON array of errors if any
    processing_time_ms INTEGER,
    backlog_md_hash TEXT,  -- Hash of BACKLOG.md for change detection
    source_file_path TEXT NOT NULL
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_backlog_items_priority ON backlog_items(priority);
CREATE INDEX IF NOT EXISTS idx_backlog_items_status ON backlog_items(status);
CREATE INDEX IF NOT EXISTS idx_backlog_items_created_date ON backlog_items(created_date);
CREATE INDEX IF NOT EXISTS idx_backlog_items_completed_date ON backlog_items(completed_date);
CREATE INDEX IF NOT EXISTS idx_item_history_item_id ON item_history(item_id);
CREATE INDEX IF NOT EXISTS idx_item_history_change_date ON item_history(change_date);
CREATE INDEX IF NOT EXISTS idx_item_history_change_type ON item_history(change_type);
CREATE INDEX IF NOT EXISTS idx_sprint_metrics_sprint_date ON sprint_metrics(sprint_date);
CREATE INDEX IF NOT EXISTS idx_sync_log_sync_date ON sync_log(sync_date);
CREATE INDEX IF NOT EXISTS idx_sync_log_batch_id ON sync_log(batch_id);

-- Views for common analytics queries

-- View: current_sprint_status
-- Real-time view of current sprint progress
CREATE VIEW IF NOT EXISTS current_sprint_status AS
SELECT 
    priority,
    COUNT(*) as total_items,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_items,
    ROUND(SUM(CASE WHEN estimate_hours IS NOT NULL THEN estimate_hours ELSE 0 END), 2) as total_hours,
    ROUND(SUM(CASE WHEN status = 'completed' AND estimate_hours IS NOT NULL THEN estimate_hours ELSE 0 END), 2) as completed_hours,
    ROUND(
        100.0 * SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 
        2
    ) as completion_percentage
FROM backlog_items 
GROUP BY priority
ORDER BY priority;

-- View: velocity_trend
-- Historical velocity tracking
CREATE VIEW IF NOT EXISTS velocity_trend AS
SELECT 
    sprint_date,
    total_items,
    completed_items,
    ROUND(100.0 * completed_items / NULLIF(total_items, 0), 2) as completion_rate,
    completed_estimate_hours,
    velocity_score,
    ROUND(
        LAG(completed_items) OVER (ORDER BY sprint_date),
        2
    ) as previous_completed,
    ROUND(
        100.0 * (completed_items - LAG(completed_items) OVER (ORDER BY sprint_date)) / 
        NULLIF(LAG(completed_items) OVER (ORDER BY sprint_date), 0),
        2
    ) as velocity_change_percent
FROM sprint_metrics 
ORDER BY sprint_date DESC;

-- View: priority_change_analysis
-- Track how often items change priority
CREATE VIEW IF NOT EXISTS priority_change_analysis AS
SELECT 
    item_id,
    (SELECT title FROM backlog_items WHERE id = item_id) as title,
    COUNT(*) as priority_changes,
    MIN(change_date) as first_change,
    MAX(change_date) as last_change,
    GROUP_CONCAT(old_value || ' → ' || new_value, ', ') as change_history
FROM item_history 
WHERE change_type = 'priority_changed'
GROUP BY item_id
ORDER BY priority_changes DESC;

-- View: completion_time_analysis
-- Analyze how long items take to complete
CREATE VIEW IF NOT EXISTS completion_time_analysis AS
SELECT 
    title,
    priority,
    estimate_hours,
    created_date,
    completed_date,
    ROUND(
        (julianday(completed_date) - julianday(created_date)) * 24,
        2
    ) as actual_hours,
    CASE 
        WHEN estimate_hours IS NOT NULL AND estimate_hours > 0 THEN
            ROUND(
                ((julianday(completed_date) - julianday(created_date)) * 24) / estimate_hours,
                2
            )
        ELSE NULL
    END as estimate_accuracy_ratio
FROM backlog_items 
WHERE status = 'completed' 
    AND created_date IS NOT NULL 
    AND completed_date IS NOT NULL
ORDER BY completed_date DESC;