"""اختبار سريع للطابعة - Arabic Printing Test"""
from src.utils.printer import get_printer_manager

def test_arabic_printing():
    """اختبار طباعة النص العربي"""
    printer = get_printer_manager()

    test_text = """
مطعم الطيب
ATAYEB RESTAURANT
================================
شاورما دجاج x2 ........ 20.00
  (Shawarma Chicken)
بيبسي x1 ............... 5.00
  (Pepsi)
================================
المجموع: 25.00 ر.س
Total: 25.00 SAR
================================
شكراً لزيارتكم!
Thank you!
    """

    print("=" * 50)
    print("🖨️ اختبار الطباعة العربية")
    print("=" * 50)
    print(f"الطابعة: {printer.printer_name}")
    print("-" * 50)

    success, error = printer.print_text(test_text)

    if success:
        print("✅ تمت الطباعة بنجاح!")
    else:
        print(f"❌ فشلت الطباعة: {error}")

    return success


def test_force_image():
    """اختبار تحويل كل النصوص لصور"""
    printer = get_printer_manager()

    test_text = """
Test Force Image Mode
هذا اختبار لوضع الصور الإجباري
123.45 ر.س
    """

    print("\n" + "=" * 50)
    print("🖼️ اختبار وضع الصور الإجباري")
    print("=" * 50)

    success, error = printer.print_text(test_text, force_image=True)

    if success:
        print("✅ تمت الطباعة بنجاح!")
    else:
        print(f"❌ فشلت الطباعة: {error}")

    return success


if __name__ == "__main__":
    print("\n🔧 بدء اختبارات الطباعة...\n")

    # اختبار 1: الطباعة العادية
    test_arabic_printing()

    # اختبار 2: وضع الصور الإجباري (اختياري)
    # test_force_image()

    print("\n✨ انتهت الاختبارات!")
