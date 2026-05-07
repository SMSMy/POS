"""
النافذة الرئيسية
Main Window
"""

from PyQt5.QtWidgets import (
    QMainWindow, QToolBar, QAction, QStatusBar, QLabel,
    QStackedWidget, QWidget, QVBoxLayout, QMessageBox,
    QHBoxLayout, QPushButton, QFrame, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from loguru import logger

from database import get_current_shift, db_manager
from src.ui.pos_screen import POSScreen
from src.ui.inventory_dialog import InventoryDialog
from src.ui.reports_dialog import ReportsDialog
from src.ui.shifts_dialog import ShiftsDialog
from src.ui.settings_dialog import SettingsDialog
from src.ui.returns_dialog import ReturnsDialog


class MainWindow(QMainWindow):
    """النافذة الرئيسية للتطبيق"""

    def __init__(self, user_data: dict, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.current_shift = None
        self._setup_ui()
        self._check_shift_status()

        # الاتصال بمدير اللغة للتحديث عند تغيير اللغة
        from src.utils.language_manager import language_manager
        language_manager.language_changed.connect(self._on_language_changed)

    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        self.setWindowTitle(self.tr("نظام نقاط البيع - Restaurant POS"))
        self.showMaximized()

        # إعداد شريط الأدوات
        self._setup_toolbar()

        # إعداد المحتوى الرئيسي
        self._setup_central_widget()

        # إعداد شريط الحالة
        self._setup_statusbar()

    def _setup_toolbar(self):
        """إعداد شريط الأدوات"""
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(32, 32))
        toolbar.setMovable(False)

        # أزرار شريط الأدوات
        actions = [
            ("POS", self.tr("نقطة البيع"), "💰", self._show_pos),
            ("Inventory", self.tr("المخزون"), "📦", self._show_inventory),
            ("Reports", self.tr("التقارير"), "📊", self._show_reports),
            ("Shifts", self.tr("الورديات"), "🕒", self._show_shifts),
            ("Returns", self.tr("المرتجعات"), "🔄", self._show_returns),
            ("Settings", self.tr("الإعدادات"), "⚙️", self._show_settings),
        ]

        for name, text, icon, callback in actions:
            action = QAction(text, self)
            action.setToolTip(text)
            action.triggered.connect(callback)
            toolbar.addAction(action)

            # إضافة فاصل
            if name != "Settings":
                toolbar.addSeparator()

        self.addToolBar(toolbar)

    def _setup_central_widget(self):
        """إعداد المحتوى الرئيسي"""
        # المكدس
        self.stack = QStackedWidget()

        # شاشة نقطة البيع
        self.pos_screen = POSScreen(self.user_data)
        self.stack.addWidget(self.pos_screen)

        # شاشة ترحيبية
        welcome_widget = self._create_welcome_widget()
        self.stack.addWidget(welcome_widget)

        self.setCentralWidget(self.stack)

        # عرض شاشة الترحيب أولاً
        self.stack.setCurrentWidget(welcome_widget)

    def _create_welcome_widget(self) -> QWidget:
        """إنشاء شاشة الترحيب"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        # شعار المطعم
        from PyQt5.QtGui import QPixmap
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setFixedSize(150, 150)

        try:
            from database import get_setting
            import os
            logo_path = get_setting('restaurant_logo', '')
            if logo_path and os.path.exists(logo_path):
                pixmap = QPixmap(logo_path).scaled(130, 130, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                logo_label.setPixmap(pixmap)
                layout.addWidget(logo_label)
        except:
            pass

        # العنوان
        title = QLabel(self.tr("مرحباً بك في نظام نقاط البيع"))
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # اسم المستخدم
        user_label = QLabel(f"👤 {self.user_data['display_name']}")
        user_label.setFont(QFont("Arial", 16))
        user_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(user_label)

        # الدور
        role_text = {
            'admin': self.tr('مدير'),
            'manager': self.tr('مشرف'),
            'cashier': self.tr('كاشير')
        }.get(self.user_data['role'], self.user_data['role'])

        role_label = QLabel(f"🎭 {role_text}")
        role_label.setFont(QFont("Arial", 14))
        role_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(role_label)

        # فاصل
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #ddd;")
        separator.setFixedWidth(300)
        layout.addWidget(separator)

        # رسالة
        message = QLabel(self.tr("اختر من شريط الأدوات للبدء"))
        message.setFont(QFont("Arial", 12))
        message.setAlignment(Qt.AlignCenter)
        message.setStyleSheet("color: #666;")
        layout.addWidget(message)

        # زر الذهاب لنقطة البيع
        if self.user_data['role'] in ['admin', 'cashier']:
            go_pos_btn = QPushButton(self.tr("الذهاب لنقطة البيع"))
            go_pos_btn.setMinimumHeight(50)
            go_pos_btn.setFont(QFont("Arial", 14, QFont.Bold))
            go_pos_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 10px;
                    min-width: 200px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
            go_pos_btn.clicked.connect(self._show_pos)

            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            btn_layout.addWidget(go_pos_btn)
            btn_layout.addStretch()
            layout.addLayout(btn_layout)

        widget.setLayout(layout)
        return widget

    def _setup_statusbar(self):
        """إعداد شريط الحالة"""
        statusbar = QStatusBar()

        # معلومات الوردية
        self.shift_label = QLabel(self.tr("لا توجد وردية مفتوحة"))
        self.shift_label.setStyleSheet("font-weight: bold;")
        statusbar.addWidget(self.shift_label)

        statusbar.addPermanentWidget(QLabel("|"))

        # معلومات المستخدم
        user_label = QLabel(f"👤 {self.user_data['display_name']}")
        statusbar.addPermanentWidget(user_label)

        self.setStatusBar(statusbar)

    def _check_shift_status(self):
        """التحقق من حالة الوردية"""
        shift = get_current_shift()

        if shift:
            self.current_shift = shift
            self.shift_label.setText(
                f"🟢 {self.tr('الوردية')} #{shift['shift_number']} - {shift['display_name']}"
            )
            # تفعيل شاشة نقطة البيع
            self.pos_screen.setEnabled(True)
        else:
            self.shift_label.setText("🔴 لا توجد وردية مفتوحة")
            # تعطيل شاشة نقطة البيع
            self.pos_screen.setEnabled(False)

    def _show_pos(self):
        """عرض شاشة نقطة البيع"""
        if not self.current_shift and self.user_data['role'] == 'cashier':
            QMessageBox.warning(
                self,
                self.tr("تحذير"),
                self.tr("يجب فتح وردية أولاً قبل البدء في البيع")
            )
            return

        self.stack.setCurrentWidget(self.pos_screen)

    def _show_inventory(self):
        """عرض إدارة المخزون"""
        dialog = InventoryDialog(self)
        dialog.exec_()
        # تحديث شاشة البيع بعد إغلاق نافذة المخزون
        self.pos_screen._load_categories()
        self.pos_screen._load_products(self.pos_screen.selected_category)

    def _show_reports(self):
        """عرض التقارير"""
        dialog = ReportsDialog(self)
        dialog.exec_()

    def _show_shifts(self):
        """عرض إدارة الورديات"""
        dialog = ShiftsDialog(self, self.user_data)
        dialog.shift_opened.connect(self._on_shift_changed)
        dialog.shift_closed.connect(self._on_shift_changed)
        dialog.exec_()

    def _show_returns(self):
        """عرض المرتجعات"""
        dialog = ReturnsDialog(self, self.user_data, self.current_shift)
        dialog.exec_()

    def _show_settings(self):
        """عرض الإعدادات"""
        dialog = SettingsDialog(self)
        dialog.exec_()

    def _on_shift_changed(self):
        """معاللة تغيير الوردية"""
        self._check_shift_status()
        if self.current_shift:
            self.pos_screen.refresh_screen()

    def _on_language_changed(self, lang: str):
        """معالجة تغيير اللغة - Handle language change"""
        # تحديث عنوان النافذة
        self.setWindowTitle(self.tr("نظام نقاط البيع - Restaurant POS"))

        # تحديث شريط الحالة
        self._check_shift_status()

        # تحديث شريط الأدوات
        toolbar = self.findChild(QToolBar)
        if toolbar:
            # فلترة الأزرار الحقيقية فقط (استبعاد الفواصل)
            real_actions = [a for a in toolbar.actions() if not a.isSeparator()]
            action_texts = [
                self.tr("نقطة البيع"),
                self.tr("المخزون"),
                self.tr("التقارير"),
                self.tr("الورديات"),
                self.tr("المرتجعات"),
                self.tr("الإعدادات"),
            ]
            for i, action in enumerate(real_actions):
                if i < len(action_texts):
                    action.setText(action_texts[i])
                    action.setToolTip(action_texts[i])

    def closeEvent(self, event):
        """معاللة إغلاق النافذة"""
        if self.current_shift:
            reply = QMessageBox.question(
                self,
                self.tr("تأكيد الإغلاق"),
                self.tr("هناك وردية مفتوحة. هل تريد إغلاق النظام؟"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return

        logger.info("إغلاق التطبيق")
        event.accept()
