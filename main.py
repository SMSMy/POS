"""
نظام نقاط البيع للمطاعم - التطبيق الرئيسي
Restaurant POS System - Main Application
"""

import sys
import os
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QStatusBar, QLabel
from PyQt5.QtCore import Qt, QTranslator, QDir
from PyQt5.QtGui import QFont, QIcon
from loguru import logger

# إضافة المسار للاستيراد
sys.path.insert(0, str(Path(__file__).parent))

from database import db_manager, get_setting, set_setting, get_default_db_path
from src.ui.login_dialog import LoginDialog
from src.ui.main_window import MainWindow


# ==========================================
# إعدادات التسجيل
# ==========================================

app_data_dir = Path(get_default_db_path()).parent
log_dir = app_data_dir / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logger.add(
    log_dir / "app.log",
    rotation="1 day",
    retention="30 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)


# ==========================================
# دوال مساعدة
# ==========================================

def get_resource_path(relative_path: str) -> str:
    """الحصول على مسار المورد"""
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent
    return str(base_path / relative_path)


def setup_translator(app: QApplication) -> str:
    """إعداد الترجمة"""
    language = get_setting('language', 'ar')

    translator = QTranslator()
    qm_file = get_resource_path(f"translations/{language}.qm")

    if os.path.exists(qm_file):
        translator.load(qm_file)
        app.installTranslator(translator)
        logger.info(f"✅ تم تحميل الترجمة: {language}")
    else:
        logger.warning(f"⚠️ ملف الترجمة غير موجود: {qm_file}")

    # إعداد اتجاه النص - دائماً من اليمين لليسار
    app.setLayoutDirection(Qt.RightToLeft)

    # إعداد الخط حسب اللغة
    if language == 'ar':
        app.setFont(QFont("Traditional Arabic", 11))
    else:
        app.setFont(QFont("Arial", 10))

    return language


# ==========================================
# التطبيق الرئيسي
# ==========================================

class POSApplication(QApplication):
    """تطبيق نقاط البيع الرئيسي"""

    def __init__(self, argv):
        super().__init__(argv)
        self._setup_application()
        self.current_user = None
        self.main_window = None

    def _setup_application(self):
        """إعداد التطبيق"""
        # إعدادات High DPI
        self.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        self.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        # إعدادات التطبيق
        self.setApplicationName("Restaurant POS")
        self.setApplicationVersion("3.0")
        self.setOrganizationName("My Restaurant")

        # إعداد الترجمة
        self.language = setup_translator(self)

    def run(self):
        """تشغيل التطبيق"""
        try:
            # عرض نافذة تسجيل الدخول
            login_dialog = LoginDialog()

            if login_dialog.exec_() == LoginDialog.Accepted:
                self.current_user = login_dialog.user_data
                logger.info(f"✅ تسجيل دخول ناجح: {self.current_user['username']}")

                # فتح النافذة الرئيسية
                self.main_window = MainWindow(self.current_user)
                self.main_window.show()

                return self.exec_()
            else:
                logger.info("تم إلغاء تسجيل الدخول")
                return 0

        except Exception as e:
            logger.error(f"❌ خطأ في تشغيل التطبيق: {e}")
            QMessageBox.critical(None, "خطأ", f"حدث خطأ في تشغيل التطبيق:\n{str(e)}")
            return 1
        finally:
            db_manager.close()


# ==========================================
# نقطة الدخول
# ==========================================

def main():
    """الدالة الرئيسية"""
    try:
        logger.info("=" * 50)
        logger.info("بدء تشغيل نظام نقاط البيع")
        logger.info("=" * 50)

        # إنشاء التطبيق
        app = POSApplication(sys.argv)

        # تشغيل التطبيق
        return app.run()

    except Exception as e:
        logger.error(f"❌ خطأ فادح: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
