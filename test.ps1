# InfraGuard Test Runner - Run analysis with container in background
# Usage: .\test.ps1 [-rebuild] [-stop]
# -rebuild: Force image rebuild (when dependencies change)
# -stop: Stop container after completion (normally runs in background)

param(
    [switch]$rebuild,
    [switch]$stop
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$ContainerName = "infraguard-sentinel"

Write-Host "[InfraGuard Sentinel - Test Runner - Fast Mode]" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

# Check .env
if (!(Test-Path ".env")) {
    Write-Host "[ERROR] .env file does not exist!" -ForegroundColor Red
    Write-Host "Create it: Copy-Item .env.template .env" -ForegroundColor Yellow
    exit 1
}

# Check if container is running
$running = docker ps --filter "name=$ContainerName" --quiet

if ([string]::IsNullOrWhiteSpace($running)) {
    Write-Host "[INFO] Container not running. Starting (once)..." -ForegroundColor Yellow
    docker-compose down --remove-orphans 2>$null
    if ($rebuild) {
        docker-compose build
    }
    docker-compose up -d
    Start-Sleep -Seconds 2
    Write-Host "[OK] Container is running in background!" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "[OK] Container already running ($($running.Substring(0, 12)))!" -ForegroundColor Green
    if ($rebuild) {
        Write-Host "[INFO] Rebuild: Stopping and restarting..." -ForegroundColor Yellow
        docker-compose down
        docker-compose build
        docker-compose up -d
        Start-Sleep -Seconds 2
    }
    Write-Host ""
}

Write-Host "[INFO] Running Terraform file analysis..." -ForegroundColor Cyan
Write-Host ""

# Run analysis
docker exec $ContainerName python dev.py

Write-Host ""
Write-Host "[OK] Analysis complete!" -ForegroundColor Green

if ($stop) {
    Write-Host "[INFO] Stopping container (--stop was used)..." -ForegroundColor Yellow
    docker-compose down
} else {
    Write-Host "[TIP] Container running in background. Use: docker-compose down (to stop)" -ForegroundColor Cyan
}
