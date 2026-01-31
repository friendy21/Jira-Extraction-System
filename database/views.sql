-- Jira MCP System - PostgreSQL Views for Reporting
-- Run this script after schema.sql

-- ============================================
-- VELOCITY & SPRINT VIEWS
-- ============================================

-- Team Velocity View
CREATE OR REPLACE VIEW vw_team_velocity AS
SELECT 
    t.id AS team_id,
    t.team_name,
    o.name AS organization,
    s.id AS sprint_id,
    s.name AS sprint_name,
    s.start_date,
    s.end_date,
    COALESCE(sm.points_committed, 0) AS points_committed,
    COALESCE(sm.points_completed, 0) AS points_completed,
    COALESCE(sm.issues_committed, 0) AS issues_committed,
    COALESCE(sm.issues_completed, 0) AS issues_completed,
    COALESCE(sm.velocity, 0) AS velocity,
    COALESCE(sm.completion_rate, 0) AS completion_rate
FROM teams t
JOIN organizations o ON t.org_id = o.id
JOIN jira_projects p ON p.team_id = t.id
JOIN jira_boards b ON b.project_id = p.id
JOIN jira_sprints s ON s.board_id = b.id
LEFT JOIN sprint_metrics sm ON sm.sprint_id = s.id
WHERE s.state = 'closed'
ORDER BY t.id, s.end_date DESC;

-- Sprint Metrics View (detailed)
CREATE OR REPLACE VIEW vw_sprint_metrics AS
SELECT 
    s.id AS sprint_id,
    s.jira_id AS jira_sprint_id,
    s.name AS sprint_name,
    s.state,
    s.start_date,
    s.end_date,
    s.complete_date,
    s.goal,
    b.name AS board_name,
    b.board_type,
    p.project_key,
    p.project_name,
    t.team_name,
    o.name AS organization,
    -- Issue counts
    COUNT(DISTINCT i.id) AS total_issues,
    COUNT(DISTINCT CASE WHEN st.name IN ('Done', 'Closed', 'Resolved') THEN i.id END) AS completed_issues,
    COUNT(DISTINCT CASE WHEN st.name NOT IN ('Done', 'Closed', 'Resolved') THEN i.id END) AS incomplete_issues,
    -- Story points
    COALESCE(SUM(i.story_points), 0) AS total_points,
    COALESCE(SUM(CASE WHEN st.name IN ('Done', 'Closed', 'Resolved') THEN i.story_points ELSE 0 END), 0) AS completed_points,
    -- Completion rate
    CASE 
        WHEN COUNT(DISTINCT i.id) > 0 
        THEN ROUND(100.0 * COUNT(DISTINCT CASE WHEN st.name IN ('Done', 'Closed', 'Resolved') THEN i.id END) / COUNT(DISTINCT i.id), 2)
        ELSE 0 
    END AS completion_percentage
FROM jira_sprints s
JOIN jira_boards b ON s.board_id = b.id
LEFT JOIN jira_projects p ON b.project_id = p.id
LEFT JOIN teams t ON p.team_id = t.id
LEFT JOIN organizations o ON t.org_id = o.id
LEFT JOIN jira_issues i ON i.sprint_id = s.id
LEFT JOIN jira_statuses st ON i.status_id = st.id
GROUP BY s.id, s.jira_id, s.name, s.state, s.start_date, s.end_date, s.complete_date, s.goal,
         b.name, b.board_type, p.project_key, p.project_name, t.team_name, o.name
ORDER BY s.start_date DESC;

-- ============================================
-- TICKET AGING & BACKLOG VIEWS
-- ============================================

-- Ticket Aging View
CREATE OR REPLACE VIEW vw_ticket_aging AS
SELECT 
    i.id AS issue_id,
    i.issue_key,
    i.summary,
    p.project_key,
    p.project_name,
    t.team_name,
    o.name AS organization,
    it.name AS issue_type,
    pr.name AS priority,
    st.name AS status,
    u.display_name AS assignee,
    i.created_date,
    i.updated_date,
    -- Age calculations
    EXTRACT(DAY FROM (CURRENT_TIMESTAMP - i.created_date)) AS age_days,
    EXTRACT(DAY FROM (CURRENT_TIMESTAMP - i.updated_date)) AS days_since_update,
    -- Age buckets
    CASE 
        WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - i.created_date)) <= 7 THEN '0-7 days'
        WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - i.created_date)) <= 14 THEN '8-14 days'
        WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - i.created_date)) <= 30 THEN '15-30 days'
        WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - i.created_date)) <= 60 THEN '31-60 days'
        WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - i.created_date)) <= 90 THEN '61-90 days'
        ELSE '90+ days'
    END AS age_bucket
FROM jira_issues i
JOIN jira_projects p ON i.project_id = p.id
LEFT JOIN teams t ON p.team_id = t.id
LEFT JOIN organizations o ON t.org_id = o.id
LEFT JOIN jira_issue_types it ON i.issue_type_id = it.id
LEFT JOIN jira_priorities pr ON i.priority_id = pr.id
LEFT JOIN jira_statuses st ON i.status_id = st.id
LEFT JOIN jira_users u ON i.assignee_id = u.id
WHERE i.resolution_id IS NULL
ORDER BY i.created_date ASC;

-- ============================================
-- KANBAN & FLOW VIEWS
-- ============================================

-- Kanban Flow Metrics View
CREATE OR REPLACE VIEW vw_kanban_flow AS
SELECT 
    b.id AS board_id,
    b.name AS board_name,
    p.project_key,
    t.team_name,
    o.name AS organization,
    st.name AS status,
    sc.name AS status_category,
    COUNT(DISTINCT i.id) AS issue_count,
    COALESCE(SUM(i.story_points), 0) AS total_points,
    -- WIP count (In Progress items)
    SUM(CASE WHEN sc.key = 'indeterminate' THEN 1 ELSE 0 END) AS wip_count
FROM jira_boards b
JOIN jira_projects p ON b.project_id = p.id
LEFT JOIN teams t ON p.team_id = t.id
LEFT JOIN organizations o ON t.org_id = o.id
LEFT JOIN jira_issues i ON i.project_id = p.id AND i.resolution_id IS NULL
LEFT JOIN jira_statuses st ON i.status_id = st.id
LEFT JOIN jira_status_categories sc ON st.category_id = sc.id
WHERE b.board_type = 'kanban'
GROUP BY b.id, b.name, p.project_key, t.team_name, o.name, st.name, sc.name
ORDER BY b.name, sc.id, st.name;

-- Cycle Time View
CREATE OR REPLACE VIEW vw_cycle_time AS
SELECT 
    i.id AS issue_id,
    i.issue_key,
    i.summary,
    p.project_key,
    t.team_name,
    it.name AS issue_type,
    pr.name AS priority,
    i.created_date,
    i.resolution_date,
    -- Cycle time in hours (from creation to resolution)
    CASE 
        WHEN i.resolution_date IS NOT NULL 
        THEN ROUND(EXTRACT(EPOCH FROM (i.resolution_date - i.created_date)) / 3600, 2)
        ELSE NULL 
    END AS cycle_time_hours,
    -- Cycle time in days
    CASE 
        WHEN i.resolution_date IS NOT NULL 
        THEN ROUND(EXTRACT(DAY FROM (i.resolution_date - i.created_date)), 2)
        ELSE NULL 
    END AS cycle_time_days
FROM jira_issues i
JOIN jira_projects p ON i.project_id = p.id
LEFT JOIN teams t ON p.team_id = t.id
LEFT JOIN jira_issue_types it ON i.issue_type_id = it.id
LEFT JOIN jira_priorities pr ON i.priority_id = pr.id
WHERE i.resolution_date IS NOT NULL
ORDER BY i.resolution_date DESC;

-- Lead Time View (first status change to resolution)
CREATE OR REPLACE VIEW vw_lead_time AS
SELECT 
    i.id AS issue_id,
    i.issue_key,
    i.summary,
    p.project_key,
    t.team_name,
    i.created_date,
    MIN(tr.transition_date) AS first_transition_date,
    i.resolution_date,
    -- Lead time in hours (from first transition to resolution)
    CASE 
        WHEN i.resolution_date IS NOT NULL AND MIN(tr.transition_date) IS NOT NULL
        THEN ROUND(EXTRACT(EPOCH FROM (i.resolution_date - MIN(tr.transition_date))) / 3600, 2)
        ELSE NULL 
    END AS lead_time_hours
FROM jira_issues i
JOIN jira_projects p ON i.project_id = p.id
LEFT JOIN teams t ON p.team_id = t.id
LEFT JOIN issue_transitions tr ON tr.issue_id = i.id
WHERE i.resolution_date IS NOT NULL
GROUP BY i.id, i.issue_key, i.summary, p.project_key, t.team_name, i.created_date, i.resolution_date
ORDER BY i.resolution_date DESC;

-- ============================================
-- PRIORITY & DISTRIBUTION VIEWS
-- ============================================

-- Priority Distribution View
CREATE OR REPLACE VIEW vw_priority_distribution AS
SELECT 
    t.id AS team_id,
    t.team_name,
    o.name AS organization,
    p.project_key,
    pr.name AS priority,
    pr.sort_order AS priority_order,
    COUNT(DISTINCT i.id) AS issue_count,
    COUNT(DISTINCT CASE WHEN i.resolution_id IS NULL THEN i.id END) AS open_count,
    COUNT(DISTINCT CASE WHEN i.resolution_id IS NOT NULL THEN i.id END) AS resolved_count,
    COALESCE(SUM(i.story_points), 0) AS total_points
FROM teams t
JOIN organizations o ON t.org_id = o.id
JOIN jira_projects p ON p.team_id = t.id
JOIN jira_issues i ON i.project_id = p.id
LEFT JOIN jira_priorities pr ON i.priority_id = pr.id
GROUP BY t.id, t.team_name, o.name, p.project_key, pr.name, pr.sort_order
ORDER BY t.team_name, pr.sort_order;

-- Label Analysis View
CREATE OR REPLACE VIEW vw_label_analysis AS
SELECT 
    l.id AS label_id,
    l.name AS label_name,
    p.project_key,
    t.team_name,
    o.name AS organization,
    COUNT(DISTINCT il.issue_id) AS issue_count,
    COUNT(DISTINCT CASE WHEN i.resolution_id IS NULL THEN il.issue_id END) AS open_count,
    COUNT(DISTINCT CASE WHEN i.resolution_id IS NOT NULL THEN il.issue_id END) AS resolved_count
FROM jira_labels l
JOIN issue_labels il ON il.label_id = l.id
JOIN jira_issues i ON il.issue_id = i.id
JOIN jira_projects p ON i.project_id = p.id
LEFT JOIN teams t ON p.team_id = t.id
LEFT JOIN organizations o ON t.org_id = o.id
GROUP BY l.id, l.name, p.project_key, t.team_name, o.name
ORDER BY issue_count DESC;

-- Swimlane Workload View
CREATE OR REPLACE VIEW vw_swimlane_workload AS
SELECT 
    sw.id AS swimlane_id,
    sw.name AS swimlane_name,
    sw.swimlane_type,
    b.name AS board_name,
    b.board_type,
    p.project_key,
    t.team_name,
    COUNT(DISTINCT i.id) AS issue_count,
    COALESCE(SUM(i.story_points), 0) AS total_points,
    COUNT(DISTINCT CASE WHEN i.resolution_id IS NULL THEN i.id END) AS open_issues
FROM jira_swimlanes sw
JOIN jira_boards b ON sw.board_id = b.id
JOIN jira_projects p ON b.project_id = p.id
LEFT JOIN teams t ON p.team_id = t.id
LEFT JOIN jira_issues i ON i.project_id = p.id AND i.resolution_id IS NULL
GROUP BY sw.id, sw.name, sw.swimlane_type, b.name, b.board_type, p.project_key, t.team_name
ORDER BY b.name, sw.position;

-- ============================================
-- COMPONENT & VERSION VIEWS
-- ============================================

-- Component Workload View
CREATE OR REPLACE VIEW vw_component_workload AS
SELECT 
    c.id AS component_id,
    c.name AS component_name,
    p.project_key,
    t.team_name,
    o.name AS organization,
    u.display_name AS component_lead,
    COUNT(DISTINCT ic.issue_id) AS issue_count,
    COUNT(DISTINCT CASE WHEN i.resolution_id IS NULL THEN ic.issue_id END) AS open_count,
    COUNT(DISTINCT CASE WHEN i.resolution_id IS NOT NULL THEN ic.issue_id END) AS resolved_count,
    COALESCE(SUM(i.story_points), 0) AS total_points
FROM jira_components c
JOIN jira_projects p ON c.project_id = p.id
LEFT JOIN teams t ON p.team_id = t.id
LEFT JOIN organizations o ON t.org_id = o.id
LEFT JOIN jira_users u ON c.lead_id = u.id
LEFT JOIN issue_components ic ON ic.component_id = c.id
LEFT JOIN jira_issues i ON ic.issue_id = i.id
GROUP BY c.id, c.name, p.project_key, t.team_name, o.name, u.display_name
ORDER BY issue_count DESC;

-- Version Progress View
CREATE OR REPLACE VIEW vw_version_progress AS
SELECT 
    v.id AS version_id,
    v.name AS version_name,
    p.project_key,
    t.team_name,
    v.start_date,
    v.release_date,
    v.released,
    v.archived,
    v.overdue,
    COUNT(DISTINCT ifv.issue_id) AS total_issues,
    COUNT(DISTINCT CASE WHEN i.resolution_id IS NOT NULL THEN ifv.issue_id END) AS completed_issues,
    COUNT(DISTINCT CASE WHEN i.resolution_id IS NULL THEN ifv.issue_id END) AS remaining_issues,
    COALESCE(SUM(i.story_points), 0) AS total_points,
    COALESCE(SUM(CASE WHEN i.resolution_id IS NOT NULL THEN i.story_points ELSE 0 END), 0) AS completed_points,
    -- Progress percentage
    CASE 
        WHEN COUNT(DISTINCT ifv.issue_id) > 0 
        THEN ROUND(100.0 * COUNT(DISTINCT CASE WHEN i.resolution_id IS NOT NULL THEN ifv.issue_id END) / COUNT(DISTINCT ifv.issue_id), 2)
        ELSE 0 
    END AS progress_percentage
FROM jira_versions v
JOIN jira_projects p ON v.project_id = p.id
LEFT JOIN teams t ON p.team_id = t.id
LEFT JOIN issue_fix_versions ifv ON ifv.version_id = v.id
LEFT JOIN jira_issues i ON ifv.issue_id = i.id
GROUP BY v.id, v.name, p.project_key, t.team_name, v.start_date, v.release_date, v.released, v.archived, v.overdue
ORDER BY v.release_date DESC NULLS LAST;

-- ============================================
-- ASSIGNEE & WORKLOAD VIEWS
-- ============================================

-- Assignee Workload View
CREATE OR REPLACE VIEW vw_assignee_workload AS
SELECT 
    u.id AS user_id,
    u.display_name AS assignee,
    u.email_address,
    t.team_name,
    o.name AS organization,
    p.project_key,
    -- Issue counts
    COUNT(DISTINCT i.id) AS total_assigned,
    COUNT(DISTINCT CASE WHEN i.resolution_id IS NULL THEN i.id END) AS open_issues,
    COUNT(DISTINCT CASE WHEN i.resolution_id IS NOT NULL THEN i.id END) AS resolved_issues,
    -- Story points
    COALESCE(SUM(CASE WHEN i.resolution_id IS NULL THEN i.story_points ELSE 0 END), 0) AS open_points,
    COALESCE(SUM(CASE WHEN i.resolution_id IS NOT NULL THEN i.story_points ELSE 0 END), 0) AS completed_points,
    -- By priority
    COUNT(DISTINCT CASE WHEN pr.name IN ('Highest', 'High') AND i.resolution_id IS NULL THEN i.id END) AS high_priority_open
FROM jira_users u
JOIN jira_issues i ON i.assignee_id = u.id
JOIN jira_projects p ON i.project_id = p.id
LEFT JOIN teams t ON p.team_id = t.id
LEFT JOIN organizations o ON t.org_id = o.id
LEFT JOIN jira_priorities pr ON i.priority_id = pr.id
GROUP BY u.id, u.display_name, u.email_address, t.team_name, o.name, p.project_key
ORDER BY open_issues DESC;

-- ============================================
-- ISSUE TYPE & RESOLUTION VIEWS
-- ============================================

-- Issue Type Distribution View
CREATE OR REPLACE VIEW vw_issue_type_distribution AS
SELECT 
    t.id AS team_id,
    t.team_name,
    o.name AS organization,
    p.project_key,
    it.name AS issue_type,
    it.subtask AS is_subtask,
    COUNT(DISTINCT i.id) AS issue_count,
    COUNT(DISTINCT CASE WHEN i.resolution_id IS NULL THEN i.id END) AS open_count,
    COUNT(DISTINCT CASE WHEN i.resolution_id IS NOT NULL THEN i.id END) AS resolved_count,
    COALESCE(SUM(i.story_points), 0) AS total_points
FROM teams t
JOIN organizations o ON t.org_id = o.id
JOIN jira_projects p ON p.team_id = t.id
JOIN jira_issues i ON i.project_id = p.id
LEFT JOIN jira_issue_types it ON i.issue_type_id = it.id
GROUP BY t.id, t.team_name, o.name, p.project_key, it.name, it.subtask
ORDER BY t.team_name, issue_count DESC;

-- Resolution Analysis View
CREATE OR REPLACE VIEW vw_resolution_analysis AS
SELECT 
    t.team_name,
    o.name AS organization,
    p.project_key,
    r.name AS resolution,
    COUNT(DISTINCT i.id) AS issue_count,
    -- Average resolution time in days
    ROUND(AVG(EXTRACT(DAY FROM (i.resolution_date - i.created_date))), 2) AS avg_resolution_days
FROM jira_issues i
JOIN jira_projects p ON i.project_id = p.id
LEFT JOIN teams t ON p.team_id = t.id
LEFT JOIN organizations o ON t.org_id = o.id
JOIN jira_resolutions r ON i.resolution_id = r.id
GROUP BY t.team_name, o.name, p.project_key, r.name
ORDER BY issue_count DESC;

-- ============================================
-- TIME TRACKING VIEW
-- ============================================

-- Time Tracking View
CREATE OR REPLACE VIEW vw_time_tracking AS
SELECT 
    i.id AS issue_id,
    i.issue_key,
    i.summary,
    p.project_key,
    t.team_name,
    u.display_name AS assignee,
    -- Time estimates (in hours)
    ROUND(COALESCE(i.original_estimate, 0) / 3600.0, 2) AS original_estimate_hours,
    ROUND(COALESCE(i.remaining_estimate, 0) / 3600.0, 2) AS remaining_estimate_hours,
    ROUND(COALESCE(i.time_spent, 0) / 3600.0, 2) AS time_spent_hours,
    -- Logged time from worklogs
    ROUND(COALESCE(SUM(w.time_spent), 0) / 3600.0, 2) AS worklog_hours,
    -- Variance
    CASE 
        WHEN i.original_estimate > 0 
        THEN ROUND((COALESCE(i.time_spent, 0) - i.original_estimate) / 3600.0, 2)
        ELSE NULL 
    END AS variance_hours,
    -- Accuracy percentage
    CASE 
        WHEN i.original_estimate > 0 AND i.time_spent > 0
        THEN ROUND(100.0 * i.time_spent / i.original_estimate, 2)
        ELSE NULL 
    END AS accuracy_percentage
FROM jira_issues i
JOIN jira_projects p ON i.project_id = p.id
LEFT JOIN teams t ON p.team_id = t.id
LEFT JOIN jira_users u ON i.assignee_id = u.id
LEFT JOIN issue_worklogs w ON w.issue_id = i.id
WHERE i.original_estimate > 0 OR i.time_spent > 0
GROUP BY i.id, i.issue_key, i.summary, p.project_key, t.team_name, u.display_name,
         i.original_estimate, i.remaining_estimate, i.time_spent
ORDER BY i.updated_date DESC;
