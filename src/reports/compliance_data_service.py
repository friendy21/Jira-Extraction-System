"""
Compliance Data Service Module
Provides live compliance data for dashboard display.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import time

from src.compliance.checks import (
    StatusHygieneCheck,
    CancellationCheck,
    UpdateFrequencyCheck,
    RoleOwnershipCheck,
    DocumentationCheck,
    LifecycleCheck,
    ZeroToleranceCheck
)
from src.jira_client import JiraClient
from src.database.connection import get_session
from src.database.models import JiraUser
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ComplianceDataService:
    """
    Service for generating live compliance data for dashboard display.
    
    Provides JSON-formatted compliance data with caching to reduce JIRA API calls.
    """
    
    def __init__(self, jira_client: JiraClient):
        """
        Initialize compliance data service.
        
        Args:
            jira_client: Authenticated JIRA client instance
        """
        self.jira = jira_client
        
        # Initialize compliance checks
        self.checks = {
            'status_hygiene': StatusHygieneCheck(),
            'cancellation': CancellationCheck(),
            'update_frequency': UpdateFrequencyCheck(),
            'role_ownership': RoleOwnershipCheck(),
            'documentation': DocumentationCheck(),
            'lifecycle': LifecycleCheck(),
            'zero_tolerance': ZeroToleranceCheck()
        }
        
        # Simple in-memory cache
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
        
        logger.info("Compliance data service initialized")
    
    def get_live_data(
        self,
        team_id: Optional[int] = None,
        week_offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get live compliance data for specified week.
        
        Args:
            team_id: Optional team filter
            week_offset: Number of weeks back from current (0 = current week)
            
        Returns:
            List of compliance records as dictionaries
        """
        # Generate cache key
        cache_key = f"team_{team_id}_week_{week_offset}"
        
        # Check cache
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                logger.debug(f"Returning cached data for {cache_key}")
                return cached_data
        
        logger.info(f"Generating live compliance data: team_id={team_id}, week_offset={week_offset}")
        
        # Calculate week dates
        today = datetime.now()
        week_start = self._get_week_start(today, week_offset)
        week_end = week_start + timedelta(days=6)
        
        # Get active employees
        employees = self._get_active_employees(team_id)
        
        # Generate compliance data
        compliance_data = []
        for employee in employees:
            record = self._evaluate_employee_week(employee, week_start, week_end)
            if record:  # Only include if employee had activity
                compliance_data.append(record)
        
        # Cache the results
        self._cache[cache_key] = (compliance_data, time.time())
        
        logger.info(f"Generated {len(compliance_data)} compliance records")
        return compliance_data
    
    def _get_week_start(self, date: datetime, week_offset: int) -> datetime:
        """
        Get Monday of the week for given date and offset.
        
        Args:
            date: Reference date
            week_offset: Number of weeks to go back
            
        Returns:
            Monday of the target week
        """
        # Go to Monday of current week
        monday = date - timedelta(days=date.weekday())
        
        # Apply offset
        target_monday = monday - timedelta(weeks=week_offset)
        
        # Set to start of day
        return target_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def _get_active_employees(self, team_id: Optional[int]) -> List[JiraUser]:
        """
        Get list of active employees.
        
        Args:
            team_id: Optional team filter
            
        Returns:
            List of JiraUser objects
        """
        with get_session() as session:
            query = session.query(JiraUser).filter(JiraUser.active == True)
            
            # TODO: Add team filtering when team-user mapping is available
            # if team_id:
            #     query = query.join(...).filter(Team.id == team_id)
            
            employees = query.order_by(JiraUser.display_name).all()
            
            logger.debug(f"Found {len(employees)} active employees")
            return employees
    
    def _evaluate_employee_week(
        self,
        employee: JiraUser,
        week_start: datetime,
        week_end: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate compliance for employee during specific week.
        
        Args:
            employee: JiraUser object
            week_start: Monday of the week
            week_end: Sunday of the week
            
        Returns:
            Compliance data dictionary or None if no activity
        """
        # Get employee's issues for the week
        issues = self._get_employee_issues(employee, week_start, week_end)
        
        if not issues:
            logger.debug(f"No activity for {employee.display_name} week of {week_start.date()}")
            return None
        
        logger.debug(f"Evaluating {employee.display_name} week of {week_start.date()} ({len(issues)} issues)")
        
        # Run all compliance checks
        results = {}
        for check_name, check in self.checks.items():
            try:
                results[check_name] = check.evaluate(issues, employee)
            except Exception as e:
                logger.error(f"Check {check_name} failed for {employee.display_name}: {e}")
                results[check_name] = "Error"
        
        # Calculate overall compliance
        overall = self._calculate_overall_compliance(results)
        
        # Generate auditor notes
        notes = self._generate_auditor_notes(results)
        
        # Return JSON-serializable dictionary
        return {
            'employee_name': employee.display_name,
            'week_start_date': week_start.strftime('%Y-%m-%d'),
            'status_hygiene': results['status_hygiene'],
            'cancellation': results['cancellation'],
            'update_frequency': results['update_frequency'],
            'role_ownership': results['role_ownership'],
            'documentation': results['documentation'],
            'lifecycle': results['lifecycle'],
            'zero_tolerance': results['zero_tolerance'],
            'overall_compliance': overall,
            'auditor_notes': notes
        }
    
    def _get_employee_issues(
        self,
        employee: JiraUser,
        week_start: datetime,
        week_end: datetime
    ) -> List[Dict[str, Any]]:
        """
        Fetch employee's JIRA issues for the week.
        
        Args:
            employee: JiraUser object
            week_start: Week start (Monday)
            week_end: Week end (Sunday)
            
        Returns:
            List of issue dictionaries with full data
        """
        try:
            # Build JQL query for employee's issues in the week
            jql = f'''
                (assignee = "{employee.account_id}" OR reporter = "{employee.account_id}")
                AND updated >= "{week_start.strftime('%Y-%m-%d')}"
                AND updated <= "{week_end.strftime('%Y-%m-%d')}"
            '''
            
            # Fetch issues with changelog and comments expanded
            issues = list(self.jira.fetch_issues(
                jql=jql.strip(),
                fields=['*all'],
                expand=['changelog', 'renderedFields'],
                max_results=100
            ))
            
            logger.debug(f"Fetched {len(issues)} issues for {employee.display_name}")
            return issues
            
        except Exception as e:
            logger.error(f"Failed to fetch issues for {employee.display_name}: {e}")
            return []
    
    def _calculate_overall_compliance(self, results: Dict[str, str]) -> str:
        """
        Calculate overall pass/fail based on all checks.
        
        Logic: Fail if ANY check is "No" or contains "No -" or zero-tolerance violation
        """
        for check_name, result in results.items():
            # Check for "No" or "No - [reason]"
            if result.startswith("No"):
                return "Fail"
            
            # Zero-tolerance: "Yes" means violation found (inverted logic)
            if check_name == 'zero_tolerance' and result == "Yes":
                return "Fail"
            
            # Error in check
            if result == "Error":
                return "Fail"
        
        return "Pass"
    
    def _generate_auditor_notes(self, results: Dict[str, str]) -> str:
        """Generate human-readable notes from compliance results."""
        issues = []
        
        for check_name, result in results.items():
            # Extract reasons from "No - [reason]" format
            if result.startswith("No -"):
                issues.append(result[5:])  # Extract reason after "No - "
            elif result.startswith("Yes -") and check_name == 'cancellation':
                # Cancellation has "Yes - [details]" format
                issues.append(result[6:])
            elif result == "No" and check_name == 'cancellation':
                # No cancellation is good, skip
                pass
            elif result == "No":
                # Generic "No" without reason
                check_display = check_name.replace('_', ' ').title()
                issues.append(f"{check_display} failed")
            elif check_name == 'zero_tolerance' and result == "Yes":
                issues.append("Zero-tolerance violation detected")
            elif result == "Error":
                issues.append(f"{check_name.replace('_', ' ').title()} check error")
        
        return "; ".join(issues) if issues else "All checks passed"
    
    def clear_cache(self):
        """Clear the data cache."""
        self._cache.clear()
        logger.info("Cache cleared")
