"""
SQLAlchemy ORM Models
Defines all database models for the Jira MCP system.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey,
    Integer, String, Text, UniqueConstraint, Index, Float
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


# ============================================
# REFERENCE DATA MODELS
# ============================================

class Organization(Base):
    """Organization model (top-level grouping)."""
    __tablename__ = 'organizations'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    teams = relationship("Team", back_populates="organization", cascade="all, delete-orphan")


class Team(Base):
    """Team model."""
    __tablename__ = 'teams'
    
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    team_code = Column(String(50), nullable=False)
    team_name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('org_id', 'team_code', name='uq_team_org_code'),
    )
    
    # Relationships
    organization = relationship("Organization", back_populates="teams")
    projects = relationship("JiraProject", back_populates="team")


class JiraUser(Base):
    """Jira user model."""
    __tablename__ = 'jira_users'
    
    id = Column(Integer, primary_key=True)
    account_id = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255))
    email_address = Column(String(255))
    active = Column(Boolean, default=True)
    timezone = Column(String(100))
    avatar_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class JiraProjectCategory(Base):
    """Project category model."""
    __tablename__ = 'jira_project_categories'
    
    id = Column(Integer, primary_key=True)
    jira_id = Column(String(50), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class JiraStatusCategory(Base):
    """Status category model."""
    __tablename__ = 'jira_status_categories'
    
    id = Column(Integer, primary_key=True)
    jira_id = Column(Integer, nullable=False, unique=True)
    key = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    color_name = Column(String(50))
    
    # Relationships
    statuses = relationship("JiraStatus", back_populates="category")


class JiraStatus(Base):
    """Jira status model."""
    __tablename__ = 'jira_statuses'
    
    id = Column(Integer, primary_key=True)
    jira_id = Column(String(50), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category_id = Column(Integer, ForeignKey('jira_status_categories.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    category = relationship("JiraStatusCategory", back_populates="statuses")


class JiraPriority(Base):
    """Jira priority model."""
    __tablename__ = 'jira_priorities'
    
    id = Column(Integer, primary_key=True)
    jira_id = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    icon_url = Column(Text)
    status_color = Column(String(50))
    sort_order = Column(Integer, default=0)


class JiraIssueType(Base):
    """Jira issue type model."""
    __tablename__ = 'jira_issue_types'
    
    id = Column(Integer, primary_key=True)
    jira_id = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    icon_url = Column(Text)
    subtask = Column(Boolean, default=False)
    hierarchy_level = Column(Integer, default=0)


class JiraResolution(Base):
    """Jira resolution model."""
    __tablename__ = 'jira_resolutions'
    
    id = Column(Integer, primary_key=True)
    jira_id = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)


class JiraIssueLinkType(Base):
    """Issue link type model."""
    __tablename__ = 'jira_issue_link_types'
    
    id = Column(Integer, primary_key=True)
    jira_id = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    inward = Column(String(255))
    outward = Column(String(255))


class JiraLabel(Base):
    """Jira label model."""
    __tablename__ = 'jira_labels'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    issues = relationship("IssueLabel", back_populates="label")


# ============================================
# PROJECT-LEVEL MODELS
# ============================================

class JiraProject(Base):
    """Jira project model."""
    __tablename__ = 'jira_projects'
    
    id = Column(Integer, primary_key=True)
    jira_id = Column(String(50), nullable=False, unique=True)
    project_key = Column(String(50), nullable=False, unique=True)
    project_name = Column(String(255), nullable=False)
    description = Column(Text)
    project_type = Column(String(100))
    style = Column(String(50))
    lead_id = Column(Integer, ForeignKey('jira_users.id'))
    category_id = Column(Integer, ForeignKey('jira_project_categories.id'))
    team_id = Column(Integer, ForeignKey('teams.id'))
    url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    team = relationship("Team", back_populates="projects")
    lead = relationship("JiraUser")
    category = relationship("JiraProjectCategory")
    issues = relationship("JiraIssue", back_populates="project", cascade="all, delete-orphan")
    components = relationship("JiraComponent", back_populates="project", cascade="all, delete-orphan")
    versions = relationship("JiraVersion", back_populates="project", cascade="all, delete-orphan")
    boards = relationship("JiraBoard", back_populates="project")


class JiraComponent(Base):
    """Jira component model."""
    __tablename__ = 'jira_components'
    
    id = Column(Integer, primary_key=True)
    jira_id = Column(String(50), nullable=False, unique=True)
    project_id = Column(Integer, ForeignKey('jira_projects.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    lead_id = Column(Integer, ForeignKey('jira_users.id'))
    assignee_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("JiraProject", back_populates="components")
    lead = relationship("JiraUser")


class JiraVersion(Base):
    """Jira version/release model."""
    __tablename__ = 'jira_versions'
    
    id = Column(Integer, primary_key=True)
    jira_id = Column(String(50), nullable=False, unique=True)
    project_id = Column(Integer, ForeignKey('jira_projects.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    archived = Column(Boolean, default=False)
    released = Column(Boolean, default=False)
    start_date = Column(Date)
    release_date = Column(Date)
    overdue = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("JiraProject", back_populates="versions")


class JiraBoard(Base):
    """Jira board model (Scrum/Kanban)."""
    __tablename__ = 'jira_boards'
    
    id = Column(Integer, primary_key=True)
    jira_id = Column(Integer, nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    board_type = Column(String(50), nullable=False)  # 'scrum' or 'kanban'
    project_id = Column(Integer, ForeignKey('jira_projects.id'))
    filter_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("JiraProject", back_populates="boards")
    swimlanes = relationship("JiraSwimlane", back_populates="board", cascade="all, delete-orphan")
    sprints = relationship("JiraSprint", back_populates="board")


class JiraSwimlane(Base):
    """Jira swimlane model."""
    __tablename__ = 'jira_swimlanes'
    
    id = Column(Integer, primary_key=True)
    board_id = Column(Integer, ForeignKey('jira_boards.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    swimlane_type = Column(String(50))
    query = Column(Text)
    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    board = relationship("JiraBoard", back_populates="swimlanes")


class JiraSprint(Base):
    """Jira sprint model."""
    __tablename__ = 'jira_sprints'
    
    id = Column(Integer, primary_key=True)
    jira_id = Column(Integer, nullable=False, unique=True)
    board_id = Column(Integer, ForeignKey('jira_boards.id'))
    name = Column(String(255), nullable=False)
    state = Column(String(50))  # 'active', 'closed', 'future'
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    complete_date = Column(DateTime)
    goal = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    board = relationship("JiraBoard", back_populates="sprints")
    issues = relationship("JiraIssue", back_populates="sprint")
    metrics = relationship("SprintMetric", back_populates="sprint", uselist=False)


# ============================================
# ISSUE MODELS
# ============================================

class JiraIssue(Base):
    """Main Jira issue model."""
    __tablename__ = 'jira_issues'
    
    id = Column(Integer, primary_key=True)
    jira_id = Column(String(50), nullable=False, unique=True)
    issue_key = Column(String(50), nullable=False, unique=True)
    project_id = Column(Integer, ForeignKey('jira_projects.id'), nullable=False)
    parent_issue_id = Column(Integer, ForeignKey('jira_issues.id'))
    
    # Core fields
    summary = Column(Text, nullable=False)
    description = Column(Text)
    environment = Column(Text)
    
    # Type and status
    issue_type_id = Column(Integer, ForeignKey('jira_issue_types.id'))
    status_id = Column(Integer, ForeignKey('jira_statuses.id'))
    priority_id = Column(Integer, ForeignKey('jira_priorities.id'))
    resolution_id = Column(Integer, ForeignKey('jira_resolutions.id'))
    
    # People
    assignee_id = Column(Integer, ForeignKey('jira_users.id'))
    reporter_id = Column(Integer, ForeignKey('jira_users.id'))
    creator_id = Column(Integer, ForeignKey('jira_users.id'))
    
    # Epic/Sprint
    sprint_id = Column(Integer, ForeignKey('jira_sprints.id'))
    epic_key = Column(String(50))
    epic_name = Column(String(255))
    
    # Time tracking
    story_points = Column(Float)
    original_estimate = Column(Integer)  # seconds
    remaining_estimate = Column(Integer)  # seconds
    time_spent = Column(Integer)  # seconds
    
    # Dates
    created_date = Column(DateTime, nullable=False)
    updated_date = Column(DateTime, nullable=False)
    resolution_date = Column(DateTime)
    due_date = Column(Date)
    
    # Metrics
    votes = Column(Integer, default=0)
    watches = Column(Integer, default=0)
    
    # Additional
    security_level = Column(String(255))
    subtask_count = Column(Integer, default=0)
    
    # SLA tracking
    first_response_date = Column(DateTime)
    sla_breached = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("JiraProject", back_populates="issues")
    # parent = relationship("JiraIssue", remote_side="[JiraIssue.id]", backref="subtasks")
    issue_type = relationship("JiraIssueType")
    status = relationship("JiraStatus")
    priority = relationship("JiraPriority")
    resolution = relationship("JiraResolution")
    assignee = relationship("JiraUser", foreign_keys=[assignee_id])
    reporter = relationship("JiraUser", foreign_keys=[reporter_id])
    creator = relationship("JiraUser", foreign_keys=[creator_id])
    sprint = relationship("JiraSprint", back_populates="issues")
    
    labels = relationship("IssueLabel", back_populates="issue", cascade="all, delete-orphan")
    components = relationship("IssueComponent", back_populates="issue", cascade="all, delete-orphan")
    fix_versions = relationship("IssueFixVersion", back_populates="issue", cascade="all, delete-orphan")
    affects_versions = relationship("IssueAffectsVersion", back_populates="issue", cascade="all, delete-orphan")
    watchers = relationship("IssueWatcher", back_populates="issue", cascade="all, delete-orphan")
    comments = relationship("IssueComment", back_populates="issue", cascade="all, delete-orphan")
    worklogs = relationship("IssueWorklog", back_populates="issue", cascade="all, delete-orphan")
    attachments = relationship("IssueAttachment", back_populates="issue", cascade="all, delete-orphan")
    transitions = relationship("IssueTransition", back_populates="issue", cascade="all, delete-orphan")
    changelog = relationship("IssueChangelog", back_populates="issue", cascade="all, delete-orphan")
    custom_fields = relationship("IssueCustomField", back_populates="issue", cascade="all, delete-orphan")


# Many-to-Many Association Tables
class IssueLabel(Base):
    """Issue-Label association."""
    __tablename__ = 'issue_labels'
    
    id = Column(Integer, primary_key=True)
    issue_id = Column(Integer, ForeignKey('jira_issues.id', ondelete='CASCADE'), nullable=False)
    label_id = Column(Integer, ForeignKey('jira_labels.id', ondelete='CASCADE'), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('issue_id', 'label_id', name='uq_issue_label'),
    )
    
    issue = relationship("JiraIssue", back_populates="labels")
    label = relationship("JiraLabel", back_populates="issues")


class IssueComponent(Base):
    """Issue-Component association."""
    __tablename__ = 'issue_components'
    
    id = Column(Integer, primary_key=True)
    issue_id = Column(Integer, ForeignKey('jira_issues.id', ondelete='CASCADE'), nullable=False)
    component_id = Column(Integer, ForeignKey('jira_components.id', ondelete='CASCADE'), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('issue_id', 'component_id', name='uq_issue_component'),
    )
    
    issue = relationship("JiraIssue", back_populates="components")
    component = relationship("JiraComponent")


class IssueFixVersion(Base):
    """Issue-FixVersion association."""
    __tablename__ = 'issue_fix_versions'
    
    id = Column(Integer, primary_key=True)
    issue_id = Column(Integer, ForeignKey('jira_issues.id', ondelete='CASCADE'), nullable=False)
    version_id = Column(Integer, ForeignKey('jira_versions.id', ondelete='CASCADE'), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('issue_id', 'version_id', name='uq_issue_fix_version'),
    )
    
    issue = relationship("JiraIssue", back_populates="fix_versions")
    version = relationship("JiraVersion")


class IssueAffectsVersion(Base):
    """Issue-AffectsVersion association."""
    __tablename__ = 'issue_affects_versions'
    
    id = Column(Integer, primary_key=True)
    issue_id = Column(Integer, ForeignKey('jira_issues.id', ondelete='CASCADE'), nullable=False)
    version_id = Column(Integer, ForeignKey('jira_versions.id', ondelete='CASCADE'), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('issue_id', 'version_id', name='uq_issue_affects_version'),
    )
    
    issue = relationship("JiraIssue", back_populates="affects_versions")
    version = relationship("JiraVersion")


class IssueWatcher(Base):
    """Issue-Watcher association."""
    __tablename__ = 'issue_watchers'
    
    id = Column(Integer, primary_key=True)
    issue_id = Column(Integer, ForeignKey('jira_issues.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('jira_users.id', ondelete='CASCADE'), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('issue_id', 'user_id', name='uq_issue_watcher'),
    )
    
    issue = relationship("JiraIssue", back_populates="watchers")
    user = relationship("JiraUser")


class IssueLink(Base):
    """Issue link model."""
    __tablename__ = 'issue_links'
    
    id = Column(Integer, primary_key=True)
    jira_id = Column(String(50), nullable=False, unique=True)
    link_type_id = Column(Integer, ForeignKey('jira_issue_link_types.id'), nullable=False)
    inward_issue_id = Column(Integer, ForeignKey('jira_issues.id', ondelete='CASCADE'), nullable=False)
    outward_issue_id = Column(Integer, ForeignKey('jira_issues.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    link_type = relationship("JiraIssueLinkType")
    inward_issue = relationship("JiraIssue", foreign_keys=[inward_issue_id])
    outward_issue = relationship("JiraIssue", foreign_keys=[outward_issue_id])


# ============================================
# ACTIVITY MODELS
# ============================================

class IssueComment(Base):
    """Issue comment model."""
    __tablename__ = 'issue_comments'
    
    id = Column(Integer, primary_key=True)
    jira_id = Column(String(50), nullable=False, unique=True)
    issue_id = Column(Integer, ForeignKey('jira_issues.id', ondelete='CASCADE'), nullable=False)
    author_id = Column(Integer, ForeignKey('jira_users.id'))
    body = Column(Text)
    created_date = Column(DateTime, nullable=False)
    updated_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    issue = relationship("JiraIssue", back_populates="comments")
    author = relationship("JiraUser")


class IssueWorklog(Base):
    """Issue worklog model."""
    __tablename__ = 'issue_worklogs'
    
    id = Column(Integer, primary_key=True)
    jira_id = Column(String(50), nullable=False, unique=True)
    issue_id = Column(Integer, ForeignKey('jira_issues.id', ondelete='CASCADE'), nullable=False)
    author_id = Column(Integer, ForeignKey('jira_users.id'))
    time_spent = Column(Integer, nullable=False)  # seconds
    started = Column(DateTime, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    issue = relationship("JiraIssue", back_populates="worklogs")
    author = relationship("JiraUser")


class IssueAttachment(Base):
    """Issue attachment model."""
    __tablename__ = 'issue_attachments'
    
    id = Column(Integer, primary_key=True)
    jira_id = Column(String(50), nullable=False, unique=True)
    issue_id = Column(Integer, ForeignKey('jira_issues.id', ondelete='CASCADE'), nullable=False)
    author_id = Column(Integer, ForeignKey('jira_users.id'))
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(255))
    size = Column(Integer)  # bytes
    content_url = Column(Text)
    thumbnail_url = Column(Text)
    created_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    issue = relationship("JiraIssue", back_populates="attachments")
    author = relationship("JiraUser")


class IssueTransition(Base):
    """Issue status transition model."""
    __tablename__ = 'issue_transitions'
    
    id = Column(Integer, primary_key=True)
    issue_id = Column(Integer, ForeignKey('jira_issues.id', ondelete='CASCADE'), nullable=False)
    from_status_id = Column(Integer, ForeignKey('jira_statuses.id'))
    to_status_id = Column(Integer, ForeignKey('jira_statuses.id'))
    author_id = Column(Integer, ForeignKey('jira_users.id'))
    transition_date = Column(DateTime, nullable=False)
    duration_seconds = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    issue = relationship("JiraIssue", back_populates="transitions")
    from_status = relationship("JiraStatus", foreign_keys=[from_status_id])
    to_status = relationship("JiraStatus", foreign_keys=[to_status_id])
    author = relationship("JiraUser")


class IssueChangelog(Base):
    """Issue changelog model (full history)."""
    __tablename__ = 'issue_changelog'
    
    id = Column(Integer, primary_key=True)
    jira_id = Column(String(50), nullable=False)
    issue_id = Column(Integer, ForeignKey('jira_issues.id', ondelete='CASCADE'), nullable=False)
    author_id = Column(Integer, ForeignKey('jira_users.id'))
    field_name = Column(String(255), nullable=False)
    field_type = Column(String(100))
    from_value = Column(Text)
    from_string = Column(Text)
    to_value = Column(Text)
    to_string = Column(Text)
    change_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    issue = relationship("JiraIssue", back_populates="changelog")
    author = relationship("JiraUser")


class IssueCustomField(Base):
    """Issue custom field model (JSON storage)."""
    __tablename__ = 'issue_custom_fields'
    
    id = Column(Integer, primary_key=True)
    issue_id = Column(Integer, ForeignKey('jira_issues.id', ondelete='CASCADE'), nullable=False)
    field_id = Column(String(100), nullable=False)
    field_name = Column(String(255))
    field_type = Column(String(100))
    value = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('issue_id', 'field_id', name='uq_issue_custom_field'),
    )
    
    issue = relationship("JiraIssue", back_populates="custom_fields")


# ============================================
# METRICS MODELS
# ============================================

class DailyMetric(Base):
    """Daily metrics model."""
    __tablename__ = 'daily_metrics'
    
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('teams.id'))
    project_id = Column(Integer, ForeignKey('jira_projects.id'))
    metric_date = Column(Date, nullable=False)
    
    # Issue counts
    tickets_created = Column(Integer, default=0)
    tickets_resolved = Column(Integer, default=0)
    tickets_updated = Column(Integer, default=0)
    backlog_count = Column(Integer, default=0)
    
    # Time metrics (in hours)
    avg_resolution_time = Column(Float)
    avg_cycle_time = Column(Float)
    avg_lead_time = Column(Float)
    
    # Story points
    points_committed = Column(Float)
    points_completed = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('team_id', 'project_id', 'metric_date', name='uq_daily_metric'),
    )
    
    team = relationship("Team")
    project = relationship("JiraProject")


class SprintMetric(Base):
    """Sprint metrics model."""
    __tablename__ = 'sprint_metrics'
    
    id = Column(Integer, primary_key=True)
    sprint_id = Column(Integer, ForeignKey('jira_sprints.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Commitment
    issues_committed = Column(Integer, default=0)
    points_committed = Column(Float, default=0)
    
    # Completion
    issues_completed = Column(Integer, default=0)
    points_completed = Column(Float, default=0)
    
    # Additional
    issues_added = Column(Integer, default=0)
    issues_removed = Column(Integer, default=0)
    
    # Velocity
    velocity = Column(Float)
    completion_rate = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    sprint = relationship("JiraSprint", back_populates="metrics")


class EtlRun(Base):
    """ETL run tracking model."""
    __tablename__ = 'etl_runs'
    
    id = Column(Integer, primary_key=True)
    run_type = Column(String(50), nullable=False)  # 'full', 'incremental'
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String(50), nullable=False, default='running')  # 'running', 'completed', 'failed'
    records_processed = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    error_message = Column(Text)
    last_sync_timestamp = Column(DateTime)
