#!/usr/bin/env python3
"""
Build script to create acervo-install.exe using PyInstaller.

Usage:
    pip install pyinstaller
    python installers/build_exe.py
"""

import sys
import subprocess
from pathlib import Path

def build_exe():
    """Build the Windows installer executable."""

    # Create a simple installer launcher script
    launcher = Path("installers/launcher.py")
    launcher_code = '''
import subprocess
import sys
import os

def main():
    """Simple launcher that runs the PowerShell installer."""
    # Get the directory where this exe is located
    base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
    ps_script = os.path.join(base_dir, "acervo-install.ps1")

    if not os.path.exists(ps_script):
        print("Erro: acervo-install.ps1 não encontrado!")
        input("Pressione ENTER para sair...")
        return 1

    try:
        subprocess.run([
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", ps_script,
            "-Language", "pt-BR"
        ], check=False)
    except Exception as e:
        print(f"Erro ao executar o instalador: {e}")
        input("Pressione ENTER para sair...")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
'''

    launcher.write_text(launcher_code)
    print(f"✓ Criado {launcher}")

    # Build with PyInstaller
    print("\n🔨 Compilando executável com PyInstaller...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "Acervo-Install",
        "--icon", "installers/acervo.ico" if Path("installers/acervo.ico").exists() else None,
        "--add-data", f"installers{os.pathsep}installers",
        "--distpath", "dist",
        "--buildpath", "build",
        "installers/launcher.py"
    ]

    cmd = [c for c in cmd if c is not None]  # Remove None values

    result = subprocess.run(cmd, cwd=Path.cwd())

    if result.returncode == 0:
        print("\n✅ Sucesso! Executável criado em: dist/Acervo-Install.exe")
        print("\nAgora você pode:")
        print("1. Distribuir dist/Acervo-Install.exe para os usuários")
        print("2. Eles clicam duas vezes e a instalação acontece automaticamente")
    else:
        print("\n❌ Erro ao compilar o executável")
        return 1

    return 0

if __name__ == "__main__":
    if "pyinstaller" not in sys.modules:
        print("PyInstaller não está instalado.")
        print("Instale com: pip install pyinstaller")
        sys.exit(1)

    import os
    sys.exit(build_exe())
