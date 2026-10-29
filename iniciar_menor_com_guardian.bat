@echo off
chcp 65001 > nul
setlocal

:: Ativa ambiente virtual se existir
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

echo ========================================================
echo [Menor.AI] Iniciando com Guardian Supervisor
echo ========================================================

python guardian_supervisor.py --project .

if errorlevel 1 (
    echo.
    echo ========================================================
    echo [Guardian] O supervisor encerrou com erro.
    echo Dica: execute 'python guardian_supervisor.py --project . --check' para depurar.
    echo ========================================================
    pause
)
