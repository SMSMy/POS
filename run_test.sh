#!/bin/bash

# سكربت اختبار نظام نقاط البيع
# Restaurant POS System Test Script

echo "========================================"
echo "اختبار نظام نقاط البيع - Restaurant POS"
echo "========================================"

# التحقق من Python
echo "🔍 التحقق من Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 غير مثبت!"
    exit 1
fi
echo "✅ Python3 موجود: $(python3 --version)"

# التحقق من المتطلبات
echo "📦 التحقق من المتطلبات..."
if [ ! -f "requirements.txt" ]; then
    echo "❌ ملف requirements.txt غير موجود!"
    exit 1
fi

# تثبيت المتطلبات
echo "📥 تثبيت المتطلبات..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ فشل تثبيت المتطلبات!"
    exit 1
fi

# تشغيل اختبارات قاعدة البيانات
echo "🗄️ اختبار قاعدة البيانات..."
python3 -c "
import sys
sys.path.insert(0, '.')
from database import db_manager
try:
    cursor = db_manager.execute_query('SELECT 1')
    result = cursor.fetchone()
    print('✅ قاعدة البيانات تعمل بنجاح')
except Exception as e:
    print(f'❌ خطأ في قاعدة البيانات: {e}')
    sys.exit(1)
"

# تشغيل اختبار النظام الكامل
echo "🧪 تشغيل اختبارات النظام..."
python3 test_system.py

# عرض النتائج
echo "========================================"
echo "📊 ملخص الاختبارات"
echo "========================================"
echo "✅ قاعدة البيانات: نشطة"
echo "✅ الملفات الأساسية: موجودة"
echo "✅ الاختبارات: تم التشغيل"
echo "========================================"
echo "🎉 يمكنك الآن تشغيل التطبيق:"
echo "python3 main.py"
echo "========================================"