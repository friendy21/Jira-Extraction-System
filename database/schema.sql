-- Jira MCP System - PostgreSQL Database Schema
-- Run this script to create all tables

-- ============================================
-- REFERENCE DATA TABLES
-- ============================================

-- Organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Teams table
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    team_code VARCHAR(50) NOT NULL,
    team_name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(org_id, team_code)
);

CREATE INDEX idx_teams_org_id ON teams(org_id);

-- Jira Users table
CREATE TABLE IF NOT EXISTS jira_users (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255),
    email_address VARCHAR(255),
    active BOOLEAN DEFAULT TRUE,
    timezone VARCHAR(100),
    avatar_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_jira_users_account_id ON jira_users(account_id);
CREATE INDEX idx_jira_users_email ON jira_users(email_address);

-- Project Categories table
CREATE TABLE IF NOT EXISTS jira_project_categories (
    id SERIAL PRIMARY KEY,
    jira_id VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Jira Projects table
CREATE TABLE IF NOT EXISTS jira_projects (
    id SERIAL PRIMARY KEY,
    jira_id VARCHAR(50) NOT NULL UNIQUE,
    project_key VARCHAR(50) NOT NULL UNIQUE,
    project_name VARCHAR(255) NOT NULL,
    description TEXT,
    project_type VARCHAR(100),
    style VARCHAR(50),
    lead_id INTEGER REFERENCES jira_users(id),
    category_id INTEGER REFERENCES jira_project_categories(id),
    team_id INTEGER REFERENCES teams(id),
    url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_jira_projects_key ON jira_projects(project_key);
CREATE INDEX idx_jira_projects_team ON jira_projects(team_id);

-- Status Categories table
CREATE TABLE IF NOT EXISTS jira_status_categories (
    id SERIAL PRIMARY KEY,
    jira_id INTEGER NOT NULL UNIQUE,
    key VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    color_name VARCHAR(50)
);

-- Statuses table
CREATE TABLE IF NOT EXISTS jira_statuses (
    id SERIAL PRIMARY KEY,
    jira_id VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category_id INTEGER REFERENCES jira_status_categories(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_jira_statuses_name ON jira_statuses(name);

-- Priorities table
CREATE TABLE IF NOT EXISTS jira_priorities (
    id SERIAL PRIMARY KEY,
    jira_id VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon_url TEXT,
    status_color VARCHAR(50),
    sort_order INTEGER DEFAULT 0
);

-- Issue Types table
CREATE TABLE IF NOT EXISTS jira_issue_types (
    id SERIAL PRIMARY KEY,
    jira_id VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon_url TEXT,
    subtask BOOLEAN DEFAULT FALSE,
    hierarchy_level INTEGER DEFAULT 0
);

-- Resolutions table
CREATE TABLE IF NOT EXISTS jira_resolutions (
    id SERIAL PRIMARY KEY,
    jira_id VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT
);

-- Issue Link Types table
CREATE TABLE IF NOT EXISTS jira_issue_link_types (
    id SERIAL PRIMARY KEY,
    jira_id VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    inward VARCHAR(255),
    outward VARCHAR(255)
);

-- Labels table
CREATE TABLE IF NOT EXISTS jira_labels (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_jira_labels_name ON jira_labels(name);

-- ============================================
-- PROJECT-LEVEL TABLES
-- ============================================

-- Components table
CREATE TABLE IF NOT EXISTS jira_components (
    id SERIAL PRIMARY KEY,
    jira_id VARCHAR(50) NOT NULL UNIQUE,
    project_id INTEGER NOT NULL REFERENCES jira_projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    lead_id INTEGER REFERENCES jira_users(id),
    assignee_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_jira_components_project ON jira_components(project_id);

-- Versions table
CREATE TABLE IF NOT EXISTS jira_versions (
    id SERIAL PRIMARY KEY,
    jira_id VARCHAR(50) NOT NULL UNIQUE,
    project_id INTEGER NOT NULL REFERENCES jira_projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    archived BOOLEAN DEFAULT FALSE,
    released BOOLEAN DEFAULT FALSE,
    start_date DATE,
    release_date DATE,
    overdue BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_jira_versions_project ON jira_versions(project_id);

-- Boards table (Scrum & Kanban)
CREATE TABLE IF NOT EXISTS jira_boards (
    id SERIAL PRIMARY KEY,
    jira_id INTEGER NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    board_type VARCHAR(50) NOT NULL,  -- 'scrum' or 'kanban'
    project_id INTEGER REFERENCES jira_projects(id),
    filter_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_jira_boards_project ON jira_boards(project_id);
CREATE INDEX idx_jira_boards_type ON jira_boards(board_type);

-- Swimlanes table
CREATE TABLE IF NOT EXISTS jira_swimlanes (
    id SERIAL PRIMARY KEY,
    board_id INTEGER NOT NULL REFERENCES jira_boards(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    swimlane_type VARCHAR(50),  -- 'assignee', 'epic', 'project', 'custom', etc.
    query TEXT,
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_jira_swimlanes_board ON jira_swimlanes(board_id);

-- Sprints table
CREATE TABLE IF NOT EXISTS jira_sprints (
    id SERIAL PRIMARY KEY,
    jira_id INTEGER NOT NULL UNIQUE,
    board_id INTEGER REFERENCES jira_boards(id),
    name VARCHAR(255) NOT NULL,
    state VARCHAR(50),  -- 'active', 'closed', 'future'
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    complete_date TIMESTAMP,
    goal TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_jira_sprints_board ON jira_sprints(board_id);
CREATE INDEX idx_jira_sprints_state ON jira_sprints(state);
CREATE INDEX idx_jira_sprints_dates ON jira_sprints(start_date, end_date);

-- ============================================
-- ISSUE TABLES
-- ============================================

-- Main Issues table
CREATE TABLE IF NOT EXISTS jira_issues (
    id SERIAL PRIMARY KEY,
    jira_id VARCHAR(50) NOT NULL UNIQUE,
    issue_key VARCHAR(50) NOT NULL UNIQUE,
    project_id INTEGER NOT NULL REFERENCES jira_projects(id),
    parent_issue_id INTEGER REFERENCES jira_issues(id),
    
    -- Core fields
    summary TEXT NOT NULL,
    description TEXT,
    environment TEXT,
    
    -- Type and status
    issue_type_id INTEGER REFERENCES jira_issue_types(id),
    status_id INTEGER REFERENCES jira_statuses(id),
    priority_id INTEGER REFERENCES jira_priorities(id),
    resolution_id INTEGER REFERENCES jira_resolutions(id),
    
    -- People
    assignee_id INTEGER REFERENCES jira_users(id),
    reporter_id INTEGER REFERENCES jira_users(id),
    creator_id INTEGER REFERENCES jira_users(id),
    
    -- Epic/Sprint
    sprint_id INTEGER REFERENCES jira_sprints(id),
    epic_key VARCHAR(50),
    epic_name VARCHAR(255),
    
    -- Time tracking
    story_points DECIMAL(10, 2),
    original_estimate INTEGER,  -- seconds
    remaining_estimate INTEGER,  -- seconds
    time_spent INTEGER,  -- seconds
    
    -- Dates
    created_date TIMESTAMP NOT NULL,
    updated_date TIMESTAMP NOT NULL,
    resolution_date TIMESTAMP,
    due_date DATE,
    
    -- Metrics
    votes INTEGER DEFAULT 0,
    watches INTEGER DEFAULT 0,
    
    -- Additional
    security_level VARCHAR(255),
    subtask_count INTEGER DEFAULT 0,
    
    -- SLA tracking
    first_response_date TIMESTAMP,
    sla_breached BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_jira_issues_key ON jira_issues(issue_key);
CREATE INDEX idx_jira_issues_project ON jira_issues(project_id);
CREATE INDEX idx_jira_issues_status ON jira_issues(status_id);
CREATE INDEX idx_jira_issues_assignee ON jira_issues(assignee_id);
CREATE INDEX idx_jira_issues_sprint ON jira_issues(sprint_id);
CREATE INDEX idx_jira_issues_epic ON jira_issues(epic_key);
CREATE INDEX idx_jira_issues_created ON jira_issues(created_date);
CREATE INDEX idx_jira_issues_updated ON jira_issues(updated_date);
CREATE INDEX idx_jira_issues_priority ON jira_issues(priority_id);
CREATE INDEX idx_jira_issues_type ON jira_issues(issue_type_id);

-- Issue Labels (many-to-many)
CREATE TABLE IF NOT EXISTS issue_labels (
    id SERIAL PRIMARY KEY,
    issue_id INTEGER NOT NULL REFERENCES jira_issues(id) ON DELETE CASCADE,
    label_id INTEGER NOT NULL REFERENCES jira_labels(id) ON DELETE CASCADE,
    UNIQUE(issue_id, label_id)
);

CREATE INDEX idx_issue_labels_issue ON issue_labels(issue_id);
CREATE INDEX idx_issue_labels_label ON issue_labels(label_id);

-- Issue Components (many-to-many)
CREATE TABLE IF NOT EXISTS issue_components (
    id SERIAL PRIMARY KEY,
    issue_id INTEGER NOT NULL REFERENCES jira_issues(id) ON DELETE CASCADE,
    component_id INTEGER NOT NULL REFERENCES jira_components(id) ON DELETE CASCADE,
    UNIQUE(issue_id, component_id)
);

CREATE INDEX idx_issue_components_issue ON issue_components(issue_id);
CREATE INDEX idx_issue_components_component ON issue_components(component_id);

-- Issue Fix Versions (many-to-many)
CREATE TABLE IF NOT EXISTS issue_fix_versions (
    id SERIAL PRIMARY KEY,
    issue_id INTEGER NOT NULL REFERENCES jira_issues(id) ON DELETE CASCADE,
    version_id INTEGER NOT NULL REFERENCES jira_versions(id) ON DELETE CASCADE,
    UNIQUE(issue_id, version_id)
);

CREATE INDEX idx_issue_fix_versions_issue ON issue_fix_versions(issue_id);
CREATE INDEX idx_issue_fix_versions_version ON issue_fix_versions(version_id);

-- Issue Affects Versions (many-to-many)
CREATE TABLE IF NOT EXISTS issue_affects_versions (
    id SERIAL PRIMARY KEY,
    issue_id INTEGER NOT NULL REFERENCES jira_issues(id) ON DELETE CASCADE,
    version_id INTEGER NOT NULL REFERENCES jira_versions(id) ON DELETE CASCADE,
    UNIQUE(issue_id, version_id)
);

CREATE INDEX idx_issue_affects_versions_issue ON issue_affects_versions(issue_id);

-- Issue Watchers (many-to-many)
CREATE TABLE IF NOT EXISTS issue_watchers (
    id SERIAL PRIMARY KEY,
    issue_id INTEGER NOT NULL REFERENCES jira_issues(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES jira_users(id) ON DELETE CASCADE,
    UNIQUE(issue_id, user_id)
);

CREATE INDEX idx_issue_watchers_issue ON issue_watchers(issue_id);

-- Issue Links
CREATE TABLE IF NOT EXISTS issue_links (
    id SERIAL PRIMARY KEY,
    jira_id VARCHAR(50) NOT NULL UNIQUE,
    link_type_id INTEGER NOT NULL REFERENCES jira_issue_link_types(id),
    inward_issue_id INTEGER NOT NULL REFERENCES jira_issues(id) ON DELETE CASCADE,
    outward_issue_id INTEGER NOT NULL REFERENCES jira_issues(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_issue_links_inward ON issue_links(inward_issue_id);
CREATE INDEX idx_issue_links_outward ON issue_links(outward_issue_id);

-- ============================================
-- ACTIVITY TABLES
-- ============================================

-- Issue Comments
CREATE TABLE IF NOT EXISTS issue_comments (
    id SERIAL PRIMARY KEY,
    jira_id VARCHAR(50) NOT NULL UNIQUE,
    issue_id INTEGER NOT NULL REFERENCES jira_issues(id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES jira_users(id),
    body TEXT,
    created_date TIMESTAMP NOT NULL,
    updated_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_issue_comments_issue ON issue_comments(issue_id);
CREATE INDEX idx_issue_comments_author ON issue_comments(author_id);
CREATE INDEX idx_issue_comments_date ON issue_comments(created_date);

-- Issue Worklogs
CREATE TABLE IF NOT EXISTS issue_worklogs (
    id SERIAL PRIMARY KEY,
    jira_id VARCHAR(50) NOT NULL UNIQUE,
    issue_id INTEGER NOT NULL REFERENCES jira_issues(id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES jira_users(id),
    time_spent INTEGER NOT NULL,  -- seconds
    started TIMESTAMP NOT NULL,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_issue_worklogs_issue ON issue_worklogs(issue_id);
CREATE INDEX idx_issue_worklogs_author ON issue_worklogs(author_id);
CREATE INDEX idx_issue_worklogs_started ON issue_worklogs(started);

-- Issue Attachments
CREATE TABLE IF NOT EXISTS issue_attachments (
    id SERIAL PRIMARY KEY,
    jira_id VARCHAR(50) NOT NULL UNIQUE,
    issue_id INTEGER NOT NULL REFERENCES jira_issues(id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES jira_users(id),
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(255),
    size INTEGER,  -- bytes
    content_url TEXT,
    thumbnail_url TEXT,
    created_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_issue_attachments_issue ON issue_attachments(issue_id);

-- Issue Transitions (Status Changes)
CREATE TABLE IF NOT EXISTS issue_transitions (
    id SERIAL PRIMARY KEY,
    issue_id INTEGER NOT NULL REFERENCES jira_issues(id) ON DELETE CASCADE,
    from_status_id INTEGER REFERENCES jira_statuses(id),
    to_status_id INTEGER REFERENCES jira_statuses(id),
    author_id INTEGER REFERENCES jira_users(id),
    transition_date TIMESTAMP NOT NULL,
    duration_seconds INTEGER,  -- time in previous status
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_issue_transitions_issue ON issue_transitions(issue_id);
CREATE INDEX idx_issue_transitions_date ON issue_transitions(transition_date);
CREATE INDEX idx_issue_transitions_to_status ON issue_transitions(to_status_id);

-- Issue Changelog (Full History)
CREATE TABLE IF NOT EXISTS issue_changelog (
    id SERIAL PRIMARY KEY,
    jira_id VARCHAR(50) NOT NULL,
    issue_id INTEGER NOT NULL REFERENCES jira_issues(id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES jira_users(id),
    field_name VARCHAR(255) NOT NULL,
    field_type VARCHAR(100),
    from_value TEXT,
    from_string TEXT,
    to_value TEXT,
    to_string TEXT,
    change_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_issue_changelog_issue ON issue_changelog(issue_id);
CREATE INDEX idx_issue_changelog_field ON issue_changelog(field_name);
CREATE INDEX idx_issue_changelog_date ON issue_changelog(change_date);

-- Custom Fields (JSON storage for flexibility)
CREATE TABLE IF NOT EXISTS issue_custom_fields (
    id SERIAL PRIMARY KEY,
    issue_id INTEGER NOT NULL REFERENCES jira_issues(id) ON DELETE CASCADE,
    field_id VARCHAR(100) NOT NULL,
    field_name VARCHAR(255),
    field_type VARCHAR(100),
    value JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(issue_id, field_id)
);

CREATE INDEX idx_issue_custom_fields_issue ON issue_custom_fields(issue_id);
CREATE INDEX idx_issue_custom_fields_field ON issue_custom_fields(field_id);
CREATE INDEX idx_issue_custom_fields_value ON issue_custom_fields USING GIN(value);

-- ============================================
-- METRICS TABLES
-- ============================================

-- Daily Metrics (Pre-calculated)
CREATE TABLE IF NOT EXISTS daily_metrics (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id),
    project_id INTEGER REFERENCES jira_projects(id),
    metric_date DATE NOT NULL,
    
    -- Issue counts
    tickets_created INTEGER DEFAULT 0,
    tickets_resolved INTEGER DEFAULT 0,
    tickets_updated INTEGER DEFAULT 0,
    backlog_count INTEGER DEFAULT 0,
    
    -- Time metrics (in hours)
    avg_resolution_time DECIMAL(10, 2),
    avg_cycle_time DECIMAL(10, 2),
    avg_lead_time DECIMAL(10, 2),
    
    -- Story points
    points_committed DECIMAL(10, 2),
    points_completed DECIMAL(10, 2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(team_id, project_id, metric_date)
);

CREATE INDEX idx_daily_metrics_date ON daily_metrics(metric_date);
CREATE INDEX idx_daily_metrics_team ON daily_metrics(team_id);
CREATE INDEX idx_daily_metrics_project ON daily_metrics(project_id);

-- Sprint Metrics
CREATE TABLE IF NOT EXISTS sprint_metrics (
    id SERIAL PRIMARY KEY,
    sprint_id INTEGER NOT NULL REFERENCES jira_sprints(id) ON DELETE CASCADE,
    
    -- Commitment
    issues_committed INTEGER DEFAULT 0,
    points_committed DECIMAL(10, 2) DEFAULT 0,
    
    -- Completion
    issues_completed INTEGER DEFAULT 0,
    points_completed DECIMAL(10, 2) DEFAULT 0,
    
    -- Additional
    issues_added INTEGER DEFAULT 0,
    issues_removed INTEGER DEFAULT 0,
    
    -- Velocity
    velocity DECIMAL(10, 2),
    completion_rate DECIMAL(5, 2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sprint_id)
);

CREATE INDEX idx_sprint_metrics_sprint ON sprint_metrics(sprint_id);

-- ETL Run Tracking
CREATE TABLE IF NOT EXISTS etl_runs (
    id SERIAL PRIMARY KEY,
    run_type VARCHAR(50) NOT NULL,  -- 'full', 'incremental'
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'running',  -- 'running', 'completed', 'failed'
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    error_message TEXT,
    last_sync_timestamp TIMESTAMP
);

CREATE INDEX idx_etl_runs_status ON etl_runs(status);
CREATE INDEX idx_etl_runs_started ON etl_runs(started_at);

-- ============================================
-- FUNCTIONS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to tables with updated_at
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON teams FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_jira_users_updated_at BEFORE UPDATE ON jira_users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_jira_projects_updated_at BEFORE UPDATE ON jira_projects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_jira_boards_updated_at BEFORE UPDATE ON jira_boards FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_jira_sprints_updated_at BEFORE UPDATE ON jira_sprints FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_jira_issues_updated_at BEFORE UPDATE ON jira_issues FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_issue_custom_fields_updated_at BEFORE UPDATE ON issue_custom_fields FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_sprint_metrics_updated_at BEFORE UPDATE ON sprint_metrics FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
