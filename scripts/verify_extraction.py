
import sys
import json
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.jira_client import JiraClient
from src.reports.audit_report_builder import AuditReportBuilder
from src.utils.logger import setup_logging

def main():
    log_file = open("debug_verify.log", "w", encoding="utf-8")
    sys.stdout = log_file
    sys.stderr = log_file

    try:
        print("Starting verification...")
        setup_logging()
        client = JiraClient()
        
        print("Fetching 1 issue key...")
        issues = list(client.fetch_issues("order by created DESC", max_results=1))
        
        if not issues:
            print("No issues found.")
            return

        issue_summary = issues[0]
        key = issue_summary['key']
        print(f"Found issue key: {key}")
        
        print("Fetching full issue data...")
        issue = client.fetch_issue(key, expand=['changelog', 'names'])
        print(f"Fetched issue data. ID: {issue.get('id')}")
        
        print("Initializing AuditReportBuilder...")
        builder = AuditReportBuilder(client)
        
        print(f"Running generate_audit_report for {key}...")
        report_path = builder.generate_audit_report([key], output_format="markdown")
        print(f"Report generated at: {report_path}")
        
        print("\nAUDIT REPORT CONTENT:")
        with open(report_path, 'r', encoding='utf-8') as f:
            print(f.read())
            
        print("\nSUCCESS")
        
    except Exception as e:
        print("\nERROR:")
        traceback.print_exc()
    finally:
        log_file.close()

if __name__ == "__main__":
    main()
