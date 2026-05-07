"""
Language Manager - مدير اللغة
Enables fast dynamic language switching without restart
تبديل سريع للغة بدون إعادة تشغيل
"""

from PyQt5.QtCore import QObject, pyqtSignal, QTranslator, Qt, QTimer, QThread
from PyQt5.QtWidgets import QApplication
from loguru import logger
import os
import sys
from pathlib import Path


class DatabaseSaveWorker(QThread):
    """Thread لحفظ اللغة في الخلفية بدون تجميد الواجهة"""
    def __init__(self, lang: str):
        super().__init__()
        self._lang = lang

    def run(self):
        try:
            from database import set_setting
            set_setting('language', self._lang)
        except Exception as e:
            logger.error(f"خطأ في حفظ اللغة: {e}")


class LanguageManager(QObject):
    """Singleton for managing application language - مدير اللغة المحسن للسرعة"""

    language_changed = pyqtSignal(str)  # Emitted when language changes

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        self._translator = None
        self._current_lang = self._get_saved_language()
        self._save_worker = None
        # تخزين مؤقت لملف الترجمة
        self._cached_translators = {}
        # تحميل مسبق للترجمات
        QTimer.singleShot(100, self._preload_translations)

    def _preload_translations(self):
        """تحميل مسبق لملفات الترجمة لتسريع التبديل"""
        try:
            for lang in ['ar', 'en']:
                qm_path = self._get_translation_path(lang)
                if os.path.exists(qm_path):
                    translator = QTranslator()
                    if translator.load(qm_path):
                        self._cached_translators[lang] = translator
                        logger.debug(f"تم تحميل الترجمة مسبقاً: {lang}")
        except Exception as e:
            logger.debug(f"فشل التحميل المسبق: {e}")

    def _get_saved_language(self) -> str:
        """Get saved language from database"""
        try:
            from database import get_setting
            return get_setting('language', 'ar')
        except:
            return 'ar'

    @property
    def current_language(self) -> str:
        return self._current_lang

    def switch_language(self) -> str:
        """Toggle between Arabic and English - تبديل سريع"""
        new_lang = 'en' if self._current_lang == 'ar' else 'ar'
        self.set_language_fast(new_lang)
        return new_lang

    def set_language_fast(self, lang: str):
        """تعيين اللغة بأسرع طريقة ممكنة - للأجهزة الضعيفة"""
        if lang == self._current_lang:
            return

        app = QApplication.instance()
        if not app:
            return

        # إزالة المترجم القديم
        if self._translator:
            app.removeTranslator(self._translator)

        # استخدام المترجم المخزن مؤقتاً أو تحميله
        if lang in self._cached_translators:
            self._translator = self._cached_translators[lang]
        else:
            self._translator = QTranslator()
            qm_path = self._get_translation_path(lang)
            if os.path.exists(qm_path):
                self._translator.load(qm_path)
                self._cached_translators[lang] = self._translator

        if self._translator:
            app.installTranslator(self._translator)

        # تحديث اللغة المحلية فوراً
        self._current_lang = lang

        # إرسال الإشارة للواجهة
        self.language_changed.emit(lang)

        # حفظ في قاعدة البيانات بالخلفية (لا تجميد)
        self._save_worker = DatabaseSaveWorker(lang)
        self._save_worker.start()

    def set_language(self, lang: str):
        """Set specific language - النسخة القديمة للتوافق"""
        self.set_language_fast(lang)

    def _get_translation_path(self, lang: str) -> str:
        """Get path to translation file"""
        if getattr(sys, 'frozen', False):
            base = Path(sys._MEIPASS)
        else:
            base = Path(__file__).parent.parent.parent

        return str(base / "translations" / f"{lang}.qm")

    def get_text(self, key: str, default: str = "") -> str:
        """Get translated text by key (for non-widget contexts)"""
        # This is a simple lookup, translations are handled by Qt
        return default


# Global instance
language_manager = LanguageManager()
