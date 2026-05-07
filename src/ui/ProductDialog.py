"""
نافذة إضافة/تعديل منتج
Product Dialog
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QDoubleSpinBox, QSpinBox, QPushButton, QHBoxLayout,
    QMessageBox, QCheckBox, QFileDialog, QLabel, QColorDialog, QFrame,
    QScrollArea, QWidget
)
from PyQt5.QtGui import QFont, QPixmap, QColor
from PyQt5.QtCore import Qt
from database import db_manager
from loguru import logger
import os


class ProductDialog(QDialog):
    """نافذة إضافة/تعديل منتج"""

    # صيغ الصور المدعومة
    SUPPORTED_IMAGES = "الصور (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;كل الملفات (*.*)"

    def __init__(self, parent=None, product_id: int = None):
        super().__init__(parent)
        self.product_id = product_id  # Use product_id instead of barcode for lookup
        self.product_data = None
        self.selected_image_path = ""
        self.selected_color = ""
        self._setup_ui()

        if product_id:
            self._load_product()

    def _setup_ui(self):
        """إعداد الواجهة"""
        self.setWindowTitle(self.tr("إضافة منتج" if not self.product_id else "تعديل منتج"))
        self.setFixedSize(520, 700)

        # ScrollArea للمحتوى
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        form = QFormLayout()
        form.setSpacing(8)

        # الحقول
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText(self.tr("اختياري"))
        self.barcode_input.setMinimumHeight(40)
        form.addRow(self.tr("الباركود:"), self.barcode_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(self.tr("مطلوب"))
        self.name_input.setMinimumHeight(40)
        form.addRow(self.tr("الاسم بالعربية:"), self.name_input)

        self.name_en_input = QLineEdit()
        self.name_en_input.setPlaceholderText(self.tr("اختياري - إذا تُرك فارغاً يستخدم الاسم العربي"))
        self.name_en_input.setMinimumHeight(40)
        form.addRow(self.tr("الاسم بالإنجليزية:"), self.name_en_input)

        self.category_combo = QComboBox()
        self.category_combo.setMinimumHeight(40)
        self._load_categories()
        form.addRow(self.tr("الفئة:"), self.category_combo)

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

        # ═══════════════════════════════════════════════════════════
        # اختيار اللون
        # ═══════════════════════════════════════════════════════════
        color_layout = QHBoxLayout()

        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText(self.tr("اختياري - مثال: #e74c3c"))
        self.color_input.setMinimumHeight(40)
        self.color_input.textChanged.connect(self._update_color_preview)
        color_layout.addWidget(self.color_input, 1)

        self.color_preview = QFrame()
        self.color_preview.setFixedSize(40, 40)
        self.color_preview.setStyleSheet("background-color: #ecf0f1; border: 2px solid #bdc3c7; border-radius: 4px;")
        color_layout.addWidget(self.color_preview)

        color_btn = QPushButton("🎨")
        color_btn.setFixedSize(40, 40)
        color_btn.setFont(QFont("Arial", 16))
        color_btn.setToolTip(self.tr("اختيار لون"))
        color_btn.clicked.connect(self._pick_color)
        color_layout.addWidget(color_btn)

        form.addRow(self.tr("اللون:"), color_layout)

        # ═══════════════════════════════════════════════════════════
        # الأسعار والكميات
        # ═══════════════════════════════════════════════════════════
        self.cost_price_spin = QDoubleSpinBox()
        self.cost_price_spin.setRange(0, 100000)
        self.cost_price_spin.setDecimals(2)
        self.cost_price_spin.setSuffix(" " + self.tr("ريال"))
        self.cost_price_spin.setMinimumHeight(40)
        form.addRow(self.tr("سعر التكلفة:"), self.cost_price_spin)

        self.selling_price_spin = QDoubleSpinBox()
        self.selling_price_spin.setRange(0, 100000)
        self.selling_price_spin.setDecimals(2)
        self.selling_price_spin.setSuffix(" " + self.tr("ريال"))
        self.selling_price_spin.setMinimumHeight(40)
        form.addRow(self.tr("سعر البيع:"), self.selling_price_spin)

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(0, 100000)
        self.quantity_spin.setMinimumHeight(40)
        form.addRow(self.tr("الكمية الحالية:"), self.quantity_spin)

        self.min_alert_spin = QSpinBox()
        self.min_alert_spin.setRange(0, 1000)
        self.min_alert_spin.setValue(10)
        self.min_alert_spin.setMinimumHeight(40)
        form.addRow(self.tr("الحد الأدنى للتنبيه:"), self.min_alert_spin)

        self.tax_spin = QDoubleSpinBox()
        self.tax_spin.setRange(0, 100)
        self.tax_spin.setDecimals(0)
        self.tax_spin.setValue(15)
        self.tax_spin.setSuffix("%")
        self.tax_spin.setMinimumHeight(40)
        form.addRow(self.tr("نسبة الضريبة:"), self.tax_spin)

        # ترتيب العرض
        self.display_order_spin = QSpinBox()
        self.display_order_spin.setRange(0, 9999)
        self.display_order_spin.setValue(0)
        self.display_order_spin.setMinimumHeight(40)
        self.display_order_spin.setToolTip(self.tr("رقم أصغر = يظهر أولاً"))
        form.addRow(self.tr("ترتيب العرض:"), self.display_order_spin)

        self.is_active_check = QCheckBox(self.tr("نشط"))
        self.is_active_check.setChecked(True)
        form.addRow(self.tr("الحالة:"), self.is_active_check)

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
        save_btn.clicked.connect(self._on_save_clicked)
        buttons_layout.addWidget(save_btn)

        layout.addLayout(buttons_layout)

        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

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
        else:
            self.color_preview.setStyleSheet("background-color: #ecf0f1; border: 2px solid #bdc3c7; border-radius: 4px;")

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

    def _load_categories(self):
        """تحميل الفئات"""
        try:
            cursor = db_manager.execute_query(
                "SELECT id, name FROM categories WHERE is_active = 1 ORDER BY name"
            )
            categories = cursor.fetchall()

            for cat in categories:
                self.category_combo.addItem(cat['name'], cat['id'])
        except Exception as e:
            logger.error(f"خطأ في تحميل الفئات: {e}")

    def _load_product(self):
        """تحميل بيانات المنتج للتعديل"""
        try:
            cursor = db_manager.execute_query(
                "SELECT * FROM products WHERE id = ?", (self.product_id,)
            )
            product = cursor.fetchone()

            if not product:
                return

            self.product_data = product
            self.barcode_input.setText(product['barcode'] or '')
            self.name_input.setText(product['name'])

            # تحميل الاسم الإنجليزي
            try:
                name_en = product['name_en']
                if name_en:
                    self.name_en_input.setText(name_en)
            except (KeyError, IndexError):
                pass

            # اختيار الفئة
            index = self.category_combo.findData(product['category_id'])
            if index >= 0:
                self.category_combo.setCurrentIndex(index)

            self.cost_price_spin.setValue(product['cost_price'])
            self.selling_price_spin.setValue(product['selling_price'])
            self.quantity_spin.setValue(int(product['quantity']))
            self.min_alert_spin.setValue(int(product['min_alert_level']))
            self.tax_spin.setValue(product['tax_rate'] * 100)
            self.is_active_check.setChecked(product['is_active'] == 1)

            # تحميل اللون
            try:
                color = product['color']
                if color:
                    self.color_input.setText(color)
                    self._update_color_preview()
            except (KeyError, IndexError):
                pass

            # تحميل الصورة
            try:
                image_path = product['image_path']
                if image_path and os.path.exists(image_path):
                    self.selected_image_path = image_path
                    self._show_image_preview(image_path)
            except (KeyError, IndexError):
                pass

            # تحميل ترتيب العرض
            try:
                display_order = product['display_order']
                if display_order is not None:
                    self.display_order_spin.setValue(int(display_order))
            except (KeyError, IndexError):
                pass

        except Exception as e:
            logger.error(f"خطأ في تحميل المنتج: {e}")

    def _on_save_clicked(self):
        """حفظ المنتج"""
        # التحقق من البيانات
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("اسم المنتج مطلوب"))
            return

        category_id = self.category_combo.currentData()
        if not category_id:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("الفئة مطلوبة"))
            return

        try:
            barcode = self.barcode_input.text().strip() or None
            name_en = self.name_en_input.text().strip() or name  # استخدام الاسم العربي كافتراضي
            cost_price = self.cost_price_spin.value()
            selling_price = self.selling_price_spin.value()
            quantity = self.quantity_spin.value()
            min_alert = self.min_alert_spin.value()
            tax_rate = self.tax_spin.value() / 100
            is_active = 1 if self.is_active_check.isChecked() else 0
            color = self.color_input.text().strip() or None
            image_path = self.selected_image_path or None

            # التحقق من وجود عمود image_path
            self._ensure_image_column()

            # التحقق من تغير السعر للإشعار
            try:
                if self.product_id:
                    cursor = db_manager.execute_query("SELECT selling_price, name FROM products WHERE id = ?", (self.product_id,))
                    old_product = cursor.fetchone()
                    if old_product and float(old_product['selling_price']) != float(selling_price):
                        # إرسال إشعار تليجرام
                        try:
                            from src.utils.telegram import get_telegram_manager
                            telegram = get_telegram_manager()
                            telegram.send_price_change_alert(
                                {'name': old_product['name']},
                                float(old_product['selling_price']),
                                float(selling_price),
                                self.parent().user_data.get('display_name', '') if hasattr(self.parent(), 'user_data') else 'Admin'
                            )
                        except Exception as e:
                            logger.warning(f"Failed to send price change alert: {e}")
            except Exception as e:
                logger.error(f"Error checking price change: {e}")

            if self.product_id:
                # تعديل - use product_id for lookup
                db_manager.execute_query(
                    """UPDATE products SET
                       barcode = ?, name = ?, name_en = ?, category_id = ?, cost_price = ?,
                       selling_price = ?, quantity = ?, min_alert_level = ?,
                       tax_rate = ?, is_active = ?, color = ?, image_path = ?, display_order = ?
                       WHERE id = ?""",
                    (barcode, name, name_en, category_id, cost_price, selling_price, quantity,
                     min_alert, tax_rate, is_active, color, image_path, self.display_order_spin.value(), self.product_id)
                )
            else:
                # إضافة
                db_manager.execute_query(
                    """INSERT INTO products (
                        barcode, name, name_en, category_id, cost_price, selling_price,
                        quantity, min_alert_level, tax_rate, is_active, color, image_path, display_order
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (barcode, name, name_en, category_id, cost_price, selling_price,
                     quantity, min_alert, tax_rate, is_active, color, image_path, self.display_order_spin.value())
                )

            db_manager.commit()
            self.accept()

        except Exception as e:
            logger.error(f"خطأ في حفظ المنتج: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr("حدث خطأ أثناء الحفظ"))

    def _ensure_image_column(self):
        """التأكد من وجود عمود image_path في جدول المنتجات"""
        try:
            # محاولة إضافة العمود إذا لم يكن موجوداً
            db_manager.execute_query(
                "ALTER TABLE products ADD COLUMN image_path TEXT"
            )
            db_manager.commit()
        except:
            # العمود موجود بالفعل، تجاهل الخطأ
            pass
