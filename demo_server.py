"""
Simple Demo Server for JIRA MCP Dashboard
Serves the compliance UI without requiring database connection
"""

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
import os
from datetime import datetime

app = Flask(__name__, static_folder='static')
CORS(app)

@app.route('/')
def index():
    """Root endpoint with API info."""
    return jsonify({
        'name': 'Jira MCP Dashboard API (Demo Mode)',
        'version': '1.0.0',
        'mode': 'DEMO - No database required',
        'endpoints': {
            '/': 'API info',
            '/compliance': 'Compliance Report UI',
            '/health': 'Health check',
            '/api/reports/teams': 'List teams (demo data)',
            '/api/reports/compliance/list': 'List reports (demo data)',
            '/api/reports/compliance/demo': 'Generate demo report'
        }
    })

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'mode': 'demo',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/compliance')
def compliance_ui():
    """Serve the compliance report UI."""
    return send_from_directory('static', 'compliance-ui.html')

@app.route('/api/reports/teams')
def get_teams():
    """Return demo teams data."""
    return jsonify({
        'success': True,
        'teams': [
            {'id': 1, 'code': 'BEE', 'name': 'Backend Engineering Excellence'},
            {'id': 2, 'code': 'AITEAM', 'name': 'AI Team'},
            {'id': 3, 'code': 'DHAP', 'name': 'Digital Health Application Platform'},
            {'id': 4, 'code': 'DEMT', 'name': 'Data Engineering and Management'},
            {'id': 5, 'code': 'DEV', 'name': 'Development Team'},
            {'id': 6, 'code': 'FRONT', 'name': 'Frontend Team'},
            {'id': 7, 'code': 'ASA', 'name': 'Acumen Strategy Analytics'},
            {'id': 8, 'code': 'CH', 'name': 'Corporate Health'},
            {'id': 9, 'code': 'CT', 'name': 'Corporate Technology'},
            {'id': 10, 'code': 'LEAD', 'name': 'Leadership Team'}
        ]
    })

@app.route('/api/reports/compliance/list')
def list_compliance_reports():
    """Return demo compliance reports list."""
    return jsonify({
        'success': True,
        'reports': [
            {
                'filename': 'JIRA_Compliance_Report_20260131_073745.xlsx',
                'created_at': '2026-01-31T07:37:45',
                'size_bytes': 15360
            },
            {
                'filename': 'JIRA_Compliance_Report_20260130_143022.xlsx',
                'created_at': '2026-01-30T14:30:22',
                'size_bytes': 14892
            },
            {
                'filename': 'JIRA_Compliance_Report_20260129_091533.xlsx',
                'created_at': '2026-01-29T09:15:33',
                'size_bytes': 16124
            }
        ]
    })

@app.route('/api/reports/compliance/demo', methods=['POST'])
def generate_demo_report():
    """Simulate demo report generation."""
    return jsonify({
        'success': True,
        'message': 'Demo report generated successfully',
        'file_name': f'JIRA_Compliance_Report_Demo_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
        'file_path': 'outputs/demo_report.xlsx',
        'mode': 'demo'
    })

@app.route('/api/reports/compliance/generate', methods=['POST'])
def generate_compliance_report():
    """Simulate compliance report generation."""
    return jsonify({
        'success': True,
        'message': 'Compliance report generated successfully (Demo Mode)',
        'file_name': f'JIRA_Compliance_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
        'file_path': 'outputs/compliance_report.xlsx',
        'mode': 'demo',
        'note': 'This is demo mode. Connect to database for real data.'
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 JIRA MCP Dashboard - Demo Server")
    print("=" * 60)
    print(f"📍 Server starting on: http://localhost:6922")
    print(f"🌐 Compliance UI: http://localhost:6922/compliance")
    print(f"📊 API Documentation: http://localhost:6922/")
    print(f"💚 Health Check: http://localhost:6922/health")
    print("=" * 60)
    print("⚠️  DEMO MODE: No database connection required")
    print("   Using mock data for demonstration purposes")
    print("=" * 60)
    
    app.run(
        host='0.0.0.0',
        port=6922,
        debug=True
    )
