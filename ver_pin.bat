@echo off
title MacroEngine - Codigo PIN de Pareamento
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command "
$cfgPath = Join-Path $PSScriptRoot 'config.json'
$pin = '------'
$devicesInfo = ''
if (Test-Path $cfgPath) {
    try {
        $json = Get-Content $cfgPath -Raw | ConvertFrom-Json
        if ($json.security.pin) { $pin = $json.security.pin }
        if ($json.security.paired_devices -and $json.security.paired_devices.Count -gt 0) {
            $devicesInfo = \"`n  DISPOSITIVOS AUTORIZADOS SALVOS NO PC:`n\"
            foreach ($dev in $json.security.paired_devices) {
                $devicesInfo += \"  - [OK] \" + $dev.device_name + \" (Salvo permanentemente)`n\"
            }
        }
    } catch {}
}

Write-Host ''
Write-Host '=============================================================' -ForegroundColor Cyan
Write-Host '  MACROENGINE - CODIGO DE PAREAMENTO DO CELULAR' -ForegroundColor Yellow
Write-Host '=============================================================' -ForegroundColor Cyan
Write-Host ''
Write-Host '  SEU PIN ALEATORIO ATUAL:  ' -NoNewline
Write-Host \"$pin\" -ForegroundColor Green -BackgroundColor Black
Write-Host ''
if ($devicesInfo) {
    Write-Host $devicesInfo -ForegroundColor Green
}
Write-Host '  COMO CONECTAR O SEU CELULAR:' -ForegroundColor White
Write-Host '  1. Abra o app MacroEngine no celular.' -ForegroundColor Gray
Write-Host '  2. Toque no icone de Engrenagem (Configuracoes).' -ForegroundColor Gray
Write-Host '  3. Na aba Rede, va no card PAREAMENTO & SEGURANCA.' -ForegroundColor Gray
Write-Host \"  4. Digite o PIN aleatorio $pin e toque em PAREAR COM MEU PC.\" -ForegroundColor Gray
Write-Host ''
Write-Host '  IMPORTANTE: Apos o primeiro pareamento bem-sucedido,' -ForegroundColor Yellow
Write-Host '  os dados do celular ficam salvos permanentemente no PC' -ForegroundColor Yellow
Write-Host '  e voce nunca mais precisara digitar o codigo PIN!' -ForegroundColor Yellow
Write-Host '=============================================================' -ForegroundColor Cyan
Write-Host ''

Set-Clipboard -Value $pin
Write-Host '[OK] Codigo PIN copiado para a area de transferencia!' -ForegroundColor Green
Write-Host ''

Add-Type -AssemblyName System.Windows.Forms
$msg = \"Seu codigo PIN aleatorio do MacroEngine e:`n`n$pin`n`nEle foi copiado para a area de transferencia!`n`nApos parear pela primeira vez no app, seu celular ficara salvo permanentemente.\"
[System.Windows.Forms.MessageBox]::Show($msg, \"MacroEngine - Codigo de Pareamento\", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null
"

pause
