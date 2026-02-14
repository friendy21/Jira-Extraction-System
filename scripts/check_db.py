import sys
from pathlib import Path
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import get_db, DatabaseConnection

def main():
    print("Checking database connection...")
    try:
        db = get_db()
        # Print connection details (careful with password)
        config = db._build_connection_url(db._config if hasattr(db, '_config') else {})
        # Manually reconstruct to show what it thinks it's using
        from src.config_manager import ConfigManager
        cm = ConfigManager()
        db_config = cm.get_database_config()
        print(f"Host: {db_config.get('host')}")
        print(f"Port: {db_config.get('port')}")
        print(f"User: {db_config.get('user')}")
        print(f"DB Name: {db_config.get('name')}")
        
        if db.check_connection():
            print("✅ Database connection successful!")
            sys.exit(0)
        else:
            print("❌ Database connection failed!")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error checking connection: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
