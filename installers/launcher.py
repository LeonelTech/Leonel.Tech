"""
Acervo Installer Launcher v2.0
Launches the improved PowerShell installer with proper error handling
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def get_base_dir():
    """Get base directory (works with both PyInstaller and regular Python)"""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        return os.path.dirname(sys.executable)
    else:
        # Running as regular Python script
        return os.path.dirname(os.path.abspath(__file__))

def check_powershell():
    """Check if PowerShell is available"""
    return shutil.which('powershell') is not None

def show_error_dialog(title, message):
    """Show error dialog using tkinter"""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        messagebox.showerror(title, message)
        root.destroy()
    except ImportError:
        # Fallback if tkinter not available
        print(f"\n❌ {title}")
        print(f"   {message}\n")

def show_info_dialog(title, message):
    """Show info dialog using tkinter"""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        messagebox.showinfo(title, message)
        root.destroy()
    except ImportError:
        # Fallback if tkinter not available
        print(f"\nℹ️  {title}")
        print(f"   {message}\n")

def main():
    """Main launcher function"""

    base_dir = get_base_dir()
    ps_script = os.path.join(base_dir, 'acervo-install.ps1')
    batch_script = os.path.join(base_dir, 'INSTALAR.bat')

    # ========================================================================
    # Check if required files exist
    # ========================================================================

    if not os.path.exists(ps_script):
        error_msg = (
            f"PowerShell script not found!\n\n"
            f"Expected: {ps_script}\n\n"
            f"Make sure 'acervo-install.ps1' is in the same directory."
        )
        show_error_dialog("Acervo Installer - File Not Found", error_msg)
        return 1

    # ========================================================================
    # Check if PowerShell is available
    # ========================================================================

    if not check_powershell():
        error_msg = (
            "PowerShell is not available on your system!\n\n"
            "Please install PowerShell 5.0 or higher:\n"
            "https://github.com/PowerShell/PowerShell/releases\n\n"
            "Or update Windows to Windows 10+ which includes PowerShell by default."
        )
        show_error_dialog("Acervo Installer - PowerShell Not Found", error_msg)
        return 1

    # ========================================================================
    # Show welcome message
    # ========================================================================

    info_msg = (
        "Welcome to Acervo Installer v2.0\n\n"
        "This will install Acervo - Catalogação Jurídica Local\n\n"
        "The installation process will:\n"
        "  • Check your Python environment\n"
        "  • Create a virtual environment\n"
        "  • Install all dependencies\n"
        "  • Create desktop shortcuts (optional)\n\n"
        "Click OK to continue..."
    )
    show_info_dialog("Acervo Installer", info_msg)

    # ========================================================================
    # Execute PowerShell installer
    # ========================================================================

    try:
        result = subprocess.run(
            [
                'powershell',
                '-NoProfile',
                '-ExecutionPolicy', 'Bypass',
                '-File', ps_script,
                '-Language', 'pt-BR'
            ],
            check=False,
            cwd=base_dir
        )

        return result.returncode

    except FileNotFoundError:
        error_msg = (
            "PowerShell executable not found!\n\n"
            "Please ensure PowerShell is properly installed and available in your system PATH."
        )
        show_error_dialog("Acervo Installer - Execution Error", error_msg)
        return 1

    except Exception as e:
        error_msg = (
            f"Error executing the installer:\n\n{str(e)}\n\n"
            f"Please try running INSTALAR.bat manually or check the log file."
        )
        show_error_dialog("Acervo Installer - Error", error_msg)
        return 1

if __name__ == '__main__':
    sys.exit(main())
