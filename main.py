from telegram.ext import ApplicationBuilder, CommandHandler, PicklePersistence
from handlers.start_handler import start, cancel_command, language_command, setup_start_handlers
from handlers.admin_panel import setup_admin_handlers
from handlers.ready_accounts import setup_ready_accounts_handlers
from handlers.admin_ready_accounts import setup_admin_ready_handlers
from handlers.admin_handlers_extra import setup_extra_handlers
from handlers.admin_countries import setup_countries_handlers
from handlers.admin_accounts import setup_accounts_handlers
import database
import config
import threading
import time
import logging
import sys
from datetime import datetime

# إعدادات التسجيل
logging.basicConfig(
    level=config.LOGGING_CONFIG['level'],
    format=config.LOGGING_CONFIG['format'],
    handlers=[
        logging.FileHandler(config.LOGGING_CONFIG['file']),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

print("🔧 بدء تحميل النظام المتقدم...")

# استيراد نظام المراجعة
ReviewSystem = None
HAS_REVIEW_SYSTEM = False
try:
    from review_system import ReviewSystem
    HAS_REVIEW_SYSTEM = True
    logger.info("✅ نظام المراجعة المتقدم متاح")
except ImportError as e:
    logger.error(f"❌ نظام المراجعة غير متاح: {e}")
except Exception as e:
    logger.error(f"❌ خطأ في تحميل نظام المراجعة: {e}")

# استيراد نظام المراقبة الدورية
AccountMonitor = None
HAS_MONITOR_SYSTEM = False
try:
    from account_monitor import AccountMonitor
    HAS_MONITOR_SYSTEM = True
    logger.info("✅ نظام المراقبة الدورية متاح")
except ImportError as e:
    logger.error(f"❌ نظام المراقبة الدورية غير متاح: {e}")
except Exception as e:
    logger.error(f"❌ خطأ في تحميل نظام المراقبة الدورية: {e}")

# استيراد Rate Limiter
try:
    from rate_limiter import RateLimiter
    rate_limiter = RateLimiter()
    logger.info("✅ نظام Rate Limiting متاح")
except ImportError as e:
    logger.error(f"❌ نظام Rate Limiting غير متاح: {e}")
    rate_limiter = None
except Exception as e:
    logger.error(f"❌ خطأ في تحميل نظام Rate Limiting: {e}")
    rate_limiter = None

def start_review_system():
    """تشغيل نظام المراجعة في thread منفصل"""
    if not HAS_REVIEW_SYSTEM:
        logger.error("❌ نظام المراجعة غير مفعل - التخطي")
        return

    logger.info("🚀 بدء تشغيل نظام المراجعة المتقدم في الخلفية...")

    retry_count = 0
    max_retries = 5
    
    while retry_count < max_retries:
        try:
            if ReviewSystem is None:
                logger.error("❌ ReviewSystem غير متاح")
                return
            system = ReviewSystem()
            logger.info("✅ تم إنشاء نظام المراجعة المتقدم")
            system.start_review_system()
            break
        except Exception as e:
            retry_count += 1
            logger.error(f"❌ خطأ في نظام المراجعة (محاولة {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                wait_time = min(30 * retry_count, 300)
                logger.info(f"🔄 إعادة تشغيل نظام المراجعة بعد {wait_time} ثانية...")
                time.sleep(wait_time)
            else:
                logger.error("❌ فشل نظام المراجعة بعد 5 محاولات - التوقف")

def start_monitor_system():
    """تشغيل نظام المراقبة الدورية في thread منفصل"""
    if not HAS_MONITOR_SYSTEM:
        logger.error("❌ نظام المراقبة الدورية غير مفعل - التخطي")
        return

    logger.info("🚀 بدء تشغيل نظام المراقبة الدورية في الخلفية...")
    
    time.sleep(60)

    while True:
        try:
            if AccountMonitor is None:
                logger.error("❌ AccountMonitor غير متاح")
                return
            monitor = AccountMonitor()
            logger.info("✅ تم إنشاء نظام المراقبة الدورية")
            monitor.start_monitor()
        except Exception as e:
            logger.error(f"❌ خطأ في نظام المراقبة الدورية: {e}")
            logger.info("🔄 إعادة تشغيل نظام المراقبة بعد 60 ثانية...")
            time.sleep(60)

def cleanup_expired_sessions():
    """تنظيف الجلسات المنتهية periodically"""
    try:
        import sqlite3
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()

        # تنظيف user_sessions المنتهية
        cursor.execute('DELETE FROM user_sessions WHERE expires_at < ?', 
                      (datetime.now().isoformat(),))

        # تنظيف verification_sessions المنتهية  
        cursor.execute('DELETE FROM verification_sessions WHERE expires_at < ?',
                      (datetime.now().isoformat(),))

        conn.commit()
        conn.close()
        logger.info("✅ تم تنظيف الجلسات المنتهية")
    except Exception as e:
        logger.error(f"❌ خطأ في تنظيف الجلسات: {e}")

def start_cleanup_scheduler():
    """بدء المجدول لتنظيف الجلسات"""
    while True:
        try:
            cleanup_expired_sessions()
            time.sleep(300)  # كل 5 دقائق
        except Exception as e:
            logger.error(f"❌ خطأ في مجدول التنظيف: {e}")
            time.sleep(60)

def main():
    logger.info("🎯 بدء تشغيل البوت المتقدم...")

    try:
        # تهيئة الداتابيز
        logger.info("📊 تهيئة قاعدة البيانات...")
        database.init_db()
        logger.info("✅ قاعدة البيانات جاهزة")

        # بناء البوت
        logger.info("🔨 بناء البوت...")
        if not config.BOT_TOKEN:
            logger.error("❌ BOT_TOKEN غير موجود في environment variables")
            sys.exit(1)
        
        # إضافة persistence لحفظ بيانات المستخدمين
        persistence = PicklePersistence(filepath='bot_persistence.pkl')
        app = ApplicationBuilder().token(config.BOT_TOKEN).persistence(persistence).build()
        logger.info("✅ البوت مبنى")

        # إضافة الـ main admin
        if config.ADMIN_ID and config.ADMIN_ID > 0:
            if not database.is_admin(config.ADMIN_ID):
                database.add_admin(config.ADMIN_ID, "Main Admin", config.ADMIN_ID)
                logger.info(f"✅ تم إضافة الـ Main Admin: {config.ADMIN_ID}")

        # إضافة ال handlers
        logger.info("🔗 إضافة ال handlers...")
        
        # إضافة CommandHandlers الأساسية
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("cancel", cancel_command))
        app.add_handler(CommandHandler("language", language_command))
        
        # معالج الأدمن لازم يكون الأول عشان ياخد الرسائل قبل معالج المستخدمين
        setup_admin_handlers(app)
        setup_admin_ready_handlers(app)
        setup_extra_handlers(app)
        setup_countries_handlers(app)
        setup_accounts_handlers(app)
        setup_ready_accounts_handlers(app)
        setup_start_handlers(app)
        logger.info("✅ ال handlers مضافين")

        # تشغيل نظام المراجعة
        if HAS_REVIEW_SYSTEM:
            logger.info("🔄 تشغيل نظام المراجعة المتقدم...")
            review_thread = threading.Thread(target=start_review_system, daemon=True)
            review_thread.start()
            logger.info("✅ نظام المراجعة المتقدم شغال في الخلفية")
        else:
            logger.warning("⚠️ نظام المراجعة غير شغال")

        # تشغيل نظام المراقبة الدورية
        if HAS_MONITOR_SYSTEM:
            logger.info("🔄 تشغيل نظام المراقبة الدورية...")
            monitor_thread = threading.Thread(target=start_monitor_system, daemon=True)
            monitor_thread.start()
            logger.info("✅ نظام المراقبة الدورية شغال في الخلفية")
        else:
            logger.warning("⚠️ نظام المراقبة الدورية غير شغال")

        # تشغيل مجدول التنظيف
        logger.info("🧹 تشغيل مجدول تنظيف الجلسات...")
        cleanup_thread = threading.Thread(target=start_cleanup_scheduler, daemon=True)
        cleanup_thread.start()
        logger.info("✅ مجدول التنظيف شغال")

        # تشغيل البوت
        logger.info("🎊 البوت المتقدم جاهز للعمل!")
        print("=" * 50)
        print("🚀 البوت اشتغل بنجاح!")
        print("📱 أرسل /start في تليجرام لتجربة البوت")
        print("🛡️  نظام Rate Limiting مفعل")
        print("🔒 نظام Circuit Breaker شغال")
        print("🔄 نظام إعادة المحاولة التلقائية مفعل")
        print("📝 نظام التسجيل المتقدم مفعل")
        print("🧹 نظام تنظيف الجلسات التلقائي شغال")
        print("👁️  نظام المراقبة الدورية للحسابات شغال")
        print("=" * 50)

        # إعداد Menu Button Commands
        async def post_init(application):
            from telegram import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat
            from telegram.error import BadRequest
            
            try:
                # Commands للمستخدمين العاديين
                user_commands = [
                    BotCommand("start", "Start Bot"),
                    BotCommand("cancel", "Cancel Operation"),
                    BotCommand("language", "Change Language")
                ]
                await application.bot.set_my_commands(user_commands, scope=BotCommandScopeAllPrivateChats())
                
                # Commands للأدمن الرئيسي
                admin_commands = [
                    BotCommand("start", "Start Bot"),
                    BotCommand("cancel", "Cancel Operation"),
                    BotCommand("language", "Change Language"),
                    BotCommand("admin", "Admin Panel")
                ]
                
                if config.ADMIN_ID and config.ADMIN_ID > 0:
                    try:
                        await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(config.ADMIN_ID))
                    except BadRequest as e:
                        logger.warning(f"⚠️ تعذر تعيين الأوامر للأدمن الرئيسي: {e}")
                
                # Commands للأدمنز الثانويين
                admins = database.get_all_admins()
                for admin in admins:
                    admin_id = admin[0]
                    if admin_id != config.ADMIN_ID:
                        try:
                            await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(admin_id))
                        except BadRequest as e:
                            logger.warning(f"⚠️ تعذر تعيين الأوامر للأدمن {admin_id}: {e}")
            except Exception as e:
                logger.error(f"❌ خطأ في تعيين الأوامر: {e}")
        
        app.post_init = post_init
        app.run_polling()

    except Exception as e:
        logger.error(f"❌ خطأ في البوت الرئيسي: {e}")
        logger.error("❌ البوت توقف بسبب خطأ حرج")
        sys.exit(1)

if __name__ == '__main__':
    main()