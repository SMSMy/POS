"""
Widget مخصص لأزرار المنتجات - يرسم الصورة الخلفية والسعر فقط
اسم المنتج يظهر أسفل الزر في ProductCard
"""

from PyQt5.QtWidgets import QPushButton, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, pyqtSignal, QRect
from PyQt5.QtGui import QPainter, QPixmap, QColor, QFont, QPen, QBrush
import os

# استيراد نظام التخزين المؤقت للصور
try:
    from src.utils.image_cache import image_cache, get_optimized_path
    USE_IMAGE_CACHE = True
except ImportError:
    USE_IMAGE_CACHE = False

# استيراد مدير اللغة
try:
    from src.utils.language_manager import language_manager
    USE_LANGUAGE_MANAGER = True
except ImportError:
    USE_LANGUAGE_MANAGER = False


def get_display_name(product: dict) -> str:
    """الحصول على اسم المنتج حسب اللغة الحالية"""
    if USE_LANGUAGE_MANAGER:
        lang = language_manager.current_language
        if lang == 'en':
            # استخدام الاسم الإنجليزي إن وجد، وإلا العربي
            return product.get('name_en') or product.get('name', '')
    return product.get('name', '')


class ProductButton(QPushButton):
    """
    زر منتج مخصص يعرض:
    - صورة خلفية (أوضح الآن بدون نص فوقها)
    - السعر فقط في الأسفل
    - اسم المنتج يظهر أسفل الزر في ProductCard
    - متجاوب مع دقة الشاشة
    """

    clicked_with_data = pyqtSignal(dict)

    def __init__(self, product: dict, parent=None, responsive: dict = None):
        super().__init__(parent)

        self.product = product
        self.product_name = product['name']
        self.price = product['selling_price']

        # إعدادات الحجم المتجاوبة
        if responsive:
            min_size = responsive.get('product_card_min', (100, 80))
            max_size = responsive.get('product_card_max', (130, 100))
        else:
            min_size = (100, 80)
            max_size = (130, 100)

        # الحصول على لون المنتج
        try:
            self.color = product['color'] if product['color'] else '#3498db'
        except (KeyError, IndexError):
            self.color = '#3498db'

        # تحميل الصورة - باستخدام الكاش للأداء الأفضل
        self.background_image = None
        try:
            image_path = product.get('image_path')
            if image_path:
                if USE_IMAGE_CACHE:
                    # استخدام الكاش + البحث عن صورة محسّنة
                    optimized_path = get_optimized_path(image_path)
                    pixmap = image_cache.get_pixmap(optimized_path)
                    if pixmap and not pixmap.isNull():
                        self.background_image = pixmap
                else:
                    # تحميل مباشر (fallback)
                    if os.path.exists(image_path):
                        pixmap = QPixmap(image_path)
                        if not pixmap.isNull():
                            self.background_image = pixmap
        except Exception:
            pass

        # الحالة
        self.is_hovered = False
        self.is_pressed_state = False

        # الإعدادات المتجاوبة - حجم البطاقة حسب دقة الشاشة
        self.setMinimumSize(min_size[0], min_size[1])
        self.setMaximumSize(max_size[0], max_size[1])
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

        # ربط الحدث
        self.clicked.connect(lambda: self.clicked_with_data.emit(self.product))

    def paintEvent(self, event):
        """رسم الزر يدوياً - صورة + سعر فقط"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        rect = self.rect()

        # ―― 1) رسم الخلفية ――
        if self.background_image:
            # رسم الصورة بشفافية أعلى (أوضح) لأن الاسم لم يعد فوقها
            overlay_color = QColor(0, 0, 0, 30)  # شبه شفاف
            if self.is_pressed_state:
                overlay_color = QColor(0, 0, 0, 80)
            elif self.is_hovered:
                overlay_color = QColor(0, 0, 0, 50)

            # تكبير الصورة لتملأ الزر
            scaled_image = self.background_image.scaled(
                rect.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            painter.drawPixmap(rect, scaled_image)
            painter.fillRect(rect, overlay_color)
        else:
            # بدون صورة - خلفية ملونة
            bg_color = QColor(self.color)
            if self.is_pressed_state:
                bg_color = bg_color.darker(120)
            elif self.is_hovered:
                bg_color = bg_color.lighter(110)
            painter.fillRect(rect, bg_color)

        # ―― 2) رسم الحدود الملونة ――
        border_color = QColor(self.color)
        border_width = 3 if self.is_hovered else 2
        if self.is_pressed_state:
            border_color = QColor("#e74c3c")
        elif self.is_hovered:
            border_color = QColor("#f39c12")

        pen = QPen(border_color, border_width)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 8, 8)

        # ―― 3) رسم السعر في الأسفل مع خلفية شبه شفافة ――
        price_height = 22
        price_rect = QRect(0, rect.height() - price_height, rect.width(), price_height)

        # خلفية السعر
        painter.fillRect(price_rect, QColor(0, 0, 0, 180))

        # نص السعر
        painter.setPen(QColor(255, 255, 255))
        font_price = QFont("Arial", 10, QFont.Bold)
        painter.setFont(font_price)
        painter.drawText(price_rect, Qt.AlignCenter, f"{self.price:.2f} ريال")

    def enterEvent(self, event):
        """عند تمرير الماوس"""
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """عند خروج الماوس"""
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """عند الضغط"""
        if event.button() == Qt.LeftButton:
            self.is_pressed_state = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """عند رفع الضغط"""
        if event.button() == Qt.LeftButton:
            self.is_pressed_state = False
            self.update()
        super().mouseReleaseEvent(event)


class ProductCard(QWidget):
    """
    بطاقة منتج تحتوي على:
    - زر الصورة في الأعلى
    - اسم المنتج
    - أزرار +/- للتحكم بالكمية
    - متجاوب مع دقة الشاشة
    """

    clicked_with_data = pyqtSignal(dict)
    quantity_changed = pyqtSignal(dict, int)  # product, quantity change (+1 or -1)

    def __init__(self, product: dict, parent=None, responsive: dict = None):
        super().__init__(parent)

        self.product = product
        self.responsive = responsive or {}

        # حساب أحجام الأزرار المتجاوبة
        font_size = self.responsive.get('font_small', 9)
        btn_size = (30, 26) if self.responsive.get('font_small', 9) <= 9 else (35, 30)

        layout = QVBoxLayout()
        layout.setSpacing(1)
        layout.setContentsMargins(0, 0, 0, 0)

        # زر المنتج (الصورة + السعر) - مع الإعدادات المتجاوبة
        self.button = ProductButton(product, self, responsive)
        self.button.clicked_with_data.connect(self.clicked_with_data.emit)
        layout.addWidget(self.button)

        # اسم المنتج - حسب اللغة الحالية مع حجم خط متجاوب
        display_name = get_display_name(product)
        self.name_label = QLabel(display_name)  # حفظ مرجع للتحديث لاحقاً
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setMaximumHeight(35)
        self.name_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                background-color: rgba(0, 0, 0, 0.7);
                padding: 2px;
                border-radius: 2px;
                font-size: {font_size + 2}px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(self.name_label)

        # أزرار التحكم بالكمية - متجاوبة
        from PyQt5.QtWidgets import QHBoxLayout
        qty_layout = QHBoxLayout()
        qty_layout.setSpacing(2)
        qty_layout.setContentsMargins(1, 1, 1, 1)

        # زر الطرح - متجاوب
        self.minus_btn = QPushButton("-")
        self.minus_btn.setFixedSize(btn_size[0], btn_size[1])
        self.minus_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: {font_size + 5}px;
                font-weight: bold;
            }}
            QPushButton:pressed {{
                background-color: #c0392b;
            }}
        """)
        self.minus_btn.clicked.connect(lambda: self.quantity_changed.emit(self.product, -1))
        qty_layout.addWidget(self.minus_btn)

        # عرض الكمية في السلة (تُحدث من الخارج) - متجاوب
        self.qty_label = QLabel("0")
        self.qty_label.setAlignment(Qt.AlignCenter)
        self.qty_label.setMinimumWidth(25)
        self.qty_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                background-color: #2c3e50;
                padding: 2px;
                border-radius: 4px;
                font-size: {font_size + 2}px;
                font-weight: bold;
            }}
        """)
        qty_layout.addWidget(self.qty_label)

        # زر الإضافة - متجاوب
        self.plus_btn = QPushButton("+")
        self.plus_btn.setFixedSize(btn_size[0], btn_size[1])
        self.plus_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: {font_size + 5}px;
                font-weight: bold;
            }}
            QPushButton:pressed {{
                background-color: #1e8449;
            }}
        """)
        self.plus_btn.clicked.connect(lambda: self.quantity_changed.emit(self.product, 1))
        qty_layout.addWidget(self.plus_btn)

        layout.addLayout(qty_layout)

        self.setLayout(layout)
        # الحد الأقصى للعرض متجاوب
        max_width = self.responsive.get('product_card_max', (130, 100))[0] + 15
        self.setMaximumWidth(max_width)

    def set_quantity(self, qty: int):
        """تحديث عرض الكمية"""
        self.qty_label.setText(str(qty))

    def update_display_name(self):
        """تحديث اسم المنتج حسب اللغة الحالية - للتبديل السريع"""
        new_name = get_display_name(self.product)
        self.name_label.setText(new_name)
