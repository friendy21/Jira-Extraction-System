"""
Unit Tests for Compliance Checks
Tests each compliance check with mock JIRA data.
"""

import unittest
from datetime import datetime
from unittest.mock import Mock

from src.compliance.checks import (
    StatusHygieneCheck,
    CancellationCheck,
    UpdateFrequencyCheck,
    RoleOwnershipCheck,
    DocumentationCheck,
    LifecycleCheck,
    ZeroToleranceCheck
)


class TestStatusHygieneCheck(unittest.TestCase):
    """Test status hygiene compliance check."""
    
    def setUp(self):
        self.check = StatusHygieneCheck()
        self.employee = Mock(account_id='user123', display_name='Test User')
    
    def test_valid_transitions(self):
        """Test that valid transitions pass."""
        issues = [{
            'key': 'TEST-1',
            'changelog': {
                'histories': [
                    {
                        'created': '2026-01-20T10:00:00.000+0000',
                        'items': [{
                            'field': 'status',
                            'fromString': 'To Do',
                            'toString': 'In Progress'
                        }]
                    },
                    {
                        'created': '2026-01-21T15:00:00.000+0000',
                        'items': [{
                            'field': 'status',
                            'fromString': 'In Progress',
                            'toString': 'Done'
                        }]
                    }
                ]
            }
        }]
        
        result = self.check.evaluate(issues, self.employee)
        self.assertEqual(result, "Yes")
    
    def test_invalid_transitions(self):
        """Test that invalid transitions fail."""
        issues = [{
            'key': 'TEST-2',
            'changelog': {
                'histories': [
                    {
                        'created': '2026-01-20T10:00:00.000+0000',
                        'items': [{
                            'field': 'status',
                            'fromString': 'To Do',
                            'toString': 'Done'  # Invalid - skipped In Progress
                        }]
                    }
                ]
            }
        }]
        
        result = self.check.evaluate(issues, self.employee)
        self.assertTrue(result.startswith("No"))
        self.assertIn("Invalid transition", result)
    
    def test_no_issues(self):
        """Test with no issues returns NA."""
        result = self.check.evaluate([], self.employee)
        self.assertEqual(result, "NA")


class TestCancellationCheck(unittest.TestCase):
    """Test cancellation compliance check."""
    
    def setUp(self):
        self.check = CancellationCheck()
        self.employee = Mock(account_id='user123', display_name='Test User')
    
    def test_no_cancellations(self):
        """Test that no cancellations returns No (good)."""
        issues = [{
            'key': 'TEST-1',
            'changelog': {
                'histories': [
                    {
                        'created': '2026-01-20T10:00:00.000+0000',
                        'items': [{
                            'field': 'status',
                            'fromString': 'To Do',
                            'toString': 'In Progress'
                        }]
                    }
                ]
            },
            'fields': {
                'comment': {
                    'comments': []
                }
            }
        }]
        
        result = self.check.evaluate(issues, self.employee)
        self.assertEqual(result, "No")
    
    def test_cancellation_with_approval(self):
        """Test cancellation with approval comment passes."""
        issues = [{
            'key': 'TEST-2',
            'changelog': {
                'histories': [
                    {
                        'created': '2026-01-20T10:00:00.000+0000',
                        'items': [{
                            'field': 'status',
                            'fromString': 'In Progress',
                            'toString': 'Cancelled'
                        }]
                    }
                ]
            },
            'fields': {
                'comment': {
                    'comments': [
                        {
                            'created': '2026-01-20T09:50:00.000+0000',
                            'body': 'This task has been approved for cancellation by the manager.'
                        }
                    ]
                }
            }
        }]
        
        result = self.check.evaluate(issues, self.employee)
        self.assertEqual(result, "No")  # No violations
    
    def test_cancellation_without_approval(self):
        """Test cancellation without approval fails."""
        issues = [{
            'key': 'TEST-3',
            'changelog': {
                'histories': [
                    {
                        'created': '2026-01-20T10:00:00.000+0000',
                        'items': [{
                            'field': 'status',
                            'fromString': 'In Progress',
                            'toString': 'Cancelled'
                        }]
                    }
                ]
            },
            'fields': {
                'comment': {
                    'comments': []
                }
            }
        }]
        
        result = self.check.evaluate(issues, self.employee)
        self.assertTrue(result.startswith("Yes"))
        self.assertIn("TEST-3", result)


class TestRoleOwnershipCheck(unittest.TestCase):
    """Test role ownership compliance check."""
    
    def setUp(self):
        self.check = RoleOwnershipCheck()
        self.employee = Mock(account_id='user123', display_name='Test User')
    
    def test_valid_roles(self):
        """Test valid reporter and assignee."""
        issues = [{
            'key': 'TEST-1',
            'fields': {
                'reporter': {'accountId': 'user123'},
                'assignee': {'accountId': 'user456'}
            }
        }]
        
        result = self.check.evaluate(issues, self.employee)
        self.assertEqual(result, "Yes")
    
    def test_missing_reporter(self):
        """Test missing reporter fails."""
        issues = [{
            'key': 'TEST-2',
            'fields': {
                'reporter': None,
                'assignee': {'accountId': 'user456'}
            }
        }]
        
        result = self.check.evaluate(issues, self.employee)
        self.assertEqual(result, "No - Reporter missing")
    
    def test_missing_assignee(self):
        """Test missing assignee fails."""
        issues = [{
            'key': 'TEST-3',
            'fields': {
                'reporter': {'accountId': 'user123'},
                'assignee': None
            }
        }]
        
        result = self.check.evaluate(issues, self.employee)
        self.assertEqual(result, "No - Assignee missing")
    
    def test_reporter_equals_assignee(self):
        """Test reporter == assignee fails."""
        issues = [{
            'key': 'TEST-4',
            'fields': {
                'reporter': {'accountId': 'user123'},
                'assignee': {'accountId': 'user123'}
            }
        }]
        
        result = self.check.evaluate(issues, self.employee)
        self.assertEqual(result, "No - Reporter = Assignee")


class TestDocumentationCheck(unittest.TestCase):
    """Test documentation compliance check."""
    
    def setUp(self):
        self.check = DocumentationCheck()
        self.employee = Mock(account_id='user123', display_name='Test User')
    
    def test_complete_documentation(self):
        """Test complete documentation passes."""
        issues = [{
            'key': 'TEST-1',
            'fields': {
                'description': 'This is a detailed description with more than 50 characters to meet the requirement.',
                'issuelinks': [{'id': '12345'}],
                'attachment': [],
                'duedate': '2026-02-01'
            }
        }]
        
        result = self.check.evaluate(issues, self.employee)
        self.assertEqual(result, "Yes")
    
    def test_short_description(self):
        """Test short description fails."""
        issues = [{
            'key': 'TEST-2',
            'fields': {
                'description': 'Short',
                'issuelinks': [{'id': '12345'}],
                'attachment': []
            }
        }]
        
        result = self.check.evaluate(issues, self.employee)
        self.assertEqual(result, "No - Description incomplete")
    
    def test_no_links_or_attachments(self):
        """Test no links or attachments fails."""
        issues = [{
            'key': 'TEST-3',
            'fields': {
                'description': 'This is a detailed description with more than 50 characters.',
                'issuelinks': [],
                'attachment': []
            }
        }]
        
        result = self.check.evaluate(issues, self.employee)
        self.assertEqual(result, "No - No traceability links")


class TestLifecycleCheck(unittest.TestCase):
    """Test lifecycle adherence check."""
    
    def setUp(self):
        self.check = LifecycleCheck()
        self.employee = Mock(account_id='user123', display_name='Test User')
    
    def test_proper_lifecycle(self):
        """Test proper lifecycle passes."""
        issues = [{
            'key': 'TEST-1',
            'changelog': {
                'histories': [
                    {
                        'items': [{
                            'field': 'status',
                            'toString': 'In Progress'
                        }]
                    },
                    {
                        'items': [{
                            'field': 'status',
                            'toString': 'Done'
                        }]
                    }
                ]
            },
            'fields': {
                'status': {'name': 'Done'}
            }
        }]
        
        result = self.check.evaluate(issues, self.employee)
        self.assertEqual(result, "Yes")
    
    def test_skipped_in_progress(self):
        """Test skipping In Progress fails."""
        issues = [{
            'key': 'TEST-2',
            'changelog': {
                'histories': [
                    {
                        'items': [{
                            'field': 'status',
                            'toString': 'Done'
                        }]
                    }
                ]
            },
            'fields': {
                'status': {'name': 'Done'}
            }
        }]
        
        result = self.check.evaluate(issues, self.employee)
        self.assertTrue(result.startswith("No"))
        self.assertIn("Skipped In Progress", result)


if __name__ == '__main__':
    unittest.main()
