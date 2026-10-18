# MacroEngine - Servidor Desktop (PowerShell)
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Iniciando MacroEngine Server (FastAPI + UDP)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

# Identificar comando Python
$pyCmd = $null
if (Get-Command "py" -ErrorAction SilentlyContinue) {
    $pyCmd = "py -3.12"
} elseif (Get-Command "python" -ErrorAction SilentlyContinue) {
    $pyCmd = "python"
} elseif (Test-Path "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe") {
    $pyCmd = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
}

if (-not $pyCmd) {
    Write-Host "[ERRO] Interpretador Python não encontrado." -ForegroundColor Red
    exit 1
}

Write-Host "Interpretador localizado: $pyCmd" -ForegroundColor Green
Write-Host ""
Write-Host "[1/2] Verificando dependências..." -ForegroundColor Yellow

if ($pyCmd -match "^py\s+(.+)") {
    py -3.12 -m pip install -r requirements.txt --quiet
    Write-Host ""
    Write-Host "[2/2] Iniciando Servidor..." -ForegroundColor Green
    Write-Host ""
    py -3.12 server.py
} else {
    & $pyCmd -m pip install -r requirements.txt --quiet
    Write-Host ""
    Write-Host "[2/2] Iniciando Servidor..." -ForegroundColor Green
    Write-Host ""
    & $pyCmd server.py
}
