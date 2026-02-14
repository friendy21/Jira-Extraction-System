#!/usr/bin/env python
"""
Run ETL Script
Command-line script for running ETL operations.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import setup_logging, get_logger
from src.etl_pipeline import run_etl


def main():
    """Main entry point for ETL script."""
    parser = argparse.ArgumentParser(description='Run Jira ETL pipeline')
    parser.add_argument(
        '--full',
        action='store_true',
        help='Run full sync instead of incremental'
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
        logger.info(f"Starting ETL: full={args.full}")
        
        result = run_etl(full=args.full)
        
        print(f"\n{'='*50}")
        print("ETL Run Complete")
        print(f"{'='*50}")
        print(f"Run ID: {result.id}")
        print(f"Type: {result.run_type}")
        print(f"Status: {result.status}")
        print(f"Records Processed: {result.records_processed}")
        print(f"Records Inserted: {result.records_inserted}")
        print(f"Records Updated: {result.records_updated}")
        print(f"Duration: {(result.completed_at - result.started_at).total_seconds():.2f}s")
        
        if result.error_message:
            print(f"Error: {result.error_message}")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"ETL failed: {e}")
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
