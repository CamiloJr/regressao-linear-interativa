@echo off
setlocal
cd /d "%~dp0"
title Regressao Linear Interativa - Aula 6
echo.
echo Regressao Linear Interativa - Aula 6
echo.
if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente Python local...
    where py >nul 2>&1
    if errorlevel 1 (python -m venv .venv) else (py -3 -m venv .venv)
    if errorlevel 1 goto python_error
)
".venv\Scripts\python.exe" -c "import pygame" >nul 2>&1
if errorlevel 1 (
    echo Instalando pygame-ce. Conexao com a internet e necessaria na primeira vez...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto install_error
)
echo Abrindo a aplicacao...
".venv\Scripts\python.exe" regressao_interativa.py
if errorlevel 1 goto app_error
exit /b 0

:python_error
echo.
echo Nao foi possivel criar o ambiente. Verifique se o Python e o lancador py estao instalados.
echo Consulte o README.md para as instrucoes manuais.
pause
exit /b 1

:install_error
echo.
echo A instalacao nao terminou. Confira sua conexao e a mensagem acima.
echo Consulte o README.md para as instrucoes manuais.
pause
exit /b 1

:app_error
echo.
echo A aplicacao encerrou com erro. Consulte a mensagem acima.
pause
exit /b 1
