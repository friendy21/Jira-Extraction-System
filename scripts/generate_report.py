#!/usr/bin/env python
"""
Generate Report Script
Command-line script for generating Excel dashboards.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import setup_logging, get_logger
from src.reports.excel_builder import generate_report


def main():
    """Main entry point for report generation script."""
    parser = argparse.ArgumentParser(description='Generate Jira dashboard report')
    parser.add_argument(
        '--team',
        '-t',
        type=int,
        help='Team ID to filter by (optional)'
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        help='Output file path (optional)'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    try:
        logger.info(f"Generating report: team_id={args.team}")
        
        output_path = generate_report(
            team_id=args.team,
            output_path=args.output
        )
        
        print(f"\n{'='*50}")
        print("Report Generated Successfully")
        print(f"{'='*50}")
        print(f"Output: {output_path}")
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
