# 📦 Acervo Installer v2.0 - Professional Installation Experience

## 🎯 What's New

The improved Acervo installer now provides:

✅ **Visual Progress Bar** - See installation progress with percentage  
✅ **Error Handling** - Detailed error messages for troubleshooting  
✅ **Success Dialog** - Professional success confirmation screen  
✅ **Desktop Shortcut Option** - Add icon to desktop after successful installation  
✅ **Logging System** - Complete installation logs for support  
✅ **Multi-Language** - Portuguese (pt-BR) and English (en-US) support  
✅ **Pre-flight Checks** - Validates Python, permissions, and disk space  
✅ **Beautiful UI** - Modern, professional installation interface  

---

## 🚀 Installation Methods

### Method 1: Batch File Launcher (Recommended for Windows)

**File:** `INSTALAR.bat`

```bash
INSTALAR.bat
```

This is the easiest way to start the installation on Windows:
1. Double-click `INSTALAR.bat`
2. Select your language (Portuguese or English)
3. Follow the on-screen prompts
4. Watch the progress bar
5. Choose to add desktop shortcut (optional)

**Advantages:**
- No additional tools needed
- Works on all Windows versions
- Clean, professional interface
- Language selection menu

---

### Method 2: PowerShell Script

**File:** `acervo-install.ps1`

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "acervo-install.ps1" -Language "pt-BR"
```

**Parameters:**
- `-Language "pt-BR"` - Portuguese (Brazil) - default
- `-Language "en-US"` - English (USA)
- `-InstallPath "C:\Custom\Path"` - Custom installation path (default: `C:\Program Files\Acervo`)

**Examples:**

```powershell
# Portuguese installation
powershell -ExecutionPolicy Bypass -File "acervo-install.ps1" -Language "pt-BR"

# English installation
powershell -ExecutionPolicy Bypass -File "acervo-install.ps1" -Language "en-US"

# Custom installation path
powershell -ExecutionPolicy Bypass -File "acervo-install.ps1" -InstallPath "D:\Acervo"
```

**Advantages:**
- Full control over installation process
- Can specify custom install paths
- Direct PowerShell execution

---

### Method 3: Python Launcher

**File:** `launcher.py`

```bash
python launcher.py
```

This method works on Windows, Mac, and Linux:
1. Run `python launcher.py`
2. A GUI window will appear with welcome message
3. Click OK to start installation
4. PowerShell will execute the installation script

**Advantages:**
- Cross-platform compatible
- Graphical user interface (GUI) dialogs
- Professional error messages

---

## 📊 Installation Flow

The installation process follows these steps (each with progress tracking):

```
1️⃣  Check Python (3.11+)
     └─ Verifies Python is installed and compatible

2️⃣  Check Permissions
     └─ Ensures write access to installation directory

3️⃣  Create Directory
     └─ Creates installation folder

4️⃣  Copy Files
     └─ Copies all application files

5️⃣  Create Virtual Environment
     └─ Sets up isolated Python environment

6️⃣  Install Dependencies
     └─ Installs all required Python packages

7️⃣  Create Desktop Shortcut (Optional)
     └─ Adds convenient desktop icon

8️⃣  Finalize
     └─ Completes installation and shows success screen
```

---

## 🎨 Installation Screens

### 1. Welcome Screen

```
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║              📦 Instalador Acervo v2.0 📦               ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

### 2. Progress Bar

```
  █████████████████████░░░░░░░░░░░░░░░░░░░░░░░ [65%]
  ▸ Installing dependencies...
```

### 3. Success Screen

```
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║  ✅ INSTALLATION SUCCESSFUL!                      ✅      ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

A dialog box will ask:
```
Do you want to add an icon to the desktop?
[Yes, add it] [No, thanks]
```

### 4. Next Steps Screen

Shows exactly how to run the application after installation.

---

## ⚠️ Error Handling

The installer includes professional error handling for:

### ❌ Python Not Found
- **Message:** "Python not found"
- **Solution:** Install Python 3.11+ from https://www.python.org/downloads/
- **Action:** Download and install Python, then run installer again

### ❌ Permission Denied
- **Message:** "Permission denied for installation path"
- **Solution:** Run as Administrator or choose different location
- **Action:** Right-click batch file → "Run as administrator"

### ❌ Copy Error
- **Message:** "Error copying files"
- **Solution:** Check source files and permissions
- **Action:** Ensure all application files are present and readable

### ❌ Virtual Environment Error
- **Message:** "Error creating virtual environment"
- **Solution:** Check Python installation and disk space
- **Action:** Verify Python works correctly and free up disk space

### ❌ Dependency Installation Error
- **Message:** "Error installing dependencies"
- **Solution:** Check internet connection and disk space
- **Action:** Ensure you have internet and at least 500MB free space

---

## 📋 Log Files

All installation details are logged to:

```
Windows: %TEMP%\acervo-install.log
Example: C:\Users\Username\AppData\Local\Temp\acervo-install.log
```

**View the log:**

```powershell
# PowerShell
notepad $env:TEMP\acervo-install.log

# Command Prompt
notepad %TEMP%\acervo-install.log
```

**Log contents include:**
- Installation start/end times
- Each installation step
- Progress percentages
- Any warnings or errors
- Final status

---

## 🎯 Post-Installation

After successful installation, you can run Acervo in these ways:

### Method 1: Desktop Shortcut (if created)
- Double-click the "Acervo" icon on desktop
- Server starts automatically
- Browser opens to http://127.0.0.1:8787

### Method 2: Command Line
```powershell
cd "C:\Program Files\Acervo"
python -m acervo.main
```

### Method 3: Using the Batch Script
```powershell
cd "C:\Program Files\Acervo"
./iniciar.bat
```

---

## 🔧 Troubleshooting

### "Port 8787 already in use"
```powershell
# Find the process using port 8787
netstat -ano | findstr :8787

# Kill the process (replace PID with number from above)
taskkill /PID <PID> /F

# Or change the port in acervo/config.py
```

### "Python not found in PATH"
```powershell
# Verify Python is installed
python --version

# If not installed, download from:
https://www.python.org/downloads/

# Make sure "Add Python to PATH" is checked during installation
```

### "Permission denied"
```powershell
# Run Command Prompt as Administrator
# Then execute the installer batch file again
```

### "Disk space error"
```powershell
# Free up at least 1GB of disk space
# Installation needs:
# - ~500MB for dependencies
# - ~200MB for Python virtual environment
# - ~100MB for application files
```

---

## 📞 Support

If you encounter issues:

1. **Check the log file:** `%TEMP%\acervo-install.log`
2. **Verify Python:** `python --version` (should be 3.11+)
3. **Check permissions:** Run as Administrator
4. **Free disk space:** Ensure at least 1GB available
5. **Internet connection:** Required for downloading dependencies
6. **PowerShell version:** Should be 5.0 or higher

---

## 🛠️ Advanced Options

### Custom Installation Path

```powershell
powershell -ExecutionPolicy Bypass -File "acervo-install.ps1" -InstallPath "D:\MyApps\Acervo"
```

### English Language Installation

```powershell
powershell -ExecutionPolicy Bypass -File "acervo-install.ps1" -Language "en-US"
```

### Silent Installation (No Dialogs)

For automated installations, use:

```powershell
# Note: This still shows progress in console
powershell -NoProfile -ExecutionPolicy Bypass -File "acervo-install.ps1" -Language "pt-BR" | Out-Null
```

---

## 📊 Installation Statistics

- **Installation time:** ~2-5 minutes (depending on internet)
- **Disk space required:** ~500-800MB
- **Dependencies:** ~400+ Python packages
- **Desktop shortcut:** Optional

---

## 🎉 Version History

### v2.0 (Current)
- ✅ Added visual progress bar with percentage
- ✅ Improved error handling with detailed messages
- ✅ Desktop shortcut optional prompt
- ✅ Professional success/error dialogs
- ✅ Comprehensive logging system
- ✅ Better UI/UX throughout
- ✅ Pre-flight validation checks

### v1.0 (Previous)
- Basic installation without visual feedback
- Limited error handling
- Manual desktop shortcut creation

---

**🎉 Welcome to Acervo! Happy cataloging!**
