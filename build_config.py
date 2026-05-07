# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File for Atayb POS System
==========================================

الإعدادات:
- onedir: مجلد واحد للتوزيع
- UPX: ضغط الملفات التنفيذية
- استبعاد المكتبات غير الضرورية
- الربط مع pos_calc (Rust extension)

للتشغيل:
    pyinstaller build_config.py
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# المسار الحالي
CURRENT_DIR = os.path.dirname(os.path.abspath(SPEC))

# ===============================================
# إعدادات البناء
# ===============================================

APP_NAME = 'AtaybPOS'
APP_VERSION = '1.0.0'
MAIN_SCRIPT = 'main.py'
ICON_FILE = 'icon.ico'

# ===============================================
# الملفات المطلوبة (datas)
# ===============================================

datas = [
    # الترجمات
    ('translations', 'translations'),
    # الأصول
    ('assets', 'assets'),
    # أيقونة التطبيق
    ('icon.ico', '.'),
]

# إضافة صور المنتجات المحسّنة إذا وجدت
if os.path.exists(r'C:\imege_optimized'):
    datas.append((r'C:\imege_optimized', 'imege_optimized'))

# ===============================================
# المكتبات الثنائية (binaries)
# ===============================================

binaries = []

# إضافة pos_calc.pyd (Rust extension)
import site
for site_path in site.getsitepackages():
    pos_calc_path = os.path.join(site_path, 'pos_calc.cp311-win_amd64.pyd')
    if os.path.exists(pos_calc_path):
        binaries.append((pos_calc_path, '.'))
        print(f"[OK] Found pos_calc at: {pos_calc_path}")
        break
    # البحث عن اسم مختلف
    pos_calc_path2 = os.path.join(site_path, 'pos_calc.pyd')
    if os.path.exists(pos_calc_path2):
        binaries.append((pos_calc_path2, '.'))
        print(f"[OK] Found pos_calc at: {pos_calc_path2}")
        break

# ===============================================
# الوحدات المخفية (hiddenimports)
# ===============================================

hiddenimports = [
    # PyQt5
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.QtPrintSupport',

    # قاعدة البيانات
    'sqlite3',

    # التسجيل
    'loguru',

    # الصور
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',

    # الشبكة (للتيلجرام)
    'requests',
    'urllib3',

    # Rust extension
    'pos_calc',

    # الوحدات الداخلية
    'src',
    'src.ui',
    'src.utils',
    'src.ui.pos_screen',
    'src.ui.payment_dialog',
    'src.ui.reports_dialog',
    'src.ui.main_window',
    'src.ui.login_window',
    'src.ui.product_button',
    'src.ui.settings_dialog',
    'src.ui.inventory_window',
    'src.utils.printer',
    'src.utils.telegram',
    'src.utils.zatca',
    'src.utils.image_cache',

    # قاعدة البيانات
    'database',
]

# ===============================================
# الاستبعادات (excludes)
# ===============================================

excludes = [
    # مكتبات التطوير
    'pytest',
    'pylint',
    'flake8',
    'black',
    'isort',
    'mypy',

    # مكتبات غير مستخدمة
    'tkinter',
    'tk',
    'tcl',
    '_tkinter',
    'tkinter.filedialog',

    # Jupyter/IPython
    'IPython',
    'jupyter',
    'notebook',
    'ipykernel',

    # Matplotlib (غير مستخدم)
    'matplotlib',
    'mpl_toolkits',

    # Test frameworks
    'unittest',
    'doctest',

    # Documentation
    'sphinx',
    'pydoc',

    # Debugging
    'pdb',
    'cProfile',
    'profile',
]

# ===============================================
# تحليل الكود
# ===============================================

a = Analysis(
    [MAIN_SCRIPT],
    pathex=[CURRENT_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=2,  # تحسين bytecode
)

# ===============================================
# إزالة الملفات غير الضرورية
# ===============================================

# إزالة ملفات التوثيق والاختبار
a.binaries = [x for x in a.binaries if not x[0].startswith('test')]
a.binaries = [x for x in a.binaries if 'unittest' not in x[0]]

# ===============================================
# إنشاء PYZ
# ===============================================

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,
)

# ===============================================
# إنشاء EXE
# ===============================================

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # مطلوب لـ onedir
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # تفعيل UPX
    upx_exclude=[
        'vcruntime140.dll',
        'python311.dll',
        'Qt5*.dll',
    ],
    console=False,  # بدون نافذة console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_FILE if os.path.exists(ICON_FILE) else None,
    version=None,
)

# ===============================================
# إنشاء COLLECT (onedir)
# ===============================================

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'vcruntime140.dll',
        'python311.dll',
        'Qt5*.dll',
    ],
    name=APP_NAME,
)

print(f"\n{'='*60}")
print(f"Build completed: {APP_NAME}")
print(f"Output: dist/{APP_NAME}/")
print(f"{'='*60}")
