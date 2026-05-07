"""
نافذة إضافة/تعديل مكون
Ingredient Dialog
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDoubleSpinBox,
    QPushButton, QHBoxLayout, QMessageBox
)
from PyQt5.QtGui import QFont
from database import db_manager
from loguru import logger


class IngredientDialog(QDialog):
    def __init__(self, parent=None, ingredient_data: dict = None):
        super().__init__(parent)
        self.ingredient_data = ingredient_data  # للتعديل
        self.setWindowTitle(
            self.tr("تعديل مكون") if ingredient_data else self.tr("إضافة مكون")
        )
        self.setFixedSize(400, 400)
        self._setup_ui()

        # إذا كانت بيانات موجودة، املأ الحقول
        if self.ingredient_data:
            self._fill_data()

    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QFormLayout()
        form.setSpacing(10)

        # الاسم
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(self.tr("مطلوب"))
        form.addRow(self.tr("الاسم:"), self.name_input)

        # الوحدة
        self.unit_input = QLineEdit()
        self.unit_input.setPlaceholderText(self.tr("kg, liter, piece"))
        form.addRow(self.tr("الوحدة:"), self.unit_input)

        # الكمية
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0, 10000)
        self.quantity_spin.setDecimals(2)
        form.addRow(self.tr("الكمية:"), self.quantity_spin)

        # الحد الأدنى
        self.min_alert_spin = QDoubleSpinBox()
        self.min_alert_spin.setRange(0, 1000)
        self.min_alert_spin.setDecimals(2)
        form.addRow(self.tr("الحد الأدنى للتنبيه:"), self.min_alert_spin)

        # سعر الوحدة
        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0, 10000)
        self.cost_spin.setDecimals(2)
        self.cost_spin.setSuffix(" " + self.tr("ريال"))
        form.addRow(self.tr("سعر الوحدة:"), self.cost_spin)

        layout.addLayout(form)

        # الأزرار
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        cancel_btn = QPushButton(self.tr("إلغاء"))
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton(self.tr("حفظ"))
        save_btn.clicked.connect(self._save_ingredient)
        buttons_layout.addWidget(save_btn)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def _fill_data(self):
        """ملء الحقول بالبيانات الموجودة"""
        self.name_input.setText(self.ingredient_data['name'])
        self.unit_input.setText(self.ingredient_data['unit'])
        self.quantity_spin.setValue(self.ingredient_data['quantity'])
        self.min_alert_spin.setValue(self.ingredient_data['min_alert_level'])
        self.cost_spin.setValue(self.ingredient_data['cost_per_unit'])

    def _save_ingredient(self):
        """حفظ المكون"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, self.tr("تحذير"), self.tr("الاسم مطلوب"))
            return

        try:
            if self.ingredient_data:
                # تحديث
                db_manager.execute_query(
                    """UPDATE ingredients SET name = ?, unit = ?, quantity = ?,
                       min_alert_level = ?, cost_per_unit = ? WHERE id = ?""",
                    (name, self.unit_input.text(), self.quantity_spin.value(),
                     self.min_alert_spin.value(), self.cost_spin.value(),
                     self.ingredient_data['id'])
                )
            else:
                # إضافة
                db_manager.execute_query(
                    """INSERT INTO ingredients (name, unit, quantity, min_alert_level, cost_per_unit, is_active)
                       VALUES (?, ?, ?, ?, ?, 1)""",
                    (name, self.unit_input.text(), self.quantity_spin.value(),
                     self.min_alert_spin.value(), self.cost_spin.value())
                )

            db_manager.commit()
            self.accept()

        except Exception as e:
            db_manager.rollback()
            logger.error(f"خطأ في حفظ المكون: {e}")
            QMessageBox.critical(self, self.tr("خطأ"), str(e))
