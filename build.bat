@echo off
chcp 65001 >nul
title Atayb POS Build Script
color 0B

echo ============================================================
echo            Atayb POS System - Build Script
echo ============================================================
echo.

:: التحقق من وجود PyInstaller
where pyinstaller >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyInstaller not found!
    echo [INFO] Installing PyInstaller...
    pip install pyinstaller
)

:: التحقق من وجود UPX (اختياري)
where upx >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [WARNING] UPX not found - compression will be skipped
    echo [INFO] Download UPX from: https://upx.github.io/
) else (
    echo [OK] UPX found
)

:: تنظيف البناء السابق
echo.
echo [1/4] Cleaning previous build...
if exist "build" rmdir /S /Q "build"
if exist "dist" rmdir /S /Q "dist"
echo       Done

:: نسخ قاعدة البيانات للبناء
echo.
echo [2/4] Preparing files...
if exist "pos_system.db" (
    echo       Database found
) else (
    echo       [WARNING] No database file
)

:: بناء التطبيق
echo.
echo [3/4] Building application...
echo       This may take a few minutes...
echo.

pyinstaller --clean --noconfirm build_config.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

:: نسخ الملفات الإضافية
echo.
echo [4/4] Copying additional files...

:: نسخ قاعدة البيانات
if exist "pos_system.db" (
    copy "pos_system.db" "dist\AtaybPOS\" >nul
    echo       Copied database
)

:: نسخ الصور المحسّنة
if exist "C:\imege_optimized" (
    if not exist "dist\AtaybPOS\imege_optimized" (
        mkdir "dist\AtaybPOS\imege_optimized"
    )
    xcopy "C:\imege_optimized\*" "dist\AtaybPOS\imege_optimized\" /E /Y /Q >nul
    echo       Copied optimized images
)

echo.
echo ============================================================
echo                    Build Complete!
echo ============================================================
echo.
echo Output folder: dist\AtaybPOS\
echo.

:: حساب الحجم
for /f "tokens=3" %%a in ('dir "dist\AtaybPOS" /-c 2^>nul ^| find "File(s)"') do set SIZE=%%a
echo Total size: approximately %SIZE% bytes
echo.

echo Next steps:
echo   1. Run install.bat to install to C:\AtaybPOS
echo   2. Or copy dist\AtaybPOS\ to target machine
echo.
echo ============================================================
pause
