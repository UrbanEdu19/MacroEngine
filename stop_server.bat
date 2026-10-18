@echo off
title MacroEngine - Encerrar Servidor

echo ============================================================
echo   MACROENGINE - ENCERRANDO SERVIDOR
echo ============================================================
echo.

powershell -NoProfile -Command "
$port = 8000
$killed = $false
try {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($conns) {
        $pids = $conns.OwningProcess | Select-Object -Unique
        foreach ($p in $pids) {
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
            Write-Host \"[OK] Processo PID $p finalizado (Porta $port liberada).\" -ForegroundColor Green
            $killed = $true
        }
    }
} catch {}

$pyProcs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*server.py*' }
if ($pyProcs) {
    foreach ($p in $pyProcs) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host \"[OK] Servidor Python PID $($p.ProcessId) encerrado.\" -ForegroundColor Green
        $killed = $true
    }
}

if (-not $killed) {
    Write-Host '[INFO] Nenhum servidor MacroEngine ativo na porta 8000.' -ForegroundColor Yellow
}
"

echo.
timeout /t 2 >nul
exit /b 0
