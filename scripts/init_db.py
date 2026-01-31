#!/usr/bin/env python
"""
Initialize Database Script
Creates the database schema and initial data.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import setup_logging, get_logger
from src.database.connection import get_db
from src.database.models import Base
from src.config_manager import ConfigManager


def main():
    """Main entry point for database initialization."""
    parser = argparse.ArgumentParser(description='Initialize database schema')
    parser.add_argument(
        '--drop',
        action='store_true',
        help='Drop existing tables before creating (DANGEROUS)'
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
        logger.info("Initializing database")
        
        db = get_db()
        engine = db.engine
        
        # Check connection
        if not db.check_connection():
            print("Error: Cannot connect to database")
            sys.exit(1)
        
        print("Database connection successful")
        
        if args.drop:
            confirm = input("Are you sure you want to drop all tables? (yes/no): ")
            if confirm.lower() == 'yes':
                logger.warning("Dropping all tables")
                Base.metadata.drop_all(engine)
                print("All tables dropped")
            else:
                print("Cancelled")
                sys.exit(0)
        
        # Create tables
        logger.info("Creating tables")
        Base.metadata.create_all(engine)
        
        print(f"\n{'='*50}")
        print("Database Initialized Successfully")
        print(f"{'='*50}")
        
        # List created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\nTables created: {len(tables)}")
        for table in sorted(tables):
            print(f"  - {table}")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
