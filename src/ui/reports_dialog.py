"""
التقارير
Reports Dialog
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QGroupBox, QFormLayout, QDateEdit,
    QComboBox, QMessageBox, QAbstractItemView, QHeaderView, QLabel,
    QTextEdit, QFileDialog, QWidget, QCheckBox
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QColor
from loguru import logger

from database import db_manager

# استيراد مكتبة Rust للحسابات السريعة (مع fallback للـ Python)
try:
    from pos_calc import calculate_sales_summary, calculate_statistics, analyze_inventory
    USE_RUST_CALC = True
    logger.info("تم تحميل مكتبة pos_calc (Rust) بنجاح")
except ImportError:
    USE_RUST_CALC = False
    logger.info("مكتبة pos_calc غير متوفرة، سيتم استخدام Python")


class ReportsDialog(QDialog):
    """نافذة التقارير"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("التقارير"))
        self.setMinimumSize(900, 700)
        self._setup_ui()

    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        layout = QVBoxLayout()

        # التبويبات
        tabs = QTabWidget()

        # تبويب تقرير المبيعات
        sales_tab = self._create_sales_report_tab()
        tabs.addTab(sales_tab, self.tr("تقرير المبيعات"))

        # تبويب تقرير المخزون
        inventory_tab = self._create_inventory_report_tab()
        tabs.addTab(inventory_tab, self.tr("تقرير المخزون"))

        # تبويب تقرير الورديات
        shifts_tab = self._create_shifts_report_tab()
        tabs.addTab(shifts_tab, self.tr("تقرير الورديات"))

        layout.addWidget(tabs)
        self.setLayout(layout)

    def _create_sales_report_tab(self):
        """إنشاء تبويب تقرير المبيعات"""
        widget = QWidget()
        layout = QVBoxLayout()

        # أدوات التحكم
        controls_layout = QHBoxLayout()

        controls_layout.addWidget(QLabel(self.tr("من:")))
        self.from_date = QDateEdit()
        self.from_date.setDate(QDate.currentDate())
        self.from_date.setCalendarPopup(True)
        self.from_date.setMinimumHeight(35)
        controls_layout.addWidget(self.from_date)

        controls_layout.addWidget(QLabel(self.tr("إلى:")))
        self.to_date = QDateEdit()
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setCalendarPopup(True)
        self.to_date.setMinimumHeight(35)
        controls_layout.addWidget(self.to_date)

        self.generate_sales_btn = QPushButton(self.tr("📊 إنشاء التقرير"))
        self.generate_sales_btn.setMinimumHeight(40)
        self.generate_sales_btn.clicked.connect(self._generate_sales_report)
        controls_layout.addWidget(self.generate_sales_btn)

        self.export_sales_btn = QPushButton(self.tr("📤 تصدير Excel"))
        self.export_sales_btn.setMinimumHeight(40)
        self.export_sales_btn.clicked.connect(self._export_sales_report)
        controls_layout.addWidget(self.export_sales_btn)

        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        # ملخص التقرير
        self.sales_summary = QGroupBox(self.tr("ملخص التقرير"))
        self.sales_summary.setFont(QFont("Arial", 11, QFont.Bold))
        summary_layout = QVBoxLayout()

        self.total_sales_label = QLabel(self.tr("إجمالي المبيعات: 0.00 ريال"))
        self.total_sales_label.setFont(QFont("Arial", 12))
        summary_layout.addWidget(self.total_sales_label)

        self.total_invoices_label = QLabel(self.tr("عدد الفواتير: 0"))
        summary_layout.addWidget(self.total_invoices_label)

        self.total_tax_label = QLabel(self.tr("إجمالي الضريبة: 0.00 ريال"))
        summary_layout.addWidget(self.total_tax_label)

        self.sales_summary.setLayout(summary_layout)
        layout.addWidget(self.sales_summary)

        # جدول التفاصيل
        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(6)
        self.sales_table.setHorizontalHeaderLabels([
            self.tr("رقم الفاتورة"),
            self.tr("التاريخ"),
            self.tr("الإجمالي"),
            self.tr("الضريبة"),
            self.tr("الكاشير"),
            self.tr("الحالة")
        ])
        self.sales_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sales_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        layout.addWidget(self.sales_table)

        widget.setLayout(layout)
        return widget

    def _create_inventory_report_tab(self):
        """إنشاء تبويب تقرير المخزون"""
        widget = QWidget()
        layout = QVBoxLayout()

        # أدوات التحكم
        controls_layout = QHBoxLayout()

        self.low_stock_only_check = QCheckBox(self.tr("المنتجات منخفضة المخزون فقط"))
        controls_layout.addWidget(self.low_stock_only_check)

        self.generate_inventory_btn = QPushButton(self.tr("📊 إنشاء التقرير"))
        self.generate_inventory_btn.setMinimumHeight(40)
        self.generate_inventory_btn.clicked.connect(self._generate_inventory_report)
        controls_layout.addWidget(self.generate_inventory_btn)

        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        # جدول المخزون
        self.inventory_table = QTableWidget()
        self.inventory_table.setColumnCount(7)
        self.inventory_table.setHorizontalHeaderLabels([
            self.tr("المنتج"),
            self.tr("الفئة"),
            self.tr("الكمية الحالية"),
            self.tr("الحد الأدنى"),
            self.tr("سعر البيع"),
            self.tr("الحالة"),
            self.tr("القيمة الإجمالية")
        ])
        self.inventory_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.inventory_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        layout.addWidget(self.inventory_table)

        widget.setLayout(layout)
        self._generate_inventory_report()
        return widget

    def _create_shifts_report_tab(self):
        """إنشاء تبويب تقرير الورديات"""
        widget = QWidget()
        layout = QVBoxLayout()

        # أدوات التحكم
        controls_layout = QHBoxLayout()

        controls_layout.addWidget(QLabel(self.tr("من:")))
        self.shifts_from_date = QDateEdit()
        self.shifts_from_date.setDate(QDate.currentDate().addDays(-7))
        self.shifts_from_date.setCalendarPopup(True)
        controls_layout.addWidget(self.shifts_from_date)

        controls_layout.addWidget(QLabel(self.tr("إلى:")))
        self.shifts_to_date = QDateEdit()
        self.shifts_to_date.setDate(QDate.currentDate())
        self.shifts_to_date.setCalendarPopup(True)
        controls_layout.addWidget(self.shifts_to_date)

        self.generate_shifts_btn = QPushButton(self.tr("📊 إنشاء التقرير"))
        self.generate_shifts_btn.setMinimumHeight(40)
        self.generate_shifts_btn.clicked.connect(self._generate_shifts_report)
        controls_layout.addWidget(self.generate_shifts_btn)

        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        # جدول الورديات
        self.shifts_table = QTableWidget()
        self.shifts_table.setColumnCount(8)
        self.shifts_table.setHorizontalHeaderLabels([
            self.tr("رقم الوردية"),
            self.tr("الكاشير"),
            self.tr("بداية الوردية"),
            self.tr("نهاية الوردية"),
            self.tr("المبيعات"),
            self.tr("المرتجعات"),
            self.tr("الإيداعات"),
            self.tr("السحوبات")
        ])
        self.shifts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.shifts_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        layout.addWidget(self.shifts_table)

        widget.setLayout(layout)
        self._generate_shifts_report()
        return widget

    def _generate_sales_report(self):
        """إنشاء تقرير المبيعات"""
        try:
            from_date = self.from_date.date().toString("yyyy-MM-dd")
            to_date = self.to_date.date().toString("yyyy-MM-dd")

            cursor = db_manager.execute_query("""
                SELECT i.*, u.display_name as cashier_name
                FROM invoices i
                JOIN users u ON i.cashier_id = u.id
                WHERE i.type = 'sale' AND DATE(i.created_at) BETWEEN ? AND ?
                ORDER BY i.created_at DESC
            """, (from_date, to_date))

            invoices = cursor.fetchall()

            # تحديث الملخص - استخدام Rust إن توفر
            if USE_RUST_CALC:
                # تحويل الفواتير لقائمة قواميس لـ Rust
                invoices_list = [dict(inv) for inv in invoices]
                summary = calculate_sales_summary(invoices_list)
                total_sales = summary['total_sales']
                total_tax = summary['total_tax']
            else:
                # الحساب بـ Python (fallback)
                total_sales = sum(inv['total'] for inv in invoices)
                total_tax = sum(inv['tax_amount'] for inv in invoices)

            self.total_sales_label.setText(f"{self.tr('إجمالي المبيعات')}: {total_sales:.2f} {self.tr('ريال')}")
            self.total_invoices_label.setText(f"{self.tr('عدد الفواتير')}: {len(invoices)}")
            self.total_tax_label.setText(f"{self.tr('إجمالي الضريبة')}: {total_tax:.2f} {self.tr('ريال')}")

            # تحديث الجدول
            self.sales_table.setRowCount(len(invoices))

            for i, invoice in enumerate(invoices):
                self.sales_table.setItem(i, 0, QTableWidgetItem(str(invoice['invoice_number'])))
                self.sales_table.setItem(i, 1, QTableWidgetItem(invoice['created_at']))
                self.sales_table.setItem(i, 2, QTableWidgetItem(f"{invoice['total']:.2f}"))
                self.sales_table.setItem(i, 3, QTableWidgetItem(f"{invoice['tax_amount']:.2f}"))
                self.sales_table.setItem(i, 4, QTableWidgetItem(invoice['cashier_name']))
                self.sales_table.setItem(i, 5, QTableWidgetItem(self.tr("مكتملة") if invoice['status'] == 'completed' else self.tr("معلقة")))

        except Exception as e:
            logger.error(f"خطأ في إنشاء تقرير المبيعات: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr("حدث خطأ أثناء إنشاء التقرير"))


    def _generate_inventory_report(self):
        """إنشاء تقرير المخزون"""
        try:
            low_stock_only = self.low_stock_only_check.isChecked()

            if low_stock_only:
                query = """
                    SELECT p.*, c.name as category_name
                    FROM products p
                    LEFT JOIN categories c ON p.category_id = c.id
                    WHERE p.quantity <= p.min_alert_level AND p.is_active = 1
                    ORDER BY p.name
                """
            else:
                query = """
                    SELECT p.*, c.name as category_name
                    FROM products p
                    LEFT JOIN categories c ON p.category_id = c.id
                    WHERE p.is_active = 1
                    ORDER BY p.name
                """

            cursor = db_manager.execute_query(query)
            products = cursor.fetchall()

            self.inventory_table.setRowCount(len(products))

            for i, product in enumerate(products):
                self.inventory_table.setItem(i, 0, QTableWidgetItem(product['name']))
                self.inventory_table.setItem(i, 1, QTableWidgetItem(product['category_name'] or ''))
                self.inventory_table.setItem(i, 2, QTableWidgetItem(f"{product['quantity']:.0f}"))
                self.inventory_table.setItem(i, 3, QTableWidgetItem(f"{product['min_alert_level']:.0f}"))
                self.inventory_table.setItem(i, 4, QTableWidgetItem(f"{product['selling_price']:.2f}"))
                self.inventory_table.setItem(i, 5, QTableWidgetItem(self.tr("نشط") if product['is_active'] else self.tr("غير نشط")))

                total_value = product['quantity'] * product['selling_price']
                self.inventory_table.setItem(i, 6, QTableWidgetItem(f"{total_value:.2f}"))

                # تلوين المنتجات منخفضة المخزون
                if product['quantity'] <= product['min_alert_level']:
                    for j in range(7):
                        self.inventory_table.item(i, j).setBackground(QColor(255, 200, 200))

        except Exception as e:
            logger.error(f"خطأ في إنشاء تقرير المخزون: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr("حدث خطأ أثناء إنشاء التقرير"))

    def _generate_shifts_report(self):
        """إنشاء تقرير الورديات"""
        try:
            from_date = self.shifts_from_date.date().toString("yyyy-MM-dd")
            to_date = self.shifts_to_date.date().toString("yyyy-MM-dd")

            cursor = db_manager.execute_query("""
                SELECT s.*, u.display_name as cashier_name
                FROM shifts s
                JOIN users u ON s.cashier_id = u.id
                WHERE DATE(s.start_time) BETWEEN ? AND ?
                ORDER BY s.start_time DESC
            """, (from_date, to_date))

            shifts = cursor.fetchall()

            self.shifts_table.setRowCount(len(shifts))

            for i, shift in enumerate(shifts):
                self.shifts_table.setItem(i, 0, QTableWidgetItem(f"#{shift['shift_number']}"))
                self.shifts_table.setItem(i, 1, QTableWidgetItem(shift['cashier_name']))
                self.shifts_table.setItem(i, 2, QTableWidgetItem(shift['start_time']))
                self.shifts_table.setItem(i, 3, QTableWidgetItem(shift['end_time'] or ''))
                self.shifts_table.setItem(i, 4, QTableWidgetItem(f"{shift['total_sales']:.2f}"))
                self.shifts_table.setItem(i, 5, QTableWidgetItem(f"{shift['total_returns']:.2f}"))
                self.shifts_table.setItem(i, 6, QTableWidgetItem(f"{shift['total_deposits']:.2f}"))
                self.shifts_table.setItem(i, 7, QTableWidgetItem(f"{shift['total_withdrawals']:.2f}"))

        except Exception as e:
            logger.error(f"خطأ في إنشاء تقرير الورديات: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr("حدث خطأ أثناء إنشاء التقرير"))

    def _export_sales_report(self):
        """تصدير تقرير المبيعات إلى Excel"""
        try:
            import csv

            filename, _ = QFileDialog.getSaveFileName(
                self, self.tr("حفظ التقرير"),
                f"sales_report_{QDate.currentDate().toString('yyyy-MM-dd')}.csv",
                "CSV Files (*.csv)"
            )

            if not filename:
                return

            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)

                # الرأس
                headers = ['رقم الفاتورة', 'التاريخ', 'الإجمالي', 'الضريبة', 'الكاشير', 'الحالة']
                writer.writerow(headers)

                # البيانات
                for row in range(self.sales_table.rowCount()):
                    row_data = [
                        self.sales_table.item(row, col).text()
                        for col in range(self.sales_table.columnCount())
                    ]
                    writer.writerow(row_data)

            QMessageBox.information(self, self.tr("نجاح"), self.tr(f"تم تصدير التقرير إلى:\n{filename}"))

        except Exception as e:
            logger.error(f"خطأ في تصدير التقرير: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr("حدث خطأ أثناء التصدير"))
