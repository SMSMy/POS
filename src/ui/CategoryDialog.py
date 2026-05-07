"""
نافذة إضافة/تعديل فئة
Category Dialog
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox,
    QPushButton, QHBoxLayout, QMessageBox, QFileDialog, QLabel,
    QColorDialog, QFrame
)
from PyQt5.QtGui import QFont, QPixmap, QColor
from PyQt5.QtCore import Qt
from database import db_manager
from loguru import logger
import os


class CategoryDialog(QDialog):
    # صيغ الصور المدعومة
    SUPPORTED_IMAGES = "الصور (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;كل الملفات (*.*)"

    def __init__(self, parent=None, category_data: dict = None):
        super().__init__(parent)
        self.category_data = category_data  # للتعديل
        self.selected_image_path = ""
        self.selected_color = "#3498db"

        self.setWindowTitle(
            self.tr("تعديل فئة") if category_data else self.tr("إضافة فئة")
        )
        self.setFixedSize(450, 450)
        self._setup_ui()

        # إذا كانت بيانات موجودة، املأ الحقول
        if self.category_data:
            self._fill_data()

    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QFormLayout()
        form.setSpacing(10)

        # الاسم بالعربية
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(self.tr("مطلوب"))
        self.name_input.setMinimumHeight(40)
        form.addRow(self.tr("الاسم بالعربية:"), self.name_input)

        # الاسم بالإنجليزية
        self.name_en_input = QLineEdit()
        self.name_en_input.setPlaceholderText(self.tr("اختياري - للعرض عند تبديل اللغة"))
        self.name_en_input.setMinimumHeight(40)
        form.addRow(self.tr("الاسم بالإنجليزية:"), self.name_en_input)

        # ═══════════════════════════════════════════════════════════
        # اختيار اللون
        # ═══════════════════════════════════════════════════════════
        color_layout = QHBoxLayout()

        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText(self.tr("#3498db"))
        self.color_input.setMinimumHeight(40)
        self.color_input.textChanged.connect(self._update_color_preview)
        color_layout.addWidget(self.color_input, 1)

        self.color_preview = QFrame()
        self.color_preview.setFixedSize(40, 40)
        self.color_preview.setStyleSheet("background-color: #3498db; border: 2px solid #2c3e50; border-radius: 4px;")
        color_layout.addWidget(self.color_preview)

        color_btn = QPushButton("🎨")
        color_btn.setFixedSize(40, 40)
        color_btn.setFont(QFont("Arial", 16))
        color_btn.setToolTip(self.tr("اختيار لون"))
        color_btn.clicked.connect(self._pick_color)
        color_layout.addWidget(color_btn)

        form.addRow(self.tr("اللون:"), color_layout)

        # ═══════════════════════════════════════════════════════════
        # اختيار الصورة
        # ═══════════════════════════════════════════════════════════
        image_layout = QVBoxLayout()

        # معاينة الصورة
        self.image_preview = QLabel()
        self.image_preview.setFixedSize(100, 100)
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setStyleSheet("""
            QLabel {
                background-color: #ecf0f1;
                border: 2px dashed #bdc3c7;
                border-radius: 8px;
            }
        """)
        self.image_preview.setText("📷\nلا توجد صورة")

        # أزرار الصورة
        image_buttons = QHBoxLayout()

        select_image_btn = QPushButton("📁 اختيار صورة")
        select_image_btn.setMinimumHeight(35)
        select_image_btn.clicked.connect(self._pick_image)
        image_buttons.addWidget(select_image_btn)

        clear_image_btn = QPushButton("🗑️ إزالة")
        clear_image_btn.setMinimumHeight(35)
        clear_image_btn.clicked.connect(self._clear_image)
        image_buttons.addWidget(clear_image_btn)

        image_layout.addWidget(self.image_preview, alignment=Qt.AlignCenter)
        image_layout.addLayout(image_buttons)

        form.addRow(self.tr("الصورة:"), image_layout)

        # الترتيب
        self.order_spin = QSpinBox()
        self.order_spin.setRange(0, 100)
        self.order_spin.setMinimumHeight(40)
        form.addRow(self.tr("ترتيب العرض:"), self.order_spin)

        layout.addLayout(form)

        # الأزرار
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        cancel_btn = QPushButton(self.tr("❌ إلغاء"))
        cancel_btn.setMinimumHeight(45)
        cancel_btn.setFont(QFont("Arial", 12))
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton(self.tr("✅ حفظ"))
        save_btn.setMinimumHeight(45)
        save_btn.setFont(QFont("Arial", 12, QFont.Bold))
        save_btn.clicked.connect(self._save_category)
        buttons_layout.addWidget(save_btn)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def _pick_color(self):
        """فتح نافذة اختيار اللون"""
        current_color = QColor(self.color_input.text() or "#3498db")
        color = QColorDialog.getColor(current_color, self, self.tr("اختيار لون"))
        if color.isValid():
            self.color_input.setText(color.name())
            self.selected_color = color.name()
            self._update_color_preview()

    def _update_color_preview(self):
        """تحديث معاينة اللون"""
        color = self.color_input.text()
        if color and QColor(color).isValid():
            self.color_preview.setStyleSheet(f"background-color: {color}; border: 2px solid #2c3e50; border-radius: 4px;")
            self.selected_color = color

    def _pick_image(self):
        """فتح نافذة اختيار الصورة"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("اختيار صورة"),
            "",
            self.SUPPORTED_IMAGES
        )
        if file_path:
            self.selected_image_path = file_path
            self._show_image_preview(file_path)

    def _show_image_preview(self, path):
        """عرض معاينة الصورة"""
        if os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_preview.setPixmap(scaled)
                self.image_preview.setStyleSheet("""
                    QLabel {
                        background-color: #ffffff;
                        border: 2px solid #27ae60;
                        border-radius: 8px;
                    }
                """)

    def _clear_image(self):
        """إزالة الصورة المختارة"""
        self.selected_image_path = ""
        self.image_preview.setPixmap(QPixmap())
        self.image_preview.setText("📷\nلا توجد صورة")
        self.image_preview.setStyleSheet("""
            QLabel {
                background-color: #ecf0f1;
                border: 2px dashed #bdc3c7;
                border-radius: 8px;
            }
        """)

    def _fill_data(self):
        """ملء الحقول بالبيانات الموجودة"""
        self.name_input.setText(self.category_data['name'])

        # الاسم الإنجليزي
        try:
            name_en = self.category_data.get('name_en', '') or self.category_data['name_en']
            if name_en and name_en != self.category_data['name']:
                self.name_en_input.setText(name_en)
        except (KeyError, TypeError):
            pass

        self.color_input.setText(self.category_data.get('color', ''))
        self.order_spin.setValue(self.category_data.get('display_order', 0))

        # تحميل الصورة إذا موجودة
        icon_path = self.category_data.get('icon', '')
        if icon_path and os.path.exists(icon_path):
            self.selected_image_path = icon_path
            self._show_image_preview(icon_path)

        self._update_color_preview()

    def _save_category(self):
        """حفظ الفئة"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("الاسم مطلوب"))
            return

        try:
            color = self.color_input.text().strip() or "#3498db"
            icon = self.selected_image_path
            name_en = self.name_en_input.text().strip() or name  # الاسم العربي كافتراضي

            if self.category_data:
                # تحديث
                db_manager.execute_query(
                    "UPDATE categories SET name = ?, name_en = ?, color = ?, icon = ?, display_order = ? WHERE id = ?",
                    (name, name_en, color, icon, self.order_spin.value(), self.category_data['id'])
                )
            else:
                # إضافة
                db_manager.execute_query(
                    "INSERT INTO categories (name, name_en, color, icon, display_order, is_active) VALUES (?, ?, ?, ?, ?, 1)",
                    (name, name_en, color, icon, self.order_spin.value())
                )

            db_manager.commit()
            self.accept()

        except Exception as e:
            db_manager.rollback()
            logger.error(f"خطأ في حفظ الفئة: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), str(e))
