
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.jira_client import JiraClient, JiraAPIError

print("Starting debugger...")
try:
    c = JiraClient()
    
    boards = c.fetch_boards()
    if not boards:
        print("No boards")
        sys.exit()
        
    # Find a Scrum board
    scrum_board = next((b for b in boards if b['type'] == 'scrum'), None)
    if not scrum_board:
        print("No Scrum boards found, trying first board")
        scrum_board = boards[0]
            
    print(f"Using Board: {scrum_board['name']} (ID: {scrum_board['id']})")
    
    # Fetch Sprints
    try:
        sprints = c.fetch_sprints(scrum_board['id'])
        print(f"Found {len(sprints)} sprints")
        
        if sprints:
            sprint = sprints[-1] # Valid/latest sprint
            print(f"Checking Sprint: {sprint['name']} (ID: {sprint['id']})")
            
            # Fetch Issues (Agile API)
            issues = c.fetch_sprint_issues(sprint['id'])
            print(f"Found {len(issues)} issues in sprint")
            if issues:
                print(f"Sample Issue: {issues[0]['key']} - {issues[0]['fields']['summary'][:30]}...")
            else:
                print("No issues in this sprint")
                
    except JiraAPIError as e:
        print(f"Sprint fetch failed: {e.status_code}")
        
except Exception as e:
    print(f"Exception: {e}")
print("Debugger finished.")
