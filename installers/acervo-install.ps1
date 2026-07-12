# Acervo Installer for Windows (PowerShell)
# Execução: powershell -ExecutionPolicy Bypass -File acervo-install.ps1

param(
    [string]$InstallPath = "$env:PROGRAMFILES\Acervo",
    [string]$Language = "pt-BR"
)

# Mensagens em português/inglês
$messages = @{
    "pt-BR" = @{
        "title" = "Instalador Acervo"
        "checking_python" = "Verificando Python 3.11+"
        "python_not_found" = "Python não encontrado! Baixando Python 3.12..."
        "python_installed" = "Python detectado: "
        "creating_venv" = "Criando ambiente virtual..."
        "installing_deps" = "Instalando dependências (pode levar alguns minutos)..."
        "creating_shortcuts" = "Criando atalhos no Desktop..."
        "success" = "✓ Acervo instalado com sucesso!"
        "start_server" = "Iniciando servidor web em http://127.0.0.1:8787..."
        "error" = "✗ Erro durante a instalação: "
    }
    "en-US" = @{
        "title" = "Acervo Installer"
        "checking_python" = "Checking Python 3.11+"
        "python_not_found" = "Python not found! Downloading Python 3.12..."
        "python_installed" = "Python detected: "
        "creating_venv" = "Creating virtual environment..."
        "installing_deps" = "Installing dependencies (this may take a few minutes)..."
        "creating_shortcuts" = "Creating Desktop shortcuts..."
        "success" = "✓ Acervo installed successfully!"
        "start_server" = "Starting web server at http://127.0.0.1:8787..."
        "error" = "✗ Installation error: "
    }
}

$msg = $messages[$Language]

Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        $($msg['title'])                 ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar Python
Write-Host $msg['checking_python'] -ForegroundColor Yellow
$python = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python -ErrorAction SilentlyContinue
}

if (-not $python) {
    Write-Host $msg['python_not_found'] -ForegroundColor Red
    Write-Host "Visite: https://www.python.org/downloads/" -ForegroundColor Gray
    exit 1
}

$pythonVersion = & $python.Source --version
Write-Host "$($msg['python_installed'])$pythonVersion" -ForegroundColor Green
Write-Host ""

# 2. Criar diretório de instalação
Write-Host "Instalando em: $InstallPath" -ForegroundColor Gray
if (-not (Test-Path $InstallPath)) {
    New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
}

# 3. Copiar arquivos da aplicação
Write-Host "Copiando arquivos..." -ForegroundColor Yellow
Copy-Item ".\acervo" "$InstallPath\" -Recurse -Force
Copy-Item ".\requirements.txt" "$InstallPath\" -Force
Copy-Item ".\README.md" "$InstallPath\" -Force

# 4. Criar venv
Write-Host $msg['creating_venv'] -ForegroundColor Yellow
& $python.Source -m venv "$InstallPath\.venv"
$pipExe = "$InstallPath\.venv\Scripts\pip.exe"
$pythonExe = "$InstallPath\.venv\Scripts\python.exe"

# 5. Instalar dependências
Write-Host $msg['installing_deps'] -ForegroundColor Yellow
& $pipExe install --upgrade pip | Out-Null
& $pipExe install -r "$InstallPath\requirements.txt"

# 6. Criar atalho no Desktop
Write-Host $msg['creating_shortcuts'] -ForegroundColor Yellow
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = "$desktopPath\Acervo.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonExe
$shortcut.Arguments = "-m acervo.cli serve"
$shortcut.WorkingDirectory = $InstallPath
$shortcut.IconLocation = "$InstallPath\acervo\web\icon.ico"
$shortcut.Description = "Acervo - Catalogação Jurídica Local"
$shortcut.Save()

# 7. Criar script de inicialização
$startScript = @"
@echo off
cd "$InstallPath"
"$pythonExe" -m acervo.cli serve
pause
"@
$startScript | Out-File -FilePath "$InstallPath\iniciar.bat" -Encoding ASCII

Write-Host ""
Write-Host $msg['success'] -ForegroundColor Green
Write-Host ""
Write-Host "Próximos passos:" -ForegroundColor Cyan
Write-Host "1. Procure por 'Acervo' no Menu Iniciar ou use o atalho no Desktop"
Write-Host "2. O servidor abrirá em http://127.0.0.1:8787"
Write-Host "3. Selecione seus arquivos de origem e destino"
Write-Host ""
Write-Host $msg['start_server'] -ForegroundColor Yellow
Start-Process -FilePath $pythonExe -ArgumentList "-m acervo.cli serve" -WorkingDirectory $InstallPath
