"""
Database Connection Module
Handles PostgreSQL connection pooling and session management using SQLAlchemy.
"""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool

from src.config_manager import ConfigManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseConnection:
    """Manages database connections with connection pooling."""
    
    _instance = None
    _engine: Engine = None
    _session_factory = None
    
    def __new__(cls):
        """Singleton pattern to ensure single connection pool."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize database connection if not already done."""
        if self._engine is None:
            self._initialize_engine()
    
    def _initialize_engine(self) -> None:
        """Create SQLAlchemy engine with connection pooling."""
        config = ConfigManager()
        db_config = config.get_database_config()
        
        # Build connection URL
        db_url = self._build_connection_url(db_config)
        
        # Engine configuration
        pool_size = db_config.get('pool_size', 5)
        max_overflow = db_config.get('max_overflow', 10)
        pool_timeout = db_config.get('pool_timeout', 30)
        
        logger.info(f"Initializing database connection to {db_config.get('host')}:{db_config.get('port')}/{db_config.get('name')}")
        
        self._engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_pre_ping=True,  # Enable connection health checks
            echo=os.getenv('SQL_ECHO', 'false').lower() == 'true'
        )
        
        # Create session factory
        self._session_factory = sessionmaker(bind=self._engine)
        
        logger.info("Database engine initialized successfully")
    
    def _build_connection_url(self, db_config: dict) -> str:
        """Build PostgreSQL connection URL from config."""
        host = db_config.get('host', 'localhost')
        port = db_config.get('port', 5432)
        name = db_config.get('name', 'jira_dashboard')
        user = db_config.get('user', 'jira_etl')
        password = db_config.get('password', '')
        
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
    
    @property
    def engine(self) -> Engine:
        """Get the SQLAlchemy engine."""
        return self._engine
    
    def get_session(self) -> Session:
        """Create a new database session."""
        return self._session_factory()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.
        
        Usage:
            with db.session_scope() as session:
                session.query(...)
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def check_connection(self) -> bool:
        """
        Check if database connection is healthy.
        
        Returns:
            bool: True if connection is healthy, False otherwise.
        """
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.debug("Database connection health check passed")
            return True
        except Exception as e:
            logger.error(f"Database connection health check failed: {e}")
            return False
    
    def execute_raw_sql(self, sql: str, params: dict = None) -> list:
        """
        Execute raw SQL query and return results.
        
        Args:
            sql: SQL query string
            params: Optional query parameters
            
        Returns:
            List of result rows
        """
        with self._engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            return result.fetchall()
    
    def dispose(self) -> None:
        """Dispose of the connection pool."""
        if self._engine:
            self._engine.dispose()
            logger.info("Database connection pool disposed")


# Convenience function for getting database connection
def get_db() -> DatabaseConnection:
    """Get the singleton database connection instance."""
    return DatabaseConnection()


# Convenience context manager
@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Convenience function to get a database session.
    
    Usage:
        with get_session() as session:
            session.query(...)
    """
    db = get_db()
    with db.session_scope() as session:
        yield session
