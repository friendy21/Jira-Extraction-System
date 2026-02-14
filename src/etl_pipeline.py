"""
ETL Pipeline Module
Orchestrates data extraction from Jira, transformation, and loading into PostgreSQL.
"""

from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.config_manager import ConfigManager
from src.jira_client import JiraClient, JiraAPIError
from src.database.connection import get_db, get_session
from src.database.models import (
    Organization, Team, JiraUser, JiraProject, JiraProjectCategory,
    JiraBoard, JiraSprint, JiraSwimlane, JiraStatus, JiraStatusCategory,
    JiraPriority, JiraIssueType, JiraResolution, JiraIssueLinkType, JiraLabel,
    JiraComponent, JiraVersion, JiraIssue, IssueLabel, IssueComponent,
    IssueFixVersion, IssueAffectsVersion, IssueComment, IssueWorklog,
    IssueAttachment, IssueTransition, IssueChangelog, IssueCustomField,
    EtlRun, Base
)
from src.utils.logger import get_logger
from src.utils.helpers import (
    parse_jira_datetime, parse_jira_date, safe_get, chunk_list, sanitize_string
)

logger = get_logger(__name__)


class ETLPipeline:
    """
    ETL Pipeline for syncing Jira data to PostgreSQL.
    Supports both full and incremental loads.
    """
    
    def __init__(self):
        """Initialize ETL pipeline."""
        self.config = ConfigManager()
        self.jira = JiraClient()
        self.db = get_db()
        
        etl_config = self.config.get_etl_config()
        self.batch_size = etl_config.get('batch_size', 1000)
        self.incremental = etl_config.get('incremental', True)
        
        # Track statistics
        self.stats = {
            'records_processed': 0,
            'records_inserted': 0,
            'records_updated': 0
        }
        
        # Cache for lookups
        self._user_cache: Dict[str, int] = {}
        self._status_cache: Dict[str, int] = {}
        self._priority_cache: Dict[str, int] = {}
        self._issue_type_cache: Dict[str, int] = {}
        self._resolution_cache: Dict[str, int] = {}
        self._project_cache: Dict[str, int] = {}
        self._label_cache: Dict[str, int] = {}
        self._component_cache: Dict[str, int] = {}
        self._version_cache: Dict[str, int] = {}
        self._sprint_cache: Dict[int, int] = {}
        
        logger.info("ETL Pipeline initialized")
    
    def run_full_sync(self) -> EtlRun:
        """
        Run full synchronization from Jira.
        
        Returns:
            EtlRun record with results
        """
        logger.info("Starting full ETL sync")
        return self._run_sync(run_type='full')
    
    def run_incremental_sync(self) -> EtlRun:
        """
        Run incremental synchronization for changed data.
        
        Returns:
            EtlRun record with results
        """
        logger.info("Starting incremental ETL sync")
        return self._run_sync(run_type='incremental')
    
    def _run_sync(self, run_type: str) -> EtlRun:
        """Execute the sync process."""
        etl_run = EtlRun(
            run_type=run_type,
            started_at=datetime.utcnow(),
            status='running'
        )
        
        with get_session() as session:
            session.add(etl_run)
            session.commit()
            etl_run_id = etl_run.id
        
        try:
            # Test Jira connection
            if not self.jira.test_connection():
                raise JiraAPIError("Failed to connect to Jira")
            
            with get_session() as session:
                # Get last sync timestamp for incremental
                last_sync = None
                if run_type == 'incremental':
                    last_run = session.query(EtlRun).filter(
                        EtlRun.status == 'completed',
                        EtlRun.id != etl_run_id
                    ).order_by(EtlRun.completed_at.desc()).first()
                    
                    if last_run:
                        last_sync = last_run.last_sync_timestamp
                
                # Sync reference data (always)
                self._sync_reference_data(session)
                
                # Sync organizations and teams from config
                self._sync_organizations_and_teams(session)
                
                # Sync projects
                self._sync_projects(session)
                
                # Sync boards and sprints
                self._sync_boards_and_sprints(session)
                
                # Sync issues
                self._sync_issues(session, since=last_sync)
                
                session.commit()
            
            # Update ETL run status
            with get_session() as session:
                etl_run = session.query(EtlRun).get(etl_run_id)
                etl_run.status = 'completed'
                etl_run.completed_at = datetime.utcnow()
                etl_run.records_processed = self.stats['records_processed']
                etl_run.records_inserted = self.stats['records_inserted']
                etl_run.records_updated = self.stats['records_updated']
                etl_run.last_sync_timestamp = datetime.utcnow()
                session.commit()
            
            logger.info(f"ETL sync completed: {self.stats}")
            
        except Exception as e:
            logger.error(f"ETL sync failed: {e}")
            
            with get_session() as session:
                etl_run = session.query(EtlRun).get(etl_run_id)
                etl_run.status = 'failed'
                etl_run.completed_at = datetime.utcnow()
                etl_run.error_message = str(e)[:1000]
                session.commit()
            
            raise
        
        return etl_run
    
    # ========================================
    # Reference Data Sync
    # ========================================
    
    def _sync_reference_data(self, session: Session) -> None:
        """Sync reference data (statuses, priorities, etc.)."""
        logger.info("Syncing reference data")
        
        # Sync statuses
        statuses = self.jira.fetch_statuses()
        for status in statuses:
            self._upsert_status(session, status)
        
        # Sync priorities
        priorities = self.jira.fetch_priorities()
        for i, priority in enumerate(priorities):
            self._upsert_priority(session, priority, sort_order=i)
        
        # Sync issue types
        issue_types = self.jira.fetch_issue_types()
        for issue_type in issue_types:
            self._upsert_issue_type(session, issue_type)
        
        # Sync resolutions
        resolutions = self.jira.fetch_resolutions()
        for resolution in resolutions:
            self._upsert_resolution(session, resolution)
        
        # Sync issue link types
        link_types = self.jira.fetch_issue_link_types()
        for link_type in link_types:
            self._upsert_issue_link_type(session, link_type)
        
        session.flush()
        self._build_caches(session)
        
        logger.info("Reference data synced")
    
    def _upsert_status(self, session: Session, data: Dict) -> None:
        """Upsert a status record."""
        # Handle status category
        category_data = safe_get(data, 'statusCategory')
        category_id = None
        
        if category_data:
            stmt = pg_insert(JiraStatusCategory).values(
                jira_id=category_data.get('id'),
                key=category_data.get('key'),
                name=category_data.get('name'),
                color_name=category_data.get('colorName')
            ).on_conflict_do_update(
                index_elements=['jira_id'],
                set_={'name': category_data.get('name')}
            )
            session.execute(stmt)
            session.flush()
            
            cat = session.query(JiraStatusCategory).filter(
                JiraStatusCategory.jira_id == category_data.get('id')
            ).first()
            if cat:
                category_id = cat.id
        
        stmt = pg_insert(JiraStatus).values(
            jira_id=str(data.get('id')),
            name=data.get('name'),
            description=data.get('description'),
            category_id=category_id
        ).on_conflict_do_update(
            index_elements=['jira_id'],
            set_={'name': data.get('name'), 'category_id': category_id}
        )
        session.execute(stmt)
    
    def _upsert_priority(self, session: Session, data: Dict, sort_order: int) -> None:
        """Upsert a priority record."""
        stmt = pg_insert(JiraPriority).values(
            jira_id=str(data.get('id')),
            name=data.get('name'),
            description=data.get('description'),
            icon_url=data.get('iconUrl'),
            status_color=data.get('statusColor'),
            sort_order=sort_order
        ).on_conflict_do_update(
            index_elements=['jira_id'],
            set_={'name': data.get('name'), 'sort_order': sort_order}
        )
        session.execute(stmt)
    
    def _upsert_issue_type(self, session: Session, data: Dict) -> None:
        """Upsert an issue type record."""
        stmt = pg_insert(JiraIssueType).values(
            jira_id=str(data.get('id')),
            name=data.get('name'),
            description=data.get('description'),
            icon_url=data.get('iconUrl'),
            subtask=data.get('subtask', False),
            hierarchy_level=data.get('hierarchyLevel', 0)
        ).on_conflict_do_update(
            index_elements=['jira_id'],
            set_={'name': data.get('name'), 'subtask': data.get('subtask', False)}
        )
        session.execute(stmt)
    
    def _upsert_resolution(self, session: Session, data: Dict) -> None:
        """Upsert a resolution record."""
        stmt = pg_insert(JiraResolution).values(
            jira_id=str(data.get('id')),
            name=data.get('name'),
            description=data.get('description')
        ).on_conflict_do_update(
            index_elements=['jira_id'],
            set_={'name': data.get('name')}
        )
        session.execute(stmt)
    
    def _upsert_issue_link_type(self, session: Session, data: Dict) -> None:
        """Upsert an issue link type record."""
        stmt = pg_insert(JiraIssueLinkType).values(
            jira_id=str(data.get('id')),
            name=data.get('name'),
            inward=data.get('inward'),
            outward=data.get('outward')
        ).on_conflict_do_update(
            index_elements=['jira_id'],
            set_={'name': data.get('name')}
        )
        session.execute(stmt)
    
    # ========================================
    # Organization & Team Sync
    # ========================================
    
    def _sync_organizations_and_teams(self, session: Session) -> None:
        """Sync organizations and teams from config."""
        logger.info("Syncing organizations and teams from config")
        
        for org_data in self.config.get_organizations():
            # Upsert organization
            stmt = pg_insert(Organization).values(
                name=org_data.get('name'),
                code=org_data.get('code'),
                description=org_data.get('description')
            ).on_conflict_do_update(
                index_elements=['code'],
                set_={'name': org_data.get('name')}
            )
            session.execute(stmt)
            session.flush()
            
            org = session.query(Organization).filter(
                Organization.code == org_data.get('code')
            ).first()
            
            # Upsert teams
            for team_data in org_data.get('teams', []):
                stmt = pg_insert(Team).values(
                    org_id=org.id,
                    team_code=team_data.get('code'),
                    team_name=team_data.get('name'),
                    description=team_data.get('description')
                ).on_conflict_do_nothing()  # Skip if exists
                session.execute(stmt)
        
        session.flush()
    
    # ========================================
    # Project Sync
    # ========================================
    
    def _sync_projects(self, session: Session) -> None:
        """Sync projects from Jira."""
        logger.info("Syncing projects")
        
        projects = self.jira.fetch_projects()
        
        for project_data in projects:
            self._upsert_project(session, project_data)
            
            # Sync components
            try:
                components = self.jira.fetch_project_components(project_data.get('key'))
                for comp in components:
                    self._upsert_component(session, project_data.get('key'), comp)
            except JiraAPIError as e:
                logger.warning(f"Failed to fetch components for {project_data.get('key')}: {e}")
            
            # Sync versions
            try:
                versions = self.jira.fetch_project_versions(project_data.get('key'))
                for version in versions:
                    self._upsert_version(session, project_data.get('key'), version)
            except JiraAPIError as e:
                logger.warning(f"Failed to fetch versions for {project_data.get('key')}: {e}")
        
        session.flush()
        self._build_project_cache(session)
    
    def _upsert_project(self, session: Session, data: Dict) -> None:
        """Upsert a project record."""
        # Get lead user ID
        lead_id = None
        lead_data = safe_get(data, 'lead')
        if lead_data:
            lead_id = self._get_or_create_user(session, lead_data)
        
        # Find team by matching project key
        team_id = None
        for team in self.config.get_all_teams():
            if data.get('key') in team.get('jira_project_keys', []):
                # Look up team in database
                db_team = session.query(Team).filter(
                    Team.team_code == team.get('code')
                ).first()
                if db_team:
                    team_id = db_team.id
                break
        
        stmt = pg_insert(JiraProject).values(
            jira_id=str(data.get('id')),
            project_key=data.get('key'),
            project_name=data.get('name'),
            description=safe_get(data, 'description'),
            project_type=safe_get(data, 'projectTypeKey'),
            style=safe_get(data, 'style'),
            lead_id=lead_id,
            team_id=team_id,
            url=safe_get(data, 'self')
        ).on_conflict_do_update(
            index_elements=['jira_id'],
            set_={
                'project_name': data.get('name'),
                'lead_id': lead_id,
                'team_id': team_id
            }
        )
        session.execute(stmt)
    
    def _upsert_component(self, session: Session, project_key: str, data: Dict) -> None:
        """Upsert a component record."""
        project = session.query(JiraProject).filter(
            JiraProject.project_key == project_key
        ).first()
        if not project:
            return
        
        lead_id = None
        lead_data = safe_get(data, 'lead')
        if lead_data:
            lead_id = self._get_or_create_user(session, lead_data)
        
        stmt = pg_insert(JiraComponent).values(
            jira_id=str(data.get('id')),
            project_id=project.id,
            name=data.get('name'),
            description=data.get('description'),
            lead_id=lead_id,
            assignee_type=data.get('assigneeType')
        ).on_conflict_do_update(
            index_elements=['jira_id'],
            set_={'name': data.get('name')}
        )
        session.execute(stmt)
    
    def _upsert_version(self, session: Session, project_key: str, data: Dict) -> None:
        """Upsert a version record."""
        project = session.query(JiraProject).filter(
            JiraProject.project_key == project_key
        ).first()
        if not project:
            return
        
        stmt = pg_insert(JiraVersion).values(
            jira_id=str(data.get('id')),
            project_id=project.id,
            name=data.get('name'),
            description=data.get('description'),
            archived=data.get('archived', False),
            released=data.get('released', False),
            start_date=parse_jira_date(data.get('startDate')),
            release_date=parse_jira_date(data.get('releaseDate')),
            overdue=data.get('overdue', False)
        ).on_conflict_do_update(
            index_elements=['jira_id'],
            set_={
                'released': data.get('released', False),
                'archived': data.get('archived', False)
            }
        )
        session.execute(stmt)
    
    # ========================================
    # Board & Sprint Sync
    # ========================================
    
    def _sync_boards_and_sprints(self, session: Session) -> None:
        """Sync boards and sprints from Jira."""
        logger.info("Syncing boards and sprints")
        
        boards = self.jira.fetch_boards()
        
        for board_data in boards:
            self._upsert_board(session, board_data)
            
            # Sync sprints for this board
            try:
                sprints = self.jira.fetch_sprints(board_data.get('id'))
                for sprint in sprints:
                    self._upsert_sprint(session, board_data.get('id'), sprint)
            except JiraAPIError as e:
                logger.warning(f"Failed to fetch sprints for board {board_data.get('id')}: {e}")
        
        session.flush()
        self._build_sprint_cache(session)
    
    def _upsert_board(self, session: Session, data: Dict) -> None:
        """Upsert a board record."""
        # Find project
        project_id = None
        location = safe_get(data, 'location')
        if location:
            project_key = location.get('projectKey')
            if project_key:
                project = session.query(JiraProject).filter(
                    JiraProject.project_key == project_key
                ).first()
                if project:
                    project_id = project.id
        
        stmt = pg_insert(JiraBoard).values(
            jira_id=data.get('id'),
            name=data.get('name'),
            board_type=data.get('type', 'kanban'),
            project_id=project_id
        ).on_conflict_do_update(
            index_elements=['jira_id'],
            set_={'name': data.get('name')}
        )
        session.execute(stmt)
    
    def _upsert_sprint(self, session: Session, board_jira_id: int, data: Dict) -> None:
        """Upsert a sprint record."""
        board = session.query(JiraBoard).filter(
            JiraBoard.jira_id == board_jira_id
        ).first()
        
        board_id = board.id if board else None
        
        stmt = pg_insert(JiraSprint).values(
            jira_id=data.get('id'),
            board_id=board_id,
            name=data.get('name'),
            state=data.get('state'),
            start_date=parse_jira_datetime(data.get('startDate')),
            end_date=parse_jira_datetime(data.get('endDate')),
            complete_date=parse_jira_datetime(data.get('completeDate')),
            goal=data.get('goal')
        ).on_conflict_do_update(
            index_elements=['jira_id'],
            set_={
                'state': data.get('state'),
                'complete_date': parse_jira_datetime(data.get('completeDate'))
            }
        )
        session.execute(stmt)
    
    # ========================================
    # Issue Sync
    # ========================================
    
    def _sync_issues(self, session: Session, since: datetime = None) -> None:
        """Sync issues from Jira."""
        project_keys = self.config.get_all_project_keys()
        
        if not project_keys:
            logger.warning("No project keys configured")
            return
        
        logger.info(f"Syncing issues for projects: {project_keys}")
        
        if since:
            issues = self.jira.fetch_issues_since(project_keys, since)
        else:
            keys_str = ', '.join(project_keys)
            jql = f'project in ({keys_str}) ORDER BY updated ASC'
            issues = self.jira.fetch_issues(jql, expand=['changelog'])
        
        batch = []
        for issue_data in issues:
            batch.append(issue_data)
            
            if len(batch) >= self.batch_size:
                self._process_issue_batch(session, batch)
                session.flush()
                batch = []
        
        # Process remaining
        if batch:
            self._process_issue_batch(session, batch)
            session.flush()
    
    def _process_issue_batch(self, session: Session, issues: List[Dict]) -> None:
        """Process a batch of issues."""
        for issue_data in issues:
            try:
                self._upsert_issue(session, issue_data)
                self.stats['records_processed'] += 1
            except Exception as e:
                logger.error(f"Error processing issue {issue_data.get('key')}: {e}")
    
    def _upsert_issue(self, session: Session, data: Dict) -> None:
        """Upsert an issue record."""
        fields = data.get('fields', {})
        
        # Get foreign key IDs
        project_id = self._project_cache.get(safe_get(fields, 'project', 'key'))
        if not project_id:
            return  # Skip if project not found
        
        status_id = self._status_cache.get(safe_get(fields, 'status', 'id'))
        priority_id = self._priority_cache.get(safe_get(fields, 'priority', 'id'))
        issue_type_id = self._issue_type_cache.get(safe_get(fields, 'issuetype', 'id'))
        resolution_id = self._resolution_cache.get(safe_get(fields, 'resolution', 'id'))
        
        assignee_id = None
        if fields.get('assignee'):
            assignee_id = self._get_or_create_user(session, fields['assignee'])
        
        reporter_id = None
        if fields.get('reporter'):
            reporter_id = self._get_or_create_user(session, fields['reporter'])
        
        creator_id = None
        if fields.get('creator'):
            creator_id = self._get_or_create_user(session, fields['creator'])
        
        # Sprint handling
        sprint_id = None
        sprint_field = fields.get('sprint') or (fields.get('customfield_10020') or [None])[0] if isinstance(fields.get('customfield_10020'), list) else None
        if sprint_field and isinstance(sprint_field, dict):
            sprint_id = self._sprint_cache.get(sprint_field.get('id'))
        
        # Epic handling
        epic_key = fields.get('parent', {}).get('key') if fields.get('parent', {}).get('fields', {}).get('issuetype', {}).get('name') == 'Epic' else None
        epic_name = fields.get('parent', {}).get('fields', {}).get('summary') if epic_key else None
        
        stmt = pg_insert(JiraIssue).values(
            jira_id=str(data.get('id')),
            issue_key=data.get('key'),
            project_id=project_id,
            summary=sanitize_string(fields.get('summary'), 1000),
            description=sanitize_string(fields.get('description')),
            environment=sanitize_string(fields.get('environment')),
            issue_type_id=issue_type_id,
            status_id=status_id,
            priority_id=priority_id,
            resolution_id=resolution_id,
            assignee_id=assignee_id,
            reporter_id=reporter_id,
            creator_id=creator_id,
            sprint_id=sprint_id,
            epic_key=epic_key,
            epic_name=epic_name,
            story_points=fields.get('customfield_10016'),  # Common story points field
            original_estimate=fields.get('timeoriginalestimate'),
            remaining_estimate=fields.get('timeestimate'),
            time_spent=fields.get('timespent'),
            created_date=parse_jira_datetime(fields.get('created')),
            updated_date=parse_jira_datetime(fields.get('updated')),
            resolution_date=parse_jira_datetime(fields.get('resolutiondate')),
            due_date=parse_jira_date(fields.get('duedate')),
            votes=safe_get(fields, 'votes', 'votes', default=0),
            watches=safe_get(fields, 'watches', 'watchCount', default=0)
        ).on_conflict_do_update(
            index_elements=['jira_id'],
            set_={
                'summary': sanitize_string(fields.get('summary'), 1000),
                'status_id': status_id,
                'resolution_id': resolution_id,
                'assignee_id': assignee_id,
                'sprint_id': sprint_id,
                'updated_date': parse_jira_datetime(fields.get('updated')),
                'resolution_date': parse_jira_datetime(fields.get('resolutiondate'))
            }
        )
        session.execute(stmt)
        session.flush()
        
        # Get issue ID
        issue = session.query(JiraIssue).filter(
            JiraIssue.jira_id == str(data.get('id'))
        ).first()
        
        if issue:
            # Sync labels
            for label_name in fields.get('labels', []):
                self._add_issue_label(session, issue.id, label_name)
            
            # Sync components
            for comp in fields.get('components', []):
                self._add_issue_component(session, issue.id, str(comp.get('id')))
            
            # Sync changelog if present
            if 'changelog' in data:
                self._sync_issue_changelog(session, issue.id, data['changelog'])
    
    def _add_issue_label(self, session: Session, issue_id: int, label_name: str) -> None:
        """Add label to issue."""
        # Get or create label
        if label_name not in self._label_cache:
            stmt = pg_insert(JiraLabel).values(name=label_name).on_conflict_do_nothing()
            session.execute(stmt)
            session.flush()
            label = session.query(JiraLabel).filter(JiraLabel.name == label_name).first()
            if label:
                self._label_cache[label_name] = label.id
        
        label_id = self._label_cache.get(label_name)
        if label_id:
            stmt = pg_insert(IssueLabel).values(
                issue_id=issue_id,
                label_id=label_id
            ).on_conflict_do_nothing()
            session.execute(stmt)
    
    def _add_issue_component(self, session: Session, issue_id: int, component_jira_id: str) -> None:
        """Add component to issue."""
        if component_jira_id not in self._component_cache:
            comp = session.query(JiraComponent).filter(
                JiraComponent.jira_id == component_jira_id
            ).first()
            if comp:
                self._component_cache[component_jira_id] = comp.id
        
        component_id = self._component_cache.get(component_jira_id)
        if component_id:
            stmt = pg_insert(IssueComponent).values(
                issue_id=issue_id,
                component_id=component_id
            ).on_conflict_do_nothing()
            session.execute(stmt)
    
    def _sync_issue_changelog(self, session: Session, issue_id: int, changelog: Dict) -> None:
        """Sync changelog for an issue."""
        histories = changelog.get('histories', [])
        
        for history in histories:
            author_id = None
            if history.get('author'):
                author_id = self._get_or_create_user(session, history['author'])
            
            change_date = parse_jira_datetime(history.get('created'))
            
            for item in history.get('items', []):
                # Record changelog entry
                stmt = pg_insert(IssueChangelog).values(
                    jira_id=str(history.get('id')),
                    issue_id=issue_id,
                    author_id=author_id,
                    field_name=item.get('field'),
                    field_type=item.get('fieldtype'),
                    from_value=item.get('from'),
                    from_string=sanitize_string(item.get('fromString'), 500),
                    to_value=item.get('to'),
                    to_string=sanitize_string(item.get('toString'), 500),
                    change_date=change_date
                ).on_conflict_do_nothing()
                session.execute(stmt)
                
                # Record status transitions
                if item.get('field') == 'status':
                    from_status_id = self._status_cache.get(item.get('from'))
                    to_status_id = self._status_cache.get(item.get('to'))
                    
                    stmt = pg_insert(IssueTransition).values(
                        issue_id=issue_id,
                        from_status_id=from_status_id,
                        to_status_id=to_status_id,
                        author_id=author_id,
                        transition_date=change_date
                    ).on_conflict_do_nothing()
                    session.execute(stmt)
    
    # ========================================
    # Helper Methods
    # ========================================
    
    def _get_or_create_user(self, session: Session, data: Dict) -> Optional[int]:
        """Get or create a user record, return ID."""
        account_id = data.get('accountId')
        if not account_id:
            return None
        
        if account_id in self._user_cache:
            return self._user_cache[account_id]
        
        stmt = pg_insert(JiraUser).values(
            account_id=account_id,
            display_name=data.get('displayName'),
            email_address=data.get('emailAddress'),
            active=data.get('active', True),
            timezone=data.get('timeZone'),
            avatar_url=safe_get(data, 'avatarUrls', '48x48')
        ).on_conflict_do_update(
            index_elements=['account_id'],
            set_={'display_name': data.get('displayName')}
        )
        session.execute(stmt)
        session.flush()
        
        user = session.query(JiraUser).filter(
            JiraUser.account_id == account_id
        ).first()
        
        if user:
            self._user_cache[account_id] = user.id
            return user.id
        
        return None
    
    def _build_caches(self, session: Session) -> None:
        """Build lookup caches for reference data."""
        # Status cache
        for status in session.query(JiraStatus).all():
            self._status_cache[status.jira_id] = status.id
        
        # Priority cache
        for priority in session.query(JiraPriority).all():
            self._priority_cache[priority.jira_id] = priority.id
        
        # Issue type cache
        for it in session.query(JiraIssueType).all():
            self._issue_type_cache[it.jira_id] = it.id
        
        # Resolution cache
        for res in session.query(JiraResolution).all():
            self._resolution_cache[res.jira_id] = res.id
    
    def _build_project_cache(self, session: Session) -> None:
        """Build project lookup cache."""
        for project in session.query(JiraProject).all():
            self._project_cache[project.project_key] = project.id
    
    def _build_sprint_cache(self, session: Session) -> None:
        """Build sprint lookup cache."""
        for sprint in session.query(JiraSprint).all():
            self._sprint_cache[sprint.jira_id] = sprint.id


def run_etl(full: bool = False) -> EtlRun:
    """
    Convenience function to run ETL.
    
    Args:
        full: If True, run full sync. Otherwise, run incremental.
        
    Returns:
        EtlRun record
    """
    pipeline = ETLPipeline()
    
    if full:
        return pipeline.run_full_sync()
    else:
        return pipeline.run_incremental_sync()
