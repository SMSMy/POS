"""
شاشة نقطة البيع الرئيسية
POS Screen - Touch-First Design with Auto-Responsive Layout
تصميم متجاوب يتكيف تلقائياً مع دقة الشاشة
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QGroupBox, QSpinBox, QDialog,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView,
    QMessageBox, QInputDialog, QSpacerItem, QSizePolicy, QScroller,
    QApplication, QDesktopWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QByteArray, QBuffer, QIODevice
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPalette, QBrush
from loguru import logger
from datetime import datetime
import os

from database import db_manager, get_current_shift, get_setting
from src.ui.payment_dialog import PaymentDialog
from src.utils.printer import printer_manager
from src.utils.zatca import generate_qr_code

# استيراد مكتبة Rust للحسابات السريعة (مع fallback للـ Python)
try:
    from pos_calc import calculate_cart_totals, calculate_ingredient_deductions, search_products
    USE_RUST_CALC = True
    logger.info("تم تحميل مكتبة pos_calc (Rust) بنجاح - POSScreen")
except ImportError:
    USE_RUST_CALC = False
    logger.info("مكتبة pos_calc غير متوفرة، سيتم استخدام Python - POSScreen")


class POSScreen(QWidget):
    """شاشة نقطة البيع - تصميم متجاوب"""

    cart_updated = pyqtSignal()

    def __init__(self, user_data: dict, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.current_shift = None
        self.cart = []  # سلة المشتريات
        self.selected_category = None

        self.printer = printer_manager

        # 🎯 كشف تلقائي لدقة الشاشة وإعداد التصميم المتجاوب
        self._detect_screen_and_setup_responsive()

        self._setup_ui()
        self._load_categories()
        self._update_cart_display()
        self._check_shift()

        # مؤقت لتحديث حالة الوردية
        self.shift_timer = QTimer()
        self.shift_timer.timeout.connect(self._check_shift)
        self.shift_timer.start(5000)  # كل 5 ثواني

    def _detect_screen_and_setup_responsive(self):
        """كشف تلقائي لدقة الشاشة وإعداد المتغيرات المتجاوبة"""
        # الحصول على دقة الشاشة
        try:
            screen = QApplication.primaryScreen()
            if screen:
                geometry = screen.availableGeometry()
                self.screen_width = geometry.width()
                self.screen_height = geometry.height()
            else:
                desktop = QDesktopWidget()
                self.screen_width = desktop.availableGeometry().width()
                self.screen_height = desktop.availableGeometry().height()
        except:
            self.screen_width = 1366
            self.screen_height = 768

        logger.info(f"📺 دقة الشاشة المكتشفة: {self.screen_width}×{self.screen_height}")

        # ✅ إعدادات متجاوبة حسب عرض الشاشة
        if self.screen_width <= 800:
            # شاشة صغيرة جداً (768px)
            self.responsive = {
                'products_columns': 3,
                'left_min_width': 350,
                'right_min_width': 250,
                'spacing': 4,
                'margins': 4,
                'font_title': 10,
                'font_normal': 9,
                'font_small': 8,
                'button_height': 40,
                'category_height': 45,
                'product_card_min': (85, 70),
                'product_card_max': (110, 90),
            }
        elif self.screen_width <= 1024:
            # شاشة صغيرة (1024px)
            self.responsive = {
                'products_columns': 4,
                'left_min_width': 450,
                'right_min_width': 300,
                'spacing': 5,
                'margins': 5,
                'font_title': 11,
                'font_normal': 10,
                'font_small': 9,
                'button_height': 45,
                'category_height': 50,
                'product_card_min': (90, 75),
                'product_card_max': (120, 95),
            }
        elif self.screen_width <= 1366:
            # شاشة متوسطة (1366px)
            self.responsive = {
                'products_columns': 5,
                'left_min_width': 550,
                'right_min_width': 350,
                'spacing': 6,
                'margins': 6,
                'font_title': 12,
                'font_normal': 10,
                'font_small': 9,
                'button_height': 50,
                'category_height': 55,
                'product_card_min': (95, 78),
                'product_card_max': (125, 98),
            }
        else:
            # شاشة كبيرة (1920px+)
            self.responsive = {
                'products_columns': 6,
                'left_min_width': 650,
                'right_min_width': 400,
                'spacing': 8,
                'margins': 8,
                'font_title': 14,
                'font_normal': 11,
                'font_small': 10,
                'button_height': 55,
                'category_height': 60,
                'product_card_min': (100, 80),
                'product_card_max': (130, 100),
            }

        logger.info(f"📐 إعدادات التصميم: {self.responsive['products_columns']} أعمدة")

    def _setup_ui(self):
        """إعداد واجهة المستخدم - Touch-First Design المتجاوب"""
        # تثبيت اتجاه التخطيط (المنتجات يمين، السلة يسار) - ثابت في كلتا اللغتين
        self.setLayoutDirection(Qt.RightToLeft)

        outer_layout = QVBoxLayout()
        outer_layout.setSpacing(0)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # تنبيه عدم وجود وردية
        self.no_shift_alert = QFrame()
        self.no_shift_alert.setStyleSheet("""
            QFrame {
                background-color: #e74c3c;
                border: none;
                padding: 8px;
            }
        """)
        alert_layout = QHBoxLayout(self.no_shift_alert)
        alert_layout.setContentsMargins(10, 5, 10, 5)

        alert_icon = QLabel("⚠️")
        alert_icon.setFont(QFont("Arial", self.responsive['font_title']))
        alert_layout.addWidget(alert_icon)

        alert_text = QLabel(self.tr("لا توجد وردية مفتوحة! يجب فتح وردية أولاً لإضافة منتجات للسلة."))
        alert_text.setFont(QFont("Arial", self.responsive['font_small'], QFont.Bold))
        alert_text.setStyleSheet("color: white;")
        alert_layout.addWidget(alert_text)

        alert_layout.addStretch()

        open_shift_hint = QLabel(self.tr("اذهب إلى القائمة ← الورديات ← فتح وردية جديدة"))
        open_shift_hint.setFont(QFont("Arial", self.responsive['font_small']))
        open_shift_hint.setStyleSheet("color: white;")
        alert_layout.addWidget(open_shift_hint)

        outer_layout.addWidget(self.no_shift_alert)

        # منطقة المحتوى الرئيسية - استخدام الإعدادات المتجاوبة
        main_layout = QHBoxLayout()
        main_layout.setSpacing(self.responsive['spacing'])
        main_layout.setContentsMargins(
            self.responsive['margins'],
            self.responsive['margins'],
            self.responsive['margins'],
            self.responsive['margins']
        )

        # العمود الأيسر: الفئات والمنتجات
        left_panel = self._create_left_panel()
        left_panel.setMinimumWidth(self.responsive['left_min_width'])
        main_layout.addWidget(left_panel, 2)

        # العمود الأيمن: السلة والإجمالي
        right_panel = self._create_right_panel()
        right_panel.setMinimumWidth(self.responsive['right_min_width'])
        main_layout.addWidget(right_panel, 1)

        outer_layout.addLayout(main_layout)
        self.setLayout(outer_layout)

    def _create_left_panel(self) -> QWidget:
        """إنشاء اللوحة اليسرى (الفئات والمنتجات) - متجاوبة"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(self.responsive['spacing'])
        layout.setContentsMargins(
            self.responsive['margins'],
            self.responsive['margins'],
            self.responsive['margins'],
            self.responsive['margins']
        )

        # منطقة الفئات
        categories_group = QGroupBox(self.tr("الفئات"))
        categories_group.setFont(QFont("Arial", self.responsive['font_normal'], QFont.Bold))
        categories_layout = QVBoxLayout()
        categories_layout.setContentsMargins(3, 3, 3, 3)

        self.categories_container = QWidget()
        self.categories_layout = QHBoxLayout(self.categories_container)
        self.categories_layout.setSpacing(3)
        self.categories_layout.setContentsMargins(0, 0, 0, 0)

        # زر عرض الكل - متجاوب
        self.all_categories_btn = QPushButton(self.tr("الكل"))
        self.all_categories_btn.setMinimumHeight(self.responsive['category_height'])
        self.all_categories_btn.setFont(QFont("Arial", self.responsive['font_small'], QFont.Bold))
        self.all_categories_btn.setCheckable(True)
        self.all_categories_btn.setChecked(True)
        self.all_categories_btn.clicked.connect(lambda: self._select_category(None))
        self.categories_layout.addWidget(self.all_categories_btn)

        categories_layout.addWidget(self.categories_container)
        categories_group.setLayout(categories_layout)
        layout.addWidget(categories_group, 1)

        # منطقة المنتجات - متجاوبة
        products_group = QGroupBox(self.tr("المنتجات"))
        products_group.setFont(QFont("Arial", self.responsive['font_normal'], QFont.Bold))
        products_layout = QVBoxLayout()
        products_layout.setContentsMargins(3, 3, 3, 3)

        # شريط أدوات ترتيب المنتجات
        order_toolbar = QHBoxLayout()

        # زر قفل/فتح الترتيب - متجاوب
        self.order_lock_btn = QPushButton(self.tr("🔒 الترتيب مقفل"))
        self.order_lock_btn.setMinimumHeight(self.responsive['button_height'] - 10)
        self.order_lock_btn.setFont(QFont("Arial", self.responsive['font_small']))
        self.order_lock_btn.setCheckable(True)
        self.order_lock_btn.setChecked(True)  # مقفل افتراضياً
        self.order_lock_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 3px 10px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #27ae60;
            }
        """)
        self.order_lock_btn.clicked.connect(self._toggle_order_mode)
        order_toolbar.addWidget(self.order_lock_btn)

        # زر حفظ الترتيب (مخفي افتراضياً) - متجاوب
        self.save_order_btn = QPushButton(self.tr("💾 حفظ الترتيب"))
        self.save_order_btn.setMinimumHeight(self.responsive['button_height'] - 10)
        self.save_order_btn.setFont(QFont("Arial", self.responsive['font_small']))
        self.save_order_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 3px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.save_order_btn.clicked.connect(self._save_products_order)
        self.save_order_btn.hide()  # مخفي حتى يتم فتح القفل
        order_toolbar.addWidget(self.save_order_btn)

        order_toolbar.addStretch()
        products_layout.addLayout(order_toolbar)

        # منطقة تمرير للمنتجات
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.products_container = QWidget()
        self.products_grid = QGridLayout(self.products_container)
        self.products_grid.setSpacing(self.responsive['spacing'] - 2)
        self.products_grid.setContentsMargins(3, 3, 3, 3)

        scroll.setWidget(self.products_container)

        # تفعيل السحب باللمس للمنتجات
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)

        # متغير لتتبع حالة وضع الترتيب
        self.order_mode_active = False

        products_layout.addWidget(scroll)
        products_group.setLayout(products_layout)
        layout.addWidget(products_group, 4)

        panel.setLayout(layout)
        return panel

    def _create_right_panel(self) -> QWidget:
        """إنشاء اللوحة اليمنى (السلة والإجمالي)"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # شريط علوي: عنوان السلة + زر اللغة
        header_row = QHBoxLayout()

        # عنوان السلة
        self.cart_header_label = QLabel(self.tr("🛒 سلة المشتريات"))
        self.cart_header_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.cart_header_label.setAlignment(Qt.AlignCenter)
        header_row.addWidget(self.cart_header_label, 1)

        # زر تبديل اللغة
        from src.utils.language_manager import language_manager
        self.lang_btn = QPushButton("🌐 EN" if language_manager.current_language == 'ar' else "🌐 عربي")
        self.lang_btn.setFixedSize(80, 40)
        self.lang_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.lang_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
            QPushButton:pressed {
                background-color: #7d3c98;
            }
        """)
        self.lang_btn.setToolTip(self.tr("تبديل اللغة"))
        self.lang_btn.clicked.connect(self._toggle_language)
        header_row.addWidget(self.lang_btn)

        layout.addLayout(header_row)


        # جدول السلة
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(4)
        self.cart_table.setHorizontalHeaderLabels([
            self.tr("المنتج"),
            self.tr("السعر"),
            self.tr("الكمية"),
            self.tr("الإجمالي")
        ])
        self.cart_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cart_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.cart_table.setMinimumHeight(300)

        # تكوين العرض
        header = self.cart_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.cart_table.itemDoubleClicked.connect(self._edit_cart_item)
        layout.addWidget(self.cart_table, 2)

        # أزرار التحكم في السلة
        cart_controls = QHBoxLayout()

        self.clear_cart_btn = QPushButton(self.tr("🗑️ إفراغ"))
        self.clear_cart_btn.setMinimumHeight(45)
        self.clear_cart_btn.clicked.connect(self._clear_cart)
        cart_controls.addWidget(self.clear_cart_btn)

        self.remove_item_btn = QPushButton(self.tr("❌ حذف"))
        self.remove_item_btn.setMinimumHeight(45)
        self.remove_item_btn.clicked.connect(self._remove_selected_item)
        cart_controls.addWidget(self.remove_item_btn)

        layout.addLayout(cart_controls)

        # تم إزالة معلومات الفاتورة (رقم الطاولة واسم العميل)
        # الاحتفاظ بالمتغيرات للتوافق مع الكود الحالي
        self.table_input = None
        self.customer_input = None

        # الإجمالي
        totals_frame = QFrame()
        totals_frame.setFrameShape(QFrame.Box)
        totals_frame.setStyleSheet("background-color: #f8f9fa;")
        totals_layout = QVBoxLayout()

        self.subtotal_label = QLabel(self.tr("المجموع: 0.00 ريال"))
        self.subtotal_label.setFont(QFont("Arial", 12))
        self.subtotal_label.setAlignment(Qt.AlignRight)
        totals_layout.addWidget(self.subtotal_label)

        self.tax_label = QLabel(self.tr("الضريبة (15%): 0.00 ريال"))
        self.tax_label.setFont(QFont("Arial", 12))
        self.tax_label.setAlignment(Qt.AlignRight)
        totals_layout.addWidget(self.tax_label)

        self.total_label = QLabel(self.tr("الإجمالي: 0.00 ريال"))
        self.total_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.total_label.setAlignment(Qt.AlignRight)
        self.total_label.setStyleSheet("color: #e74c3c;")
        totals_layout.addWidget(self.total_label)

        totals_frame.setLayout(totals_layout)
        layout.addWidget(totals_frame)

        # زر الدفع
        self.checkout_btn = QPushButton(self.tr("💳 إتمام الدفع"))
        self.checkout_btn.setMinimumHeight(70)
        self.checkout_btn.setFont(QFont("Arial", 16, QFont.Bold))
        self.checkout_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.checkout_btn.clicked.connect(self._on_checkout)
        layout.addWidget(self.checkout_btn)

        panel.setLayout(layout)
        return panel

    def _load_categories(self):
        """تحميل الفئات"""
        try:
            # مسح أزرار الفئات السابقة (ما عدا زر 'الكل')
            while self.categories_layout.count() > 1:
                item = self.categories_layout.takeAt(1)
                if item.widget():
                    item.widget().deleteLater()

            cursor = db_manager.execute_query(
                "SELECT * FROM categories WHERE is_active = 1 ORDER BY display_order"
            )
            categories = cursor.fetchall()

            # الحصول على اللغة الحالية
            try:
                from src.utils.language_manager import language_manager
                current_lang = language_manager.current_language
            except:
                current_lang = 'ar'

            # إضافة أزرار الفئات
            for i, category in enumerate(categories):
                # اختيار الاسم حسب اللغة
                if current_lang == 'en':
                    try:
                        cat_name = category['name_en'] or category['name']
                    except (KeyError, IndexError):
                        cat_name = category['name']
                else:
                    cat_name = category['name']

                btn = QPushButton(cat_name)
                btn.setMinimumHeight(60)
                btn.setFont(QFont("Arial", 11, QFont.Bold))
                btn.setCheckable(True)
                btn.setProperty('category_id', category['id'])

                # تحديد اللون والصورة
                color = category['color'] if category['color'] else '#3498db'
                icon_path = None
                try:
                    icon_path = category['icon']
                except (KeyError, IndexError):
                    pass

                # إذا كانت هناك صورة
                if icon_path and os.path.exists(icon_path):
                    # تحميل الصورة وتصغيرها
                    pixmap = QPixmap(icon_path)
                    if not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(50, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        btn.setIcon(QIcon(scaled_pixmap))
                        btn.setIconSize(scaled_pixmap.size())
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: rgba(0, 0, 0, 0.6);
                            color: white;
                            border: 2px solid {color};
                            border-radius: 8px;
                            padding: 5px;
                            font-weight: bold;
                        }}
                        QPushButton:checked {{
                            border: 3px solid #f39c12;
                            background-color: rgba(243, 156, 18, 0.7);
                        }}
                        QPushButton:hover {{
                            background-color: rgba(0, 0, 0, 0.4);
                        }}
                    """)
                else:
                    # بدون صورة - استخدم اللون فقط
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {color};
                            color: white;
                            border: none;
                            border-radius: 8px;
                            padding: 5px;
                            font-weight: bold;
                        }}
                        QPushButton:checked {{
                            border: 3px solid #f39c12;
                        }}
                        QPushButton:hover {{
                            opacity: 0.8;
                        }}
                    """)

                btn.clicked.connect(lambda _, cat_id=category['id']: self._select_category(cat_id))
                self.categories_layout.addWidget(btn)

            self._load_products()

        except Exception as e:
            logger.error(f"خطأ في تحميل الفئات: {e}")

    def _load_products(self, category_id: int = None):
        """تحميل المنتجات باستخدام ProductButton المخصص - متجاوب"""
        try:
            # مسح الأزرار السابقة
            while self.products_grid.count():
                item = self.products_grid.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # استعلام المنتجات
            if category_id:
                query = "SELECT * FROM products WHERE category_id = ? AND is_active = 1 ORDER BY display_order, name"
                params = (category_id,)
            else:
                query = "SELECT * FROM products WHERE is_active = 1 ORDER BY display_order, name"
                params = ()
            cursor = db_manager.execute_query(query, params)
            products = cursor.fetchall()

            # عدد الأعمدة المتجاوب حسب دقة الشاشة
            columns = self.responsive['products_columns']

            # بناء الأزرار المخصصة
            from src.ui.product_button import ProductCard

            for idx, product in enumerate(products):
                # تحويل Row إلى dict
                product_dict = dict(product)

                # إنشاء بطاقة المنتج (الصورة + الاسم أسفلها) مع إعدادات متجاوبة
                card = ProductCard(product_dict, self, self.responsive)

                # ربط الأحداث
                card.clicked_with_data.connect(self._add_to_cart)
                card.quantity_changed.connect(self._change_cart_quantity)

                # تحديث عرض الكمية الحالية في السلة
                current_qty = 0
                for item in self.cart:
                    if item['product_id'] == product_dict['id']:
                        current_qty = int(item['quantity'])
                        break
                card.set_quantity(current_qty)

                # إضافة للشبكة - استخدام عدد الأعمدة المتجاوب
                self.products_grid.addWidget(card, idx // columns, idx % columns)

        except Exception as e:
            logger.error(f"خطأ في تحميل المنتجات: {e}")

    def _darken_color(self, hex_color: str, factor: float = 0.2) -> str:
        """تعتيم اللون"""
        try:
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            r = int(r * (1 - factor))
            g = int(g * (1 - factor))
            b = int(b * (1 - factor))
            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            return '#2980b9'

    def _toggle_order_mode(self):
        """تفعيل/إلغاء وضع تغيير الترتيب"""
        if self.order_lock_btn.isChecked():
            # الترتيب مقفل
            self.order_mode_active = False
            self.order_lock_btn.setText(self.tr("🔒 الترتيب مقفل"))
            self.save_order_btn.hide()
        else:
            # الترتيب مفتوح
            if self.selected_category is None:
                QMessageBox.warning(
                    self,
                    self.tr("تحذير"),
                    self.tr("يرجى اختيار تصنيف معين أولاً لترتيب منتجاته")
                )
                self.order_lock_btn.setChecked(True)
                return

            self.order_mode_active = True
            self.order_lock_btn.setText(self.tr("🔓 الترتيب مفتوح"))
            self.save_order_btn.show()
            QMessageBox.information(
                self,
                self.tr("معلومة"),
                self.tr("اضغط على المنتج ثم اضغط على المنتج الآخر لتبديل موقعهما.\nبعد الانتهاء، اضغط 'حفظ الترتيب'.")
            )
            # تحديث المنتجات لإظهار أرقام الترتيب
            self._load_products(self.selected_category)

    def _save_products_order(self):
        """حفظ ترتيب المنتجات في قاعدة البيانات"""
        try:
            from src.ui.product_button import ProductCard

            # جمع المنتجات بترتيبها الحالي
            products_order = []
            for i in range(self.products_grid.count()):
                widget = self.products_grid.itemAt(i).widget()
                if isinstance(widget, ProductCard):
                    products_order.append(widget.product['id'])

            # تحديث الترتيب في قاعدة البيانات
            for order, product_id in enumerate(products_order):
                db_manager.execute_query(
                    "UPDATE products SET display_order = ? WHERE id = ?",
                    (order, product_id)
                )

            db_manager.commit()

            # قفل الترتيب
            self.order_lock_btn.setChecked(True)
            self._toggle_order_mode()

            QMessageBox.information(
                self,
                self.tr("نجاح"),
                self.tr("تم حفظ ترتيب المنتجات بنجاح")
            )

        except Exception as e:
            logger.error(f"خطأ في حفظ ترتيب المنتجات: {e}")
            QMessageBox.critical(
                self,
                self.tr("خطأ"),
                self.tr("حدث خطأ أثناء حفظ الترتيب")
            )

    def _select_category(self, category_id: int):
        """اختيار فئة"""
        self.selected_category = category_id

        # تحديث أزرار الفئات
        for i in range(1, self.categories_layout.count()):
            btn = self.categories_layout.itemAt(i).widget()
            btn.setChecked(btn.property('category_id') == category_id)

        self.all_categories_btn.setChecked(category_id is None)

        # تحميل المنتجات
        self._load_products(category_id)

    def _add_to_cart(self, product: dict):
        """إضافة منتج للسلة أو تبديل الترتيب في وضع الترتيب"""

        # إذا كان وضع الترتيب مفعل، تعامل مع التبديل
        if hasattr(self, 'order_mode_active') and self.order_mode_active:
            self._handle_order_swap(product)
            return

        if not self.current_shift:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("يجب فتح وردية أولاً"))
            return

        # البحث عن المنتج في السلة
        for item in self.cart:
            if item['product_id'] == product['id']:
                item['quantity'] += 1
                item['line_total'] = item['quantity'] * item['unit_price']
                self._update_cart_display()
                return

        # إضافة منتج جديد
        cart_item = {
            'product_id': product['id'],
            'product_name': product['name'],
            'product_name_en': product.get('name_en', '') or product['name'],  # الاسم الإنجليزي للفاتورة
            'unit_price': product['selling_price'],
            'cost_price': product['cost_price'],
            'quantity': 1,
            'tax_rate': product['tax_rate'],
            'line_total': product['selling_price']
        }

        self.cart.append(cart_item)
        self._update_cart_display()

    def _handle_order_swap(self, product: dict):
        """التعامل مع تبديل ترتيب المنتجات"""
        from src.ui.product_button import ProductCard

        # إذا لم يكن هناك منتج أول محدد
        if not hasattr(self, '_swap_first_product') or self._swap_first_product is None:
            self._swap_first_product = product
            self._swap_first_widget = None
            # تمييز المنتج المحدد
            for i in range(self.products_grid.count()):
                widget = self.products_grid.itemAt(i).widget()
                if isinstance(widget, ProductCard) and widget.product['id'] == product['id']:
                    self._swap_first_widget = widget
                    widget.setStyleSheet(widget.styleSheet() + "border: 4px solid #e74c3c !important;")
                    break
            return

        # إذا كان نفس المنتج، إلغاء التحديد
        if self._swap_first_product['id'] == product['id']:
            # إزالة التمييز
            if hasattr(self, '_swap_first_widget') and self._swap_first_widget:
                self._swap_first_widget.setStyleSheet(self._swap_first_widget.styleSheet().replace("border: 4px solid #e74c3c !important;", ""))
            self._swap_first_product = None
            self._swap_first_widget = None
            return

        # تبديل المنتجين في الشبكة
        first_widget = None
        second_widget = None
        first_pos = None
        second_pos = None

        for i in range(self.products_grid.count()):
            widget = self.products_grid.itemAt(i).widget()
            if isinstance(widget, ProductCard):
                if widget.product['id'] == self._swap_first_product['id']:
                    first_widget = widget
                    first_pos = self.products_grid.getItemPosition(i)  # (row, col, rowspan, colspan)
                elif widget.product['id'] == product['id']:
                    second_widget = widget
                    second_pos = self.products_grid.getItemPosition(i)

        if first_widget and second_widget and first_pos and second_pos:
            # إزالة كلا الويدجت
            self.products_grid.removeWidget(first_widget)
            self.products_grid.removeWidget(second_widget)

            # إضافتهما بالعكس
            self.products_grid.addWidget(first_widget, second_pos[0], second_pos[1])
            self.products_grid.addWidget(second_widget, first_pos[0], first_pos[1])

            # إزالة التمييز من المنتج الأول
            first_widget.setStyleSheet(first_widget.styleSheet().replace("border: 4px solid #e74c3c !important;", ""))

        # إعادة تعيين المنتج الأول
        self._swap_first_product = None
        self._swap_first_widget = None

    def _change_cart_quantity(self, product: dict, delta: int):
        """تغيير كمية منتج في السلة عبر أزرار +/-"""
        if not self.current_shift:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("يجب فتح وردية أولاً"))
            return

        product_id = product['id']

        # البحث عن المنتج في السلة
        for i, item in enumerate(self.cart):
            if item['product_id'] == product_id:
                new_qty = item['quantity'] + delta
                if new_qty <= 0:
                    # إزالة المنتج من السلة
                    del self.cart[i]
                else:
                    item['quantity'] = new_qty
                    item['line_total'] = new_qty * item['unit_price']
                self._update_cart_display()
                self._update_product_card_quantities()
                return

        # المنتج غير موجود في السلة - إضافته إذا كان delta موجب
        if delta > 0:
            self._add_to_cart(product)
            self._update_product_card_quantities()

    def _update_product_card_quantities(self):
        """تحديث عرض الكميات على بطاقات المنتجات"""
        from src.ui.product_button import ProductCard
        for i in range(self.products_grid.count()):
            widget = self.products_grid.itemAt(i).widget()
            if isinstance(widget, ProductCard):
                product_id = widget.product['id']
                qty = 0
                for item in self.cart:
                    if item['product_id'] == product_id:
                        qty = int(item['quantity'])
                        break
                widget.set_quantity(qty)

    def _update_cart_display(self):
        """تحديث عرض السلة"""
        self.cart_table.setRowCount(len(self.cart))

        for i, item in enumerate(self.cart):
            # اسم المنتج
            name_item = QTableWidgetItem(item['product_name'])
            name_item.setTextAlignment(Qt.AlignRight)
            self.cart_table.setItem(i, 0, name_item)

            # السعر
            price_item = QTableWidgetItem(f"{item['unit_price']:.2f}")
            price_item.setTextAlignment(Qt.AlignCenter)
            self.cart_table.setItem(i, 1, price_item)

            # الكمية - widget مع أزرار +/-
            qty_widget = QWidget()
            qty_layout = QHBoxLayout(qty_widget)
            qty_layout.setContentsMargins(2, 2, 2, 2)
            qty_layout.setSpacing(2)

            # زر الطرح
            minus_btn = QPushButton("-")
            minus_btn.setFixedSize(28, 28)
            minus_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:pressed { background-color: #c0392b; }
            """)
            minus_btn.clicked.connect(lambda _, idx=i: self._cart_item_decrement(idx))
            qty_layout.addWidget(minus_btn)

            # عرض الكمية
            qty_label = QLabel(str(int(item['quantity'])))
            qty_label.setAlignment(Qt.AlignCenter)
            qty_label.setMinimumWidth(30)
            qty_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            qty_layout.addWidget(qty_label)

            # زر الإضافة
            plus_btn = QPushButton("+")
            plus_btn.setFixedSize(28, 28)
            plus_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:pressed { background-color: #1e8449; }
            """)
            plus_btn.clicked.connect(lambda _, idx=i: self._cart_item_increment(idx))
            qty_layout.addWidget(plus_btn)

            self.cart_table.setCellWidget(i, 2, qty_widget)

            # الإجمالي
            total_item = QTableWidgetItem(f"{item['line_total']:.2f}")
            total_item.setTextAlignment(Qt.AlignCenter)
            self.cart_table.setItem(i, 3, total_item)

        # حساب الإجماليات - استخدام Rust إن توفر
        tax_inclusive = get_setting('tax_inclusive', '1') == '1'

        if USE_RUST_CALC:
            # حساب سريع بـ Rust
            cart_list = [dict(item) for item in self.cart]
            totals = calculate_cart_totals(cart_list, tax_inclusive)
            subtotal = totals['subtotal']
            tax = totals['tax']
            total = totals['total']
        else:
            # الحساب بـ Python (fallback)
            if tax_inclusive:
                # الأسعار شاملة الضريبة - استخراج الضريبة من الإجمالي
                total = sum(item['line_total'] for item in self.cart)
                # حساب الضريبة لكل عنصر حسب نسبة الضريبة الخاصة به
                tax = sum(item['line_total'] - (item['line_total'] / (1 + item['tax_rate'])) for item in self.cart)
                subtotal = total - tax
            else:
                # الأسعار غير شاملة - إضافة الضريبة
                subtotal = sum(item['line_total'] for item in self.cart)
                tax = sum(item['line_total'] * item['tax_rate'] for item in self.cart)
                total = subtotal + tax

        # تحديث العرض
        self.subtotal_label.setText(f"{self.tr('الصافي')}: {subtotal:.2f} {self.tr('ريال')}")
        self.tax_label.setText(f"{self.tr('الضريبة')}: {tax:.2f} {self.tr('ريال')}")
        self.total_label.setText(f"{self.tr('الإجمالي')}: {total:.2f} {self.tr('ريال')}")

        # تحديث حالة زر الدفع
        self.checkout_btn.setEnabled(len(self.cart) > 0 and self.current_shift is not None)

        # تحديث عدد الأصناف
        item_count = sum(item['quantity'] for item in self.cart)
        self.cart_table.setHorizontalHeaderLabels([
            f"{self.tr('المنتج')} ({len(self.cart)})",
            self.tr("السعر"),
            self.tr("الكمية"),
            self.tr("الإجمالي")
        ])

    def _cart_item_increment(self, row: int):
        """زيادة كمية عنصر في السلة"""
        if 0 <= row < len(self.cart):
            self.cart[row]['quantity'] += 1
            self.cart[row]['line_total'] = self.cart[row]['quantity'] * self.cart[row]['unit_price']
            self._update_cart_display()
            self._update_product_card_quantities()

    def _cart_item_decrement(self, row: int):
        """تقليل كمية عنصر في السلة"""
        if 0 <= row < len(self.cart):
            if self.cart[row]['quantity'] > 1:
                self.cart[row]['quantity'] -= 1
                self.cart[row]['line_total'] = self.cart[row]['quantity'] * self.cart[row]['unit_price']
            else:
                # إزالة العنصر إذا وصلت الكمية لصفر
                del self.cart[row]
            self._update_cart_display()
            self._update_product_card_quantities()

    def _edit_cart_item(self, item):
        """تعديل عنصر في السلة"""
        row = item.row()
        if row < len(self.cart):
            current_qty = self.cart[row]['quantity']
            new_qty, ok = QInputDialog.getInt(
                self,
                self.tr("تعديل الكمية"),
                self.tr("أدخل الكمية الجديدة:"),
                int(current_qty), 1, 100, 1
            )

            if ok and new_qty != current_qty:
                self.cart[row]['quantity'] = new_qty
                self.cart[row]['line_total'] = new_qty * self.cart[row]['unit_price']
                self._update_cart_display()

    def _remove_selected_item(self):
        """حذف العنصر المحدد"""
        current_row = self.cart_table.currentRow()
        if current_row >= 0 and current_row < len(self.cart):
            reply = QMessageBox.question(
                self,
                self.tr("تأكيد الحذف"),
                self.tr("هل أنت متأكد من حذف هذا العنصر؟"),
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                del self.cart[current_row]
                self._update_cart_display()

    def _clear_cart(self):
        """إفراغ السلة"""
        if not self.cart:
            return

        reply = QMessageBox.question(
            self,
            self.tr("تأكيد الإفراغ"),
            self.tr("هل أنت متأكد من إفراغ السلة بالكامل؟"),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.cart.clear()
            self._update_cart_display()

    def _add_customer_name(self):
        """إضافة اسم العميل"""
        name, ok = QInputDialog.getText(
            self,
            self.tr("اسم العميل"),
            self.tr("أدخل اسم العميل:")
        )
        if ok and name.strip():
            self.customer_input.setText(name.strip())

    def _on_checkout(self):
        """إتمام الدفع"""
        if not self.cart:
            return

        if not self.current_shift:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("يجب فتح وردية أولاً"))
            return

        # حساب الإجمالي مع مراعاة إعداد الأسعار الشاملة للضريبة
        tax_inclusive = get_setting('tax_inclusive', '1') == '1'

        if tax_inclusive:
            total = sum(item['line_total'] for item in self.cart)
            tax = sum(item['line_total'] - (item['line_total'] / (1 + item['tax_rate'])) for item in self.cart)
            subtotal = total - tax
        else:
            subtotal = sum(item['line_total'] for item in self.cart)
            tax = sum(item['line_total'] * item['tax_rate'] for item in self.cart)
            total = subtotal + tax

        # فتح نافذة الدفع
        payment_dialog = PaymentDialog(total, self)
        if payment_dialog.exec_() == QDialog.Accepted:
            self._process_sale(payment_dialog.payment_data)

    def _process_sale(self, payment_data: dict):
        """معالجة عملية البيع"""
        try:
            # حساب الإجماليات مع مراعاة إعداد الأسعار الشاملة للضريبة
            tax_inclusive = get_setting('tax_inclusive', '1') == '1'

            if tax_inclusive:
                total = sum(item['line_total'] for item in self.cart)
                tax = sum(item['line_total'] - (item['line_total'] / (1 + item['tax_rate'])) for item in self.cart)
                subtotal = total - tax
            else:
                subtotal = sum(item['line_total'] for item in self.cart)
                tax = sum(item['line_total'] * item['tax_rate'] for item in self.cart)
                total = subtotal + tax

            # إنشاء الفاتورة
            invoice_number = self._generate_invoice_number()

            cursor = db_manager.execute_query(
                """
                INSERT INTO invoices (
                    invoice_number, type, subtotal, tax_amount, total,
                    paid_amount, change_amount, status, cashier_id, shift_id,
                    table_number, customer_name, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_number,
                    'sale',
                    subtotal,
                    tax,
                    total,
                    payment_data['paid_amount'],
                    payment_data['change'],
                    'completed',
                    self.user_data['id'],
                    self.current_shift['id'],
                    self.table_input.value() if hasattr(self, 'table_input') and self.table_input and self.table_input.value() > 0 else None,
                    self.customer_input.text() if hasattr(self, 'customer_input') and self.customer_input and self.customer_input.text() != self.tr("إضافة") else None,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            )

            invoice_id = cursor.lastrowid

            # إضافة عناصر الفاتورة
            for item in self.cart:
                db_manager.execute_query(
                    """
                    INSERT INTO invoice_items (
                        invoice_id, product_id, product_name, quantity,
                        unit_price, cost_price, tax_rate, line_total
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        invoice_id,
                        item['product_id'],
                        item['product_name'],
                        item['quantity'],
                        item['unit_price'],
                        item['cost_price'],
                        item['tax_rate'],
                        item['line_total']
                    )
                )

                # تحديث المخزون
                db_manager.execute_query(
                    "UPDATE products SET quantity = quantity - ? WHERE id = ?",
                    (item['quantity'], item['product_id'])
                )

                # ✨ خصم المكونات من المخزون بناءً على الوصفة
                # Deduct ingredients based on recipe
                self._deduct_ingredients(item['product_id'], item['quantity'])

            # إضافة الدفعة/الدفعات
            if payment_data['method'] == 'multi':
                # الدفع المتعدد: سجل كل جزء على حدة (نقدي + بطاقة)
                if payment_data.get('cash_amount', 0) > 0:
                    db_manager.execute_query(
                        """
                        INSERT INTO payments (invoice_id, payment_method, amount, reference_number)
                        VALUES (?, ?, ?, ?)
                        """,
                        (invoice_id, 'cash', payment_data['cash_amount'], '')
                    )
                if payment_data.get('card_amount', 0) > 0:
                    db_manager.execute_query(
                        """
                        INSERT INTO payments (invoice_id, payment_method, amount, reference_number)
                        VALUES (?, ?, ?, ?)
                        """,
                        (invoice_id, 'card', payment_data['card_amount'], payment_data.get('reference', ''))
                    )
            else:
                # دفعة واحدة (نقدي / بطاقة / توصيل)
                # نسجل قيمة البيع (total) وليس ما دفعه الزبون (paid_amount)
                db_manager.execute_query(
                    """
                    INSERT INTO payments (invoice_id, payment_method, amount, reference_number)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        invoice_id,
                        payment_data['method'],
                        total,  # قيمة البيع الفعلية وليس المبلغ المدفوع من الزبون
                        payment_data.get('reference', '')
                    )
                )

            # تحديث إجمالي المبيعات في الوردية
            db_manager.execute_query(
                "UPDATE shifts SET total_sales = total_sales + ? WHERE id = ?",
                (total, self.current_shift['id'])
            )

            db_manager.commit()

            # التحقق من نقص المخزون وإرسال إشعار تليجرام
            try:
                from src.utils.telegram import get_telegram_manager
                telegram = get_telegram_manager()

                low_stock_products = []
                for item in self.cart:
                    product_id = item['product_id']
                    cursor = db_manager.execute_query(
                        "SELECT name, quantity, min_alert_level FROM products WHERE id = ?",
                        (product_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        # الوصول للقيم بالترتيب: name=0, quantity=1, min_alert_level=2
                        name, quantity, min_alert_level = row[0], row[1], row[2]
                        if quantity <= min_alert_level:
                            low_stock_products.append({
                                'name': name,
                                'current_stock': quantity,
                                'min_level': min_alert_level
                            })

                if low_stock_products:
                    telegram.send_low_stock_alert(low_stock_products)

            except Exception as e:
                logger.warning(f"Failed to check low stock: {e}")

            # ✨ التحقق من نقص المكونات وإرسال تنبيه تليجرام
            # Check low ingredients and send Telegram alert
            self._check_low_ingredients()

            # طباعة الفاتورة
            self._print_receipt(invoice_id, invoice_number)

            # إفراغ السلة
            self.cart.clear()
            self._update_cart_display()

            # نافذة تأكيد البيع (لمسية)
            from src.ui.payment_dialog import SaleConfirmationDialog
            confirm_dialog = SaleConfirmationDialog(
                invoice_number=invoice_number,
                total=total,
                paid=payment_data['paid_amount'],
                method=payment_data['method'],
                change=payment_data['change'],
                parent=self
            )
            confirm_dialog.exec_()

        except Exception as e:
            db_manager.rollback()
            logger.error(f"خطأ في معالجة البيع: {e}")
            try:
                QMessageBox.critical(self, self.tr("خطأ"), self.tr(f"حدث خطأ أثناء معالجة البيع:\n{str(e)}"))
            except:
                pass

    def _generate_invoice_number(self) -> str:
        """توليد رقم الفاتورة"""
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def _print_receipt(self, invoice_id: int, invoice_number: str):
        """طباعة الفاتورة"""
        try:
            # بناء نص الفاتورة
            company_name = get_setting('company_name', 'مطعمي')
            vat_number = get_setting('vat_number', '')

            receipt_lines = []
            receipt_lines.append(f"{company_name:^42}")
            if vat_number:
                receipt_lines.append(f"{self.tr('الرقم الضريبي')}: {vat_number}")
            receipt_lines.append("-" * 42)

            # معلومات الفاتورة
            receipt_lines.append(f"{self.tr('فاتورة رقم')}: {invoice_number}")
            receipt_lines.append(f"{self.tr('التاريخ')}: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

            # رقم الطاولة (إن وجد)
            if hasattr(self, 'table_input') and self.table_input and self.table_input.value() > 0:
                receipt_lines.append(f"{self.tr('الطاولة')}: {self.table_input.value()}")

            # اسم العميل (إن وجد)
            if hasattr(self, 'customer_input') and self.customer_input:
                customer_name = self.customer_input.text()
                if customer_name and customer_name != self.tr("إضافة"):
                    receipt_lines.append(f"{self.tr('العميل')}: {customer_name}")

            receipt_lines.append("-" * 42)

            # العناصر
            for item in self.cart:
                # الاسم العربي
                receipt_lines.append(f"{item['product_name']}")
                # الاسم الإنجليزي إذا كان مختلفاً
                name_en = item.get('product_name_en', '')
                if name_en and name_en != item['product_name']:
                    receipt_lines.append(f"  ({name_en})")
                receipt_lines.append(f"  {item['quantity']} x {item['unit_price']:.2f} = {item['line_total']:.2f}")

            receipt_lines.append("-" * 42)

            # الإجماليات مع مراعاة إعداد الأسعار الشاملة للضريبة
            tax_inclusive = get_setting('tax_inclusive', '1') == '1'

            if tax_inclusive:
                total = sum(item['line_total'] for item in self.cart)
                tax = sum(item['line_total'] - (item['line_total'] / (1 + item['tax_rate'])) for item in self.cart)
                subtotal = total - tax
            else:
                subtotal = sum(item['line_total'] for item in self.cart)
                tax = sum(item['line_total'] * item['tax_rate'] for item in self.cart)
                total = subtotal + tax

            receipt_lines.append(f"{self.tr('الصافي')}: {subtotal:.2f}")
            receipt_lines.append(f"{self.tr('الضريبة')}: {tax:.2f}")
            receipt_lines.append(f"{self.tr('الإجمالي')}: {total:.2f}")

            # QR Code
            qr_data = generate_qr_code({
                'seller_name': company_name,
                'vat_number': vat_number,
                'timestamp': datetime.now().isoformat(),
                'total': total,
                'vat': tax
            })
            receipt_lines.append(f"QR_DATA:{qr_data}")

            receipt_lines.append("-" * 42)
            receipt_lines.append(get_setting('receipt_footer', 'شكراً لزيارتكم'))

            # الطباعة
            self.printer.print_text("\n".join(receipt_lines))

        except Exception as e:
            logger.error(f"خطأ في الطباعة: {e}")
            # Soft Fail: لا يوقف العملية

    def _check_shift(self):
        """التحقق من حالة الوردية"""
        self.current_shift = get_current_shift()
        self.checkout_btn.setEnabled(len(self.cart) > 0 and self.current_shift is not None)

        # إظهار/إخفاء تنبيه الوردية
        if hasattr(self, 'no_shift_alert'):
            self.no_shift_alert.setVisible(self.current_shift is None)

    def refresh_screen(self):
        """تحديث الشاشة"""
        self._check_shift()
        self._load_products(self.selected_category)

    def _deduct_ingredients(self, product_id: int, quantity_sold: float):
        """
        خصم المكونات من المخزون بناءً على وصفة المنتج
        Deduct ingredients from inventory based on product recipe

        مثال: إذا كان ساندوتش فلافل يحتوي على 200 جرام بطاطس
        وتم بيع 2 ساندوتش، سيتم خصم 400 جرام من مخزون البطاطس
        """
        try:
            # جلب مكونات الوصفة للمنتج
            cursor = db_manager.execute_query(
                """
                SELECT r.ingredient_id, r.quantity_needed, i.name, i.unit
                FROM recipes r
                JOIN ingredients i ON r.ingredient_id = i.id
                WHERE r.product_id = ?
                """,
                (product_id,)
            )
            recipe_items = cursor.fetchall()

            if USE_RUST_CALC:
                # حساب سريع بـ Rust
                recipes_list = [dict(item) for item in recipe_items]
                deductions = calculate_ingredient_deductions(recipes_list, quantity_sold)

                # تنفيذ الخصم من قاعدة البيانات
                for deduction in deductions:
                    db_manager.execute_query(
                        "UPDATE ingredients SET quantity = quantity - ? WHERE id = ?",
                        (deduction['deduct_amount'], deduction['ingredient_id'])
                    )

                # تسجيل في اللوج
                for i, item in enumerate(recipe_items):
                    logger.debug(
                        f"خصم {deductions[i]['deduct_amount']} {item['unit']} من {item['name']} "
                        f"(الوصفة: {item['quantity_needed']} × {quantity_sold} قطعة)"
                    )
            else:
                # الحساب بـ Python (fallback)
                for item in recipe_items:
                    ingredient_id = item['ingredient_id']
                    quantity_needed = item['quantity_needed']

                    # حساب الكمية المطلوب خصمها
                    # quantity_needed = الكمية المطلوبة لقطعة واحدة
                    # quantity_sold = عدد القطع المباعة
                    total_to_deduct = quantity_needed * quantity_sold

                    # خصم من مخزون المكون
                    db_manager.execute_query(
                        "UPDATE ingredients SET quantity = quantity - ? WHERE id = ?",
                        (total_to_deduct, ingredient_id)
                    )

                    logger.debug(
                        f"خصم {total_to_deduct} {item['unit']} من {item['name']} "
                        f"(الوصفة: {quantity_needed} × {quantity_sold} قطعة)"
                    )

        except Exception as e:
            logger.error(f"خطأ في خصم المكونات للمنتج {product_id}: {e}")
            # لا نوقف العملية - نسجل الخطأ فقط

    def _check_low_ingredients(self):
        """
        التحقق من المكونات التي وصلت لحد الإنذار
        Check ingredients that reached minimum alert level
        """
        try:
            cursor = db_manager.execute_query(
                """
                SELECT id, name, unit, quantity, min_alert_level
                FROM ingredients
                WHERE is_active = 1 AND quantity <= min_alert_level
                """
            )
            low_ingredients = cursor.fetchall()

            if low_ingredients:
                # إرسال تنبيه تليجرام
                try:
                    from src.utils.telegram import get_telegram_manager
                    telegram = get_telegram_manager()

                    ingredients_list = [{
                        'name': item['name'],
                        'current_stock': item['quantity'],
                        'unit': item['unit'],
                        'min_level': item['min_alert_level']
                    } for item in low_ingredients]

                    telegram.send_low_ingredients_alert(ingredients_list)

                except Exception as e:
                    logger.warning(f"فشل إرسال تنبيه نقص المكونات: {e}")

        except Exception as e:
            logger.error(f"خطأ في التحقق من نقص المكونات: {e}")

    def _toggle_language(self):
        """تبديل لغة التطبيق - Toggle application language - نسخة محسنة للسرعة"""
        from src.utils.language_manager import language_manager

        # تبديل اللغة (سريع - محسن)
        new_lang = language_manager.switch_language()

        # تثبيت اتجاه التخطيط (المنتجات يمين، السلة يسار) - ثابت في كلتا اللغتين
        self.setLayoutDirection(Qt.RightToLeft)

        # تحديث نص زر اللغة
        self.lang_btn.setText("🌐 عربي" if new_lang == 'en' else "🌐 EN")

        # تحديث أسماء المنتجات مباشرة (بدون تحميل من قاعدة البيانات)
        self._update_product_names_fast()

        # تحديث أسماء الفئات مباشرة (بدون تحميل من قاعدة البيانات)
        self._update_category_names_fast(new_lang)

        # تحديث النصوص الثابتة
        self._retranslate_ui()

        logger.info(f"✅ تم تبديل اللغة بسرعة إلى: {new_lang}")

    def _update_product_names_fast(self):
        """تحديث أسماء المنتجات بسرعة بدون إعادة تحميل"""
        from src.ui.product_button import ProductCard
        for i in range(self.products_grid.count()):
            widget = self.products_grid.itemAt(i).widget()
            if isinstance(widget, ProductCard):
                widget.update_display_name()

    def _update_category_names_fast(self, lang: str):
        """تحديث أسماء الفئات بسرعة - استعلام واحد لكل الفئات"""
        try:
            # جلب كل الأسماء دفعة واحدة (أسرع بكثير)
            cursor = db_manager.execute_query(
                "SELECT id, name, name_en FROM categories WHERE is_active = 1"
            )
            categories = {row['id']: row for row in cursor.fetchall()}

            # تحديث أزرار الفئات
            for i in range(1, self.categories_layout.count()):
                btn = self.categories_layout.itemAt(i).widget()
                if btn and hasattr(btn, 'property'):
                    category_id = btn.property('category_id')
                    if category_id and category_id in categories:
                        cat = categories[category_id]
                        if lang == 'en':
                            new_name = cat['name_en'] or cat['name']
                        else:
                            new_name = cat['name']
                        btn.setText(new_name)
        except Exception as e:
            logger.debug(f"خطأ في تحديث أسماء الفئات: {e}")

    def _retranslate_ui(self):
        """تحديث جميع النصوص القابلة للترجمة - Update all translatable texts"""
        # تحديث عنوان السلة
        self.cart_header_label.setText(self.tr("🛒 سلة المشتريات"))

        # تحديث أزرار الفئات
        self.all_categories_btn.setText(self.tr("الكل"))

        # تحديث أزرار الترتيب
        if self.order_lock_btn.isChecked():
            self.order_lock_btn.setText(self.tr("🔒 الترتيب مقفل"))
        else:
            self.order_lock_btn.setText(self.tr("🔓 الترتيب مفتوح"))
        self.save_order_btn.setText(self.tr("💾 حفظ الترتيب"))

        # تحديث أزرار التحكم في السلة
        self.clear_cart_btn.setText(self.tr("🗑️ إفراغ"))
        self.remove_item_btn.setText(self.tr("❌ حذف"))

        # تحديث زر الدفع
        self.checkout_btn.setText(self.tr("💳 إتمام الدفع"))

        # تحديث تسميات الإجمالي
        self._update_cart_display()

        # تحديث رؤوس جدول السلة
        self.cart_table.setHorizontalHeaderLabels([
            self.tr("المنتج"),
            self.tr("السعر"),
            self.tr("الكمية"),
            self.tr("الإجمالي")
        ])

        # تحديث تنبيه عدم وجود وردية
        for child in self.no_shift_alert.findChildren(QLabel):
            text = child.text()
            if "وردية" in text or "shift" in text.lower():
                if "اذهب" in text or "Go" in text:
                    child.setText(self.tr("اذهب إلى القائمة ← الورديات ← فتح وردية جديدة"))
                else:
                    child.setText(self.tr("لا توجد وردية مفتوحة! يجب فتح وردية أولاً لإضافة منتجات للسلة."))

    def refresh_screen(self):
        """تحديث الشاشة بالكامل - Refresh entire screen"""
        self._check_shift()
        self._load_categories()
        self._load_products(self.selected_category)
        self._update_cart_display()

