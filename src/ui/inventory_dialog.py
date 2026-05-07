"""
إدارة المخزون
Inventory Management Dialog
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QGroupBox, QFormLayout, QLineEdit,
    QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox, QMessageBox,
    QInputDialog, QAbstractItemView, QHeaderView, QLabel, QFileDialog,
    QWidget, QListWidget, QRadioButton
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtGui import QFont, QColor
from loguru import logger
import json
import csv
from datetime import datetime

from database import db_manager
from src.ui.ProductDialog import ProductDialog
from src.ui.CategoryDialog import CategoryDialog
from src.ui.IngredientDialog import IngredientDialog


class InventoryDialog(QDialog):
    """نافذة إدارة المخزون"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("إدارة المخزون"))
        self.setMinimumSize(900, 700)
        self._setup_ui()

    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        layout = QVBoxLayout()

        # التبويبات
        tabs = QTabWidget()

        # تبويب المنتجات
        products_tab = self._create_products_tab()
        tabs.addTab(products_tab, self.tr("المنتجات"))

        # تبويب الفئات
        categories_tab = self._create_categories_tab()
        tabs.addTab(categories_tab, self.tr("الفئات"))

        # تبويب المكونات (جديد في النسخة 2.0)
        ingredients_tab = self._create_ingredients_tab()
        tabs.addTab(ingredients_tab, self.tr("المكونات"))

        # تبويب الوصفات (جديد في النسخة 2.0)
        recipes_tab = self._create_recipes_tab()
        tabs.addTab(recipes_tab, self.tr("الوصفات"))

        # تبويب الاستيراد/التصدير
        import_export_tab = self._create_import_export_tab()
        tabs.addTab(import_export_tab, self.tr("استيراد/تصدير"))

        layout.addWidget(tabs)
        self.setLayout(layout)

    def _create_products_tab(self):
        """إنشاء تبويب المنتجات"""
        widget = QWidget()
        layout = QVBoxLayout()

        # أزرار التحكم
        controls_layout = QHBoxLayout()

        self.add_product_btn = QPushButton(self.tr("➕ إضافة منتج"))
        self.add_product_btn.setMinimumHeight(40)
        self.add_product_btn.clicked.connect(self._add_product)
        controls_layout.addWidget(self.add_product_btn)

        self.edit_product_btn = QPushButton(self.tr("✏️ تعديل"))
        self.edit_product_btn.setMinimumHeight(40)
        self.edit_product_btn.clicked.connect(self._edit_product)
        controls_layout.addWidget(self.edit_product_btn)

        self.delete_product_btn = QPushButton(self.tr("🗑️ حذف"))
        self.delete_product_btn.setMinimumHeight(40)
        self.delete_product_btn.clicked.connect(self._delete_product)
        controls_layout.addWidget(self.delete_product_btn)

        controls_layout.addStretch()

        # البحث
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("بحث..."))
        self.search_input.setMinimumHeight(40)
        self.search_input.textChanged.connect(self._search_products)
        controls_layout.addWidget(self.search_input)

        layout.addLayout(controls_layout)

        # جدول المنتجات
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(11)  # +1 للترتيب
        self.products_table.setHorizontalHeaderLabels([
            self.tr("الترتيب"),
            self.tr("الباركود"),
            self.tr("الاسم"),
            self.tr("الفئة"),
            self.tr("سعر التكلفة"),
            self.tr("سعر البيع"),
            self.tr("الكمية"),
            self.tr("الحد الأدنى"),
            self.tr("الضريبة %"),
            self.tr("الحالة"),
            self.tr("الهامش %")
        ])
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.products_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # إضافة النقر المزدوج لفتح نافذة التعديل
        self.products_table.doubleClicked.connect(self._edit_product)

        header = self.products_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)  # السماح بالتوسيع اليدوي
        header.setStretchLastSection(True)  # تمديد العمود الأخير
        # تعيين عرض ابتدائي للأعمدة
        self.products_table.setColumnWidth(0, 60)  # الترتيب
        self.products_table.setColumnWidth(2, 200)  # الاسم

        layout.addWidget(self.products_table)

        widget.setLayout(layout)
        self._load_products()
        return widget

    def _toggle_drag_drop(self, locked: bool):
        """تفعيل/إلغاء تفعيل السحب والإفلات"""
        if locked:
            self.products_table.setDragEnabled(False)
            self.products_table.setAcceptDrops(False)
            self.drag_lock_check.setText(self.tr("🔒 قفل الترتيب"))
        else:
            self.products_table.setDragEnabled(True)
            self.products_table.setAcceptDrops(True)
            self.drag_lock_check.setText(self.tr("🔓 الترتيب مفتوح"))
            QMessageBox.information(
                self,
                self.tr("معلومة"),
                self.tr("يمكنك الآن سحب الصفوف وإفلاتها لإعادة ترتيب المنتجات.\nبعد الانتهاء، اضغط 'حفظ الترتيب' لحفظ التغييرات.")
            )

    def _create_categories_tab(self):
        """إنشاء تبويب الفئات"""
        widget = QWidget()
        layout = QVBoxLayout()

        # أزرار التحكم
        controls_layout = QHBoxLayout()

        self.add_category_btn = QPushButton(self.tr("➕ إضافة فئة"))
        self.add_category_btn.setMinimumHeight(40)
        self.add_category_btn.clicked.connect(self._add_category)
        controls_layout.addWidget(self.add_category_btn)

        self.edit_category_btn = QPushButton(self.tr("✏️ تعديل"))
        self.edit_category_btn.setMinimumHeight(40)
        self.edit_category_btn.clicked.connect(self._edit_category)
        controls_layout.addWidget(self.edit_category_btn)

        self.delete_category_btn = QPushButton(self.tr("🗑️ حذف"))
        self.delete_category_btn.setMinimumHeight(40)
        self.delete_category_btn.clicked.connect(self._delete_category)
        controls_layout.addWidget(self.delete_category_btn)

        layout.addLayout(controls_layout)

        # جدول الفئات
        self.categories_table = QTableWidget()
        self.categories_table.setColumnCount(4)
        self.categories_table.setHorizontalHeaderLabels([
            self.tr("الاسم"),
            self.tr("اللون"),
            self.tr("الترتيب"),
            self.tr("الحالة")
        ])
        self.categories_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.categories_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        layout.addWidget(self.categories_table)

        widget.setLayout(layout)
        self._load_categories()
        return widget

    def _create_ingredients_tab(self):
        """إنشاء تبويب المكونات (جديد في النسخة 2.0)"""
        widget = QWidget()
        layout = QVBoxLayout()

        # أزرار التحكم
        controls_layout = QHBoxLayout()

        self.add_ingredient_btn = QPushButton(self.tr("➕ إضافة مكون"))
        self.add_ingredient_btn.setMinimumHeight(40)
        self.add_ingredient_btn.clicked.connect(self._add_ingredient)
        controls_layout.addWidget(self.add_ingredient_btn)

        self.edit_ingredient_btn = QPushButton(self.tr("✏️ تعديل"))
        self.edit_ingredient_btn.setMinimumHeight(40)
        self.edit_ingredient_btn.clicked.connect(self._edit_ingredient)
        controls_layout.addWidget(self.edit_ingredient_btn)

        self.delete_ingredient_btn = QPushButton(self.tr("🗑️ حذف"))
        self.delete_ingredient_btn.setMinimumHeight(40)
        self.delete_ingredient_btn.clicked.connect(self._delete_ingredient)
        controls_layout.addWidget(self.delete_ingredient_btn)

        layout.addLayout(controls_layout)

        # جدول المكونات
        self.ingredients_table = QTableWidget()
        self.ingredients_table.setColumnCount(6)
        self.ingredients_table.setHorizontalHeaderLabels([
            self.tr("الاسم"),
            self.tr("الوحدة"),
            self.tr("الكمية"),
            self.tr("الحد الأدنى"),
            self.tr("سعر الوحدة"),
            self.tr("الحالة")
        ])
        self.ingredients_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ingredients_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        layout.addWidget(self.ingredients_table)

        widget.setLayout(layout)
        self._load_ingredients()
        return widget

    def _create_recipes_tab(self):
        """إنشاء تبويب الوصفات (جديد في النسخة 2.0)"""
        widget = QWidget()
        layout = QVBoxLayout()

        # اختيار المنتج
        product_layout = QHBoxLayout()
        product_layout.addWidget(QLabel(self.tr("اختر المنتج:")))

        self.recipe_product_combo = QComboBox()
        self.recipe_product_combo.currentIndexChanged.connect(self._load_recipe)
        product_layout.addWidget(self.recipe_product_combo)

        self.load_products_for_recipe()
        layout.addLayout(product_layout)

        # جدول الوصفة
        self.recipe_table = QTableWidget()
        self.recipe_table.setColumnCount(4)
        self.recipe_table.setHorizontalHeaderLabels([
            self.tr("المكون"),
            self.tr("الوحدة"),
            self.tr("الكمية المطلوبة"),
            self.tr("الإجراءات")
        ])
        self.recipe_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.recipe_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        layout.addWidget(self.recipe_table)

        # أزرار التحكم
        controls_layout = QHBoxLayout()

        self.add_recipe_item_btn = QPushButton(self.tr("➕ إضافة مكون"))
        self.add_recipe_item_btn.clicked.connect(self._add_recipe_item)
        controls_layout.addWidget(self.add_recipe_item_btn)

        self.save_recipe_btn = QPushButton(self.tr("💾 حفظ الوصفة"))
        self.save_recipe_btn.clicked.connect(self._save_recipe)
        controls_layout.addWidget(self.save_recipe_btn)

        layout.addLayout(controls_layout)

        widget.setLayout(layout)
        return widget

    def _create_import_export_tab(self):
        """إنشاء تبويب الاستيراد والتصدير"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)

        # خيارات التنسيق
        format_group = QGroupBox(self.tr("تنسيق الملف"))
        format_group.setFont(QFont("Arial", 11, QFont.Bold))
        format_layout = QHBoxLayout()

        self.csv_radio = QRadioButton("CSV (Excel)")
        self.csv_radio.setChecked(True)
        self.json_radio = QRadioButton("JSON")

        format_layout.addWidget(self.csv_radio)
        format_layout.addWidget(self.json_radio)
        format_layout.addStretch()

        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        # تصدير
        export_group = QGroupBox(self.tr("تصدير البيانات"))
        export_group.setFont(QFont("Arial", 11, QFont.Bold))
        export_layout = QHBoxLayout()

        export_buttons = [
            (self.tr("تصدير المنتجات"), "products"),
            (self.tr("تصدير الفئات"), "categories"),
            (self.tr("تصدير المكونات"), "ingredients"),
            (self.tr("تصدير الوصفات"), "recipes"),
        ]

        for text, data_type in export_buttons:
            btn = QPushButton(text)
            btn.setMinimumHeight(40)
            btn.clicked.connect(lambda _, t=data_type: self._export_data(t))
            export_layout.addWidget(btn)

        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

        # استيراد
        import_group = QGroupBox(self.tr("استيراد البيانات"))
        import_group.setFont(QFont("Arial", 11, QFont.Bold))
        import_layout = QVBoxLayout()

        import_buttons = [
            (self.tr("استيراد المنتجات"), "products"),
            (self.tr("استيراد الفئات"), "categories"),
            (self.tr("استيراد المكونات"), "ingredients"),
            (self.tr("استيراد الوصفات"), "recipes"),
        ]

        for text, data_type in import_buttons:
            btn = QPushButton(text)
            btn.setMinimumHeight(40)
            btn.clicked.connect(lambda _, t=data_type: self._import_data(t))
            import_layout.addWidget(btn)

        # زر الاستيراد الشامل
        combined_btn = QPushButton(self.tr("📦 استيراد شامل (الكل)"))
        combined_btn.setMinimumHeight(50)
        combined_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; font-size: 14px;")
        combined_btn.setToolTip(self.tr("استيراد جميع البيانات: الفئات + المكونات + المنتجات + الوصفات"))
        combined_btn.clicked.connect(self._import_all_data)
        import_layout.addWidget(combined_btn)

        import_group.setLayout(import_layout)
        layout.addWidget(import_group)

        # القوالب
        template_group = QGroupBox(self.tr("قوالب جاهزة"))
        template_group.setFont(QFont("Arial", 11, QFont.Bold))
        template_layout = QHBoxLayout()

        template_buttons = [
            (self.tr("قالب المنتجات"), "products"),
            (self.tr("قالب الفئات"), "categories"),
            (self.tr("قالب المكونات"), "ingredients"),
            (self.tr("قالب الوصفات"), "recipes"),
            (self.tr("قالب شامل"), "all"),
        ]

        for text, data_type in template_buttons:
            btn = QPushButton("📥 " + text)
            btn.setMinimumHeight(40)
            btn.setStyleSheet("background-color: #f39c12; color: white;")
            btn.clicked.connect(lambda _, t=data_type: self._download_template(t))
            template_layout.addWidget(btn)

        template_group.setLayout(template_layout)
        layout.addWidget(template_group)

        widget.setLayout(layout)
        return widget
        layout.addWidget(import_group)

        widget.setLayout(layout)
        return widget

    def _load_products(self):
        """تحميل المنتجات"""
        try:
            cursor = db_manager.execute_query("""
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                ORDER BY p.display_order, p.name
            """)
            products = cursor.fetchall()

            self.products_table.setRowCount(len(products))

            for i, product in enumerate(products):
                # عمود الترتيب (مع تخزين معرف المنتج)
                try:
                    order_val = product['display_order'] if product['display_order'] is not None else 0
                except (KeyError, IndexError):
                    order_val = 0
                order_item = QTableWidgetItem(str(order_val))
                order_item.setData(Qt.UserRole, product['id'])  # Store product ID
                self.products_table.setItem(i, 0, order_item)

                # باقي الأعمدة (مع إزاحة +1)
                self.products_table.setItem(i, 1, QTableWidgetItem(product['barcode'] or ''))
                self.products_table.setItem(i, 2, QTableWidgetItem(product['name']))
                self.products_table.setItem(i, 3, QTableWidgetItem(product['category_name'] or ''))
                self.products_table.setItem(i, 4, QTableWidgetItem(f"{product['cost_price']:.2f}"))
                self.products_table.setItem(i, 5, QTableWidgetItem(f"{product['selling_price']:.2f}"))
                self.products_table.setItem(i, 6, QTableWidgetItem(f"{product['quantity']:.0f}"))
                self.products_table.setItem(i, 7, QTableWidgetItem(f"{product['min_alert_level']:.0f}"))
                self.products_table.setItem(i, 8, QTableWidgetItem(f"{product['tax_rate']*100:.0f}"))
                self.products_table.setItem(i, 9, QTableWidgetItem(self.tr("نشط") if product['is_active'] else self.tr("غير نشط")))

                # حساب الهامش
                margin = ((product['selling_price'] - product['cost_price']) / product['cost_price'] * 100) if product['cost_price'] > 0 else 0
                self.products_table.setItem(i, 10, QTableWidgetItem(f"{margin:.1f}%"))

                # تلوين المنتجات منخفضة المخزون
                if product['quantity'] <= product['min_alert_level']:
                    for j in range(11):
                        self.products_table.item(i, j).setBackground(QColor(255, 200, 200))

        except Exception as e:
            logger.error(f"خطأ في تحميل المنتجات: {e}")

    def _load_categories(self):
        """تحميل الفئات"""
        try:
            cursor = db_manager.execute_query("SELECT * FROM categories ORDER BY display_order")
            categories = cursor.fetchall()

            self.categories_table.setRowCount(len(categories))

            for i, category in enumerate(categories):
                self.categories_table.setItem(i, 0, QTableWidgetItem(category['name']))
                self.categories_table.setItem(i, 1, QTableWidgetItem(category['color'] or ''))
                self.categories_table.setItem(i, 2, QTableWidgetItem(str(category['display_order'])))
                self.categories_table.setItem(i, 3, QTableWidgetItem(self.tr("نشط") if category['is_active'] else self.tr("غير نشط")))

        except Exception as e:
            logger.error(f"خطأ في تحميل الفئات: {e}")

    def _load_ingredients(self):
        """تحميل المكونات"""
        try:
            cursor = db_manager.execute_query("SELECT * FROM ingredients ORDER BY name")
            ingredients = cursor.fetchall()

            self.ingredients_table.setRowCount(len(ingredients))

            for i, ingredient in enumerate(ingredients):
                self.ingredients_table.setItem(i, 0, QTableWidgetItem(ingredient['name']))
                self.ingredients_table.setItem(i, 1, QTableWidgetItem(ingredient['unit']))
                self.ingredients_table.setItem(i, 2, QTableWidgetItem(f"{ingredient['quantity']:.2f}"))
                self.ingredients_table.setItem(i, 3, QTableWidgetItem(f"{ingredient['min_alert_level']:.2f}"))
                self.ingredients_table.setItem(i, 4, QTableWidgetItem(f"{ingredient['cost_per_unit']:.2f}"))
                self.ingredients_table.setItem(i, 5, QTableWidgetItem(self.tr("نشط") if ingredient['is_active'] else self.tr("غير نشط")))

                # تلوين المكونات منخفضة
                if ingredient['quantity'] <= ingredient['min_alert_level']:
                    for j in range(6):
                        self.ingredients_table.item(i, j).setBackground(QColor(255, 200, 200))

        except Exception as e:
            logger.error(f"خطأ في تحميل المكونات: {e}")

    def load_products_for_recipe(self):
        """تحميل المنتجات للوصفات"""
        try:
            cursor = db_manager.execute_query("SELECT id, name FROM products WHERE is_active = 1 ORDER BY name")
            products = cursor.fetchall()

            self.recipe_product_combo.clear()
            for product in products:
                self.recipe_product_combo.addItem(product['name'], product['id'])

        except Exception as e:
            logger.error(f"خطأ في تحميل المنتجات للوصفات: {e}")

    def _load_recipe(self):
        """تحميل وصفة المنتج المحدد"""
        try:
            # التحقق من وجود recipe_table قبل الاستخدام
            if not hasattr(self, 'recipe_table'):
                return

            product_id = self.recipe_product_combo.currentData()
            if not product_id:
                return

            cursor = db_manager.execute_query("""
                SELECT r.*, i.name as ingredient_name, i.unit
                FROM recipes r
                JOIN ingredients i ON r.ingredient_id = i.id
                WHERE r.product_id = ?
            """, (product_id,))

            recipe_items = cursor.fetchall()

            self.recipe_table.setRowCount(len(recipe_items))

            for i, item in enumerate(recipe_items):
                self.recipe_table.setItem(i, 0, QTableWidgetItem(item['ingredient_name']))
                self.recipe_table.setItem(i, 1, QTableWidgetItem(item['unit']))
                self.recipe_table.setItem(i, 2, QTableWidgetItem(f"{item['quantity_needed']:.3f}"))

                # زر حذف
                delete_btn = QPushButton(self.tr("حذف"))
                delete_btn.clicked.connect(lambda _, r_id=item['id']: self._delete_recipe_item(r_id))
                self.recipe_table.setCellWidget(i, 3, delete_btn)

        except Exception as e:
            logger.error(f"خطأ في تحميل الوصفة: {e}")

    def _add_product(self):
        """إضافة منتج جديد"""
        dialog = ProductDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_products()

    def _edit_product(self):
        """تعديل منتج"""
        current_row = self.products_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("الرجاء اختيار منتج للتعديل"))
            return

        # الحصول على معرف المنتج المخزن في الصف
        product_id = self.products_table.item(current_row, 0).data(Qt.UserRole)
        if not product_id:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("تعذر الحصول على معرف المنتج"))
            return

        dialog = ProductDialog(self, product_id)
        if dialog.exec_() == QDialog.Accepted:
            self._load_products()

    def _delete_product(self):
        """حذف منتج"""
        current_row = self.products_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("الرجاء اختيار منتج للحذف"))
            return

        # الحصول على معرف المنتج من Qt.UserRole
        product_id = self.products_table.item(current_row, 0).data(Qt.UserRole)
        product_name = self.products_table.item(current_row, 2).text()  # العمود 2 هو الاسم

        if not product_id:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("تعذر الحصول على معرف المنتج"))
            return

        reply = QMessageBox.question(
            self,
            self.tr("تأكيد الحذف"),
            self.tr(f"هل أنت متأكد من حذف المنتج '{product_name}'؟"),
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                db_manager.execute_query(
                    "UPDATE products SET is_active = 0 WHERE id = ?",
                    (product_id,)
                )
                db_manager.commit()
                self._load_products()
            except Exception as e:
                logger.error(f"خطأ في حذف المنتج: {e}")
                QMessageBox.critical(self, self.tr("خطأ"), self.tr("حدث خطأ أثناء حذف المنتج"))

    def _search_products(self):
        """بحث في المنتجات"""
        search_text = self.search_input.text().strip()
        if not search_text:
            self._load_products()
            return

        try:
            cursor = db_manager.execute_query("""
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE (p.name LIKE ? OR p.barcode LIKE ?) AND p.is_active = 1
                ORDER BY p.display_order, p.name
            """, (f'%{search_text}%', f'%{search_text}%'))

            products = cursor.fetchall()

            self.products_table.setRowCount(len(products))

            for i, product in enumerate(products):
                # عمود الترتيب (مع تخزين معرف المنتج) - مهم للتعديل!
                try:
                    order_val = product['display_order'] if product['display_order'] is not None else 0
                except (KeyError, IndexError):
                    order_val = 0
                order_item = QTableWidgetItem(str(order_val))
                order_item.setData(Qt.UserRole, product['id'])  # تخزين معرف المنتج
                self.products_table.setItem(i, 0, order_item)

                # باقي الأعمدة
                self.products_table.setItem(i, 1, QTableWidgetItem(product['barcode'] or ''))
                self.products_table.setItem(i, 2, QTableWidgetItem(product['name']))
                self.products_table.setItem(i, 3, QTableWidgetItem(product['category_name'] or ''))
                self.products_table.setItem(i, 4, QTableWidgetItem(f"{product['cost_price']:.2f}"))
                self.products_table.setItem(i, 5, QTableWidgetItem(f"{product['selling_price']:.2f}"))
                self.products_table.setItem(i, 6, QTableWidgetItem(f"{product['quantity']:.0f}"))
                self.products_table.setItem(i, 7, QTableWidgetItem(f"{product['min_alert_level']:.0f}"))
                self.products_table.setItem(i, 8, QTableWidgetItem(f"{product['tax_rate']*100:.0f}"))
                self.products_table.setItem(i, 9, QTableWidgetItem(self.tr("نشط") if product['is_active'] else self.tr("غير نشط")))

                # حساب الهامش
                margin = ((product['selling_price'] - product['cost_price']) / product['cost_price'] * 100) if product['cost_price'] > 0 else 0
                self.products_table.setItem(i, 10, QTableWidgetItem(f"{margin:.1f}%"))

                # تلوين المنتجات منخفضة المخزون
                if product['quantity'] <= product['min_alert_level']:
                    for j in range(11):
                        if self.products_table.item(i, j):
                            self.products_table.item(i, j).setBackground(QColor(255, 200, 200))

        except Exception as e:
            logger.error(f"خطأ في البحث عن المنتجات: {e}")

    def _add_category(self):
        """إضافة فئة"""
        dialog = CategoryDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_categories()

    def _edit_category(self):
        """تعديل فئة"""
        QMessageBox.information(self, self.tr("معلومات"), self.tr("سيتم تنفيذ هذه الميزة لاحقاً"))

    def _delete_category(self):
        """حذف فئة"""
        QMessageBox.information(self, self.tr("معلومات"), self.tr("سيتم تنفيذ هذه الميزة لاحقاً"))

    def _add_ingredient(self):
        """إضافة مكون"""
        dialog = IngredientDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_ingredients()

    def _edit_ingredient(self):
        """تعديل مكون"""
        QMessageBox.information(self, self.tr("معلومات"), self.tr("سيتم تنفيذ هذه الميزة لاحقاً"))

    def _delete_ingredient(self):
        """حذف مكون"""
        QMessageBox.information(self, self.tr("معلومات"), self.tr("سيتم تنفيذ هذه الميزة لاحقاً"))

    def _export_data(self, data_type: str):
        """تصدير البيانات (CSV/JSON)"""
        try:
            is_json = self.json_radio.isChecked()
            ext = "json" if is_json else "csv"
            file_filter = "JSON Files (*.json)" if is_json else "CSV Files (*.csv)"

            filename, _ = QFileDialog.getSaveFileName(
                self, self.tr("تصدير البيانات"),
                f"{data_type}_export_{datetime.now().strftime('%Y%m%d')}.{ext}",
                file_filter
            )

            if not filename:
                return

            if data_type == 'products':
                cursor = db_manager.execute_query("""
                    SELECT p.name, p.barcode, p.cost_price, p.selling_price,
                           p.quantity, p.min_alert_level, c.name as category,
                           p.unit, p.tax_rate
                    FROM products p
                    LEFT JOIN categories c ON p.category_id = c.id
                    WHERE p.is_active = 1
                """)
                headers = ['المنتج', 'الباركود', 'سعر التكلفة', 'سعر البيع',
                          'الكمية', 'الحد الأدنى', 'الفئة', 'الوحدة', 'الضريبة']

            elif data_type == 'categories':
                cursor = db_manager.execute_query("SELECT name, color, display_order FROM categories WHERE is_active = 1")
                headers = ['الفئة', 'اللون', 'الترتيب']

            elif data_type == 'ingredients':
                cursor = db_manager.execute_query("SELECT name, unit, quantity, cost_per_unit, min_alert_level FROM ingredients WHERE is_active = 1")
                headers = ['المكون', 'الوحدة', 'الكمية', 'سعر الوحدة', 'الحد الأدنى']

            elif data_type == 'recipes':
                cursor = db_manager.execute_query("""
                    SELECT p.name as product_name, i.name as ingredient_name,
                           i.unit, r.quantity_needed
                    FROM recipes r
                    JOIN products p ON r.product_id = p.id
                    JOIN ingredients i ON r.ingredient_id = i.id
                    WHERE p.is_active = 1 AND i.is_active = 1
                    ORDER BY p.name, i.name
                """)
                headers = ['المنتج', 'المكون', 'الوحدة', 'الكمية المطلوبة']
            else:
                return

            # تحويل البيانات إلى قائمة من القواميس
            rows_data = [dict(row) for row in cursor.fetchall()]

            if is_json:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(rows_data, f, ensure_ascii=False, indent=2)
            else:
                with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    # Mapping logic for CSV based on headers would be better, but simple writer works if query matches
                    # Here we map explicitly to ensure order
                    for row in rows_data:
                        if data_type == 'products':
                            values = [row.get('name'), row.get('barcode'), row.get('cost_price'), row.get('selling_price'),
                                     row.get('quantity'), row.get('min_alert_level'), row.get('category'), row.get('unit'), row.get('tax_rate')]
                        elif data_type == 'categories':
                            values = [row.get('name'), row.get('color'), row.get('display_order')]
                        elif data_type == 'ingredients':
                            values = [row.get('name'), row.get('unit'), row.get('quantity'), row.get('cost_per_unit'), row.get('min_alert_level')]
                        elif data_type == 'recipes':
                            values = [row.get('product_name'), row.get('ingredient_name'), row.get('unit'), row.get('quantity_needed')]
                        writer.writerow([str(v) if v is not None else '' for v in values])

            QMessageBox.information(self, self.tr("نجاح"), self.tr(f"تم تصدير {len(rows_data)} سجل بنجاح إلى:\n{filename}"))

        except Exception as e:
            logger.error(f"خطأ في تصدير البيانات: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr("حدث خطأ أثناء التصدير"))(
                self, self.tr("تصدير البيانات"),
                f"{data_type}_export_{datetime.now().strftime('%Y%m%d')}.csv",
                "CSV Files (*.csv)"
            )

            if not filename:
                return

            if data_type == 'products':
                cursor = db_manager.execute_query("""
                    SELECT p.name, p.barcode, p.cost_price, p.selling_price,
                           p.quantity, p.min_alert_level, c.name as category
                    FROM products p
                    LEFT JOIN categories c ON p.category_id = c.id
                    WHERE p.is_active = 1
                """)
                headers = ['المنتج', 'الباركود', 'سعر التكلفة', 'سعر البيع',
                          'الكمية', 'الحد الأدنى', 'الفئة']
            elif data_type == 'categories':
                cursor = db_manager.execute_query("SELECT name, display_order FROM categories WHERE is_active = 1")
                headers = ['الفئة', 'ترتيب العرض']
            elif data_type == 'ingredients':
                cursor = db_manager.execute_query("SELECT name, unit, quantity, cost_per_unit FROM ingredients WHERE is_active = 1")
                headers = ['المكون', 'الوحدة', 'الكمية', 'سعر الوحدة']
            else:
                return

            data = cursor.fetchall()

            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(headers)

                for row in data:
                    writer.writerow([str(row.get(col, '')) for col in row.keys()])

            QMessageBox.information(self, self.tr("نجاح"), self.tr(f"تم تصدير البيانات إلى:\n{filename}"))

        except Exception as e:
            logger.error(f"خطأ في تصدير البيانات: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr("حدث خطأ أثناء التصدير"))

    def _import_data(self, data_type: str):
        """استيراد البيانات (CSV/JSON)"""
        try:
            is_json = self.json_radio.isChecked()
            file_filter = "JSON Files (*.json)" if is_json else "CSV Files (*.csv)"

            filename, _ = QFileDialog.getOpenFileName(
                self, self.tr("استيراد البيانات"),
                "",
                f"{file_filter};;All Files (*.*)"
            )

            if not filename:
                return

            rows_data = []
            if is_json:
                with open(filename, 'r', encoding='utf-8') as f:
                    rows_data = json.load(f)
            else:
                with open(filename, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    rows_data = list(reader)

            if not rows_data:
                QMessageBox.warning(self, self.tr("تحذير"), self.tr("الملف فارغ أو بتنسيق غير صحيح"))
                return

            imported = 0
            updated = 0
            errors = 0

            try:
                for row in rows_data:
                    # تنظيف البيانات
                    row = {k: str(v).strip() for k, v in row.items() if v is not None}

                    if data_type == 'products':
                        # تعيين قيم افتراضية
                        name = row.get('name') or row.get('المنتج')
                        barcode = row.get('barcode') or row.get('الباركود')
                        cost = float(row.get('cost_price') or row.get('سعر التكلفة') or 0)
                        price = float(row.get('selling_price') or row.get('سعر البيع') or 0)

                        if not name: continue

                        # التحقق من وجود المنتج
                        cursor = db_manager.execute_query("SELECT id FROM products WHERE name = ?", (name,))
                        existing = cursor.fetchone()

                        if existing:
                            db_manager.execute_query("""
                                UPDATE products SET barcode=?, cost_price=?, selling_price=?
                                WHERE id=?
                            """, (barcode, cost, price, existing['id']))
                            updated += 1
                        else:
                            db_manager.execute_query("""
                                INSERT INTO products (name, barcode, cost_price, selling_price, is_active)
                                VALUES (?, ?, ?, ?, 1)
                            """, (name, barcode, cost, price))
                            imported += 1

                    elif data_type == 'ingredients':
                        name = row.get('name') or row.get('المكون')
                        unit = row.get('unit') or row.get('الوحدة') or 'kg'

                        if not name: continue

                        cursor = db_manager.execute_query("SELECT id FROM ingredients WHERE name = ?", (name,))
                        if cursor.fetchone():
                            updated += 1 # تحديث (ممكن إضافة منطق للتحديث هنا)
                        else:
                            db_manager.execute_query("""
                                INSERT INTO ingredients (name, unit, quantity, is_active)
                                VALUES (?, ?, 0, 1)
                            """, (name, unit))
                            imported += 1

                    elif data_type == 'categories':
                        name = row.get('name') or row.get('الفئة')
                        color = row.get('color') or row.get('اللون') or '#4CAF50'
                        display_order = int(row.get('display_order') or row.get('الترتيب') or 0)

                        if not name: continue

                        cursor = db_manager.execute_query("SELECT id FROM categories WHERE name = ?", (name,))
                        existing = cursor.fetchone()

                        if existing:
                            db_manager.execute_query("""
                                UPDATE categories SET color=?, display_order=?
                                WHERE id=?
                            """, (color, display_order, existing['id']))
                            updated += 1
                        else:
                            db_manager.execute_query("""
                                INSERT INTO categories (name, color, display_order, is_active)
                                VALUES (?, ?, ?, 1)
                            """, (name, color, display_order))
                            imported += 1

                    elif data_type == 'recipes':
                        # استيراد الوصفات - ربط المنتجات بالمكونات
                        product_name = row.get('product_name') or row.get('المنتج')
                        ingredient_name = row.get('ingredient_name') or row.get('المكون')
                        quantity_needed = float(row.get('quantity_needed') or row.get('الكمية المطلوبة') or 0)

                        if not product_name or not ingredient_name: continue

                        # البحث عن المنتج
                        cursor = db_manager.execute_query("SELECT id FROM products WHERE name = ?", (product_name,))
                        product = cursor.fetchone()
                        if not product:
                            errors += 1
                            continue

                        # البحث عن المكون
                        cursor = db_manager.execute_query("SELECT id FROM ingredients WHERE name = ?", (ingredient_name,))
                        ingredient = cursor.fetchone()
                        if not ingredient:
                            errors += 1
                            continue

                        # التحقق من وجود الوصفة
                        cursor = db_manager.execute_query(
                            "SELECT id FROM recipes WHERE product_id = ? AND ingredient_id = ?",
                            (product['id'], ingredient['id'])
                        )
                        existing = cursor.fetchone()

                        if existing:
                            db_manager.execute_query("""
                                UPDATE recipes SET quantity_needed = ? WHERE id = ?
                            """, (quantity_needed, existing['id']))
                            updated += 1
                        else:
                            db_manager.execute_query("""
                                INSERT INTO recipes (product_id, ingredient_id, quantity_needed)
                                VALUES (?, ?, ?)
                            """, (product['id'], ingredient['id'], quantity_needed))
                            imported += 1

                db_manager.commit()

                # تحديث الواجهة
                if data_type == 'products': self._load_products()
                elif data_type == 'ingredients': self._load_ingredients()
                elif data_type == 'categories': self._load_categories()
                elif data_type == 'recipes': self._load_recipe()

                msg = f"تمت العملية بنجاح:\n\nسجلات جديدة: {imported}\nسجلات محدثة: {updated}"
                if errors > 0:
                    msg += f"\nأخطاء: {errors}"
                QMessageBox.information(self, self.tr("نجاح"), self.tr(msg))

            except Exception as e:
                db_manager.rollback()
                raise e

        except Exception as e:
            logger.error(f"خطأ في استيراد البيانات: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr(f"حدث خطأ أثناء الاستيراد:\n{str(e)}"))

    def _import_combined_data(self):
        """استيراد شامل للمنتجات والتصنيفات من ملف واحد"""
        try:
            is_json = self.json_radio.isChecked()
            file_filter = "JSON Files (*.json)" if is_json else "CSV Files (*.csv)"

            filename, _ = QFileDialog.getOpenFileName(
                self, self.tr("استيراد شامل (منتجات + تصنيفات)"),
                "",
                f"{file_filter};;All Files (*.*)"
            )

            if not filename:
                return

            rows_data = []
            if is_json:
                with open(filename, 'r', encoding='utf-8') as f:
                    rows_data = json.load(f)
            else:
                with open(filename, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    rows_data = list(reader)

            if not rows_data:
                QMessageBox.warning(self, self.tr("تحذير"), self.tr("الملف فارغ أو بتنسيق غير صحيح"))
                return

            categories_imported = 0
            categories_updated = 0
            products_imported = 0
            products_updated = 0

            try:
                # استخراج الفئات الفريدة أولاً
                unique_categories = set()
                for row in rows_data:
                    category = row.get('category') or row.get('الفئة')
                    if category:
                        unique_categories.add(category.strip())

                # إنشاء الفئات أولاً
                category_map = {}  # تخزين اسم الفئة -> id
                for cat_name in unique_categories:
                    cursor = db_manager.execute_query("SELECT id FROM categories WHERE name = ?", (cat_name,))
                    existing = cursor.fetchone()

                    if existing:
                        category_map[cat_name] = existing['id']
                        categories_updated += 1
                    else:
                        db_manager.execute_query("""
                            INSERT INTO categories (name, color, display_order, is_active)
                            VALUES (?, ?, ?, 1)
                        """, (cat_name, '#4CAF50', 0))
                        # الحصول على ID الفئة الجديدة
                        cursor = db_manager.execute_query("SELECT id FROM categories WHERE name = ?", (cat_name,))
                        new_cat = cursor.fetchone()
                        if new_cat:
                            category_map[cat_name] = new_cat['id']
                        categories_imported += 1

                # استيراد المنتجات
                for row in rows_data:
                    row = {k: str(v).strip() for k, v in row.items() if v is not None}

                    name = row.get('name') or row.get('المنتج')
                    barcode = row.get('barcode') or row.get('الباركود')
                    cost = float(row.get('cost_price') or row.get('سعر التكلفة') or 0)
                    price = float(row.get('selling_price') or row.get('سعر البيع') or 0)
                    category = row.get('category') or row.get('الفئة')
                    unit = row.get('unit') or row.get('الوحدة') or 'حبة'
                    tax_rate = float(row.get('tax_rate') or row.get('الضريبة') or 0.15)

                    if not name:
                        continue

                    category_id = category_map.get(category) if category else None

                    cursor = db_manager.execute_query("SELECT id FROM products WHERE name = ?", (name,))
                    existing = cursor.fetchone()

                    if existing:
                        db_manager.execute_query("""
                            UPDATE products SET barcode=?, cost_price=?, selling_price=?,
                                   category_id=?, unit=?, tax_rate=?
                            WHERE id=?
                        """, (barcode, cost, price, category_id, unit, tax_rate, existing['id']))
                        products_updated += 1
                    else:
                        db_manager.execute_query("""
                            INSERT INTO products (name, barcode, cost_price, selling_price,
                                   category_id, unit, tax_rate, quantity, is_active)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1)
                        """, (name, barcode, cost, price, category_id, unit, tax_rate))
                        products_imported += 1

                db_manager.commit()

                # تحديث الواجهة
                self._load_products()
                self._load_categories()

                msg = f"""تمت العملية بنجاح:

📁 التصنيفات:
   - جديدة: {categories_imported}
   - محدثة: {categories_updated}

📦 المنتجات:
   - جديدة: {products_imported}
   - محدثة: {products_updated}"""

                QMessageBox.information(self, self.tr("نجاح"), self.tr(msg))

            except Exception as e:
                db_manager.rollback()
                raise e

        except Exception as e:
            logger.error(f"خطأ في الاستيراد الشامل: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr(f"حدث خطأ أثناء الاستيراد:\n{str(e)}"))

    def _import_all_data(self):
        """استيراد شامل لجميع البيانات: الفئات + المكونات + المنتجات + الوصفات"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, self.tr("استيراد شامل (الكل)"),
                "",
                "JSON Files (*.json);;All Files (*.*)"
            )

            if not filename:
                return

            # قراءة ملف JSON
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, dict):
                QMessageBox.warning(self, self.tr("تحذير"),
                    self.tr("صيغة الملف غير صحيحة. يجب أن يحتوي على أقسام: categories, ingredients, products, recipes"))
                return

            # إحصائيات
            stats = {
                'categories': {'imported': 0, 'updated': 0},
                'ingredients': {'imported': 0, 'updated': 0},
                'products': {'imported': 0, 'updated': 0},
                'recipes': {'imported': 0, 'updated': 0, 'errors': 0}
            }

            try:
                # 1. استيراد الفئات أولاً
                for row in data.get('categories', []):
                    name = row.get('name') or row.get('الفئة')
                    if not name: continue
                    color = row.get('color') or row.get('اللون') or '#4CAF50'
                    display_order = int(row.get('display_order') or row.get('الترتيب') or 0)

                    cursor = db_manager.execute_query("SELECT id FROM categories WHERE name = ?", (name,))
                    existing = cursor.fetchone()

                    if existing:
                        db_manager.execute_query("UPDATE categories SET color=?, display_order=? WHERE id=?",
                            (color, display_order, existing['id']))
                        stats['categories']['updated'] += 1
                    else:
                        db_manager.execute_query(
                            "INSERT INTO categories (name, color, display_order, is_active) VALUES (?, ?, ?, 1)",
                            (name, color, display_order))
                        stats['categories']['imported'] += 1

                # 2. استيراد المكونات
                for row in data.get('ingredients', []):
                    name = row.get('name') or row.get('المكون')
                    if not name: continue
                    unit = row.get('unit') or row.get('الوحدة') or 'kg'
                    quantity = float(row.get('quantity') or row.get('الكمية') or 0)
                    cost_per_unit = float(row.get('cost_per_unit') or row.get('سعر الوحدة') or 0)
                    min_alert = float(row.get('min_alert_level') or row.get('الحد الأدنى') or 0)

                    cursor = db_manager.execute_query("SELECT id FROM ingredients WHERE name = ?", (name,))
                    existing = cursor.fetchone()

                    if existing:
                        db_manager.execute_query(
                            "UPDATE ingredients SET unit=?, quantity=?, cost_per_unit=?, min_alert_level=? WHERE id=?",
                            (unit, quantity, cost_per_unit, min_alert, existing['id']))
                        stats['ingredients']['updated'] += 1
                    else:
                        db_manager.execute_query(
                            "INSERT INTO ingredients (name, unit, quantity, cost_per_unit, min_alert_level, is_active) VALUES (?, ?, ?, ?, ?, 1)",
                            (name, unit, quantity, cost_per_unit, min_alert))
                        stats['ingredients']['imported'] += 1

                # 3. استيراد المنتجات
                for row in data.get('products', []):
                    name = row.get('name') or row.get('المنتج')
                    if not name: continue
                    barcode = row.get('barcode') or row.get('الباركود') or ''
                    cost = float(row.get('cost_price') or row.get('سعر التكلفة') or 0)
                    price = float(row.get('selling_price') or row.get('سعر البيع') or 0)
                    category_name = row.get('category') or row.get('الفئة')

                    # البحث عن الفئة
                    category_id = None
                    if category_name:
                        cursor = db_manager.execute_query("SELECT id FROM categories WHERE name = ?", (category_name,))
                        cat = cursor.fetchone()
                        if cat:
                            category_id = cat['id']

                    cursor = db_manager.execute_query("SELECT id FROM products WHERE name = ?", (name,))
                    existing = cursor.fetchone()

                    if existing:
                        db_manager.execute_query(
                            "UPDATE products SET barcode=?, cost_price=?, selling_price=?, category_id=? WHERE id=?",
                            (barcode, cost, price, category_id, existing['id']))
                        stats['products']['updated'] += 1
                    else:
                        db_manager.execute_query(
                            "INSERT INTO products (name, barcode, cost_price, selling_price, category_id, is_active) VALUES (?, ?, ?, ?, ?, 1)",
                            (name, barcode, cost, price, category_id))
                        stats['products']['imported'] += 1

                # 4. استيراد الوصفات (أخيراً لأنها تعتمد على المنتجات والمكونات)
                for row in data.get('recipes', []):
                    product_name = row.get('product_name') or row.get('المنتج')
                    ingredient_name = row.get('ingredient_name') or row.get('المكون')
                    quantity_needed = float(row.get('quantity_needed') or row.get('الكمية المطلوبة') or 0)

                    if not product_name or not ingredient_name: continue

                    # البحث عن المنتج
                    cursor = db_manager.execute_query("SELECT id FROM products WHERE name = ?", (product_name,))
                    product = cursor.fetchone()
                    if not product:
                        stats['recipes']['errors'] += 1
                        continue

                    # البحث عن المكون
                    cursor = db_manager.execute_query("SELECT id FROM ingredients WHERE name = ?", (ingredient_name,))
                    ingredient = cursor.fetchone()
                    if not ingredient:
                        stats['recipes']['errors'] += 1
                        continue

                    # التحقق من وجود الوصفة
                    cursor = db_manager.execute_query(
                        "SELECT id FROM recipes WHERE product_id = ? AND ingredient_id = ?",
                        (product['id'], ingredient['id']))
                    existing = cursor.fetchone()

                    if existing:
                        db_manager.execute_query("UPDATE recipes SET quantity_needed = ? WHERE id = ?",
                            (quantity_needed, existing['id']))
                        stats['recipes']['updated'] += 1
                    else:
                        db_manager.execute_query(
                            "INSERT INTO recipes (product_id, ingredient_id, quantity_needed) VALUES (?, ?, ?)",
                            (product['id'], ingredient['id'], quantity_needed))
                        stats['recipes']['imported'] += 1

                db_manager.commit()

                # تحديث الواجهة
                self._load_products()
                self._load_categories()
                self._load_ingredients()
                self._load_recipe()

                msg = f"""تم الاستيراد الشامل بنجاح:

📁 الفئات:
   - جديدة: {stats['categories']['imported']}
   - محدثة: {stats['categories']['updated']}

🥗 المكونات:
   - جديدة: {stats['ingredients']['imported']}
   - محدثة: {stats['ingredients']['updated']}

📦 المنتجات:
   - جديدة: {stats['products']['imported']}
   - محدثة: {stats['products']['updated']}

📋 الوصفات:
   - جديدة: {stats['recipes']['imported']}
   - محدثة: {stats['recipes']['updated']}
   - أخطاء: {stats['recipes']['errors']}"""

                QMessageBox.information(self, self.tr("نجاح"), self.tr(msg))

            except Exception as e:
                db_manager.rollback()
                raise e

        except Exception as e:
            logger.error(f"خطأ في الاستيراد الشامل: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr(f"حدث خطأ أثناء الاستيراد:\n{str(e)}"))

    def _download_template(self, data_type: str):
        """تحميل قالب للبيانات"""
        try:
            is_json = self.json_radio.isChecked()
            ext = "json" if is_json else "csv"
            file_filter = "JSON Files (*.json)" if is_json else "CSV Files (*.csv)"

            filename, _ = QFileDialog.getSaveFileName(
                self, self.tr("حفظ القالب"),
                f"{data_type}_template.{ext}",
                file_filter
            )

            if not filename:
                return

            templates = {
                'products': [
                    {'name': 'برجر دجاج', 'barcode': '123456', 'cost_price': '10.0', 'selling_price': '25.0', 'category': 'سندويتشات', 'unit': 'حبه', 'tax_rate': '0.15'},
                    {'name': 'بيبسي', 'barcode': '789012', 'cost_price': '2.0', 'selling_price': '5.0', 'category': 'مشروبات', 'unit': 'علبة', 'tax_rate': '0.15'},
                    {'name': 'ساندوتش فلافل', 'barcode': '111222', 'cost_price': '5.0', 'selling_price': '12.0', 'category': 'سندويتشات', 'unit': 'حبه', 'tax_rate': '0.15'},
                    {'name': 'بطاطس جيزاني', 'barcode': '333444', 'cost_price': '8.0', 'selling_price': '18.0', 'category': 'مقبلات', 'unit': 'حبه', 'tax_rate': '0.15'}
                ],
                'categories': [
                    {'name': 'سندويتشات', 'color': '#ff0000', 'display_order': '1'},
                    {'name': 'مشروبات', 'color': '#00ff00', 'display_order': '2'},
                    {'name': 'مقبلات', 'color': '#ff9800', 'display_order': '3'}
                ],
                'ingredients': [
                    {'name': 'خبز برجر', 'unit': 'حبه', 'quantity': '100', 'cost_per_unit': '1.0', 'min_alert_level': '10'},
                    {'name': 'طماطم', 'unit': 'kg', 'quantity': '5.0', 'cost_per_unit': '5.0', 'min_alert_level': '2'},
                    {'name': 'بطاطس', 'unit': 'kg', 'quantity': '20.0', 'cost_per_unit': '4.0', 'min_alert_level': '5'},
                    {'name': 'فلافل جاهز', 'unit': 'kg', 'quantity': '10.0', 'cost_per_unit': '15.0', 'min_alert_level': '3'}
                ],
                'recipes': [
                    {'product_name': 'ساندوتش فلافل', 'ingredient_name': 'بطاطس', 'unit': 'kg', 'quantity_needed': '0.2'},
                    {'product_name': 'ساندوتش فلافل', 'ingredient_name': 'فلافل جاهز', 'unit': 'kg', 'quantity_needed': '0.15'},
                    {'product_name': 'ساندوتش فلافل', 'ingredient_name': 'طماطم', 'unit': 'kg', 'quantity_needed': '0.05'},
                    {'product_name': 'بطاطس جيزاني', 'ingredient_name': 'بطاطس', 'unit': 'kg', 'quantity_needed': '0.6'},
                    {'product_name': 'برجر دجاج', 'ingredient_name': 'خبز برجر', 'unit': 'حبه', 'quantity_needed': '1'},
                    {'product_name': 'برجر دجاج', 'ingredient_name': 'طماطم', 'unit': 'kg', 'quantity_needed': '0.05'}
                ],
                'all': {
                    'categories': [
                        {'name': 'سندويتشات', 'color': '#e74c3c', 'display_order': '1'},
                        {'name': 'مقبلات', 'color': '#f39c12', 'display_order': '2'},
                        {'name': 'مشروبات', 'color': '#3498db', 'display_order': '3'}
                    ],
                    'ingredients': [
                        {'name': 'بطاطس', 'unit': 'kg', 'quantity': '20.0', 'cost_per_unit': '4.0', 'min_alert_level': '5'},
                        {'name': 'فلافل جاهز', 'unit': 'kg', 'quantity': '10.0', 'cost_per_unit': '15.0', 'min_alert_level': '3'},
                        {'name': 'خبز برجر', 'unit': 'حبه', 'quantity': '100', 'cost_per_unit': '1.0', 'min_alert_level': '10'},
                        {'name': 'طماطم', 'unit': 'kg', 'quantity': '5.0', 'cost_per_unit': '5.0', 'min_alert_level': '2'}
                    ],
                    'products': [
                        {'name': 'ساندوتش فلافل', 'barcode': '111', 'cost_price': '5.0', 'selling_price': '12.0', 'category': 'سندويتشات'},
                        {'name': 'بطاطس جيزاني', 'barcode': '222', 'cost_price': '8.0', 'selling_price': '18.0', 'category': 'مقبلات'},
                        {'name': 'برجر دجاج', 'barcode': '333', 'cost_price': '10.0', 'selling_price': '25.0', 'category': 'سندويتشات'}
                    ],
                    'recipes': [
                        {'product_name': 'ساندوتش فلافل', 'ingredient_name': 'بطاطس', 'quantity_needed': '0.2'},
                        {'product_name': 'ساندوتش فلافل', 'ingredient_name': 'فلافل جاهز', 'quantity_needed': '0.15'},
                        {'product_name': 'بطاطس جيزاني', 'ingredient_name': 'بطاطس', 'quantity_needed': '0.6'},
                        {'product_name': 'برجر دجاج', 'ingredient_name': 'خبز برجر', 'quantity_needed': '1'},
                        {'product_name': 'برجر دجاج', 'ingredient_name': 'طماطم', 'quantity_needed': '0.05'}
                    ]
                }
            }

            data = templates.get(data_type, [])

            # معالجة خاصة للقالب الشامل - JSON فقط
            if data_type == 'all':
                if not is_json:
                    QMessageBox.warning(self, self.tr("تحذير"),
                        self.tr("القالب الشامل يدعم JSON فقط. سيتم حفظه كملف JSON."))
                    filename = filename.replace('.csv', '.json') if filename.endswith('.csv') else filename + '.json'

                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            elif is_json:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                if not data:
                    QMessageBox.warning(self, self.tr("تحذير"), self.tr("لا توجد بيانات للقالب"))
                    return
                with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)

            QMessageBox.information(self, self.tr("نجاح"), self.tr("تم حفظ القالب بنجاح"))

        except Exception as e:
            logger.error(f"Template download error: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr("فشل حفظ القالب"))


    def _add_category(self):
        """إضافة فئة"""
        dialog = CategoryDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_categories()

    def _edit_category(self):
        """تعديل فئة"""
        current_row = self.categories_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(
                self,
                self.tr("تحذير"),
                self.tr("الرجاء اختيار فئة من الجدول للتعديل")
            )
            return

        try:
            # الحصول على اسم الفئة من الجدول
            category_name = self.categories_table.item(current_row, 0).text()

            # جلب بيانات الفئة الكاملة من قاعدة البيانات
            cursor = db_manager.execute_query(
                "SELECT * FROM categories WHERE name = ? AND is_active = 1",
                (category_name,)
            )
            category = cursor.fetchone()

            if not category:
                QMessageBox.warning(
                    self,
                    self.tr("خطأ"),
                    self.tr("لم يتم العثور على الفئة في قاعدة البيانات")
                )
                return

            # فتح نافذة التعديل مع البيانات الحالية
            # ملاحظة: CategoryDialog يجب أن يدعم معامل category_id
            from src.ui.CategoryDialog import CategoryDialog
            # تحويل sqlite3.Row إلى dictionary
            category_dict = dict(category)
            dialog = CategoryDialog(self, category_data=category_dict)

            if dialog.exec_() == QDialog.Accepted:
                self._load_categories()
                QMessageBox.information(
                    self,
                    self.tr("نجاح"),
                    self.tr("تم تحديث بيانات الفئة بنجاح")
                )
                logger.info(f"Category edited: {category_name}")

        except Exception as e:
            logger.error(f"خطأ في تعديل الفئة: {e}")
            QMessageBox.critical(
                self,
                self.tr("خطأ"),
                self.tr(f"حدث خطأ أثناء تعديل الفئة:\\n{str(e)}")
            )

    def _delete_category(self):
        """حذف فئة"""
        current_row = self.categories_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(
                self,
                self.tr("تحذير"),
                self.tr("الرجاء اختيار فئة من الجدول للحذف")
            )
            return

        try:
            category_name = self.categories_table.item(current_row, 0).text()

            # الحصول على معرف الفئة
            cursor = db_manager.execute_query(
                "SELECT id FROM categories WHERE name = ? AND is_active = 1",
                (category_name,)
            )
            category = cursor.fetchone()

            if not category:
                QMessageBox.warning(
                    self,
                    self.tr("خطأ"),
                    self.tr("لم يتم العثور على الفئة")
                )
                return

            # التحقق من وجود منتجات مرتبطة بالفئة
            cursor = db_manager.execute_query(
                "SELECT COUNT(*) as count FROM products WHERE category_id = ? AND is_active = 1",
                (category['id'],)
            )
            result = cursor.fetchone()

            if result and result['count'] > 0:
                QMessageBox.warning(
                    self,
                    self.tr("تحذير"),
                    self.tr(f"لا يمكن حذف الفئة '{category_name}'\\n\\nيوجد {result['count']} منتج مرتبط بهذه الفئة.\\n\\nالرجاء حذف أو نقل المنتجات أولاً.")
                )
                return

            # تأكيد الحذف من المستخدم
            reply = QMessageBox.question(
                self,
                self.tr("تأكيد الحذف"),
                self.tr(f"هل أنت متأكد من حذف الفئة '{category_name}'؟\\n\\nهذا الإجراء لا يمكن التراجع عنه."),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # حذف منطقي (Soft Delete)
                db_manager.execute_query(
                    "UPDATE categories SET is_active = 0 WHERE id = ?",
                    (category['id'],)
                )
                db_manager.commit()

                # إعادة تحميل الجدول
                self._load_categories()

                QMessageBox.information(
                    self,
                    self.tr("نجاح"),
                    self.tr(f"تم حذف الفئة '{category_name}' بنجاح")
                )

                logger.info(f"Category deleted (soft): {category_name} (ID: {category['id']})")

        except Exception as e:
            db_manager.rollback()
            logger.error(f"خطأ في حذف الفئة: {e}")
            QMessageBox.critical(
                self,
                self.tr("خطأ"),
                self.tr(f"حدث خطأ أثناء حذف الفئة:\\n{str(e)}")
            )

    def _add_ingredient(self):
        """إضافة مكون"""
        dialog = IngredientDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_ingredients()

    def _edit_ingredient(self):
        """تعديل مكون"""
        current_row = self.ingredients_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(
                self,
                self.tr("تحذير"),
                self.tr("الرجاء اختيار مكون من الجدول للتعديل")
            )
            return

        try:
            # الحصول على اسم المكون من الجدول
            ingredient_name = self.ingredients_table.item(current_row, 0).text()

            # جلب بيانات المكون الكاملة من قاعدة البيانات
            cursor = db_manager.execute_query(
                "SELECT * FROM ingredients WHERE name = ? AND is_active = 1",
                (ingredient_name,)
            )
            ingredient = cursor.fetchone()

            if not ingredient:
                QMessageBox.warning(
                    self,
                    self.tr("خطأ"),
                    self.tr("لم يتم العثور على المكون في قاعدة البيانات")
                )
                return

            # فتح نافذة التعديل مع البيانات الحالية
            from src.ui.IngredientDialog import IngredientDialog
            # تحويل sqlite3.Row إلى dictionary
            ingredient_dict = dict(ingredient)
            dialog = IngredientDialog(self, ingredient_data=ingredient_dict)

            if dialog.exec_() == QDialog.Accepted:
                self._load_ingredients()
                QMessageBox.information(
                    self,
                    self.tr("نجاح"),
                    self.tr("تم تحديث بيانات المكون بنجاح")
                )
                logger.info(f"Ingredient edited: {ingredient_name}")

        except Exception as e:
            logger.error(f"خطأ في تعديل المكون: {e}")
            QMessageBox.critical(
                self,
                self.tr("خطأ"),
                self.tr(f"حدث خطأ أثناء تعديل المكون:\\n{str(e)}")
            )

    def _delete_ingredient(self):
        """حذف مكون"""
        current_row = self.ingredients_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(
                self,
                self.tr("تحذير"),
                self.tr("الرجاء اختيار مكون من الجدول للحذف")
            )
            return

        try:
            ingredient_name = self.ingredients_table.item(current_row, 0).text()

            # الحصول على معرف المكون
            cursor = db_manager.execute_query(
                "SELECT id FROM ingredients WHERE name = ? AND is_active = 1",
                (ingredient_name,)
            )
            ingredient = cursor.fetchone()

            if not ingredient:
                QMessageBox.warning(
                    self,
                    self.tr("خطأ"),
                    self.tr("لم يتم العثور على المكون")
                )
                return

            # التحقق من استخدام المكون في الوصفات
            cursor = db_manager.execute_query(
                "SELECT COUNT(*) as count FROM recipes WHERE ingredient_id = ?",
                (ingredient['id'],)
            )
            result = cursor.fetchone()

            if result and result['count'] > 0:
                QMessageBox.warning(
                    self,
                    self.tr("تحذير"),
                    self.tr(f"لا يمكن حذف المكون '{ingredient_name}'\\n\\nهذا المكون مستخدم في {result['count']} وصفة.\\n\\nالرجاء حذف الوصفات أولاً أو استبدال المكون.")
                )
                return

            # تأكيد الحذف من المستخدم
            reply = QMessageBox.question(
                self,
                self.tr("تأكيد الحذف"),
                self.tr(f"هل أنت متأكد من حذف المكون '{ingredient_name}'؟\\n\\nهذا الإجراء لا يمكن التراجع عنه."),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # حذف منطقي (Soft Delete)
                db_manager.execute_query(
                    "UPDATE ingredients SET is_active = 0 WHERE id = ?",
                    (ingredient['id'],)
                )
                db_manager.commit()

                # إعادة تحميل الجدول
                self._load_ingredients()

                QMessageBox.information(
                    self,
                    self.tr("نجاح"),
                    self.tr(f"تم حذف المكون '{ingredient_name}' بنجاح")
                )

                logger.info(f"Ingredient deleted (soft): {ingredient_name} (ID: {ingredient['id']})")

        except Exception as e:
            db_manager.rollback()
            logger.error(f"خطأ في حذف المكون: {e}")
            QMessageBox.critical(
                self,
                self.tr("خطأ"),
                self.tr(f"حدث خطأ أثناء حذف المكون:\\n{str(e)}")
            )

    def _add_recipe_item(self):
        """إضافة مكون للوصفة"""
        from PyQt5.QtWidgets import QInputDialog

        product_id = self.recipe_product_combo.currentData()
        if not product_id:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("الرجاء اختيار منتج أولاً"))
            return

        try:
            # الحصول على جميع المكونات النشطة
            cursor = db_manager.execute_query(
                "SELECT id, name, unit FROM ingredients WHERE is_active = 1 ORDER BY name"
            )
            ingredients = cursor.fetchall()

            if not ingredients:
                QMessageBox.warning(self, self.tr("تحذير"), self.tr("لا توجد مكونات متاحة. الرجاء إضافة مكونات أولاً"))
                return

            # عرض قائمة المكونات للاختيار
            ingredient_names = [f"{ing['name']} ({ing['unit']})" for ing in ingredients]
            ingredient_name, ok = QInputDialog.getItem(
                self,
                self.tr("اختر المكون"),
                self.tr("اختر المكون المطلوب إضافته:"),
                ingredient_names,
                0,
                False
            )

            if not ok:
                return

            # الحصول على المكون المحدد
            selected_idx = ingredient_names.index(ingredient_name)
            ingredient = ingredients[selected_idx]

            # التحقق من عدم وجود المكون في الوصفة مسبقاً
            cursor = db_manager.execute_query(
                "SELECT id FROM recipes WHERE product_id = ? AND ingredient_id = ?",
                (product_id, ingredient['id'])
            )
            if cursor.fetchone():
                QMessageBox.warning(
                    self,
                    self.tr("تحذير"),
                    self.tr("هذا المكون موجود بالفعل في الوصفة")
                )
                return

            # طلب إدخال الكمية المطلوبة
            quantity, ok = QInputDialog.getDouble(
                self,
                self.tr("الكمية المطلوبة"),
                self.tr(f"أدخل كمية {ingredient['name']} المطلوبة لكل وحدة منتج ({ingredient['unit']}):"),
                0.000, 0.001, 10000.0, 3
            )

            if not ok or quantity <= 0:
                return

            # الحفظ في قاعدة البيانات
            db_manager.execute_query(
                "INSERT INTO recipes (product_id, ingredient_id, quantity_needed) VALUES (?, ?, ?)",
                (product_id, ingredient['id'], quantity)
            )
            db_manager.commit()

            # إعادة تحميل جدول الوصفة
            self._load_recipe()

            QMessageBox.information(
                self,
                self.tr("نجاح"),
                self.tr(f"تم إضافة '{ingredient['name']}' إلى الوصفة بنجاح\\nالكمية: {quantity:.3f} {ingredient['unit']}")
            )

            logger.info(f"Recipe item added: Product ID {product_id}, Ingredient ID {ingredient['id']}, Qty {quantity}")

        except Exception as e:
            db_manager.rollback()
            logger.error(f"خطأ في إضافة مكون للوصفة: {e}")
            QMessageBox.critical(
                self,
                self.tr("خطأ"),
                self.tr(f"حدث خطأ أثناء إضافة المكون:\\n{str(e)}")
            )


    def _save_recipe(self):
        """حفظ الوصفة"""
        product_id = self.recipe_product_combo.currentData()
        if not product_id:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("الرجاء اختيار منتج"))
            return

        # التحقق من وجود مكونات
        row_count = self.recipe_table.rowCount()
        if row_count == 0:
            QMessageBox.warning(
                self,
                self.tr("تحذير"),
                self.tr("الرجاء إضافة مكون واحد على الأقل إلى الوصفة")
            )
            return

        # الوصفة محفوظة تلقائياً عند إضافة كل مكون
        product_name = self.recipe_product_combo.currentText()
        QMessageBox.information(
            self,
            self.tr("معلومات"),
            self.tr(f"وصفة '{product_name}' محفوظة بنجاح\\n\\nعدد المكونات: {row_count}\\n\\nملاحظة: يتم الحفظ تلقائياً عند إضافة كل مكون")
        )

        logger.info(f"Recipe saved confirmation for Product ID {product_id} with {row_count} ingredients")


    def _delete_recipe_item(self, recipe_id: int):
        """حذف عنصر من الوصفة"""
        reply = QMessageBox.question(
            self,
            self.tr("تأكيد الحذف"),
            self.tr("هل أنت متأكد من حذف هذا المكون من الوصفة؟\\n\\nهذا الإجراء لا يمكن التراجع عنه."),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # حذف من قاعدة البيانات
                db_manager.execute_query(
                    "DELETE FROM recipes WHERE id = ?",
                    (recipe_id,)
                )
                db_manager.commit()

                # إعادة تحميل جدول الوصفة
                self._load_recipe()

                QMessageBox.information(
                    self,
                    self.tr("نجاح"),
                    self.tr("تم حذف المكون من الوصفة بنجاح")
                )

                logger.info(f"Recipe item deleted: Recipe ID {recipe_id}")

            except Exception as e:
                db_manager.rollback()
                logger.error(f"خطأ في حذف مكون من الوصفة: {e}")
                QMessageBox.critical(
                    self,
                    self.tr("خطأ"),
                    self.tr(f"حدث خطأ أثناء الحذف:\\n{str(e)}")
                )



