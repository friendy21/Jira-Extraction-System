"""
Reports API Blueprint
Provides REST endpoints for generating and downloading reports.
"""

import os
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, send_file

from src.reports.excel_builder import ExcelBuilder, generate_report
from src.reports.compliance_builder import ComplianceReportBuilder
from src.jira_client import JiraClient
from src.database.connection import get_session
from src.database.models import Team
from src.config_manager import ConfigManager
from src.utils.logger import get_logger

logger = get_logger(__name__)

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')


@reports_bp.route('/generate', methods=['POST'])
def generate_dashboard():
    """
    Generate a new dashboard report.
    
    Query params:
        team_id: Optional team filter
    
    Returns:
        JSON with report details and download link
    """
    try:
        team_id = request.args.get('team_id', type=int)
        
        logger.info(f"Report generation triggered: team_id={team_id}")
        
        output_path = generate_report(team_id=team_id)
        
        return jsonify({
            'success': True,
            'message': 'Report generated successfully',
            'file_path': output_path,
            'file_name': os.path.basename(output_path),
            'download_url': f'/api/reports/download/{os.path.basename(output_path)}'
        })
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@reports_bp.route('/download/<filename>', methods=['GET'])
def download_report(filename: str):
    """
    Download a generated report file.
    
    Args:
        filename: Report filename
    
    Returns:
        Excel file download
    """
    try:
        config = ConfigManager()
        reports_config = config.get_reports_config()
        output_dir = reports_config.get('output_dir', './outputs')
        
        file_path = os.path.join(output_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
        
        # Security check - ensure file is in output directory
        abs_output_dir = os.path.abspath(output_dir)
        abs_file_path = os.path.abspath(file_path)
        
        if not abs_file_path.startswith(abs_output_dir):
            return jsonify({
                'success': False,
                'error': 'Invalid file path'
            }), 403
        
        return send_file(
            abs_file_path,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Report download failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@reports_bp.route('/list', methods=['GET'])
def list_reports():
    """
    List available report files.
    
    Returns:
        JSON with list of report files
    """
    try:
        config = ConfigManager()
        reports_config = config.get_reports_config()
        output_dir = reports_config.get('output_dir', './outputs')
        
        if not os.path.exists(output_dir):
            return jsonify({
                'success': True,
                'reports': []
            })
        
        reports = []
        for filename in os.listdir(output_dir):
            if filename.endswith('.xlsx'):
                file_path = os.path.join(output_dir, filename)
                stat = os.stat(file_path)
                reports.append({
                    'filename': filename,
                    'size_bytes': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'download_url': f'/api/reports/download/{filename}'
                })
        
        # Sort by creation time, newest first
        reports.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'reports': reports
        })
        
    except Exception as e:
        logger.error(f"Failed to list reports: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@reports_bp.route('/teams', methods=['GET'])
def list_teams():
    """
    List available teams for report filtering.
    
    Returns:
        JSON with list of teams
    """
    try:
        with get_session() as session:
            teams = session.query(Team).all()
            
            result = []
            for team in teams:
                result.append({
                    'id': team.id,
                    'code': team.team_code,
                    'name': team.team_name,
                    'organization': team.organization.name if team.organization else None
                })
        
        return jsonify({
            'success': True,
            'teams': result
        })
        
    except Exception as e:
        logger.error(f"Failed to list teams: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# COMPLIANCE REPORT ENDPOINTS
# ============================================

@reports_bp.route('/compliance/generate', methods=['POST'])
def generate_compliance_report():
    """
    Generate a new compliance audit report.
    
    Query params:
        start_date: Start date (YYYY-MM-DD), default: 4 weeks ago
        end_date: End date (YYYY-MM-DD), default: today
        team_id: Optional team filter
    
    Returns:
        JSON with report details and download link
    """
    try:
        # Parse query parameters
        team_id = request.args.get('team_id', type=int)
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # Parse dates
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        else:
            end_date = datetime.now()
        
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        else:
            start_date = end_date - timedelta(weeks=4)
        
        # Validate date range
        if start_date > end_date:
            return jsonify({
                'success': False,
                'error': 'start_date must be before end_date'
            }), 400
        
        logger.info(f"Compliance report generation triggered: {start_date.date()} to {end_date.date()}, team_id={team_id}")
        
        # Initialize builder
        jira_client = JiraClient()
        builder = ComplianceReportBuilder(jira_client)
        
        # Generate report
        output_path = builder.generate_report(
            start_date=start_date,
            end_date=end_date,
            team_id=team_id
        )
        
        return jsonify({
            'success': True,
            'message': 'Compliance report generated successfully',
            'file_path': output_path,
            'file_name': os.path.basename(output_path),
            'download_url': f'/api/reports/download/{os.path.basename(output_path)}',
            'report_type': 'compliance',
            'date_range': {
                'start': start_date.date().isoformat(),
                'end': end_date.date().isoformat()
            }
        })
        
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        return jsonify({
            'success': False,
            'error': f'Invalid date format. Use YYYY-MM-DD: {str(e)}'
        }), 400
    
    except Exception as e:
        logger.error(f"Compliance report generation failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@reports_bp.route('/compliance/list', methods=['GET'])
def list_compliance_reports():
    """
    List available compliance report files.
    
    Returns:
        JSON with list of compliance report files
    """
    try:
        config = ConfigManager()
        reports_config = config.get_reports_config()
        output_dir = reports_config.get('output_dir', './outputs')
        
        if not os.path.exists(output_dir):
            return jsonify({
                'success': True,
                'reports': []
            })
        
        reports = []
        for filename in os.listdir(output_dir):
            # Filter for compliance reports only
            if filename.startswith('JIRA_Compliance_Report_') and filename.endswith('.xlsx'):
                file_path = os.path.join(output_dir, filename)
                stat = os.stat(file_path)
                reports.append({
                    'filename': filename,
                    'size_bytes': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'download_url': f'/api/reports/download/{filename}',
                    'report_type': 'compliance'
                })
        
        # Sort by creation time, newest first
        reports.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'count': len(reports),
            'reports': reports
        })
        
    except Exception as e:
        logger.error(f"Failed to list compliance reports: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@reports_bp.route('/compliance/demo', methods=['POST'])
def generate_compliance_demo():
    """
    Generate a demo compliance report with mock data.
    
    Returns:
        JSON with demo report details and download link
    """
    try:
        logger.info("Demo compliance report generation triggered")
        
        # Import and run demo generation
        import sys
        from pathlib import Path
        from scripts.demo_compliance_report import create_demo_compliance_report
        
        output_path = create_demo_compliance_report()
        
        return jsonify({
            'success': True,
            'message': 'Demo compliance report generated successfully',
            'file_path': output_path,
            'file_name': os.path.basename(output_path),
            'download_url': f'/api/reports/download/{os.path.basename(output_path)}',
            'report_type': 'compliance_demo'
        })
        
    except Exception as e:
        logger.error(f"Demo compliance report generation failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# AUDIT REPORT ENDPOINTS (NEW)
# ============================================

@reports_bp.route('/audit/generate', methods=['POST'])
def generate_audit_report():
    """
    Generate detailed ticket-by-ticket compliance audit report.
    
    JSON Body:
        ticket_keys: List[str] - List of Jira issue keys
        format: str - "markdown" or "json" (default: markdown)
    """
    try:
        data = request.get_json()
        if not data or 'ticket_keys' not in data:
            return jsonify({'success': False, 'error': 'ticket_keys required'}), 400
            
        ticket_keys = data['ticket_keys']
        output_format = data.get('format', 'markdown')
        
        logger.info(f"Audit report requested for {len(ticket_keys)} tickets, format={output_format}")
        
        from src.reports.audit_report_builder import AuditReportBuilder
        
        jira_client = JiraClient()
        builder = AuditReportBuilder(jira_client)
        
        report_path = builder.generate_audit_report(ticket_keys, output_format)
        
        # If Markdown, return file content directly for preview if requested
        download_url = f'/api/reports/download/audit_reports/{os.path.basename(report_path)}'
        
        # Ensure download endpoint can serve from audit_reports subdir (needs update in download_report)
        # For now, let's just make sure output_dir in download_report handles subdirs or flat structure.
        # AuditReportBuilder defaults to ./outputs/audit_reports
        
        return jsonify({
            'success': True,
            'message': 'Audit report generated',
            'file_path': report_path,
            'download_url': download_url
        })

    except Exception as e:
        logger.error(f"Audit report generation failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/audit/ticket/<issue_key>', methods=['GET'])
def check_ticket_compliance(issue_key: str):
    """Evaluate compliance for a single ticket."""
    try:
        from src.reports.audit_report_builder import AuditReportBuilder
        
        jira_client = JiraClient()
        builder = AuditReportBuilder(jira_client)
        
        # Hack: leverage existing private methods for single ticket check
        # Ideally AuditReportBuilder would expose public check_ticket method
        ticket = builder._fetch_tickets_data([issue_key])[0]
        result = builder._evaluate_ticket(ticket)
        
        return jsonify({
            'success': True,
            'issue_key': issue_key,
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Ticket check failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
