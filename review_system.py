import asyncio
import sqlite3
import time
import logging
import json
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest
from telethon.errors import FloodWaitError, PhoneNumberBannedError, AuthKeyError
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

class ReviewSystem:
    def __init__(self):
        self.spam_bot_username = "@SpamBot"
        self.loop = None  # سنحفظ event loop هنا
        logger.info("🔧 نظام المراجعة الجديد تم تفعيله!")

    def start_review_system(self):
        """بدء نظام المراجعة"""
        logger.info("🚀 بدء تشغيل نظام المراجعة...")
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                asyncio.run(self._review_loop())
                break
            except Exception as e:
                retry_count += 1
                logger.error(f"❌ خطأ في نظام المراجعة (محاولة {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    wait_time = 60 * retry_count
                    logger.info(f"🔄 إعادة المحاولة بعد {wait_time} ثانية...")
                    time.sleep(wait_time)
                else:
                    logger.error("❌ فشل نظام المراجعة بعد 3 محاولات")

    async def _review_loop(self):
        """حلقة المراجعة الرئيسية"""
        logger.info("🔄 بدء حلقة المراجعة...")
        
        # حفظ event loop للاستخدام في الإشعارات
        self.loop = asyncio.get_running_loop()

        while True:
            try:
                pending_reviews = self.get_pending_reviews()
                logger.info(f"📊 عدد الحسابات المعلقة: {len(pending_reviews)}")

                for review in pending_reviews:
                    review_id, user_id, phone, session_str, price, review_until, created_at, device_info_json, proxy_id = review

                    created_time = datetime.fromisoformat(created_at)
                    review_time = datetime.fromisoformat(review_until)
                    now = datetime.now()

                    time_since_created = (now - created_time).total_seconds()
                    time_remaining = (review_time - now).total_seconds()

                    if time_since_created < 30:
                        logger.info(f"🆕 حساب جديد: {phone} - بدء المراجعة الأولية")
                        await self.initial_review(review_id, user_id, phone, session_str, device_info_json, proxy_id)
                    
                    elif time_remaining <= 0:
                        logger.info(f"⏰ وقت المراجعة انتهى للرقم {phone} - المراجعة النهائية")
                        await self.final_review(review_id, user_id, phone, session_str, price, device_info_json, proxy_id)
                    
                    else:
                        minutes_left = int(time_remaining / 60)
                        logger.info(f"⏳ الرقم {phone} - الوقت المتبقي: {minutes_left} دقيقة")

                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"❌ خطأ في حلقة المراجعة: {e}")
                await asyncio.sleep(30)

    async def initial_review(self, review_id, user_id, phone, session_str, device_info_json=None, proxy_id=None):
        """المراجعة الأولية - بعد التسجيل مباشرة"""
        logger.info(f"🔍 المراجعة الأولية للرقم: {phone}")

        try:
            # جلب معلومات الجهاز
            device_info = json.loads(device_info_json) if device_info_json else {}
            
            # جلب البروكسي المخصص للحساب
            proxy_config = None
            if proxy_id:
                import database
                proxy_data = database.get_proxy_by_id(proxy_id)
                if proxy_data:
                    proxy_config = database.parse_proxy_address(proxy_data[1])
                    logger.info(f"🔒 استخدام البروكسي ID: {proxy_id} للرقم: {phone}")
            
            client = TelegramClient(
                StringSession(session_str), 
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
                logger.error(f"❌ الجلسة غير صالحة للرقم: {phone}")
                await client.disconnect()
                self.reject_account(review_id, user_id, ["الجلسة غير صالحة"])
                return

            issues = []

            logger.info(f"1️⃣ إضافة 2FA للرقم {phone}")
            if not await self.add_2fa(client):
                issues.append("فشل في تأمين الحساب")

            if not issues:
                logger.info(f"2️⃣ فحص السبام للرقم {phone}")
                spam_result = await self.check_spam(client)
                if spam_result:
                    issues.append("حساب سبام")

            if not issues:
                logger.info(f"3️⃣ فحص التجميد للرقم {phone}")
                frozen_result = await self.check_frozen(client)
                if frozen_result:
                    issues.append("الحساب مجمد")

            if not issues:
                logger.info(f"4️⃣ فحص الجلسات للرقم {phone}")
                sessions_result = await self.logout_all_sessions(client)
                
                if not sessions_result['success'] and sessions_result['had_sessions']:
                    logger.warning(f"⚠️ فشل في الخروج من بعض الجلسات - سيتم المحاولة مرة أخرى في المراجعة النهائية")

            await client.disconnect()

            if issues:
                logger.error(f"❌ رفض الحساب {phone} في المراجعة الأولية: {issues}")
                self.reject_account(review_id, user_id, issues)
            else:
                logger.info(f"✅ المراجعة الأولية نجحت للرقم {phone} - انتظار المراجعة النهائية")
                self.mark_initial_review_done(review_id)

        except Exception as e:
            logger.error(f"❌ خطأ في المراجعة الأولية {phone}: {e}")
            self.reject_account(review_id, user_id, [f"خطأ في المراجعة: {str(e)}"])

    async def final_review(self, review_id, user_id, phone, session_str, price, device_info_json=None, proxy_id=None):
        """المراجعة النهائية - بعد انتهاء الوقت"""
        logger.info(f"🔍 المراجعة النهائية للرقم: {phone}")

        try:
            # جلب معلومات الجهاز
            device_info = json.loads(device_info_json) if device_info_json else {}
            
            # جلب البروكسي المخصص للحساب
            proxy_config = None
            if proxy_id:
                import database
                proxy_data = database.get_proxy_by_id(proxy_id)
                if proxy_data:
                    proxy_config = database.parse_proxy_address(proxy_data[1])
                    logger.info(f"🔒 استخدام البروكسي ID: {proxy_id} للرقم: {phone}")
            
            client = TelegramClient(
                StringSession(session_str), 
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
                logger.error(f"❌ الجلسة غير صالحة للرقم: {phone}")
                await client.disconnect()
                self.reject_account(review_id, user_id, ["الجلسة غير صالحة"])
                return

            issues = []

            logger.info(f"1️⃣ فحص التجميد النهائي للرقم {phone}")
            frozen_result = await self.check_frozen(client)
            if frozen_result:
                issues.append("الحساب مجمد")

            if not issues:
                logger.info(f"2️⃣ فحص الجلسات النهائي للرقم {phone}")
                sessions_result = await self.logout_all_sessions(client)
                
                if not sessions_result['success'] and sessions_result['had_sessions']:
                    logger.warning(f"⚠️ فشل في الخروج من الجلسات - تأجيل 24 ساعة")
                    await client.disconnect()
                    self.delay_review_24h(review_id)
                    return

            await client.disconnect()

            if issues:
                logger.error(f"❌ رفض الحساب {phone}: {issues}")
                self.reject_account(review_id, user_id, issues)
            else:
                logger.info(f"✅ قبول الحساب {phone}")
                self.approve_account(review_id, user_id, price)

        except Exception as e:
            logger.error(f"❌ خطأ في المراجعة النهائية {phone}: {e}")
            self.reject_account(review_id, user_id, [f"خطأ في المراجعة: {str(e)}"])

    async def add_2fa(self, client):
        """إضافة كلمة مرور 2FA"""
        try:
            me = await client.get_me()
            if not me:
                return False

            try:
                await client.edit_2fa(
                    current_password=None,
                    new_password=config.TWO_FA_PASSWORD,
                    hint="كلمة مرور البوت"
                )
                logger.info("✅ تم إضافة 2FA")
                return True
            except Exception as e:
                error_msg = str(e).lower()
                if any(word in error_msg for word in ['password', 'already', 'two', 'step']):
                    logger.info("✅ 2FA موجود مسبقاً")
                    return True
                logger.warning(f"⚠️ خطأ في إضافة 2FA: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ خطأ في فحص 2FA: {e}")
            return False

    async def check_spam(self, client):
        """فحص السبام عن طريق SpamBot"""
        try:
            await client.send_message(self.spam_bot_username, "/start")
            await asyncio.sleep(3)

            messages = await client.get_messages(self.spam_bot_username, limit=3)

            for msg in messages:
                if msg.message:
                    text = msg.message.lower()
                    
                    if any(word in text for word in ['good news', 'no limits', 'free as a bird', 'no restrictions']):
                        logger.info("✅ الحساب نظيف من السبام")
                        return False
                    
                    if any(word in text for word in ['spam', 'limited', 'restricted', 'banned']):
                        logger.warning("❌ الحساب سبام")
                        return True

            logger.info("✅ الحساب نظيف (لا توجد مؤشرات)")
            return False

        except Exception as e:
            logger.error(f"❌ خطأ في فحص السبام: {e}")
            return False

    async def check_frozen(self, client):
        """فحص التجميد عن طريق إرسال رسالة للـ Saved Messages"""
        try:
            me = await client.get_me()
            test_message = await client.send_message('me', '🔍 اختبار التجميد')
            await asyncio.sleep(2)
            
            try:
                await test_message.delete()
                logger.info("✅ الحساب غير مجمد")
                return False
            except:
                logger.warning("❌ الحساب مجمد")
                return True

        except Exception as e:
            error_msg = str(e).lower()
            if any(word in error_msg for word in ['frozen', 'banned', 'deactivated']):
                logger.warning("❌ الحساب مجمد")
                return True
            logger.error(f"❌ خطأ في فحص التجميد: {e}")
            return False

    async def logout_all_sessions(self, client):
        """الخروج من جميع الجلسات الأخرى"""
        try:
            auths = await client(GetAuthorizationsRequest())
            other_sessions = [auth for auth in auths.authorizations if not auth.current]
            
            logger.info(f"📊 عدد الجلسات الأخرى: {len(other_sessions)}")

            if not other_sessions:
                logger.info("✅ لا توجد جلسات أخرى")
                return {'success': True, 'had_sessions': False}

            failed = 0
            for session in other_sessions:
                try:
                    await client(ResetAuthorizationRequest(hash=session.hash))
                    logger.info(f"✅ تم الخروج من: {session.device_model}")
                except Exception as e:
                    logger.warning(f"❌ فشل الخروج من جلسة: {e}")
                    failed += 1

            if failed == 0:
                logger.info("✅ تم الخروج من جميع الجلسات")
                return {'success': True, 'had_sessions': True}
            else:
                logger.warning(f"⚠️ فشل الخروج من {failed} جلسة")
                return {'success': False, 'had_sessions': True}

        except Exception as e:
            logger.error(f"❌ خطأ في فحص الجلسات: {e}")
            return {'success': False, 'had_sessions': False}

    def get_pending_reviews(self):
        """جلب الحسابات المعلقة"""
        try:
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, user_id, phone_number, session_string, price, review_until, created_at, device_info, proxy_id 
                FROM account_reviews 
                WHERE status = 'pending'
            ''')
            reviews = cursor.fetchall()
            conn.close()
            return reviews
        except Exception as e:
            logger.error(f"❌ خطأ في جلب المراجعات: {e}")
            return []

    def mark_initial_review_done(self, review_id):
        """تحديث أن المراجعة الأولية تمت"""
        try:
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            cursor.execute('UPDATE account_reviews SET issues = ? WHERE id = ?', 
                         ('initial_review_done', review_id))
            conn.commit()
            conn.close()
            logger.info(f"✅ تم تحديث حالة المراجعة الأولية")
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث المراجعة: {e}")

    def delay_review_24h(self, review_id):
        """تأجيل المراجعة 24 ساعة"""
        try:
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            
            new_review_time = (datetime.now() + timedelta(hours=24)).isoformat()
            
            cursor.execute('SELECT user_id, phone_number FROM account_reviews WHERE id = ?', (review_id,))
            result = cursor.fetchone()
            
            if result:
                user_id, phone_number = result
                
                cursor.execute('UPDATE account_reviews SET review_until = ?, issues = ? WHERE id = ?', 
                             (new_review_time, 'delayed_24h_sessions', review_id))
                conn.commit()
                logger.info(f"⏰ تم تأجيل المراجعة 24 ساعة للحساب رقم {review_id}")
                
                # إرسال الإشعار عبر event loop إذا كان متاحاً
                if self.loop and self.loop.is_running():
                    try:
                        asyncio.run_coroutine_threadsafe(
                            self.notify_user_delay(user_id, phone_number),
                            self.loop
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ فشل إرسال إشعار التأجيل: {e}")
            
            conn.close()
        except Exception as e:
            logger.error(f"❌ خطأ في تأجيل المراجعة: {e}")

    def approve_account(self, review_id, user_id, price):
        """قبول الحساب"""
        try:
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()

            cursor.execute('SELECT phone_number, session_string FROM account_reviews WHERE id = ?', (review_id,))
            result = cursor.fetchone()
            
            if result:
                phone_number, session_string = result

                cursor.execute('''
                    INSERT INTO accounts (user_id, phone_number, session_string, status, price, created_at)
                    VALUES (?, ?, ?, 'approved', ?, ?)
                ''', (user_id, phone_number, session_string, price, datetime.now().isoformat()))

                cursor.execute('UPDATE account_reviews SET status = ? WHERE id = ?', ('approved', review_id))

                cursor.execute('UPDATE users SET balance = balance + ?, total_earnings = total_earnings + ? WHERE user_id = ?', 
                             (price, price, user_id))

                conn.commit()
                logger.info(f"✅ تم قبول الحساب {phone_number}")

                # إرسال الإشعار عبر event loop إذا كان متاحاً
                if self.loop and self.loop.is_running():
                    try:
                        asyncio.run_coroutine_threadsafe(
                            self.notify_user_approval(user_id, phone_number, price),
                            self.loop
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ فشل إرسال إشعار القبول: {e}")

            conn.close()
        except Exception as e:
            logger.error(f"❌ خطأ في قبول الحساب: {e}")

    def reject_account(self, review_id, user_id, issues):
        """رفض الحساب"""
        try:
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()

            cursor.execute('SELECT phone_number FROM account_reviews WHERE id = ?', (review_id,))
            result = cursor.fetchone()
            
            if result:
                phone_number = result[0]
                issues_text = ', '.join(issues)

                cursor.execute('UPDATE account_reviews SET status = ?, issues = ? WHERE id = ?', 
                             ('rejected', issues_text, review_id))

                conn.commit()
                logger.info(f"❌ تم رفض الحساب {phone_number}: {issues_text}")

                # إرسال الإشعار عبر event loop إذا كان متاحاً
                if self.loop and self.loop.is_running():
                    try:
                        asyncio.run_coroutine_threadsafe(
                            self.notify_user_rejection(user_id, phone_number, issues_text),
                            self.loop
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ فشل إرسال إشعار الرفض: {e}")

            conn.close()
        except Exception as e:
            logger.error(f"❌ خطأ في رفض الحساب: {e}")

    async def notify_user_approval(self, user_id, phone_number, price):
        """إشعار المستخدم بالقبول"""
        try:
            from telegram import Bot
            if not config.BOT_TOKEN:
                return
            bot = Bot(token=config.BOT_TOKEN)
            
            message = f"""
✅ **تم قبول حسابك!**

📱 **الرقم:** `{phone_number}`
💰 **المبلغ:** {price} جنيه

تم إضافة المبلغ إلى رصيدك! 🎉
            """
            
            await bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
            logger.info(f"📤 تم إرسال إشعار القبول للمستخدم {user_id}")
        except Exception as e:
            logger.error(f"❌ فشل في إرسال إشعار القبول: {e}")

    async def notify_user_rejection(self, user_id, phone_number, issues):
        """إشعار المستخدم بالرفض"""
        try:
            from telegram import Bot
            if not config.BOT_TOKEN:
                return
            bot = Bot(token=config.BOT_TOKEN)
            
            message = f"""
❌ **تم رفض حسابك**

📱 **الرقم:** `{phone_number}`
⚠️ **السبب:** {issues}

يرجى محاولة إضافة حساب آخر.
            """
            
            await bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
            logger.info(f"📤 تم إرسال إشعار الرفض للمستخدم {user_id}")
        except Exception as e:
            logger.error(f"❌ فشل في إرسال إشعار الرفض: {e}")

    async def notify_user_delay(self, user_id, phone_number):
        """إشعار المستخدم بالتأجيل 24 ساعة"""
        try:
            from telegram import Bot
            if not config.BOT_TOKEN:
                return
            bot = Bot(token=config.BOT_TOKEN)
            
            message = f"""
⏰ **تم تأجيل مراجعة حسابك**

📱 **الرقم:** `{phone_number}`
⏳ **السبب:** الحساب عليه جلسات قديمة لم نتمكن من الخروج منها

🔄 **سيتم المراجعة مرة أخرى بعد 24 ساعة**

لا تقلق، سنحاول الخروج من الجلسات القديمة ومراجعة حسابك مرة أخرى.
            """
            
            await bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
            logger.info(f"📤 تم إرسال إشعار التأجيل للمستخدم {user_id}")
        except Exception as e:
            logger.error(f"❌ فشل في إرسال إشعار التأجيل: {e}")
