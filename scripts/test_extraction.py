#!/usr/bin/env python
"""
Quick JIRA Data Extraction Test
Extracts a small sample of real JIRA data to verify the extraction pipeline works.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.jira_client import JiraClient
from src.utils.logger import setup_logging, get_logger
from datetime import datetime

def main():
    """Extract sample JIRA data."""
    setup_logging()
    logger = get_logger(__name__)
    
    print("=" * 70)
    print("🚀 JIRA Data Extraction Test")
    print("=" * 70)
    
    try:
        client = JiraClient()
        
        # Test 1: Fetch Projects
        print("\n📊 Test 1: Fetching Projects...")
        projects = list(client.fetch_projects())
        print(f"✅ Found {len(projects)} projects:")
        for project in projects[:5]:
            print(f"   - {project.get('key')}: {project.get('name')}")
        if len(projects) > 5:
            print(f"   ... and {len(projects) - 5} more")
        
        # Test 2: Fetch Boards
        print("\n📋 Test 2: Fetching Boards...")
        boards = list(client.fetch_boards())
        print(f"✅ Found {len(boards)} boards:")
        for board in boards[:5]:
            board_type = board.get('type', 'unknown')
            print(f"   - {board.get('name')} (ID: {board.get('id')}, Type: {board_type})")
        if len(boards) > 5:
            print(f"   ... and {len(boards) - 5} more")
        
        # Test 3: Fetch Issues (last 10 updated)
        print("\n🎫 Test 3: Fetching Recent Issues...")
        jql = "ORDER BY updated DESC"
        issues = list(client.fetch_issues(jql, max_results=10))
        print(f"✅ Found {len(issues)} recent issues:")
        for issue in issues:
            key = issue.get('key')
            fields = issue.get('fields', {})
            summary = fields.get('summary', 'No summary')
            status = fields.get('status', {}).get('name', 'Unknown')
            assignee = fields.get('assignee')
            assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
            
            print(f"   - {key}: {summary[:50]}")
            print(f"     Status: {status} | Assignee: {assignee_name}")
        
        # Test 4: Fetch Sprints (if available)
        if boards:
            print("\n🏃 Test 4: Fetching Sprints...")
            # Try to find a scrum board
            scrum_board = next((b for b in boards if b.get('type') == 'scrum'), boards[0])
            board_id = scrum_board.get('id')
            board_name = scrum_board.get('name')
            
            print(f"   Using board: {board_name} (ID: {board_id})")
            
            try:
                sprints = list(client.fetch_sprints(board_id))
                print(f"✅ Found {len(sprints)} sprints:")
                for sprint in sprints[:5]:
                    sprint_name = sprint.get('name', 'Unnamed')
                    sprint_state = sprint.get('state', 'unknown')
                    print(f"   - {sprint_name} (State: {sprint_state})")
                if len(sprints) > 5:
                    print(f"   ... and {len(sprints) - 5} more")
                    
                # Try to get issues from the most recent sprint
                if sprints:
                    recent_sprint = sprints[0]
                    sprint_id = recent_sprint.get('id')
                    sprint_name = recent_sprint.get('name')
                    
                    print(f"\n   📌 Fetching issues from sprint: {sprint_name}")
                    try:
                        sprint_issues = list(client.fetch_sprint_issues(sprint_id))
                        print(f"   ✅ Found {len(sprint_issues)} issues in this sprint")
                        for issue in sprint_issues[:3]:
                            key = issue.get('key')
                            summary = issue.get('fields', {}).get('summary', 'No summary')
                            print(f"      - {key}: {summary[:40]}")
                    except Exception as e:
                        print(f"   ⚠️  Could not fetch sprint issues: {e}")
                        
            except Exception as e:
                print(f"⚠️  Could not fetch sprints: {e}")
        
        # Test 5: Fetch Users (sample)
        print("\n👥 Test 5: Fetching Users...")
        if projects:
            project_key = projects[0].get('key')
            try:
                users = list(client.fetch_users_in_project(project_key))
                print(f"✅ Found {len(users)} users in project {project_key}:")
                for user in users[:5]:
                    display_name = user.get('displayName', 'Unknown')
                    email = user.get('emailAddress', 'No email')
                    print(f"   - {display_name} ({email})")
                if len(users) > 5:
                    print(f"   ... and {len(users) - 5} more")
            except Exception as e:
                print(f"⚠️  Could not fetch users: {e}")
        
        print("\n" + "=" * 70)
        print("✅ JIRA Data Extraction Test: SUCCESSFUL")
        print("=" * 70)
        print("\n✨ The JIRA extraction pipeline is working correctly!")
        print("   You can now run full ETL with: python scripts/run_etl.py --full")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Extraction Test Failed!")
        print(f"   Error: {str(e)}")
        logger.error(f"JIRA extraction test failed: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
