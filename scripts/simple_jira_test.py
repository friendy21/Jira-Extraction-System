#!/usr/bin/env python
"""
Simple JIRA Test - Direct API Call
Test JIRA credentials with minimal dependencies.
"""

import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

JIRA_URL = os.getenv('JIRA_URL')
JIRA_USERNAME = os.getenv('JIRA_USERNAME')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')

print("=" * 60)
print("🔌 Simple JIRA Connection Test")
print("=" * 60)

print(f"\n📍 JIRA URL: {JIRA_URL}")
print(f"👤 Username: {JIRA_USERNAME}")
print(f"🔑 API Token: {'*' * 20} (configured)")

# Test 1: Server Info
print("\n\n🔄 Test 1: Getting Server Info...")
try:
    url = f"{JIRA_URL.rstrip('/')}/rest/api/3/serverInfo"
    response = requests.get(
        url,
        auth=HTTPBasicAuth(JIRA_USERNAME, JIRA_API_TOKEN),
        headers={'Accept': 'application/json'},
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ SUCCESS!")
        print(f"   Server Version: {data.get('version', 'Unknown')}")
        print(f"   Build Number: {data.get('buildNumber', 'Unknown')}")
        print(f"   Server Title: {data.get('serverTitle', 'Unknown')}")
    else:
        print(f"❌ FAILED: HTTP {response.status_code}")
        print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"❌ ERROR: {str(e)}")

# Test 2: Get Projects
print("\n\n🔄 Test 2: Fetching Projects...")
try:
    url = f"{JIRA_URL.rstrip('/')}/rest/api/3/project"
    response = requests.get(
        url,
        auth=HTTPBasicAuth(JIRA_USERNAME, JIRA_API_TOKEN),
        headers={'Accept': 'application/json'},
        timeout=10
    )
    
    if response.status_code == 200:
        projects = response.json()
        print(f"✅ SUCCESS! Found {len(projects)} projects:")
        for project in projects[:10]:
            print(f"   - {project.get('key')}: {project.get('name')}")
        if len(projects) > 10:
            print(f"   ... and {len(projects) - 10} more")
    else:
        print(f"❌ FAILED: HTTP {response.status_code}")
        print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"❌ ERROR: {str(e)}")

# Test 3: Search Issues (JQL)
print("\n\n🔄 Test 3: Searching Issues (5 most recent)...")
try:
    url = f"{JIRA_URL.rstrip('/')}/rest/api/3/search"
    params = {
        'jql': 'ORDER BY updated DESC',
        'maxResults': 5,
        'fields': 'summary,status,assignee,created,updated'
    }
    response = requests.get(
        url,
        auth=HTTPBasicAuth(JIRA_USERNAME, JIRA_API_TOKEN),
        headers={'Accept': 'application/json'},
        params=params,
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        issues = data.get('issues', [])
        total = data.get('total', 0)
        print(f"✅ SUCCESS! Found {total} total issues (showing {len(issues)}):")
        for issue in issues:
            key = issue.get('key')
            summary = issue.get('fields', {}).get('summary', 'No summary')
            status = issue.get('fields', {}).get('status', {}).get('name', 'Unknown')
            print(f"   - {key}: {summary[:50]} [{status}]")
    else:
        print(f"❌ FAILED: HTTP {response.status_code}")
        print(f"   Response: {response.text[:500]}")
except Exception as e:
    print(f"❌ ERROR: {str(e)}")

print("\n" + "=" * 60)
print("✅ JIRA Connection Tests Complete!")
print("=" * 60)
