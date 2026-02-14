"""
Helper Utilities Module
Common utility functions used across the application.
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from dateutil import parser as date_parser
import pytz


def parse_jira_datetime(dt_string: Optional[str]) -> Optional[datetime]:
    """
    Parse Jira datetime string to Python datetime.
    
    Args:
        dt_string: Jira datetime string (ISO 8601 format)
        
    Returns:
        datetime object or None if parsing fails
    """
    if not dt_string:
        return None
    
    try:
        return date_parser.parse(dt_string)
    except (ValueError, TypeError):
        return None


def parse_jira_date(date_string: Optional[str]) -> Optional[datetime]:
    """
    Parse Jira date string (YYYY-MM-DD) to Python date.
    
    Args:
        date_string: Date string in YYYY-MM-DD format
        
    Returns:
        date object or None if parsing fails
    """
    if not date_string:
        return None
    
    try:
        return datetime.strptime(date_string, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def seconds_to_hours(seconds: Optional[int]) -> Optional[float]:
    """Convert seconds to hours with 2 decimal places."""
    if seconds is None:
        return None
    return round(seconds / 3600, 2)


def hours_to_seconds(hours: Optional[float]) -> Optional[int]:
    """Convert hours to seconds."""
    if hours is None:
        return None
    return int(hours * 3600)


def calculate_duration_hours(start: datetime, end: datetime) -> float:
    """
    Calculate duration in hours between two datetimes.
    
    Args:
        start: Start datetime
        end: End datetime
        
    Returns:
        Duration in hours
    """
    if not start or not end:
        return 0.0
    
    delta = end - start
    return round(delta.total_seconds() / 3600, 2)


def calculate_business_days(start: datetime, end: datetime) -> int:
    """
    Calculate business days between two dates (excluding weekends).
    
    Args:
        start: Start date
        end: End date
        
    Returns:
        Number of business days
    """
    if not start or not end:
        return 0
    
    # Ensure we're working with dates
    if hasattr(start, 'date'):
        start = start.date()
    if hasattr(end, 'date'):
        end = end.date()
    
    business_days = 0
    current = start
    
    while current <= end:
        if current.weekday() < 5:  # Monday = 0, Friday = 4
            business_days += 1
        current += timedelta(days=1)
    
    return business_days


def extract_issue_key(text: str) -> Optional[str]:
    """
    Extract Jira issue key from text.
    
    Args:
        text: Text containing issue key
        
    Returns:
        Issue key or None
    """
    if not text:
        return None
    
    pattern = r'([A-Z][A-Z0-9]+-\d+)'
    match = re.search(pattern, text)
    return match.group(1) if match else None


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def safe_get(data: Dict, *keys, default=None) -> Any:
    """
    Safely get nested dictionary value.
    
    Args:
        data: Dictionary to traverse
        *keys: Keys to follow
        default: Default value if key not found
        
    Returns:
        Value at path or default
    """
    result = data
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
        else:
            return default
        if result is None:
            return default
    return result


def sanitize_string(text: Optional[str], max_length: int = None) -> Optional[str]:
    """
    Sanitize string for database storage.
    
    Args:
        text: Text to sanitize
        max_length: Maximum length (truncate if exceeded)
        
    Returns:
        Sanitized string
    """
    if text is None:
        return None
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Truncate if needed
    if max_length and len(text) > max_length:
        text = text[:max_length - 3] + '...'
    
    return text


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "2h 30m")
    """
    if not seconds:
        return "0m"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or not parts:
        parts.append(f"{minutes}m")
    
    return " ".join(parts)


def get_date_range(days: int) -> tuple:
    """
    Get date range for the past N days.
    
    Args:
        days: Number of days to look back
        
    Returns:
        Tuple of (start_date, end_date)
    """
    end_date = datetime.now(pytz.UTC)
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


def build_jql(project_keys: List[str], additional_clauses: List[str] = None) -> str:
    """
    Build JQL query string.
    
    Args:
        project_keys: List of project keys
        additional_clauses: Additional JQL clauses
        
    Returns:
        JQL query string
    """
    clauses = []
    
    if project_keys:
        keys_str = ', '.join(f'"{k}"' for k in project_keys)
        clauses.append(f"project in ({keys_str})")
    
    if additional_clauses:
        clauses.extend(additional_clauses)
    
    return ' AND '.join(clauses) if clauses else ''
