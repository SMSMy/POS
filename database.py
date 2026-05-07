"""
قاعدة البيانات - نظام نقاط البيع للمطاعم
Database Manager for Restaurant POS System
"""

import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from loguru import logger


def get_default_db_path() -> str:
    """الحصول على المسار الافتراضي لقاعدة البيانات في مجلد المستخدم"""
    if sys.platform == 'win32':
        app_data = Path(os.environ.get('APPDATA', Path.home())) / 'RestaurantPOS'
    else:
        app_data = Path.home() / '.restaurant_pos'
    app_data.mkdir(parents=True, exist_ok=True)
    return str(app_data / "pos_system.db")


class DatabaseManager:
    """مدير قاعدة البيانات"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path if db_path else get_default_db_path()
        self.conn = None
        self._initialize_database()

    def _initialize_database(self):
        """تهيئة قاعدة البيانات"""
        if not os.path.exists(self.db_path):
            logger.info("إنشاء قاعدة البيانات لأول مرة...")
            self._create_database()
        else:
            self._check_and_update_schema()

    def _create_database(self):
        """إنشاء قاعدة البيانات من المخطط"""
        try:
            schema_path = Path(__file__).parent / "database_schema.sql"
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = f.read()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.executescript(schema)
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ تم إنشاء قاعدة البيانات بنجاح")

        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء قاعدة البيانات: {e}")
            raise

    def _check_and_update_schema(self):
        """التحقق من المخطط وتحديثه إذا لزم الأمر"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # التحقق من وجود جدول المكونات
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='ingredients'
            """)

            if not cursor.fetchone():
                logger.info("⚠️ جدول المكونات غير موجود، إضافته...")
                cursor.execute("""
                    CREATE TABLE ingredients (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        unit TEXT NOT NULL,
                        quantity REAL NOT NULL DEFAULT 0,
                        min_alert_level REAL NOT NULL DEFAULT 0,
                        cost_per_unit REAL NOT NULL,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # إضافة جدول الوصفات
                cursor.execute("""
                    CREATE TABLE recipes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id INTEGER NOT NULL,
                        ingredient_id INTEGER NOT NULL,
                        quantity_needed REAL NOT NULL,
                        FOREIGN KEY (product_id) REFERENCES products(id),
                        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id),
                        UNIQUE(product_id, ingredient_id)
                    )
                """)

                # إضافة جدول قائمة انتظار التليجرام
                cursor.execute("""
                    CREATE TABLE telegram_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message TEXT NOT NULL,
                        report_type TEXT NOT NULL,
                        attempt_count INTEGER NOT NULL DEFAULT 0,
                        max_attempts INTEGER NOT NULL DEFAULT 10,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        sent_at TEXT,
                        error_message TEXT
                    )
                """)

                # إضافة الفهارس
                cursor.execute("CREATE INDEX idx_recipes_product ON recipes(product_id)")
                cursor.execute("CREATE INDEX idx_recipes_ingredient ON recipes(ingredient_id)")
                cursor.execute("CREATE INDEX idx_telegram_queue_sent ON telegram_queue(sent_at)")

                # إضافة المكونات الافتراضية
                default_ingredients = [
                    ('خبز برجر', 'piece', 200, 50, 0.50),
                    ('لحم مفروم', 'kg', 10, 2, 25.00),
                    ('طماطم', 'kg', 5, 1, 8.00),
                    ('خس', 'kg', 3, 0.5, 6.00),
                    ('بطاطس', 'kg', 20, 5, 4.00)
                ]

                for name, unit, qty, min_level, cost in default_ingredients:
                    cursor.execute("""
                        INSERT INTO ingredients (name, unit, quantity, min_alert_level, cost_per_unit)
                        VALUES (?, ?, ?, ?, ?)
                    """, (name, unit, qty, min_level, cost))

                conn.commit()
                logger.info("✅ تم تحديث المخطط بنجاح")

            # التحقق من وجود جدول قائمة انتظار التليجرام
            try:
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='telegram_queue'
                """)
                if not cursor.fetchone():
                    logger.info("⚠️ جدول telegram_queue غير موجود، إضافته...")
                    cursor.execute("""
                        CREATE TABLE telegram_queue (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            message TEXT NOT NULL,
                            report_type TEXT NOT NULL,
                            attempt_count INTEGER NOT NULL DEFAULT 0,
                            max_attempts INTEGER NOT NULL DEFAULT 10,
                            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            sent_at TEXT,
                            error_message TEXT
                        )
                    """)
                    cursor.execute("CREATE INDEX idx_telegram_queue_sent ON telegram_queue(sent_at)")
                    conn.commit()
                    logger.info("✅ تم تحديث جدول telegram_queue بنجاح")
            except Exception as e:
                logger.warning(f"⚠️ خطأ في التحقق من telegram_queue: {e}")

            # التحقق من وجود جدول سجل تغيير الأسعار
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='product_price_history'")
                if not cursor.fetchone():
                    logger.info("⚠️ جدول product_price_history غير موجود، إضافته...")
                    cursor.execute("""
                        CREATE TABLE product_price_history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            product_id INTEGER NOT NULL,
                            old_price REAL NOT NULL,
                            new_price REAL NOT NULL,
                            changed_by INTEGER NOT NULL,
                            reason TEXT,
                            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (product_id) REFERENCES products(id),
                            FOREIGN KEY (changed_by) REFERENCES users(id)
                        )
                    """)
                    conn.commit()
            except Exception as e:
                logger.warning(f"⚠️ خطأ في التحقق من product_price_history: {e}")

            # التحقق من وجود جدول سجل التدقيق
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")
                if not cursor.fetchone():
                    logger.info("⚠️ جدول audit_log غير موجود، إضافته...")
                    cursor.execute("""
                        CREATE TABLE audit_log (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            action TEXT NOT NULL,
                            table_name TEXT,
                            record_id INTEGER,
                            old_value TEXT,
                            new_value TEXT,
                            ip_address TEXT,
                            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(id)
                        )
                    """)
                    cursor.execute("CREATE INDEX idx_audit_log_user ON audit_log(user_id)")
                    cursor.execute("CREATE INDEX idx_audit_log_created ON audit_log(created_at)")
                    conn.commit()
            except Exception as e:
                logger.warning(f"⚠️ خطأ في التحقق من audit_log: {e}")

            # ========== Column Migrations ==========

            # 1. invoice_items -> tax_rate
            try:
                cursor.execute("SELECT tax_rate FROM invoice_items LIMIT 1")
            except:
                logger.info("⚠️ عمود tax_rate غير موجود في invoice_items، إضافته...")
                try:
                    cursor.execute("ALTER TABLE invoice_items ADD COLUMN tax_rate REAL NOT NULL DEFAULT 0.15")
                    conn.commit()
                except Exception as e: logger.error(f"فشل إضافة tax_rate: {e}")

            # 2. cash_movements -> recipient_name
            try:
                cursor.execute("SELECT recipient_name FROM cash_movements LIMIT 1")
            except:
                logger.info("⚠️ عمود recipient_name غير موجود في cash_movements، إضافته...")
                try:
                    cursor.execute("ALTER TABLE cash_movements ADD COLUMN recipient_name TEXT")
                    conn.commit()
                except Exception as e: logger.error(f"فشل إضافة recipient_name: {e}")

            # 3. products -> image_path
            try:
                cursor.execute("SELECT image_path FROM products LIMIT 1")
            except:
                logger.info("⚠️ عمود image_path غير موجود في products، إضافته...")
                try:
                    cursor.execute("ALTER TABLE products ADD COLUMN image_path TEXT")
                    conn.commit()
                except Exception as e: logger.error(f"فشل إضافة image_path: {e}")

            # 4. invoices -> invoice_hash (for ZATCA)
            try:
                cursor.execute("SELECT invoice_hash FROM invoices LIMIT 1")
            except:
                logger.info("⚠️ عمود invoice_hash غير موجود في invoices، إضافته...")
                try:
                    cursor.execute("ALTER TABLE invoices ADD COLUMN invoice_hash TEXT")
                    conn.commit()
                except Exception as e: logger.error(f"فشل إضافة invoice_hash: {e}")

            # 5. products -> display_order (for product ordering)
            try:
                cursor.execute("SELECT display_order FROM products LIMIT 1")
            except:
                logger.info("⚠️ عمود display_order غير موجود في products، إضافته...")
                try:
                    cursor.execute("ALTER TABLE products ADD COLUMN display_order INTEGER NOT NULL DEFAULT 0")
                    conn.commit()
                    logger.info("✅ تم إضافة عمود display_order للمنتجات")
                except Exception as e: logger.error(f"فشل إضافة display_order: {e}")

            # 6. products -> name_en (English product name for bilingual support)
            try:
                cursor.execute("SELECT name_en FROM products LIMIT 1")
            except:
                logger.info("⚠️ عمود name_en غير موجود في products، إضافته...")
                try:
                    cursor.execute("ALTER TABLE products ADD COLUMN name_en TEXT")
                    conn.commit()
                    logger.info("✅ تم إضافة عمود name_en للمنتجات")
                except Exception as e: logger.error(f"فشل إضافة name_en للمنتجات: {e}")

            # 7. categories -> name_en (English category name for bilingual support)
            try:
                cursor.execute("SELECT name_en FROM categories LIMIT 1")
            except:
                logger.info("⚠️ عمود name_en غير موجود في categories، إضافته...")
                try:
                    cursor.execute("ALTER TABLE categories ADD COLUMN name_en TEXT")
                    conn.commit()
                    logger.info("✅ تم إضافة عمود name_en للتصنيفات")
                except Exception as e: logger.error(f"فشل إضافة name_en للتصنيفات: {e}")


            # ========== Migration: Update payments table CHECK constraint ==========
            # Check if payments table exists and update to allow new payment methods
            try:
                cursor.execute("""
                    SELECT sql FROM sqlite_master
                    WHERE type='table' AND name='payments'
                """)
                result = cursor.fetchone()
                if result and 'delivery_app' not in result[0]:
                    logger.info("⚠️ تحديث جدول الدفعات لإضافة طرق دفع جديدة...")

                    # Create new payments table with updated constraint
                    cursor.execute("""
                        CREATE TABLE payments_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            invoice_id INTEGER NOT NULL,
                            payment_method TEXT NOT NULL CHECK (payment_method IN ('cash', 'card', 'transfer', 'delivery_app', 'multi')),
                            amount REAL NOT NULL,
                            reference_number TEXT,
                            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
                        )
                    """)

                    # Copy data from old table
                    cursor.execute("""
                        INSERT INTO payments_new (id, invoice_id, payment_method, amount, reference_number, created_at)
                        SELECT id, invoice_id, payment_method, amount, reference_number, created_at
                        FROM payments
                    """)

                    # Drop old table and rename new
                    cursor.execute("DROP TABLE payments")
                    cursor.execute("ALTER TABLE payments_new RENAME TO payments")
                    cursor.execute("CREATE INDEX idx_payments_invoice ON payments(invoice_id)")

                    conn.commit()
                    logger.info("✅ تم تحديث جدول الدفعات بنجاح")
            except Exception as e:
                logger.warning(f"⚠️ لم يتم تحديث جدول الدفعات: {e}")

            conn.close()

        except Exception as e:
            logger.error(f"❌ خطأ في تحديث المخطط: {e}")

    def get_connection(self) -> sqlite3.Connection:
        """الحصول على اتصال بقاعدة البيانات"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def execute_query(self, query: str, params: tuple = None) -> sqlite3.Cursor:
        """تنفيذ استعلام"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor

    def execute_many(self, query: str, params: List[tuple]):
        """تنفيذ استعلام متعدد"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.executemany(query, params)
        conn.commit()
        return cursor

    def commit(self):
        """حفظ التغييرات"""
        if self.conn:
            self.conn.commit()

    def rollback(self):
        """التراجع عن التغييرات"""
        if self.conn:
            self.conn.rollback()

    def close(self):
        """إغلاق الاتصال"""
        if self.conn:
            self.conn.close()
            self.conn = None


# ==========================================
# دوال مساعدة عامة
# ==========================================

def get_setting(key: str, default: str = None) -> str:
    """الحصول على قيمة إعداد"""
    try:
        db = DatabaseManager()
        cursor = db.execute_query(
            "SELECT value FROM settings WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        return row['value'] if row else default
    except Exception as e:
        logger.error(f"خطأ في الحصول على الإعداد {key}: {e}")
        return default


def set_setting(key: str, value: str):
    """تعيين قيمة إعداد"""
    try:
        db = DatabaseManager()
        db.execute_query(
            """INSERT OR REPLACE INTO settings (key, value, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)""",
            (key, value)
        )
        db.commit()
    except Exception as e:
        logger.error(f"خطأ في تعيين الإعداد {key}: {e}")


def validate_shift_open() -> bool:
    """التحقق من وجود وردية مفتوحة"""
    try:
        db = DatabaseManager()
        cursor = db.execute_query(
            "SELECT id FROM shifts WHERE status = 'open' LIMIT 1"
        )
        return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"خطأ في التحقق من الوردية: {e}")
        return False


def get_current_shift() -> Optional[Dict[str, Any]]:
    """الحصول على الوردية الحالية"""
    try:
        db = DatabaseManager()
        cursor = db.execute_query(
            """SELECT s.*, u.username, u.display_name
               FROM shifts s
               JOIN users u ON s.cashier_id = u.id
               WHERE s.status = 'open' LIMIT 1"""
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"خطأ في الحصول على الوردية الحالية: {e}")
        return None


# ==========================================
# مثيل عام من قاعدة البيانات
# ==========================================

db_manager = DatabaseManager()
