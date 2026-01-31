#!/usr/bin/env python
"""
Test JIRA Connection
Quick script to verify JIRA credentials and connection.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.jira_client import JiraClient
from src.config_manager import ConfigManager
from src.utils.logger import setup_logging, get_logger

def main():
    """Test JIRA connection."""
    setup_logging()
    logger = get_logger(__name__)
    
    print("=" * 60)
    print("🔌 Testing JIRA Connection")
    print("=" * 60)
    
    try:
        # Initialize config and client
        config = ConfigManager()
        jira_config = config.get_jira_config()
        
        print(f"\n📍 JIRA URL: {jira_config.get('url')}")
        print(f"👤 Username: {jira_config.get('username')}")
        print(f"🔑 API Token: {'*' * 20} (configured)")
        
        print("\n🔄 Connecting to JIRA...")
        client = JiraClient()
        
        # Test connection
        print("\n✅ Testing connection...")
        is_connected = client.test_connection()
        
        if not is_connected:
            raise Exception("Failed to connect to JIRA")
        
        # Get server info
        print("\n✅ Getting server info...")
        server_info = client.get_server_info()
        
        print(f"\n✅ Connection Successful!")
        print(f"   Server Version: {server_info.get('version', 'Unknown')}")
        print(f"   Build Number: {server_info.get('buildNumber', 'Unknown')}")
        print(f"   Server Title: {server_info.get('serverTitle', 'Unknown')}")
        
        # Get projects
        print("\n📊 Fetching projects...")
        projects = list(client.fetch_projects())
        
        print(f"\n✅ Found {len(projects)} projects:")
        for project in projects[:10]:  # Show first 10
            print(f"   - {project.get('key')}: {project.get('name')}")
        
        if len(projects) > 10:
            print(f"   ... and {len(projects) - 10} more")
        
        # Get a sample of issues
        print("\n📋 Fetching sample issues...")
        jql = "ORDER BY updated DESC"
        issues = list(client.fetch_issues(jql, max_results=5))
        
        print(f"\n✅ Found {len(issues)} issues (showing most recent):")
        for issue in issues:
            summary = issue.get('fields', {}).get('summary', 'No summary')
            print(f"   - {issue.get('key')}: {summary[:60]}")
        
        print("\n" + "=" * 60)
        print("✅ JIRA Connection Test: PASSED")
        print("=" * 60)
        print("\n✨ Ready for real data extraction!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Connection Test Failed!")
        print(f"   Error: {str(e)}")
        logger.error(f"JIRA connection test failed: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
