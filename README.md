# Jira MCP Dashboard

A production-ready system for extracting Jira data, storing it in PostgreSQL, and generating professional Excel dashboards.

## Features

- **Comprehensive Jira Data Extraction**: Projects, issues, sprints, boards, users, components, versions, labels, priorities, and more
- **PostgreSQL Storage**: Robust relational database with 30+ tables and pre-built reporting views
- **Professional Excel Dashboards**: Multi-sheet reports with charts, formatting, and metrics
- **REST API**: Flask-based API for triggering ETL, generating reports, and querying metrics
- **Automation**: Scheduled ETL and report generation via APScheduler
- **Docker Support**: Full containerization with Docker Compose

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Jira Cloud account with API access

### 1. Clone and Install

```bash
cd "Jira Program"
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Jira Credentials
JIRA_URL=https://your-company.atlassian.net
JIRA_USERNAME=your-email@company.com
JIRA_API_TOKEN=your-api-token

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=jira_dashboard
DB_USER=jira_etl
DB_PASSWORD=your-password

# Flask
FLASK_SECRET_KEY=your-secret-key
```

### 3. Initialize Database

```bash
# Using psql
psql -U postgres -c "CREATE DATABASE jira_dashboard;"
psql -U postgres -c "CREATE USER jira_etl WITH PASSWORD 'your-password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE jira_dashboard TO jira_etl;"

# Create schema
psql -U jira_etl -d jira_dashboard -f database/schema.sql
psql -U jira_etl -d jira_dashboard -f database/views.sql
```

Or use the Python script:

```bash
python scripts/init_db.py
```

### 4. Run ETL

```bash
# Full sync
python scripts/run_etl.py --full

# Incremental sync
python scripts/run_etl.py
```

### 5. Generate Report

```bash
# Generate for all teams
python scripts/generate_report.py

# Generate for specific team
python scripts/generate_report.py --team 1 --output my_report.xlsx
```

### 6. Start Web Server

```bash
# Development
python src/app.py

# Production with Gunicorn
gunicorn --bind 0.0.0.0:6922 --workers 2 src.app:app
```

## Docker Deployment

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/etl/run?full=true` | POST | Trigger ETL |
| `/api/etl/status` | GET | ETL run history |
| `/api/reports/generate?team_id=1` | POST | Generate dashboard report |
| `/api/reports/list` | GET | List dashboard reports |
| `/api/reports/download/{filename}` | GET | Download report |
| `/api/reports/teams` | GET | List teams |
| **`/api/reports/compliance/generate`** | **POST** | **Generate compliance report** |
| **`/api/reports/compliance/list`** | **GET** | **List compliance reports** |
| **`/api/reports/compliance/demo`** | **POST** | **Generate demo compliance report** |
| `/api/metrics/velocity/{team_id}` | GET | Team velocity |
| `/api/metrics/sprint/{sprint_id}` | GET | Sprint metrics |
| `/api/metrics/daily/{team_id}` | GET | Daily metrics |
| `/api/metrics/priority/{team_id}` | GET | Priority distribution |
| `/api/metrics/aging/{team_id}` | GET | Ticket aging |
| `/api/metrics/kanban/{board_id}` | GET | Kanban flow |

### Compliance Report API Examples

```bash
# Generate demo compliance report
curl -X POST http://localhost:6922/api/reports/compliance/demo

# Generate compliance report for last 4 weeks
curl -X POST http://localhost:6922/api/reports/compliance/generate

# Generate for specific date range
curl -X POST "http://localhost:6922/api/reports/compliance/generate?start_date=2026-01-01&end_date=2026-01-31"

# Generate for specific team
curl -X POST "http://localhost:6922/api/reports/compliance/generate?team_id=1&start_date=2026-01-20&end_date=2026-01-27"

# List all compliance reports
curl http://localhost:6922/api/reports/compliance/list

# Download a specific report
curl -O http://localhost:6922/api/reports/download/JIRA_Compliance_Report_20260131_073745.xlsx
```

## Configuration

### config/config.yaml

Main application configuration for Jira, database, ETL, reports, and scheduler settings.

### config/teams_mapping.yaml

Team and organization mappings with Jira project keys, JQL templates, and status category definitions.

## Dashboard Sheets

The generated Excel dashboard includes:

1. **Executive Summary**: Key metrics, velocity chart, overall statistics
2. **Velocity Analysis**: Sprint-by-sprint velocity with averages
3. **Sprint Analysis**: Detailed sprint metrics and goals
4. **Priority Analysis**: Issue distribution by priority with pie charts
5. **Ticket Aging**: Age bucket analysis with bar charts
6. **Time Tracking**: Estimated vs logged hours summary

## Compliance Reports

**NEW:** Generate single-sheet compliance audit reports tracking employee weekly JIRA process adherence.

### 🌐 Web UI (Recommended)

**Access the interactive web interface:**

```
http://localhost:6922/compliance
```

**Features:**
- 📅 Visual date pickers for easy date selection
- 👥 Team dropdown filter
- ⏳ Real-time progress bar with status updates
- 📊 Report history with one-click downloads
- 🎯 Demo mode (no JIRA required)
- 📱 Mobile-friendly responsive design

## Running

### Start the Flask API Server

```bash
python src/app.py
```

The server will start on `http://localhost:6922`

**Access Points:**
- API Documentation: `http://localhost:6922/`
- **Web UI for Compliance Reports**: `http://localhost:6922/compliance` ⭐
- Health Check: `http://localhost:6922/health`

**Usage:**
1. Open browser to `http://localhost:6922/compliance`
2. Select date range and team (optional)
3. Click "Generate Compliance Report"
4. Watch progress bar complete
5. Download from report history

See [`docs/WEB_UI_GUIDE.md`](docs/WEB_UI_GUIDE.md) for detailed UI documentation.

---

### 💻 Command Line (CLI)

For automation and scripting:

```bash
# Demo report with mock data
python scripts/demo_compliance_report.py

# Generate for all teams, last 4 weeks
python scripts/generate_compliance_report.py

# Generate for specific date range
python scripts/generate_compliance_report.py --start 2026-01-01 --end 2026-01-31

# Generate for specific team
python scripts/generate_compliance_report.py --team 1 --start 2026-01-01 --end 2026-01-31

# Custom output directory
python scripts/generate_compliance_report.py --output ./custom_reports/
```

### Compliance Report Structure

Single-sheet Excel report with 11 columns tracking 7 compliance criteria:

| Column | Description |
|--------|-------------|
| **Employee Name** | Full name of team member |
| **Week Start Date** | Monday of reporting week (YYYY-MM-DD) |
| **Status Hygiene Correct** | All tickets have proper status transitions |
| **Any Tasks Cancelled w/o Approval** | Tracks unauthorized cancellations |
| **Wed/Fri Updates Shared** | Biweekly update compliance |
| **Roles & Ownership Correct** | Proper assignee/reporter fields |
| **Documentation & Traceability Complete** | Links, comments, descriptions |
| **Lifecycle Adherence** | Follows workflow (Created→In Progress→Done) |
| **Zero-Tolerance Violation** | Critical violations (bulk changes, retroactive edits) |
| **Overall Compliance (Pass/Fail)** | Composite pass/fail |
| **Auditor's Notes** | Freeform comments on issues found |

### Compliance Criteria

1. **Status Hygiene**: Validates workflow transitions (To Do → In Progress → Done)
2. **Cancellation Check**: Detects tasks cancelled without approval comments
3. **Update Frequency**: Requires comments on Wednesday AND Friday each week
4. **Roles & Ownership**: Reporter ≠ Assignee, both fields populated
5. **Documentation**: Description > 50 chars, has linked issues or attachments
6. **Lifecycle**: Enforces Created → In Progress → Done sequence
7. **Zero-Tolerance**: Flags bulk changes (>5 issues/hour), missing required fields

**Pass/Fail Logic**: Fails if ANY criterion is "No" or any zero-tolerance violation exists.

### Output Format

- **Filename**: `JIRA_Compliance_Report_YYYYMMDD_HHMMSS.xlsx`
- **Formatting**: 
  - Header row: Bold white text on dark blue background
  - Pass: Green background (#00B050)
  - Fail: Red background (#FF0000)
  - All cells have borders
  - Header row frozen for scrolling

## Project Structure

```
Jira Program/
├── config/
│   ├── config.yaml              # Main configuration
│   └── teams_mapping.yaml       # Team mappings
├── database/
│   ├── schema.sql               # PostgreSQL schema
│   └── views.sql                # Reporting views
├── scripts/
│   ├── init_db.py               # Database initialization
│   ├── run_etl.py               # ETL runner
│   ├── generate_report.py       # Dashboard report generator
│   ├── generate_compliance_report.py  # NEW: Compliance report generator
│   └── demo_compliance_report.py      # NEW: Demo compliance report
├── src/
│   ├── api/                     # Flask API blueprints
│   ├── compliance/              # NEW: Compliance check framework
│   │   ├── __init__.py
│   │   └── checks.py            # 7 compliance check implementations
│   ├── database/                # SQLAlchemy models & queries
│   ├── reports/                 # Excel generation
│   │   ├── excel_builder.py    # Dashboard builder
│   │   └── compliance_builder.py  # NEW: Compliance report builder
│   ├── utils/                   # Helpers & logging
│   ├── app.py                   # Flask application
│   ├── config_manager.py        # Configuration
│   ├── etl_pipeline.py          # ETL orchestration
│   └── jira_client.py           # Jira REST API
├── outputs/                     # Generated reports
├── logs/                        # Application logs
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Scheduling

### Using APScheduler (Built-in)

Configure in `config/config.yaml`:

```yaml
scheduler:
  enabled: true
  etl_schedule: "0 2 * * *"      # 2 AM daily
  report_schedule: "0 6 * * 1"   # 6 AM Monday
```

### Using Windows Task Scheduler

Create a batch file `run_daily.bat`:

```batch
@echo off
cd /d "C:\path\to\Jira Program"
call venv\Scripts\activate
python scripts/run_etl.py
python scripts/generate_report.py
```

Then schedule via Task Scheduler.

## License

MIT License
