"""
نظام تخزين مؤقت للصور في الذاكرة
Image Memory Cache for POS System

الوظيفة:
- تخزين الصور في الذاكرة لتجنب إعادة التحميل
- تصغير الصور للحجم المطلوب
- أيقونة افتراضية عند فشل التحميل
"""

import os
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QSize
from loguru import logger


class ImageCache:
    """
    تخزين مؤقت ذكي للصور في الذاكرة

    الاستخدام:
        from src.utils.image_cache import image_cache

        icon = image_cache.get_icon("C:/imege_optimized/فلافل.webp")
        button.setIcon(icon)
    """

    def __init__(self, icon_size=(80, 80)):
        """
        تهيئة الكاش

        Args:
            icon_size: حجم الأيقونات (width, height)
        """
        self.icon_size = QSize(*icon_size)
        self._memory_cache = {}  # {image_path: QIcon}
        self._default_icon = None
        self._placeholder_icon = None

        logger.info(f"تم تهيئة ImageCache بحجم {icon_size}")

    def get_icon(self, image_path, product_id=None):
        """
        الحصول على أيقونة (من الذاكرة أو القرص)

        Args:
            image_path: مسار الصورة الكامل
            product_id: معرف المنتج (اختياري - للتسجيل)

        Returns:
            QIcon: الأيقونة جاهزة للاستخدام
        """
        # التحقق من المسار
        if not image_path:
            return self._get_default_icon()

        # تحويل المسار لنص
        image_path = str(image_path)

        # التحقق من الذاكرة المؤقتة
        if image_path in self._memory_cache:
            return self._memory_cache[image_path]

        # التحقق من وجود الملف
        if not os.path.exists(image_path):
            logger.debug(f"الصورة غير موجودة: {image_path}")
            return self._get_default_icon()

        # تحميل من القرص
        try:
            pixmap = QPixmap(image_path)

            if pixmap.isNull():
                logger.warning(f"فشل تحميل الصورة: {image_path}")
                return self._get_default_icon()

            # تصغير الصورة للحجم المطلوب
            scaled = pixmap.scaled(
                self.icon_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            # إنشاء أيقونة وتخزينها
            icon = QIcon(scaled)
            self._memory_cache[image_path] = icon

            logger.debug(f"تم تحميل: {os.path.basename(image_path)}")
            return icon

        except Exception as e:
            logger.error(f"خطأ في تحميل الصورة {image_path}: {e}")
            return self._get_default_icon()

    def get_pixmap(self, image_path, size=None):
        """
        الحصول على QPixmap بدلاً من QIcon

        Args:
            image_path: مسار الصورة
            size: الحجم المطلوب (اختياري)

        Returns:
            QPixmap: الصورة
        """
        if not image_path or not os.path.exists(str(image_path)):
            return self._get_default_pixmap(size)

        try:
            pixmap = QPixmap(str(image_path))

            if pixmap.isNull():
                return self._get_default_pixmap(size)

            target_size = size if size else self.icon_size

            return pixmap.scaled(
                target_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

        except Exception as e:
            logger.error(f"خطأ في تحميل الصورة: {e}")
            return self._get_default_pixmap(size)

    def _get_default_icon(self):
        """أيقونة افتراضية عند فشل التحميل"""
        if self._default_icon is None:
            self._default_icon = QIcon(self._get_default_pixmap())
        return self._default_icon

    def _get_default_pixmap(self, size=None):
        """صورة افتراضية رمادية مع علامة استفهام"""
        target_size = size if size else self.icon_size

        pixmap = QPixmap(target_size)
        pixmap.fill(QColor(200, 200, 200))  # رمادي فاتح

        # رسم علامة استفهام
        painter = QPainter(pixmap)
        painter.setPen(QColor(150, 150, 150))

        font = painter.font()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)

        painter.drawText(
            pixmap.rect(),
            Qt.AlignCenter,
            "?"
        )

        painter.end()

        return pixmap

    def preload_images(self, image_paths):
        """
        تحميل مسبق لمجموعة صور

        Args:
            image_paths: قائمة بمسارات الصور
        """
        loaded = 0
        for path in image_paths:
            if path and str(path) not in self._memory_cache:
                icon = self.get_icon(path)
                if icon != self._default_icon:
                    loaded += 1

        if loaded > 0:
            logger.info(f"تم التحميل المسبق لـ {loaded} صورة")

        return loaded

    def preload_from_directory(self, directory, extensions=('.webp', '.png', '.jpg', '.jpeg')):
        """
        تحميل مسبق لجميع الصور في مجلد

        Args:
            directory: مسار المجلد
            extensions: الامتدادات المدعومة
        """
        if not os.path.exists(directory):
            logger.warning(f"المجلد غير موجود: {directory}")
            return 0

        image_paths = []
        for file in os.listdir(directory):
            if any(file.lower().endswith(ext) for ext in extensions):
                image_paths.append(os.path.join(directory, file))

        return self.preload_images(image_paths)

    def clear_cache(self):
        """مسح الذاكرة المؤقتة"""
        count = len(self._memory_cache)
        self._memory_cache.clear()
        logger.info(f"تم مسح {count} صورة من الذاكرة المؤقتة")
        return count

    def remove_from_cache(self, image_path):
        """إزالة صورة معينة من الكاش"""
        if str(image_path) in self._memory_cache:
            del self._memory_cache[str(image_path)]
            return True
        return False

    def get_cache_size(self):
        """الحصول على عدد الصور المخزنة"""
        return len(self._memory_cache)

    def get_cache_info(self):
        """معلومات الذاكرة المؤقتة"""
        return {
            'cached_images': len(self._memory_cache),
            'icon_size': (self.icon_size.width(), self.icon_size.height()),
            'cached_paths': list(self._memory_cache.keys())
        }

    def set_icon_size(self, width, height):
        """
        تغيير حجم الأيقونات (يمسح الكاش)

        Args:
            width: العرض
            height: الارتفاع
        """
        self.icon_size = QSize(width, height)
        self.clear_cache()
        self._default_icon = None
        logger.info(f"تم تغيير حجم الأيقونات إلى {width}×{height}")


# ===============================================
# مثيل عام للاستخدام في كل التطبيق
# ===============================================

# الحجم الافتراضي للأيقونات في شاشة البيع
image_cache = ImageCache(icon_size=(80, 80))


# ===============================================
# دوال مساعدة إضافية
# ===============================================

def get_optimized_path(original_path, optimized_dir=r"C:\imege_optimized"):
    """
    الحصول على مسار الصورة المحسّنة

    Args:
        original_path: المسار الأصلي
        optimized_dir: مجلد الصور المحسّنة

    Returns:
        str: مسار الصورة المحسّنة (أو الأصلية إذا لم توجد)
    """
    if not original_path:
        return None

    # استخراج اسم الملف بدون امتداد
    from pathlib import Path
    original_name = Path(original_path).stem

    # البحث عن الصورة المحسّنة
    optimized_path = os.path.join(optimized_dir, f"{original_name}.webp")

    if os.path.exists(optimized_path):
        return optimized_path

    # إرجاع المسار الأصلي إذا لم توجد صورة محسّنة
    return original_path


def preload_product_images(products_list, optimized_dir=r"C:\imege_optimized"):
    """
    تحميل مسبق لصور المنتجات

    Args:
        products_list: قائمة المنتجات (كل منتج dict)
        optimized_dir: مجلد الصور المحسّنة
    """
    paths = []
    for product in products_list:
        original_path = product.get('image_path') or product.get('image')
        if original_path:
            optimized_path = get_optimized_path(original_path, optimized_dir)
            paths.append(optimized_path)

    return image_cache.preload_images(paths)
