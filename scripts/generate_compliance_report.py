#!/usr/bin/env python
"""
Generate JIRA Compliance Report
Creates compliance audit reports tracking employee weekly JIRA process adherence.

Usage:
    # Generate for all teams, last 4 weeks
    python scripts/generate_compliance_report.py
    
    # Generate for specific team and date range
    python scripts/generate_compliance_report.py --team 1 --start 2026-01-01 --end 2026-01-31
    
    # Generate with custom output path
    python scripts/generate_compliance_report.py --output ./reports/compliance_2026_Q1.xlsx
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_manager import ConfigManager
from src.jira_client import JiraClient
from src.reports.compliance_builder import ComplianceReportBuilder
from src.utils.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate JIRA Compliance Audit Report',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Generate for last 4 weeks (all teams)
  python scripts/generate_compliance_report.py
  
  # Generate for specific date range
  python scripts/generate_compliance_report.py --start 2026-01-01 --end 2026-01-31
  
  # Generate for specific team
  python scripts/generate_compliance_report.py --team 1
  
  # Custom output directory
  python scripts/generate_compliance_report.py --output ./custom_reports/
        '''
    )
    
    parser.add_argument(
        '--start',
        type=str,
        help='Start date (YYYY-MM-DD). Default: 4 weeks ago'
    )
    
    parser.add_argument(
        '--end',
        type=str,
        help='End date (YYYY-MM-DD). Default: today'
    )
    
    parser.add_argument(
        '--team',
        type=int,
        help='Team ID to filter by (optional)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='./outputs',
        help='Output directory for report. Default: ./outputs'
    )
    
    return parser.parse_args()


def parse_date(date_str: str) -> datetime:
    """Parse date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


def main():
    """Main entry point."""
    args = parse_args()
    
    try:
        # Parse dates
        if args.end:
            end_date = parse_date(args.end)
        else:
            end_date = datetime.now()
        
        if args.start:
            start_date = parse_date(args.start)
        else:
            # Default: 4 weeks ago
            start_date = end_date - timedelta(weeks=4)
        
        # Validate date range
        if start_date > end_date:
            logger.error("Start date must be before end date")
            print("❌ Error: Start date must be before end date")
            sys.exit(1)
        
        # Initialize JIRA client
        logger.info("Initializing JIRA client...")
        print("🔧 Initializing JIRA client...")
        
        config = ConfigManager()
        jira_client = JiraClient()
        
        # Test connection
        try:
            server_info = jira_client.get_server_info()
            logger.info(f"Connected to JIRA: {server_info.get('baseUrl')}")
            print(f"✅ Connected to JIRA: {server_info.get('baseUrl')}")
        except Exception as e:
            logger.error(f"Failed to connect to JIRA: {e}")
            print(f"❌ Failed to connect to JIRA: {e}")
            sys.exit(1)
        
        # Create report builder
        builder = ComplianceReportBuilder(
            jira_client,
            output_dir=args.output
        )
        
        # Generate report
        print(f"\n📊 Generating compliance report...")
        print(f"   Date range: {start_date.date()} to {end_date.date()}")
        if args.team:
            print(f"   Team ID: {args.team}")
        else:
            print(f"   Team ID: All teams")
        print()
        
        report_path = builder.generate_report(
            start_date=start_date,
            end_date=end_date,
            team_id=args.team
        )
        
        # Print success message
        print(f"\n{'='*70}")
        print("✅ Compliance Report Generated Successfully!")
        print(f"{'='*70}")
        print(f"📁 Output: {report_path}")
        print(f"\n📊 Report Details:")
        print(f"   • Format: Single-sheet Excel with 11 compliance columns")
        print(f"   • Date Range: {start_date.date()} to {end_date.date()}")
        print(f"   • Compliance Checks: 7 (Status, Cancellation, Updates, Roles, Docs, Lifecycle, Zero-Tolerance)")
        print(f"   • Output Format: Pass/Fail with color coding")
        print(f"\n💡 Open the file to review employee compliance!")
        print(f"{'='*70}\n")
        
        logger.info(f"Compliance report generated successfully: {report_path}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Report generation cancelled by user")
        logger.warning("Report generation cancelled by user")
        sys.exit(130)
    
    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        print("\nCheck logs for detailed error information.")
        sys.exit(1)


if __name__ == '__main__':
    main()
