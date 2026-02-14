"""
Jira REST API Client Module
Handles all communication with the Jira Cloud REST API.
"""

import time
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config_manager import ConfigManager
from src.utils.logger import get_logger
from src.utils.helpers import parse_jira_datetime, safe_get

logger = get_logger(__name__)


class JiraAPIError(Exception):
    """Custom exception for Jira API errors."""
    
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class JiraClient:
    """
    Jira REST API client with pagination, rate limiting, and error handling.
    """
    
    def __init__(self):
        """Initialize Jira client from configuration."""
        config = ConfigManager()
        jira_config = config.get_jira_config()
        
        self.base_url = jira_config.get('url', '').rstrip('/')
        self.username = jira_config.get('username', '')
        self.api_token = jira_config.get('api_token', '')
        
        # Rate limiting
        self.requests_per_second = jira_config.get('requests_per_second', 5)
        self.max_retries = jira_config.get('max_retries', 3)
        self.retry_delay = jira_config.get('retry_delay', 1)
        
        self._last_request_time = 0
        self._session = self._create_session()
        
        logger.info(f"Jira client initialized for {self.base_url}")
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic."""
        session = requests.Session()
        
        # Set authentication
        session.auth = (self.username, self.api_token)
        
        # Set default headers
        session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Configure retries
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=['GET', 'POST', 'PUT']
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        
        return session
    
    def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        if self.requests_per_second <= 0:
            return
        
        min_interval = 1.0 / self.requests_per_second
        elapsed = time.time() - self._last_request_time
        
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        
        self._last_request_time = time.time()
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        json_data: Dict = None
    ) -> Dict:
        """
        Make HTTP request to Jira API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            json_data: JSON body data
            
        Returns:
            Response JSON
            
        Raises:
            JiraAPIError: If request fails
        """
        self._rate_limit()
        
        url = urljoin(f"{self.base_url}/rest/", endpoint)
        
        try:
            response = self._session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=30
            )
            
            # Check for errors
            if response.status_code == 401:
                raise JiraAPIError("Authentication failed. Check your credentials.", 401)
            elif response.status_code == 403:
                raise JiraAPIError("Access forbidden. Check permissions.", 403)
            elif response.status_code == 404:
                raise JiraAPIError(f"Resource not found: {endpoint}", 404)
            elif response.status_code >= 400:
                raise JiraAPIError(
                    f"API error: {response.text}",
                    response.status_code,
                    response.json() if response.text else None
                )
            
            return response.json() if response.text else {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise JiraAPIError(f"Request failed: {str(e)}")
    
    def _paginate(
        self,
        endpoint: str,
        params: Dict = None,
        json_data: Dict = None,
        method: str = 'GET',
        data_key: str = 'values',
        max_results: int = 100,
        pagination_strategy: str = 'offset'
    ) -> Generator[Dict, None, None]:
        """
        Paginate through API results.
        
        Args:
            endpoint: API endpoint
            params: Query parameters (for GET)
            json_data: JSON body data (for POST)
            method: HTTP method (GET or POST)
            data_key: Key containing results in response
            max_results: Results per page
            pagination_strategy: 'offset' (startAt) or 'cursor' (nextPageToken)
            
        Yields:
            Individual result items
        """
        params = params or {}
        json_data = (json_data or {}).copy()  # Copy to avoid modifying caller's dict
        
        if method == 'GET':
            params['maxResults'] = max_results
        else:
            json_data['maxResults'] = max_results
            
        start_at = 0
        next_page_token = None
        
        while True:
            # Handle pagination parameters based on strategy
            if pagination_strategy == 'offset':
                if method == 'GET':
                    params['startAt'] = start_at
                else:
                    json_data['startAt'] = start_at
            elif pagination_strategy == 'cursor':
                # Cursor-based pagination uses nextPageToken
                if next_page_token:
                    if method == 'GET':
                        params['nextPageToken'] = next_page_token
                    else:
                        json_data['nextPageToken'] = next_page_token
                
                # IMPORTANT: Remove startAt if present, as it causes errors with cursor endpoints
                if method == 'GET' and 'startAt' in params:
                    del params['startAt']
                if method == 'POST' and 'startAt' in json_data:
                    del json_data['startAt']
                
            # Ensure we don't send empty dict as json body for GET requests
            request_json = json_data if json_data else None
            
            response = self._make_request(method, endpoint, params=params, json_data=request_json)
            
            items = response.get(data_key, [])
            if not items:
                break
            
            for item in items:
                yield item
            
            # Prepare for next page
            if pagination_strategy == 'offset':
                # Check if there are more results
                total = response.get('total', 0)
                start_at += len(items)
                
                if start_at >= total:
                    break
                logger.debug(f"Fetched {start_at}/{total} items from {endpoint}")
                
            elif pagination_strategy == 'cursor':
                # Get next page token
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                logger.debug(f"Fetched page from {endpoint}, getting next page...")
    
    # ========================================
    # Project Methods
    # ========================================
    
    def fetch_projects(self) -> List[Dict]:
        """Fetch all accessible projects."""
        logger.info("Fetching all projects")
        projects = list(self._paginate('api/3/project/search', data_key='values'))
        logger.info(f"Fetched {len(projects)} projects")
        return projects
    
    def fetch_project(self, project_key: str) -> Dict:
        """Fetch a single project by key."""
        return self._make_request('GET', f'api/3/project/{project_key}')
    
    def fetch_project_components(self, project_key: str) -> List[Dict]:
        """Fetch components for a project."""
        return self._make_request('GET', f'api/3/project/{project_key}/components')
    
    def fetch_project_versions(self, project_key: str) -> List[Dict]:
        """Fetch versions for a project."""
        return list(self._paginate(
            f'api/3/project/{project_key}/version',
            data_key='values'
        ))
    
    # ========================================
    # Issue Methods
    # ========================================
    
    def fetch_issues(
        self,
        jql: str,
        fields: List[str] = None,
        expand: List[str] = None,
        max_results: int = 100
    ) -> Generator[Dict, None, None]:
        """
        Fetch issues matching JQL query.
        
        Args:
            jql: JQL query string
            fields: Fields to include
            expand: Fields to expand
            max_results: Results per page
            
        Yields:
            Issue dictionaries
        """
        logger.info(f"Fetching issues with JQL: {jql[:100]}...")
    
        # Sanitize JQL (remove newlines from multiline strings)
        jql = jql.replace('\n', ' ').strip()
    
        # Use POST /api/3/search/jql as required by latest Jira Cloud API
        # Reference: https://developer.atlassian.com/changelog/#CHANGE-2046
        json_data = {'jql': jql}
        
        if fields:
            json_data['fields'] = fields
        if expand:
            # For search/jql endpoint, expand should be sent as a list
            json_data['expand'] = expand if isinstance(expand, list) else [expand]
            
        # Fetch issues with pagination (POST method)
        # Using cursor-based pagination (nextPageToken) which is required for this endpoint
        for issue in self._paginate(
            'api/3/search/jql',
            json_data=json_data,
            method='POST',
            data_key='issues',
            max_results=max_results,
            pagination_strategy='cursor'
        ):
            yield issue

    def get_issue(self, key: str, fields: List[str] = None, expand: List[str] = None) -> Dict:
        """
        Fetch single issue details.
        """
        params = {}
        if fields:
            params['fields'] = ','.join(fields)
        if expand:
            params['expand'] = ','.join(expand)
            
        return self._make_request('GET', f'api/3/issue/{key}', params=params)    
    
    def fetch_issues_since(
        self,
        project_keys: List[str],
        since: datetime,
        expand_changelog: bool = True
    ) -> Generator[Dict, None, None]:
        """
        Fetch issues updated since a timestamp.
        
        Args:
            project_keys: List of project keys
            since: Fetch issues updated after this time
            expand_changelog: Whether to expand changelog
            
        Yields:
            Issue dictionaries
        """
        keys_str = ', '.join(project_keys)
        since_str = since.strftime('%Y-%m-%d %H:%M')
        jql = f'project in ({keys_str}) AND updated >= "{since_str}" ORDER BY updated ASC'
        
        expand = ['changelog'] if expand_changelog else None
        
        yield from self.fetch_issues(jql, expand=expand)
    
    def fetch_issue(self, issue_key: str, expand: List[str] = None) -> Dict:
        """Fetch a single issue by key."""
        params = {}
        if expand:
            params['expand'] = ','.join(expand)
        
        return self._make_request('GET', f'api/3/issue/{issue_key}', params=params)
    
    def fetch_issue_changelog(self, issue_key: str) -> List[Dict]:
        """Fetch changelog for an issue."""
        result = []
        for item in self._paginate(f'api/3/issue/{issue_key}/changelog', data_key='values'):
            result.append(item)
        return result
    
    def fetch_issue_comments(self, issue_key: str) -> List[Dict]:
        """Fetch comments for an issue."""
        result = []
        for item in self._paginate(f'api/3/issue/{issue_key}/comment', data_key='comments'):
            result.append(item)
        return result
    
    def fetch_issue_worklogs(self, issue_key: str) -> List[Dict]:
        """Fetch worklogs for an issue."""
        result = []
        for item in self._paginate(f'api/3/issue/{issue_key}/worklog', data_key='worklogs'):
            result.append(item)
        return result
    
    # ========================================
    # Board & Sprint Methods (Agile API)
    # ========================================
    
    def fetch_boards(self, project_key: str = None) -> List[Dict]:
        """Fetch all boards, optionally filtered by project."""
        params = {}
        if project_key:
            params['projectKeyOrId'] = project_key
        
        result = []
        for item in self._paginate('agile/1.0/board', params=params, data_key='values'):
            result.append(item)
        
        logger.info(f"Fetched {len(result)} boards")
        return result
    
    def fetch_board(self, board_id: int) -> Dict:
        """Fetch a single board."""
        return self._make_request('GET', f'agile/1.0/board/{board_id}')
    
    def fetch_board_configuration(self, board_id: int) -> Dict:
        """Fetch board configuration (columns, swimlanes)."""
        return self._make_request('GET', f'agile/1.0/board/{board_id}/configuration')
    
    def fetch_sprints(self, board_id: int, state: str = None) -> List[Dict]:
        """
        Fetch sprints for a board.
        
        Args:
            board_id: Board ID
            state: Filter by state ('active', 'closed', 'future')
        """
        params = {}
        if state:
            params['state'] = state
        
        result = []
        for item in self._paginate(f'agile/1.0/board/{board_id}/sprint', params=params, data_key='values'):
            result.append(item)
        
        return result
    
    def fetch_sprint_issues(self, sprint_id: int) -> List[Dict]:
        """Fetch issues in a sprint."""
        result = []
        for item in self._paginate(f'agile/1.0/sprint/{sprint_id}/issue', data_key='issues'):
            result.append(item)
        return result
    
    # ========================================
    # Reference Data Methods
    # ========================================
    
    def fetch_statuses(self) -> List[Dict]:
        """Fetch all statuses."""
        return self._make_request('GET', 'api/3/status')
    
    def fetch_priorities(self) -> List[Dict]:
        """Fetch all priorities."""
        return self._make_request('GET', 'api/3/priority')
    
    def fetch_issue_types(self) -> List[Dict]:
        """Fetch all issue types."""
        return self._make_request('GET', 'api/3/issuetype')
    
    def fetch_resolutions(self) -> List[Dict]:
        """Fetch all resolutions."""
        return self._make_request('GET', 'api/3/resolution')
    
    def fetch_issue_link_types(self) -> List[Dict]:
        """Fetch all issue link types."""
        response = self._make_request('GET', 'api/3/issueLinkType')
        return response.get('issueLinkTypes', [])
    
    def fetch_fields(self) -> List[Dict]:
        """Fetch all available fields including custom fields."""
        return self._make_request('GET', 'api/3/field')
    
    def fetch_labels(self) -> List[str]:
        """Fetch all labels (requires searching issues)."""
        # Labels are extracted from issues, not a direct API endpoint
        # This is a helper that would need to aggregate from issue fetches
        logger.warning("Labels are extracted from issues, not fetched directly")
        return []
    
    # ========================================
    # User Methods
    # ========================================
    
    def fetch_user(self, account_id: str) -> Dict:
        """Fetch user by account ID."""
        return self._make_request('GET', 'api/3/user', params={'accountId': account_id})
    
    def fetch_users_in_project(self, project_key: str) -> List[Dict]:
        """Fetch users assignable in a project."""
        result = []
        for user in self._paginate(
            'api/3/user/assignable/search',
            params={'project': project_key},
            data_key='values'
        ):
            result.append(user)
        return result
    
    # ========================================
    # Utility Methods
    # ========================================
    
    def test_connection(self) -> bool:
        """Test connection to Jira API."""
        try:
            self._make_request('GET', 'api/3/myself')
            logger.info("Jira connection test successful")
            return True
        except JiraAPIError as e:
            logger.error(f"Jira connection test failed: {e.message}")
            return False
    
    def get_server_info(self) -> Dict:
        """Get Jira server information."""
        return self._make_request('GET', 'api/3/serverInfo')


# Convenience function
def get_jira_client() -> JiraClient:
    """Get Jira client instance."""
    return JiraClient()
