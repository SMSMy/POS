"""
إدارة المرتجعات
Returns Management Dialog
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QGroupBox, QFormLayout, QLineEdit,
    QSpinBox, QDoubleSpinBox, QMessageBox, QInputDialog, QAbstractItemView,
    QHeaderView, QLabel, QFrame, QListWidget, QWidget, QGridLayout,
    QScrollArea, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from datetime import datetime
from loguru import logger

from database import db_manager, get_current_shift


class ReturnsDialog(QDialog):
    """نافذة إدارة المرتجعات"""

    def __init__(self, parent=None, user_data: dict = None, current_shift: dict = None):
        super().__init__(parent)
        self.user_data = user_data
        self.current_shift = current_shift
        self.setWindowTitle(self.tr("إدارة المرتجعات"))
        self.setMinimumSize(900, 700)

        # سلة المرتجعات اليدوية
        self.manual_return_cart = []
        self.selected_category_id = None

        self._setup_ui()

    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        layout = QVBoxLayout()

        # التبويبات
        tabs = QTabWidget()

        # تبويب الإرجاع بالفاتورة
        invoice_tab = self._create_invoice_return_tab()
        tabs.addTab(invoice_tab, self.tr("إرجاع بالفاتورة"))

        # تبويب الإرجاع اليدوي
        manual_tab = self._create_manual_return_tab()
        tabs.addTab(manual_tab, self.tr("إرجاع يدوي"))

        layout.addWidget(tabs)
        self.setLayout(layout)

    def _create_invoice_return_tab(self):
        """إنشاء تبويب الإرجاع بالفاتورة"""
        widget = QWidget()
        layout = QVBoxLayout()

        # البحث عن الفاتورة
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel(self.tr("رقم الفاتورة:")))

        self.invoice_number_input = QLineEdit()
        self.invoice_number_input.setMinimumHeight(35)
        self.invoice_number_input.setFont(QFont("Arial", 12))
        search_layout.addWidget(self.invoice_number_input)

        self.search_invoice_btn = QPushButton(self.tr("🔍 بحث"))
        self.search_invoice_btn.setMinimumHeight(40)
        self.search_invoice_btn.clicked.connect(self._search_invoice)
        search_layout.addWidget(self.search_invoice_btn)

        layout.addLayout(search_layout)

        # معلومات الفاتورة
        self.invoice_info_frame = QFrame()
        self.invoice_info_frame.setFrameShape(QFrame.Box)
        self.invoice_info_frame.setVisible(False)

        self.invoice_info_layout = QVBoxLayout()
        self.invoice_info_frame.setLayout(self.invoice_info_layout)

        layout.addWidget(self.invoice_info_frame)

        # عناصر الفاتورة
        self.invoice_items_table = QTableWidget()
        self.invoice_items_table.setColumnCount(6)
        self.invoice_items_table.setHorizontalHeaderLabels([
            self.tr("المنتج"),
            self.tr("السعر"),
            self.tr("الكمية المباعة"),
            self.tr("الكمية المرتجعة"),
            self.tr("الكمية القابلة للإرجاع"),
            self.tr("الكمية المطلوب إرجاعها")
        ])
        self.invoice_items_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.invoice_items_table.setVisible(False)

        header = self.invoice_items_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        layout.addWidget(self.invoice_items_table)

        # أزرار الإجراءات
        actions_layout = QHBoxLayout()

        self.process_return_btn = QPushButton(self.tr("🔄 معالجة الإرجاع"))
        self.process_return_btn.setMinimumHeight(45)
        self.process_return_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.process_return_btn.clicked.connect(self._process_invoice_return)
        self.process_return_btn.setVisible(False)
        actions_layout.addWidget(self.process_return_btn)

        layout.addLayout(actions_layout)

        widget.setLayout(layout)
        return widget

    def _create_manual_return_tab(self):
        """إنشاء تبويب الإرجاع اليدوي"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # ═══════════════════════════════════════════════════════════
        # شبكة المنتجات (مثل شاشة البيع)
        # ═══════════════════════════════════════════════════════════
        products_layout = QHBoxLayout()
        products_layout.setSpacing(10)

        # الفئات
        categories_group = QGroupBox(self.tr("الفئات"))
        categories_group.setFont(QFont("Arial", 11, QFont.Bold))
        categories_group.setMaximumWidth(180)
        categories_layout = QVBoxLayout()

        self.categories_list = QListWidget()
        self.categories_list.setFont(QFont("Arial", 11))
        self.categories_list.itemClicked.connect(self._select_category_for_return)
        categories_layout.addWidget(self.categories_list)

        categories_group.setLayout(categories_layout)
        products_layout.addWidget(categories_group)

        # المنتجات (شبكة قابلة للتمرير)
        products_group = QGroupBox(self.tr("المنتجات - اضغط للإضافة"))
        products_group.setFont(QFont("Arial", 11, QFont.Bold))
        products_inner_layout = QVBoxLayout()

        self.products_scroll = QScrollArea()
        self.products_scroll.setWidgetResizable(True)
        self.products_container = QWidget()
        self.products_grid = QGridLayout(self.products_container)
        self.products_grid.setSpacing(8)
        self.products_scroll.setWidget(self.products_container)

        products_inner_layout.addWidget(self.products_scroll)
        products_group.setLayout(products_inner_layout)
        products_layout.addWidget(products_group, 3)

        layout.addLayout(products_layout, 2)

        # ═══════════════════════════════════════════════════════════
        # سلة المرتجعات
        # ═══════════════════════════════════════════════════════════
        cart_group = QGroupBox(self.tr("سلة المرتجعات"))
        cart_group.setFont(QFont("Arial", 11, QFont.Bold))
        cart_layout = QVBoxLayout()

        self.return_cart_table = QTableWidget()
        self.return_cart_table.setColumnCount(5)
        self.return_cart_table.setHorizontalHeaderLabels([
            self.tr("المنتج"),
            self.tr("السعر"),
            self.tr("الكمية"),
            self.tr("الإجمالي"),
            self.tr("حذف")
        ])
        self.return_cart_table.setMaximumHeight(150)

        header = self.return_cart_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        cart_layout.addWidget(self.return_cart_table)

        # الإجمالي وسبب الإرجاع
        totals_layout = QHBoxLayout()

        # سبب الإرجاع
        totals_layout.addWidget(QLabel(self.tr("سبب الإرجاع:")))
        self.return_reason_combo = QComboBox()
        self.return_reason_combo.addItems([
            self.tr("عيب في المنتج"),
            self.tr("خطأ في الطلب"),
            self.tr("عدم رضا العميل"),
            self.tr("منتج منتهي الصلاحية"),
            self.tr("تغيير رأي العميل"),
            self.tr("أخرى")
        ])
        self.return_reason_combo.setMinimumWidth(150)
        totals_layout.addWidget(self.return_reason_combo)

        totals_layout.addStretch()

        self.return_total_label = QLabel(self.tr("الإجمالي: 0.00 ريال"))
        self.return_total_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.return_total_label.setStyleSheet("color: #e74c3c;")
        totals_layout.addWidget(self.return_total_label)

        cart_layout.addLayout(totals_layout)

        cart_group.setLayout(cart_layout)
        layout.addWidget(cart_group)

        # ═══════════════════════════════════════════════════════════
        # أزرار الإجراءات
        # ═══════════════════════════════════════════════════════════
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(15)

        self.clear_return_cart_btn = QPushButton(self.tr("🗑️ إفراغ السلة"))
        self.clear_return_cart_btn.setMinimumHeight(50)
        self.clear_return_cart_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.clear_return_cart_btn.setStyleSheet("""
            QPushButton { background-color: #95a5a6; color: white; border-radius: 8px; }
            QPushButton:pressed { background-color: #7f8c8d; }
        """)
        self.clear_return_cart_btn.clicked.connect(self._clear_return_cart)
        actions_layout.addWidget(self.clear_return_cart_btn)

        self.process_manual_return_btn = QPushButton(self.tr("🔄 تنفيذ الإرجاع اليدوي"))
        self.process_manual_return_btn.setMinimumHeight(50)
        self.process_manual_return_btn.setFont(QFont("Arial", 14, QFont.Bold))
        self.process_manual_return_btn.setStyleSheet("""
            QPushButton { background-color: #e74c3c; color: white; border-radius: 8px; }
            QPushButton:pressed { background-color: #c0392b; }
        """)
        self.process_manual_return_btn.clicked.connect(self._process_manual_return)
        actions_layout.addWidget(self.process_manual_return_btn, 2)

        layout.addLayout(actions_layout)

        widget.setLayout(layout)
        self._load_categories_for_return()
        return widget

    # ═══════════════════════════════════════════════════════════════════════════
    # INVOICE RETURN METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def _search_invoice(self):
        """البحث عن الفاتورة"""
        invoice_number = self.invoice_number_input.text().strip()
        if not invoice_number:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("الرجاء إدخال رقم الفاتورة"))
            return

        try:
            cursor = db_manager.execute_query("""
                SELECT i.*, u.display_name as cashier_name
                FROM invoices i
                JOIN users u ON i.cashier_id = u.id
                WHERE i.invoice_number = ? AND i.type = 'sale'
            """, (invoice_number,))

            invoice = cursor.fetchone()

            if not invoice:
                QMessageBox.warning(self, self.tr("تحذير"), self.tr("لم يتم العثور على الفاتورة"))
                return

            self._display_invoice_info(invoice)
            self._load_invoice_items(invoice['id'])

            self.invoice_info_frame.setVisible(True)
            self.invoice_items_table.setVisible(True)
            self.process_return_btn.setVisible(True)

        except Exception as e:
            logger.error(f"خطأ في البحث عن الفاتورة: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr("حدث خطأ أثناء البحث عن الفاتورة"))

    def _display_invoice_info(self, invoice: dict):
        """عرض معلومات الفاتورة"""
        for i in reversed(range(self.invoice_info_layout.count())):
            self.invoice_info_layout.itemAt(i).widget().setParent(None)

        info_layout = QFormLayout()
        info_layout.addRow(self.tr("رقم الفاتورة:"), QLabel(str(invoice['invoice_number'])))
        info_layout.addRow(self.tr("التاريخ:"), QLabel(invoice['created_at']))
        info_layout.addRow(self.tr("الكاشير:"), QLabel(invoice['cashier_name']))
        info_layout.addRow(self.tr("الإجمالي:"), QLabel(f"{invoice['total']:.2f} {self.tr('ريال')}"))

        if invoice.get('table_number'):
            info_layout.addRow(self.tr("رقم الطاولة:"), QLabel(str(invoice['table_number'])))

        if invoice.get('customer_name'):
            info_layout.addRow(self.tr("اسم العميل:"), QLabel(invoice['customer_name']))

        self.invoice_info_layout.addLayout(info_layout)

    def _load_invoice_items(self, invoice_id: int):
        """تحميل عناصر الفاتورة"""
        try:
            cursor = db_manager.execute_query("""
                SELECT ii.*,
                       COALESCE(SUM(ri.quantity), 0) as returned_qty
                FROM invoice_items ii
                LEFT JOIN invoice_items ri ON ii.invoice_id = ri.original_invoice_id AND ii.product_id = ri.product_id
                WHERE ii.invoice_id = ?
                GROUP BY ii.id
            """, (invoice_id,))

            items = cursor.fetchall()

            self.invoice_items_table.setRowCount(len(items))
            self.invoice_items = items

            for i, item in enumerate(items):
                self.invoice_items_table.setItem(i, 0, QTableWidgetItem(item['product_name']))
                self.invoice_items_table.setItem(i, 1, QTableWidgetItem(f"{item['unit_price']:.2f}"))
                self.invoice_items_table.setItem(i, 2, QTableWidgetItem(str(int(item['quantity']))))
                self.invoice_items_table.setItem(i, 3, QTableWidgetItem(str(int(item['returned_qty']))))

                available_qty = item['quantity'] - item['returned_qty']
                self.invoice_items_table.setItem(i, 4, QTableWidgetItem(str(int(available_qty))))

                qty_spin = QSpinBox()
                qty_spin.setRange(0, int(available_qty))
                qty_spin.setValue(0)
                self.invoice_items_table.setCellWidget(i, 5, qty_spin)

                if available_qty <= 0:
                    for j in range(6):
                        item_widget = self.invoice_items_table.item(i, j)
                        if item_widget:
                            item_widget.setBackground(QColor(200, 200, 200))

        except Exception as e:
            logger.error(f"خطأ في تحميل عناصر الفاتورة: {e}")

    def _process_invoice_return(self):
        """معالجة الإرجاع من الفاتورة"""
        if not self.current_shift:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("يجب فتح وردية أولاً"))
            return

        return_items = []
        total_return = 0

        for i in range(self.invoice_items_table.rowCount()):
            qty_spin = self.invoice_items_table.cellWidget(i, 5)
            return_qty = qty_spin.value()

            if return_qty > 0:
                item = self.invoice_items[i]
                return_items.append({
                    'product_id': item['product_id'],
                    'product_name': item['product_name'],
                    'unit_price': item['unit_price'],
                    'quantity': return_qty,
                    'line_total': return_qty * item['unit_price']
                })
                total_return += return_qty * item['unit_price']

        if not return_items:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("الرجاء تحديد كمية للإرجاع"))
            return

        reply = QMessageBox.question(
            self,
            self.tr("تأكيد الإرجاع"),
            self.tr(f"إجمالي المرتجع: {total_return:.2f} ريال\nهل أنت متأكد من الإرجاع؟"),
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self._create_return_invoice(return_items, total_return)

    def _create_return_invoice(self, return_items: list, total_return: float, is_manual: bool = False, reason: str = ""):
        """إنشاء فاتورة مرتجع"""
        try:
            if is_manual:
                invoice_number = f"MR{datetime.now().strftime('%Y%m%d%H%M%S')}"
                original_invoice_id = None
            else:
                invoice_number = f"R{self.invoice_number_input.text().strip()}"
                original_invoice_id = self.invoice_number_input.text().strip()

            cursor = db_manager.execute_query(
                """
                INSERT INTO invoices (
                    invoice_number, type, subtotal, tax_amount, total,
                    paid_amount, status, cashier_id, shift_id, original_invoice_id,
                    notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_number,
                    'return',
                    total_return,
                    0,
                    total_return,
                    total_return,
                    'completed',
                    self.user_data['id'] if self.user_data else 1,
                    self.current_shift['id'] if self.current_shift else None,
                    original_invoice_id,
                    reason,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            )

            return_invoice_id = cursor.lastrowid

            for item in return_items:
                # جلب سعر التكلفة من المنتج
                cost_price = 0
                try:
                    cursor = db_manager.execute_query(
                        "SELECT cost_price FROM products WHERE id = ?", (item['product_id'],)
                    )
                    result = cursor.fetchone()
                    if result:
                        cost_price = result['cost_price'] or 0
                except:
                    pass

                db_manager.execute_query(
                    """
                    INSERT INTO invoice_items (
                        invoice_id, product_id, product_name, quantity,
                        unit_price, cost_price, tax_rate, line_total
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        return_invoice_id,
                        item['product_id'],
                        item['product_name'],
                        -item['quantity'],
                        item['unit_price'],
                        cost_price,
                        0.15, # Default tax rate for manual returns (can be improved to fetch from settings)
                        -item['line_total']
                    )
                )

                db_manager.execute_query(
                    "UPDATE products SET quantity = quantity + ? WHERE id = ?",
                    (item['quantity'], item['product_id'])
                )

                self._return_ingredients(item['product_id'], item['quantity'])

            if self.current_shift:
                db_manager.execute_query(
                    "UPDATE shifts SET total_returns = total_returns + ? WHERE id = ?",
                    (total_return, self.current_shift['id'])
                )

            db_manager.commit()

            # إرسال إشعار تليجرام
            try:
                from src.utils.telegram import get_telegram_manager
                telegram = get_telegram_manager()
                telegram.send_return_alert({
                    'original_invoice': original_invoice_id or self.tr("يدوي"),
                    'amount': total_return,
                    'reason': reason or self.tr("بدون سبب"),
                    'user': self.user_data.get('display_name', '') if self.user_data else self.tr("غير معروف")
                })
            except Exception as e:
                logger.warning(f"فشل إرسال إشعار التليجرام: {e}")

            QMessageBox.information(
                self,
                self.tr("نجاح"),
                self.tr(f"تم إنشاء فاتورة مرتجع بنجاح\nرقم الفاتورة: {invoice_number}\nالإجمالي: {total_return:.2f} ريال")
            )

            try:
                if not is_manual:
                    self._search_invoice()
                else:
                    self._clear_return_cart()
            except Exception as e:
                logger.error(f"خطأ في تحديث الواجهة بعد الإرجاع: {e}")

        except Exception as e:
            db_manager.rollback()
            logger.error(f"خطأ في إنشاء فاتورة المرتجع: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr("حدث خطأ أثناء معالجة الإرجاع"))

    def _return_ingredients(self, product_id: int, quantity: float):
        """إعادة المكونات للمخزون"""
        try:
            cursor = db_manager.execute_query(
                "SELECT ingredient_id, quantity_needed FROM recipes WHERE product_id = ?",
                (product_id,)
            )
            recipe_items = cursor.fetchall()

            for recipe_item in recipe_items:
                returned_quantity = recipe_item['quantity_needed'] * quantity
                db_manager.execute_query(
                    "UPDATE ingredients SET quantity = quantity + ? WHERE id = ?",
                    (returned_quantity, recipe_item['ingredient_id'])
                )

        except Exception as e:
            logger.error(f"خطأ في إعادة المكونات: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # MANUAL RETURN METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def _load_categories_for_return(self):
        """تحميل الفئات للإرجاع اليدوي"""
        try:
            cursor = db_manager.execute_query(
                "SELECT * FROM categories WHERE is_active = 1 ORDER BY display_order"
            )
            categories = cursor.fetchall()

            self.categories_list.clear()
            self.categories_data = {}

            for cat in categories:
                self.categories_list.addItem(cat['name'])
                self.categories_data[cat['name']] = cat['id']

        except Exception as e:
            logger.error(f"خطأ في تحميل الفئات: {e}")

    def _select_category_for_return(self, item):
        """اختيار فئة للإرجاع اليدوي"""
        category_name = item.text()
        self.selected_category_id = self.categories_data.get(category_name)
        self._load_products_for_return(self.selected_category_id)

    def _load_products_for_return(self, category_id: int):
        """تحميل المنتجات حسب الفئة"""
        # مسح المنتجات السابقة
        while self.products_grid.count():
            child = self.products_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        try:
            cursor = db_manager.execute_query("""
                SELECT id, name, selling_price FROM products
                WHERE category_id = ? AND is_active = 1
                ORDER BY name
            """, (category_id,))

            products = cursor.fetchall()

            row, col = 0, 0
            for product in products:
                btn = QPushButton(f"{product['name']}\n{product['selling_price']:.2f} ر.س")
                btn.setMinimumSize(120, 80)
                btn.setFont(QFont("Arial", 10, QFont.Bold))
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3498db;
                        color: white;
                        border-radius: 8px;
                        padding: 5px;
                    }
                    QPushButton:pressed {
                        background-color: #2980b9;
                    }
                """)
                btn.clicked.connect(lambda _, p=product: self._add_to_return_cart(p))
                self.products_grid.addWidget(btn, row, col)

                col += 1
                if col >= 4:
                    col = 0
                    row += 1

        except Exception as e:
            logger.error(f"خطأ في تحميل المنتجات: {e}")

    def _add_to_return_cart(self, product: dict):
        """إضافة منتج لسلة المرتجعات"""
        # التحقق من وجود المنتج في السلة
        for item in self.manual_return_cart:
            if item['product_id'] == product['id']:
                item['quantity'] += 1
                item['line_total'] = item['quantity'] * item['unit_price']
                self._update_return_cart_display()
                return

        # إضافة منتج جديد
        self.manual_return_cart.append({
            'product_id': product['id'],
            'product_name': product['name'],
            'unit_price': product['selling_price'],
            'quantity': 1,
            'line_total': product['selling_price']
        })
        self._update_return_cart_display()

    def _update_return_cart_display(self):
        """تحديث عرض سلة المرتجعات"""
        self.return_cart_table.setRowCount(len(self.manual_return_cart))
        total = 0

        for i, item in enumerate(self.manual_return_cart):
            self.return_cart_table.setItem(i, 0, QTableWidgetItem(item['product_name']))
            self.return_cart_table.setItem(i, 1, QTableWidgetItem(f"{item['unit_price']:.2f}"))

            # سبينر للكمية
            qty_spin = QSpinBox()
            qty_spin.setRange(1, 100)
            qty_spin.setValue(item['quantity'])
            qty_spin.valueChanged.connect(lambda v, idx=i: self._update_cart_item_qty(idx, v))
            self.return_cart_table.setCellWidget(i, 2, qty_spin)

            self.return_cart_table.setItem(i, 3, QTableWidgetItem(f"{item['line_total']:.2f}"))

            # زر الحذف
            del_btn = QPushButton("🗑️")
            del_btn.setStyleSheet("background-color: #e74c3c; color: white;")
            del_btn.clicked.connect(lambda _, idx=i: self._remove_from_cart(idx))
            self.return_cart_table.setCellWidget(i, 4, del_btn)

            total += item['line_total']

        self.return_total_label.setText(self.tr(f"الإجمالي: {total:.2f} ريال"))

    def _update_cart_item_qty(self, index: int, qty: int):
        """تحديث كمية عنصر في السلة"""
        if 0 <= index < len(self.manual_return_cart):
            self.manual_return_cart[index]['quantity'] = qty
            self.manual_return_cart[index]['line_total'] = qty * self.manual_return_cart[index]['unit_price']
            self._update_return_cart_display()

    def _remove_from_cart(self, index: int):
        """حذف عنصر من السلة"""
        if 0 <= index < len(self.manual_return_cart):
            del self.manual_return_cart[index]
            self._update_return_cart_display()

    def _clear_return_cart(self):
        """إفراغ سلة المرتجعات"""
        self.manual_return_cart = []
        self._update_return_cart_display()

    def _process_manual_return(self):
        """معالجة الإرجاع اليدوي"""
        if not self.manual_return_cart:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("سلة المرتجعات فارغة"))
            return

        if not self.current_shift:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("يجب فتح وردية أولاً"))
            return

        total = sum(item['line_total'] for item in self.manual_return_cart)
        reason = self.return_reason_combo.currentText()

        reply = QMessageBox.question(
            self,
            self.tr("تأكيد الإرجاع اليدوي"),
            self.tr(f"إجمالي المرتجع: {total:.2f} ريال\nالسبب: {reason}\n\nهل أنت متأكد من تنفيذ الإرجاع؟"),
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self._create_return_invoice(self.manual_return_cart, total, is_manual=True, reason=reason)
