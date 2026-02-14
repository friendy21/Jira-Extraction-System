import unittest
from datetime import datetime, timedelta
import pytz
from scripts.batch_extract_employees import (
    check_mit_compliance,
    check_updates_compliance,
    check_roles_compliance,
    check_documentation_compliance,
    check_status_hygiene,
    check_zero_tolerance
)

class TestComplianceLogic(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(pytz.UTC)
        self.start_date = self.now - timedelta(days=28)
        self.user_email = "test@example.com"
        self.user_account_id = "12345"

    def test_mit_compliance(self):
        # Case 1: No MITs
        self.assertEqual(check_mit_compliance([], self.start_date, self.now)[0], 'No')
        
        # Case 2: Open MIT
        issues = [{
            'fields': {
                'labels': ['MIT'],
                'priority': {'name': 'High'},
                'status': {'name': 'In Progress'}
            }
        }]
        self.assertEqual(check_mit_compliance(issues, self.start_date, self.now)[0], 'No')
        
        # Case 3: Closed MIT
        issues[0]['fields']['status']['name'] = 'Done'
        issues[0]['fields']['resolutiondate'] = self.now.strftime('%Y-%m-%dT%H:%M:%S.%f%z')
        self.assertEqual(check_mit_compliance(issues, self.start_date, self.now)[0], 'Yes')

    def test_updates_compliance(self):
        # Case 1: No comments
        self.assertEqual(check_updates_compliance([], self.user_email, self.start_date, self.now)[0], 'No')
        
        # Case 2: Wed and Fri comments
        # Find next Wed and Fri from start_date
        wed = self.start_date + timedelta(days=(2 - self.start_date.weekday() + 7) % 7)
        fri = self.start_date + timedelta(days=(4 - self.start_date.weekday() + 7) % 7)
        
        issues = [{
            'fields': {
                'comment': {
                    'comments': [
                        {'author': {'emailAddress': self.user_email}, 'created': wed.strftime('%Y-%m-%dT%H:%M:%S.%f%z')},
                        {'author': {'emailAddress': self.user_email}, 'created': fri.strftime('%Y-%m-%dT%H:%M:%S.%f%z')}
                    ]
                }
            }
        }]
        self.assertEqual(check_updates_compliance(issues, self.user_email, self.start_date, self.now)[0], 'Yes')

    def test_roles_compliance(self):
        # Case 1: Self-assigned
        issues = [{
            'fields': {
                'reporter': {'accountId': self.user_account_id},
                'assignee': {'accountId': self.user_account_id}
            }
        }]
        self.assertEqual(check_roles_compliance(issues, self.user_account_id)[0], 'No')
        
        # Case 2: Different user
        issues[0]['fields']['reporter']['accountId'] = '67890'
        self.assertEqual(check_roles_compliance(issues, self.user_account_id)[0], 'Yes')

    def test_documentation_compliance(self):
        # Case 1: Empty description
        issues = [{'fields': {'description': ''}}]
        self.assertEqual(check_documentation_compliance(issues)[0], 'No')
        
        # Case 2: Good description
        issues = [{'fields': {'description': 'A reasonable description of the task.'}}]
        self.assertEqual(check_documentation_compliance(issues)[0], 'Yes')

    def test_status_hygiene(self):
        # Case 1: Stale issue
        stale_date = self.now - timedelta(days=10)
        issues = [{
            'fields': {
                'updated': stale_date.strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
                'status': {'name': 'In Progress'}
            }
        }]
        self.assertEqual(check_status_hygiene(issues)[0], 'No')
        
        # Case 2: Fresh issue
        fresh_date = self.now - timedelta(days=2)
        issues[0]['fields']['updated'] = fresh_date.strftime('%Y-%m-%dT%H:%M:%S.%f%z')
        self.assertEqual(check_status_hygiene(issues)[0], 'Yes')

if __name__ == '__main__':
    unittest.main()
