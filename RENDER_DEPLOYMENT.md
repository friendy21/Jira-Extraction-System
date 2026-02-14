# Render Deployment for JIRA Compliance Dashboard

## Overview

This Flask application provides a **complete JIRA compliance reporting system** with:
- ✅ **Web UI**: Interactive dashboard at `/compliance`
- ✅ **Backend API**: REST endpoints for ETL, reports, and metrics
- ✅ **Database**: PostgreSQL for data storage
- ✅ **Scheduled Jobs**: Automated ETL and report generation

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  JIRA Compliance Dashboard (Single Application)    │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Frontend (UI)                                      │
│  ├─ /compliance → compliance-ui.html               │
│  ├─ /audit      → audit-report-ui.html             │
│  └─ JavaScript calls API                           │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Backend (Flask + APIs)                             │
│  ├─ src/app.py                                     │
│  ├─ API Routes:                                    │
│  │   ├─ /api/reports/compliance/live-data         │
│  │   ├─ /api/etl/run                              │
│  │   └─ /api/metrics/*                            │
│  └─ Scheduled Jobs (ETL, Reports)                 │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Database (PostgreSQL - Render Managed)             │
│  └─ Stores extracted JIRA data                    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Deployment to Render

### Step 1: Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **JIRA Credentials**: Your JIRA API token and email
3. **Git Repository**: Push this code to GitHub/GitLab

### Step 2: Create PostgreSQL Database

1. Go to Render Dashboard → **New** → **PostgreSQL**
2. Name: `jira-compliance-db`
3. Database: `jira_mcp`
4. User: `jira_admin`
5. Region: Choose closest to you
6. Plan: Free tier for testing (Starter+ for production)
7. **Create Database**
8. 📝 **Copy Internal Database URL** from database details page

### Step 3: Deploy Web Service

1. Go to Render Dashboard → **New** → **Web Service**
2. Connect your Git repository
3. **Configuration**:

| Setting | Value |
|---------|-------|
| **Name** | `jira-compliance-dashboard` |
| **Region** | Same as database |
| **Branch** | `main` |
| **Root Directory** | `.` (or leave blank) |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | Uses `Procfile` (auto-detected) |
| **Plan** | Free tier for testing |

### Step 4: Environment Variables

Add these environment variables in Render dashboard:

```bash
# Flask Configuration
FLASK_SECRET_KEY=your-random-secret-key-change-this
FLASK_PORT=10000
FLASK_DEBUG=false

# Database (use Internal Database URL from Step 2)
DATABASE_URL=postgresql://user:pass@host/dbname

# JIRA Credentials
JIRA_DOMAIN=your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token

# Optional: Scheduler
SCHEDULER_ENABLED=true
```

> **Important**: Get Internal Database URL from your PostgreSQL service dashboard

### Step 5: Deploy!

1. Click **Create Web Service**
2. Wait for deployment to complete (~5-10 minutes)
3. Render will provide you with a URL like: `https://jira-compliance-dashboard.onrender.com`

### Step 6: Initialize Database

After deployment, initialize the database schema:

```bash
# Option 1: Use Render Shell
# Go to your web service → Shell tab
python -c "from src.database.connection import init_db; init_db()"

# Option 2: Create an initialization script
curl https://jira-compliance-dashboard.onrender.com/health
```

## Accessing Your Application

Once deployed:

| URL | Purpose |
|-----|---------|
| `https://your-app.onrender.com/` | API info |
| `https://your-app.onrender.com/compliance` | **Web UI Dashboard** |
| `https://your-app.onrender.com/audit` | **Auditor Mode UI** |
| `https://your-app.onrender.com/health` | Health check |
| `https://your-app.onrender.com/api/etl/run` | Trigger ETL (POST) |

## UI Features

The **Compliance Dashboard** provides:

1. **Real-time Data Display**
   - Interactive table with filtering and sorting
   - Auto-refresh every hour
   - Live statistics (pass/fail rates)

2. **Filtering**
   - By team
   - By week
   - By compliance status

3. **Export Options**
   - Export to Excel
   - Export to PDF

4. **API Integration**
   - UI calls `/api/reports/compliance/live-data`
   - Backend connects to PostgreSQL
   - Data extracted from JIRA via API

5. **Detailed Auditor Mode**
   - Deep-dive analysis of specific tickets
   - 22-point compliance check
   - Markdown & JSON export
   - Zero-Tolerance violation detection

## Post-Deployment

### Run Initial ETL

Trigger the first data extraction:

```bash
curl -X POST https://your-app.onrender.com/api/etl/run \
  -H "Content-Type: application/json" \
  -d '{"full": true}'
```

### Automated Scheduling

The application includes automatic scheduling:
- **ETL**: Runs daily at 2 AM
- **Reports**: Generated Monday at 6 AM

Configure in `config/config.yaml` or via environment variables.

## Troubleshooting

### UI Not Loading

Check:
1. `/health` endpoint returns `{"status": "healthy"}`
2. Flask log shows: `Flask application created`
3. Static folder exists and contains `compliance-ui.html`

### Database Connection Fails

1. Verify `DATABASE_URL` environment variable
2. Check PostgreSQL service is running
3. Ensure Internal Database URL is used (not External)

### JIRA API Errors

1. Verify `JIRA_DOMAIN`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
2. Test JIRA credentials manually
3. Check JIRA API token hasn't expired

### Free Tier Limitations

Render Free tier:
- ⚠️ Service spins down after 15 min inactivity
- ⚠️ First request after spin-down takes ~30s
- ✅ Solution: Upgrade to Starter plan ($7/month) for always-on

## Cost Estimate

| Component | Free Tier | Starter | Purpose |
|-----------|-----------|---------|---------|
| Web Service | ✅ Free | $7/month | Flask app |
| PostgreSQL | ✅ Free | $7/month | Database |
| **Total** | **$0/month** | **$14/month** | Production-ready |

## Monitoring

Access logs in Render Dashboard:
- **Logs**: Real-time application logs
- **Metrics**: CPU, Memory, Network usage
- **Events**: Deployment history

## Support

- 📚 Render Docs: https://render.com/docs
- 🐛 Check application logs for errors
- 📧 Contact support via Render dashboard

---

**Next Steps**: Deploy now and access your live compliance dashboard! 🚀
