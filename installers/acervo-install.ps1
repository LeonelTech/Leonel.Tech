# Acervo Installer for Windows (PowerShell) - MELHORADO v2.0
# Execution: powershell -ExecutionPolicy Bypass -File acervo-install.ps1
# Features: Progress bar, error handling, desktop shortcut option

param(
    [string]$InstallPath = "$env:PROGRAMFILES\Acervo",
    [string]$Language = "pt-BR"
)

# ============================================================================
# GLOBAIS E CONSTANTES
# ============================================================================

$ProgressPercent = 0
$InstallationSteps = 8
$LogFile = "$env:TEMP\acervo-install.log"
$ErrorOccurred = $false
$ErrorMessage = ""
$ErrorType = "unknown"

# Mensagens em português/inglês
$messages = @{
    "pt-BR" = @{
        "title" = "Instalador Acervo v2.0"
        "checking_python" = "Verificando Python 3.11+"
        "python_not_found" = "Python não encontrado"
        "python_installed" = "Python detectado"
        "checking_permissions" = "Verificando permissões de escrita"
        "permission_denied" = "Permissão negada"
        "creating_directory" = "Criando diretório de instalação"
        "copying_files" = "Copiando arquivos da aplicação"
        "copy_error" = "Erro ao copiar arquivos"
        "creating_venv" = "Criando ambiente virtual"
        "venv_error" = "Erro ao criar ambiente virtual"
        "installing_deps" = "Instalando dependências"
        "deps_error" = "Erro ao instalar dependências"
        "creating_shortcuts" = "Criando atalhos"
        "finalizing" = "Finalizando instalação"
        "success" = "✓ INSTALAÇÃO COM SUCESSO!"
        "success_msg" = "Acervo foi instalado perfeitamente"
        "desktop_shortcut" = "Deseja adicionar ícone na área de trabalho?"
        "yes_text" = "Sim, adicionar"
        "no_text" = "Não, obrigado"
        "shortcut_added" = "✓ Atalho adicionado na área de trabalho"
        "server_starting" = "Iniciando servidor web..."
        "error_title" = "ERRO NA INSTALAÇÃO"
        "error_details" = "Detalhes do erro"
        "installation_failed" = "Instalação falhou"
        "next_steps" = "Próximos passos"
        "support" = "Consulte o arquivo de log para detalhes"
        "log_location" = "Arquivo de log"
    }
    "en-US" = @{
        "title" = "Acervo Installer v2.0"
        "checking_python" = "Checking Python 3.11+"
        "python_not_found" = "Python not found"
        "python_installed" = "Python detected"
        "checking_permissions" = "Checking write permissions"
        "permission_denied" = "Permission denied"
        "creating_directory" = "Creating installation directory"
        "copying_files" = "Copying application files"
        "copy_error" = "Error copying files"
        "creating_venv" = "Creating virtual environment"
        "venv_error" = "Error creating virtual environment"
        "installing_deps" = "Installing dependencies"
        "deps_error" = "Error installing dependencies"
        "creating_shortcuts" = "Creating shortcuts"
        "finalizing" = "Finalizing installation"
        "success" = "✓ INSTALLATION SUCCESSFUL!"
        "success_msg" = "Acervo has been installed successfully"
        "desktop_shortcut" = "Do you want to add an icon to the desktop?"
        "yes_text" = "Yes, add it"
        "no_text" = "No, thanks"
        "shortcut_added" = "✓ Shortcut added to desktop"
        "server_starting" = "Starting web server..."
        "error_title" = "INSTALLATION ERROR"
        "error_details" = "Error details"
        "installation_failed" = "Installation failed"
        "next_steps" = "Next steps"
        "support" = "See log file for details"
        "log_location" = "Log file"
    }
}

$msg = $messages[$Language]

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[$timestamp] [$Level] $Message"
    Add-Content -Path $LogFile -Value $logLine -Encoding UTF8
}

function Update-Progress {
    param(
        [int]$Step,
        [string]$Status
    )
    $percent = [math]::Min(($Step / $InstallationSteps) * 100, 100)
    $ProgressPercent = [int]$percent

    # Barra de progresso visual
    $barLength = 40
    $filledLength = [int]($barLength * $percent / 100)
    $bar = "█" * $filledLength + "░" * ($barLength - $filledLength)

    Write-Host ""
    Write-Host "  $bar [$ProgressPercent%]" -ForegroundColor Cyan
    Write-Host "  ▸ $Status" -ForegroundColor White
    Write-Host ""

    Write-Log "[$ProgressPercent%] $Status"
}

function Show-ErrorDialog {
    param(
        [string]$ErrorMsg,
        [string]$ErrorDetails = "",
        [string]$ErrorType = "unknown"
    )

    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        "$ErrorMsg`n`n$ErrorDetails",
        $msg['error_title'],
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    )

    Write-Log "ERROR: $ErrorMsg - $ErrorDetails" -Level "ERROR"
}

function Show-SuccessDialog {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        $msg['success_msg'],
        $msg['success'],
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information
    )
}

function Ask-DesktopShortcut {
    Add-Type -AssemblyName System.Windows.Forms
    $result = [System.Windows.Forms.MessageBox]::Show(
        $msg['desktop_shortcut'],
        "Acervo",
        [System.Windows.Forms.MessageBoxButtons]::YesNo,
        [System.Windows.Forms.MessageBoxIcon]::Question
    )
    return $result -eq "Yes"
}

# ============================================================================
# INÍCIO DA INSTALAÇÃO
# ============================================================================

Clear-Host
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                            ║" -ForegroundColor Cyan
Write-Host "║              📦 $($msg['title']) 📦              ║" -ForegroundColor Cyan
Write-Host "║                                                            ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Log "=== ACERVO INSTALLATION STARTED ==="
Write-Log "Language: $Language"
Write-Log "Install Path: $InstallPath"

# ============================================================================
# PASSO 1: VERIFICAR PYTHON
# ============================================================================

Update-Progress -Step 1 -Status $msg['checking_python']

$python = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python -ErrorAction SilentlyContinue
}

if (-not $python) {
    $ErrorOccurred = $true
    $ErrorType = "python_not_found"
    $ErrorMessage = "$($msg['python_not_found'])`n`nVisit: https://www.python.org/downloads/`n`nAfter installing Python, run this installer again."
    Write-Log "Python not found on system" -Level "ERROR"
} else {
    try {
        $pythonVersion = & $python.Source --version 2>&1
        Write-Log "Python found: $pythonVersion"
        Write-Host "  ✓ $($msg['python_installed']): $pythonVersion" -ForegroundColor Green
    } catch {
        $ErrorOccurred = $true
        $ErrorType = "python_check_failed"
        $ErrorMessage = "Failed to verify Python version`n`nError: $_"
        Write-Log "Python version check failed: $_" -Level "ERROR"
    }
}

if ($ErrorOccurred) {
    Show-ErrorDialog -ErrorMsg $ErrorMessage -ErrorType $ErrorType
    Write-Log "=== INSTALLATION FAILED ===" -Level "ERROR"
    Write-Host ""
    Write-Host "  📋 $($msg['log_location']): $LogFile" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# ============================================================================
# PASSO 2: VERIFICAR PERMISSÕES
# ============================================================================

Update-Progress -Step 2 -Status $msg['checking_permissions']

try {
    $parentPath = Split-Path $InstallPath -Parent
    $testFile = Join-Path $parentPath ".acervo_test_write"
    "test" | Out-File $testFile -ErrorAction Stop
    Remove-Item $testFile -Force -ErrorAction SilentlyContinue
    Write-Log "Write permissions verified"
} catch {
    $ErrorOccurred = $true
    $ErrorType = "permission_denied"
    $ErrorMessage = "$($msg['permission_denied'])`n`nInstall path: $InstallPath`n`nRun as Administrator or choose a different location."
    Write-Log "Permission check failed: $_" -Level "ERROR"
    Show-ErrorDialog -ErrorMsg $ErrorMessage -ErrorType $ErrorType
    Write-Log "=== INSTALLATION FAILED ===" -Level "ERROR"
    exit 1
}

# ============================================================================
# PASSO 3: CRIAR DIRETÓRIO
# ============================================================================

Update-Progress -Step 3 -Status $msg['creating_directory']

try {
    if (-not (Test-Path $InstallPath)) {
        New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
        Write-Log "Installation directory created: $InstallPath"
    }
    Write-Host "  ✓ $InstallPath" -ForegroundColor Green
} catch {
    $ErrorOccurred = $true
    $ErrorType = "directory_error"
    $ErrorMessage = "Failed to create directory`n`n$($msg['creating_directory'])`n`nError: $_"
    Write-Log "Directory creation failed: $_" -Level "ERROR"
    Show-ErrorDialog -ErrorMsg $ErrorMessage -ErrorType $ErrorType
    Write-Log "=== INSTALLATION FAILED ===" -Level "ERROR"
    exit 1
}

# ============================================================================
# PASSO 4: COPIAR ARQUIVOS
# ============================================================================

Update-Progress -Step 4 -Status $msg['copying_files']

try {
    $srcDir = Get-Location

    if (Test-Path ".\acervo") {
        Copy-Item ".\acervo" "$InstallPath\" -Recurse -Force -ErrorAction Stop
        Write-Log "Acervo source copied"
    }

    if (Test-Path ".\requirements.txt") {
        Copy-Item ".\requirements.txt" "$InstallPath\" -Force -ErrorAction Stop
        Write-Log "requirements.txt copied"
    }

    if (Test-Path ".\README.md") {
        Copy-Item ".\README.md" "$InstallPath\" -Force -ErrorAction Stop
        Write-Log "README.md copied"
    }

    Write-Host "  ✓ Files copied successfully" -ForegroundColor Green
} catch {
    $ErrorOccurred = $true
    $ErrorType = "copy_error"
    $ErrorMessage = "$($msg['copy_error'])`n`nError: $_`n`nMake sure you have read access to source files."
    Write-Log "File copy failed: $_" -Level "ERROR"
    Show-ErrorDialog -ErrorMsg $ErrorMessage -ErrorType $ErrorType
    Write-Log "=== INSTALLATION FAILED ===" -Level "ERROR"
    exit 1
}

# ============================================================================
# PASSO 5: CRIAR AMBIENTE VIRTUAL
# ============================================================================

Update-Progress -Step 5 -Status $msg['creating_venv']

try {
    & $python.Source -m venv "$InstallPath\.venv" -ErrorAction Stop
    $global:pythonExe = "$InstallPath\.venv\Scripts\python.exe"
    $global:pipExe = "$InstallPath\.venv\Scripts\pip.exe"
    Write-Log "Virtual environment created"
    Write-Host "  ✓ Virtual environment created" -ForegroundColor Green
} catch {
    $ErrorOccurred = $true
    $ErrorType = "venv_error"
    $ErrorMessage = "$($msg['venv_error'])`n`nError: $_"
    Write-Log "Virtual environment creation failed: $_" -Level "ERROR"
    Show-ErrorDialog -ErrorMsg $ErrorMessage -ErrorType $ErrorType
    Write-Log "=== INSTALLATION FAILED ===" -Level "ERROR"
    exit 1
}

# ============================================================================
# PASSO 6: INSTALAR DEPENDÊNCIAS
# ============================================================================

Update-Progress -Step 6 -Status $msg['installing_deps']

try {
    Write-Host "  ⏳ This may take a few minutes..." -ForegroundColor Yellow

    # Upgrade pip
    & $pipExe install --upgrade pip -q 2>&1 | Out-Null
    Write-Log "Pip upgraded"

    # Install requirements
    & $pipExe install -r "$InstallPath\requirements.txt" -q 2>&1 | Out-Null
    Write-Log "Dependencies installed"

    Write-Host "  ✓ Dependencies installed" -ForegroundColor Green
} catch {
    $ErrorOccurred = $true
    $ErrorType = "deps_error"
    $ErrorMessage = "$($msg['deps_error'])`n`nError: $_`n`nMake sure you have internet connection and enough disk space."
    Write-Log "Dependency installation failed: $_" -Level "ERROR"
    Show-ErrorDialog -ErrorMsg $ErrorMessage -ErrorType $ErrorType
    Write-Log "=== INSTALLATION FAILED ===" -Level "ERROR"
    exit 1
}

# ============================================================================
# PASSO 7: CRIAR ATALHO NO DESKTOP (Opcional)
# ============================================================================

Update-Progress -Step 7 -Status $msg['creating_shortcuts']

$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = "$desktopPath\Acervo.lnk"
$shortcutCreated = $false

try {
    # Pergunta ao usuário
    $shouldCreateShortcut = Ask-DesktopShortcut

    if ($shouldCreateShortcut) {
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $pythonExe
        $shortcut.Arguments = "-m acervo.main"
        $shortcut.WorkingDirectory = $InstallPath
        $shortcut.Description = "Acervo - Catalogação Jurídica Local"
        # $shortcut.IconLocation = "$InstallPath\acervo\web\icon.ico"
        $shortcut.Save()
        $shortcutCreated = $true
        Write-Log "Desktop shortcut created"
        Write-Host "  ✓ $($msg['shortcut_added'])" -ForegroundColor Green
    } else {
        Write-Log "User declined desktop shortcut"
        Write-Host "  ○ Desktop shortcut skipped" -ForegroundColor Gray
    }
} catch {
    Write-Log "Shortcut creation failed (non-fatal): $_" -Level "WARNING"
    Write-Host "  ⚠ Could not create desktop shortcut (non-fatal)" -ForegroundColor Yellow
}

# ============================================================================
# PASSO 8: FINALIZAR
# ============================================================================

Update-Progress -Step 8 -Status $msg['finalizing']

Write-Host "  ✓ Installation files prepared" -ForegroundColor Green
Write-Log "=== INSTALLATION COMPLETED SUCCESSFULLY ==="

# ============================================================================
# SCREEN DE SUCESSO
# ============================================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                                                            ║" -ForegroundColor Green
Write-Host "║  ✅ $($msg['success'])                     ✅  ║" -ForegroundColor Green
Write-Host "║                                                            ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Show-SuccessDialog

# ============================================================================
# PRÓXIMOS PASSOS
# ============================================================================

Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                  $($msg['next_steps'])                 ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

if ($shortcutCreated) {
    Write-Host "  1️⃣  Clique no ícone 'Acervo' na área de trabalho" -ForegroundColor White
    Write-Host "  2️⃣  O servidor abrirá em http://127.0.0.1:8787" -ForegroundColor White
    Write-Host "  3️⃣  Comece a usar o software!" -ForegroundColor White
} else {
    Write-Host "  1️⃣  Abra o terminal (CMD ou PowerShell)" -ForegroundColor White
    Write-Host "  2️⃣  Execute: cd ""$InstallPath"" && python -m acervo.main" -ForegroundColor White
    Write-Host "  3️⃣  Abra: http://127.0.0.1:8787 no navegador" -ForegroundColor White
}

Write-Host ""
Write-Host "  📋 $($msg['log_location']): $LogFile" -ForegroundColor Yellow
Write-Host ""
Write-Host ""

# Pergunta se deseja iniciar o servidor
$startServer = [System.Windows.Forms.MessageBox]::Show(
    $msg['server_starting'],
    "Acervo",
    [System.Windows.Forms.MessageBoxButtons]::YesNo,
    [System.Windows.Forms.MessageBoxIcon]::Question
)

if ($startServer -eq "Yes") {
    Write-Log "Starting server..."
    Start-Process -FilePath $pythonExe -ArgumentList "-m acervo.main" -WorkingDirectory $InstallPath
}
