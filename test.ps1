# InfraGuard Test Runner - Spousteni analyzy s kontejnerem na pozadí
# Spusteni: .\test.ps1 [-rebuild] [-stop]
# -rebuild: Vynutit rebuild image (když se změní dependencies)
# -stop: Zastavit container po skončení (normálně běží na "pozadí)

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

# Kontrola .env
if (!(Test-Path ".env")) {
    Write-Host "[ERROR] .env soubor neexistuje!" -ForegroundColor Red
    Write-Host "Vytvor ho: Copy-Item .env.template .env" -ForegroundColor Yellow
    exit 1
}

# Zkontroluj, je-li kontejner spusteny
$running = docker ps --filter "name=$ContainerName" --quiet

if ([string]::IsNullOrWhiteSpace($running)) {
    Write-Host "[INFO] Kontejner nebezi. Spoustim (jednou)..." -ForegroundColor Yellow
    docker-compose down --remove-orphans 2>$null
    if ($rebuild) {
        docker-compose build
    }
    docker-compose up -d
    Start-Sleep -Seconds 2
    Write-Host "[OK] Kontejner je spusten a bezi na pozadí!" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "[OK] Kontejner uz bezi ($($running.Substring(0, 12)))!" -ForegroundColor Green
    if ($rebuild) {
        Write-Host "[INFO] Rebuild: Zastavuji a startuju..." -ForegroundColor Yellow
        docker-compose down
        docker-compose build
        docker-compose up -d
        Start-Sleep -Seconds 2
    }
    Write-Host ""
}

Write-Host "[INFO] Spousteni analyzy Terraform souboru..." -ForegroundColor Cyan
Write-Host ""

# Spust analyzu
docker exec $ContainerName python dev.py

Write-Host ""
Write-Host "[OK] Analyza hotova!" -ForegroundColor Green

if ($stop) {
    Write-Host "[INFO] Zastavuji kontejner (--stop se pouzil)..." -ForegroundColor Yellow
    docker-compose down
} else {
    Write-Host "[TIP] Container bezi na pozadí. Pouzij: docker-compose down (zastavit)" -ForegroundColor Cyan
}
