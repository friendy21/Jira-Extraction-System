from src.jira_client import JiraClient
from scripts.batch_extract_employees import generate_report
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_pagination():
    print("Testing pagination for SP 2026...")
    client = JiraClient()
    jql = "project = SP AND created >= '2026-01-01' AND created <= '2026-12-31' ORDER BY created ASC"
    
    try:
        issues = list(client.fetch_issues(jql, max_results=5))
        print(f"Successfully fetched {len(issues)} issues.")
        for i, issue in enumerate(issues):
            print(f"Issue {i+1}: {issue.get('key')}")
    except Exception as e:
        print(f"Pagination failed: {e}")
        import traceback
        traceback.print_exc()

def test_report_gen():
    print("\nTesting report generation...")
    dummy_users = [
        {'name': 'Test User 1', 'email': 'test1@example.com', 'active': True},
        {'name': 'Test User 2', 'email': 'test2@example.com', 'active': True}
    ]
    try:
        file_path, num, total, pass_c, fail_c, rate = generate_report(dummy_users, weeks=4)
        print(f"Report generated at: {file_path}")
    except Exception as e:
        print(f"Report generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pagination()
    test_report_gen()
