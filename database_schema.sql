-- نظام نقاط البيع للمطاعم - قاعدة البيانات
-- Restaurant POS System - Database Schema
-- الإصدار: 2.0 Enhanced

-- =====================================
-- 1. جدول المستخدمين
-- =====================================
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'cashier')),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TEXT
);

-- =====================================
-- 2. جدول التصنيفات
-- =====================================
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT,
    icon TEXT,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =====================================
-- 3. جدول المنتجات
-- =====================================
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT UNIQUE,
    name TEXT NOT NULL,
    category_id INTEGER,
    cost_price REAL NOT NULL,
    selling_price REAL NOT NULL,
    quantity REAL NOT NULL DEFAULT 0,
    min_alert_level REAL NOT NULL DEFAULT 0,
    unit TEXT NOT NULL DEFAULT 'piece',
    tax_rate REAL NOT NULL DEFAULT 0.15,
    color TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- =====================================
-- 4. جدول المكونات (جديد في النسخة 2.0)
-- =====================================
CREATE TABLE ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    unit TEXT NOT NULL,
    quantity REAL NOT NULL DEFAULT 0,
    min_alert_level REAL NOT NULL DEFAULT 0,
    cost_per_unit REAL NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =====================================
-- 5. جدول الوصفات (جديد في النسخة 2.0)
-- =====================================
CREATE TABLE recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    quantity_needed REAL NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id),
    UNIQUE(product_id, ingredient_id)
);

-- =====================================
-- 6. جدول الورديات
-- =====================================
CREATE TABLE shifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_number INTEGER NOT NULL,
    cashier_id INTEGER NOT NULL,
    starting_amount REAL NOT NULL,
    expected_amount REAL NOT NULL DEFAULT 0,
    actual_amount REAL,
    difference REAL,
    total_sales REAL NOT NULL DEFAULT 0,
    total_returns REAL NOT NULL DEFAULT 0,
    total_deposits REAL NOT NULL DEFAULT 0,
    total_withdrawals REAL NOT NULL DEFAULT 0,
    start_time TEXT NOT NULL,
    end_time TEXT,
    status TEXT NOT NULL CHECK (status IN ('open', 'closed')) DEFAULT 'open',
    notes TEXT,
    FOREIGN KEY (cashier_id) REFERENCES users(id)
);

-- =====================================
-- 7. جدول الفواتير
-- =====================================
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK (type IN ('sale', 'return', 'hold')) DEFAULT 'sale',
    subtotal REAL NOT NULL,
    tax_amount REAL NOT NULL,
    discount_amount REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL,
    paid_amount REAL NOT NULL DEFAULT 0,
    change_amount REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('pending', 'completed', 'cancelled')) DEFAULT 'pending',
    cashier_id INTEGER NOT NULL,
    shift_id INTEGER NOT NULL,
    original_invoice_id INTEGER,
    table_number INTEGER,
    customer_name TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    invoice_hash TEXT,
    FOREIGN KEY (cashier_id) REFERENCES users(id),
    FOREIGN KEY (shift_id) REFERENCES shifts(id),
    FOREIGN KEY (original_invoice_id) REFERENCES invoices(id)
);

-- =====================================
-- 8. جدول عناصر الفاتورة
-- =====================================
CREATE TABLE invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit_price REAL NOT NULL,
    cost_price REAL NOT NULL,
    tax_rate REAL NOT NULL,
    discount_amount REAL NOT NULL DEFAULT 0,
    line_total REAL NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- =====================================
-- 9. جدول الدفعات
-- =====================================
CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    payment_method TEXT NOT NULL CHECK (payment_method IN ('cash', 'card', 'transfer', 'delivery_app', 'multi')),
    amount REAL NOT NULL,
    reference_number TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

-- =====================================
-- 10. جدول حركات الخزينة
-- =====================================
CREATE TABLE cash_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK (type IN ('deposit', 'withdrawal', 'expense')),
    amount REAL NOT NULL,
    reason TEXT NOT NULL,
    category TEXT NOT NULL,
    shift_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shift_id) REFERENCES shifts(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- =====================================
-- 11. جدول سجل التدقيق
-- =====================================
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
);

-- =====================================
-- 12. جدول الإعدادات
-- =====================================
CREATE TABLE settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT,
    description TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =====================================
-- 13. جدول قائمة انتظار التليجرام (جديد في النسخة 2.0)
-- =====================================
CREATE TABLE telegram_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT NOT NULL,
    report_type TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 10,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TEXT,
    error_message TEXT
);

-- =====================================
-- 14. جدول أسعار المنتجات السابقة
-- =====================================
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
);

-- =====================================
-- الفهارس (Indexes)
-- =====================================
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_barcode ON products(barcode);
CREATE INDEX idx_products_active ON products(is_active);

CREATE INDEX idx_recipes_product ON recipes(product_id);
CREATE INDEX idx_recipes_ingredient ON recipes(ingredient_id);

CREATE INDEX idx_invoices_number ON invoices(invoice_number);
CREATE INDEX idx_invoices_shift ON invoices(shift_id);
CREATE INDEX idx_invoices_cashier ON invoices(cashier_id);
CREATE INDEX idx_invoices_created ON invoices(created_at);

CREATE INDEX idx_invoice_items_invoice ON invoice_items(invoice_id);
CREATE INDEX idx_invoice_items_product ON invoice_items(product_id);

CREATE INDEX idx_payments_invoice ON payments(invoice_id);

CREATE INDEX idx_cash_movements_shift ON cash_movements(shift_id);
CREATE INDEX idx_cash_movements_user ON cash_movements(user_id);

CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_created ON audit_log(created_at);

CREATE INDEX idx_telegram_queue_sent ON telegram_queue(sent_at);
CREATE INDEX idx_telegram_queue_attempts ON telegram_queue(attempt_count);

-- =====================================
-- القيم الافتراضية
-- =====================================

-- المستخدم الإداري الافتراضي
INSERT INTO users (username, password, display_name, role) VALUES
('admin', 'admin123', 'مدير النظام', 'admin');

-- الإعدادات الافتراضية
INSERT INTO settings (key, value, description) VALUES
('company_name', 'مطعمي', 'اسم المطعم'),
('vat_number', '123456789', 'الرقم الضريبي'),
('currency', 'SAR', 'العملة'),
('language', 'ar', 'اللغة الافتراضية'),
('tax_rate', '0.15', 'نسبة الضريبة الافتراضية'),
('telegram_bot_token', '', 'توكن بوت التليجرام'),
('telegram_chat_id', '', 'معرف محادثة التليجرام'),
('telegram_topic_id', '', 'معرف موضوع التليجرام'),
('receipt_header', '', 'نص رأس الفاتورة'),
('receipt_footer', 'شكراً لزيارتكم', 'نص تذييل الفاتورة'),
('kitchen_printer_enabled', '0', 'تفعيل طباعة تذكرة المطبخ'),
('auto_backup', '1', 'النسخ الاحتياطي التلقائي'),
('max_backups', '30', 'الحد الأقصى للنسخ الاحتياطية');

-- التصنيفات الافتراضية
INSERT INTO categories (name, color, display_order) VALUES
('مشروبات', '#3498db', 1),
('مأكولات رئيسية', '#e74c3c', 2),
('حلويات', '#f39c12', 3),
('مقبلات', '#2ecc71', 4);

-- المنتجات الافتراضية
INSERT INTO products (name, barcode, category_id, cost_price, selling_price, quantity, min_alert_level, unit, tax_rate) VALUES
('كولا 330مل', '123456789', 1, 1.50, 2.00, 100, 20, 'piece', 0.15),
('مياه معدنية', '987654321', 1, 0.75, 1.00, 150, 30, 'piece', 0.15),
('برجر', '111222333', 2, 8.00, 12.00, 50, 10, 'piece', 0.15),
('شاورما', '444555666', 2, 6.00, 9.00, 60, 15, 'piece', 0.15);

-- المكونات الافتراضية
INSERT INTO ingredients (name, unit, quantity, min_alert_level, cost_per_unit) VALUES
('خبز برجر', 'piece', 200, 50, 0.50),
('لحم مفروم', 'kg', 10, 2, 25.00),
('طماطم', 'kg', 5, 1, 8.00),
('خس', 'kg', 3, 0.5, 6.00),
('بطاطس', 'kg', 20, 5, 4.00);

-- الوصفات الافتراضية
INSERT INTO recipes (product_id, ingredient_id, quantity_needed) VALUES
(3, 1, 2),    -- برجر يحتاج 2 خبز
(3, 2, 0.15), -- برجر يحتاج 150جرام لحم
(3, 3, 0.05), -- برجر يحتاج 50جرام طماطم
(3, 4, 0.02); -- برجر يحتاج 20جرام خس
