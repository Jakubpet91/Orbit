#!/usr/bin/env pwsh
<#
.SYNOPSIS
Chaos Testing & Review Pipeline - Chaos Injection + Sentinel Detection + AI Review

.PARAMETER Level
Severity level: low, medium, high, random

.EXAMPLES
.\chaos.ps1
.\chaos.ps1 -Level high
.\chaos.ps1 -Level medium -Rebuild
#>

param(
    [ValidateSet('low', 'medium', 'high', 'random')]
    [string]$Level = 'random',
    [switch]$Rebuild
)

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  CHAOS TESTING & REVIEW PIPELINE" -ForegroundColor Cyan
Write-Host "  Injection → Detection → AI Review" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Ensure container
if ($Rebuild) {
    Write-Host "[*] Building container..." -ForegroundColor Yellow
    docker-compose up -d --build 2>&1 | Out-Null
} else {
    $exists = docker-compose ps --services 2>$null | Select-String "infraguard-sentinel"
    if (!$exists) {
        Write-Host "[*] Starting container..." -ForegroundColor Yellow
        docker-compose up -d 2>&1 | Out-Null
    }
}

# Run chaos agent with full pipeline
Write-Host "[+] STAGE 1: Chaos Injection" -ForegroundColor Cyan
Write-Host "[+] STAGE 2: Sentinel Detection" -ForegroundColor Cyan  
Write-Host "[+] STAGE 3: AI Review Analysis" -ForegroundColor Cyan
Write-Host "[+] STAGE 4: Evaluation" -ForegroundColor Cyan
Write-Host ""
Write-Host "Running: chaos_agent.py --level $Level" -ForegroundColor Gray
Write-Host ""

# Execute chaos agent
$bashScript = @"
cd /code
git config user.email 'chaos@test.local'
git config user.name 'Chaos Agent'
python /app/chaos_agent.py --level $Level
"@

$output = docker-compose exec -T infraguard-sentinel bash -c $bashScript 2>&1
$outputStr = $output -join "`n"

# Display output
Write-Host $outputStr
Write-Host ""

# Save logs
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = "$env:TEMP/chaos_${timestamp}_${Level}.log"
$output | Out-File -FilePath $logFile -Encoding UTF8
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Log saved: $logFile" -ForegroundColor Gray
Write-Host "Branch:    https://github.com/Jakubpet91/Orbit/tree/chaos-testing" -ForegroundColor Gray
Write-Host ""
