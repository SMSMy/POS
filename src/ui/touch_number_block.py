"""
كتلة رقمية لمسية لإدخال المبالغ
Touch Number Block for amount input
"""

from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                             QLineEdit, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class TouchNumberBlock(QWidget):
    """كتلة لمسية: عنوان + شاشة رقمية + زرا +/–"""
    valueChanged = pyqtSignal(float)

    def __init__(self, title="المبلغ", suffix=" ر.س", maxVal=999999, parent=None):
        super().__init__(parent)
        self.suffix = suffix
        self._max = maxVal
        self._val = 0.0
        self._step = 1.0  # قيمة افتراضية ثابتة
        self._color = "#27ae60"  # لون افتراضي ثابت
        self._title_text = title
        self._setupUi()
        self._syncLine()

    # ---------- إنشاء الواجهة ----------
    def _setupUi(self):
        main = QVBoxLayout(self)
        main.setSpacing(6)
        main.setContentsMargins(0, 0, 0, 0)

        # العنوان
        self.title = QLabel(self._title_text)
        self.title.setFont(QFont("Arial", 13, QFont.Bold))
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet(f"color: {self._color};")
        main.addWidget(self.title)

        # الصف الأوسط: –  الشاشة  +
        mid = QHBoxLayout()
        mid.setSpacing(4)

        self.minusBtn = QPushButton("–")
        self.minusBtn.setFixedSize(70, 60)
        self.minusBtn.setFont(QFont("Arial", 24, QFont.Bold))
        self.minusBtn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color};
                color: white;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:pressed {{
                background-color: #1a7a3a;
            }}
        """)
        self.minusBtn.clicked.connect(lambda: self._step_value(-self._step))

        self.screen = QLineEdit()
        self.screen.setFont(QFont("Arial", 22, QFont.Bold))
        self.screen.setAlignment(Qt.AlignCenter)
        self.screen.setReadOnly(True)
        self.screen.setMinimumHeight(55)
        self.screen.setStyleSheet(f"""
            QLineEdit {{
                background: #1a1a1a;
                color: #00ff00;
                border: 3px solid {self._color};
                border-radius: 8px;
                padding: 4px;
            }}
        """)

        self.plusBtn = QPushButton("+")
        self.plusBtn.setFixedSize(70, 60)
        self.plusBtn.setFont(QFont("Arial", 24, QFont.Bold))
        self.plusBtn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color};
                color: white;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:pressed {{
                background-color: #1a7a3a;
            }}
        """)
        self.plusBtn.clicked.connect(lambda: self._step_value(self._step))

        mid.addWidget(self.minusBtn)
        mid.addWidget(self.screen, 1)
        mid.addWidget(self.plusBtn)
        main.addLayout(mid)

        # زر «المبلغ بالكامل» – يخفى/يظهر حسب الحاجة
        self.exactBtn = QPushButton("المبلغ بالكامل")
        self.exactBtn.setMinimumHeight(45)
        self.exactBtn.setFont(QFont("Arial", 13))
        self.exactBtn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color};
                color: white;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:pressed {{
                background-color: #1a7a3a;
            }}
        """)
        self.exactBtn.setVisible(False)  # مخفي افتراضياً
        main.addWidget(self.exactBtn)

    # ---------- منطق القيمة ----------
    def _step_value(self, delta):
        new = self._val + delta
        if 0 <= new <= self._max:
            self._val = new
            self._syncLine()
            self.valueChanged.emit(self._val)

    def setValue(self, v):
        self._val = max(0, min(v, self._max))
        self._syncLine()
        self.valueChanged.emit(self._val)

    def value(self):
        return self._val

    def _syncLine(self):
        self.screen.setText(f"{self._val:.2f}{self.suffix}")

    # ---------- تلوين ديناميكي (اختياري) ----------
    def setOkColor(self, ok: bool):
        col = "#28a745" if ok else "#ffc107"
        self.screen.setStyleSheet(f"""
            QLineEdit {{
                background: #1a1a1a;
                color: #00ff00;
                border: 3px solid {col};
                border-radius: 8px;
                padding: 4px;
            }}
        """)

    def showExactButton(self, show: bool, text: str = "المبلغ بالكامل"):
        """إظهار/إخفاء زر المبلغ بالكامل"""
        self.exactBtn.setText(text)
        self.exactBtn.setVisible(show)

    def connectExactButton(self, callback):
        """ربط زر المبلغ بالكامل بوظيفة خارجية"""
        self.exactBtn.clicked.connect(callback)
