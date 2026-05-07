"""
اختبار شامل للنظام بعد الإصلاحات
Complete System Test
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from loguru import logger

from database import db_manager, get_setting, get_current_shift


def test_imports():
    """اختبار الاستيرادات"""
    tests = [
        ("main", lambda: __import__('main')),
        ("database", lambda: __import__('database')),
        ("login_dialog", lambda: __import__('src.ui.login_dialog', fromlist=['LoginDialog'])),
        ("main_window", lambda: __import__('src.ui.main_window', fromlist=['MainWindow'])),
        ("pos_screen", lambda: __import__('src.ui.pos_screen', fromlist=['POSScreen'])),
        ("payment_dialog", lambda: __import__('src.ui.payment_dialog', fromlist=['PaymentDialog'])),
        ("inventory_dialog", lambda: __import__('src.ui.inventory_dialog', fromlist=['InventoryDialog'])),
        ("ProductDialog", lambda: __import__('src.ui.ProductDialog', fromlist=['ProductDialog'])),
        ("CategoryDialog", lambda: __import__('src.ui.CategoryDialog', fromlist=['CategoryDialog'])),
        ("IngredientDialog", lambda: __import__('src.ui.IngredientDialog', fromlist=['IngredientDialog'])),
        ("shifts_dialog", lambda: __import__('src.ui.shifts_dialog', fromlist=['ShiftsDialog'])),
        ("reports_dialog", lambda: __import__('src.ui.reports_dialog', fromlist=['ReportsDialog'])),
        ("returns_dialog", lambda: __import__('src.ui.returns_dialog', fromlist=['ReturnsDialog'])),
        ("settings_dialog", lambda: __import__('src.ui.settings_dialog', fromlist=['SettingsDialog'])),
        ("printer", lambda: __import__('src.utils.printer', fromlist=['ThermalPrinter'])),
        ("zatca", lambda: __import__('src.utils.zatca', fromlist=['generate_qr_code'])),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            logger.success(f"✅ {test_name}: imported successfully")
            passed += 1
        except Exception as e:
            logger.error(f"❌ {test_name}: import failed - {e}")
            failed += 1
    
    return passed, failed


def test_database():
    """اختبار قاعدة البيانات"""
    try:
        # اختبار الاتصال
        cursor = db_manager.execute_query("SELECT 1")
        result = cursor.fetchone()
        
        if result[0] == 1:
            logger.success("✅ Database connection: OK")
        else:
            logger.error("❌ Database connection: FAILED")
            return False
        
        # اختبار الجداول
        tables = [
            'users', 'categories', 'products', 'ingredients', 'recipes',
            'shifts', 'invoices', 'invoice_items', 'payments', 
            'cash_movements', 'settings', 'telegram_queue'
        ]
        
        for table in tables:
            try:
                cursor = db_manager.execute_query(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.success(f"✅ Table {table}: {count} rows")
            except Exception as e:
                logger.error(f"❌ Table {table}: ERROR - {e}")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test: FAILED - {e}")
        return False


def test_default_data():
    """اختبار البيانات الافتراضية"""
    tests = [
        ("Admin user", "SELECT * FROM users WHERE username = 'admin'"),
        ("Categories", "SELECT COUNT(*) FROM categories WHERE is_active = 1"),
        ("Products", "SELECT COUNT(*) FROM products WHERE is_active = 1"),
        ("Ingredients", "SELECT COUNT(*) FROM ingredients WHERE is_active = 1"),
        ("Settings", "SELECT COUNT(*) FROM settings"),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, query in tests:
        try:
            cursor = db_manager.execute_query(query)
            result = cursor.fetchone()
            
            if test_name == "Admin user":
                if result:
                    logger.success(f"✅ {test_name}: exists")
                    passed += 1
                else:
                    logger.error(f"❌ {test_name}: not found")
                    failed += 1
            else:
                count = result[0]
                if count > 0:
                    logger.success(f"✅ {test_name}: {count} items")
                    passed += 1
                else:
                    logger.error(f"❌ {test_name}: no items found")
                    failed += 1
                    
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
            failed += 1
    
    return passed, failed


def test_zatca():
    """اختبار ZATCA"""
    try:
        from src.utils.zatca import generate_qr_code
        
        test_data = {
            'seller_name': 'Restaurant',
            'vat_number': '123456789',
            'timestamp': '2024-01-01T12:00:00',
            'total': 100.00,
            'vat': 15.00
        }
        
        qr_code = generate_qr_code(test_data)
        
        if qr_code:
            logger.success(f"✅ ZATCA QR Code: generated ({len(qr_code)} chars)")
            return True
        else:
            logger.error("❌ ZATCA QR Code: failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ ZATCA test: ERROR - {e}")
        return False


def main():
    """الاختبار الرئيسي"""
    logger.info("=" * 60)
    logger.info("اختبار شامل لنظام نقاط البيع")
    logger.info("=" * 60)
    
    total_passed = 0
    total_failed = 0
    
    # اختبار الاستيرادات
    logger.info("\n📦 اختبار الاستيرادات...")
    passed, failed = test_imports()
    total_passed += passed
    total_failed += failed
    
    # اختبار قاعدة البيانات
    logger.info("\n🗄️ اختبار قاعدة البيانات...")
    if test_database():
        total_passed += 1
    else:
        total_failed += 1
    
    # اختبار البيانات الافتراضية
    logger.info("\n📊 اختبار البيانات الافتراضية...")
    passed, failed = test_default_data()
    total_passed += passed
    total_failed += failed
    
    # اختبار ZATCA
    logger.info("\n📱 اختبار ZATCA...")
    if test_zatca():
        total_passed += 1
    else:
        total_failed += 1
    
    # الملخص
    logger.info("\n" + "=" * 60)
    logger.info(f"📊 ملخص الاختبارات:")
    logger.info(f"✅ ناجح: {total_passed}")
    logger.info(f"❌ فاشل: {total_failed}")
    logger.info(f"📈 النسبة: {total_passed/(total_passed+total_failed)*100:.1f}%")
    logger.info("=" * 60)
    
    # إغلاق قاعدة البيانات
    db_manager.close()
    
    return total_failed == 0


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)