"""
Simple Flask app to test the compliance dashboard UI without database dependencies.
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import random

app = Flask(__name__, 
            static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'),
            static_url_path='/static')
CORS(app)

# Mock data for testing
MOCK_EMPLOYEES = [
    "John Doe", "Jane Smith", "Bob Johnson", "Alice Williams", 
    "Charlie Brown", "Diana Prince", "Eve Anderson", "Frank Miller"
]

def generate_mock_data(count=10):
    """Generate mock compliance data."""
    data = []
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    
    for i in range(count):
        employee = random.choice(MOCK_EMPLOYEES)
        is_compliant = random.random() > 0.3  # 70% pass rate
        
        record = {
            'employee_name': employee,
            'week_start_date': week_start.strftime('%Y-%m-%d'),
            'status_hygiene': 'Yes' if random.random() > 0.2 else 'No - Invalid transition',
            'cancellation': 'No' if random.random() > 0.1 else 'Yes - Task123 cancelled w/o approval',
            'update_frequency': random.choice(['Yes', 'Partial', 'No']),
            'role_ownership': 'Yes' if random.random() > 0.15 else 'No - Reporter = Assignee',
            'documentation': 'Yes' if random.random() > 0.2 else 'No - Description incomplete',
            'lifecycle': 'Yes' if random.random() > 0.1 else 'No - Skipped In Progress',
            'zero_tolerance': 'No' if random.random() > 0.05 else 'Yes',
            'overall_compliance': 'Pass' if is_compliant else 'Fail',
            'auditor_notes': 'All checks passed' if is_compliant else 'Multiple violations detected'
        }
        data.append(record)
    
    return data

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/')
def root():
    return jsonify({
        'name': 'Compliance Dashboard Test Server',
        'version': '1.0.0',
        'endpoints': {
            '/compliance': 'Compliance Dashboard UI',
            '/api/reports/compliance/live-data': 'Live compliance data (GET)',
            '/api/reports/teams': 'Teams list (GET)'
        }
    })

@app.route('/compliance')
def compliance_ui():
    """Serve the compliance dashboard UI."""
    return send_from_directory(app.static_folder, 'compliance-ui.html')

@app.route('/api/reports/compliance/live-data')
def get_live_compliance_data():
    """Get mock compliance data."""
    team_id = request.args.get('team_id', type=int)
    week_offset = request.args.get('week_offset', type=int, default=0)
    
    # Generate mock data
    data = generate_mock_data(count=random.randint(8, 15))
    
    return jsonify({
        'success': True,
        'count': len(data),
        'data': data,
        'metadata': {
            'team_id': team_id,
            'week_offset': week_offset,
            'generated_at': datetime.now().isoformat()
        }
    })

@app.route('/api/reports/teams')
def get_teams():
    """Get mock teams list."""
    teams = [
        {'id': 1, 'name': 'Engineering Team', 'code': 'ENG'},
        {'id': 2, 'name': 'Product Team', 'code': 'PROD'},
        {'id': 3, 'name': 'Design Team', 'code': 'DESIGN'},
        {'id': 4, 'name': 'QA Team', 'code': 'QA'}
    ]
    
    return jsonify({
        'success': True,
        'teams': teams
    })

if __name__ == '__main__':
    print("=" * 60)
    print("COMPLIANCE DASHBOARD TEST SERVER")
    print("=" * 60)
    print(f"Dashboard URL: http://localhost:6922/compliance")
    print(f"API Endpoint: http://localhost:6922/api/reports/compliance/live-data")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=6922, debug=True)
