"""
شاشة تسجيل الدخول
Login Dialog
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QMessageBox, QFrame, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap

from database import db_manager


class LoginDialog(QDialog):
    """نافذة تسجيل الدخول"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_data = None
        self._setup_ui()

    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        self.setWindowTitle(self.tr("تسجيل الدخول"))
        self.setFixedSize(400, 500)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        # التخطيط الرئيسي
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # الشعار والعنوان
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.NoFrame)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setAlignment(Qt.AlignCenter)

        # الشعار (صورة المطعم)
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setFixedSize(120, 120)

        # محاولة تحميل شعار المطعم
        try:
            from database import get_setting
            import os
            logo_path = get_setting('restaurant_logo', '')
            if logo_path and os.path.exists(logo_path):
                pixmap = QPixmap(logo_path).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                logo_label.setPixmap(pixmap)
            else:
                # لا يوجد شعار - استخدام اسم المطعم
                company_name = get_setting('company_name', 'مطعم')
                logo_label.setText(company_name[:2] if len(company_name) >= 2 else company_name)
                logo_label.setFont(QFont("Arial", 36, QFont.Bold))
                logo_label.setStyleSheet("color: #27ae60;")
        except:
            logo_label.setText("POS")
            logo_label.setFont(QFont("Arial", 36, QFont.Bold))
            logo_label.setStyleSheet("color: #27ae60;")

        header_layout.addWidget(logo_label)

        # العنوان
        title_label = QLabel(self.tr("نظام نقاط البيع"))
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)

        subtitle_label = QLabel(self.tr("Restaurant POS System"))
        subtitle_label.setFont(QFont("Arial", 10))
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #666;")
        header_layout.addWidget(subtitle_label)

        main_layout.addWidget(header_frame)

        # فاصل
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #ddd;")
        main_layout.addWidget(separator)

        # نموذج تسجيل الدخول
        form_frame = QFrame()
        form_frame.setFrameShape(QFrame.NoFrame)
        form_layout = QFormLayout(form_frame)
        form_layout.setSpacing(15)

        # اسم المستخدم
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(self.tr("اسم المستخدم"))
        self.username_input.setMinimumHeight(45)
        self.username_input.setFont(QFont("Arial", 12))
        self.username_input.setAlignment(Qt.AlignCenter)
        form_layout.addRow(self.tr("اسم المستخدم:"), self.username_input)

        # كلمة المرور
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText(self.tr("كلمة المرور"))
        self.password_input.setMinimumHeight(45)
        self.password_input.setFont(QFont("Arial", 12))
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setAlignment(Qt.AlignCenter)
        form_layout.addRow(self.tr("كلمة المرور:"), self.password_input)

        main_layout.addWidget(form_frame)

        # زر تسجيل الدخول
        self.login_button = QPushButton(self.tr("تسجيل الدخول"))
        self.login_button.setMinimumHeight(50)
        self.login_button.setFont(QFont("Arial", 14, QFont.Bold))
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        self.login_button.clicked.connect(self._on_login_clicked)
        main_layout.addWidget(self.login_button)

        # معلومات المستخدم الافتراضية (للاختبار)
        self.username_input.setText("admin")
        self.password_input.setText("admin123")

        # ربط Enter بزر تسجيل الدخول
        self.username_input.returnPressed.connect(self.login_button.click)
        self.password_input.returnPressed.connect(self.login_button.click)

        # إضافة مسافة مرنة
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # النسخة
        version_label = QLabel("v3.0")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #999; font-size: 10px;")
        main_layout.addWidget(version_label)

        self.setLayout(main_layout)

    def _on_login_clicked(self):
        """معالجة زر تسجيل الدخول"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("الرجاء إدخال اسم المستخدم وكلمة المرور"))
            return

        try:
            # البحث عن المستخدم
            cursor = db_manager.execute_query(
                """SELECT * FROM users
                   WHERE username = ? AND is_active = 1""",
                (username,)
            )
            user = cursor.fetchone()

            if not user:
                QMessageBox.warning(self, self.tr("خطأ"), self.tr("اسم المستخدم غير صحيح"))
                return

            # التحقق من كلمة المرور (في الوقت الحالي بدون تشفير)
            if user['password'] != password:
                QMessageBox.warning(self, self.tr("خطأ"), self.tr("كلمة المرور غير صحيحة"))
                return

            # تسجيل الدخول ناجح
            self.user_data = {
                'id': user['id'],
                'username': user['username'],
                'display_name': user['display_name'],
                'role': user['role']
            }

            # تحديث آخر تسجيل دخول
            db_manager.execute_query(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (user['id'],)
            )
            db_manager.commit()

            # إرسال إشعار تليجرام
            try:
                from src.utils.telegram import get_telegram_manager
                from datetime import datetime
                telegram = get_telegram_manager()
                telegram.send_login_alert({
                    'username': user['username'],
                    'display_name': user['display_name'],
                    'role': user['role'],
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M')
                })
            except Exception as e:
                # لا نوقف الدخول بسبب فشل التليجرام
                print(f"Failed to send telegram login alert: {e}")

            # قبول الحوار
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, self.tr("خطأ"), self.tr(f"حدث خطأ أثناء تسجيل الدخول:\n{str(e)}"))
