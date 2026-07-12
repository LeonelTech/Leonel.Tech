@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

cls
echo ╔════════════════════════════════════════════╗
echo ║     Acervo - Instalador para Windows       ║
echo ╚════════════════════════════════════════════╝
echo.

:: Verificar se PowerShell está disponível
where powershell >nul 2>nul
if errorlevel 1 (
    echo ✗ PowerShell não encontrado. Por favor, instale PowerShell 5.0+
    pause
    exit /b 1
)

:: Menu de idioma
echo Escolha o idioma / Choose language:
echo.
echo [1] Português (Brasil)
echo [2] English
echo.
set /p LANG_CHOICE="Digite a opção (1 ou 2): "

if "%LANG_CHOICE%"=="1" (
    set LANGUAGE=pt-BR
    echo Iniciando instalação em português...
) else if "%LANG_CHOICE%"=="2" (
    set LANGUAGE=en-US
    echo Starting installation in English...
) else (
    set LANGUAGE=pt-BR
    echo Usando Português (padrão)...
)

echo.
timeout /t 2

:: Executar o script PowerShell com política de execução temporária
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0acervo-install.ps1" -Language %LANGUAGE%

pause
