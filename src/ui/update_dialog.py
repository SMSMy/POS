"""
نافذة التحديث
Update Dialog
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QFrame, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from loguru import logger
import sys


class CheckUpdateThread(QThread):
    """خيط فحص التحديثات"""
    finished = pyqtSignal(bool, str, str, str)  # has_update, version, url, notes/error

    def run(self):
        from src.utils.updater import get_update_manager
        manager = get_update_manager()
        has_update, version, url, notes = manager.check_for_updates()
        self.finished.emit(has_update, version or "", url or "", notes or "")


class DownloadThread(QThread):
    """خيط تحميل التحديث"""
    progress = pyqtSignal(int, int)  # downloaded, total
    finished = pyqtSignal(bool, str, str)  # success, file_path, error

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        from src.utils.updater import get_update_manager
        manager = get_update_manager()
        success, file_path, error = manager.download_update(
            self.url,
            progress_callback=lambda d, t: self.progress.emit(d, t)
        )
        self.finished.emit(success, file_path or "", error or "")


class UpdateDialog(QDialog):
    """نافذة التحديث التلقائي"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.download_thread = None
        self.check_thread = None
        self.installer_path = None
        self.download_url = None
        self._setup_ui()

    def _setup_ui(self):
        """إعداد الواجهة"""
        self.setWindowTitle(self.tr("تحديث التطبيق"))
        self.setFixedSize(500, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        # العنوان
        title = QLabel(self.tr("🔄 تحديث نظام نقطة البيع"))
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # فاصل
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        layout.addWidget(line)

        # معلومات الإصدار
        version_frame = QFrame()
        version_frame.setStyleSheet("background-color: #f8f9fa; border-radius: 8px; padding: 10px;")
        version_layout = QVBoxLayout(version_frame)

        # الإصدار الحالي
        from src.utils.updater import get_update_manager
        manager = get_update_manager()

        self.current_version_label = QLabel(self.tr(f"الإصدار الحالي: {manager.current_version}"))
        self.current_version_label.setFont(QFont("Arial", 12))
        version_layout.addWidget(self.current_version_label)

        # أحدث إصدار
        self.latest_version_label = QLabel(self.tr("أحدث إصدار: جاري الفحص..."))
        self.latest_version_label.setFont(QFont("Arial", 12))
        version_layout.addWidget(self.latest_version_label)

        layout.addWidget(version_frame)

        # الحالة
        self.status_label = QLabel(self.tr("جاهز للفحص"))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.status_label)

        # شريط التقدم
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # ملاحظات الإصدار
        self.release_notes = QTextEdit()
        self.release_notes.setReadOnly(True)
        self.release_notes.setMaximumHeight(100)
        self.release_notes.setPlaceholderText(self.tr("ملاحظات الإصدار ستظهر هنا..."))
        self.release_notes.hide()
        layout.addWidget(self.release_notes)

        layout.addStretch()

        # الأزرار
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self.check_btn = QPushButton(self.tr("🔍 التحقق من التحديثات"))
        self.check_btn.setMinimumHeight(45)
        self.check_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.check_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:disabled { background-color: #bdc3c7; }
        """)
        self.check_btn.clicked.connect(self._check_for_updates)
        buttons_layout.addWidget(self.check_btn)

        self.download_btn = QPushButton(self.tr("⬇️ تحميل التحديث"))
        self.download_btn.setMinimumHeight(45)
        self.download_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #219a52; }
            QPushButton:disabled { background-color: #bdc3c7; }
        """)
        self.download_btn.clicked.connect(self._download_update)
        self.download_btn.setEnabled(False)
        buttons_layout.addWidget(self.download_btn)

        self.install_btn = QPushButton(self.tr("🚀 تثبيت التحديث"))
        self.install_btn.setMinimumHeight(45)
        self.install_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.install_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #8e44ad; }
            QPushButton:disabled { background-color: #bdc3c7; }
        """)
        self.install_btn.clicked.connect(self._install_update)
        self.install_btn.setEnabled(False)
        buttons_layout.addWidget(self.install_btn)

        layout.addLayout(buttons_layout)

        # زر الإغلاق
        close_btn = QPushButton(self.tr("إغلاق"))
        close_btn.setMinimumHeight(35)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def _check_for_updates(self):
        """فحص التحديثات"""
        self.status_label.setText(self.tr("جاري الفحص..."))
        self.status_label.setStyleSheet("color: #3498db;")
        self.check_btn.setEnabled(False)
        self.download_btn.setEnabled(False)

        self.check_thread = CheckUpdateThread()
        self.check_thread.finished.connect(self._on_check_finished)
        self.check_thread.start()

    def _on_check_finished(self, has_update: bool, version: str, url: str, notes: str):
        """معالجة نتيجة الفحص"""
        self.check_btn.setEnabled(True)

        if not version and notes:
            # خطأ
            self.status_label.setText(notes)
            self.status_label.setStyleSheet("color: #e74c3c;")
            self.latest_version_label.setText(self.tr("أحدث إصدار: غير متاح"))
            return

        self.latest_version_label.setText(self.tr(f"أحدث إصدار: {version}"))

        if has_update:
            self.status_label.setText(self.tr("✅ يتوفر تحديث جديد!"))
            self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.download_url = url
            self.download_btn.setEnabled(True)

            if notes:
                self.release_notes.setText(notes)
                self.release_notes.show()
        else:
            self.status_label.setText(self.tr("✅ أنت تستخدم أحدث إصدار"))
            self.status_label.setStyleSheet("color: #27ae60;")

    def _download_update(self):
        """تحميل التحديث"""
        if not self.download_url:
            return

        self.status_label.setText(self.tr("جاري التحميل..."))
        self.status_label.setStyleSheet("color: #3498db;")
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.download_btn.setEnabled(False)
        self.check_btn.setEnabled(False)

        self.download_thread = DownloadThread(self.download_url)
        self.download_thread.progress.connect(self._on_download_progress)
        self.download_thread.finished.connect(self._on_download_finished)
        self.download_thread.start()

    def _on_download_progress(self, downloaded: int, total: int):
        """تحديث شريط التقدم"""
        if total > 0:
            percent = int((downloaded / total) * 100)
            self.progress_bar.setValue(percent)
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self.status_label.setText(self.tr(f"جاري التحميل: {mb_downloaded:.1f} / {mb_total:.1f} MB"))

    def _on_download_finished(self, success: bool, file_path: str, error: str):
        """معالجة انتهاء التحميل"""
        self.check_btn.setEnabled(True)

        if success:
            self.installer_path = file_path
            self.status_label.setText(self.tr("✅ تم التحميل بنجاح - اضغط 'تثبيت التحديث'"))
            self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.progress_bar.setValue(100)
            self.install_btn.setEnabled(True)
        else:
            self.status_label.setText(error)
            self.status_label.setStyleSheet("color: #e74c3c;")
            self.download_btn.setEnabled(True)

    def _install_update(self):
        """تثبيت التحديث"""
        if not self.installer_path:
            return

        reply = QMessageBox.question(
            self,
            self.tr("تأكيد التثبيت"),
            self.tr("سيتم إغلاق التطبيق لتثبيت التحديث.\nهل تريد المتابعة؟"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply != QMessageBox.Yes:
            return

        from src.utils.updater import get_update_manager
        manager = get_update_manager()
        success, error = manager.install_update(self.installer_path)

        if success:
            # إغلاق التطبيق
            QApplication.instance().quit()
            sys.exit(0)
        else:
            QMessageBox.critical(self, self.tr("خطأ"), error)

    def showEvent(self, event):
        """عند فتح النافذة - فحص تلقائي"""
        super().showEvent(event)
        # فحص تلقائي عند الفتح
        self._check_for_updates()
