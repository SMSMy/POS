"""
═══════════════════════════════════════════════════════════════════════════════
Restaurant POS System - Telegram Integration
═══════════════════════════════════════════════════════════════════════════════
Sends reports and notifications via Telegram Bot API
Queue system for offline/failed messages
═══════════════════════════════════════════════════════════════════════════════
"""

import threading
import time
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from loguru import logger

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.warning("requests not installed - Telegram disabled")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from database import db_manager, get_setting, set_setting, get_default_db_path


class TelegramManager:
    """
    Manages Telegram bot integration.
    Features:
    - 16 report types
    - Queue system for failed messages
    - Background retry thread
    """

    # Report types with Arabic/English names
    REPORT_TYPES = {
        'shift_open': ('فتح وردية', 'Shift Opened'),
        'shift_close': ('إغلاق وردية', 'Shift Closed'),
        'daily_summary': ('الملخص اليومي', 'Daily Summary'),
        'monthly_summary': ('الملخص الشهري', 'Monthly Summary'),
        'low_stock': ('نقص المخزون', 'Low Stock Alert'),
        'low_ingredients': ('نقص المكونات', 'Low Ingredients Alert'),
        'top_products': ('الأكثر مبيعاً', 'Top Products'),
        'profit_report': ('تقرير الأرباح', 'Profit Report'),
        'shortage_alert': ('تنبيه عجز', 'Shortage Alert'),
        'surplus_alert': ('تنبيه زيادة', 'Surplus Alert'),
        'return_processed': ('مرتجع', 'Return Processed'),
        'ingredient_usage': ('استهلاك المكونات', 'Ingredient Usage'),
        'cash_movement': ('حركة نقدية', 'Cash Movement'),
        'print_failed': ('فشل الطباعة', 'Print Failed'),
        'login': ('تسجيل دخول', 'Login'),
        'price_change': ('تغيير سعر', 'Price Changed'),
    }

    def __init__(self):
        """Initialize Telegram manager."""
        self._retry_thread: Optional[threading.Thread] = None
        self._stop_retry = threading.Event()
        self._load_settings()
        logger.info("TelegramManager initialized")

    def _load_settings(self):
        """Load Telegram settings from database."""
        self.bot_token = get_setting('telegram_bot_token', '')
        self.chat_id = get_setting('telegram_chat_id', '')
        self.topic_id = get_setting('telegram_topic_id', '')
        self.enabled = get_setting('telegram_enabled', '0') == '1'

        # Load report toggles
        self.report_settings = {}
        for report_type in self.REPORT_TYPES:
            key = f'telegram_{report_type}'
            self.report_settings[report_type] = get_setting(key, '1') == '1'

    def reload_settings(self):
        """Reload settings from database."""
        self._load_settings()

    @property
    def is_configured(self) -> bool:
        """Check if Telegram is properly configured."""
        return bool(self.bot_token and self.chat_id)

    def send_message(self, message: str, parse_mode: str = "HTML") -> Tuple[bool, str]:
        """
        Send message via Telegram Bot API.

        Args:
            message: Message text (supports HTML formatting)
            parse_mode: Telegram parse mode (HTML or Markdown)

        Returns:
            (success, error_message)
        """
        if not HAS_REQUESTS:
            return False, "requests library not installed"

        if not self.is_configured:
            return False, "Telegram not configured"

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }

            # Add topic ID if configured (for group topics)
            if self.topic_id:
                payload["message_thread_id"] = self.topic_id

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.debug(f"Telegram message sent successfully")
                return True, ""
            else:
                error = response.json().get('description', 'Unknown error')
                logger.warning(f"Telegram API error: {error}")
                return False, error

        except requests.Timeout:
            return False, "Request timeout"
        except requests.RequestException as e:
            return False, str(e)
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False, str(e)

    def test_connection(self) -> Tuple[bool, str]:
        """Test Telegram connection with a test message."""
        test_message = "🔔 <b>اختبار الاتصال</b>\n\n✅ تم الاتصال بنجاح!\nConnection test successful!"
        return self.send_message(test_message)

    def send_with_queue(self, message: str, report_type: str) -> bool:
        """
        Send message with queue fallback - ASYNC (non-blocking).
        If sending fails, adds to queue for retry.

        Returns True immediately (message sent in background).
        """
        if not self.enabled:
            logger.debug(f"Telegram disabled, skipping {report_type}")
            return False

        # Check if this report type is enabled
        if not self.report_settings.get(report_type, True):
            logger.debug(f"Report type {report_type} disabled")
            return False

        # إرسال في الخلفية - لا يحجب واجهة المستخدم
        def _send_in_background():
            try:
                success, error = self.send_message(message)
                if not success:
                    self._queue_message(message, report_type)
                    logger.info(f"Telegram message queued: {report_type}")
            except Exception as e:
                logger.error(f"Background send error: {e}")
                self._queue_message(message, report_type)

        thread = threading.Thread(target=_send_in_background, daemon=True)
        thread.start()
        return True  # Returns immediately

    def _queue_message(self, message: str, report_type: str):
        """Add message to queue for retry."""
        try:
            import sqlite3
            import sqlite3
            db_path = get_setting('db_path', get_default_db_path())
            if not db_path: db_path = get_default_db_path()

            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    INSERT INTO telegram_queue (message, report_type, attempt_count, max_attempts)
                    VALUES (?, ?, 0, 10)
                """, (message, report_type))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to queue Telegram message: {e}")

    def _get_pending_messages(self) -> List[Dict]:
        """Get pending messages from queue."""
        try:
            import sqlite3
            db_path = get_setting('db_path', get_default_db_path())
            if not db_path: db_path = get_default_db_path()

            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM telegram_queue
                    WHERE sent_at IS NULL AND attempt_count < max_attempts
                    ORDER BY created_at ASC
                    LIMIT 10
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get pending messages: {e}")
            return []

    def _mark_sent(self, message_id: int):
        """Mark message as sent."""
        try:
            import sqlite3
            db_path = get_setting('db_path', get_default_db_path())
            if not db_path: db_path = get_default_db_path()

            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    UPDATE telegram_queue SET sent_at = CURRENT_TIMESTAMP WHERE id = ?
                """, (message_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to mark message as sent: {e}")

    def _increment_attempt(self, message_id: int, error: str):
        """Increment attempt count and record error."""
        try:
            import sqlite3
            db_path = get_setting('db_path', get_default_db_path())
            if not db_path: db_path = get_default_db_path()

            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    UPDATE telegram_queue
                    SET attempt_count = attempt_count + 1, error_message = ?
                    WHERE id = ?
                """, (error, message_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to increment attempt: {e}")

    def process_queue(self) -> int:
        """
        Process pending messages in queue.

        Returns number of successfully sent messages.
        """
        pending = self._get_pending_messages()
        sent_count = 0

        for msg in pending:
            if msg['attempt_count'] >= msg['max_attempts']:
                continue

            success, error = self.send_message(msg['message'])

            if success:
                self._mark_sent(msg['id'])
                sent_count += 1
                logger.info(f"Queued message sent: #{msg['id']}")
            else:
                self._increment_attempt(msg['id'], error)
                logger.warning(f"Queue retry failed: #{msg['id']} - {error}")

        return sent_count

    def start_retry_thread(self, interval_seconds: int = 300):
        """Start background thread for queue processing."""
        if self._retry_thread and self._retry_thread.is_alive():
            return

        self._stop_retry.clear()
        self._retry_thread = threading.Thread(
            target=self._retry_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self._retry_thread.start()
        logger.info(f"Telegram retry thread started (interval: {interval_seconds}s)")

    def stop_retry_thread(self):
        """Stop the background retry thread."""
        self._stop_retry.set()
        if self._retry_thread:
            self._retry_thread.join(timeout=5)
        logger.info("Telegram retry thread stopped")

    def _retry_loop(self, interval: int):
        """Background loop for processing queue."""
        while not self._stop_retry.is_set():
            try:
                sent = self.process_queue()
                if sent > 0:
                    logger.info(f"Processed {sent} queued messages")
            except Exception as e:
                logger.error(f"Queue processing error: {e}")

            # Wait with interruptible sleep
            self._stop_retry.wait(timeout=interval)

    # ═══════════════════════════════════════════════════════════════════════════
    # REPORT GENERATORS
    # ═══════════════════════════════════════════════════════════════════════════

    def send_shift_open_report(self, shift: Dict):
        """Send shift opening report."""
        message = f"""
🟢 <b>فتح وردية | Shift Opened</b>
═══════════════════════════
📋 الوردية: #{shift.get('shift_number', '')}
👤 الكاشير: {shift.get('cashier_name', '')}
💰 مبلغ البداية: {shift.get('starting_amount', 0):.2f} ر.س
⏰ الوقت: {shift.get('opened_at', '')}
"""
        self.send_with_queue(message.strip(), 'shift_open')

    def send_shift_close_report(self, shift: Dict):
        """Send shift closing report."""
        diff = shift.get('difference', 0)
        diff_emoji = "⚠️ عجز" if diff < 0 else "✅ زيادة" if diff > 0 else "✅ متطابق"

        # Payment breakdown
        breakdown = shift.get('payment_breakdown', {})
        delivery_app_sales = breakdown.get('delivery_app', 0)

        method_names = {'cash': 'نقداً', 'card': 'بطاقة', 'transfer': 'تحويل', 'delivery_app': 'توصيل (لا تُحسب)', 'multi': 'متعدد'}
        breakdown_lines = ""
        for method, amount in breakdown.items():
            label = method_names.get(method, method)
            breakdown_lines += f"  ↳ {label}: {amount:.2f} ر.س\n"

        # ملاحظة للتوصيل إذا وُجدت
        delivery_note = ""
        if delivery_app_sales > 0:
            delivery_note = f"\n📱 ملاحظة: مبيعات التوصيل ({delivery_app_sales:.2f}) تذهب لحسابات التطبيقات"

        message = f"""
🔴 <b>إغلاق وردية | Shift Closed</b>
═══════════════════════════
📋 الوردية: #{shift.get('shift_number', '')}
👤 الكاشير: {shift.get('cashier_name', '')}
⏰ من: {shift.get('opened_at', '')}
⏰ إلى: {shift.get('closed_at', '')}

💰 مبلغ البداية: {shift.get('starting_amount', 0):.2f} ر.س
💵 المبيعات: {shift.get('total_sales', 0):.2f} ر.س
{breakdown_lines}🔄 المرتجعات: {shift.get('total_returns', 0):.2f} ر.س
➕ الإيداعات: {shift.get('total_deposits', 0):.2f} ر.س
➖ السحوبات: {shift.get('total_withdrawals', 0):.2f} ر.س
═══════════════════════════
✅ المتوقع في الخزينة: {shift.get('expected_amount', 0):.2f} ر.س
💵 الفعلي: {shift.get('actual_amount', 0):.2f} ر.س
{diff_emoji}: {abs(diff):.2f} ر.س
{delivery_note}
📝 الفواتير: {shift.get('total_invoices', 0)}
"""
        self.send_with_queue(message.strip(), 'shift_close')

    def send_daily_summary(self, summary: Dict):
        """Send comprehensive daily sales summary."""
        # Top products
        top_products_str = ""
        if summary.get('top_products'):
            top_products_str = "\n🏆 <b>الأكثر مبيعاً | Top Products</b>\n" + "\n".join([
                f"  • {p['name']}: {p['quantity']:.0f} ({p['total']:.2f})"
                for p in summary.get('top_products', [])[:5]
            ])

        # Cash movements
        movements_str = ""
        deposits = summary.get('total_deposits', 0)
        withdrawals = summary.get('total_withdrawals', 0)
        expenses = summary.get('total_expenses', 0)

        if deposits > 0 or withdrawals > 0 or expenses > 0:
            movements_str = f"""
💳 <b>الحركات النقدية | Cash Movements</b>
  ➕ إيداعات: {deposits:.2f}
  ➖ سحوبات: {withdrawals:.2f}
  💸 مصروفات: {expenses:.2f}"""

        # Profit info
        profit_str = ""
        if summary.get('total_profit') is not None:
            profit_str = f"""
📈 <b>الأرباح | Profit</b>
  💰 الربح: {summary.get('total_profit', 0):.2f}
  📊 الهامش: {summary.get('profit_margin', 0):.1f}%"""

        message = f"""
📊 <b>الملخص اليومي الشامل | Daily Summary</b>
═══════════════════════════
📅 التاريخ: {summary.get('date', datetime.now().strftime('%Y-%m-%d'))}

📝 <b>المبيعات | Sales</b>
  • الفواتير: {summary.get('invoice_count', 0)}
  • المبيعات: {summary.get('total_sales', 0):.2f}
  • المرتجعات: {summary.get('total_returns', 0):.2f}
  • الصافي: {summary.get('net_sales', 0):.2f}
  • الضريبة: {summary.get('total_tax', 0):.2f}

💳 <b>طرق الدفع | Payment Methods</b>
  • نقدي: {summary.get('cash_sales', 0):.2f}
  • شبكة: {summary.get('card_sales', 0):.2f}
{movements_str}
{profit_str}
{top_products_str}
═══════════════════════════
⏰ {datetime.now().strftime('%H:%M')}
"""
        # Check for separate bot for daily summary
        use_separate = get_setting('daily_summary_separate_bot', '0') == '1'

        if use_separate:
            separate_token = get_setting('daily_summary_bot_token', '')
            separate_chat = get_setting('daily_summary_chat_id', '')
            separate_topic = get_setting('daily_summary_topic_id', '')

            if separate_token and separate_chat:
                try:
                    self._send_to_separate_bot(message.strip(), separate_token, separate_chat, separate_topic)
                    return
                except Exception as e:
                    logger.error(f"Failed to send to separate bot, falling back to main: {e}")

        self.send_with_queue(message.strip(), 'daily_summary')

    def _send_to_separate_bot(self, message: str, bot_token: str, chat_id: str, topic_id: str = ''):
        """Send message to a separate bot directly."""
        if not HAS_REQUESTS:
            logger.warning("Requests library not available for separate bot")
            return

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        if topic_id:
            payload["message_thread_id"] = topic_id

        response = requests.post(url, json=payload, timeout=10)

        if response.status_code != 200:
            error = response.json().get('description', 'Unknown error')
            raise Exception(f"Telegram API error: {error}")

        logger.info("Daily summary sent via separate bot")

    def send_low_stock_alert(self, products: List[Dict]):
        """Send low stock alert."""
        if get_setting('telegram_low_stock', '1') != '1':
            return

        if not products:
            return

        items = "\n".join([
            f"• {p['name']}: {p['quantity']:.0f} (الحد: {p['min_alert_level']:.0f})"
            for p in products[:10]  # Limit to 10 items
        ])

        message = f"""
⚠️ <b>تنبيه نقص المخزون | Low Stock Alert</b>
═══════════════════════════
🔢 عدد المنتجات: {len(products)}

{items}
{"..." if len(products) > 10 else ""}
"""
        self.send_with_queue(message.strip(), 'low_stock')

    def send_low_ingredients_alert(self, ingredients: List[Dict]):
        """Send low ingredients alert."""
        if get_setting('telegram_low_ingredients', '1') != '1':
            return

        if not ingredients:
            return

        items = "\n".join([
            f"• {i['name']}: {i['quantity']:.2f} {i['unit']} (الحد: {i['min_alert_level']:.2f})"
            for i in ingredients[:10]
        ])

        message = f"""
⚠️ <b>تنبيه نقص المكونات | Low Ingredients Alert</b>
═══════════════════════════
🔢 عدد المكونات: {len(ingredients)}

{items}
{"..." if len(ingredients) > 10 else ""}
"""
        self.send_with_queue(message.strip(), 'low_ingredients')

    def send_cash_movement_alert(self, movement: Dict):
        """Send cash movement notification."""
        if get_setting('telegram_cash_movement', '1') != '1':
            return

        type_names = {
            'deposit': ('إيداع', '➕'),
            'withdrawal': ('سحب للمالك', '➖'),
            'expense': ('مصروف', '💸')
        }

        name, emoji = type_names.get(movement['type'], ('حركة', '💰'))

        # اسم المستلم (للسحب والمصروفات)
        recipient = movement.get('recipient_name', '')
        recipient_line = f"👤 المستلم: {recipient}\n" if recipient else ""

        message = f"""
{emoji} <b>{name} نقدي | Cash {movement['type'].title()}</b>
═══════════════════════════
💰 المبلغ: {movement['amount']:.2f} ر.س
📝 السبب: {movement['reason']}
📂 التصنيف: {movement.get('category', '')}
{recipient_line}👤 بواسطة: {movement.get('user_name', '')}
⏰ الوقت: {movement.get('created_at', '')}
"""
        self.send_with_queue(message.strip(), 'cash_movement')

    def send_price_change_alert(self, product: Dict, old_price: float, new_price: float, user: str):
        """Send price change notification."""
        if get_setting('telegram_price_change', '1') != '1':
            return

        change_pct = ((new_price - old_price) / old_price * 100) if old_price > 0 else 0
        message = f"""
💲 <b>تغيير سعر | Price Changed</b>
═══════════════════════════
📦 المنتج: {product.get('name', '')}
💰 السعر القديم: {old_price:.2f} ر.س
💰 السعر الجديد: {new_price:.2f} ر.س
📈 التغيير: {change_pct:.1f}%
👤 بواسطة: {user}
"""
        self.send_with_queue(message.strip(), 'price_change')

    def send_login_alert(self, user: Dict):
        """Send login notification."""
        if get_setting('telegram_login', '1') != '1':
            return

        message = f"""
🔐 <b>تسجيل دخول | Login</b>
═══════════════════════════
👤 المستخدم: {user.get('display_name', '')}
🔑 الدور: {user.get('role', '')}
⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        self.send_with_queue(message.strip(), 'login')

    def send_return_alert(self, return_data: Dict):
        """Send return processed notification."""
        if get_setting('telegram_return_processed', '1') != '1':
            return

        message = f"""
🔄 <b>مرتجع | Return Processed</b>
═══════════════════════════
📋 رقم الفاتورة الأصلية: {return_data.get('original_invoice', '')}
💰 المبلغ المسترد: {return_data.get('amount', 0):.2f} ر.س
📝 السبب: {return_data.get('reason', '')}
👤 بواسطة: {return_data.get('user', '')}
"""
        self.send_with_queue(message.strip(), 'return_processed')

    def send_profit_report(self, report: Dict):
        """Send profit report."""
        if get_setting('telegram_profit_report', '1') != '1':
            return

        message = f"""
💰 <b>تقرير الأرباح | Profit Report</b>
═══════════════════════════
📅 الفترة: {report.get('period', '')}
💵 إجمالي المبيعات: {report.get('total_sales', 0):.2f} ر.س
💸 إجمالي التكلفة: {report.get('total_cost', 0):.2f} ر.س
📈 صافي الربح: {report.get('net_profit', 0):.2f} ر.س
📊 نسبة الربح: {report.get('profit_margin', 0):.1f}%
"""
        self.send_with_queue(message.strip(), 'profit_report')


    def start_scheduler(self):
        """Start daily summary scheduler."""
        self._scheduler_stop = threading.Event()
        self._scheduler_thread = threading.Thread(
            target=self._daily_scheduler_loop,
            daemon=True
        )
        self._scheduler_thread.start()
        logger.info("Daily summary scheduler started")

    def _daily_scheduler_loop(self):
        """Loop to check for scheduled daily summary time."""
        logger.info("Daily summary scheduler loop started")

        while not self._scheduler_stop.is_set():
            try:
                # Check setting - إعادة تحميل من قاعدة البيانات
                scheduled_time = get_setting('daily_summary_time', '00:00')
                last_sent_date = get_setting('daily_summary_last_sent_date', '')
                current_date = datetime.now().strftime('%Y-%m-%d')
                current_time = datetime.now().strftime('%H:%M')

                # Debug logging كل 5 دقائق
                current_minute = datetime.now().minute
                if current_minute % 5 == 0 and datetime.now().second < 15:
                    logger.debug(f"Scheduler check: now={current_time}, target={scheduled_time}, last_sent={last_sent_date}")

                # Check if matches time and not sent today
                # المطابقة: الوقت الحالي == الوقت المجدول ولم يُرسل اليوم
                if current_time == scheduled_time and last_sent_date != current_date:
                    logger.info(f"✅ Triggering scheduled daily summary for {current_date} at {current_time}")

                    # Generate and send report
                    summary_data = self._generate_daily_report_data()
                    self.send_daily_summary(summary_data)

                    # Update last sent
                    set_setting('daily_summary_last_sent_date', current_date)
                    logger.info(f"Daily summary sent successfully, updated last_sent_date to {current_date}")

                    # Wait for a minute to avoid double sending
                    time.sleep(60)

            except Exception as e:
                logger.error(f"Scheduler error: {e}")

            # Check every 15 seconds (كان 30، الآن 15 للدقة أفضل)
            self._scheduler_stop.wait(15)

    def _generate_daily_report_data(self) -> Dict:
        """Generate comprehensive daily report data from database."""
        today = datetime.now().strftime('%Y-%m-%d')

        # Base stats
        data = {
            'date': today,
            'invoice_count': 0,
            'total_sales': 0.0,
            'cash_sales': 0.0,
            'card_sales': 0.0,
            'total_returns': 0.0,
            'net_sales': 0.0,
            'total_tax': 0.0,
            'total_deposits': 0.0,
            'total_withdrawals': 0.0,
            'total_expenses': 0.0,
            'top_products': [],
            'total_profit': 0.0,
            'profit_margin': 0.0
        }

        try:
            # استخدام اتصال قاعدة بيانات جديد للخيط الحالي
            import sqlite3
            db_path = get_setting('db_path', 'pos_system.db')
            if not db_path or db_path == 'pos.db':
                 db_path = 'pos_system.db'

            # Create a new connection for this thread
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 1. Sales & Invoices (يعمل حتى بدون وردية - يبحث حسب التاريخ)
            try:
                cursor.execute("""
                    SELECT
                        COUNT(*) as count,
                        COALESCE(SUM(total), 0) as total,
                        COALESCE(SUM(tax_amount), 0) as tax,
                        COALESCE(SUM(paid_amount), 0) as paid
                    FROM invoices
                    WHERE DATE(created_at) = ? AND status != 'cancelled'
                """, (today,))
                sales_row = cursor.fetchone()
                if sales_row:
                    data['invoice_count'] = sales_row['count'] or 0
                    data['total_sales'] = sales_row['total'] or 0.0
                    data['total_tax'] = sales_row['tax'] or 0.0
            except Exception as e:
                logger.debug(f"Sales query error (may be empty): {e}")

            # 2. Returns (إذا كان هناك عمود type)
            try:
                cursor.execute("""
                    SELECT COALESCE(SUM(total), 0) as total
                    FROM invoices
                    WHERE DATE(created_at) = ? AND status != 'cancelled'
                    AND type = 'return'
                """, (today,))
                returns_row = cursor.fetchone()
                if returns_row:
                    data['total_returns'] = returns_row['total'] or 0.0
            except Exception as e:
                logger.debug(f"Returns query skipped: {e}")

            data['net_sales'] = data['total_sales'] - data['total_returns']

            # 3. Payment Methods - استخدام payment_method بدلاً من type
            try:
                cursor.execute("""
                    SELECT payment_method, COALESCE(SUM(amount), 0) as total
                    FROM payments
                    WHERE DATE(created_at) = ?
                    GROUP BY payment_method
                """, (today,))
                for row in cursor.fetchall():
                    method = row['payment_method']
                    if method == 'cash':
                        data['cash_sales'] = row['total'] or 0.0
                    elif method == 'card':
                        data['card_sales'] = row['total'] or 0.0
            except Exception as e:
                logger.debug(f"Payments query error: {e}")

            # 4. Cash Movements
            try:
                cursor.execute("""
                    SELECT type, COALESCE(SUM(amount), 0) as total
                    FROM cash_movements
                    WHERE DATE(created_at) = ?
                    GROUP BY type
                """, (today,))
                for row in cursor.fetchall():
                    if row['type'] == 'deposit':
                        data['total_deposits'] = row['total'] or 0.0
                    elif row['type'] == 'withdrawal':
                        data['total_withdrawals'] = row['total'] or 0.0
                    elif row['type'] == 'expense':
                        data['total_expenses'] = row['total'] or 0.0
            except Exception as e:
                logger.debug(f"Cash movements query error: {e}")

            # 5. Top Products
            try:
                cursor.execute("""
                    SELECT
                        p.name,
                        COALESCE(SUM(ii.quantity), 0) as quantity,
                        COALESCE(SUM(ii.line_total), 0) as total
                    FROM invoice_items ii
                    JOIN invoices i ON ii.invoice_id = i.id
                    JOIN products p ON ii.product_id = p.id
                    WHERE DATE(i.created_at) = ? AND i.status != 'cancelled'
                    GROUP BY ii.product_id
                    ORDER BY quantity DESC
                    LIMIT 5
                """, (today,))
                data['top_products'] = [dict(row) for row in cursor.fetchall()]
            except Exception as e:
                logger.debug(f"Top products query error: {e}")

            # 6. Profit Calculation
            try:
                cursor.execute("""
                    SELECT
                        COALESCE(SUM(ii.line_total), 0) as revenue,
                        COALESCE(SUM(ii.quantity * ii.cost_price), 0) as cost
                    FROM invoice_items ii
                    JOIN invoices i ON ii.invoice_id = i.id
                    WHERE DATE(i.created_at) = ? AND i.status != 'cancelled'
                """, (today,))
                profit_row = cursor.fetchone()
                if profit_row and profit_row['revenue']:
                    revenue = profit_row['revenue']
                    cost = profit_row['cost'] or 0
                    gross_profit = revenue - cost
                    data['total_profit'] = gross_profit
                    data['profit_margin'] = (gross_profit / revenue * 100) if revenue else 0
            except Exception as e:
                logger.debug(f"Profit query error: {e}")

            conn.close()

        except Exception as e:
            logger.error(f"Error generating daily report data: {e}")

        return data


# Global telegram manager instance
_telegram_manager = None


def get_telegram_manager() -> TelegramManager:
    """Get telegram manager instance."""
    global _telegram_manager
    if _telegram_manager is None:
        _telegram_manager = TelegramManager()
        # Start background threads
        _telegram_manager.start_retry_thread()
        _telegram_manager.start_scheduler()
    return _telegram_manager
