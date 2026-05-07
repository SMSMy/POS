"""
اختبار النظام - FIRST_RUN_TEST.md
System Test - First Run
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from PyQt5.QtTest import QTest
from loguru import logger

from database import db_manager, get_setting, get_current_shift
from src.ui.login_dialog import LoginDialog
from src.ui.main_window import MainWindow
from src.ui.pos_screen import POSScreen


class SystemTest:
    """اختبار النظام"""
    
    def __init__(self):
        self.app = None
        self.test_results = []
        self.passed = 0
        self.failed = 0
    
    def _log_result(self, test_name: str, passed: bool, message: str = ""):
        """تسجيل نتيجة الاختبار"""
        if passed:
            self.passed += 1
            logger.success(f"✅ {test_name}: نجح")
            self.test_results.append(f"✅ {test_name}: نجح")
        else:
            self.failed += 1
            logger.error(f"❌ {test_name}: فشل - {message}")
            self.test_results.append(f"❌ {test_name}: فشل - {message}")
    
    def test_database_connection(self):
        """اختبار اتصال قاعدة البيانات"""
        try:
            cursor = db_manager.execute_query("SELECT 1")
            result = cursor.fetchone()
            self._log_result("اتصال قاعدة البيانات", result[0] == 1)
            return result[0] == 1
        except Exception as e:
            self._log_result("اتصال قاعدة البيانات", False, str(e))
            return False
    
    def test_default_user(self):
        """اختبار وجود المستخدم الافتراضي"""
        try:
            cursor = db_manager.execute_query(
                "SELECT * FROM users WHERE username = 'admin'"
            )
            user = cursor.fetchone()
            self._log_result("المستخدم الافتراضي admin", user is not None)
            return user is not None
        except Exception as e:
            self._log_result("المستخدم الافتراضي admin", False, str(e))
            return False
    
    def test_default_categories(self):
        """اختبار وجود الفئات الافتراضية"""
        try:
            cursor = db_manager.execute_query(
                "SELECT COUNT(*) as count FROM categories WHERE is_active = 1"
            )
            count = cursor.fetchone()['count']
            self._log_result("الفئات الافتراضية", count >= 4)
            return count >= 4
        except Exception as e:
            self._log_result("الفئات الافتراضية", False, str(e))
            return False
    
    def test_default_products(self):
        """اختبار وجود المنتجات الافتراضية"""
        try:
            cursor = db_manager.execute_query(
                "SELECT COUNT(*) as count FROM products WHERE is_active = 1"
            )
            count = cursor.fetchone()['count']
            self._log_result("المنتجات الافتراضية", count >= 4)
            return count >= 4
        except Exception as e:
            self._log_result("المنتجات الافتراضية", False, str(e))
            return False
    
    def test_default_ingredients(self):
        """اختبار وجود المكونات الافتراضية"""
        try:
            cursor = db_manager.execute_query(
                "SELECT COUNT(*) as count FROM ingredients WHERE is_active = 1"
            )
            count = cursor.fetchone()['count']
            self._log_result("المكونات الافتراضية", count >= 5)
            return count >= 5
        except Exception as e:
            self._log_result("المكونات الافتراضية", False, str(e))
            return False
    
    def test_default_settings(self):
        """اختبار الإعدادات الافتراضية"""
        try:
            company_name = get_setting('company_name')
            self._log_result("إعدادات الشركة", company_name == 'مطعمي')
            return company_name == 'مطعمي'
        except Exception as e:
            self._log_result("إعدادات الشركة", False, str(e))
            return False
    
    def test_login_dialog(self):
        """اختبار شاشة تسجيل الدخول"""
        try:
            from src.ui.login_dialog import LoginDialog
            dialog = LoginDialog()
            
            # التحقق من وجود الحقول
            has_username = hasattr(dialog, 'username_input')
            has_password = hasattr(dialog, 'password_input')
            has_button = hasattr(dialog, 'login_button')
            
            self._log_result("شاشة تسجيل الدخول", has_username and has_password and has_button)
            return has_username and has_password and has_button
        except Exception as e:
            self._log_result("شاشة تسجيل الدخول", False, str(e))
            return False
    
    def test_main_window(self):
        """اختبار النافذة الرئيسية"""
        try:
            from src.ui.main_window import MainWindow
            
            # بيانات مستخدم وهمية
            user_data = {
                'id': 1,
                'username': 'admin',
                'display_name': 'مدير النظام',
                'role': 'admin'
            }
            
            window = MainWindow(user_data)
            
            # التحقق من وجود العناصر الأساسية
            has_toolbar = window.toolBar() is not None
            has_statusbar = window.statusBar() is not None
            
            self._log_result("النافذة الرئيسية", has_toolbar and has_statusbar)
            return has_toolbar and has_statusbar
        except Exception as e:
            self._log_result("النافذة الرئيسية", False, str(e))
            return False
    
    def test_pos_screen(self):
        """اختبار شاشة نقطة البيع"""
        try:
            from src.ui.pos_screen import POSScreen
            
            user_data = {
                'id': 1,
                'username': 'admin',
                'display_name': 'مدير النظام',
                'role': 'admin'
            }
            
            screen = POSScreen(user_data)
            
            # التحقق من وجود العناصر
            has_categories = hasattr(screen, 'categories_container')
            has_products = hasattr(screen, 'products_container')
            has_cart = hasattr(screen, 'cart_table')
            
            self._log_result("شاشة نقطة البيع", has_categories and has_products and has_cart)
            return has_categories and has_products and has_cart
        except Exception as e:
            self._log_result("شاشة نقطة البيع", False, str(e))
            return False
    
    def test_inventory_dialog(self):
        """اختبار نافذة المخزون"""
        try:
            from src.ui.inventory_dialog import InventoryDialog
            dialog = InventoryDialog()
            
            # التحقق من التبويبات
            has_tabs = hasattr(dialog, 'products_table')
            
            self._log_result("نافذة المخزون", has_tabs)
            return has_tabs
        except Exception as e:
            self._log_result("نافذة المخزون", False, str(e))
            return False
    
    def test_printer_utility(self):
        """اختبار أداة الطباعة"""
        try:
            from src.utils.printer import ThermalPrinter
            printer = ThermalPrinter()
            
            # التحقق من التهيئة
            has_printer_name = hasattr(printer, 'printer_name')
            
            self._log_result("أداة الطباعة", has_printer_name)
            return has_printer_name
        except Exception as e:
            self._log_result("أداة الطباعة", False, str(e))
            return False
    
    def test_zatca_utility(self):
        """اختبار أداة ZATCA"""
        try:
            from src.utils.zatca import generate_qr_code
            
            test_data = {
                'seller_name': 'مطعمي',
                'vat_number': '123456789',
                'timestamp': '2024-01-01T12:00:00',
                'total': 100.00,
                'vat': 15.00
            }
            
            qr_code = generate_qr_code(test_data)
            
            self._log_result("أداة ZATCA", len(qr_code) > 0)
            return len(qr_code) > 0
        except Exception as e:
            self._log_result("أداة ZATCA", False, str(e))
            return False
    
    def run_all_tests(self):
        """تشغيل جميع الاختبارات"""
        logger.info("=" * 60)
        logger.info("بدء اختبارات نظام نقاط البيع")
        logger.info("=" * 60)
        
        # إنشاء تطبيق Qt (مطلوب للواجهات الرسومية)
        self.app = QApplication([])
        
        # قائمة الاختبارات
        tests = [
            ("اتصال قاعدة البيانات", self.test_database_connection),
            ("المستخدم الافتراضي admin", self.test_default_user),
            ("الفئات الافتراضية", self.test_default_categories),
            ("المنتجات الافتراضية", self.test_default_products),
            ("المكونات الافتراضية", self.test_default_ingredients),
            ("إعدادات الشركة", self.test_default_settings),
            ("شاشة تسجيل الدخول", self.test_login_dialog),
            ("النافذة الرئيسية", self.test_main_window),
            ("شاشة نقطة البيع", self.test_pos_screen),
            ("نافذة المخزون", self.test_inventory_dialog),
            ("أداة الطباعة", self.test_printer_utility),
            ("أداة ZATCA", self.test_zatca_utility),
        ]
        
        # تشغيل الاختبارات
        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                self._log_result(test_name, False, f"استثناء: {e}")
        
        # ملخص النتائج
        logger.info("=" * 60)
        logger.info(f"📊 ملخص الاختبارات:")
        logger.info(f"✅ ناجح: {self.passed}")
        logger.info(f"❌ فاشل: {self.failed}")
        logger.info(f"📈 النسبة: {self.passed/(self.passed+self.failed)*100:.1f}%")
        logger.info("=" * 60)
        
        # عرض النتائج التفصيلية
        print("\n" + "=" * 60)
        print("تفاصيل الاختبارات:")
        print("=" * 60)
        for result in self.test_results:
            print(result)
        print("=" * 60)
        
        # إغلاق قاعدة البيانات
        db_manager.close()
        
        return self.failed == 0


def main():
    """الدالة الرئيسية"""
    test = SystemTest()
    success = test.run_all_tests()
    
    if success:
        logger.info("🎉 جميع الاختبارات نجحت!")
    else:
        logger.warning("⚠️ بعض الاختبارات فشلت")
    
    return success


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)