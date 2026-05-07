"""
نافذة الدفع - تصميم مرن متجاوب
Payment Dialog - Flexible Responsive Design
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QButtonGroup, QRadioButton, QFrame, QGridLayout,
    QMessageBox, QInputDialog, QScrollArea, QWidget, QSizePolicy,
    QApplication, QScroller
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from src.ui.touch_number_block import TouchNumberBlock
from database import get_setting


class PaymentDialog(QDialog):
    """نافذة إتمام الدفع - تصميم مرن"""

    def __init__(self, total_amount: float, parent=None):
        super().__init__(parent)
        self.total_amount = total_amount  # الإجمالي النهائي من pos_screen (محسوب مسبقاً)
        self.payment_data = {}
        self.current_input = ""

        # قراءة ألوان المستخدم (إن وُجدت)
        self.cash_color = get_setting('cash_color', '#27ae60')
        self.card_color = get_setting('card_color', '#3498db')
        self.multi_color = get_setting('multi_color', '#e74c3c')

        # استخراج تفاصيل الضريبة للعرض فقط (الإجمالي لا يتغير)
        self.tax_rate = float(get_setting('tax_rate', '0.15'))
        self.tax_inclusive = get_setting('tax_inclusive', '1') == '1'

        # دائماً نستخرج الضريبة من الإجمالي للعرض فقط
        # الإجمالي محسوب مسبقاً في pos_screen بالطريقة الصحيحة
        self.net_amount = self.total_amount / (1 + self.tax_rate)
        self.tax_amount = self.total_amount - self.net_amount

        self._setup_ui()

    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        self.setWindowTitle(self.tr("إتمام الدفع"))
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

        # تحسين الحجم للشاشات اللمسية - 500x700 حجم جيد لمعظم الشاشات
        self.setFixedSize(500, 700)

        # ScrollArea للمحتوى
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: #f5f5f5; }")

        # تفعيل السحب باللمس (Touch Scrolling)
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # تم إزالة المربع الأخضر العلوي (الصافي/الضريبة/الإجمالي)

        # ═══════════════════════════════════════════════════════════
        # طرق الدفع
        # ═══════════════════════════════════════════════════════════
        payment_layout = QHBoxLayout()
        payment_layout.setSpacing(6)

        self.payment_buttons = QButtonGroup()

        methods = [
            ('cash', '💵', self.tr('نقدي'), '#27ae60'),
            ('card', '💳', self.tr('بطاقة'), '#3498db'),
            ('delivery_app', '🛵', self.tr('توصيل'), '#9b59b6'),
            ('multi', '🔀', self.tr('تقسيم'), '#e74c3c'),
        ]

        for i, (method_id, icon, text, color) in enumerate(methods):
            btn = QRadioButton(f"{icon} {text}")
            btn.setFont(QFont("Arial", 11, QFont.Bold))
            btn.setProperty('method_id', method_id)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setMinimumHeight(40)
            btn.setStyleSheet(f"""
                QRadioButton {{
                    padding: 8px;
                    border: 2px solid #ddd;
                    border-radius: 6px;
                    background-color: white;
                }}
                QRadioButton:checked {{
                    background-color: {color};
                    color: white;
                    border-color: {color};
                }}
                QRadioButton::indicator {{ width: 0; height: 0; }}
            """)
            if i == 0:
                btn.setChecked(True)
            self.payment_buttons.addButton(btn, i)
            payment_layout.addWidget(btn)

        self.payment_buttons.buttonClicked.connect(self._on_payment_method_changed)
        main_layout.addLayout(payment_layout)

        # ═══════════════════════════════════════════════════════════
        # لوحة الدفع المتعدد (مخفية افتراضياً)
        # ═══════════════════════════════════════════════════════════
        self.multi_payment_frame = QFrame()
        self.multi_payment_frame.setStyleSheet("""
            QFrame#multiFrame {
                border: 2px solid #e74c3c;
                border-radius: 8px;
                padding: 10px;
                background: #fff5f5;
            }
        """)
        self.multi_payment_frame.setObjectName("multiFrame")
        multi_layout = QVBoxLayout(self.multi_payment_frame)
        multi_layout.setSpacing(10)

        # عنوان
        multi_title = QLabel(self.tr("💰 تقسيم المبلغ"))
        multi_title.setFont(QFont("Arial", 14, QFont.Bold))
        multi_title.setAlignment(Qt.AlignCenter)
        multi_title.setStyleSheet("color: #e74c3c;")
        multi_layout.addWidget(multi_title)

        # Cash TouchNumberBlock
        self.cash_amount = TouchNumberBlock(
            title=self.tr("💵 نقدي"),
            suffix=self.tr(" ر.س"),
            maxVal=100000
        )
        self.cash_amount.valueChanged.connect(self._on_cash_changed)
        multi_layout.addWidget(self.cash_amount)

        # Card TouchNumberBlock
        self.card_amount = TouchNumberBlock(
            title=self.tr("💳 بطاقة"),
            suffix=self.tr(" ر.س"),
            maxVal=100000
        )
        self.card_amount.valueChanged.connect(self._on_card_changed)
        multi_layout.addWidget(self.card_amount)

        # أزرار سريعة للدفع المتعدد
        multi_quick_layout = QGridLayout()
        multi_quick_layout.setSpacing(4)
        for i, amount in enumerate([10, 50, 100, 200]):
            btn = QPushButton(f"+{amount}")
            btn.setMinimumHeight(35)
            btn.setFont(QFont("Arial", 10, QFont.Bold))
            btn.setStyleSheet("""
                QPushButton { background-color: #27ae60; color: white; border: none; border-radius: 4px; }
                QPushButton:pressed { background-color: #229954; }
            """)
            btn.clicked.connect(lambda _, a=amount: self.cash_amount.setValue(self.cash_amount.value() + a))
            multi_quick_layout.addWidget(btn, 0, i)
        multi_layout.addLayout(multi_quick_layout)

        # زر المبلغ بالضبط
        exact_multi_btn = QPushButton(self.tr("المبلغ كامل نقداً:") + f" {self.total_amount:.2f}")
        exact_multi_btn.setMinimumHeight(40)
        exact_multi_btn.setFont(QFont("Arial", 11, QFont.Bold))
        exact_multi_btn.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; border: none; border-radius: 6px; }
            QPushButton:pressed { background-color: #2980b9; }
        """)
        exact_multi_btn.clicked.connect(lambda: self.cash_amount.setValue(self.total_amount))
        multi_layout.addWidget(exact_multi_btn)

        # لوحة أرقام للدفع المتعدد
        multi_keypad = QGridLayout()
        multi_keypad.setSpacing(4)
        keypad_buttons = ['7', '8', '9', '4', '5', '6', '1', '2', '3', 'C', '0', '⌫']
        for idx, key in enumerate(keypad_buttons):
            btn = QPushButton(key)
            btn.setMinimumHeight(40)
            btn.setFont(QFont("Arial", 14, QFont.Bold))
            if key in ['C', '⌫']:
                btn.setStyleSheet("""
                    QPushButton { background-color: #e74c3c; color: white; border: none; border-radius: 6px; }
                    QPushButton:pressed { background-color: #c0392b; }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton { background-color: #ecf0f1; border: 1px solid #bdc3c7; border-radius: 6px; color: #2c3e50; }
                    QPushButton:pressed { background-color: #3498db; color: white; }
                """)
            btn.clicked.connect(lambda _, k=key: self._on_multi_keypad_click(k))
            multi_keypad.addWidget(btn, idx // 3, idx % 3)
        multi_layout.addLayout(multi_keypad)

        self.multi_payment_frame.setVisible(False)
        main_layout.addWidget(self.multi_payment_frame)

        # ═══════════════════════════════════════════════════════════
        # شاشة المبلغ المدفوع
        # ═══════════════════════════════════════════════════════════
        self.paid_frame = QFrame()
        paid_layout = QVBoxLayout(self.paid_frame)
        paid_layout.setSpacing(6)

        self.amount_display = QLabel("0.00")
        self.amount_display.setFont(QFont("Courier New", 24, QFont.Bold))
        self.amount_display.setAlignment(Qt.AlignCenter)
        self.amount_display.setStyleSheet("""
            background-color: #1a1a1a;
            border: 2px solid #3498db;
            border-radius: 6px;
            color: #00ff00;
            padding: 10px;
        """)
        paid_layout.addWidget(self.amount_display)

        # مربع المتبقي للزبون (داخل الشاشة السوداء)
        self.change_display = QLabel(self.tr("الباقي:") + " 0.00")
        self.change_display.setFont(QFont("Arial", 14, QFont.Bold))
        self.change_display.setAlignment(Qt.AlignCenter)
        self.change_display.setStyleSheet("""
            background-color: #1a1a1a;
            border: 2px solid #27ae60;
            border-radius: 6px;
            color: #f39c12;
            padding: 8px;
        """)
        paid_layout.addWidget(self.change_display)

        # لوحة الأرقام - في container قابل للإخفاء
        self.keypad_container = QWidget()
        keypad_container_layout = QVBoxLayout(self.keypad_container)
        keypad_container_layout.setContentsMargins(0, 0, 0, 0)
        keypad_container_layout.setSpacing(4)

        keypad_layout = QGridLayout()
        keypad_layout.setSpacing(4)

        buttons = ['7', '8', '9', '4', '5', '6', '1', '2', '3', 'C', '0', '⌫']

        for i, text in enumerate(buttons):
            btn = QPushButton(text)
            btn.setMinimumHeight(45)
            btn.setFont(QFont("Arial", 16, QFont.Bold))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            if text in ['C', '⌫']:
                btn.setStyleSheet("""
                    QPushButton { background-color: #e74c3c; color: white; border: none; border-radius: 6px; }
                    QPushButton:pressed { background-color: #c0392b; }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton { background-color: #ecf0f1; border: 1px solid #bdc3c7; border-radius: 6px; color: #2c3e50; }
                    QPushButton:pressed { background-color: #3498db; color: white; }
                """)

            btn.clicked.connect(lambda _, t=text: self._on_keypad_click(t))
            keypad_layout.addWidget(btn, i // 3, i % 3)

        keypad_container_layout.addLayout(keypad_layout)

        # أزرار سريعة
        quick_layout = QGridLayout()
        quick_layout.setSpacing(4)
        quick_amounts = [10, 20, 50, 100, 200, 500]

        for i, amount in enumerate(quick_amounts):
            btn = QPushButton(f"+{amount}")
            btn.setMinimumHeight(35)
            btn.setFont(QFont("Arial", 10, QFont.Bold))
            btn.setStyleSheet("""
                QPushButton { background-color: #95a5a6; color: white; border: none; border-radius: 4px; }
                QPushButton:pressed { background-color: #7f8c8d; }
            """)
            btn.clicked.connect(lambda _, a=amount: self._add_quick_amount(a))
            quick_layout.addWidget(btn, i // 3, i % 3)

        keypad_container_layout.addLayout(quick_layout)

        # زر المبلغ بالضبط
        self.exact_btn = QPushButton(self.tr("المبلغ بالضبط:") + f" {self.total_amount:.2f}")
        self.exact_btn.setMinimumHeight(40)
        self.exact_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.exact_btn.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; border: none; border-radius: 6px; }
            QPushButton:pressed { background-color: #2980b9; }
        """)
        self.exact_btn.clicked.connect(lambda: self._set_amount(self.total_amount))
        keypad_container_layout.addWidget(self.exact_btn)

        paid_layout.addWidget(self.keypad_container)

        main_layout.addWidget(self.paid_frame)

        # أزرار التحكم
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        cancel_btn = QPushButton(self.tr("❌ إلغاء"))
        cancel_btn.setMinimumHeight(50)
        cancel_btn.setFont(QFont("Arial", 14, QFont.Bold))
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #e74c3c; color: white; border: none; border-radius: 8px; }
            QPushButton:pressed { background-color: #c0392b; }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        self.pay_btn = QPushButton(self.tr("✅ إتمام الدفع"))
        self.pay_btn.setMinimumHeight(50)
        self.pay_btn.setFont(QFont("Arial", 14, QFont.Bold))
        self.pay_btn.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; border: none; border-radius: 8px; }
            QPushButton:pressed { background-color: #229954; }
            QPushButton:disabled { background-color: #95a5a6; }
        """)
        self.pay_btn.clicked.connect(self._on_pay_clicked)
        buttons_layout.addWidget(self.pay_btn, 2)

        main_layout.addLayout(buttons_layout)

        # إعداد الـ ScrollArea
        scroll.setWidget(container)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(scroll)

        # متغيرات للتحكم في التحديث التلقائي
        self._updating_cash = False
        self._updating_card = False

        # البدء بمبلغ 0 للدفع النقدي
        self._set_amount(0)

    def _on_payment_method_changed(self, button):
        method = button.property('method_id')
        is_multi = method == 'multi'

        self.multi_payment_frame.setVisible(is_multi)
        self.paid_frame.setVisible(not is_multi)

        if is_multi:
            self.cash_amount.setValue(0)
            self.card_amount.setValue(0)
            self._update_multi_total()
        elif method == 'cash':
            # الدفع النقدي - ابدأ بـ 0 ليدخل المستخدم المبلغ
            self.keypad_container.setVisible(True)
            self._set_amount(0)
        elif method == 'card' or method == 'delivery_app':
            # الدفع بالبطاقة أو تطبيقات التوصيل - المبلغ المطلوب مباشرة بدون لوحة أرقام
            self.keypad_container.setVisible(False)
            self._set_amount(self.total_amount)

    def _update_multi_total(self):
        # تحديث المتبقي في الدفع المتعدد - حساب تلقائي
        cash = self.cash_amount.value()
        card = self.card_amount.value()
        total_paid = cash + card

        # تفعيل زر الدفع فقط إذا تم تغطية المبلغ بالكامل
        if total_paid >= self.total_amount - 0.01: # سماحية بسيطة للفواصل العائمة
            self.pay_btn.setEnabled(True)
        else:
            self.pay_btn.setEnabled(False)

    def _on_multi_keypad_click(self, key: str):
        # التعامل مع لوحة أرقام الدفع المتعدد
        # نستخدم المبلغ النقدي كحقل افتراضي
        current_text = str(int(self.cash_amount.value() * 100))

        if key == 'C':
            current_text = ""
        elif key == '⌫':
            current_text = current_text[:-1]
        else:
            if len(current_text) < 8:
                current_text += key

        if current_text:
            try:
                new_value = float(current_text) / 100
                self.cash_amount.setValue(new_value)
            except:
                pass
        else:
            self.cash_amount.setValue(0)

    def _on_cash_changed(self):
        # عند تغيير المبلغ النقدي - احسب المتبقي للبطاقة تلقائياً
        cash = self.cash_amount.value()
        remaining_for_card = max(0, self.total_amount - cash)
        # فقط إذا كان المستخدم غير المبلغ النقدي، حدث البطاقة
        if not self._updating_card:
            self._updating_cash = True
            self.card_amount.setValue(remaining_for_card)
            self._updating_cash = False
        self._update_multi_total()

    def _on_card_changed(self):
        # عند تغيير مبلغ البطاقة - احسب المتبقي للنقدي تلقائياً
        card = self.card_amount.value()
        remaining_for_cash = max(0, self.total_amount - card)
        if not self._updating_cash:
            self._updating_card = True
            self.cash_amount.setValue(remaining_for_cash)
            self._updating_card = False
        self._update_multi_total()

    def _on_keypad_click(self, text: str):
        if text == 'C':
            self.current_input = ""
        elif text == '⌫':
            self.current_input = self.current_input[:-1]
        else:
            if len(self.current_input) < 8:
                self.current_input += text

        if self.current_input:
            try:
                amount = float(self.current_input) / 100
                self.amount_display.setText(f"{amount:.2f}")
            except:
                self.amount_display.setText("0.00")
        else:
            self.amount_display.setText("0.00")

        self._update_change()

    def _add_quick_amount(self, amount: float):
        try:
            current = float(self.amount_display.text())
            self._set_amount(current + amount)
        except ValueError:
            self._set_amount(amount)

    def _set_amount(self, amount: float):
        self.current_input = str(int(amount * 100))
        self.amount_display.setText(f"{amount:.2f}")
        self._update_change()

    def _update_change(self):
        # التحقق من المبلغ وتحديث المتبقي وتفعيل/تعطيل زر الدفع
        try:
            paid = float(self.amount_display.text())
            change = max(0, paid - self.total_amount)

            # تحديث شاشة المتبقي
            if change > 0:
                self.change_display.setText(self.tr("الباقي:") + f" {change:.2f}")
                self.change_display.setStyleSheet("""
                    background-color: #1a1a1a;
                    border: 2px solid #27ae60;
                    border-radius: 6px;
                    color: #27ae60;
                    padding: 8px;
                """)
            else:
                remaining = self.total_amount - paid
                if remaining > 0:
                    self.change_display.setText(self.tr("المتبقي:") + f" {remaining:.2f}")
                    self.change_display.setStyleSheet("""
                        background-color: #1a1a1a;
                        border: 2px solid #e74c3c;
                        border-radius: 6px;
                        color: #e74c3c;
                        padding: 8px;
                    """)
                else:
                    self.change_display.setText(self.tr("✓ المبلغ مطابق"))
                    self.change_display.setStyleSheet("""
                        background-color: #1a1a1a;
                        border: 2px solid #27ae60;
                        border-radius: 6px;
                        color: #27ae60;
                        padding: 8px;
                    """)

            # التحقق من طريقة الدفع
            checked_button = self.payment_buttons.checkedButton()
            if checked_button and checked_button.property('method_id') in ('card', 'delivery_app'):
                self.pay_btn.setEnabled(abs(paid - self.total_amount) < 0.01)
            else:
                self.pay_btn.setEnabled(paid >= self.total_amount)
        except ValueError:
            self.change_display.setText(self.tr("الباقي:") + " 0.00")
            self.pay_btn.setEnabled(False)

    def _on_pay_clicked(self):
        try:
            checked_button = self.payment_buttons.checkedButton()
            if not checked_button:
                QMessageBox.warning(self, self.tr("خطأ"), self.tr("اختر طريقة الدفع"))
                return

            method = checked_button.property('method_id')

            if method == 'multi':
                cash = self.cash_amount.value()
                card = self.card_amount.value()
                total_paid = cash + card

                if total_paid < self.total_amount:
                    QMessageBox.warning(self, self.tr("خطأ"), self.tr("المدفوع أقل من الإجمالي"))
                    return

                reference = ''
                if card > 0 and get_setting('require_card_reference', '0') == '1':
                    # رقم المرجع مفعل في الإعدادات
                    ref, ok = QInputDialog.getText(self, self.tr("رقم العملية"), self.tr("رقم عملية البطاقة:"))
                    if ok and ref.strip():
                        reference = ref.strip()

                self.payment_data = {
                    'method': 'multi',
                    'cash_amount': cash,
                    'card_amount': card,
                    'paid_amount': total_paid,  # مفتاح مطلوب من pos_screen
                    'total_paid': total_paid,
                    'change': total_paid - self.total_amount,
                    'reference': reference,
                    'net_amount': self.net_amount,
                    'tax_amount': self.tax_amount,
                    'total_amount': self.total_amount
                }
            else:
                paid_amount = float(self.amount_display.text())

                if paid_amount < self.total_amount:
                    QMessageBox.warning(self, self.tr("خطأ"), self.tr("المبلغ غير كافي"))
                    return

                reference = ''
                if method == 'card' and get_setting('require_card_reference', '0') == '1':
                    # رقم المرجع مفعل في الإعدادات
                    ref, ok = QInputDialog.getText(self, self.tr("رقم المرجع"), self.tr("رقم المرجع:"))
                    if ok and ref.strip():
                        reference = ref.strip()

                self.payment_data = {
                    'method': method,
                    'paid_amount': paid_amount,
                    'change': paid_amount - self.total_amount,
                    'reference': reference,
                    'net_amount': self.net_amount,
                    'tax_amount': self.tax_amount,
                    'total_amount': self.total_amount
                }

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, self.tr("خطأ"), self.tr("خطأ:") + f" {str(e)}")


class SaleConfirmationDialog(QDialog):
    """نافذة تأكيد البيع - تغلق بلمسة واحدة"""

    def __init__(self, invoice_number: str, total: float, paid: float,
                 method: str, change: float, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # حجم النافذة
        self.setFixedSize(350, 280)

        # التخطيط الرئيسي
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # الإطار الرئيسي
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-radius: 15px;
                border: 3px solid #27ae60;
            }
        """)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setSpacing(10)
        frame_layout.setContentsMargins(20, 20, 20, 20)

        # علامة النجاح
        success_label = QLabel("✅")
        success_label.setFont(QFont("Arial", 40))
        success_label.setAlignment(Qt.AlignCenter)
        frame_layout.addWidget(success_label)

        # تفاصيل الفاتورة
        method_names = {'cash': 'نقدي 💵', 'card': 'بطاقة 💳', 'delivery_app': 'توصيل 🛵', 'multi': 'تقسيم 🔀'}

        # بناء سطر المتبقي
        change_line = ""
        if change > 0.001:  # تجاهل الفروقات الصغيرة جداً
            change_line = f'<p style="color: #27ae60; font-size: 18px;"><b>الباقي للزبون: {change:.2f} ر.س</b></p>'

        details = f"""
        <div style='color: white; text-align: center; font-size: 14px;'>
            <p><b>رقم الفاتورة:</b> {invoice_number}</p>
            <p><b>الإجمالي:</b> {total:.2f} ر.س</p>
            <p><b>المدفوع:</b> {paid:.2f} ر.س</p>
            <p><b>طريقة الدفع:</b> {method_names.get(method, method)}</p>
            {change_line}
        </div>
        """
        details_label = QLabel(details)
        details_label.setAlignment(Qt.AlignCenter)
        frame_layout.addWidget(details_label)

        # رسالة الإغلاق
        close_hint = QLabel("المس أي مكان للإغلاق")
        close_hint.setStyleSheet("color: #95a5a6; font-size: 11px;")
        close_hint.setAlignment(Qt.AlignCenter)
        frame_layout.addWidget(close_hint)

        layout.addWidget(frame)

    def mousePressEvent(self, event):
        # إغلاق النافذة عند أي لمسة
        self.accept()
        super().mousePressEvent(event)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    app.setFont(QFont("Arial", 11))

    dialog = PaymentDialog(total_amount=250.75)

    if dialog.exec_() == QDialog.Accepted:
        print("✅ تم الدفع")
        print(dialog.payment_data)
    else:
        print("❌ إلغاء")

    sys.exit(app.exec_())

