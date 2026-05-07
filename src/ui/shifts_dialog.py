"""
إدارة الورديات
Shifts Management Dialog
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QGroupBox, QFormLayout, QDoubleSpinBox,
    QTextEdit, QMessageBox, QInputDialog, QAbstractItemView, QHeaderView,
    QLabel, QFrame, QWidget, QLineEdit, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from datetime import datetime
from loguru import logger

from database import db_manager, get_current_shift


class ShiftsDialog(QDialog):
    """نافذة إدارة الورديات"""

    shift_opened = pyqtSignal()
    shift_closed = pyqtSignal()

    def __init__(self, parent=None, user_data: dict = None):
        super().__init__(parent)
        self.user_data = user_data
        self.setWindowTitle(self.tr("إدارة الورديات"))
        self.setMinimumSize(800, 600)
        self._setup_ui()

    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        layout = QVBoxLayout()

        # التبويبات
        tabs = QTabWidget()

        # تبويب الوردية الحالية
        current_tab = self._create_current_shift_tab()
        tabs.addTab(current_tab, self.tr("الوردية الحالية"))

        # تبويب سجل الورديات
        history_tab = self._create_shift_history_tab()
        tabs.addTab(history_tab, self.tr("سجل الورديات"))

        # تبويب الحركات النقدية
        cash_movements_tab = self._create_cash_movements_tab()
        tabs.addTab(cash_movements_tab, self.tr("الحركات النقدية"))

        layout.addWidget(tabs)
        self.setLayout(layout)

        self._update_current_shift_display()

    def _create_current_shift_tab(self):
        """إنشاء تبويب الوردية الحالية"""
        widget = QWidget()
        layout = QVBoxLayout()

        # معلومات الوردية
        self.shift_info_frame = QFrame()
        self.shift_info_frame.setFrameShape(QFrame.Box)
        self.shift_info_frame.setStyleSheet("background-color: #f8f9fa;")

        self.shift_info_layout = QVBoxLayout()
        # ملاحظة: سيتم تحديث العرض لاحقاً بعد إنشاء الأزرار

        self.shift_info_frame.setLayout(self.shift_info_layout)
        layout.addWidget(self.shift_info_frame)

        # أزرار التحكم
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self.open_shift_btn = QPushButton(self.tr("📖 فتح وردية جديدة"))
        self.open_shift_btn.setMinimumHeight(50)
        self.open_shift_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.open_shift_btn.clicked.connect(self._open_shift_dialog)
        buttons_layout.addWidget(self.open_shift_btn)

        self.close_shift_btn = QPushButton(self.tr("🔒 إغلاق الوردية"))
        self.close_shift_btn.setMinimumHeight(50)
        self.close_shift_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.close_shift_btn.clicked.connect(self._close_shift_dialog)
        buttons_layout.addWidget(self.close_shift_btn)

        layout.addLayout(buttons_layout)

        # أزرار الحركات النقدية السريعة
        cash_buttons_layout = QHBoxLayout()
        cash_buttons_layout.setSpacing(8)

        self.quick_deposit_btn = QPushButton(self.tr("💰 إيداع"))
        self.quick_deposit_btn.setMinimumHeight(45)
        self.quick_deposit_btn.setFont(QFont("Arial", 11))
        self.quick_deposit_btn.setStyleSheet("background-color: #27ae60; color: white; border-radius: 5px;")
        self.quick_deposit_btn.clicked.connect(lambda: self._cash_movement_dialog('deposit'))
        cash_buttons_layout.addWidget(self.quick_deposit_btn)

        self.quick_withdrawal_btn = QPushButton(self.tr("💸 سحب"))
        self.quick_withdrawal_btn.setMinimumHeight(45)
        self.quick_withdrawal_btn.setFont(QFont("Arial", 11))
        self.quick_withdrawal_btn.setStyleSheet("background-color: #3498db; color: white; border-radius: 5px;")
        self.quick_withdrawal_btn.clicked.connect(lambda: self._cash_movement_dialog('withdrawal'))
        cash_buttons_layout.addWidget(self.quick_withdrawal_btn)

        self.quick_expense_btn = QPushButton(self.tr("🧾 مصروف"))
        self.quick_expense_btn.setMinimumHeight(45)
        self.quick_expense_btn.setFont(QFont("Arial", 11))
        self.quick_expense_btn.setStyleSheet("background-color: #e74c3c; color: white; border-radius: 5px;")
        self.quick_expense_btn.clicked.connect(lambda: self._cash_movement_dialog('expense'))
        cash_buttons_layout.addWidget(self.quick_expense_btn)

        layout.addLayout(cash_buttons_layout)

        widget.setLayout(layout)
        return widget

    def _create_shift_history_tab(self):
        """إنشاء تبويب سجل الورديات"""
        widget = QWidget()
        layout = QVBoxLayout()

        # جدول الورديات
        self.shifts_table = QTableWidget()
        self.shifts_table.setColumnCount(9)
        self.shifts_table.setHorizontalHeaderLabels([
            self.tr("رقم الوردية"),
            self.tr("الكاشير"),
            self.tr("بداية الوردية"),
            self.tr("نهاية الوردية"),
            self.tr("الحالة"),
            self.tr("المبيعات"),
            self.tr("المرتجعات"),
            self.tr("المتوقع"),
            self.tr("الفعلي")
        ])
        self.shifts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.shifts_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        layout.addWidget(self.shifts_table)

        widget.setLayout(layout)
        self._load_shift_history()
        return widget

    def _create_cash_movements_tab(self):
        """إنشاء تبويب الحركات النقدية"""
        widget = QWidget()
        layout = QVBoxLayout()

        # أزرار التحكم
        controls_layout = QHBoxLayout()

        self.deposit_btn = QPushButton(self.tr("💰 إيداع"))
        self.deposit_btn.setMinimumHeight(40)
        self.deposit_btn.clicked.connect(lambda: self._cash_movement_dialog('deposit'))
        controls_layout.addWidget(self.deposit_btn)

        self.withdrawal_btn = QPushButton(self.tr("💸 سحب"))
        self.withdrawal_btn.setMinimumHeight(40)
        self.withdrawal_btn.clicked.connect(lambda: self._cash_movement_dialog('withdrawal'))
        controls_layout.addWidget(self.withdrawal_btn)

        self.expense_btn = QPushButton(self.tr("🧾 مصروف"))
        self.expense_btn.setMinimumHeight(40)
        self.expense_btn.clicked.connect(lambda: self._cash_movement_dialog('expense'))
        controls_layout.addWidget(self.expense_btn)

        layout.addLayout(controls_layout)

        # جدول الحركات
        self.movements_table = QTableWidget()
        self.movements_table.setColumnCount(6)
        self.movements_table.setHorizontalHeaderLabels([
            self.tr("النوع"),
            self.tr("المبلغ"),
            self.tr("السبب"),
            self.tr("التصنيف"),
            self.tr("الوقت"),
            self.tr("المستخدم")
        ])
        self.movements_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.movements_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        layout.addWidget(self.movements_table)

        widget.setLayout(layout)
        self._load_cash_movements()
        return widget

    def _update_current_shift_display(self):
        """تحديث عرض الوردية الحالية"""
        # مسح المحتوى السابق بشكل آمن
        for i in reversed(range(self.shift_info_layout.count())):
            item = self.shift_info_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()
                elif item.layout():
                    # إذا كان layout فرعي، نمسح محتوياته
                    sub_layout = item.layout()
                    while sub_layout.count():
                        sub_item = sub_layout.takeAt(0)
                        if sub_item.widget():
                            sub_item.widget().deleteLater()
                    self.shift_info_layout.removeItem(item)

        shift = get_current_shift()

        if shift:
            # وردية مفتوحة
            status_label = QLabel(self.tr("🟢 وردية مفتوحة"))
            status_label.setFont(QFont("Arial", 16, QFont.Bold))
            status_label.setStyleSheet("color: #27ae60;")
            self.shift_info_layout.addWidget(status_label)

            info_layout = QFormLayout()
            info_layout.setSpacing(10)

            info_layout.addRow(self.tr("رقم الوردية:"), QLabel(f"#{shift['shift_number']}"))
            info_layout.addRow(self.tr("الكاشير:"), QLabel(shift['display_name']))
            info_layout.addRow(self.tr("وقت البدء:"), QLabel(shift['start_time']))
            info_layout.addRow(self.tr("الرصيد الافتتاحي:"), QLabel(f"{shift['starting_amount']:.2f} {self.tr('ريال')}"))
            info_layout.addRow(self.tr("إجمالي المبيعات:"), QLabel(f"{shift['total_sales']:.2f} {self.tr('ريال')}"))

            # Payment method breakdown for current shift
            delivery_app_sales = 0
            try:
                cursor = db_manager.execute_query("""
                    SELECT p.payment_method, SUM(p.amount) as total
                    FROM payments p
                    JOIN invoices i ON p.invoice_id = i.id
                    WHERE i.shift_id = ? AND i.type = 'sale' AND i.status = 'completed'
                    GROUP BY p.payment_method
                """, (shift['id'],))
                payment_results = cursor.fetchall()
                method_names = {
                    'cash': self.tr('نقداً'),
                    'card': self.tr('بطاقة'),
                    'transfer': self.tr('تحويل'),
                    'delivery_app': self.tr('توصيل (لا تُحسب)'),
                    'multi': self.tr('متعدد')
                }
                for row in payment_results:
                    method = row['payment_method']
                    amount = row['total']
                    label = method_names.get(method, method)
                    info_layout.addRow(f"  ↳ {label}:", QLabel(f"{amount:.2f} {self.tr('ريال')}"))
                    if method == 'delivery_app':
                        delivery_app_sales = amount
            except Exception as e:
                logger.error(f"Error getting payment breakdown: {e}")

            info_layout.addRow(self.tr("إجمالي المرتجعات:"), QLabel(f"{shift['total_returns']:.2f} {self.tr('ريال')}"))
            info_layout.addRow(self.tr("إجمالي الإيداعات:"), QLabel(f"{shift['total_deposits']:.2f} {self.tr('ريال')}"))
            info_layout.addRow(self.tr("إجمالي السحوبات:"), QLabel(f"{shift['total_withdrawals']:.2f} {self.tr('ريال')}"))

            # استبعاد مبيعات تطبيقات التوصيل من المتوقع في الخزينة
            expected = shift['starting_amount'] + shift['total_sales'] - delivery_app_sales - shift['total_returns'] + shift['total_deposits'] - shift['total_withdrawals']
            info_layout.addRow(self.tr("المتوقع في الخزينة:"), QLabel(f"{expected:.2f} {self.tr('ريال')}"))

            # صافي الخزينة = المتوقع - الرصيد الافتتاحي - مبيعات البطاقة
            card_sales = 0
            for row in payment_results:
                if row['payment_method'] == 'card':
                    card_sales = row['total']
                    break
            net_treasury = expected - shift['starting_amount'] - card_sales
            net_label = QLabel(f"{net_treasury:.2f} {self.tr('ريال')}")
            net_label.setStyleSheet("color: #9b59b6; font-weight: bold;")
            info_layout.addRow(self.tr("صافي الخزينة (نقداً فقط):"), net_label)

            self.shift_info_layout.addLayout(info_layout)

            # تحديث حالة الأزرار
            self.open_shift_btn.setEnabled(False)
            self.close_shift_btn.setEnabled(True)

        else:
            # لا توجد وردية مفتوحة
            status_label = QLabel(self.tr("🔴 لا توجد وردية مفتوحة"))
            status_label.setFont(QFont("Arial", 16, QFont.Bold))
            status_label.setStyleSheet("color: #e74c3c;")
            self.shift_info_layout.addWidget(status_label)

            message_label = QLabel(self.tr("يجب فتح وردية جديدة قبل البدء في العمل"))
            message_label.setAlignment(Qt.AlignCenter)
            message_label.setStyleSheet("color: #666;")
            self.shift_info_layout.addWidget(message_label)

            # تحديث حالة الأزرار
            self.open_shift_btn.setEnabled(True)
            self.close_shift_btn.setEnabled(False)

    def _load_shift_history(self):
        """تحميل سجل الورديات"""
        try:
            cursor = db_manager.execute_query("""
                SELECT s.*, u.display_name as cashier_name
                FROM shifts s
                JOIN users u ON s.cashier_id = u.id
                ORDER BY s.start_time DESC
                LIMIT 50
            """)
            shifts = cursor.fetchall()

            self.shifts_table.setRowCount(len(shifts))

            for i, shift in enumerate(shifts):
                self.shifts_table.setItem(i, 0, QTableWidgetItem(f"#{shift['shift_number']}"))
                self.shifts_table.setItem(i, 1, QTableWidgetItem(shift['cashier_name']))
                self.shifts_table.setItem(i, 2, QTableWidgetItem(shift['start_time']))
                self.shifts_table.setItem(i, 3, QTableWidgetItem(shift['end_time'] or ''))
                self.shifts_table.setItem(i, 4, QTableWidgetItem(self.tr("مفتوحة") if shift['status'] == 'open' else self.tr("مغلقة")))
                self.shifts_table.setItem(i, 5, QTableWidgetItem(f"{shift['total_sales']:.2f}"))
                self.shifts_table.setItem(i, 6, QTableWidgetItem(f"{shift['total_returns']:.2f}"))
                self.shifts_table.setItem(i, 7, QTableWidgetItem(f"{shift['expected_amount']:.2f}"))
                self.shifts_table.setItem(i, 8, QTableWidgetItem(f"{shift['actual_amount'] or 0:.2f}"))

                # تلوين الورديات المفتوحة
                if shift['status'] == 'open':
                    for j in range(9):
                        self.shifts_table.item(i, j).setBackground(QColor(200, 255, 200))

        except Exception as e:
            logger.error(f"خطأ في تحميل سجل الورديات: {e}")

    def _load_cash_movements(self):
        """تحميل الحركات النقدية"""
        try:
            current_shift = get_current_shift()
            if not current_shift:
                return

            cursor = db_manager.execute_query("""
                SELECT cm.*, u.display_name as user_name
                FROM cash_movements cm
                JOIN users u ON cm.user_id = u.id
                WHERE cm.shift_id = ?
                ORDER BY cm.created_at DESC
            """, (current_shift['id'],))

            movements = cursor.fetchall()

            self.movements_table.setRowCount(len(movements))

            type_names = {
                'deposit': self.tr("إيداع"),
                'withdrawal': self.tr("سحب"),
                'expense': self.tr("مصروف")
            }

            for i, movement in enumerate(movements):
                self.movements_table.setItem(i, 0, QTableWidgetItem(type_names.get(movement['type'], movement['type'])))
                self.movements_table.setItem(i, 1, QTableWidgetItem(f"{movement['amount']:.2f}"))
                self.movements_table.setItem(i, 2, QTableWidgetItem(movement['reason']))
                self.movements_table.setItem(i, 3, QTableWidgetItem(movement['category']))
                self.movements_table.setItem(i, 4, QTableWidgetItem(movement['created_at']))
                self.movements_table.setItem(i, 5, QTableWidgetItem(movement['user_name']))

        except Exception as e:
            logger.error(f"خطأ في تحميل الحركات النقدية: {e}")

    def _open_shift_dialog(self):
        """فتح نافذة فتح وردية جديدة"""
        dialog = OpenShiftDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            starting_amount = dialog.starting_amount
            notes = dialog.notes
            employee_name = dialog.employee_name

            try:
                # الحصول على رقم الوردية التالي
                cursor = db_manager.execute_query("SELECT COALESCE(MAX(shift_number), 0) + 1 FROM shifts")
                next_number = cursor.fetchone()[0]

                # فتح الوردية
                db_manager.execute_query(
                    """
                    INSERT INTO shifts (shift_number, cashier_id, starting_amount, start_time, status)
                    VALUES (?, ?, ?, ?, 'open')
                    """,
                    (next_number, self.user_data['id'], starting_amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                db_manager.commit()

                # إرسال إشعار تليجرام
                try:
                    from src.utils.telegram import get_telegram_manager
                    telegram = get_telegram_manager()
                    telegram.send_shift_open_report({
                        'shift_number': next_number,
                        'cashier_name': employee_name if employee_name else self.user_data.get('display_name', ''),
                        'starting_amount': starting_amount,
                        'opened_at': datetime.now().strftime('%Y-%m-%d %H:%M')
                    })
                except Exception as e:
                    logger.warning(f"فشل إرسال إشعار التليجرام: {e}")

                QMessageBox.information(self, self.tr("نجاح"), self.tr(f"تم فتح الوردية #{next_number} بنجاح"))
                self.shift_opened.emit()
                self._update_current_shift_display()
                self._load_shift_history()

            except Exception as e:
                logger.error(f"خطأ في فتح الوردية: {e}")
                QMessageBox.critical(self, self.tr("خطأ"), self.tr("حدث خطأ أثناء فتح الوردية"))

    def _close_shift_dialog(self):
        """فتح نافذة إغلاق الوردية"""
        current_shift = get_current_shift()
        if not current_shift:
            return

        dialog = CloseShiftDialog(current_shift, self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                # حساب المتوقع (استبعاد مبيعات تطبيقات التوصيل من المتوقع في الخزينة)
                delivery_app_sales = dialog.payment_breakdown.get('delivery_app', 0)
                expected = current_shift['starting_amount'] + current_shift['total_sales'] - delivery_app_sales - current_shift['total_returns'] + current_shift['total_deposits'] - current_shift['total_withdrawals']

                # إغلاق الوردية
                db_manager.execute_query(
                    """
                    UPDATE shifts SET
                        end_time = ?,
                        status = 'closed',
                        expected_amount = ?,
                        actual_amount = ?,
                        difference = ?,
                        notes = ?
                    WHERE id = ?
                    """,
                    (
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        expected,
                        dialog.actual_amount,
                        dialog.actual_amount - expected,
                        dialog.notes,
                        current_shift['id']
                    )
                )
                db_manager.commit()

                # بيانات التقرير
                shift_report_data = {
                    'shift_number': current_shift['shift_number'],
                    'cashier_name': current_shift.get('display_name', ''),
                    'opened_at': current_shift['start_time'],
                    'closed_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'starting_amount': current_shift['starting_amount'],
                    'total_sales': current_shift['total_sales'],
                    'payment_breakdown': dialog.payment_breakdown,
                    'delivery_app_sales': delivery_app_sales,
                    'total_returns': current_shift['total_returns'],
                    'total_deposits': current_shift['total_deposits'],
                    'total_withdrawals': current_shift['total_withdrawals'],
                    'expected_amount': expected,
                    'actual_amount': dialog.actual_amount,
                    'difference': dialog.actual_amount - expected,
                    'total_invoices': current_shift.get('total_invoices', 0),
                    'notes': dialog.notes
                }

                # طباعة تقرير إغلاق الوردية
                try:
                    from src.utils.printer import get_printer_manager
                    printer = get_printer_manager()
                    printer.print_shift_report(shift_report_data)
                except Exception as e:
                    logger.warning(f"فشل طباعة تقرير الوردية: {e}")

                # إرسال ملخص إغلاق الوردية إلى التليجرام
                try:
                    from src.utils.telegram import get_telegram_manager
                    telegram = get_telegram_manager()
                    telegram.send_shift_close_report(shift_report_data)
                except Exception as e:
                    logger.warning(f"فشل إرسال ملخص الوردية للتليجرام: {e}")

                QMessageBox.information(self, self.tr("نجاح"), self.tr("تم إغلاق الوردية بنجاح"))

                try:
                    self.shift_closed.emit()
                    if self.isVisible():
                        self._update_current_shift_display()
                        self._load_shift_history()
                except Exception as e:
                    logger.warning(f"UI update warning after shift close: {e}")

            except Exception as e:
                logger.error(f"خطأ في إغلاق الوردية: {e}")
                try:
                    QMessageBox.critical(self, self.tr("خطأ"), self.tr(f"حدث خطأ أثناء إغلاق الوردية: {e}"))
                except:
                    pass

    def _cash_movement_dialog(self, movement_type: str):
        """فتح نافذة الحركة النقدية"""
        current_shift = get_current_shift()
        if not current_shift:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("يجب فتح وردية أولاً"))
            return

        dialog = CashMovementDialog(movement_type, self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                # التأكد من وجود عمود recipient_name
                try:
                    db_manager.execute_query("ALTER TABLE cash_movements ADD COLUMN recipient_name TEXT")
                    db_manager.commit()
                except:
                    pass  # العمود موجود بالفعل

                # إضافة الحركة
                db_manager.execute_query(
                    """
                    INSERT INTO cash_movements (type, amount, reason, category, shift_id, user_id, recipient_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        movement_type,
                        dialog.amount,
                        dialog.reason,
                        dialog.category,
                        current_shift['id'],
                        self.user_data['id'],
                        dialog.recipient_name
                    )
                )

                # تحديث إجمالي الحركات في الوردية
                if movement_type == 'deposit':
                    db_manager.execute_query(
                        "UPDATE shifts SET total_deposits = total_deposits + ? WHERE id = ?",
                        (dialog.amount, current_shift['id'])
                    )
                else:
                    db_manager.execute_query(
                        "UPDATE shifts SET total_withdrawals = total_withdrawals + ? WHERE id = ?",
                        (dialog.amount, current_shift['id'])
                    )

                db_manager.commit()

                # إرسال إشعار تليجرام
                try:
                    from src.utils.telegram import get_telegram_manager
                    from datetime import datetime
                    telegram = get_telegram_manager()
                    telegram.send_cash_movement_alert({
                        'type': movement_type,
                        'amount': dialog.amount,
                        'reason': dialog.reason,
                        'category': dialog.category,
                        'recipient_name': dialog.recipient_name,
                        'user_name': self.user_data.get('display_name', ''),
                        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M')
                    })
                except Exception as e:
                    logger.warning(f"فشل إرسال إشعار التليجرام: {e}")

                try:
                    self._load_cash_movements()
                    self._update_current_shift_display()
                except Exception as e:
                    logger.error(f"خطأ في تحديث الواجهة بعد الحركة النقدية: {e}")

            except Exception as e:
                logger.error(f"خطأ في إضافة الحركة النقدية: {e}")
                try:
                    QMessageBox.critical(self, self.tr("خطأ"), self.tr(f"حدث خطأ أثناء إضافة الحركة: {e}"))
                except:
                    pass


from PyQt5.QtWidgets import QGridLayout, QSizePolicy
from database import get_setting

class OpenShiftDialog(QDialog):
    """نافذة فتح وردية جديدة - تصميم لمسي"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.starting_amount = 0.0
        self.current_input = "" # لتخزين المدخلات النصية
        self.notes = ''
        self.employee_name = ''
        self._setup_ui()

    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        self.setWindowTitle(self.tr("فتح وردية جديدة"))
        self.setFixedSize(500, 700)
        self.setStyleSheet("""
            QDialog { background-color: #f5f5f5; }
            QLabel { font-size: 14px; font-weight: bold; color: #2c3e50; }
            QLineEdit, QComboBox {
                padding: 10px;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus, QComboBox:focus { border-color: #3498db; }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # رسالة ترحيب
        welcome_label = QLabel(self.tr("👋 فتح وردية جديدة"))
        welcome_label.setFont(QFont("Arial", 18, QFont.Bold))
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setStyleSheet("color: #2c3e50; margin-bottom: 5px;")
        layout.addWidget(welcome_label)

        # اختيار الموظف
        layout.addWidget(QLabel(self.tr("👤 الموظف المسؤول:")))
        self.employee_combo = QComboBox()
        self.employee_combo.setMinimumHeight(45)

        employees_str = get_setting('employees', 'موظف 1')
        employees = [e.strip() for e in employees_str.split(',') if e.strip()]
        for emp in employees:
            self.employee_combo.addItem(emp)
        layout.addWidget(self.employee_combo)

        # المبلغ الافتتاحي
        layout.addWidget(QLabel(self.tr("💰 المبلغ الافتتاحي:")))

        # شاشة العرض
        self.amount_display = QLineEdit()
        self.amount_display.setPlaceholderText("0.00")
        self.amount_display.setReadOnly(True)
        self.amount_display.setAlignment(Qt.AlignCenter)
        self.amount_display.setMinimumHeight(60)
        self.amount_display.setText("0.00")
        self.amount_display.setStyleSheet("""
            QLineEdit {
                font-size: 28px;
                font-weight: bold;
                color: #27ae60;
                background-color: white;
                border: 3px solid #27ae60;
            }
        """)
        layout.addWidget(self.amount_display)

        # لوحة الأرقام (مقتبسة من PaymentDialog)
        keypad_layout = QGridLayout()
        keypad_layout.setSpacing(6)

        buttons = ['7', '8', '9', '4', '5', '6', '1', '2', '3', 'C', '0', '⌫']

        for i, text in enumerate(buttons):
            btn = QPushButton(text)
            btn.setMinimumHeight(55)
            btn.setFont(QFont("Arial", 18, QFont.Bold))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            if text in ['C', '⌫']:
                btn.setStyleSheet("""
                    QPushButton { background-color: #e74c3c; color: white; border: none; border-radius: 8px; }
                    QPushButton:pressed { background-color: #c0392b; }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton { background-color: white; border: 1px solid #bdc3c7; border-radius: 8px; color: #2c3e50; }
                    QPushButton:pressed { background-color: #3498db; color: white; }
                """)

            btn.clicked.connect(lambda _, t=text: self._on_keypad_click(t))
            keypad_layout.addWidget(btn, i // 3, i % 3)

        layout.addLayout(keypad_layout)

        # ملاحظات
        layout.addWidget(QLabel(self.tr("📝 ملاحظات:")))
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText(self.tr("ملاحظات اختيارية..."))
        layout.addWidget(self.notes_input)

        # الأزرار
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)

        cancel_btn = QPushButton(self.tr("إلغاء"))
        cancel_btn.setMinimumHeight(50)
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #e74c3c; color: white; border-radius: 10px; font-weight: bold; font-size: 14px; }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        open_btn = QPushButton(self.tr("✅ فتح الوردية"))
        open_btn.setMinimumHeight(50)
        open_btn.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; border-radius: 10px; font-weight: bold; font-size: 14px; }
        """)
        open_btn.clicked.connect(self._on_open_clicked)
        buttons_layout.addWidget(open_btn)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def _on_keypad_click(self, text):
        """معالجة ضغطات لوحة الأرقام"""
        if text == 'C':
            self.current_input = ""
        elif text == '⌫':
            self.current_input = self.current_input[:-1]
        else:
            # Limit input length to prevent excessively large numbers
            if len(self.current_input) < 9: # e.g., 9999999.99
                self.current_input += text

        # Update the display based on current_input
        if not self.current_input:
            self.amount_display.setText("0.00")
        else:
            try:
                # Treat input as cents/halalas for display, e.g., "123" -> "1.23"
                val = float(self.current_input) / 100
                self.amount_display.setText(f"{val:.2f}")
            except ValueError:
                # Should not happen with digit-only current_input, but for safety
                self.amount_display.setText("0.00")


    def _on_open_clicked(self):
        """معالجة زر فتح الوردية"""
        try:
            # استخراج القيمة من النص المعروض
            text_val = self.amount_display.text()
            self.starting_amount = float(text_val)
        except ValueError:
            self.starting_amount = 0.0

        self.notes = self.notes_input.text().strip()
        self.employee_name = self.employee_combo.currentText()

        if self.starting_amount < 0:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("المبلغ الافتتاحي لا يمكن أن يكون سالباً"))
            return

        self.accept()


class CloseShiftDialog(QDialog):
    """نافذة إغلاق الوردية"""

    def __init__(self, shift_data: dict, parent=None):
        super().__init__(parent)
        self.shift_data = shift_data
        self.actual_amount = 0.0
        self.notes = ''
        self.payment_breakdown = self._get_payment_breakdown()
        self._setup_ui()

    def _get_payment_breakdown(self) -> dict:
        """Get sales breakdown by payment method for this shift"""
        try:
            cursor = db_manager.execute_query("""
                SELECT p.payment_method, SUM(p.amount) as total
                FROM payments p
                JOIN invoices i ON p.invoice_id = i.id
                WHERE i.shift_id = ? AND i.type = 'sale' AND i.status = 'completed'
                GROUP BY p.payment_method
            """, (self.shift_data['id'],))
            results = cursor.fetchall()
            breakdown = {}
            for row in results:
                breakdown[row['payment_method']] = row['total']
            return breakdown
        except Exception as e:
            logger.error(f"Error getting payment breakdown: {e}")
            return {}

    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        self.setWindowTitle(self.tr("إغلاق الوردية"))
        self.setFixedSize(550, 700)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # ملخص الوردية
        summary_frame = QFrame()
        summary_frame.setFrameShape(QFrame.Box)
        summary_frame.setStyleSheet("background-color: #f8f9fa;")
        summary_layout = QFormLayout()
        summary_layout.setSpacing(10)

        # حساب المتوقع (استبعاد مبيعات تطبيقات التوصيل)
        delivery_app_sales = self.payment_breakdown.get('delivery_app', 0)
        expected = self.shift_data['starting_amount'] + self.shift_data['total_sales'] - delivery_app_sales - self.shift_data['total_returns'] + self.shift_data['total_deposits'] - self.shift_data['total_withdrawals']

        summary_layout.addRow(self.tr("رقم الوردية:"), QLabel(f"#{self.shift_data['shift_number']}"))
        summary_layout.addRow(self.tr("الرصيد الافتتاحي:"), QLabel(f"{self.shift_data['starting_amount']:.2f} {self.tr('ريال')}"))
        summary_layout.addRow(self.tr("إجمالي المبيعات:"), QLabel(f"{self.shift_data['total_sales']:.2f} {self.tr('ريال')}"))

        # Payment method breakdown
        method_names = {
            'cash': self.tr('نقداً'),
            'card': self.tr('بطاقة'),
            'transfer': self.tr('تحويل'),
            'delivery_app': self.tr('توصيل (لا تُحسب في الخزينة)'),
            'multi': self.tr('متعدد')
        }
        for method, amount in self.payment_breakdown.items():
            method_label = method_names.get(method, method)
            summary_layout.addRow(f"  ↳ {method_label}:", QLabel(f"{amount:.2f} {self.tr('ريال')}"))

        summary_layout.addRow(self.tr("إجمالي المرتجعات:"), QLabel(f"{self.shift_data['total_returns']:.2f} {self.tr('ريال')}"))
        summary_layout.addRow(self.tr("إجمالي الإيداعات:"), QLabel(f"{self.shift_data['total_deposits']:.2f} {self.tr('ريال')}"))
        summary_layout.addRow(self.tr("إجمالي السحوبات:"), QLabel(f"{self.shift_data['total_withdrawals']:.2f} {self.tr('ريال')}"))

        expected_label = QLabel(f"{expected:.2f} {self.tr('ريال')}")
        expected_label.setFont(QFont("Arial", 14, QFont.Bold))
        expected_label.setStyleSheet("color: #3498db;")
        summary_layout.addRow(self.tr("المتوقع في الخزينة:"), expected_label)

        # صافي الخزينة = المتوقع - الرصيد الافتتاحي - مبيعات البطاقة
        card_sales = self.payment_breakdown.get('card', 0)
        net_treasury = expected - self.shift_data['starting_amount'] - card_sales
        net_label = QLabel(f"{net_treasury:.2f} {self.tr('ريال')}")
        net_label.setFont(QFont("Arial", 14, QFont.Bold))
        net_label.setStyleSheet("color: #9b59b6;")
        summary_layout.addRow(self.tr("صافي الخزينة (نقداً فقط):"), net_label)

        summary_frame.setLayout(summary_layout)
        layout.addWidget(summary_frame)

        # المبلغ الفعلي
        form = QFormLayout()
        form.setSpacing(15)

        self.actual_spin = QDoubleSpinBox()
        self.actual_spin.setRange(0, 100000)
        self.actual_spin.setDecimals(2)
        self.actual_spin.setSuffix(" " + self.tr("ريال"))
        self.actual_spin.setMinimumHeight(40)
        self.actual_spin.setFont(QFont("Arial", 14))
        self.actual_spin.setValue(expected)
        self.actual_spin.valueChanged.connect(self._update_difference)
        form.addRow(self.tr("المبلغ الفعلي في الخزينة:"), self.actual_spin)

        # الفرق
        self.difference_label = QLabel("0.00")
        self.difference_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.difference_label.setAlignment(Qt.AlignCenter)
        form.addRow(self.tr("الفرق:"), self.difference_label)

        layout.addLayout(form)

        # ملاحظات
        self.notes_text = QTextEdit()
        self.notes_text.setMaximumHeight(80)
        self.notes_text.setPlaceholderText(self.tr("ملاحظات حول الفرق (إن وجد)..."))
        layout.addWidget(self.notes_text)

        # الأزرار
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        cancel_btn = QPushButton(self.tr("إلغاء"))
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        close_btn = QPushButton(self.tr("إغلاق الوردية"))
        close_btn.setMinimumHeight(40)
        close_btn.setFont(QFont("Arial", 12, QFont.Bold))
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
            }
        """)
        close_btn.clicked.connect(self._on_close_clicked)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

        self._update_difference()

    def _update_difference(self):
        """تحديث عرض الفرق"""
        # استبعاد مبيعات تطبيقات التوصيل من المتوقع
        delivery_app_sales = self.payment_breakdown.get('delivery_app', 0)
        expected = self.shift_data['starting_amount'] + self.shift_data['total_sales'] - delivery_app_sales - self.shift_data['total_returns'] + self.shift_data['total_deposits'] - self.shift_data['total_withdrawals']
        actual = self.actual_spin.value()
        difference = actual - expected

        self.difference_label.setText(f"{difference:.2f} {self.tr('ريال')}")

        if difference > 0:
            self.difference_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        elif difference < 0:
            self.difference_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        else:
            self.difference_label.setStyleSheet("color: #333; font-weight: bold;")

    def _on_close_clicked(self):
        """معالجة زر إغلاق الوردية"""
        self.actual_amount = self.actual_spin.value()
        self.notes = self.notes_text.toPlainText().strip()

        if self.actual_amount < 0:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("المبلغ الفعلي لا يمكن أن يكون سالباً"))
            return

        self.accept()


class CashMovementDialog(QDialog):
    """نافذة الحركة النقدية"""

    def __init__(self, movement_type: str, parent=None):
        super().__init__(parent)
        self.movement_type = movement_type
        self.amount = 0.0
        self.reason = ''
        self.category = ''
        self.recipient_name = ''  # اسم المستلم (مالك/موظف)
        self._setup_ui()

    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        type_names = {
            'deposit': self.tr("إيداع نقدي"),
            'withdrawal': self.tr("سحب نقدي"),
            'expense': self.tr("تسجيل مصروف")
        }

        self.setWindowTitle(type_names.get(self.movement_type, self.tr("حركة نقدية")))
        self.setFixedSize(400, 350)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # العنوان
        title_label = QLabel(type_names.get(self.movement_type, self.tr("حركة نقدية")))
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # توضيح للسحب النقدي
        if self.movement_type == 'withdrawal':
            note_label = QLabel(self.tr("⚠️ السحب النقدي للمالك فقط - المبلغ يخرج مباشرة للمالك"))
            note_label.setStyleSheet("color: #e67e22; background-color: #fef9e7; padding: 8px; border-radius: 5px;")
            note_label.setAlignment(Qt.AlignCenter)
            note_label.setWordWrap(True)
            layout.addWidget(note_label)

        form = QFormLayout()
        form.setSpacing(15)

        # المبلغ
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 10000)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setSuffix(" " + self.tr("ريال"))
        self.amount_spin.setMinimumHeight(40)
        self.amount_spin.setFont(QFont("Arial", 14))
        form.addRow(self.tr("المبلغ:"), self.amount_spin)

        # السبب
        self.reason_input = QLineEdit()
        self.reason_input.setPlaceholderText(self.tr("مطلور"))
        self.reason_input.setMinimumHeight(35)
        form.addRow(self.tr("السبب:"), self.reason_input)

        # التصنيف
        self.category_combo = QComboBox()
        self.category_combo.setMinimumHeight(35)

        categories = {
            'deposit': [self.tr("إيداع"), self.tr("تحويل من الخزنة الرئيسية")],
            'withdrawal': [self.tr("سحب"), self.tr("إيداع في الخزنة الرئيسية")],
            'expense': [self.tr("مشتروات"), self.tr("صيانة"), self.tr("مرافق"), self.tr("رواتب"), self.tr("إيجار"), self.tr("أخرى")]
        }

        for cat in categories.get(self.movement_type, []):
            self.category_combo.addItem(cat)

        form.addRow(self.tr("التصنيف:"), self.category_combo)

        # اسم المستلم (للسحب النقدي والمصروفات)
        if self.movement_type in ('withdrawal', 'expense'):
            self.recipient_combo = QComboBox()
            self.recipient_combo.setMinimumHeight(35)
            self.recipient_combo.setEditable(True)  # يمكن كتابة اسم جديد

            # تحميل الأسماء من الإعدادات
            from database import get_setting
            if self.movement_type == 'withdrawal':
                names_str = get_setting('owners', 'المالك')
                label_text = self.tr("اسم المالك:")
            else:
                names_str = get_setting('employees', 'موظف 1')
                label_text = self.tr("اسم الموظف:")

            names = [n.strip() for n in names_str.split(',') if n.strip()]
            for name in names:
                self.recipient_combo.addItem(name)

            form.addRow(label_text, self.recipient_combo)

        layout.addLayout(form)

        # الأزرار
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        cancel_btn = QPushButton(self.tr("إلغاء"))
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton(self.tr("حفظ"))
        save_btn.setMinimumHeight(40)
        save_btn.setFont(QFont("Arial", 12, QFont.Bold))
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
            }
        """)
        save_btn.clicked.connect(self._on_save_clicked)
        buttons_layout.addWidget(save_btn)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def _on_save_clicked(self):
        """معالجة زر الحفظ"""
        self.amount = self.amount_spin.value()
        self.reason = self.reason_input.text().strip()
        self.category = self.category_combo.currentText()

        # اسم المستلم
        if hasattr(self, 'recipient_combo'):
            self.recipient_name = self.recipient_combo.currentText().strip()
        else:
            self.recipient_name = ''

        if self.amount <= 0:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("المبلغ يجب أن يكون أكبر من صفر"))
            return

        if not self.reason:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("السبب مطلوب"))
            return

        # التحقق من اسم المستلم للسحب والمصروفات
        if self.movement_type in ('withdrawal', 'expense') and not self.recipient_name:
            if self.movement_type == 'withdrawal':
                QMessageBox.warning(self, self.tr("تحذير"), self.tr("اسم المالك مطلوب"))
            else:
                QMessageBox.warning(self, self.tr("تحذير"), self.tr("اسم الموظف مطلوب"))
            return

        self.accept()
