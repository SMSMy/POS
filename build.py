"""
سكربت البناء باستخدام PyInstaller
Build script using PyInstaller
"""

import os
import sys
import subprocess
from pathlib import Path
from loguru import logger


def build_windows():
    """بناء التطبيق على Windows"""
    try:
        # التحقق من وجود PyInstaller
        try:
            import PyInstaller
        except ImportError:
            logger.error("❌ PyInstaller غير مثبت. قم بتثبيته أولاً: pip install pyinstaller")
            return False
        
        # إنشاء ملف .spec مخصص
        spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

# الملفات الإضافية
added_files = [
    ('database_schema.sql', '.'),
    ('translations', 'translations'),
    ('README.md', '.'),
]

# تحليل المسار
pathex = [str(Path(__file__).parent)]

a = Analysis(
    ['main.py'],
    pathex=pathex,
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtPrintSupport',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RestaurantPOS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # يمكنك إضافة أيقونة
)
'''
        
        # حفظ ملف .spec
        with open('main.spec', 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        # البناء
        logger.info("🔄 بدء عملية البناء...")
        result = subprocess.run([
            sys.executable, '-m', 'PyInstaller', 
            '-y',
            '--onedir',
            '--windowed',
            '--name=RestaurantPOS',
            '--icon=icon.ico',
            '--add-data=database_schema.sql;.',
            '--add-data=version.json;.',
            '--add-data=translations;translations',
            '--hidden-import=PyQt5.QtCore',
            '--hidden-import=PyQt5.QtGui', 
            '--hidden-import=PyQt5.QtWidgets',
            '--hidden-import=PyQt5.QtPrintSupport',
            'main.py'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ تم بناء التطبيق بنجاح!")
            logger.info(f"📁 الملف النهائي: dist/RestaurantPOS.exe")
            return True
        else:
            logger.error(f"❌ فشل البناء: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ خطأ في البناء: {e}")
        return False


def build_linux():
    """بناء التطبيق على Linux"""
    try:
        logger.info("⚠️ البناء على Linux غير مدعوم حالياً للواجهات الرسومية")
        logger.info("💡 يمكن تشغيل التطبيق مباشرة باستخدام: python main.py")
        return False
        
    except Exception as e:
        logger.error(f"❌ خطأ: {e}")
        return False


def main():
    """الدالة الرئيسية"""
    logger.info("=" * 50)
    logger.info("سكربت بناء نظام نقاط البيع")
    logger.info("=" * 50)
    
    # تحديد النظام
    if sys.platform == 'win32':
        logger.info("🖥️ تم اكتشاف نظام Windows")
        success = build_windows()
    elif sys.platform.startswith('linux'):
        logger.info("🐧 تم اكتشاف نظام Linux")
        success = build_linux()
    else:
        logger.error(f"❌ نظام التشغيل غير مدعوم: {sys.platform}")
        return False
    
    if success:
        logger.info("✅ انتهى البناء بنجاح!")
    else:
        logger.error("❌ فشل البناء")
    
    return success


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)