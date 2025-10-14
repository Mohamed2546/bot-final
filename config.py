import os

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0') or '0')

# إعدادات التليجرام API
API_ID = os.getenv('API_ID', '123456')
API_HASH = os.getenv('API_HASH', 'abc123')

# كلمة مرور 2FA (يفضل وضعها في environment variable)
TWO_FA_PASSWORD = os.getenv('TWO_FA_PASSWORD', 'SecureBotPassword123!')

# Telethon API credentials للحسابات الجاهزة (من environment variables)
TELETHON_API_ID = int(os.getenv('TELETHON_API_ID') or os.getenv('API_ID', '27211139'))
TELETHON_API_HASH = os.getenv('TELETHON_API_HASH') or os.getenv('API_HASH', 'a06899fd158d49479ccebf1e7161989c')

# إعدادات القناة
CHANNEL_USERNAME = "@X_TG_Recever"
CHANNEL_URL = f"https://t.me/{CHANNEL_USERNAME[1:]}"

# إعدادات الكابتشا
CAPTCHA_QUESTIONS = [
    {"question": "🎯 5 + 3 = ?", "answer": "8"},
    {"question": "🎯 10 - 4 = ?", "answer": "6"}, 
    {"question": "🎯 2 × 3 = ?", "answer": "6"}
]

# 🆕 إعدادات Rate Limiting
RATE_LIMITS = {
    'start': 3,  # 3 محاولات في الدقيقة
    'phone_input': 2,  # 2 رقم في الدقيقة
    'verification': 1,  # 1 عملية تحقق في الدقيقتين
}

# 🆕 إعدادات المراجعة
REVIEW_SETTINGS = {
    'max_retries': 3,
    'retry_delay': 30,  # ثانية
    'circuit_breaker_threshold': 5,  # 5 أخطاء متتالية
    'circuit_breaker_timeout': 300,  # 5 دقائق
}

# 🆕 إعدادات التسجيل
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': 'bot.log'
}