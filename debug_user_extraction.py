from src.jira_client import JiraClient
import json

def debug_issue_fields():
    client = JiraClient()
    # OH project had issues in previous runs
    jql = "project = SP ORDER BY created DESC"
    print("Fetching 1 issue from SP...")
    
    issues_gen = client.fetch_issues(
        jql, 
        max_results=1,
        fields=['summary', 'status', 'assignee', 'reporter', 'creator']
    )
    
    try:
        issue = next(issues_gen)
    except StopIteration:
        print("No issues found in OH")
        return
        
    print(f"Raw Issue Object: {issue}")
    print(f"Issue Key: {issue.get('key')}")
    fields = issue.get('fields', {})
    
    print("\n--- Assignee ---")
    assignee = fields.get('assignee')
    print(json.dumps(assignee, indent=2) if assignee else "None")
    
    print("\n--- Reporter ---")
    reporter = fields.get('reporter')
    print(json.dumps(reporter, indent=2) if reporter else "None")
    
    print("\n--- Creator ---")
    creator = fields.get('creator')
    print(json.dumps(creator, indent=2) if creator else "None")

if __name__ == "__main__":
    debug_issue_fields()
