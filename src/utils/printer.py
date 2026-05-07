"""
═══════════════════════════════════════════════════════════════════════════════
Restaurant POS System - Thermal Printer Manager
═══════════════════════════════════════════════════════════════════════════════
Handles thermal receipt printing with ESC/POS commands
Supports 80mm and 58mm thermal printers on Windows
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
from typing import Optional, Dict, List
from datetime import datetime
from loguru import logger
import re

# Windows printing support
try:
    import win32print
    import win32ui
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logger.warning("pywin32 not installed - Printing disabled")


class ESCPOSCommands:
    """ESC/POS command constants for thermal printers."""

    # Printer initialization
    INIT = b'\x1b\x40'  # ESC @

    # Text formatting
    BOLD_ON = b'\x1b\x45\x01'  # ESC E 1
    BOLD_OFF = b'\x1b\x45\x00'  # ESC E 0
    DOUBLE_HEIGHT_ON = b'\x1b\x21\x10'  # ESC ! 16
    DOUBLE_WIDTH_ON = b'\x1b\x21\x20'  # ESC ! 32
    DOUBLE_SIZE_ON = b'\x1b\x21\x30'  # ESC ! 48
    NORMAL_SIZE = b'\x1b\x21\x00'  # ESC ! 0

    # Text alignment
    ALIGN_LEFT = b'\x1b\x61\x00'  # ESC a 0
    ALIGN_CENTER = b'\x1b\x61\x01'  # ESC a 1
    ALIGN_RIGHT = b'\x1b\x61\x02'  # ESC a 2

    # Line spacing
    LINE_SPACING_DEFAULT = b'\x1b\x32'  # ESC 2
    LINE_SPACING_TIGHT = b'\x1b\x33\x10'  # ESC 3 n

    # Paper operations
    CUT_PAPER = b'\x1d\x56\x00'  # GS V 0 (full cut)
    CUT_PAPER_PARTIAL = b'\x1d\x56\x01'  # GS V 1 (partial cut)
    FEED_LINES = b'\x1b\x64'  # ESC d n (feed n lines)

    # Cash drawer
    OPEN_DRAWER = b'\x1b\x70\x00\x19\xfa'  # ESC p 0 25 250


def image_to_escpos(image_path: str, max_width: int = 384) -> bytes:
    """
    تحويل صورة إلى بيانات ESC/POS للطباعة الحرارية.

    Args:
        image_path: مسار الصورة
        max_width: أقصى عرض بالبكسل (384 لورق 80 مم)

    Returns:
        بيانات ESC/POS الجاهزة للطباعة
    """
    try:
        from PIL import Image
        import os

        if not os.path.exists(image_path):
            logger.warning(f"Logo file not found: {image_path}")
            return b''

        # فتح الصورة
        img = Image.open(image_path)

        # تحويل إلى RGBA إذا لزم الأمر
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # إنشاء خلفية بيضاء
        background = Image.new('RGBA', img.size, (255, 255, 255, 255))
        background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)

        # تحويل إلى رمادي ثم أسود وأبيض
        img = background.convert('L')  # Grayscale

        # تغيير الحجم مع الحفاظ على النسبة
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)

        # تحويل إلى أسود وأبيض (1-bit)
        img = img.point(lambda x: 0 if x < 128 else 255, '1')

        # التأكد من أن العرض مضاعف لـ 8
        width = img.width
        if width % 8 != 0:
            new_width = (width // 8 + 1) * 8
            new_img = Image.new('1', (new_width, img.height), 1)
            new_img.paste(img, (0, 0))
            img = new_img

        width = img.width
        height = img.height

        # GS v 0 - Print raster bit image
        # Format: GS v 0 m xL xH yL yH d1...dk
        # m = 0 (normal), 1 (double width), 2 (double height), 3 (quadruple)

        xL = (width // 8) % 256
        xH = (width // 8) // 256
        yL = height % 256
        yH = height // 256

        # بناء أمر ESC/POS
        data = b'\x1d\x76\x30\x00'  # GS v 0 m (m=0)
        data += bytes([xL, xH, yL, yH])

        # تحويل الصورة إلى بيانات بايت
        pixels = list(img.getdata())
        byte_width = width // 8

        for y in range(height):
            for x in range(byte_width):
                byte = 0
                for bit in range(8):
                    px_idx = y * width + x * 8 + bit
                    if px_idx < len(pixels) and pixels[px_idx] == 0:  # Black pixel
                        byte |= (1 << (7 - bit))
                data += bytes([byte])

        return data

    except ImportError:
        logger.warning("Pillow not installed - Logo printing disabled")
        return b''
    except Exception as e:
        logger.error(f"Error converting image: {e}")
        return b''


def arabic_text_to_image(text: str, max_width: int = 384, font_size: int = 24) -> bytes:
    """
    تحويل نص عربي إلى صورة للطباعة الحرارية.
    يعالج الحروف العربية المتصلة واتجاه النص من اليمين لليسار.

    Args:
        text: النص العربي
        max_width: أقصى عرض بالبكسل (384 لورق 80 مم)
        font_size: حجم الخط

    Returns:
        بيانات ESC/POS الجاهزة للطباعة
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import os

        # محاولة استخدام arabic_reshaper و bidi لمعالجة النص العربي
        try:
            import arabic_reshaper
            reshaped_text = arabic_reshaper.reshape(text)

            try:
                from bidi.algorithm import get_display
                bidi_text = get_display(reshaped_text)
            except ImportError:
                # Custom simple BiDi: Reverse chars but keep numbers (including decimals) LTR
                rev_text = reshaped_text[::-1]
                # Match numbers including decimals like "6.00" or "123.45"
                bidi_text = re.sub(r'[\d.]+', lambda m: m.group(0)[::-1], rev_text)

        except ImportError:
            # إذا لم تكن المكتبات متوفرة، استخدم النص كما هو
            logger.warning("arabic_reshaper not installed - Arabic may not display correctly")
            bidi_text = text

        # البحث عن خط عربي
        arabic_fonts = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/tahoma.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/calibri.ttf",
        ]

        font = None
        for font_path in arabic_fonts:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except:
                    continue

        if font is None:
            font = ImageFont.load_default()
            logger.warning("No Arabic font found, using default font")

        # إنشاء صورة مؤقتة لقياس النص
        temp_img = Image.new('1', (1, 1), 1)
        temp_draw = ImageDraw.Draw(temp_img)

        # قياس أبعاد النص
        bbox = temp_draw.textbbox((0, 0), bidi_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # إضافة هوامش
        padding = 10
        img_width = min(text_width + padding * 2, max_width)
        img_height = text_height + padding * 2

        # التأكد من أن العرض مضاعف لـ 8
        if img_width % 8 != 0:
            img_width = (img_width // 8 + 1) * 8

        # إنشاء الصورة النهائية
        img = Image.new('1', (img_width, img_height), 1)  # 1 = أبيض
        draw = ImageDraw.Draw(img)

        # رسم النص في المنتصف
        x = (img_width - text_width) // 2
        y = padding
        draw.text((x, y), bidi_text, font=font, fill=0)  # 0 = أسود

        # تحويل إلى بيانات ESC/POS
        width = img.width
        height = img.height

        xL = (width // 8) % 256
        xH = (width // 8) // 256
        yL = height % 256
        yH = height // 256

        data = b'\x1d\x76\x30\x00'  # GS v 0 m (m=0)
        data += bytes([xL, xH, yL, yH])

        pixels = list(img.getdata())
        byte_width = width // 8

        for y in range(height):
            for x in range(byte_width):
                byte = 0
                for bit in range(8):
                    px_idx = y * width + x * 8 + bit
                    if px_idx < len(pixels) and pixels[px_idx] == 0:  # Black pixel
                        byte |= (1 << (7 - bit))
                data += bytes([byte])

        return data

    except ImportError:
        logger.warning("Pillow not installed - Arabic image printing disabled")
        return b''
    except Exception as e:
        logger.error(f"Error creating Arabic text image: {e}")
        return b''


def qr_to_escpos(data: str, max_width: int = 384) -> bytes:
    """
    Generate QR code image for ESC/POS.
    """
    try:
        import qrcode
        from PIL import Image

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Resize if too big
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height))

        # Convert similar to image_to_escpos logic
        # But qrcode image is already 1-bit or close to it.
        # Ensure it's 1-bit monochrome
        img = img.convert('1')

        # Padding to multiple of 8
        width = img.width
        if width % 8 != 0:
             new_width = (width // 8 + 1) * 8
             new_img = Image.new('1', (new_width, img.height), 1)
             new_img.paste(img, (0,0))
             img = new_img

        width = img.width
        height = img.height

        xL = (width // 8) % 256
        xH = (width // 8) // 256
        yL = height % 256
        yH = height // 256

        esc_data = b'\x1d\x76\x30\x00'
        esc_data += bytes([xL, xH, yL, yH])

        pixels = list(img.getdata())
        byte_width = width // 8

        for y in range(height):
            for x in range(byte_width):
                byte = 0
                for bit in range(8):
                    px_idx = y * width + x * 8 + bit
                    if px_idx < len(pixels) and pixels[px_idx] == 0:
                        byte |= (1 << (7 - bit))
                esc_data += bytes([byte])

        return esc_data

    except Exception as e:
        logger.error(f"Error generating QR: {e}")
        return b''

def has_arabic(text: str) -> bool:
    """التحقق من وجود أحرف عربية في النص."""
    for char in text:
        if '\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F':
            return True
    return False


class PrinterManager:
    """
    Manages thermal receipt printing.
    Implements Soft Fail - printing errors don't stop sales.
    """

    # Character widths for different paper sizes
    PAPER_WIDTHS = {
        80: 42,  # 80mm paper = 42 characters
        58: 32,  # 58mm paper = 32 characters
    }

    def __init__(self, printer_name: str = None, paper_width: int = 80):
        """
        Initialize printer manager.

        Args:
            printer_name: Name of thermal printer (None = default printer)
            paper_width: Paper width in mm (80 or 58)
        """
        self.printer_name = printer_name
        self.paper_width = paper_width
        self.char_width = self.PAPER_WIDTHS.get(paper_width, 42)

        if not printer_name and HAS_WIN32:
            try:
                self.printer_name = win32print.GetDefaultPrinter()
            except:
                pass

        logger.info(f"PrinterManager initialized: {self.printer_name or 'No printer'}")

    @property
    def is_available(self) -> bool:
        """Check if printer is available."""
        if not HAS_WIN32:
            return False
        return self.printer_name is not None

    def get_available_printers(self) -> List[str]:
        """Get list of available printers."""
        if not HAS_WIN32:
            return []

        try:
            printers = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
            return [p[2] for p in printers]
        except Exception as e:
            logger.error(f"Error listing printers: {e}")
            return []

    def set_printer(self, printer_name: str):
        """Set the active printer."""
        self.printer_name = printer_name
        logger.info(f"Printer set to: {printer_name}")

    def print_raw(self, data: bytes) -> tuple[bool, str]:
        """
        Send raw bytes to printer.

        Returns:
            (success, error_message)
        """
        if not HAS_WIN32:
            return False, "Printing not available (pywin32 not installed)"

        if not self.printer_name:
            return False, "No printer configured"

        try:
            hPrinter = win32print.OpenPrinter(self.printer_name)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("POS Receipt", None, "RAW"))
                try:
                    win32print.StartPagePrinter(hPrinter)
                    win32print.WritePrinter(hPrinter, data)
                    win32print.EndPagePrinter(hPrinter)
                finally:
                    win32print.EndDocPrinter(hPrinter)
            finally:
                win32print.ClosePrinter(hPrinter)

            return True, ""

        except Exception as e:
            logger.error(f"Print error: {e}")

            # إرسال إشعار تليجرام
            try:
                from database import get_setting
                if get_setting('telegram_print_failed', '1') == '1':
                    from src.utils.telegram import get_telegram_manager
                    telegram = get_telegram_manager()
                    telegram.send_with_queue(
                        f"⚠️ <b>فشل الطباعة</b>\n\n"
                        f"الطابعة: {self.printer_name}\n"
                        f"الخطأ: {str(e)}",
                        'print_failed'
                    )
            except:
                pass

            return False, str(e)

    def print_logo(self, logo_path: str = None) -> tuple[bool, str]:
        """
        طباعة الشعار.

        Args:
            logo_path: مسار الشعار (None = استخدام الشعار المحفوظ في الإعدادات)

        Returns:
            (success, error_message)
        """
        try:
            from database import get_setting

            if not logo_path:
                logo_path = get_setting('restaurant_logo', '')

            if not logo_path:
                return True, "No logo configured"

            # تحويل الصورة إلى ESC/POS
            logo_data = image_to_escpos(logo_path)

            if not logo_data:
                return True, "Logo conversion failed"

            # إضافة أمر التوسيط
            data = ESCPOSCommands.ALIGN_CENTER
            data += logo_data
            data += ESCPOSCommands.ALIGN_LEFT
            data += b'\n'

            return self.print_raw(data)

        except Exception as e:
            logger.error(f"Logo print error: {e}")
            return False, str(e)

    def print_text(self, text: str, encoding: str = 'cp720', include_logo: bool = True) -> tuple[bool, str]:
        """
        Print text with automatic encoding.
        يكتشف النص العربي تلقائياً ويستخدم الطباعة بالصور للعربية.

        Args:
            text: Text to print
            encoding: Character encoding (cp720 for Arabic)
            include_logo: طباعة الشعار في الأعلى

        Returns:
            (success, error_message)
        """
        try:
            from database import get_setting

            # Build print data
            data = ESCPOSCommands.INIT

            # طباعة الشعار إذا كان مفعلاً
            if include_logo and get_setting('print_logo', '1') == '1':
                logo_path = get_setting('restaurant_logo', '')
                if logo_path:
                    logo_data = image_to_escpos(logo_path)
                    if logo_data:
                        data += ESCPOSCommands.ALIGN_CENTER
                        data += logo_data
                        data += ESCPOSCommands.ALIGN_LEFT
                        data += b'\n'

            # معالجة النص سطراً بسطر
            lines = text.split('\n')
            for line in lines:
                # Check for special QR marker
                if "QR_DATA:" in line:
                    qr_content = line.split("QR_DATA:")[1].strip()
                    if qr_content:
                        qr_data = qr_to_escpos(qr_content)
                        if qr_data:
                            data += ESCPOSCommands.ALIGN_CENTER
                            data += qr_data
                            data += ESCPOSCommands.ALIGN_LEFT
                            data += b'\n'
                    continue

                if has_arabic(line):
                    # استخدام الطباعة بالصور للنص العربي
                    arabic_img = arabic_text_to_image(line, max_width=384, font_size=22)
                    if arabic_img:
                        data += ESCPOSCommands.ALIGN_CENTER
                        data += arabic_img
                        data += ESCPOSCommands.ALIGN_LEFT
                    else:
                        # fallback to text encoding if image fails
                        data += line.encode(encoding, errors='replace')
                        data += b'\n'
                else:
                    # النص الإنجليزي والأرقام بالطريقة العادية
                    data += line.encode(encoding, errors='replace')
                    data += b'\n'

            data += b'\n\n'
            data += ESCPOSCommands.CUT_PAPER_PARTIAL

            return self.print_raw(data)

        except Exception as e:
            logger.error(f"Print text error: {e}")
            return False, str(e)

    def format_receipt(self, invoice: Dict, settings: Dict) -> str:
        """
        Format invoice as receipt text.

        Args:
            invoice: Invoice data with items and payments
            settings: Store settings (name, address, vat, etc.)

        Returns:
            Formatted receipt text
        """
        w = self.char_width
        line = '─' * w
        double_line = '═' * w

        lines = []

        # Header
        lines.append(self._center(settings.get('store_name', 'Restaurant'), w))
        if settings.get('store_address'):
            lines.append(self._center(settings['store_address'], w))
        if settings.get('store_phone'):
            lines.append(self._center(settings['store_phone'], w))
        if settings.get('vat_number'):
            lines.append(self._center(f"VAT: {settings['vat_number']}", w))

        lines.append(double_line)

        # Invoice info
        lines.append(f"Invoice: {invoice.get('invoice_number', '')}")
        lines.append(f"Date: {invoice.get('created_at', '')}")

        if invoice.get('table_number'):
            lines.append(f"Table: {invoice['table_number']}")
        if invoice.get('customer_name'):
            lines.append(f"Customer: {invoice['customer_name']}")

        lines.append(line)

        # Items
        for item in invoice.get('items', []):
            name = item['product_name'][:20]  # Truncate long names
            qty = item['quantity']
            price = item['unit_price']
            total = item['line_total']

            lines.append(name)
            lines.append(f"  {qty:.0f} x {price:.2f} = {total:.2f}")

        lines.append(line)

        # Totals
        subtotal = invoice.get('subtotal', 0)
        tax = invoice.get('tax_amount', 0)
        discount = invoice.get('discount_amount', 0)
        total = invoice.get('total', 0)

        lines.append(self._format_row("Subtotal:", f"{subtotal:.2f}", w))

        if discount > 0:
            lines.append(self._format_row("Discount:", f"-{discount:.2f}", w))

        tax_rate = int(float(settings.get('default_tax_rate', 0.15)) * 100)
        lines.append(self._format_row(f"VAT ({tax_rate}%):", f"{tax:.2f}", w))

        lines.append(line)
        lines.append(self._format_row("TOTAL:", f"{total:.2f}", w))
        lines.append(line)

        # Payment info
        paid = invoice.get('paid_amount', 0)
        change = invoice.get('change_amount', 0)

        lines.append(self._format_row("Paid:", f"{paid:.2f}", w))
        if change > 0:
            lines.append(self._format_row("Change:", f"{change:.2f}", w))

        # Payment method
        for payment in invoice.get('payments', []):
            method = payment['payment_method'].upper()
            amount = payment['amount']
            lines.append(f"  {method}: {amount:.2f}")

        lines.append(double_line)

        # Footer
        lines.append(self._center("شكراً لزيارتكم", w))
        lines.append(self._center("Thank you!", w))

        # QR Code placeholder (actual QR would be image)
        if invoice.get('zatca_qr'):
            lines.append("")
            # Use special marker to pass raw QR data to print_text
            lines.append(f"QR_DATA:{invoice['zatca_qr']}")

        lines.append("")
        lines.append("")
        lines.append("")

        return '\n'.join(lines)

    def format_kitchen_ticket(self, order: Dict) -> str:
        """
        Format kitchen ticket for food preparation.

        Args:
            order: Order data with items

        Returns:
            Formatted kitchen ticket text
        """
        w = self.char_width
        line = '─' * w

        lines = []

        # Header
        lines.append(self._center("🍳 تذكرة المطبخ", w))
        lines.append(self._center("Kitchen Ticket", w))
        lines.append(line)

        lines.append(f"Order: #{order.get('invoice_number', '')}")
        if order.get('table_number'):
            lines.append(f"Table: {order['table_number']}")
        lines.append(f"Time: {order.get('time', datetime.now().strftime('%H:%M'))}")

        lines.append(line)
        lines.append("ITEMS:")
        lines.append(line)

        for item in order.get('items', []):
            # Checkbox for preparation tracking
            lines.append(f"[ ] {item['product_name']} x{item['quantity']:.0f}")

            # Ingredients if available
            for ingredient in item.get('ingredients', []):
                qty = ingredient['quantity_needed'] * item['quantity']
                lines.append(f"    - {qty:.2f} {ingredient['unit']} {ingredient['ingredient_name']}")

        lines.append(line)

        if order.get('notes'):
            lines.append(f"NOTES: {order['notes']}")
            lines.append(line)

        lines.append("")
        lines.append("")

        return '\n'.join(lines)

    def format_shift_report(self, shift: Dict) -> str:
        """Format shift closing report for printing."""
        w = self.char_width
        line = '─' * w
        double_line = '═' * w

        lines = []

        lines.append(self._center("تقرير إغلاق الوردية", w))
        lines.append(double_line)

        lines.append(f"رقم الوردية: #{shift.get('shift_number', '')}")
        lines.append(f"الكاشير: {shift.get('cashier_name', '')}")
        lines.append(f"من: {shift.get('opened_at', '')}")
        lines.append(f"إلى: {shift.get('closed_at', '')}")

        lines.append(line)

        lines.append(self._format_row("الرصيد الافتتاحي:", f"{shift.get('starting_amount', 0):.2f}", w))
        lines.append(self._format_row("إجمالي المبيعات:", f"{shift.get('total_sales', 0):.2f}", w))

        # Payment method breakdown
        payment_breakdown = shift.get('payment_breakdown', {})
        method_names = {'cash': 'نقداً', 'card': 'بطاقة', 'transfer': 'تحويل', 'delivery_app': 'توصيل', 'multi': 'متعدد'}
        for method, amount in payment_breakdown.items():
            label = f"  ↳ {method_names.get(method, method)}:"
            lines.append(self._format_row(label, f"{amount:.2f}", w))

        lines.append(self._format_row("المرتجعات:", f"-{shift.get('total_returns', 0):.2f}", w))
        lines.append(self._format_row("الإيداعات:", f"+{shift.get('total_deposits', 0):.2f}", w))
        lines.append(self._format_row("السحوبات:", f"-{shift.get('total_withdrawals', 0):.2f}", w))

        lines.append(line)

        lines.append(self._format_row("المتوقع:", f"{shift.get('expected_amount', 0):.2f}", w))
        lines.append(self._format_row("الفعلي:", f"{shift.get('actual_amount', 0):.2f}", w))

        diff = shift.get('difference', 0)
        diff_label = "عجز:" if diff < 0 else "زيادة:" if diff > 0 else "متطابق:"
        lines.append(self._format_row(diff_label, f"{abs(diff):.2f}", w))

        # صافي الخزينة = المتوقع - الرصيد الافتتاحي - مبيعات البطاقة
        card_sales = payment_breakdown.get('card', 0)
        net_treasury = shift.get('expected_amount', 0) - shift.get('starting_amount', 0) - card_sales
        lines.append(line)
        lines.append(self._format_row("صافي الخزينة (نقداً):", f"{net_treasury:.2f}", w))

        lines.append(double_line)

        lines.append(f"عدد الفواتير: {shift.get('total_invoices', 0)}")

        if shift.get('notes'):
            lines.append(f"ملاحظات: {shift['notes']}")

        lines.append("")
        lines.append("")
        lines.append("")

        return '\n'.join(lines)


    def print_receipt(self, invoice: Dict, settings: Dict) -> tuple[bool, str]:
        """Print formatted receipt."""
        text = self.format_receipt(invoice, settings)
        return self.print_text(text)

    def print_kitchen_ticket(self, order: Dict) -> tuple[bool, str]:
        """Print kitchen preparation ticket."""
        text = self.format_kitchen_ticket(order)
        return self.print_text(text)

    def print_shift_report(self, shift: Dict) -> tuple[bool, str]:
        """Print shift closing report."""
        text = self.format_shift_report(shift)
        return self.print_text(text)

    def open_cash_drawer(self) -> tuple[bool, str]:
        """Send command to open cash drawer."""
        return self.print_raw(ESCPOSCommands.OPEN_DRAWER)

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def _center(self, text: str, width: int) -> str:
        """Center text within width."""
        return text.center(width)

    def _format_row(self, label: str, value: str, width: int) -> str:
        """Format a label-value row."""
        spaces = width - len(label) - len(value)
        return f"{label}{' ' * max(1, spaces)}{value}"

    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text to max length."""
        if len(text) <= max_len:
            return text
        return text[:max_len - 3] + "..."


# Global printer manager instance
printer_manager = PrinterManager()


def get_printer_manager() -> PrinterManager:
    """Get printer manager instance."""
    return printer_manager
