import sqlite3
from datetime import datetime, timedelta
import json

def init_db():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    # جدول المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0.0,
            total_earnings REAL DEFAULT 0.0,
            subscribed BOOLEAN DEFAULT FALSE,
            passed_captcha BOOLEAN DEFAULT FALSE,
            completed_onboarding BOOLEAN DEFAULT FALSE,
            created_at TEXT
        )
    ''')

    # جدول الحسابات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            phone_number TEXT,
            session_string TEXT,
            status TEXT DEFAULT 'active',
            price REAL DEFAULT 0.0,
            created_at TEXT
        )
    ''')

    # جدول الدول والأسعار
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS countries (
            country_code TEXT PRIMARY KEY,
            name TEXT,
            price REAL,
            review_time INTEGER,
            is_active BOOLEAN DEFAULT TRUE,
            flag TEXT DEFAULT '',
            capacity INTEGER DEFAULT 0,
            current_count INTEGER DEFAULT 0
        )
    ''')

    # جدول المراجعات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            phone_number TEXT,
            session_string TEXT,
            status TEXT DEFAULT 'pending',
            review_until TEXT,
            price REAL,
            issues TEXT,
            created_at TEXT,
            device_info TEXT
        )
    ''')
    
    # Migration: إضافة عمود device_info للجداول الموجودة
    cursor.execute("PRAGMA table_info(account_reviews)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'device_info' not in columns:
        cursor.execute("ALTER TABLE account_reviews ADD COLUMN device_info TEXT")
        print("✅ تم إضافة عمود device_info إلى account_reviews")
    
    # Migration: إضافة عمود language للمستخدمين
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [column[1] for column in cursor.fetchall()]
    if 'language' not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'ar'")
        print("✅ تم إضافة عمود language إلى users")
    
    # Migration: إضافة عمود proxy_id للحسابات
    cursor.execute("PRAGMA table_info(accounts)")
    accounts_columns = [column[1] for column in cursor.fetchall()]
    if 'proxy_id' not in accounts_columns:
        cursor.execute("ALTER TABLE accounts ADD COLUMN proxy_id INTEGER")
        print("✅ تم إضافة عمود proxy_id إلى accounts")
    
    # Migration: إضافة عمود proxy_id لجدول المراجعات
    cursor.execute("PRAGMA table_info(account_reviews)")
    reviews_columns = [column[1] for column in cursor.fetchall()]
    if 'proxy_id' not in reviews_columns:
        cursor.execute("ALTER TABLE account_reviews ADD COLUMN proxy_id INTEGER")
        print("✅ تم إضافة عمود proxy_id إلى account_reviews")

    # جدول جلسات المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            user_id INTEGER PRIMARY KEY,
            state TEXT,
            session_data TEXT,
            expires_at TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')

    # جدول عمليات التحقق
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verification_sessions (
            user_id INTEGER PRIMARY KEY,
            phone_number TEXT,
            session_string TEXT,
            phone_code_hash TEXT,
            client_data TEXT,
            expires_at TEXT,
            created_at TEXT
        )
    ''')

    # جدول الأدمنز
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            added_by INTEGER,
            added_at TEXT
        )
    ''')

    # جدول البروكسيات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proxies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proxy_address TEXT UNIQUE,
            proxy_type TEXT DEFAULT 'socks5',
            is_connected BOOLEAN DEFAULT TRUE,
            added_by INTEGER,
            added_at TEXT
        )
    ''')

    # جدول السحوبات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            amount REAL,
            wallet_address TEXT,
            wallet_name TEXT,
            status TEXT DEFAULT 'pending',
            admin_id INTEGER,
            rejection_reason TEXT,
            created_at TEXT,
            processed_at TEXT
        )
    ''')

    # جدول المستخدمين المحظورين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            banned_by INTEGER,
            banned_at TEXT,
            reason TEXT
        )
    ''')

    # جدول تاريخ الاستيراد
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS import_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_code TEXT,
            count INTEGER,
            format TEXT,
            admin_id INTEGER,
            admin_username TEXT,
            imported_at TEXT
        )
    ''')

    # جدول إعدادات البوت
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT,
            updated_at TEXT
        )
    ''')

    # جدول أسعار الحسابات الجاهزة
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ready_accounts_prices (
            country_code TEXT PRIMARY KEY,
            price REAL DEFAULT 0.0,
            created_at TEXT,
            updated_at TEXT
        )
    ''')

    # جدول مشتريات الحسابات الجاهزة
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ready_accounts_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            phone_number TEXT,
            country_code TEXT,
            session_string TEXT,
            price REAL,
            balance_before REAL,
            balance_after REAL,
            login_code TEXT,
            purchased_at TEXT,
            code_requested_at TEXT,
            logged_out BOOLEAN DEFAULT FALSE,
            logged_out_at TEXT
        )
    ''')

    # Migration: إضافة عمود sold_as_ready للحسابات المراجعة
    cursor.execute("PRAGMA table_info(account_reviews)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'sold_as_ready' not in columns:
        cursor.execute("ALTER TABLE account_reviews ADD COLUMN sold_as_ready BOOLEAN DEFAULT FALSE")
        print("✅ تم إضافة عمود sold_as_ready إلى account_reviews")
    
    # Migration: إضافة عمود device_info للمشتريات
    cursor.execute("PRAGMA table_info(ready_accounts_purchases)")
    purchase_columns = [column[1] for column in cursor.fetchall()]
    if 'device_info' not in purchase_columns:
        cursor.execute("ALTER TABLE ready_accounts_purchases ADD COLUMN device_info TEXT")
        print("✅ تم إضافة عمود device_info إلى ready_accounts_purchases")

    # جدول سجلات الفحص الدوري للحسابات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitor_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_checked INTEGER DEFAULT 0,
            valid_count INTEGER DEFAULT 0,
            frozen_count INTEGER DEFAULT 0,
            invalid_count INTEGER DEFAULT 0,
            checked_at TEXT
        )
    ''')

    # إضافة الإعدادات الافتراضية
    # استخدام القيمة من config بدلاً من hardcoded value
    import config as cfg
    
    default_settings = {
        'bot_enabled': 'true',
        'accept_accounts': 'true',
        'spam_check': 'true',
        'session_check': 'true',
        'freeze_check': 'true',
        'add_2fa': 'true',
        'channel_username': '@X_TG_Recever',
        'welcome_message': 'مرحباً بك في بوت استلام حسابات التليجرام!',
        'review_message': 'جاري مراجعة الرقم...',
        'menu_message': 'اختر من القائمة:',
        'support_username': '@XxXxDeVxXxX',
        'support_message': 'للتواصل مع الدعم',
        'min_withdrawal': '5',
        'max_withdrawal': '1000',
        '2fa_password': cfg.TWO_FA_PASSWORD,
        'spam_bot_username': '@SpamBot',
        'monitor_enabled': 'true',
        'monitor_interval_hours': '2'
    }
    
    for key, value in default_settings.items():
        cursor.execute('''
            INSERT OR IGNORE INTO bot_settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, ?)
        ''', (key, value, datetime.now().isoformat()))

    # إضافة بيانات الدول الافتراضية
    cursor.execute('''
        INSERT OR IGNORE INTO countries (country_code, name, price, review_time) 
        VALUES 
        (?, ?, ?, ?),
        (?, ?, ?, ?),
        (?, ?, ?, ?)
    ''', (
        '+20', 'مصر', 0.50, 5,
        '+966', 'السعودية', 1.00, 10,
        '+971', 'الإمارات', 1.50, 15
    ))

    conn.commit()
    conn.close()

# دوال جديدة لإدارة الجلسات
def save_user_session(user_id, state, session_data=None, expires_minutes=10):
    """حفظ حالة المستخدم في الداتابيز"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    expires_at = (datetime.now() + timedelta(minutes=expires_minutes)).isoformat()
    data_json = json.dumps(session_data) if session_data else None

    cursor.execute('''
        INSERT OR REPLACE INTO user_sessions 
        (user_id, state, session_data, expires_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, state, data_json, expires_at, datetime.now().isoformat(), datetime.now().isoformat()))

    conn.commit()
    conn.close()

def get_user_session(user_id):
    """جلب حالة المستخدم من الداتابيز"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    # مسح الجلسات المنتهية
    cursor.execute('DELETE FROM user_sessions WHERE expires_at < ?', (datetime.now().isoformat(),))

    cursor.execute('SELECT state, session_data FROM user_sessions WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        session_data = json.loads(result[1]) if result[1] else {}
        return result[0], session_data
    return None, {}

def delete_user_session(user_id):
    """حذف حالة المستخدم"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_sessions WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# دوال جديدة لإدارة جلسات التحقق
def save_verification_session(user_id, phone_number, session_string, phone_code_hash, client_data=None, expires_minutes=5):
    """حفظ جلسة التحقق في الداتابيز"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    expires_at = (datetime.now() + timedelta(minutes=expires_minutes)).isoformat()
    client_json = json.dumps(client_data) if client_data else None

    cursor.execute('''
        INSERT OR REPLACE INTO verification_sessions 
        (user_id, phone_number, session_string, phone_code_hash, client_data, expires_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, phone_number, session_string, phone_code_hash, client_json, expires_at, datetime.now().isoformat()))

    conn.commit()
    conn.close()

def get_verification_session(user_id):
    """جلب جلسة التحقق من الداتابيز"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    # مسح الجلسات المنتهية
    cursor.execute('DELETE FROM verification_sessions WHERE expires_at < ?', (datetime.now().isoformat(),))

    cursor.execute('SELECT * FROM verification_sessions WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()

    return result

def delete_verification_session(user_id):
    """حذف جلسة التحقق"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM verification_sessions WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# الدوال الأصلية
def add_user(user_id, username):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR IGNORE INTO users (user_id, username, created_at) VALUES (?, ?, ?)',
        (user_id, username, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user_subscription(user_id, subscribed):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET subscribed = ? WHERE user_id = ?', (subscribed, user_id))
    conn.commit()
    conn.close()

def update_user_captcha(user_id, passed):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET passed_captcha = ? WHERE user_id = ?', (passed, user_id))
    conn.commit()
    conn.close()

def update_user_onboarding(user_id, completed):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET completed_onboarding = ? WHERE user_id = ?', (completed, user_id))
    conn.commit()
    conn.close()

def add_account(user_id, phone_number, session_string, price=0.0):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO accounts (user_id, phone_number, session_string, price, created_at) VALUES (?, ?, ?, ?, ?)',
        (user_id, phone_number, session_string, price, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_country(country_code):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM countries WHERE country_code = ?', (country_code,))
    country = cursor.fetchone()
    conn.close()
    return country

def get_active_countries():
    """الحصول على الدول النشطة فقط"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM countries WHERE is_active = TRUE ORDER BY country_code')
    countries = cursor.fetchall()
    conn.close()
    return countries

def is_country_active(country_code):
    """التحقق من أن الدولة نشطة"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT is_active FROM countries WHERE country_code = ?', (country_code,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0]

def check_phone_number_status(phone_number):
    """
    التحقق من حالة رقم الهاتف
    Returns: 
        - 'approved': الرقم موافق عليه
        - 'pending': الرقم في المراجعة
        - 'rejected_recent': الرقم مرفوض ولم يمضي 24 ساعة
        - 'rejected_old': الرقم مرفوض ومضى أكثر من 24 ساعة
        - 'available': الرقم متاح للإضافة
    """
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    # التحقق من الأرقام الموافق عليها
    cursor.execute('''
        SELECT id FROM account_reviews 
        WHERE phone_number = ? AND status = 'approved'
    ''', (phone_number,))
    if cursor.fetchone():
        conn.close()
        return 'approved'
    
    # التحقق من الأرقام في المراجعة
    cursor.execute('''
        SELECT id FROM account_reviews 
        WHERE phone_number = ? AND status = 'pending'
    ''', (phone_number,))
    if cursor.fetchone():
        conn.close()
        return 'pending'
    
    # التحقق من الأرقام المرفوضة
    cursor.execute('''
        SELECT created_at FROM account_reviews 
        WHERE phone_number = ? AND status = 'rejected'
        ORDER BY created_at DESC
        LIMIT 1
    ''', (phone_number,))
    rejected = cursor.fetchone()
    
    if rejected:
        rejected_time = datetime.fromisoformat(rejected[0])
        time_diff = datetime.now() - rejected_time
        
        if time_diff.total_seconds() < 86400:  # 24 ساعة = 86400 ثانية
            conn.close()
            return 'rejected_recent'
        else:
            conn.close()
            return 'rejected_old'
    
    conn.close()
    return 'available'

def add_account_review(user_id, phone_number, session_string, price, review_time_minutes, device_info=None):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    review_until = (datetime.now() + timedelta(minutes=review_time_minutes)).isoformat()
    device_info_json = json.dumps(device_info) if device_info else None
    
    # اختيار بروكسي عشوائي للحساب
    proxy = get_random_proxy()
    proxy_id = proxy[0] if proxy else None

    cursor.execute('''
        INSERT INTO account_reviews (user_id, phone_number, session_string, price, review_until, device_info, proxy_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, phone_number, session_string, price, review_until, device_info_json, proxy_id, datetime.now().isoformat()))

    conn.commit()
    conn.close()

def update_user_balance(user_id, amount):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET balance = balance + ?, total_earnings = total_earnings + ?
        WHERE user_id = ?
    ''', (amount, amount, user_id))
    conn.commit()
    conn.close()

# دوال إدارة الإعدادات
def get_setting(key, default=None):
    """الحصول على قيمة إعداد"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else default

def update_setting(key, value):
    """تحديث قيمة إعداد"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO bot_settings (setting_key, setting_value, updated_at)
        VALUES (?, ?, ?)
    ''', (key, value, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# دوال إدارة الأدمنز
def is_admin(user_id):
    """التحقق من صلاحيات الأدمن"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM admins WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def add_admin(user_id, username, added_by):
    """إضافة أدمن"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO admins (user_id, username, added_by, added_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, added_by, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def remove_admin(user_id):
    """حذف أدمن"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_all_admins():
    """الحصول على جميع الأدمنز"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admins')
    admins = cursor.fetchall()
    conn.close()
    return admins

# دوال إدارة البروكسيات
def add_proxy(proxy_address, proxy_type, added_by):
    """إضافة بروكسي"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO proxies (proxy_address, proxy_type, added_by, added_at)
            VALUES (?, ?, ?, ?)
        ''', (proxy_address, proxy_type, added_by, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def remove_proxy(proxy_id):
    """حذف بروكسي"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM proxies WHERE id = ?', (proxy_id,))
    conn.commit()
    conn.close()

def get_all_proxies():
    """الحصول على جميع البروكسيات"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM proxies')
    proxies = cursor.fetchall()
    conn.close()
    return proxies

def get_random_proxy():
    """اختيار بروكسي عشوائي متصل"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM proxies WHERE is_connected = 1 ORDER BY RANDOM() LIMIT 1')
    proxy = cursor.fetchone()
    conn.close()
    return proxy

def get_proxy_by_id(proxy_id):
    """الحصول على بروكسي معين بواسطة ID"""
    if not proxy_id:
        return None
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM proxies WHERE id = ?', (proxy_id,))
    proxy = cursor.fetchone()
    conn.close()
    return proxy

def parse_proxy_address(proxy_address):
    """تحويل عنوان البروكسي إلى dict"""
    try:
        parts = proxy_address.split(':')
        if len(parts) == 4:
            return {
                'proxy_type': 'socks5',
                'addr': parts[0],
                'port': int(parts[1]),
                'username': parts[2],
                'password': parts[3]
            }
        elif len(parts) == 2:
            return {
                'proxy_type': 'socks5',
                'addr': parts[0],
                'port': int(parts[1])
            }
    except:
        pass
    return None

# دوال إدارة الحظر
def ban_user(user_id, username, banned_by, reason):
    """حظر مستخدم"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO banned_users (user_id, username, banned_by, banned_at, reason)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, banned_by, datetime.now().isoformat(), reason))
    conn.commit()
    conn.close()

def unban_user(user_id):
    """فك حظر مستخدم"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM banned_users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def is_banned(user_id):
    """التحقق من الحظر"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM banned_users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def create_withdrawal(user_id, wallet_name, wallet_address, amount):
    """إنشاء طلب سحب جديد"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    # الحصول على username
    cursor.execute('SELECT username FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    username = result[0] if result else None
    
    # إضافة طلب السحب
    cursor.execute('''
        INSERT INTO withdrawals (user_id, username, amount, wallet_address, wallet_name, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, username, amount, wallet_address, wallet_name, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

# ================== دوال الحسابات الجاهزة ==================

def set_ready_account_price(country_code, price):
    """تحديد سعر الحسابات الجاهزة لدولة معينة"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO ready_accounts_prices (country_code, price, created_at, updated_at)
        VALUES (?, ?, ?, ?)
    ''', (country_code, price, datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_ready_account_price(country_code):
    """الحصول على سعر الحسابات الجاهزة لدولة"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT price FROM ready_accounts_prices WHERE country_code = ?', (country_code,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0.0

def get_all_ready_prices():
    """الحصول على جميع أسعار الحسابات الجاهزة"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ready_accounts_prices')
    prices = cursor.fetchall()
    conn.close()
    return prices

def get_available_ready_accounts_by_country(country_code):
    """الحصول على الحسابات الجاهزة المتاحة لدولة معينة"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM account_reviews 
        WHERE status = 'approved' 
        AND phone_number LIKE ?
        AND id NOT IN (
            SELECT ar.id FROM account_reviews ar
            INNER JOIN ready_accounts_purchases p ON ar.phone_number = p.phone_number
            WHERE p.logged_out = FALSE OR p.logged_out IS NULL
        )
        ORDER BY created_at ASC
    ''', (f'{country_code}%',))
    accounts = cursor.fetchall()
    conn.close()
    return accounts

def get_ready_accounts_count_by_country(country_code):
    """الحصول على عدد الحسابات المتاحة لدولة"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM account_reviews 
        WHERE status = 'approved' 
        AND phone_number LIKE ?
        AND id NOT IN (
            SELECT ar.id FROM account_reviews ar
            INNER JOIN ready_accounts_purchases p ON ar.phone_number = p.phone_number
            WHERE p.logged_out = FALSE OR p.logged_out IS NULL
        )
    ''', (f'{country_code}%',))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_countries_with_ready_accounts():
    """الحصول على الدول التي لديها حسابات جاهزة متاحة"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            country_code, 
            name, 
            flag,
            price,
            available_count
        FROM (
            SELECT 
                c.country_code, 
                c.name, 
                c.flag,
                COALESCE(rp.price, 0.0) as price,
                (SELECT COUNT(*) 
                 FROM account_reviews ar 
                 WHERE ar.status = 'approved' 
                 AND ar.phone_number LIKE c.country_code || '%'
                 AND ar.id NOT IN (
                     SELECT ar2.id FROM account_reviews ar2
                     INNER JOIN ready_accounts_purchases p ON ar2.phone_number = p.phone_number
                     WHERE p.logged_out = FALSE OR p.logged_out IS NULL
                 )) as available_count
            FROM countries c
            LEFT JOIN ready_accounts_prices rp ON c.country_code = rp.country_code
            WHERE c.is_active = TRUE
        )
        WHERE available_count > 0
        ORDER BY country_code
    ''')
    countries = cursor.fetchall()
    conn.close()
    return countries

def purchase_ready_account(user_id, username, account_id):
    """شراء حساب جاهز"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    try:
        # بدء transaction صريح
        cursor.execute('BEGIN IMMEDIATE')
        
        # الحصول على معلومات الحساب والتحقق من أنه متاح
        cursor.execute('''
            SELECT phone_number, session_string, device_info 
            FROM account_reviews 
            WHERE id = ? AND status = 'approved'
        ''', (account_id,))
        account = cursor.fetchone()
        
        if not account:
            conn.rollback()
            conn.close()
            return False, "الحساب غير موجود أو غير مقبول"
        
        phone_number = account[0]
        session_string = account[1]
        device_info = account[2]
        
        cursor.execute('''
            SELECT id FROM ready_accounts_purchases 
            WHERE phone_number = ? AND (logged_out = FALSE OR logged_out IS NULL)
        ''', (phone_number,))
        if cursor.fetchone():
            conn.rollback()
            conn.close()
            return False, "الحساب تم بيعه بالفعل"
        
        # استخراج كود الدولة من رقم الهاتف
        country_code = None
        cursor.execute('SELECT country_code FROM countries')
        all_codes = cursor.fetchall()
        
        for code_tuple in all_codes:
            code = code_tuple[0]
            if phone_number.startswith(code):
                country_code = code
                break
        
        if not country_code:
            conn.rollback()
            conn.close()
            return False, "لم يتم التعرف على كود الدولة"
        
        # الحصول على السعر الفعلي من القاعدة
        cursor.execute('SELECT price FROM ready_accounts_prices WHERE country_code = ?', (country_code,))
        price_result = cursor.fetchone()
        
        if not price_result:
            conn.rollback()
            conn.close()
            return False, "السعر غير محدد لهذه الدولة"
        
        actual_price = price_result[0]
        
        # الحصول على رصيد المستخدم
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        user_balance = cursor.fetchone()
        
        if not user_balance or user_balance[0] < actual_price:
            conn.rollback()
            conn.close()
            return False, "رصيد غير كافي"
        
        balance_before = user_balance[0]
        balance_after = balance_before - actual_price
        
        # خصم المبلغ من رصيد المستخدم
        cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?', (balance_after, user_id))
        
        # تسجيل عملية الشراء
        cursor.execute('''
            INSERT INTO ready_accounts_purchases 
            (user_id, username, phone_number, country_code, session_string, price, balance_before, balance_after, purchased_at, device_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, phone_number, country_code, session_string, actual_price, balance_before, balance_after, datetime.now().isoformat(), device_info))
        
        # commit كل العمليات مرة واحدة
        conn.commit()
        purchase_id = cursor.lastrowid
        conn.close()
        return True, purchase_id
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e)

def get_user_purchase(purchase_id):
    """الحصول على تفاصيل شراء"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ready_accounts_purchases WHERE id = ?', (purchase_id,))
    purchase = cursor.fetchone()
    conn.close()
    return purchase

def update_purchase_code(purchase_id, login_code):
    """تحديث كود الدخول للشراء"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE ready_accounts_purchases 
        SET login_code = ?, code_requested_at = ?
        WHERE id = ?
    ''', (login_code, datetime.now().isoformat(), purchase_id))
    conn.commit()
    conn.close()

def logout_purchased_account(purchase_id):
    """تسجيل خروج من حساب مشترى وحذفه من account_reviews"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT phone_number FROM ready_accounts_purchases WHERE id = ?', (purchase_id,))
    result = cursor.fetchone()
    
    if result:
        phone_number = result[0]
        
        cursor.execute('''
            UPDATE ready_accounts_purchases 
            SET logged_out = TRUE, logged_out_at = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), purchase_id))
        
        cursor.execute('''
            DELETE FROM account_reviews 
            WHERE phone_number = ? AND status = 'approved'
        ''', (phone_number,))
        
        cursor.execute('''
            UPDATE accounts 
            SET status = 'logged_out'
            WHERE phone_number = ? AND status = 'approved'
        ''', (phone_number,))
    
    conn.commit()
    conn.close()

def get_user_purchases_count(user_id):
    """الحصول على عدد مشتريات المستخدم"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM ready_accounts_purchases WHERE user_id = ?', (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_total_purchases_stats():
    """الحصول على إحصائيات المبيعات الكلية"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    # عدد الحسابات المباعة
    cursor.execute('SELECT COUNT(*) FROM ready_accounts_purchases')
    total_sold = cursor.fetchone()[0]
    
    # عدد المشترين (مستخدمين فريدين)
    cursor.execute('SELECT COUNT(DISTINCT user_id) FROM ready_accounts_purchases')
    total_buyers = cursor.fetchone()[0]
    
    # إجمالي الرصيد المدفوع
    cursor.execute('SELECT COALESCE(SUM(price), 0.0) FROM ready_accounts_purchases')
    total_revenue = cursor.fetchone()[0]
    
    conn.close()
    return {
        'total_sold': total_sold,
        'total_buyers': total_buyers,
        'total_revenue': total_revenue
    }

def get_all_purchases(limit=5, offset=0):
    """الحصول على جميع المشتريات مع pagination"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM ready_accounts_purchases 
        ORDER BY purchased_at DESC 
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    purchases = cursor.fetchall()
    conn.close()
    return purchases

def search_ready_account_by_phone(phone_number):
    """البحث عن حساب جاهز برقم الهاتف"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    # البحث في الحسابات المراجعة
    cursor.execute('SELECT * FROM account_reviews WHERE phone_number = ?', (phone_number,))
    review = cursor.fetchone()
    
    # البحث في المشتريات
    cursor.execute('SELECT * FROM ready_accounts_purchases WHERE phone_number = ?', (phone_number,))
    purchase = cursor.fetchone()
    
    conn.close()
    return {
        'review': review,
        'purchase': purchase
    }

def get_user_language(user_id):
    """الحصول على لغة المستخدم"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] else 'ar'

def set_user_language(user_id, language):
    """تحديث لغة المستخدم"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
    conn.commit()
    conn.close()

def import_accounts_to_ready(admin_id):
    """استيراد الأرقام المتصلة واستعادة الأرقام المحذوفة من الحسابات الجاهزة"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT phone_number, session_string 
        FROM accounts 
        WHERE status = 'active'
    ''')
    active_accounts = cursor.fetchall()
    
    imported_from_accounts = 0
    already_exists_count = 0
    
    for account in active_accounts:
        phone_number = account[0]
        session_string = account[1]
        
        cursor.execute('''
            SELECT id FROM account_reviews 
            WHERE phone_number = ?
        ''', (phone_number,))
        
        existing = cursor.fetchone()
        
        if not existing:
            cursor.execute('''
                INSERT INTO account_reviews 
                (user_id, phone_number, session_string, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (admin_id, phone_number, session_string, 'approved', datetime.now().isoformat()))
            imported_from_accounts += 1
        else:
            already_exists_count += 1
    
    cursor.execute('''
        SELECT ar.phone_number
        FROM account_reviews ar
        INNER JOIN ready_accounts_purchases p ON ar.phone_number = p.phone_number
        WHERE ar.status = 'approved' 
        AND (p.logged_out = FALSE OR p.logged_out IS NULL)
    ''')
    locked_numbers = cursor.fetchall()
    
    restored_count = 0
    for row in locked_numbers:
        phone_number = row[0]
        cursor.execute('''
            UPDATE ready_accounts_purchases 
            SET logged_out = TRUE, logged_out_at = ?
            WHERE phone_number = ? AND (logged_out = FALSE OR logged_out IS NULL)
        ''', (datetime.now().isoformat(), phone_number))
        restored_count += 1
    
    conn.commit()
    conn.close()
    
    return {
        'imported': imported_from_accounts,
        'restored': restored_count,
        'already_exists': already_exists_count,
        'total_scanned': len(active_accounts) + len(locked_numbers)
    }

# ================== دوال سجلات المراقبة الدورية ==================

def get_monitor_logs(limit=10):
    """الحصول على آخر سجلات الفحص الدوري"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM monitor_logs 
        ORDER BY checked_at DESC 
        LIMIT ?
    ''', (limit,))
    logs = cursor.fetchall()
    conn.close()
    return logs

def get_monitor_stats():
    """الحصول على إحصائيات المراقبة"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM monitor_logs')
    total_checks = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(frozen_count) FROM monitor_logs')
    total_frozen = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT SUM(invalid_count) FROM monitor_logs')
    total_invalid = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT checked_at FROM monitor_logs ORDER BY checked_at DESC LIMIT 1')
    last_check = cursor.fetchone()
    last_check_time = last_check[0] if last_check else None
    
    conn.close()
    
    return {
        'total_checks': total_checks,
        'total_frozen_found': total_frozen,
        'total_invalid_found': total_invalid,
        'last_check_time': last_check_time
    }