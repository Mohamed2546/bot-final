import time
import sqlite3
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

class RateLimiter:
    def __init__(self):
        self.init_db()

    def init_db(self):
        """تهيئة جدول Rate Limiting"""
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rate_limits (
                user_id INTEGER,
                action TEXT,
                attempts INTEGER DEFAULT 1,
                last_attempt TEXT,
                created_at TEXT,
                PRIMARY KEY (user_id, action)
            )
        ''')
        conn.commit()
        conn.close()

    def is_limited(self, user_id: int, action: str, max_attempts: int, window_seconds: int) -> bool:
        """التحقق إذا المستخدم تعدى الحد المسموح"""
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        window_start = (datetime.now() - timedelta(seconds=window_seconds)).isoformat()

        # جلب المحاولات الحالية
        cursor.execute('''
            SELECT attempts, last_attempt FROM rate_limits 
            WHERE user_id = ? AND action = ? AND last_attempt > ?
        ''', (user_id, action, window_start))

        result = cursor.fetchone()

        if result:
            attempts, last_attempt = result
            if attempts >= max_attempts:
                conn.close()
                return True

            # تحديث المحاولات
            cursor.execute('''
                UPDATE rate_limits 
                SET attempts = attempts + 1, last_attempt = ?
                WHERE user_id = ? AND action = ?
            ''', (now, user_id, action))
        else:
            # إدخال جديد
            cursor.execute('''
                INSERT OR REPLACE INTO rate_limits 
                (user_id, action, attempts, last_attempt, created_at)
                VALUES (?, ?, 1, ?, ?)
            ''', (user_id, action, now, now))

        conn.commit()
        conn.close()
        return False

    def get_remaining_time(self, user_id: int, action: str, window_seconds: int) -> int:
        """الحصول على الوقت المتبوي حتى إعادة المحاولة"""
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()

        window_start = (datetime.now() - timedelta(seconds=window_seconds)).isoformat()

        cursor.execute('''
            SELECT last_attempt FROM rate_limits 
            WHERE user_id = ? AND action = ? AND last_attempt > ?
        ''', (user_id, action, window_start))

        result = cursor.fetchone()
        conn.close()

        if result:
            last_attempt = datetime.fromisoformat(result[0])
            next_attempt = last_attempt + timedelta(seconds=window_seconds)
            remaining = (next_attempt - datetime.now()).total_seconds()
            return max(0, int(remaining))

        return 0

    def reset_limits(self, user_id: int, action: str = None):
        """إعادة تعيين حدود المستخدم"""
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()

        if action:
            cursor.execute('DELETE FROM rate_limits WHERE user_id = ? AND action = ?', (user_id, action))
        else:
            cursor.execute('DELETE FROM rate_limits WHERE user_id = ?', (user_id,))

        conn.commit()
        conn.close()

# إنشاء instance عالمي
rate_limiter = RateLimiter()

async def rate_limit_check(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, max_attempts: int, window_seconds: int) -> bool:
    """دالة مساعدة للتحقق من Rate Limiting"""
    user_id = update.effective_user.id

    if rate_limiter.is_limited(user_id, action, max_attempts, window_seconds):
        remaining = rate_limiter.get_remaining_time(user_id, action, window_seconds)
        minutes = remaining // 60
        seconds = remaining % 60

        message = f"""
⏰ **تم تجاوز الحد المسموح**

🔒 **السبب:** كثرة الطلبات
⏳ **الوقت المتبقي:** {minutes} دقيقة و {seconds} ثانية

🔄 **حاول مرة أخرى بعد انتهاء الوقت**
        """

        if hasattr(update, 'message'):
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(message, parse_mode='Markdown')

        return True
    return False