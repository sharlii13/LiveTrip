# LiveTrip Server Startup Script
# This script sets up the environment and starts the server

Write-Host "🚀 Starting LiveTrip Server..." -ForegroundColor Green

# Add Node.js to PATH
$env:PATH += ";C:\Program Files\nodejs"

# Check if .env file exists
if (Test-Path ".env") {
    Write-Host "✅ .env file found" -ForegroundColor Green
} else {
    Write-Host "❌ .env file not found. Please create one with your Google OAuth credentials." -ForegroundColor Red
    Write-Host "See SETUP_INSTRUCTIONS.md for details." -ForegroundColor Yellow
    exit 1
}

# Check if Google credentials are set
$envContent = Get-Content .env
$hasGoogleId = $envContent | Where-Object { $_ -match "GOOGLE_CLIENT_ID=" -and $_ -notmatch "your_google_client_id_here" }
$hasGoogleSecret = $envContent | Where-Object { $_ -match "GOOGLE_CLIENT_SECRET=" -and $_ -notmatch "your_google_client_secret_here" }

if ($hasGoogleId -and $hasGoogleSecret) {
    Write-Host "✅ Google OAuth credentials configured" -ForegroundColor Green
} else {
    Write-Host "⚠️  Google OAuth credentials not configured yet" -ForegroundColor Yellow
    Write-Host "The server will start but OAuth won't work until you add real credentials." -ForegroundColor Yellow
    Write-Host "See SETUP_INSTRUCTIONS.md for details." -ForegroundColor Yellow
}

Write-Host "🌐 Starting server on http://localhost:5000" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host ""

# Start the server
& "C:\Program Files\nodejs\npx.cmd" tsx server/index.ts
