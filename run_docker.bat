@echo off
echo ===========================================
echo 🐳 Jira Compliance Dashboard - Docker Runner
echo ===========================================

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running or not installed.
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo.
echo [1/3] Checking environment configuration...
if not exist .env (
    echo [ERROR] .env file not found!
    echo Please copy .env.example to .env and fill in your credentials.
    pause
    exit /b 1
)

echo.
echo [2/3] Building and starting containers...
echo This may take a few minutes on the first run.
echo.
docker-compose up --build -d

if %errorlevel% neq 0 (
    echo [ERROR] Docker build failed.
    pause
    exit /b 1
)

echo.
echo [3/3] Deployment successful!
echo.
echo 📊 Dashboard is running at: http://localhost:6922/compliance
echo 📄 API Documentation:      http://localhost:6922/
echo 🏥 Health Check:           http://localhost:6922/health
echo.
echo Logs are being streamed below (Press Ctrl+C to stop logs, container will keep running)
echo =================================================================================
echo.

docker-compose logs -f app
