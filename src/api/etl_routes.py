"""
ETL API Blueprint
Provides REST endpoints for triggering and monitoring ETL operations.
"""

from datetime import datetime
from flask import Blueprint, jsonify, request

from src.etl_pipeline import ETLPipeline, run_etl
from src.database.connection import get_session
from src.database.models import EtlRun
from src.utils.logger import get_logger

logger = get_logger(__name__)

etl_bp = Blueprint('etl', __name__, url_prefix='/api/etl')


@etl_bp.route('/run', methods=['POST'])
def trigger_etl():
    """
    Trigger an ETL run.
    
    Query params:
        full: If 'true', run full sync. Otherwise incremental.
    
    Returns:
        JSON with run ID and status
    """
    try:
        full_sync = request.args.get('full', 'false').lower() == 'true'
        
        logger.info(f"ETL triggered via API: full={full_sync}")
        
        etl_run = run_etl(full=full_sync)
        
        return jsonify({
            'success': True,
            'run_id': etl_run.id,
            'run_type': etl_run.run_type,
            'status': etl_run.status,
            'records_processed': etl_run.records_processed,
            'started_at': etl_run.started_at.isoformat() if etl_run.started_at else None,
            'completed_at': etl_run.completed_at.isoformat() if etl_run.completed_at else None
        })
        
    except Exception as e:
        logger.error(f"ETL run failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@etl_bp.route('/status', methods=['GET'])
def get_etl_status():
    """
    Get status of recent ETL runs.
    
    Query params:
        limit: Number of runs to return (default 10)
    
    Returns:
        JSON with list of recent ETL runs
    """
    try:
        limit = int(request.args.get('limit', 10))
        
        with get_session() as session:
            runs = session.query(EtlRun).order_by(
                EtlRun.started_at.desc()
            ).limit(limit).all()
            
            result = []
            for run in runs:
                result.append({
                    'id': run.id,
                    'run_type': run.run_type,
                    'status': run.status,
                    'started_at': run.started_at.isoformat() if run.started_at else None,
                    'completed_at': run.completed_at.isoformat() if run.completed_at else None,
                    'records_processed': run.records_processed,
                    'records_inserted': run.records_inserted,
                    'records_updated': run.records_updated,
                    'error_message': run.error_message
                })
        
        return jsonify({
            'success': True,
            'runs': result
        })
        
    except Exception as e:
        logger.error(f"Failed to get ETL status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@etl_bp.route('/status/<int:run_id>', methods=['GET'])
def get_etl_run(run_id: int):
    """
    Get details of a specific ETL run.
    
    Args:
        run_id: ETL run ID
    
    Returns:
        JSON with run details
    """
    try:
        with get_session() as session:
            run = session.query(EtlRun).get(run_id)
            
            if not run:
                return jsonify({
                    'success': False,
                    'error': 'Run not found'
                }), 404
            
            return jsonify({
                'success': True,
                'run': {
                    'id': run.id,
                    'run_type': run.run_type,
                    'status': run.status,
                    'started_at': run.started_at.isoformat() if run.started_at else None,
                    'completed_at': run.completed_at.isoformat() if run.completed_at else None,
                    'records_processed': run.records_processed,
                    'records_inserted': run.records_inserted,
                    'records_updated': run.records_updated,
                    'error_message': run.error_message,
                    'last_sync_timestamp': run.last_sync_timestamp.isoformat() if run.last_sync_timestamp else None
                }
            })
        
    except Exception as e:
        logger.error(f"Failed to get ETL run {run_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@etl_bp.route('/last-sync', methods=['GET'])
def get_last_sync():
    """
    Get timestamp of last successful sync.
    
    Returns:
        JSON with last sync timestamp
    """
    try:
        with get_session() as session:
            from src.database.queries import QueryHelpers
            queries = QueryHelpers(session)
            
            timestamp = queries.get_last_sync_timestamp()
            
            return jsonify({
                'success': True,
                'last_sync': timestamp.isoformat() if timestamp else None
            })
        
    except Exception as e:
        logger.error(f"Failed to get last sync timestamp: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
