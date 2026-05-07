"""
ZATCA - الفاتورة الإلكترونية السعودية
Saudi Electronic Invoice (ZATCA) Utility
"""

import base64
import hashlib
from datetime import datetime
from typing import Dict
from loguru import logger


def generate_qr_code(invoice_data: Dict[str, any]) -> str:
    """
    توليد QR Code لـ ZATCA
    
    :param invoice_data: بيانات الفاتورة
    :return: نص QR Code مشفر base64
    """
    try:
        # TLV Encoding (Tag-Length-Value)
        def tlv_encode(tag: int, value: str) -> bytes:
            """ترميز TLV"""
            value_bytes = value.encode('utf-8')
            length = len(value_bytes)
            
            # التحقق من الحد الأقصى (255 بايت)
            if length > 255:
                raise ValueError(f"TLV value too long: {length} bytes (max 255)")
            
            return bytes([tag, length]) + value_bytes
        
        # البيانات المطلوبة
        seller_name = invoice_data.get('seller_name', '')
        vat_number = invoice_data.get('vat_number', '')
        timestamp = invoice_data.get('timestamp', datetime.now().isoformat())
        total = f"{invoice_data.get('total', 0):.2f}"
        vat = f"{invoice_data.get('vat', 0):.2f}"
        
        # بناء البيانات
        qr_data = b''
        qr_data += tlv_encode(1, seller_name)        # اسم البائع
        qr_data += tlv_encode(2, vat_number)         # الرقم الضريبي
        qr_data += tlv_encode(3, timestamp)          # التاريخ والوقت
        qr_data += tlv_encode(4, total)              # الإجمالي شامل الضريبة
        qr_data += tlv_encode(5, vat)                # مبلغ الضريبة
        
        # ترميز base64
        return base64.b64encode(qr_data).decode('utf-8')
        
    except Exception as e:
        logger.error(f"❌ خطأ في توليد QR Code: {e}")
        return ""


def validate_vat_number(vat_number: str) -> bool:
    """
    التحقق من صحة الرقم الضريبي السعودي
    
    :param vat_number: الرقم الضريبي
    :return: True إذا كان صحيحاً
    """
    try:
        # يجب أن يكون 15 رقماً
        if len(vat_number) != 15:
            return False
        
        # يجب أن يبدأ وينتهي بـ 3
        if not vat_number.startswith('3') or not vat_number.endswith('3'):
            return False
        
        # يجب أن يحتوي فقط على أرقام
        if not vat_number.isdigit():
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطأ في التحقق من الرقم الضريبي: {e}")
        return False


def generate_invoice_hash(invoice_data: str) -> str:
    """
    توليد Hash للفاتورة
    
    :param invoice_data: بيانات الفاتورة
    :return: SHA256 Hash
    """
    try:
        return hashlib.sha256(invoice_data.encode()).hexdigest()
    except Exception as e:
        logger.error(f"❌ خطأ في توليد Hash: {e}")
        return ""


def create_tlv_string(tag: int, value: str) -> str:
    """
    إنشاء سلسلة TLV
    
    :param tag: رقم التاج
    :param value: القيمة
    :return: سلسلة TLV
    """
    try:
        value_bytes = value.encode('utf-8')
        length = len(value_bytes)
        
        if length > 255:
            raise ValueError(f"Value too long: {length} bytes")
        
        # تحويل للهكس
        tag_hex = f"{tag:02x}"
        length_hex = f"{length:02x}"
        value_hex = value_bytes.hex()
        
        return tag_hex + length_hex + value_hex
        
    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء TLV: {e}")
        return ""


def generate_zatca_invoice_string(invoice_data: Dict[str, any]) -> str:
    """
    توليد سلسلة الفاتورة الكاملة لـ ZATCA
    
    :param invoice_data: بيانات الفاتورة
    :return: سلسلة الفاتورة
    """
    try:
        # TLV لكل حقل
        tlv_parts = []
        
        # اسم البائع (Tag 1)
        if invoice_data.get('seller_name'):
            tlv_parts.append(create_tlv_string(1, invoice_data['seller_name']))
        
        # الرقم الضريبي (Tag 2)
        if invoice_data.get('vat_number'):
            tlv_parts.append(create_tlv_string(2, invoice_data['vat_number']))
        
        # التاريخ (Tag 3)
        timestamp = invoice_data.get('timestamp', datetime.now().isoformat())
        tlv_parts.append(create_tlv_string(3, timestamp))
        
        # الإجمالي شامل الضريبة (Tag 4)
        total = f"{invoice_data.get('total', 0):.2f}"
        tlv_parts.append(create_tlv_string(4, total))
        
        # مبلغ الضريبة (Tag 5)
        vat = f"{invoice_data.get('vat', 0):.2f}"
        tlv_parts.append(create_tlv_string(5, vat))
        
        # دمج جميع الأجزاء
        return ''.join(tlv_parts)
        
    except Exception as e:
        logger.error(f"❌ خطأ في توليد سلسلة ZATCA: {e}")
        return ""