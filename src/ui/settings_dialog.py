"""
الإعدادات
Settings Dialog
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QGroupBox,
    QFormLayout, QLineEdit, QDoubleSpinBox, QComboBox, QCheckBox,
    QPushButton, QMessageBox, QTextEdit, QLabel, QFrame, QWidget, QSpinBox,
    QScrollArea, QGridLayout, QFileDialog, QTimeEdit
)
from PyQt5.QtCore import Qt, QTime
from PyQt5.QtGui import QFont, QPixmap
from loguru import logger

from database import db_manager, get_setting, set_setting


class SettingsDialog(QDialog):
    """نافذة الإعدادات"""

    # أنواع تقارير التليجرام - 16 نوع
    TELEGRAM_REPORT_TYPES = {
        'shift_open': ('🟢 فتح وردية', 'Shift Open'),
        'shift_close': ('🔴 إغلاق وردية', 'Shift Close'),
        'daily_summary': ('📊 الملخص اليومي', 'Daily Summary'),
        'monthly_summary': ('📅 الملخص الشهري', 'Monthly Summary'),
        'low_stock': ('⚠️ نقص المخزون', 'Low Stock'),
        'low_ingredients': ('🥗 نقص المكونات', 'Low Ingredients'),
        'top_products': ('🏆 الأكثر مبيعاً', 'Top Products'),
        'profit_report': ('💰 تقرير الأرباح', 'Profit Report'),
        'shortage_alert': ('📉 تنبيه عجز', 'Shortage Alert'),
        'surplus_alert': ('📈 تنبيه زيادة', 'Surplus Alert'),
        'return_processed': ('🔄 مرتجع', 'Return Processed'),
        'ingredient_usage': ('🍳 استهلاك المكونات', 'Ingredient Usage'),
        'cash_movement': ('💵 حركة نقدية', 'Cash Movement'),
        'print_failed': ('🖨️ فشل الطباعة', 'Print Failed'),
        'login': ('🔐 تسجيل دخول', 'Login'),
        'price_change': ('💲 تغيير سعر', 'Price Change'),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("الإعدادات"))
        self.setMinimumSize(700, 600)
        self.telegram_checkboxes = {}  # Store report type checkboxes
        self._setup_ui()

    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        layout = QVBoxLayout()

        # التبويبات
        tabs = QTabWidget()

        # تبويب عام
        general_tab = self._create_general_tab()
        tabs.addTab(general_tab, self.tr("عام"))

        # تبويب التليجرام
        telegram_tab = self._create_telegram_tab()
        tabs.addTab(telegram_tab, self.tr("التليجرام"))

        # تبويب الطباعة
        printing_tab = self._create_printing_tab()
        tabs.addTab(printing_tab, self.tr("الطباعة"))

        # تبويب النسخ الاحتياطي
        backup_tab = self._create_backup_tab()
        tabs.addTab(backup_tab, self.tr("النسخ الاحتياطي"))

        # تبويب إدارة البيانات (خيارات خطيرة)
        data_management_tab = self._create_data_management_tab()
        tabs.addTab(data_management_tab, self.tr("إدارة البيانات"))

        layout.addWidget(tabs)

        # الأزرار
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        cancel_btn = QPushButton(self.tr("❌ إلغاء"))
        cancel_btn.setMinimumHeight(45)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton(self.tr("✅ حفظ"))
        save_btn.setMinimumHeight(45)
        save_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        save_btn.clicked.connect(self._save_settings)
        buttons_layout.addWidget(save_btn)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def _create_general_tab(self):
        """إنشاء تبويب الإعدادات العامة"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)

        # معلومات المطعم
        restaurant_group = QGroupBox(self.tr("معلومات المطعم"))
        restaurant_group.setFont(QFont("Arial", 11, QFont.Bold))
        restaurant_layout = QFormLayout()
        restaurant_layout.setSpacing(10)

        self.company_name_input = QLineEdit()
        self.company_name_input.setText(get_setting('company_name', 'مطعمي'))
        self.company_name_input.setMinimumHeight(35)
        restaurant_layout.addRow(self.tr("اسم المطعم:"), self.company_name_input)

        self.vat_number_input = QLineEdit()
        self.vat_number_input.setText(get_setting('vat_number', ''))
        self.vat_number_input.setMinimumHeight(35)
        restaurant_layout.addRow(self.tr("الرقم الضريبي:"), self.vat_number_input)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["SAR", "USD", "EUR"])
        self.currency_combo.setCurrentText(get_setting('currency', 'SAR'))
        restaurant_layout.addRow(self.tr("العملة:"), self.currency_combo)

        restaurant_group.setLayout(restaurant_layout)
        layout.addWidget(restaurant_group)

        # شعار المطعم
        logo_group = QGroupBox(self.tr("شعار المطعم"))
        logo_group.setFont(QFont("Arial", 11, QFont.Bold))
        logo_layout = QVBoxLayout()
        logo_layout.setSpacing(10)

        # عرض الشعار الحالي
        self.logo_preview = QLabel()
        self.logo_preview.setFixedSize(100, 100)
        self.logo_preview.setAlignment(Qt.AlignCenter)
        self.logo_preview.setStyleSheet("border: 2px dashed #bdc3c7; border-radius: 8px;")

        current_logo = get_setting('restaurant_logo', '')
        if current_logo:
            import os
            if os.path.exists(current_logo):
                pixmap = QPixmap(current_logo).scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.logo_preview.setPixmap(pixmap)
            else:
                self.logo_preview.setText(self.tr("لا يوجد شعار"))
        else:
            self.logo_preview.setText(self.tr("لا يوجد شعار"))
        logo_layout.addWidget(self.logo_preview, alignment=Qt.AlignCenter)

        # أزرار تحميل/حذف الشعار
        logo_buttons = QHBoxLayout()

        upload_logo_btn = QPushButton(self.tr("📷 تحميل شعار"))
        upload_logo_btn.setMinimumHeight(35)
        upload_logo_btn.clicked.connect(self._upload_logo)
        logo_buttons.addWidget(upload_logo_btn)

        remove_logo_btn = QPushButton(self.tr("🗑️ إزالة الشعار"))
        remove_logo_btn.setMinimumHeight(35)
        remove_logo_btn.clicked.connect(self._remove_logo)
        logo_buttons.addWidget(remove_logo_btn)

        logo_layout.addLayout(logo_buttons)

        # خيار طباعة الشعار
        self.print_logo_check = QCheckBox(self.tr("🖨️ طباعة الشعار في الفواتير"))
        self.print_logo_check.setChecked(get_setting('print_logo', '1') == '1')
        self.print_logo_check.setToolTip(self.tr("طباعة شعار المطعم في أعلى كل فاتورة"))
        logo_layout.addWidget(self.print_logo_check)

        logo_group.setLayout(logo_layout)
        layout.addWidget(logo_group)

        # الإعدادات العامة
        general_group = QGroupBox(self.tr("إعدادات عامة"))
        general_group.setFont(QFont("Arial", 11, QFont.Bold))
        general_layout = QFormLayout()
        general_layout.setSpacing(10)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["ar", "en"])
        self.language_combo.setCurrentText(get_setting('language', 'ar'))
        general_layout.addRow(self.tr("اللغة:"), self.language_combo)

        self.tax_rate_spin = QDoubleSpinBox()
        self.tax_rate_spin.setRange(0, 100)
        self.tax_rate_spin.setDecimals(2)
        self.tax_rate_spin.setSuffix(" %")
        self.tax_rate_spin.setValue(float(get_setting('tax_rate', '0.15')) * 100)
        general_layout.addRow(self.tr("نسبة الضريبة الافتراضية:"), self.tax_rate_spin)

        # الأسعار شاملة الضريبة
        self.tax_inclusive_check = QCheckBox(self.tr("الأسعار شاملة الضريبة (استخراج الضريبة من السعر)"))
        self.tax_inclusive_check.setChecked(get_setting('tax_inclusive', '1') == '1')
        self.tax_inclusive_check.setToolTip(self.tr("إذا كانت أسعار المنتجات تشمل الضريبة، سيتم استخراج الضريبة تلقائياً"))
        general_layout.addRow(self.tax_inclusive_check)

        # طلب رقم المرجع عند الدفع بالبطاقة
        self.require_card_reference = QCheckBox(self.tr("طلب رقم المرجع عند الدفع بالبطاقة"))
        self.require_card_reference.setChecked(get_setting('require_card_reference', '0') == '1')
        general_layout.addRow(self.require_card_reference)

        general_group.setLayout(general_layout)
        layout.addWidget(general_group)

        # ═══════════════════════════════════════════════════════════
        # الملاك والموظفين
        # ═══════════════════════════════════════════════════════════
        staff_group = QGroupBox(self.tr("الملاك والموظفين"))
        staff_group.setFont(QFont("Arial", 11, QFont.Bold))
        staff_layout = QFormLayout()
        staff_layout.setSpacing(10)

        self.owners_input = QLineEdit()
        self.owners_input.setText(get_setting('owners', 'المالك'))
        self.owners_input.setMinimumHeight(35)
        self.owners_input.setPlaceholderText(self.tr("مالك 1, مالك 2, ..."))
        self.owners_input.setToolTip(self.tr("أسماء الملاك مفصولة بفاصلة - تظهر عند السحب النقدي"))
        staff_layout.addRow(self.tr("أسماء الملاك:"), self.owners_input)

        self.employees_input = QLineEdit()
        self.employees_input.setText(get_setting('employees', 'موظف 1'))
        self.employees_input.setMinimumHeight(35)
        self.employees_input.setPlaceholderText(self.tr("موظف 1, موظف 2, ..."))
        self.employees_input.setToolTip(self.tr("أسماء الموظفين مفصولة بفاصلة - تظهر عند المصروفات"))
        staff_layout.addRow(self.tr("أسماء الموظفين:"), self.employees_input)

        staff_group.setLayout(staff_layout)
        layout.addWidget(staff_group)

        # ═══════════════════════════════════════════════════════════
        # التحديثات
        # ═══════════════════════════════════════════════════════════
        update_group = QGroupBox(self.tr("تحديثات التطبيق"))
        update_group.setFont(QFont("Arial", 11, QFont.Bold))
        update_layout = QVBoxLayout()
        update_layout.setSpacing(10)

        # عرض الإصدار الحالي
        try:
            from src.utils.updater import get_update_manager
            current_version = get_update_manager().current_version
        except:
            current_version = "3.0.0"

        version_label = QLabel(self.tr(f"الإصدار الحالي: {current_version}"))
        version_label.setStyleSheet("font-size: 13px; color: #2c3e50;")
        update_layout.addWidget(version_label)

        # زر التحقق من التحديثات
        check_updates_btn = QPushButton(self.tr("🔄 التحقق من التحديثات"))
        check_updates_btn.setMinimumHeight(45)
        check_updates_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #8e44ad; }
        """)
        check_updates_btn.clicked.connect(self._open_update_dialog)
        update_layout.addWidget(check_updates_btn)

        update_group.setLayout(update_layout)
        layout.addWidget(update_group)

        widget.setLayout(layout)
        return widget

    def _create_telegram_tab(self):
        """إنشاء تبويب إعدادات التليجرام الكامل"""
        # استخدام ScrollArea للسماح بالتمرير
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(15)

        # ═══════════════════════════════════════════════════════════
        # تفعيل التليجرام
        # ═══════════════════════════════════════════════════════════
        enable_group = QGroupBox(self.tr("تفعيل الإشعارات"))
        enable_group.setFont(QFont("Arial", 11, QFont.Bold))
        enable_layout = QHBoxLayout()

        self.telegram_enabled_check = QCheckBox(self.tr("تفعيل إشعارات التليجرام"))
        self.telegram_enabled_check.setChecked(get_setting('telegram_enabled', '0') == '1')
        self.telegram_enabled_check.setStyleSheet("font-size: 14px; font-weight: bold;")
        enable_layout.addWidget(self.telegram_enabled_check)
        enable_layout.addStretch()

        enable_group.setLayout(enable_layout)
        layout.addWidget(enable_group)

        # ═══════════════════════════════════════════════════════════
        # معلومات البوت
        # ═══════════════════════════════════════════════════════════
        bot_group = QGroupBox(self.tr("إعدادات الاتصال"))
        bot_group.setFont(QFont("Arial", 11, QFont.Bold))
        bot_layout = QFormLayout()
        bot_layout.setSpacing(10)

        self.bot_token_input = QLineEdit()
        self.bot_token_input.setText(get_setting('telegram_bot_token', ''))
        self.bot_token_input.setPlaceholderText("123456789:ABC-DEF...")
        self.bot_token_input.setMinimumHeight(35)
        self.bot_token_input.setEchoMode(QLineEdit.Password)
        bot_layout.addRow(self.tr("Bot Token:"), self.bot_token_input)

        self.chat_id_input = QLineEdit()
        self.chat_id_input.setText(get_setting('telegram_chat_id', ''))
        self.chat_id_input.setPlaceholderText("-1001234567890")
        self.chat_id_input.setMinimumHeight(35)
        bot_layout.addRow(self.tr("Chat ID:"), self.chat_id_input)

        self.topic_id_input = QLineEdit()
        self.topic_id_input.setText(get_setting('telegram_topic_id', ''))
        self.topic_id_input.setPlaceholderText(self.tr("اختياري - لمجموعات المواضيع"))
        self.topic_id_input.setMinimumHeight(35)
        bot_layout.addRow(self.tr("Topic ID:"), self.topic_id_input)

        bot_group.setLayout(bot_layout)
        layout.addWidget(bot_group)

        # زر اختبار الاتصال
        test_btn = QPushButton(self.tr("🧪 اختبار الاتصال"))
        test_btn.setMinimumHeight(45)
        test_btn.setStyleSheet("background-color: #3498db; color: white; font-weight: bold;")
        test_btn.clicked.connect(self._test_telegram_connection)
        layout.addWidget(test_btn)

        # ═══════════════════════════════════════════════════════════
        # أنواع التقارير - 16 خيار
        # ═══════════════════════════════════════════════════════════
        reports_group = QGroupBox(self.tr("أنواع الإشعارات (16 نوع)"))
        reports_group.setFont(QFont("Arial", 11, QFont.Bold))
        reports_layout = QGridLayout()
        reports_layout.setSpacing(10)

        # إنشاء Checkboxes لكل نوع تقرير
        row = 0
        col = 0
        for report_key, (arabic_name, english_name) in self.TELEGRAM_REPORT_TYPES.items():
            checkbox = QCheckBox(arabic_name)
            checkbox.setChecked(get_setting(f'telegram_{report_key}', '1') == '1')
            checkbox.setToolTip(english_name)
            checkbox.setMinimumHeight(30)
            self.telegram_checkboxes[report_key] = checkbox
            reports_layout.addWidget(checkbox, row, col)

            col += 1
            if col >= 2:  # عمودان
                col = 0
                row += 1

        # أزرار تحديد/إلغاء الكل
        select_buttons_layout = QHBoxLayout()

        select_all_btn = QPushButton(self.tr("✅ تحديد الكل"))
        select_all_btn.clicked.connect(lambda: self._toggle_all_reports(True))
        select_buttons_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton(self.tr("❌ إلغاء الكل"))
        deselect_all_btn.clicked.connect(lambda: self._toggle_all_reports(False))
        select_buttons_layout.addWidget(deselect_all_btn)

        reports_layout.addLayout(select_buttons_layout, row + 1, 0, 1, 2)

        reports_group.setLayout(reports_layout)
        layout.addWidget(reports_group)

        # ═══════════════════════════════════════════════════════════
        # إحصائيات
        # ═══════════════════════════════════════════════════════════
        stats_group = QGroupBox(self.tr("إحصائيات"))
        stats_group.setFont(QFont("Arial", 10))
        stats_layout = QFormLayout()

        # عدد الرسائل المعلقة
        try:
            cursor = db_manager.execute_query("""
                SELECT COUNT(*) as pending FROM telegram_queue
                WHERE sent_at IS NULL AND attempt_count < max_attempts
            """)
            pending = cursor.fetchone()['pending']
        except:
            pending = 0

        self.pending_label = QLabel(f"{pending}")
        stats_layout.addRow(self.tr("الرسائل المعلقة:"), self.pending_label)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # ═══════════════════════════════════════════════════════════
        # إعدادات الملخص اليومي المنفصلة
        # ═══════════════════════════════════════════════════════════
        daily_group = QGroupBox(self.tr("الملخص اليومي (بوت منفصل)"))
        daily_group.setFont(QFont("Arial", 11, QFont.Bold))
        daily_layout = QFormLayout()
        daily_layout.setSpacing(10)

        self.daily_separate_bot = QCheckBox(self.tr("استخدام بوت منفصل للملخص اليومي"))
        self.daily_separate_bot.setChecked(get_setting('daily_summary_separate_bot', '0') == '1')
        daily_layout.addRow(self.daily_separate_bot)

        self.daily_bot_token = QLineEdit()
        self.daily_bot_token.setText(get_setting('daily_summary_bot_token', ''))
        self.daily_bot_token.setPlaceholderText(self.tr("Bot Token للملخص اليومي"))
        self.daily_bot_token.setMinimumHeight(35)
        self.daily_bot_token.setEchoMode(QLineEdit.Password)
        daily_layout.addRow(self.tr("Bot Token:"), self.daily_bot_token)

        self.daily_chat_id = QLineEdit()
        self.daily_chat_id.setText(get_setting('daily_summary_chat_id', ''))
        self.daily_chat_id.setPlaceholderText(self.tr("Chat ID للملخص اليومي"))
        self.daily_chat_id.setMinimumHeight(35)
        daily_layout.addRow(self.tr("Chat ID:"), self.daily_chat_id)

        self.daily_topic_id = QLineEdit()
        self.daily_topic_id.setText(get_setting('daily_summary_topic_id', ''))
        self.daily_topic_id.setPlaceholderText(self.tr("Topic ID (اختياري)"))
        self.daily_topic_id.setMinimumHeight(35)
        daily_layout.addRow(self.tr("Topic ID:"), self.daily_topic_id)

        # وقت الملخص اليومي - استخدام QTimeEdit بدلاً من QLineEdit
        self.daily_summary_time = QTimeEdit()
        self.daily_summary_time.setLayoutDirection(Qt.LeftToRight)  # منع انعكاس الأرقام في RTL
        saved_time = get_setting('daily_summary_time', '00:00')
        try:
            hour, minute = map(int, saved_time.split(':'))
            self.daily_summary_time.setTime(QTime(hour, minute))
        except:
            self.daily_summary_time.setTime(QTime(0, 0))
        self.daily_summary_time.setDisplayFormat("HH:mm")
        self.daily_summary_time.setMinimumHeight(40)
        self.daily_summary_time.setToolTip(self.tr("وقت إرسال الملخص اليومي (24 ساعة)"))
        self.daily_summary_time.setStyleSheet("font-size: 14px; font-weight: bold;")
        daily_layout.addRow(self.tr("وقت الملخص اليومي:"), self.daily_summary_time)

        # زر إرسال الملخص اليومي الآن (للاختبار)
        send_daily_btn = QPushButton(self.tr("📊 إرسال الملخص اليومي الآن"))
        send_daily_btn.setMinimumHeight(40)
        send_daily_btn.setStyleSheet("background-color: #9b59b6; color: white; font-weight: bold;")
        send_daily_btn.clicked.connect(self._send_daily_summary_now)
        daily_layout.addRow(send_daily_btn)

        daily_group.setLayout(daily_layout)
        layout.addWidget(daily_group)

        layout.addStretch()
        widget.setLayout(layout)
        scroll.setWidget(widget)
        return scroll

    def _toggle_all_reports(self, checked: bool):
        """تحديد/إلغاء جميع التقارير"""
        for checkbox in self.telegram_checkboxes.values():
            checkbox.setChecked(checked)

    def _create_printing_tab(self):
        """إنشاء تبويب إعدادات الطباعة"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)

        # استيراد مدير الطابعة
        from src.utils.printer import printer_manager

        # ═══════════════════════════════════════════════════════════
        # إعدادات الطابعة
        # ═══════════════════════════════════════════════════════════
        printer_group = QGroupBox(self.tr("إعدادات الطابعة"))
        printer_group.setFont(QFont("Arial", 11, QFont.Bold))
        printer_layout = QFormLayout()
        printer_layout.setSpacing(10)

        # اختيار الطابعة
        self.printer_combo = QComboBox()
        self.printer_combo.setMinimumHeight(35)

        # تعبئة الطابعات المتاحة
        available_printers = printer_manager.get_available_printers()
        if available_printers:
            self.printer_combo.addItems(available_printers)
        else:
            self.printer_combo.addItem(self.tr("لا توجد طابعات"))

        current_printer = get_setting('printer_name', '')
        if current_printer in available_printers:
            self.printer_combo.setCurrentText(current_printer)

        printer_layout.addRow(self.tr("الطابعة الافتراضية:"), self.printer_combo)

        # عرض الورق
        self.paper_width_combo = QComboBox()
        self.paper_width_combo.setMinimumHeight(35)
        self.paper_width_combo.addItems(["80mm", "58mm"])

        current_width = get_setting('printer_paper_width', '80')
        self.paper_width_combo.setCurrentText(f"{current_width}mm")

        printer_layout.addRow(self.tr("عرض الورق:"), self.paper_width_combo)

        printer_group.setLayout(printer_layout)
        layout.addWidget(printer_group)

        # ═══════════════════════════════════════════════════════════
        # إعدادات الفاتورة
        # ═══════════════════════════════════════════════════════════
        receipt_group = QGroupBox(self.tr("محتوى الفاتورة"))
        receipt_group.setFont(QFont("Arial", 11, QFont.Bold))
        receipt_layout = QFormLayout()
        receipt_layout.setSpacing(10)

        self.receipt_header_text = QTextEdit()
        self.receipt_header_text.setPlainText(get_setting('receipt_header', ''))
        self.receipt_header_text.setMaximumHeight(60)
        self.receipt_header_text.setPlaceholderText(self.tr("مثال: مرحباً بكم في مطعمنا"))
        receipt_layout.addRow(self.tr("نص رأس الفاتورة:"), self.receipt_header_text)

        self.receipt_footer_text = QTextEdit()
        self.receipt_footer_text.setPlainText(get_setting('receipt_footer', 'شكراً لزيارتكم'))
        self.receipt_footer_text.setMaximumHeight(60)
        self.receipt_footer_text.setPlaceholderText(self.tr("مثال: نسعد بخدمتكم دائماً"))
        receipt_layout.addRow(self.tr("نص تذييل الفاتورة:"), self.receipt_footer_text)

        receipt_group.setLayout(receipt_layout)
        layout.addWidget(receipt_group)

        # ═══════════════════════════════════════════════════════════
        # إعدادات إضافية
        # ═══════════════════════════════════════════════════════════
        extra_group = QGroupBox(self.tr("خيارات إضافية"))
        extra_group.setFont(QFont("Arial", 11, QFont.Bold))
        extra_layout = QVBoxLayout()

        self.kitchen_printer_enabled = QCheckBox(self.tr("تفعيل طباعة تذكرة المطبخ"))
        self.kitchen_printer_enabled.setChecked(get_setting('kitchen_printer_enabled', '0') == '1')
        extra_layout.addWidget(self.kitchen_printer_enabled)

        self.auto_cut_enabled = QCheckBox(self.tr("قص الورق تلقائياً"))
        self.auto_cut_enabled.setChecked(get_setting('printer_auto_cut', '1') == '1')
        extra_layout.addWidget(self.auto_cut_enabled)

        extra_group.setLayout(extra_layout)
        layout.addWidget(extra_group)

        # زر طباعة تجريبية
        test_print_button = QPushButton(self.tr("🖨️ طباعة صفحة تجريبية"))
        test_print_button.setMinimumHeight(45)
        test_print_button.setStyleSheet("background-color: #34495e; color: white; font-weight: bold;")
        test_print_button.clicked.connect(self._test_printer)
        layout.addWidget(test_print_button)

        widget.setLayout(layout)
        return widget

    def _create_data_management_tab(self):
        """إنشاء تبويب إدارة البيانات (الخيارات الخطيرة)"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)

        # تحذير
        warning_label = QLabel(self.tr("⚠️ تحذير: هذه العمليات لا يمكن التراجع عنها!"))
        warning_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px; padding: 10px;")
        layout.addWidget(warning_label)

        # مجموعة حذف البيانات
        delete_group = QGroupBox(self.tr("حذف البيانات"))
        delete_group.setFont(QFont("Arial", 11, QFont.Bold))
        delete_layout = QVBoxLayout()
        delete_layout.setSpacing(15)

        # حذف جميع المنتجات
        products_frame = QFrame()
        products_frame.setStyleSheet("background-color: #ffebee; border-radius: 5px; padding: 10px;")
        products_layout = QVBoxLayout(products_frame)

        products_label = QLabel(self.tr("🗑️ حذف جميع المنتجات"))
        products_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        products_layout.addWidget(products_label)

        products_desc = QLabel(self.tr("سيتم حذف جميع المنتجات نهائياً من قاعدة البيانات"))
        products_desc.setStyleSheet("color: #666;")
        products_layout.addWidget(products_desc)

        delete_products_btn = QPushButton(self.tr("🗑️ حذف جميع المنتجات"))
        delete_products_btn.setMinimumHeight(45)
        delete_products_btn.setStyleSheet("background-color: #c62828; color: white; font-weight: bold;")
        delete_products_btn.clicked.connect(lambda: self._delete_all_data('products'))
        products_layout.addWidget(delete_products_btn)

        delete_layout.addWidget(products_frame)

        # حذف جميع الفئات
        categories_frame = QFrame()
        categories_frame.setStyleSheet("background-color: #fff3e0; border-radius: 5px; padding: 10px;")
        categories_layout = QVBoxLayout(categories_frame)

        categories_label = QLabel(self.tr("🗂️ حذف جميع الفئات"))
        categories_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        categories_layout.addWidget(categories_label)

        categories_desc = QLabel(self.tr("سيتم حذف جميع الفئات نهائياً من قاعدة البيانات"))
        categories_desc.setStyleSheet("color: #666;")
        categories_layout.addWidget(categories_desc)

        delete_categories_btn = QPushButton(self.tr("🗂️ حذف جميع الفئات"))
        delete_categories_btn.setMinimumHeight(45)
        delete_categories_btn.setStyleSheet("background-color: #e65100; color: white; font-weight: bold;")
        delete_categories_btn.clicked.connect(lambda: self._delete_all_data('categories'))
        categories_layout.addWidget(delete_categories_btn)

        delete_layout.addWidget(categories_frame)

        # حذف جميع المكونات
        ingredients_frame = QFrame()
        ingredients_frame.setStyleSheet("background-color: #e8f5e9; border-radius: 5px; padding: 10px;")
        ingredients_layout = QVBoxLayout(ingredients_frame)

        ingredients_label = QLabel(self.tr("🥗 حذف جميع المكونات"))
        ingredients_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        ingredients_layout.addWidget(ingredients_label)

        ingredients_desc = QLabel(self.tr("سيتم حذف جميع المكونات والوصفات نهائياً"))
        ingredients_desc.setStyleSheet("color: #666;")
        ingredients_layout.addWidget(ingredients_desc)

        delete_ingredients_btn = QPushButton(self.tr("🥗 حذف جميع المكونات"))
        delete_ingredients_btn.setMinimumHeight(45)
        delete_ingredients_btn.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold;")
        delete_ingredients_btn.clicked.connect(lambda: self._delete_all_data('ingredients'))
        ingredients_layout.addWidget(delete_ingredients_btn)

        delete_layout.addWidget(ingredients_frame)

        delete_group.setLayout(delete_layout)
        layout.addWidget(delete_group)

        # الرقم السري
        password_group = QGroupBox(self.tr("الرقم السري للحذف"))
        password_group.setFont(QFont("Arial", 11, QFont.Bold))
        password_layout = QFormLayout()
        password_layout.setSpacing(10)

        self.delete_password_input = QLineEdit()
        self.delete_password_input.setText(get_setting('delete_password', '1234'))
        self.delete_password_input.setEchoMode(QLineEdit.Password)
        self.delete_password_input.setMinimumHeight(35)
        password_layout.addRow(self.tr("تعيين الرقم السري:"), self.delete_password_input)

        password_group.setLayout(password_layout)
        layout.addWidget(password_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _delete_all_data(self, data_type: str):
        """حذف جميع البيانات من نوع معين مع التحقق من الرقم السري"""
        from PyQt5.QtWidgets import QInputDialog

        type_names = {
            'products': ('المنتجات', 'products'),
            'categories': ('الفئات', 'categories'),
            'ingredients': ('المكونات', 'ingredients')
        }

        type_name, table_name = type_names.get(data_type, ('', ''))

        # الخطوة 1: تأكيد الحذف
        reply = QMessageBox.warning(
            self,
            self.tr("تحذير خطير!"),
            self.tr(f"⚠️ أنت على وشك حذف جميع {type_name}!\n\nهذا الإجراء لا يمكن التراجع عنه!\n\nهل تريد المتابعة؟"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # الخطوة 2: كتابة DELETE للتأكيد
        confirm_text, ok = QInputDialog.getText(
            self,
            self.tr("تأكيد الحذف"),
            self.tr("اكتب DELETE للتأكيد:"),
        )

        if not ok or confirm_text.upper() != "DELETE":
            QMessageBox.information(self, self.tr("إلغاء"), self.tr("تم إلغاء عملية الحذف"))
            return

        # الخطوة 3: إدخال الرقم السري
        password, ok = QInputDialog.getText(
            self,
            self.tr("الرقم السري"),
            self.tr("أدخل الرقم السري للحذف:"),
            QLineEdit.Password
        )

        if not ok:
            return

        stored_password = get_setting('delete_password', '1234')
        if password != stored_password:
            QMessageBox.critical(self, self.tr("خطأ"), self.tr("الرقم السري غير صحيح!"))
            return

        # تنفيذ الحذف
        try:
            if data_type == 'products':
                db_manager.execute_query("DELETE FROM products")
                count_query = "SELECT 0 as count"
            elif data_type == 'categories':
                db_manager.execute_query("DELETE FROM categories")
                count_query = "SELECT 0 as count"
            elif data_type == 'ingredients':
                db_manager.execute_query("DELETE FROM recipes")  # حذف الوصفات أولاً
                db_manager.execute_query("DELETE FROM ingredients")
                count_query = "SELECT 0 as count"

            db_manager.commit()

            QMessageBox.information(
                self,
                self.tr("نجاح"),
                self.tr(f"✅ تم حذف جميع {type_name} بنجاح!")
            )

            logger.warning(f"All {data_type} deleted by user")

        except Exception as e:
            db_manager.rollback()
            logger.error(f"Error deleting all {data_type}: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr(f"حدث خطأ أثناء الحذف:\n{str(e)}"))

    def _create_backup_tab(self):
        """إنشاء تبويب النسخ الاحتياطي"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)

        # إعدادات النسخ الاحتياطي التلقائي
        backup_group = QGroupBox(self.tr("النسخ الاحتياطي التلقائي"))
        backup_group.setFont(QFont("Arial", 11, QFont.Bold))
        backup_layout = QFormLayout()
        backup_layout.setSpacing(10)

        self.auto_backup_check = QCheckBox(self.tr("تفعيل النسخ الاحتياطي التلقائي"))
        self.auto_backup_check.setChecked(get_setting('auto_backup', '1') == '1')
        backup_layout.addRow(self.auto_backup_check)

        # فترة النسخ الاحتياطي (بالساعات)
        self.backup_interval_spin = QSpinBox()
        self.backup_interval_spin.setRange(1, 168)  # من ساعة إلى أسبوع
        self.backup_interval_spin.setValue(int(get_setting('backup_interval_hours', '24')))
        self.backup_interval_spin.setSuffix(self.tr(" ساعة"))
        self.backup_interval_spin.setMinimumHeight(35)
        self.backup_interval_spin.setToolTip(self.tr("الفترة بين كل نسخة احتياطية تلقائية"))
        backup_layout.addRow(self.tr("فترة النسخ التلقائي:"), self.backup_interval_spin)

        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)

        # إدارة النسخ الاحتياطية
        manage_group = QGroupBox(self.tr("إدارة النسخ الاحتياطية"))
        manage_group.setFont(QFont("Arial", 11, QFont.Bold))
        manage_layout = QFormLayout()
        manage_layout.setSpacing(10)

        # الحد الأقصى لعدد النسخ
        self.max_backups_spin = QSpinBox()
        self.max_backups_spin.setRange(5, 500)
        self.max_backups_spin.setValue(int(get_setting('max_backups', '30')))
        self.max_backups_spin.setSuffix(self.tr(" نسخة"))
        self.max_backups_spin.setMinimumHeight(35)
        self.max_backups_spin.setToolTip(self.tr("إذا تجاوز العدد، يتم حذف الأقدم"))
        manage_layout.addRow(self.tr("الحد الأقصى للنسخ:"), self.max_backups_spin)

        # حذف النسخ الأقدم من عدد أيام معين
        self.delete_old_backups_check = QCheckBox(self.tr("حذف النسخ الأقدم من:"))
        self.delete_old_backups_check.setChecked(get_setting('delete_old_backups', '0') == '1')
        manage_layout.addRow(self.delete_old_backups_check)

        self.backup_retention_days_spin = QSpinBox()
        self.backup_retention_days_spin.setRange(7, 365)
        self.backup_retention_days_spin.setValue(int(get_setting('backup_retention_days', '180')))
        self.backup_retention_days_spin.setSuffix(self.tr(" يوم"))
        self.backup_retention_days_spin.setMinimumHeight(35)
        self.backup_retention_days_spin.setToolTip(self.tr("النسخ الأقدم من هذا العدد من الأيام سيتم حذفها تلقائياً"))
        manage_layout.addRow(self.tr("عمر النسخ الاحتياطية:"), self.backup_retention_days_spin)

        manage_group.setLayout(manage_layout)
        layout.addWidget(manage_group)

        # أزرار التحكم
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self.backup_now_btn = QPushButton(self.tr("💾 نسخ احتياطي الآن"))
        self.backup_now_btn.setMinimumHeight(45)
        self.backup_now_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.backup_now_btn.clicked.connect(self._create_backup)
        buttons_layout.addWidget(self.backup_now_btn)

        self.restore_backup_btn = QPushButton(self.tr("🔄 استعادة نسخة"))
        self.restore_backup_btn.setMinimumHeight(45)
        self.restore_backup_btn.setStyleSheet("background-color: #3498db; color: white; font-weight: bold;")
        self.restore_backup_btn.clicked.connect(self._restore_backup)
        buttons_layout.addWidget(self.restore_backup_btn)

        layout.addLayout(buttons_layout)

        # زر تنظيف النسخ القديمة يدوياً
        cleanup_btn = QPushButton(self.tr("🗑️ تنظيف النسخ القديمة الآن"))
        cleanup_btn.setMinimumHeight(40)
        cleanup_btn.setStyleSheet("background-color: #e74c3c; color: white;")
        cleanup_btn.clicked.connect(self._cleanup_old_backups)
        layout.addWidget(cleanup_btn)

        widget.setLayout(layout)
        return widget

    def _upload_logo(self):
        """تحميل شعار المطعم"""
        import os
        import shutil

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("اختر صورة الشعار"),
            "",
            self.tr("Images (*.png *.jpg *.jpeg *.bmp)")
        )

        if file_path:
            try:
                # إنشاء مجلد للشعارات
                logo_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'assets', 'logos')
                os.makedirs(logo_dir, exist_ok=True)

                # نسخ الصورة
                logo_filename = 'restaurant_logo' + os.path.splitext(file_path)[1]
                dest_path = os.path.join(logo_dir, logo_filename)
                shutil.copy2(file_path, dest_path)

                # حفظ المسار في الإعدادات
                set_setting('restaurant_logo', dest_path)

                # تحديث المعاينة
                pixmap = QPixmap(dest_path).scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.logo_preview.setPixmap(pixmap)

                QMessageBox.information(self, self.tr("نجاح"), self.tr("تم تحميل الشعار بنجاح! ✅"))

            except Exception as e:
                logger.error(f"خطأ في تحميل الشعار: {e}")
                QMessageBox.warning(self, self.tr("خطأ"), self.tr(f"فشل تحميل الشعار: {e}"))

    def _remove_logo(self):
        """إزالة شعار المطعم"""
        set_setting('restaurant_logo', '')
        self.logo_preview.clear()
        self.logo_preview.setText(self.tr("لا يوجد شعار"))
        QMessageBox.information(self, self.tr("تم"), self.tr("تم إزالة الشعار"))

    def _test_telegram_connection(self):
        """اختبار اتصال التليجرام"""
        try:
            import requests

            bot_token = self.bot_token_input.text().strip()
            chat_id = self.chat_id_input.text().strip()
            topic_id = self.topic_id_input.text().strip()

            if not bot_token or not chat_id:
                QMessageBox.warning(self, self.tr("تحذير"), self.tr("الرجاء إدخال Bot Token و Chat ID"))
                return

            # اختبار الاتصال
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': '✅ اختبار اتصال من نظام نقاط البيع\n\nConnection test successful!',
                'parse_mode': 'HTML'
            }

            if topic_id:
                data['message_thread_id'] = topic_id

            response = requests.post(url, json=data, timeout=10)

            if response.status_code == 200:
                QMessageBox.information(self, self.tr("نجاح"), self.tr("تم اختبار الاتصال بنجاح! ✅"))
            else:
                error = response.json().get('description', 'Unknown error')
                QMessageBox.warning(self, self.tr("فشل"), self.tr(f"فشل الاتصال:\n{error}"))

        except Exception as e:
            logger.error(f"خطأ في اختبار التليجرام: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr(f"حدث خطأ أثناء اختبار الاتصال:\n{str(e)}"))

    def _send_daily_summary_now(self):
        """إرسال الملخص اليومي فوراً للاختبار"""
        try:
            from src.utils.telegram import get_telegram_manager
            telegram = get_telegram_manager()

            # إنشاء وإرسال التقرير
            summary_data = telegram._generate_daily_report_data()
            telegram.send_daily_summary(summary_data)

            QMessageBox.information(
                self,
                self.tr("نجاح"),
                self.tr("تم إرسال الملخص اليومي بنجاح! ✅\n\nتحقق من التليجرام.")
            )

        except Exception as e:
            logger.error(f"خطأ في إرسال الملخص اليومي: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr(f"حدث خطأ:\n{str(e)}"))

    def _create_backup(self):
        """إنشاء نسخة احتياطية"""
        try:
            import shutil
            from datetime import datetime
            from pathlib import Path
            import os

            # المجلد الافتراضي للنسخ الاحتياطية
            default_backup_dir = Path("backups")
            default_backup_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"pos_backup_{timestamp}.db"

            # السماح للمستخدم باختيار مكان الحفظ
            backup_path, _ = QFileDialog.getSaveFileName(
                self,
                self.tr("حفظ النسخة الاحتياطية"),
                str(default_backup_dir / default_name),
                self.tr("Database Files (*.db)")
            )

            if not backup_path:
                return  # المستخدم ألغى العملية

            # نسخ قاعدة البيانات
            shutil.copy2("pos_system.db", backup_path)

            # حذف النسخ القديمة من المجلد الافتراضي فقط
            if default_backup_dir.exists():
                backups = sorted(default_backup_dir.glob("pos_backup_*.db"))
                max_backups = int(get_setting('max_backups', '30'))

                while len(backups) > max_backups:
                    backups[0].unlink()
                    backups.pop(0)

            QMessageBox.information(
                self,
                self.tr("نجاح"),
                self.tr(f"تم إنشاء نسخة احتياطية:\n{Path(backup_path).name}\n\nالمسار:\n{backup_path}")
            )

            # حذف النسخ القديمة حسب العمر (إذا كان مفعلاً)
            if get_setting('delete_old_backups', '0') == '1':
                self._delete_backups_older_than_days(int(get_setting('backup_retention_days', '180')))

        except Exception as e:
            logger.error(f"خطأ في إنشاء النسخة الاحتياطية: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr("حدث خطأ أثناء إنشاء النسخة الاحتياطية"))

    def _restore_backup(self):
        """استعادة نسخة احتياطية"""
        try:
            import shutil
            from pathlib import Path
            from datetime import datetime
            import os

            # تحديد المجلد الافتراضي للبحث
            default_backup_dir = Path("backups")
            if default_backup_dir.exists():
                start_dir = str(default_backup_dir)
            else:
                start_dir = os.path.expanduser("~")  # مجلد المستخدم الرئيسي

            # اختيار ملف النسخة الاحتياطية من أي مكان
            backup_file, _ = QFileDialog.getOpenFileName(
                self,
                self.tr("اختر نسخة احتياطية للاستعادة"),
                start_dir,
                self.tr("Database Files (*.db);;All Files (*)")
            )

            if not backup_file:
                return

            # التحقق من أن الملف موجود
            if not Path(backup_file).exists():
                QMessageBox.critical(self, self.tr("خطأ"), self.tr("الملف المحدد غير موجود"))
                return

            # تأكيد الاستعادة
            reply = QMessageBox.warning(
                self,
                self.tr("⚠️ تحذير هام!"),
                self.tr(
                    "هل أنت متأكد من استعادة هذه النسخة الاحتياطية؟\n\n"
                    "⚠️ سيتم استبدال قاعدة البيانات الحالية بالكامل!\n"
                    "⚠️ جميع البيانات الحالية ستُفقد!\n\n"
                    f"الملف: {Path(backup_file).name}"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # إغلاق اتصال قاعدة البيانات
            try:
                db_manager.close()
            except:
                pass

            # نسخ النسخة الاحتياطية
            db_path = Path("pos_system.db")

            # إنشاء نسخة من قاعدة البيانات الحالية قبل الاستعادة
            if db_path.exists():
                default_backup_dir.mkdir(exist_ok=True)  # التأكد من وجود المجلد
                backup_current = default_backup_dir / f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy2(db_path, backup_current)
                logger.info(f"Created pre-restore backup: {backup_current}")

            # استعادة النسخة الاحتياطية
            shutil.copy2(backup_file, db_path)
            logger.info(f"Restored backup from: {backup_file}")

            QMessageBox.information(
                self,
                self.tr("✅ نجاح"),
                self.tr(
                    "تم استعادة النسخة الاحتياطية بنجاح!\n\n"
                    "يجب إعادة تشغيل البرنامج لتطبيق التغييرات.\n"
                    "سيتم إغلاق البرنامج الآن."
                )
            )

            # إغلاق التطبيق
            import sys
            from PyQt5.QtWidgets import QApplication
            QApplication.quit()

        except Exception as e:
            logger.error(f"خطأ في استعادة النسخة الاحتياطية: {e}")
            QMessageBox.critical(
                self,
                self.tr("خطأ"),
                self.tr(f"حدث خطأ أثناء استعادة النسخة الاحتياطية:\n{str(e)}")
            )

    def _cleanup_old_backups(self):
        """تنظيف النسخ القديمة يدوياً"""
        try:
            from pathlib import Path
            from datetime import datetime, timedelta

            backup_dir = Path("backups")
            if not backup_dir.exists():
                QMessageBox.information(self, self.tr("معلومات"), self.tr("لا توجد نسخ احتياطية"))
                return

            retention_days = self.backup_retention_days_spin.value()
            deleted_count = self._delete_backups_older_than_days(retention_days)

            QMessageBox.information(
                self,
                self.tr("تنظيف مكتمل"),
                self.tr(f"تم حذف {deleted_count} نسخة احتياطية قديمة\n(أقدم من {retention_days} يوم)")
            )

        except Exception as e:
            logger.error(f"خطأ في تنظيف النسخ: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr(f"حدث خطأ: {str(e)}"))

    def _delete_backups_older_than_days(self, days: int) -> int:
        """حذف النسخ الأقدم من عدد أيام معين"""
        from pathlib import Path
        from datetime import datetime, timedelta
        import os

        backup_dir = Path("backups")
        if not backup_dir.exists():
            return 0

        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0

        for backup_file in backup_dir.glob("pos_backup_*.db"):
            try:
                # استخراج التاريخ من اسم الملف: pos_backup_YYYYMMDD_HHMMSS.db
                filename = backup_file.stem  # pos_backup_20241222_123456
                date_str = filename.replace("pos_backup_", "")[:8]  # 20241222
                file_date = datetime.strptime(date_str, "%Y%m%d")

                if file_date < cutoff_date:
                    backup_file.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old backup: {backup_file.name}")
            except Exception as e:
                logger.warning(f"Could not process backup file {backup_file}: {e}")

        return deleted_count

    def _test_printer(self):
        """طباعة صفحة تجريبية"""
        try:
            from src.utils.printer import printer_manager
            from datetime import datetime

            printer_name = self.printer_combo.currentText()
            printer_manager.set_printer(printer_name)

            success, error = printer_manager.print_text(
                "تجربة طباعة ناجحة\n"
                "Printer Test Successful\n"
                "--------------------------------\n"
                f"Printer: {printer_name}\n"
                f"Time: {datetime.now().strftime('%H:%M:%S')}\n"
            )

            if success:
                QMessageBox.information(self, self.tr("نجاح"), self.tr("تم إرسال أمر الطباعة بنجاح"))
            else:
                QMessageBox.warning(self, self.tr("فشل"), self.tr(f"فشل الطباعة: {error}"))

        except Exception as e:
            logger.error(f"Printer test error: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr(f"حدث خطأ: {str(e)}"))

    def _open_update_dialog(self):
        """فتح نافذة التحديث"""
        try:
            from src.ui.update_dialog import UpdateDialog
            dialog = UpdateDialog(self)
            dialog.exec_()
        except Exception as e:
            logger.error(f"Error opening update dialog: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr(f"حدث خطأ: {e}"))

    def _save_settings(self):
        """حفظ الإعدادات"""
        try:
            # معلومات المطعم
            set_setting('company_name', self.company_name_input.text().strip())
            set_setting('vat_number', self.vat_number_input.text().strip())
            set_setting('currency', self.currency_combo.currentText())

            # شعار المطعم
            set_setting('print_logo', '1' if self.print_logo_check.isChecked() else '0')

            # الإعدادات العامة
            set_setting('language', self.language_combo.currentText())
            set_setting('tax_rate', str(self.tax_rate_spin.value() / 100))
            set_setting('tax_inclusive', '1' if self.tax_inclusive_check.isChecked() else '0')
            set_setting('require_card_reference', '1' if self.require_card_reference.isChecked() else '0')

            # الملاك والموظفين
            set_setting('owners', self.owners_input.text().strip() or 'المالك')
            set_setting('employees', self.employees_input.text().strip() or 'موظف 1')

            # التليجرام - الإعدادات الأساسية
            set_setting('telegram_enabled', '1' if self.telegram_enabled_check.isChecked() else '0')
            set_setting('telegram_bot_token', self.bot_token_input.text().strip())
            set_setting('telegram_chat_id', self.chat_id_input.text().strip())
            set_setting('telegram_topic_id', self.topic_id_input.text().strip())

            # التليجرام - أنواع التقارير (16 نوع)
            for report_key, checkbox in self.telegram_checkboxes.items():
                set_setting(f'telegram_{report_key}', '1' if checkbox.isChecked() else '0')

            # التليجرام - الملخص اليومي المنفصل
            set_setting('daily_summary_separate_bot', '1' if self.daily_separate_bot.isChecked() else '0')
            set_setting('daily_summary_bot_token', self.daily_bot_token.text().strip())
            set_setting('daily_summary_chat_id', self.daily_chat_id.text().strip())
            set_setting('daily_summary_topic_id', self.daily_topic_id.text().strip())
            set_setting('daily_summary_time', self.daily_summary_time.time().toString("HH:mm"))

            # الطباعة
            set_setting('receipt_header', self.receipt_header_text.toPlainText().strip())
            set_setting('receipt_footer', self.receipt_footer_text.toPlainText().strip())
            set_setting('kitchen_printer_enabled', '1' if self.kitchen_printer_enabled.isChecked() else '0')

            # إعدادات الطابعة الجديدة
            set_setting('printer_name', self.printer_combo.currentText())
            set_setting('printer_paper_width', self.paper_width_combo.currentText().replace('mm', ''))
            set_setting('printer_auto_cut', '1' if self.auto_cut_enabled.isChecked() else '0')

            # تحديث مدير الطابعة
            from src.utils.printer import printer_manager
            printer_manager.set_printer(self.printer_combo.currentText())

            # النسخ الاحتياطي
            set_setting('auto_backup', '1' if self.auto_backup_check.isChecked() else '0')
            set_setting('backup_interval_hours', str(self.backup_interval_spin.value()))
            set_setting('max_backups', str(self.max_backups_spin.value()))
            set_setting('delete_old_backups', '1' if self.delete_old_backups_check.isChecked() else '0')
            set_setting('backup_retention_days', str(self.backup_retention_days_spin.value()))

            # الرقم السري للحذف
            if hasattr(self, 'delete_password_input'):
                set_setting('delete_password', self.delete_password_input.text().strip() or '1234')

            QMessageBox.information(self, self.tr("نجاح"), self.tr("تم حفظ الإعدادات بنجاح ✅"))
            self.accept()

        except Exception as e:
            logger.error(f"خطأ في حفظ الإعدادات: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), self.tr("حدث خطأ أثناء حفظ الإعدادات"))
