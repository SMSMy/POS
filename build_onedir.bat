@echo off
chcp 65001 > nul
echo ==============================================================
echo    Building POS System - onedir mode for best performance
echo ==============================================================
echo.

REM Check if PyInstaller is installed
where pyinstaller > nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: PyInstaller not installed. Run: pip install pyinstaller
    pause
    exit /b 1
)

echo Building application...
echo.

REM Build command with onedir
pyinstaller --noconfirm --clean --onedir --windowed --name "POS_System" --add-data "database_schema.sql;." --add-data "src;src" --add-data "translations;translations" --add-data "assets;assets" --hidden-import "PyQt5" --hidden-import "PyQt5.QtCore" --hidden-import "PyQt5.QtGui" --hidden-import "PyQt5.QtWidgets" --hidden-import "PyQt5.sip" --hidden-import "sqlite3" --hidden-import "loguru" --hidden-import "PIL" --hidden-import "PIL.Image" --hidden-import "requests" --hidden-import "bcrypt" --hidden-import "arabic_reshaper" --hidden-import "bidi" --hidden-import "bidi.algorithm" --exclude-module "matplotlib" --exclude-module "numpy" --exclude-module "pandas" --exclude-module "scipy" --exclude-module "tkinter" --exclude-module "PyQt5.QtWebEngine" --noupx main.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ==============================================================
echo    BUILD SUCCESSFUL!
echo ==============================================================
echo.
echo Output folder: dist\POS_System\
echo.
echo Next steps:
echo    1. Copy dist\POS_System folder to C:\pos_system
echo    2. Copy pos_system.db to the same folder
echo    3. Run POS_System.exe
echo.
pause
