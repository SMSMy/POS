@echo off
chcp 65001 >nul
title Atayb POS Installation Script
color 0A

echo ============================================================
echo          Atayb POS System - Installation Script
echo ============================================================
echo.

set INSTALL_DIR=C:\AtaybPOS
set DATA_DIR=C:\AtaybPOS\data
set SOURCE_DIR=%~dp0dist\AtaybPOS

echo [INFO] Source: %SOURCE_DIR%
echo [INFO] Target: %INSTALL_DIR%
echo.

:: التحقق من وجود مجلد المصدر
if not exist "%SOURCE_DIR%" (
    echo [ERROR] Build folder not found: %SOURCE_DIR%
    echo [INFO] Please run build first: pyinstaller build_config.py
    pause
    exit /b 1
)

:: إنشاء مجلد التثبيت
echo [1/6] Creating installation folder...
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    echo       Created: %INSTALL_DIR%
) else (
    echo       Folder exists: %INSTALL_DIR%
)

:: إنشاء مجلد البيانات
echo [2/6] Creating data folder...
if not exist "%DATA_DIR%" (
    mkdir "%DATA_DIR%"
    mkdir "%DATA_DIR%\backups"
    mkdir "%DATA_DIR%\logs"
    echo       Created: %DATA_DIR%
) else (
    echo       Folder exists: %DATA_DIR%
)

:: نسخ ملفات البرنامج
echo [3/6] Copying program files...
xcopy "%SOURCE_DIR%\*" "%INSTALL_DIR%\" /E /Y /Q >nul
echo       Copied all program files

:: نسخ قاعدة البيانات إذا لم تكن موجودة
echo [4/6] Setting up database...
if not exist "%DATA_DIR%\pos_system.db" (
    if exist "%SOURCE_DIR%\pos_system.db" (
        copy "%SOURCE_DIR%\pos_system.db" "%DATA_DIR%\" >nul
        echo       Copied database to data folder
    ) else (
        echo       No database found, will be created on first run
    )
) else (
    echo       Database already exists, keeping existing data
)

:: إنشاء اختصار على سطح المكتب
echo [5/6] Creating desktop shortcut...
set SHORTCUT_FILE=%USERPROFILE%\Desktop\Atayb POS.lnk
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_FILE%'); $s.TargetPath = '%INSTALL_DIR%\AtaybPOS.exe'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.IconLocation = '%INSTALL_DIR%\AtaybPOS.exe,0'; $s.Save()"
if exist "%SHORTCUT_FILE%" (
    echo       Created: %SHORTCUT_FILE%
) else (
    echo       [WARNING] Could not create shortcut
)

:: نسخ الصور المحسّنة
echo [6/6] Copying optimized images...
if exist "C:\imege_optimized" (
    if not exist "%INSTALL_DIR%\imege_optimized" (
        mkdir "%INSTALL_DIR%\imege_optimized"
    )
    xcopy "C:\imege_optimized\*" "%INSTALL_DIR%\imege_optimized\" /E /Y /Q >nul
    echo       Copied optimized images
) else (
    echo       No optimized images found
)

echo.
echo ============================================================
echo                   Installation Complete!
echo ============================================================
echo.
echo Program installed to: %INSTALL_DIR%
echo Data folder: %DATA_DIR%
echo Desktop shortcut created
echo.
echo To start the program:
echo   - Double-click the desktop shortcut, or
echo   - Run: %INSTALL_DIR%\AtaybPOS.exe
echo.
echo ============================================================
pause
