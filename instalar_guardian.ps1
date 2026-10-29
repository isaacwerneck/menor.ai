$ErrorActionPreference = 'Stop'
$Project = (Resolve-Path $PSScriptRoot).Path
$GuardianDir = Join-Path (Split-Path $Project -Parent) ('.' + (Split-Path $Project -Leaf) + '_guardian')
New-Item -ItemType Directory -Force -Path $GuardianDir | Out-Null
Copy-Item -Force (Join-Path $Project 'guardian_supervisor.py') (Join-Path $GuardianDir 'supervisor.py')
$Launcher = Join-Path $Project 'iniciar_menor_com_guardian.bat'
$Python = 'python'
@"
@echo off
"$Python" "$GuardianDir\supervisor.py" --project "$Project"
if errorlevel 1 pause
"@ | Set-Content -Encoding ASCII $Launcher
Write-Host "Guardian instalado fora da pasta editável do agente:" -ForegroundColor Green
Write-Host $GuardianDir
Write-Host "Use iniciar_menor_com_guardian.bat para abrir o Menor com recuperação automática."
