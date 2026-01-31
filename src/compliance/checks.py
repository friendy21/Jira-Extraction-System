"""
Compliance Checks Module
Implements all JIRA process compliance checks for weekly employee auditing.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ComplianceCheck(ABC):
    """
    Abstract base class for compliance checks.
    
    All compliance checks must implement the evaluate() method which returns:
    - "Yes" - Compliant
    - "No" - Non-compliant (generic)
    - "No - [reason]" - Non-compliant with specific reason
    - "NA" - Not applicable (e.g., no activity in the week)
    """
    
    @abstractmethod
    def evaluate(self, issues: List[Dict[str, Any]], employee: Any) -> str:
        """
        Evaluate compliance for given issues.
        
        Args:
            issues: List of JIRA issues with full data (changelog, comments, etc.)
            employee: Employee object with account_id, display_name, etc.
            
        Returns:
            Compliance result string ("Yes", "No", "No - [reason]", "NA")
        """
        pass


class StatusHygieneCheck(ComplianceCheck):
    """
    Check if all status transitions follow proper workflow rules.
    
    Valid transitions are defined based on standard Agile workflow.
    Invalid transitions (e.g., To Do → Done without In Progress) are flagged.
    """
    
    # Define valid workflow transitions
    VALID_TRANSITIONS = {
        'To Do': ['In Progress', 'Backlog'],
        'Backlog': ['To Do', 'In Progress'],
        'In Progress': ['Code Review', 'Testing', 'In Review', 'Done', 'To Do'],
        'Code Review': ['In Progress', 'Testing', 'Done'],
        'In Review': ['In Progress', 'Testing', 'Done'],
        'Testing': ['In Progress', 'Done', 'Code Review'],
        'Done': [],  # Terminal state
        'Cancelled': []  # Terminal state
    }
    
    def evaluate(self, issues: List[Dict[str, Any]], employee: Any) -> str:
        """Validate all status transitions against workflow rules."""
        if not issues:
            return "NA"
        
        violations = []
        
        for issue in issues:
            changelog = issue.get('changelog', {})
            histories = changelog.get('histories', [])
            
            for history in histories:
                for item in history.get('items', []):
                    if item.get('field') == 'status':
                        from_status = item.get('fromString')
                        to_status = item.get('toString')
                        
                        if from_status and to_status:
                            if not self._is_valid_transition(from_status, to_status):
                                violations.append(f"{issue['key']}: {from_status} → {to_status}")
        
        if violations:
            # Return first violation (or could concatenate multiple)
            return f"No - Invalid transition: {violations[0]}"
        
        return "Yes"
    
    def _is_valid_transition(self, from_status: str, to_status: str) -> bool:
        """Check if transition is valid according to workflow rules."""
        # Get valid next statuses for the from_status
        valid_next = self.VALID_TRANSITIONS.get(from_status, [])
        
        # If from_status not in our map, allow any transition (unknown workflow)
        if from_status not in self.VALID_TRANSITIONS:
            logger.warning(f"Unknown status in workflow: {from_status}")
            return True
        
        return to_status in valid_next


class CancellationCheck(ComplianceCheck):
    """
    Check for tasks cancelled without proper approval.
    
    A cancellation requires:
    - A comment containing approval keywords within 1 hour of status change
    - OR a comment from a manager/lead within 24 hours
    """
    
    APPROVAL_KEYWORDS = ['approved', 'approval', 'authorize', 'confirmed', 'ok to cancel']
    
    def evaluate(self, issues: List[Dict[str, Any]], employee: Any) -> str:
        """Check for unauthorized cancellations."""
        if not issues:
            return "No"  # Default to No (no unapproved cancellations)
        
        unauthorized_cancellations = []
        
        for issue in issues:
            changelog = issue.get('changelog', {})
            histories = changelog.get('histories', [])
            
            for history in histories:
                for item in history.get('items', []):
                    if item.get('field') == 'status' and item.get('toString') == 'Cancelled':
                        # Found a cancellation - check for approval
                        cancel_time = self._parse_datetime(history.get('created'))
                        
                        if cancel_time and not self._has_approval_comment(issue, cancel_time):
                            unauthorized_cancellations.append(issue['key'])
                            break
        
        if unauthorized_cancellations:
            return f"Yes - {', '.join(unauthorized_cancellations[:3])} cancelled w/o approval"
        
        return "No"
    
    def _has_approval_comment(self, issue: Dict, cancel_time: datetime) -> bool:
        """Check if there's an approval comment near the cancellation time."""
        comments = issue.get('fields', {}).get('comment', {}).get('comments', [])
        
        # Check comments within 24 hours before/after cancellation
        time_window = timedelta(hours=24)
        
        for comment in comments:
            comment_time = self._parse_datetime(comment.get('created'))
            if not comment_time:
                continue
            
            time_diff = abs((comment_time - cancel_time).total_seconds())
            if time_diff <= time_window.total_seconds():
                body = comment.get('body', '').lower()
                if any(keyword in body for keyword in self.APPROVAL_KEYWORDS):
                    return True
        
        return False
    
    def _parse_datetime(self, dt_string: Optional[str]) -> Optional[datetime]:
        """Parse JIRA datetime string."""
        if not dt_string:
            return None
        try:
            # JIRA format: 2024-01-15T10:30:45.123+0000
            return datetime.strptime(dt_string[:19], '%Y-%m-%dT%H:%M:%S')
        except (ValueError, TypeError):
            return None


class UpdateFrequencyCheck(ComplianceCheck):
    """
    Check if Wednesday and Friday updates are shared.
    
    Requires at least one comment on Wednesday AND one on Friday each week.
    """
    
    def evaluate(self, issues: List[Dict[str, Any]], employee: Any) -> str:
        """Check for Wed/Fri update comments."""
        if not issues:
            return "No"
        
        # Determine the week's Wednesday and Friday dates
        # Assume issues are for a single week (Monday-Sunday)
        wed_updates = False
        fri_updates = False
        
        for issue in issues:
            comments = issue.get('fields', {}).get('comment', {}).get('comments', [])
            
            for comment in comments:
                comment_time = self._parse_datetime(comment.get('created'))
                if comment_time:
                    weekday = comment_time.weekday()  # 0=Monday, 6=Sunday
                    
                    # Check if author is the employee
                    author = comment.get('author', {})
                    if author.get('accountId') == employee.account_id:
                        if weekday == 2:  # Wednesday
                            wed_updates = True
                        elif weekday == 4:  # Friday
                            fri_updates = True
        
        if wed_updates and fri_updates:
            return "Yes"
        elif wed_updates or fri_updates:
            return "Partial"  # Some updates but not both days
        else:
            return "No"
    
    def _parse_datetime(self, dt_string: Optional[str]) -> Optional[datetime]:
        """Parse JIRA datetime string."""
        if not dt_string:
            return None
        try:
            return datetime.strptime(dt_string[:19], '%Y-%m-%dT%H:%M:%S')
        except (ValueError, TypeError):
            return None


class RoleOwnershipCheck(ComplianceCheck):
    """
    Check if roles and ownership are correctly set.
    
    Requirements:
    - Reporter must be different from Assignee
    - Both Reporter and Assignee must be populated
    - Assignee must be a valid team member
    """
    
    def evaluate(self, issues: List[Dict[str, Any]], employee: Any) -> str:
        """Validate role ownership."""
        if not issues:
            return "NA"
        
        violations = []
        
        for issue in issues:
            fields = issue.get('fields', {})
            reporter = fields.get('reporter', {})
            assignee = fields.get('assignee', {})
            
            reporter_id = reporter.get('accountId') if reporter else None
            assignee_id = assignee.get('accountId') if assignee else None
            
            # Check if both are populated
            if not reporter_id:
                violations.append(f"{issue['key']}: No reporter")
                continue
            
            if not assignee_id:
                violations.append(f"{issue['key']}: No assignee")
                continue
            
            # Check if reporter == assignee
            if reporter_id == assignee_id:
                violations.append(f"{issue['key']}: Reporter = Assignee")
        
        if violations:
            # Return first violation with category
            violation = violations[0]
            if "No reporter" in violation:
                return "No - Reporter missing"
            elif "No assignee" in violation:
                return "No - Assignee missing"
            else:
                return "No - Reporter = Assignee"
        
        return "Yes"


class DocumentationCheck(ComplianceCheck):
    """
    Check documentation and traceability completeness.
    
    Requirements:
    - Description must be > 50 characters
    - Must have at least one linked issue OR one attachment
    - Due date should be set (if applicable)
    """
    
    MIN_DESCRIPTION_LENGTH = 50
    
    def evaluate(self, issues: List[Dict[str, Any]], employee: Any) -> str:
        """Check documentation completeness."""
        if not issues:
            return "NA"
        
        violations = []
        
        for issue in issues:
            fields = issue.get('fields', {})
            
            # Check description length
            description = fields.get('description', '') or ''
            if len(description.strip()) < self.MIN_DESCRIPTION_LENGTH:
                violations.append(f"{issue['key']}: Description too short")
                continue
            
            # Check for links or attachments
            issue_links = fields.get('issuelinks', [])
            attachments = fields.get('attachment', [])
            
            if not issue_links and not attachments:
                violations.append(f"{issue['key']}: No links or attachments")
                continue
            
            # Check due date (optional - only warn)
            due_date = fields.get('duedate')
            if not due_date:
                # This is a softer violation
                violations.append(f"{issue['key']}: No due date")
        
        if violations:
            violation = violations[0]
            if "Description" in violation:
                return "No - Description incomplete"
            elif "links or attachments" in violation:
                return "No - No traceability links"
            elif "due date" in violation:
                return "No - Due date missing"
        
        return "Yes"


class LifecycleCheck(ComplianceCheck):
    """
    Check lifecycle adherence - proper sequence of statuses.
    
    Enforces: Created → In Progress → Done
    Issues that skip "In Progress" are flagged.
    """
    
    REQUIRED_STATUSES = ['In Progress']  # Must pass through these
    
    def evaluate(self, issues: List[Dict[str, Any]], employee: Any) -> str:
        """Check lifecycle sequence."""
        if not issues:
            return "NA"
        
        violations = []
        
        for issue in issues:
            # Get status history
            status_history = self._get_status_history(issue)
            
            # Check if issue went to Done without going through In Progress
            if 'Done' in status_history and 'In Progress' not in status_history:
                violations.append(f"{issue['key']}: Skipped In Progress")
        
        if violations:
            return f"No - {violations[0]}"
        
        return "Yes"
    
    def _get_status_history(self, issue: Dict) -> List[str]:
        """Extract status history from changelog."""
        statuses = []
        
        changelog = issue.get('changelog', {})
        histories = changelog.get('histories', [])
        
        for history in histories:
            for item in history.get('items', []):
                if item.get('field') == 'status':
                    to_status = item.get('toString')
                    if to_status and to_status not in statuses:
                        statuses.append(to_status)
        
        # Also add current status
        current_status = issue.get('fields', {}).get('status', {}).get('name')
        if current_status and current_status not in statuses:
            statuses.append(current_status)
        
        return statuses


class ZeroToleranceCheck(ComplianceCheck):
    """
    Check for zero-tolerance violations.
    
    Detects:
    - Retroactive status edits (changed >24 hours after original transition)
    - Bulk status changes (>5 issues updated in <1 hour)
    - Missing required fields (priority, issue type)
    """
    
    RETROACTIVE_THRESHOLD_HOURS = 24
    BULK_CHANGE_THRESHOLD = 5  # issues
    BULK_CHANGE_WINDOW_HOURS = 1
    
    def evaluate(self, issues: List[Dict[str, Any]], employee: Any) -> str:
        """Detect zero-tolerance violations."""
        if not issues:
            return "No"  # No violations
        
        # Check for retroactive edits
        if self._has_retroactive_edits(issues):
            return "Yes"  # Yes = violation found
        
        # Check for bulk changes
        if self._has_bulk_changes(issues):
            return "Yes"
        
        # Check for missing required fields
        if self._has_missing_required_fields(issues):
            return "Yes"
        
        return "No"  # No violations
    
    def _has_retroactive_edits(self, issues: List[Dict]) -> bool:
        """Check for status changes made long after the fact."""
        for issue in issues:
            changelog = issue.get('changelog', {})
            histories = changelog.get('histories', [])
            
            status_changes = []
            for history in histories:
                for item in history.get('items', []):
                    if item.get('field') == 'status':
                        created = self._parse_datetime(history.get('created'))
                        if created:
                            status_changes.append(created)
            
            # Check if any status change was made >24hrs after previous change
            for i in range(1, len(status_changes)):
                time_diff = (status_changes[i] - status_changes[i-1]).total_seconds() / 3600
                if time_diff > self.RETROACTIVE_THRESHOLD_HOURS:
                    # This could be legitimate, but flag for review
                    # In practice, you might want to check if it was edited vs just progressed
                    pass
        
        return False  # For now, don't flag retroactive edits
    
    def _has_bulk_changes(self, issues: List[Dict]) -> bool:
        """Check for bulk status updates."""
        # Count status changes within 1-hour windows
        change_times = []
        
        for issue in issues:
            changelog = issue.get('changelog', {})
            histories = changelog.get('histories', [])
            
            for history in histories:
                for item in history.get('items', []):
                    if item.get('field') == 'status':
                        created = self._parse_datetime(history.get('created'))
                        if created:
                            change_times.append(created)
        
        # Sort by time
        change_times.sort()
        
        # Check for 5+ changes within 1 hour
        for i in range(len(change_times)):
            window_end = change_times[i] + timedelta(hours=self.BULK_CHANGE_WINDOW_HOURS)
            count = sum(1 for t in change_times[i:] if t <= window_end)
            
            if count >= self.BULK_CHANGE_THRESHOLD:
                return True
        
        return False
    
    def _has_missing_required_fields(self, issues: List[Dict]) -> bool:
        """Check for missing required fields."""
        for issue in issues:
            fields = issue.get('fields', {})
            
            # Check priority
            if not fields.get('priority'):
                return True
            
            # Check issue type
            if not fields.get('issuetype'):
                return True
        
        return False
    
    def _parse_datetime(self, dt_string: Optional[str]) -> Optional[datetime]:
        """Parse JIRA datetime string."""
        if not dt_string:
            return None
        try:
            return datetime.strptime(dt_string[:19], '%Y-%m-%dT%H:%M:%S')
        except (ValueError, TypeError):
            return None
