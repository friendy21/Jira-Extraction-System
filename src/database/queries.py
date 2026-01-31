"""
Database Query Helpers Module
Provides functions for common database queries and metrics calculations.
"""

from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.orm import Session

from src.database.models import (
    Organization, Team, JiraProject, JiraIssue, JiraSprint, JiraBoard,
    JiraStatus, JiraStatusCategory, JiraPriority, JiraUser, JiraLabel,
    JiraComponent, JiraVersion, IssueTransition, IssueComment, IssueWorklog,
    IssueLabel, IssueComponent, DailyMetric, SprintMetric, EtlRun
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class QueryHelpers:
    """Query helper functions for database operations."""
    
    def __init__(self, session: Session):
        """Initialize with database session."""
        self.session = session
    
    # ========================================
    # Team & Organization Queries
    # ========================================
    
    def get_all_organizations(self) -> List[Organization]:
        """Get all organizations."""
        return self.session.query(Organization).all()
    
    def get_all_teams(self) -> List[Team]:
        """Get all teams with organization info."""
        return self.session.query(Team).all()
    
    def get_teams_by_org(self, org_id: int) -> List[Team]:
        """Get teams for a specific organization."""
        return self.session.query(Team).filter(Team.org_id == org_id).all()
    
    # ========================================
    # Velocity & Sprint Metrics
    # ========================================
    
    def get_team_velocity(self, team_id: int, sprint_count: int = 5) -> List[Dict]:
        """
        Get velocity metrics for a team's last N sprints.
        
        Args:
            team_id: Team ID
            sprint_count: Number of sprints to include
            
        Returns:
            List of velocity data per sprint
        """
        sprints = (
            self.session.query(JiraSprint, SprintMetric)
            .join(JiraBoard, JiraSprint.board_id == JiraBoard.id)
            .join(JiraProject, JiraBoard.project_id == JiraProject.id)
            .outerjoin(SprintMetric, JiraSprint.id == SprintMetric.sprint_id)
            .filter(JiraProject.team_id == team_id)
            .filter(JiraSprint.state == 'closed')
            .order_by(desc(JiraSprint.end_date))
            .limit(sprint_count)
            .all()
        )
        
        results = []
        for sprint, metrics in sprints:
            results.append({
                'sprint_id': sprint.id,
                'sprint_name': sprint.name,
                'start_date': sprint.start_date,
                'end_date': sprint.end_date,
                'points_committed': float(metrics.points_committed) if metrics else 0,
                'points_completed': float(metrics.points_completed) if metrics else 0,
                'issues_committed': metrics.issues_committed if metrics else 0,
                'issues_completed': metrics.issues_completed if metrics else 0,
                'velocity': float(metrics.velocity) if metrics and metrics.velocity else 0,
                'completion_rate': float(metrics.completion_rate) if metrics and metrics.completion_rate else 0
            })
        
        return results
    
    def get_sprint_metrics(self, sprint_id: int) -> Optional[Dict]:
        """Get detailed metrics for a specific sprint."""
        sprint = self.session.query(JiraSprint).filter(JiraSprint.id == sprint_id).first()
        if not sprint:
            return None
        
        # Get issue counts
        issues = (
            self.session.query(JiraIssue)
            .filter(JiraIssue.sprint_id == sprint_id)
            .all()
        )
        
        total_issues = len(issues)
        completed = sum(1 for i in issues if i.resolution_id is not None)
        total_points = sum(float(i.story_points or 0) for i in issues)
        completed_points = sum(float(i.story_points or 0) for i in issues if i.resolution_id is not None)
        
        return {
            'sprint_id': sprint.id,
            'sprint_name': sprint.name,
            'state': sprint.state,
            'start_date': sprint.start_date,
            'end_date': sprint.end_date,
            'goal': sprint.goal,
            'total_issues': total_issues,
            'completed_issues': completed,
            'incomplete_issues': total_issues - completed,
            'total_points': total_points,
            'completed_points': completed_points,
            'completion_percentage': round(100 * completed / total_issues, 2) if total_issues > 0 else 0
        }
    
    # ========================================
    # Kanban & Flow Metrics
    # ========================================
    
    def get_kanban_flow_metrics(self, board_id: int) -> List[Dict]:
        """Get Kanban flow metrics by status for a board."""
        board = self.session.query(JiraBoard).filter(JiraBoard.jira_id == board_id).first()
        if not board or not board.project_id:
            return []
        
        # Get issues grouped by status
        results = (
            self.session.query(
                JiraStatus.name.label('status'),
                JiraStatusCategory.name.label('category'),
                func.count(JiraIssue.id).label('count'),
                func.coalesce(func.sum(JiraIssue.story_points), 0).label('points')
            )
            .join(JiraIssue.status)
            .outerjoin(JiraStatusCategory, JiraStatus.category_id == JiraStatusCategory.id)
            .filter(JiraIssue.project_id == board.project_id)
            .filter(JiraIssue.resolution_id.is_(None))
            .group_by(JiraStatus.name, JiraStatusCategory.name)
            .all()
        )
        
        return [
            {
                'status': r.status,
                'category': r.category,
                'issue_count': r.count,
                'story_points': float(r.points)
            }
            for r in results
        ]
    
    def get_swimlane_workload(self, board_id: int) -> List[Dict]:
        """Get workload distribution across swimlanes."""
        # This would need swimlane configuration to properly implement
        # Placeholder implementation based on assignees
        board = self.session.query(JiraBoard).filter(JiraBoard.jira_id == board_id).first()
        if not board or not board.project_id:
            return []
        
        results = (
            self.session.query(
                JiraUser.display_name.label('assignee'),
                func.count(JiraIssue.id).label('count'),
                func.coalesce(func.sum(JiraIssue.story_points), 0).label('points')
            )
            .outerjoin(JiraUser, JiraIssue.assignee_id == JiraUser.id)
            .filter(JiraIssue.project_id == board.project_id)
            .filter(JiraIssue.resolution_id.is_(None))
            .group_by(JiraUser.display_name)
            .all()
        )
        
        return [
            {
                'swimlane': r.assignee or 'Unassigned',
                'issue_count': r.count,
                'story_points': float(r.points)
            }
            for r in results
        ]
    
    # ========================================
    # Priority & Label Analysis
    # ========================================
    
    def get_priority_distribution(self, team_id: int) -> List[Dict]:
        """Get issue distribution by priority for a team."""
        results = (
            self.session.query(
                JiraPriority.name.label('priority'),
                JiraPriority.sort_order,
                func.count(JiraIssue.id).label('total'),
                func.count(JiraIssue.id).filter(JiraIssue.resolution_id.is_(None)).label('open'),
                func.count(JiraIssue.id).filter(JiraIssue.resolution_id.isnot(None)).label('resolved')
            )
            .join(JiraIssue.priority)
            .join(JiraProject, JiraIssue.project_id == JiraProject.id)
            .filter(JiraProject.team_id == team_id)
            .group_by(JiraPriority.name, JiraPriority.sort_order)
            .order_by(JiraPriority.sort_order)
            .all()
        )
        
        return [
            {
                'priority': r.priority,
                'total_count': r.total,
                'open_count': r.open,
                'resolved_count': r.resolved
            }
            for r in results
        ]
    
    def get_label_analysis(self, project_id: int) -> List[Dict]:
        """Get label usage analysis for a project."""
        results = (
            self.session.query(
                JiraLabel.name.label('label'),
                func.count(IssueLabel.issue_id).label('count')
            )
            .join(IssueLabel, JiraLabel.id == IssueLabel.label_id)
            .join(JiraIssue, IssueLabel.issue_id == JiraIssue.id)
            .filter(JiraIssue.project_id == project_id)
            .group_by(JiraLabel.name)
            .order_by(desc(func.count(IssueLabel.issue_id)))
            .limit(20)
            .all()
        )
        
        return [
            {
                'label': r.label,
                'issue_count': r.count
            }
            for r in results
        ]
    
    # ========================================
    # Ticket Aging & Backlog
    # ========================================
    
    def get_ticket_aging(self, team_id: int) -> List[Dict]:
        """Get aging buckets for open tickets."""
        now = datetime.utcnow()
        
        issues = (
            self.session.query(JiraIssue)
            .join(JiraProject, JiraIssue.project_id == JiraProject.id)
            .filter(JiraProject.team_id == team_id)
            .filter(JiraIssue.resolution_id.is_(None))
            .all()
        )
        
        buckets = {
            '0-7 days': 0,
            '8-14 days': 0,
            '15-30 days': 0,
            '31-60 days': 0,
            '61-90 days': 0,
            '90+ days': 0
        }
        
        for issue in issues:
            age = (now - issue.created_date).days
            if age <= 7:
                buckets['0-7 days'] += 1
            elif age <= 14:
                buckets['8-14 days'] += 1
            elif age <= 30:
                buckets['15-30 days'] += 1
            elif age <= 60:
                buckets['31-60 days'] += 1
            elif age <= 90:
                buckets['61-90 days'] += 1
            else:
                buckets['90+ days'] += 1
        
        return [
            {'bucket': k, 'count': v}
            for k, v in buckets.items()
        ]
    
    # ========================================
    # Daily Metrics
    # ========================================
    
    def get_daily_metrics(self, team_id: int, days: int = 30) -> List[Dict]:
        """Get daily metrics for a team over the past N days."""
        start_date = date.today() - timedelta(days=days)
        
        metrics = (
            self.session.query(DailyMetric)
            .filter(DailyMetric.team_id == team_id)
            .filter(DailyMetric.metric_date >= start_date)
            .order_by(DailyMetric.metric_date)
            .all()
        )
        
        return [
            {
                'date': m.metric_date.isoformat(),
                'tickets_created': m.tickets_created,
                'tickets_resolved': m.tickets_resolved,
                'backlog_count': m.backlog_count,
                'avg_cycle_time': float(m.avg_cycle_time) if m.avg_cycle_time else None
            }
            for m in metrics
        ]
    
    # ========================================
    # Component & Version Queries
    # ========================================
    
    def get_component_workload(self, project_id: int) -> List[Dict]:
        """Get issue distribution by component."""
        results = (
            self.session.query(
                JiraComponent.name.label('component'),
                func.count(IssueComponent.issue_id).label('count')
            )
            .outerjoin(IssueComponent, JiraComponent.id == IssueComponent.component_id)
            .filter(JiraComponent.project_id == project_id)
            .group_by(JiraComponent.name)
            .order_by(desc(func.count(IssueComponent.issue_id)))
            .all()
        )
        
        return [
            {
                'component': r.component,
                'issue_count': r.count
            }
            for r in results
        ]
    
    def get_version_progress(self, project_id: int) -> List[Dict]:
        """Get progress for each version/release."""
        versions = (
            self.session.query(JiraVersion)
            .filter(JiraVersion.project_id == project_id)
            .filter(JiraVersion.released == False)
            .order_by(JiraVersion.release_date)
            .all()
        )
        
        results = []
        for version in versions:
            # Count issues for this version
            total = self.session.query(func.count(JiraIssue.id))\
                .join('fix_versions')\
                .filter(JiraVersion.id == version.id)\
                .scalar() or 0
            
            completed = self.session.query(func.count(JiraIssue.id))\
                .join('fix_versions')\
                .filter(JiraVersion.id == version.id)\
                .filter(JiraIssue.resolution_id.isnot(None))\
                .scalar() or 0
            
            results.append({
                'version_name': version.name,
                'release_date': version.release_date.isoformat() if version.release_date else None,
                'total_issues': total,
                'completed_issues': completed,
                'progress_percentage': round(100 * completed / total, 2) if total > 0 else 0
            })
        
        return results
    
    # ========================================
    # Time Tracking
    # ========================================
    
    def get_time_tracking_summary(self, team_id: int) -> Dict:
        """Get time tracking summary for a team."""
        issues = (
            self.session.query(JiraIssue)
            .join(JiraProject)
            .filter(JiraProject.team_id == team_id)
            .filter(or_(
                JiraIssue.original_estimate.isnot(None),
                JiraIssue.time_spent.isnot(None)
            ))
            .all()
        )
        
        total_estimated = sum(i.original_estimate or 0 for i in issues)
        total_spent = sum(i.time_spent or 0 for i in issues)
        
        return {
            'total_estimated_hours': round(total_estimated / 3600, 2),
            'total_spent_hours': round(total_spent / 3600, 2),
            'variance_hours': round((total_spent - total_estimated) / 3600, 2),
            'accuracy_percentage': round(100 * total_spent / total_estimated, 2) if total_estimated > 0 else None
        }
    
    # ========================================
    # ETL Tracking
    # ========================================
    
    def get_last_etl_run(self) -> Optional[EtlRun]:
        """Get the most recent successful ETL run."""
        return (
            self.session.query(EtlRun)
            .filter(EtlRun.status == 'completed')
            .order_by(desc(EtlRun.completed_at))
            .first()
        )
    
    def get_last_sync_timestamp(self) -> Optional[datetime]:
        """Get timestamp of last successful sync."""
        last_run = self.get_last_etl_run()
        return last_run.last_sync_timestamp if last_run else None
