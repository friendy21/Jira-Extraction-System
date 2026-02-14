"""
Flask Application Factory
Main entry point for the Jira MCP web application.
"""

import os
from datetime import datetime

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config_manager import ConfigManager
from src.database.connection import get_db
from src.utils.logger import setup_logging, get_logger


def create_app(config_name: str = None) -> Flask:
    """
    Application factory for Flask app.
    
    Args:
        config_name: Optional configuration name
        
    Returns:
        Configured Flask application
    """
    # Setup logging first
    setup_logging()
    logger = get_logger(__name__)
    
    # Get absolute path to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Create Flask app with static folder
    app = Flask(
        __name__,
        static_folder=os.path.join(project_root, 'static'),
        static_url_path='/static'
    )
    
    # Load configuration
    config = ConfigManager()
    
    # Flask configuration
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['JSON_SORT_KEYS'] = False
    
    # Enable CORS
    CORS(app)
    
    # Register blueprints
    from src.api.etl_routes import etl_bp
    from src.api.report_routes import reports_bp
    from src.api.metrics_routes import metrics_bp
    
    app.register_blueprint(etl_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(metrics_bp)
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        db = get_db()
        db_healthy = db.check_connection()
        
        return jsonify({
            'status': 'healthy' if db_healthy else 'degraded',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected' if db_healthy else 'disconnected'
        })
    
    # Root endpoint
    @app.route('/', methods=['GET'])
    def root():
        """Root endpoint with API info."""
        return jsonify({
            'name': 'Jira MCP Dashboard API',
            'version': '1.0.0',
            'endpoints': {
                '/health': 'Health check',
                '/compliance': 'Compliance Report UI (Web Interface)',
                '/api/etl/run': 'Trigger ETL (POST)',
                '/api/etl/status': 'ETL status (GET)',
                '/api/reports/generate': 'Generate report (POST)',
                '/api/reports/list': 'List reports (GET)',
                '/api/reports/teams': 'List teams (GET)',
                '/api/reports/compliance/generate': 'Generate compliance report (POST)',
                '/api/reports/compliance/list': 'List compliance reports (GET)',
                '/api/reports/compliance/demo': 'Generate demo compliance report (POST)',
                '/api/metrics/velocity/<team_id>': 'Team velocity (GET)',
                '/api/metrics/sprint/<sprint_id>': 'Sprint metrics (GET)',
                '/api/metrics/daily/<team_id>': 'Daily metrics (GET)',
                '/api/metrics/priority/<team_id>': 'Priority distribution (GET)',
                '/api/metrics/aging/<team_id>': 'Ticket aging (GET)',
                '/api/metrics/time-tracking/<team_id>': 'Time tracking (GET)',
                '/api/metrics/kanban/<board_id>': 'Kanban metrics (GET)'
            }
        })
    
    # Compliance Report UI
    @app.route('/compliance', methods=['GET'])
    def compliance_ui():
        """Serve the compliance report UI."""
        try:
            return send_from_directory(app.static_folder, 'compliance-ui.html')
        except Exception as e:
            logger.error(f"Failed to serve UI: {e}")
            return jsonify({
                'success': False,
                'error': 'UI file not found'
            }), 404

    # Audit Report UI
    @app.route('/audit', methods=['GET'])
    def audit_ui():
        """Serve the detailed audit report UI."""
        try:
            return send_from_directory(app.static_folder, 'audit-report-ui.html')
        except Exception as e:
            logger.error(f"Failed to serve Audit UI: {e}")
            return jsonify({
                'success': False,
                'error': 'Audit UI file not found'
            }), 404
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Not found'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
    
    logger.info("Flask application created")
    
    return app


def create_scheduler(app: Flask = None) -> BackgroundScheduler:
    """
    Create and configure the background scheduler.
    
    Args:
        app: Optional Flask app for context
        
    Returns:
        Configured scheduler
    """
    logger = get_logger(__name__)
    config = ConfigManager()
    scheduler_config = config.get_scheduler_config()
    
    scheduler = BackgroundScheduler()
    
    if not scheduler_config.get('enabled', True):
        logger.info("Scheduler is disabled")
        return scheduler
    
    # ETL job
    etl_schedule = scheduler_config.get('etl_schedule', '0 2 * * *')  # Default: 2 AM daily
    
    @scheduler.scheduled_job(CronTrigger.from_crontab(etl_schedule))
    def scheduled_etl():
        """Scheduled ETL job."""
        logger.info("Running scheduled ETL")
        try:
            from src.etl_pipeline import run_etl
            run_etl(full=False)  # Incremental by default
            logger.info("Scheduled ETL completed")
        except Exception as e:
            logger.error(f"Scheduled ETL failed: {e}")
    
    # Report generation job
    report_schedule = scheduler_config.get('report_schedule', '0 6 * * 1')  # Default: 6 AM Monday
    
    @scheduler.scheduled_job(CronTrigger.from_crontab(report_schedule))
    def scheduled_report():
        """Scheduled report generation job."""
        logger.info("Running scheduled report generation")
        try:
            from src.reports.excel_builder import generate_report
            generate_report()
            logger.info("Scheduled report generated")
        except Exception as e:
            logger.error(f"Scheduled report generation failed: {e}")
    
    return scheduler


# Application entry point
app = create_app()


if __name__ == '__main__':
    # Development server
    scheduler = create_scheduler(app)
    scheduler.start()
    
    try:
        app.run(
            host='0.0.0.0',
            port=int(os.getenv('FLASK_PORT', 6922)),
            debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
        )
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
