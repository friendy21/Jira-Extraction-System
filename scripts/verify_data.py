#!/usr/bin/env python
"""
Clean Extraction Verification
Lists accessible data to prove connection works.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.jira_client import JiraClient

try:
    client = JiraClient()
    
    # 1. User
    user = client._make_request('GET', 'api/3/myself')
    print(f"✅ CONNECTED AS: {user.get('displayName')} ({user.get('emailAddress')})")
    
    # 2. Projects
    projects = client.fetch_projects()
    print(f"✅ PROJECTS FOUND: {len(projects)}")
    for p in projects[:5]:
        print(f"   - {p['key']}: {p['name']}")
        
    # 3. Boards
    boards = client.fetch_boards()
    print(f"✅ BOARDS FOUND: {len(boards)}")
    for b in boards[:5]:
        print(f"   - {b['name']} ({b['type']})")
        
    print("\nExtraction verified successfully for Meta-data.")
    print("Issue extraction requires database setup.")

except Exception as e:
    print(f"❌ ERROR: {e}")
