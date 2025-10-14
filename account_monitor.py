import asyncio
import sqlite3
import logging
import json
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, PhoneNumberBannedError, AuthKeyError, UserDeactivatedError
import config

logging.basicConfig(
    level=logging.INFO,
    format=config.LOGGING_CONFIG['format'],
    handlers=[
        logging.FileHandler(config.LOGGING_CONFIG['file']),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AccountMonitor:
    def __init__(self):
        import database as db
        self.check_interval_hours = int(db.get_setting('monitor_interval_hours', '2'))
        logger.info("🔧 نظام المراقبة الدورية للحسابات تم تفعيله!")

    def start_monitor(self):
        """بدء نظام المراقبة"""
        logger.info("🚀 بدء تشغيل نظام المراقبة الدورية...")
        while True:
            try:
                asyncio.run(self._monitor_loop())
            except Exception as e:
                logger.error(f"❌ خطأ في نظام المراقبة: {e}")
                import time
                time.sleep(300)
                logger.info("🔄 إعادة تشغيل نظام المراقبة...")

    async def _monitor_loop(self):
        """حلقة المراقبة الرئيسية"""
        logger.info("🔄 بدء حلقة المراقبة الدورية...")

        while True:
            try:
                import database as db
                
                monitor_enabled = db.get_setting('monitor_enabled', 'true') == 'true'
                self.check_interval_hours = int(db.get_setting('monitor_interval_hours', '2'))
                
                if monitor_enabled:
                    await self.check_all_accounts()
                else:
                    logger.info("⏸️ نظام المراقبة معطل - تخطي الفحص")
                
                wait_minutes = self.check_interval_hours * 60
                logger.info(f"⏳ الفحص القادم بعد {self.check_interval_hours} ساعة...")
                await asyncio.sleep(wait_minutes * 60)

            except Exception as e:
                logger.error(f"❌ خطأ في حلقة المراقبة: {e}")
                await asyncio.sleep(600)

    async def check_all_accounts(self):
        """فحص جميع الحسابات المقبولة"""
        logger.info("=" * 60)
        logger.info("🔍 بدء الفحص الدوري لجميع الحسابات...")
        logger.info("=" * 60)

        approved_accounts = self.get_approved_accounts()
        logger.info(f"📊 عدد الحسابات المقبولة: {len(approved_accounts)}")

        if not approved_accounts:
            logger.info("✅ لا توجد حسابات للفحص")
            return

        checked_count = 0
        valid_count = 0
        invalid_count = 0
        frozen_count = 0

        for account in approved_accounts:
            try:
                account_id = account[0]
                phone_number = account[2]
                session_string = account[3]
                device_info_json = account[9] if len(account) > 9 else None
                proxy_id = account[10] if len(account) > 10 else None
                
                logger.info(f"\n📱 فحص الرقم: {phone_number}")
                
                result = await self.check_account(
                    account_id, 
                    phone_number, 
                    session_string, 
                    device_info_json,
                    proxy_id
                )
                
                checked_count += 1
                
                if result['status'] == 'valid':
                    valid_count += 1
                    logger.info(f"✅ الرقم {phone_number} صالح ومتصل")
                elif result['status'] == 'frozen':
                    frozen_count += 1
                    logger.warning(f"❄️ الرقم {phone_number} متجمد")
                    self.mark_account_frozen(account_id, phone_number)
                elif result['status'] == 'invalid':
                    invalid_count += 1
                    logger.error(f"❌ الرقم {phone_number} جلسة غير صالحة")
                    self.mark_account_invalid(account_id, phone_number)
                
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"❌ خطأ في فحص الحساب: {e}")
                await asyncio.sleep(5)

        logger.info("\n" + "=" * 60)
        logger.info(f"📊 نتائج الفحص الدوري:")
        logger.info(f"   ✅ صالحة: {valid_count}")
        logger.info(f"   ❄️ متجمدة: {frozen_count}")
        logger.info(f"   ❌ غير صالحة: {invalid_count}")
        logger.info(f"   📈 إجمالي: {checked_count}")
        logger.info("=" * 60 + "\n")

        self.save_check_log(checked_count, valid_count, frozen_count, invalid_count)

    async def check_account(self, review_id, phone_number, session_string, device_info_json=None, proxy_id=None):
        """فحص حساب واحد"""
        try:
            device_info = {}
            if device_info_json:
                try:
                    device_info = json.loads(device_info_json)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"⚠️ فشل في قراءة معلومات الجهاز للرقم {phone_number}")
                    device_info = {}
            
            # جلب البروكسي المخصص للحساب
            proxy_config = None
            if proxy_id:
                import database
                proxy_data = database.get_proxy_by_id(proxy_id)
                if proxy_data:
                    proxy_config = database.parse_proxy_address(proxy_data[1])
                    logger.info(f"🔒 استخدام البروكسي ID: {proxy_id} للرقم: {phone_number}")
            
            client = TelegramClient(
                StringSession(session_string), 
                int(config.API_ID), 
                config.API_HASH,
                device_model=device_info.get("device_model", "Samsung Galaxy S24 Ultra"),
                system_version=device_info.get("system_version", "Android 14"),
                app_version=device_info.get("app_version", "Telegram Android 10.5.2"),
                lang_code="ar",
                system_lang_code="ar",
                proxy=proxy_config
            )
            
            await client.connect()

            if not await client.is_user_authorized():
                logger.warning(f"⚠️ الجلسة غير صالحة للرقم: {phone_number}")
                await client.disconnect()
                return {'status': 'invalid', 'reason': 'session_invalid'}

            is_frozen = await self.check_frozen(client)
            await client.disconnect()

            if is_frozen:
                return {'status': 'frozen', 'reason': 'account_frozen'}
            
            return {'status': 'valid'}

        except (PhoneNumberBannedError, UserDeactivatedError) as e:
            logger.error(f"❌ الحساب محظور أو معطل: {phone_number}")
            return {'status': 'invalid', 'reason': 'banned_or_deactivated'}
        except AuthKeyError as e:
            logger.error(f"❌ خطأ في مفتاح المصادقة: {phone_number}")
            return {'status': 'invalid', 'reason': 'auth_key_error'}
        except FloodWaitError as e:
            logger.warning(f"⚠️ فلود للرقم {phone_number}، الانتظار {e.seconds} ثانية")
            await asyncio.sleep(e.seconds)
            return {'status': 'valid'}
        except Exception as e:
            logger.error(f"❌ خطأ في فحص الحساب {phone_number}: {e}")
            return {'status': 'valid'}

    async def check_frozen(self, client):
        """فحص التجميد عن طريق إرسال رسالة للـ Saved Messages"""
        try:
            me = await client.get_me()
            test_message = await client.send_message('me', '🔍 فحص دوري')
            await asyncio.sleep(2)
            
            try:
                await test_message.delete()
                return False
            except:
                return True

        except Exception as e:
            error_msg = str(e).lower()
            if any(word in error_msg for word in ['frozen', 'banned', 'deactivated']):
                return True
            return False

    def get_approved_accounts(self):
        """جلب جميع الحسابات المقبولة من accounts و account_reviews"""
        try:
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            
            # جلب من accounts (الحسابات النشطة والجاهزة للفحص)
            cursor.execute('''
                SELECT 
                    a.id,
                    a.user_id,
                    a.phone_number,
                    a.session_string,
                    a.status,
                    NULL as review_until,
                    a.price,
                    NULL as issues,
                    a.created_at,
                    NULL as device_info,
                    a.proxy_id
                FROM accounts a
                WHERE a.status = 'approved'
                ORDER BY a.created_at ASC
            ''')
            accounts = cursor.fetchall()
            conn.close()
            return accounts
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الحسابات: {e}")
            return []

    def mark_account_frozen(self, account_id, phone_number):
        """تحديد حساب كمتجمد"""
        try:
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            
            # تحديث في جدول accounts
            cursor.execute('''
                UPDATE accounts 
                SET status = 'frozen'
                WHERE id = ?
            ''', (account_id,))
            
            # تحديث في account_reviews إن وجد
            cursor.execute('''
                UPDATE account_reviews 
                SET status = 'frozen', issues = 'الحساب متجمد - تم اكتشافه في الفحص الدوري'
                WHERE phone_number = ? AND status = 'approved'
            ''', (phone_number,))
            
            conn.commit()
            conn.close()
            logger.info(f"✅ تم تحديث حالة الحساب {phone_number} إلى متجمد")
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث حالة الحساب: {e}")

    def mark_account_invalid(self, account_id, phone_number):
        """تحديد حساب كجلسة غير صالحة"""
        try:
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            
            # تحديث في جدول accounts
            cursor.execute('''
                UPDATE accounts 
                SET status = 'invalid'
                WHERE id = ?
            ''', (account_id,))
            
            # تحديث في account_reviews إن وجد
            cursor.execute('''
                UPDATE account_reviews 
                SET status = 'invalid_session', issues = 'الجلسة غير صالحة - تم اكتشافه في الفحص الدوري'
                WHERE phone_number = ? AND status = 'approved'
            ''', (phone_number,))
            
            conn.commit()
            conn.close()
            logger.info(f"✅ تم تحديث حالة الحساب {phone_number} إلى غير صالح")
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث حالة الحساب: {e}")

    def save_check_log(self, total, valid, frozen, invalid):
        """حفظ سجل الفحص"""
        try:
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO monitor_logs (total_checked, valid_count, frozen_count, invalid_count, checked_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (total, valid, frozen, invalid, datetime.now().isoformat()))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ سجل الفحص: {e}")

if __name__ == "__main__":
    monitor = AccountMonitor()
    monitor.start_monitor()
