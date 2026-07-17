@echo off
REM Acervo Installer for Windows (Batch Launcher) - v2.0
REM This script launches the improved PowerShell installer

chcp 65001 >nul
setlocal enabledelayedexpansion
setlocal enableextensions

cls
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                                                            ║
echo ║             📦 Acervo Installer v2.0 📦                   ║
echo ║                                                            ║
echo ║        Professional Installation with Progress Bar         ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo.

REM ============================================================================
REM Verificar se PowerShell está disponível
REM ============================================================================

where powershell >nul 2>nul
if errorlevel 1 (
    cls
    echo ╔════════════════════════════════════════════════════════════╗
    echo ║  ✗ ERROR: PowerShell not found                            ║
    echo ╚════════════════════════════════════════════════════════════╝
    echo.
    echo Please install PowerShell 5.0 or higher:
    echo https://github.com/PowerShell/PowerShell/releases
    echo.
    echo Or update Windows to Windows 10+ which includes PowerShell by default.
    echo.
    pause
    exit /b 1
)

REM ============================================================================
REM Language Selection Menu
REM ============================================================================

echo Select language / Selecione o idioma:
echo.
echo  [1] Português (Brasil)
echo  [2] English
echo.
set /p LANG_CHOICE="Enter your choice (1 or 2 / Digite 1 ou 2): "

if "%LANG_CHOICE%"=="1" (
    set LANGUAGE=pt-BR
    cls
    echo.
    echo ╔════════════════════════════════════════════════════════════╗
    echo ║  Iniciando instalação em Português...                      ║
    echo ╚════════════════════════════════════════════════════════════╝
    echo.
    timeout /t 2 >nul
) else if "%LANG_CHOICE%"=="2" (
    set LANGUAGE=en-US
    cls
    echo.
    echo ╔════════════════════════════════════════════════════════════╗
    echo ║  Starting installation in English...                       ║
    echo ╚════════════════════════════════════════════════════════════╝
    echo.
    timeout /t 2 >nul
) else (
    set LANGUAGE=pt-BR
    cls
    echo.
    echo ╔════════════════════════════════════════════════════════════╗
    echo ║  Invalid choice. Using Portuguese (default)...             ║
    echo ╚════════════════════════════════════════════════════════════╝
    echo.
    timeout /t 2 >nul
)

REM ============================================================================
REM Execute PowerShell installer
REM ============================================================================

REM Get the directory where this batch file is located
set SCRIPT_DIR=%~dp0

REM Check if acervo-install.ps1 exists
if not exist "%SCRIPT_DIR%acervo-install.ps1" (
    echo.
    echo ╔════════════════════════════════════════════════════════════╗
    echo ║  ✗ ERROR: acervo-install.ps1 not found                    ║
    echo ╚════════════════════════════════════════════════════════════╝
    echo.
    echo Expected location: %SCRIPT_DIR%acervo-install.ps1
    echo.
    pause
    exit /b 1
)

REM Execute the PowerShell script
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%SCRIPT_DIR%acervo-install.ps1' -Language %LANGUAGE%"

REM Check if PowerShell execution was successful
if errorlevel 1 (
    echo.
    echo ╔════════════════════════════════════════════════════════════╗
    echo ║  ✗ Installation failed. Check the log file for details.   ║
    echo ╚════════════════════════════════════════════════════════════╝
    echo.
    echo Log file: %TEMP%\acervo-install.log
    echo.
)

pause
exit /b %ERRORLEVEL%
