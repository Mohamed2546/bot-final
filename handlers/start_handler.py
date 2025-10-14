from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telethon import TelegramClient
from telethon.sessions import StringSession
import database
from config import CHANNEL_URL, CHANNEL_USERNAME, CAPTCHA_QUESTIONS, API_ID, API_HASH, RATE_LIMITS
from rate_limiter import rate_limit_check
from translations import get_text
import random
import sqlite3
from datetime import datetime
import asyncio
import json

# قائمة الأجهزة والإصدارات
ANDROID_DEVICES = ["Samsung Galaxy S24 Ultra", "Google Pixel 8 Pro", "Xiaomi 14 Pro", "OnePlus 12"]
IPHONE_DEVICES = ["iPhone 15 Pro Max", "iPhone 14 Pro", "iPhone 13 Pro", "iPhone 12 Pro"]
ANDROID_VERSIONS = ["Android 14", "Android 13", "Android 12"]
IOS_VERSIONS = ["iOS 17.2", "iOS 17.1", "iOS 16.6"]
VERSION_NUMBERS = ["10.5.2", "10.4.1", "10.3.0", "10.2.3"]

# أعلام الدول
COUNTRY_FLAGS = {
    # دول عربية
    '+20': '🇪🇬',    # مصر
    '+966': '🇸🇦',   # السعودية
    '+971': '🇦🇪',   # الإمارات
    '+965': '🇰🇼',   # الكويت
    '+968': '🇴🇲',   # عمان
    '+974': '🇶🇦',   # قطر
    '+973': '🇧🇭',   # البحرين
    '+964': '🇮🇶',   # العراق
    '+962': '🇯🇴',   # الأردن
    '+963': '🇸🇾',   # سوريا
    '+961': '🇱🇧',   # لبنان
    '+970': '🇵🇸',   # فلسطين
    '+212': '🇲🇦',   # المغرب
    '+213': '🇩🇿',   # الجزائر
    '+216': '🇹🇳',   # تونس
    '+218': '🇱🇾',   # ليبيا
    '+249': '🇸🇩',   # السودان
    '+967': '🇾🇪',   # اليمن
    # دول آسيوية
    '+95': '🇲🇲',    # ميانمار
    '+92': '🇵🇰',    # باكستان
    '+91': '🇮🇳',    # الهند
    '+880': '🇧🇩',   # بنجلاديش
    '+63': '🇵🇭',    # الفلبين
    '+84': '🇻🇳',    # فيتنام
    '+66': '🇹🇭',    # تايلاند
    '+60': '🇲🇾',    # ماليزيا
    '+62': '🇮🇩',    # إندونيسيا
    '+86': '🇨🇳',    # الصين
    '+82': '🇰🇷',    # كوريا الجنوبية
    '+81': '🇯🇵',    # اليابان
    '+90': '🇹🇷',    # تركيا
    '+98': '🇮🇷',    # إيران
    '+93': '🇦🇫',    # أفغانستان
    '+7': '🇷🇺',     # روسيا
    # دول أمريكا اللاتينية
    '+591': '🇧🇴',   # بوليفيا
    '+593': '🇪🇨',   # الإكوادور
    '+51': '🇵🇪',    # بيرو
    '+56': '🇨🇱',    # تشيلي
    '+55': '🇧🇷',    # البرازيل
    '+54': '🇦🇷',    # الأرجنتين
    '+57': '🇨🇴',    # كولومبيا
    '+58': '🇻🇪',    # فنزويلا
    '+52': '🇲🇽',    # المكسيك
    # دول أفريقيا
    '+234': '🇳🇬',   # نيجيريا
    '+254': '🇰🇪',   # كينيا
    '+233': '🇬🇭',   # غانا
    '+27': '🇿🇦',    # جنوب أفريقيا
    '+255': '🇹🇿',   # تنزانيا
    '+256': '🇺🇬',   # أوغندا
    '+251': '🇪🇹',   # إثيوبيا
    '+225': '🇨🇮',   # ساحل العاج
    '+237': '🇨🇲',   # الكاميرون
    # دول أوروبية
    '+44': '🇬🇧',    # المملكة المتحدة
    '+49': '🇩🇪',    # ألمانيا
    '+33': '🇫🇷',    # فرنسا
    '+39': '🇮🇹',    # إيطاليا
    '+34': '🇪🇸',    # إسبانيا
    '+48': '🇵🇱',    # بولندا
    '+31': '🇳🇱',    # هولندا
    '+32': '🇧🇪',    # بلجيكا
    '+41': '🇨🇭',    # سويسرا
    '+43': '🇦🇹',    # النمسا
    '+30': '🇬🇷',    # اليونان
    '+351': '🇵🇹',   # البرتغال
    '+46': '🇸🇪',    # السويد
    '+47': '🇳🇴',    # النرويج
    '+45': '🇩🇰',    # الدنمارك
    '+358': '🇫🇮',   # فنلندا
    # دول أمريكا الشمالية
    '+1': '🇺🇸',     # الولايات المتحدة
    # دول أخرى
    '+61': '🇦🇺',    # أستراليا
    '+64': '🇳🇿',    # نيوزيلندا
    '+972': '🇮🇱',   # إسرائيل
    '+994': '🇦🇿',   # أذربيجان
    '+374': '🇦🇲',   # أرمينيا
    '+995': '🇬🇪',   # جورجيا
    '+998': '🇺🇿',   # أوزبكستان
    '+996': '🇰🇬',   # قيرغيزستان
    '+992': '🇹🇯',   # طاجيكستان
    '+993': '🇹🇲',   # تركمانستان
    '+7840': '🇦🇿',  # أذربيجان
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء البوت مع Rate Limiting"""
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    # التحقق من الحظر
    if database.is_banned(user_id):
        await update.message.reply_text(
            "⛔ <b>أنت محظور من استخدام البوت</b>\n\nللتواصل مع الإدارة راسل الدعم.",
            parse_mode='HTML'
        )
        return
    
    # التحقق من تشغيل البوت
    bot_enabled = database.get_setting('bot_enabled', 'true') == 'true'
    if not bot_enabled:
        await update.message.reply_text(get_text('bot_maintenance', lang))
        return
    
    # Rate limiting للبداية
    if await rate_limit_check(update, context, 'start', RATE_LIMITS['start'], 60):
        return

    user_id = update.effective_user.id
    username = update.effective_user.username

    database.add_user(user_id, username)

    user_data = database.get_user(user_id)
    if user_data and user_data[4]:  # subscribed
        await show_main_menu(update, context)
        return

    await show_welcome_message(update)

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء العملية الحالية"""
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    await update.message.reply_text(get_text('operation_cancelled', lang))

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغيير اللغة"""
    user_id = update.effective_user.id
    current_lang = database.get_user_language(user_id)
    
    keyboard = [
        [
            InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = get_text('select_language', current_lang)
    
    await update.message.reply_text(text, reply_markup=reply_markup)

async def show_welcome_message(update: Update):
    """عرض رسالة الترحيب"""
    # جلب رسالة الترحيب من الإعدادات
    welcome_msg = database.get_setting('welcome_message', 'مرحباً بك في بوت استلام حسابات التليجرام!')
    channel_username = database.get_setting('channel_username', CHANNEL_USERNAME)
    
    welcome_text = f"""
✨ **{welcome_msg}** ✨

📢 **قناتنا الرسمية:**
{channel_username}

🌟 **مميزات البوت:**
✅ استلام حسابات تليجرام بجودة عالية
💰 أرباح يومية مضمونة  
🎁 عروض حصرية للمشتركين

👉 **للاستفادة من خدماتنا، يرجى الاشتراك في قناتنا أولاً:**
    """

    keyboard = [
        [InlineKeyboardButton("📢 الإنضمام للقناة", url=CHANNEL_URL)],
        [InlineKeyboardButton("🚀 بدء الاستخدام", callback_data="check_subscription")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التحقق من اشتراك المستخدم في القناة"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        is_subscribed = member.status in ['member', 'administrator', 'creator']
    except:
        is_subscribed = False

    if is_subscribed:
        database.update_user_subscription(user_id, True)
        await send_captcha(query, user_id)
    else:
        error_text = f"""
❌ **لم يتم التحقق من اشتراكك!**

🔗 **رابط القناة:**
{CHANNEL_USERNAME}

📢 **يجب الاشتراك في القناة أولاً ثم الضغط على زر التحقق**
        """

        keyboard = [
            [InlineKeyboardButton("📢 الإنضمام للقناة", url=CHANNEL_URL)],
            [InlineKeyboardButton("🔄 تحقق مرة أخرى", callback_data="check_subscription")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='Markdown')

async def send_captcha(query, user_id):
    """إرسال كابتشا للمستخدم"""
    captcha = random.choice(CAPTCHA_QUESTIONS)

    # حفظ حالة الكابتشا في الداتابيز
    database.save_user_session(user_id, "captcha", {"answer": captcha["answer"]})

    captcha_text = f"""
🔐 **تحقق أمني**

{captcha['question']}

📝 **أرسل الإجابة الآن:**
    """

    await query.edit_message_text(captcha_text, parse_mode='Markdown')

async def verify_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التحقق من إجابة الكابتشا"""
    user_id = update.effective_user.id
    user_answer = update.message.text.strip()

    # جلب حالة المستخدم من الداتابيز
    state, session_data = database.get_user_session(user_id)

    if state == "captcha" and "answer" in session_data:
        correct_answer = session_data["answer"]

        if user_answer == correct_answer:
            database.update_user_captcha(user_id, True)
            database.update_user_onboarding(user_id, True)
            database.delete_user_session(user_id)  # مسح الجلسة

            # عرض القائمة الرئيسية
            await show_main_menu(update, context)
        else:
            await update.message.reply_text("❌ **إجابة خاطئة! حاول مرة أخرى:**")
    else:
        await update.message.reply_text("🔁 **اكتب /start لبدء من جديد**")

async def handle_country_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اختيار الدولة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    country_code = query.data.replace("select_country_", "")
    
    # حفظ الدولة المختارة في الجلسة
    database.save_user_session(user_id, "waiting_for_phone", {"country_code": country_code})
    
    # الحصول على معلومات الدولة
    country = database.get_country(country_code)
    if not country:
        await query.edit_message_text("❌ **حدث خطأ! الدولة غير موجودة**")
        return
    
    country_name = country[1]
    flag = country[6] if country[6] else ''
    price = country[2]
    
    # رسالة طلب الرقم
    phone_request_text = f"""
✅ **تم اختيار الدولة:**
{flag} **{country_name}**

💰 **السعر:** ${price:.2f}

📱 **الآن أرسل رقم هاتفك من هذه الدولة بالصيغة الدولية:**

مثال: `{country_code}123456789`

🔢 **يجب أن يبدأ الرقم ب {country_code}**
    """
    
    keyboard = [[InlineKeyboardButton("🔙 تغيير الدولة", callback_data="change_country")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(phone_request_text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_change_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إعادة عرض قائمة الدول"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # حذف الجلسة السابقة
    database.delete_user_session(user_id)
    
    # جلب الدول المتاحة
    active_countries = database.get_active_countries()
    
    if not active_countries:
        await query.edit_message_text("""
⚠️ **عذراً، لا توجد دول متاحة حالياً**

📞 **يرجى المحاولة لاحقاً**
        """, parse_mode='Markdown')
        return
    
    # إنشاء أزرار الدول
    keyboard = []
    for country in active_countries:
        country_code = country[0]
        country_name = country[1]
        flag = country[6] if country[6] else ''
        price = country[2]
        
        button_text = f"{flag} {country_name} - ${price:.2f}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"select_country_{country_code}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("""
📱 **اختر الدولة التي تريد إضافة رقم منها:**

🔒 **سيتم التعامل مع رقمك بخصوصية تامة**
    """, reply_markup=reply_markup, parse_mode='Markdown')

async def cancel_verification_auto(user_id):
    """إلغاء تلقائي بعد 5 دقائق"""
    await asyncio.sleep(300)

    # التحقق إذا الجلسة لسة موجودة
    verification_data = database.get_verification_session(user_id)
    if verification_data:
        try:
            # تنظيف الجلسة
            database.delete_verification_session(user_id)
        except:
            pass

async def handle_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إدخال رقم الهاتف"""
    # التحقق من تشغيل البوت
    bot_enabled = database.get_setting('bot_enabled', 'true') == 'true'
    if not bot_enabled:
        await update.message.reply_text("⚠️ **البوت متوقف حالياً للصيانة!**\n\nسيتم استئناف الخدمة قريباً.")
        return
    
    # التحقق من قبول الحسابات
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    accept_accounts = database.get_setting('accept_accounts', 'true') == 'true'
    if not accept_accounts:
        await update.message.reply_text(get_text('not_accepting_accounts', lang))
        return
    
    # Rate limiting لإدخال الأرقام
    if await rate_limit_check(update, context, 'phone_input', RATE_LIMITS['phone_input'], 60):
        return

    phone_number = update.message.text.strip()

    # تحقق من صحة الرقم
    if not phone_number.startswith('+') or len(phone_number) < 10:
        await update.message.reply_text("""
❌ **رقم غير صحيح!**

📱 **أرسل رقم هاتفك بالصيغة الدولية:**
مثال: `+20123456789`

🔢 **يجب أن يبدأ الرقم ب + ويحتوي على الأقل 10 أرقام**
        """, parse_mode='Markdown')
        return
    
    # التحقق من حالة الرقم (منع التكرار)
    phone_status = database.check_phone_number_status(phone_number)
    
    if phone_status == 'approved':
        await update.message.reply_text("""
❌ **هذا الرقم تم قبوله بالفعل!**

⚠️ **لا يمكن إضافة رقم تم الموافقة عليه مسبقاً**

📱 **يرجى إرسال رقم آخر**
        """, parse_mode='Markdown')
        return
    elif phone_status == 'pending':
        await update.message.reply_text("""
❌ **هذا الرقم قيد المراجعة حالياً!**

⏳ **الرقم ينتظر الموافقة من الإدارة**

📱 **يرجى إرسال رقم آخر**
        """, parse_mode='Markdown')
        return
    elif phone_status == 'rejected_recent':
        await update.message.reply_text("""
❌ **هذا الرقم تم رفضه مؤخراً!**

⏰ **يجب الانتظار 24 ساعة قبل إعادة إضافة رقم مرفوض**

📱 **يرجى إرسال رقم آخر أو الانتظار حتى انتهاء المدة**
        """, parse_mode='Markdown')
        return
    
    # التحقق التلقائي من أن الرقم من دولة متاحة
    country_code = None
    active_countries = database.get_active_countries()
    
    for country in active_countries:
        code = country[0]
        if phone_number.startswith(code):
            country_code = code
            break
    
    if not country_code:
        # الرقم ليس من دولة متاحة
        available_countries_text = "\n".join([f"• {c[6]} {c[1]} ({c[0]})" for c in active_countries if c[6]])
        
        await update.message.reply_text(f"""
❌ **هذا الرقم من دولة غير متاحة!**

🌍 **الدول المتاحة حالياً:**
{available_countries_text}

📱 **يرجى إرسال رقم من إحدى الدول المتاحة**
        """, parse_mode='Markdown')
        return

    # Rate limiting للتحقق
    if await rate_limit_check(update, context, 'verification', RATE_LIMITS['verification'], 120):
        return

    # تنظيف أي عملية سابقة
    old_verification = database.get_verification_session(user_id)
    if old_verification:
        database.delete_verification_session(user_id)

    wait_msg = await update.message.reply_text(get_text('sending_verification', lang))

    try:
        # اختيار عشوائي للإعدادات
        use_android = random.choice([True, False])

        if use_android:
            device_model = random.choice(ANDROID_DEVICES)
            system_version = random.choice(ANDROID_VERSIONS)
            app_version = f"Android {random.choice(VERSION_NUMBERS)}"
        else:
            device_model = random.choice(IPHONE_DEVICES)
            system_version = random.choice(IOS_VERSIONS)
            app_version = f"iOS {random.choice(VERSION_NUMBERS)}"

        # اختيار بروكسي عشوائي للحساب
        proxy_data = database.get_random_proxy()
        proxy_config = None
        if proxy_data:
            proxy_config = database.parse_proxy_address(proxy_data[1])  # proxy_data[1] هو proxy_address
        
        # إنشاء جلسة تليجرام مع البروكسي
        client = TelegramClient(
            StringSession(),
            API_ID,
            API_HASH,
            device_model=device_model,
            system_version=system_version,
            app_version=app_version,
            lang_code="ar",
            system_lang_code="ar",
            proxy=proxy_config
        )
        await client.connect()

        # إرسال كود التحقق
        sent_code = await client.send_code_request(phone_number)

        # حفظ بيانات التحقق في الداتابيز
        client_data = {
            "device_model": device_model,
            "system_version": system_version,
            "app_version": app_version,
            "proxy_id": proxy_data[0] if proxy_data else None  # حفظ البروكسي ID
        }

        database.save_verification_session(
            user_id=user_id,
            phone_number=phone_number,
            session_string=client.session.save(),
            phone_code_hash=sent_code.phone_code_hash,
            client_data=client_data
        )

        # بدء المؤقت
        timer_task = asyncio.create_task(cancel_verification_auto(user_id))

        # زر الإلغاء
        keyboard = [[InlineKeyboardButton(get_text('cancel_operation', lang), callback_data="cancel_verification")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message_text = f"""{get_text('code_sent_to', lang).format(phone=phone_number)}

{get_text('enter_code_now', lang)}
{get_text('five_minutes_limit', lang)}

{get_text('no_personal_data', lang)}"""

        await wait_msg.edit_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    except Exception as e:
        error_message = str(e).lower()

        if "phone number" in error_message and "invalid" in error_message:
            error_text = get_text('phone_invalid', lang)
        elif "flood" in error_message:
            error_text = get_text('flood_wait', lang)
        elif "phone number banned" in error_message:
            error_text = get_text('phone_banned', lang)
        else:
            error_text = get_text('send_error', lang).format(error=str(e))

        await wait_msg.edit_text(error_text)
        database.delete_verification_session(user_id)

async def cancel_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء عملية التحقق"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = database.get_user_language(user_id)

    # تنظيف الجلسة من الداتابيز
    database.delete_verification_session(user_id)

    message_text = f"""{get_text('operation_cancelled_msg', lang)}

{get_text('restart_command', lang)}"""

    await query.edit_message_text(
        message_text,
        parse_mode='Markdown'
    )

async def handle_verification_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة كود التحقق"""
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    code = update.message.text.strip()

    # جلب جلسة التحقق من الداتابيز
    verification_data = database.get_verification_session(user_id)
    if not verification_data:
        await update.message.reply_text(get_text('timeout_error', lang))
        return

    try:
        phone = verification_data[1]
        session_string = verification_data[2]
        phone_code_hash = verification_data[3]
        client_data = json.loads(verification_data[4]) if verification_data[4] else {}
        
        # استرجاع البروكسي المستخدم في إرسال الكود
        proxy_id = client_data.get("proxy_id")
        proxy_config = None
        if proxy_id:
            proxy_data = database.get_proxy_by_id(proxy_id)
            if proxy_data:
                proxy_config = database.parse_proxy_address(proxy_data[1])

        # إعادة إنشاء العميل بنفس الإعدادات ونفس البروكسي
        client = TelegramClient(
            StringSession(session_string),
            API_ID,
            API_HASH,
            device_model=client_data.get("device_model", "Samsung Galaxy S24 Ultra"),
            system_version=client_data.get("system_version", "Android 14"),
            app_version=client_data.get("app_version", "Telegram Android 10.5.2"),
            lang_code="ar",
            system_lang_code="ar",
            proxy=proxy_config
        )

        await client.connect()

        # تسجيل الدخول
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)

        # الحصول على الجلسة النهائية بنفس الإعدادات
        final_session_string = client.session.save()

        # الحصول على بيانات الدولة
        country_code = phone[:3]
        country = database.get_country(country_code)

        if country:
            price = country[2]
            review_time = country[3]
            country_name = country[1]
        else:
            price = 0.50
            review_time = 5
            country_name = "غير معروفة"

        # إضافة للمراجعة مع معلومات الجهاز
        database.add_account_review(user_id, phone, final_session_string, price, review_time, client_data)

        # تنظيف الجلسة
        database.delete_verification_session(user_id)
        await client.disconnect()

        # جلب رسالة المراجعة من الإعدادات
        review_msg = database.get_setting('review_message', 'جاري مراجعة الرقم...')
        
        # إرسال إشعار للمستخدم
        await update.message.reply_text(
            f"✅ **تم استلام الرقم بنجاح!**\n\n"
            f"📱 **الرقم:** `{phone}`\n"
            f"🌍 **الدولة:** {country_name}\n"
            f"💰 **السعر:** ${price}\n"
            f"⏰ **وقت المراجعة:** {review_time} دقيقة\n\n"
            f"🔍 **{review_msg}**\n"
            f"📨 **سيصلك إشعار بنتيجة المراجعة**",
            parse_mode='Markdown'
        )

    except Exception as e:
        error_message = str(e).lower()
        if "code" in error_message and "invalid" in error_message:
            await update.message.reply_text(get_text('verification_code_invalid', lang))
        else:
            await update.message.reply_text(get_text('error_occurred', lang).format(error=str(e)))
            database.delete_verification_session(user_id)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة جميع الرسائل النصية"""
    user_id = update.effective_user.id
    
    # التحقق من الحظر
    if database.is_banned(user_id):
        lang = database.get_user_language(user_id)
        await update.message.reply_text(
            "⛔ <b>أنت محظور من استخدام البوت</b>\n\nللتواصل مع الإدارة راسل الدعم.",
            parse_mode='HTML'
        )
        return
    
    lang = database.get_user_language(user_id)
    text = update.message.text.strip()

    # معالجة عنوان المحفظة
    if context.user_data.get('waiting_for_wallet_address'):
        context.user_data['wallet_address'] = text
        context.user_data['waiting_for_wallet_address'] = False
        
        user_data = database.get_user(user_id)
        balance = user_data[2] if user_data else 0.0
        wallet_name = context.user_data.get('withdraw_name', '')
        min_amount = context.user_data.get('withdraw_min', 0)
        
        if lang == 'ar':
            choose_amount = 'اختر المبلغ'
            wallet_label = 'المحفظة'
            address_label = 'العنوان'
            choose_method = 'اختر طريقة السحب'
            withdraw_full_btn = 'سحب المبلغ كامل'
            custom_amount_btn = 'تحديد مبلغ يدوياً'
        else:
            choose_amount = 'Choose Amount'
            wallet_label = 'Wallet'
            address_label = 'Address'
            choose_method = 'Choose withdrawal method'
            withdraw_full_btn = 'Withdraw Full Amount'
            custom_amount_btn = 'Custom Amount'
        
        amount_text = f"""╔═══════════════════════╗
║   <b>💰 {choose_amount}</b>   ║
╚═══════════════════════╝

💵 <b>{get_text('your_balance', lang)}:</b> {balance}$
📍 <b>{wallet_label}:</b> {wallet_name}
📝 <b>{address_label}:</b> <code>{text}</code>

⚠️ <b>{get_text('min_withdraw', lang)}:</b> {min_amount}$

💳 <b>{choose_method}:</b>"""
        
        keyboard = [
            [InlineKeyboardButton(f"💰 {withdraw_full_btn}", callback_data="withdraw_full")],
            [InlineKeyboardButton(f"📝 {custom_amount_btn}", callback_data="withdraw_custom")],
            [InlineKeyboardButton(get_text('cancel', lang), callback_data="withdraw")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(amount_text, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    # معالجة المبلغ المخصص
    if context.user_data.get('waiting_for_amount'):
        try:
            amount = float(text)
            user_data = database.get_user(user_id)
            balance = user_data[2] if user_data else 0.0
            min_amount = context.user_data.get('withdraw_min', 0)
            
            if amount < min_amount:
                if lang == 'ar':
                    msg = f"⚠️ المبلغ أقل من الحد الأدنى ({min_amount}$)"
                else:
                    msg = f"⚠️ Amount is less than minimum ({min_amount}$)"
                await update.message.reply_text(msg)
                return
            
            if amount > balance:
                if lang == 'ar':
                    msg = f"⚠️ المبلغ أكبر من رصيدك ({balance}$)"
                else:
                    msg = f"⚠️ Amount is greater than your balance ({balance}$)"
                await update.message.reply_text(msg)
                return
            
            context.user_data['withdraw_amount'] = amount
            context.user_data['waiting_for_amount'] = False
            
            # إتمام طلب السحب
            await process_withdrawal(update, context)
            return
            
        except ValueError:
            if lang == 'ar':
                msg = "⚠️ أدخل مبلغاً صحيحاً (رقم)"
            else:
                msg = "⚠️ Enter a valid amount (number)"
            await update.message.reply_text(msg)
            return

    # التحقق من حالة المستخدم من الداتابيز
    state, session_data = database.get_user_session(user_id)

    if state == "captcha":
        await verify_captcha(update, context)
    elif database.get_verification_session(user_id):
        await handle_verification_code(update, context)
    else:
        if text.startswith('+') and any(char.isdigit() for char in text[1:]):
            await handle_phone_number(update, context)
        else:
            if lang == 'ar':
                msg = """
❌ **أرسل رقم الهاتف أولاً**

📱 **صيغة الرقم:** 
`+20123456789`
`+966512345678`

🔁 **أو اكتب /start للبدء من جديد**
                """
            else:
                msg = """
❌ **Send phone number first**

📱 **Number format:** 
`+20123456789`
`+966512345678`

🔁 **Or type /start to begin again**
                """
            await update.message.reply_text(msg, parse_mode='Markdown')

async def handle_language_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة تغيير اللغة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = query.data.split('_')[1]  # lang_ar أو lang_en
    
    database.set_user_language(user_id, lang)
    
    from translations import get_text
    
    success_msg = get_text('success', lang) + '! ✅\n'
    if lang == 'ar':
        success_msg += 'تم تغيير اللغة إلى العربية'
    else:
        success_msg += 'Language changed to English'
    
    await query.edit_message_text(success_msg)
    await asyncio.sleep(1)
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض القائمة الرئيسية"""
    # التعامل مع Message أو CallbackQuery
    if hasattr(update, 'callback_query') and update.callback_query:
        user_id = update.callback_query.from_user.id
        query = update.callback_query
    else:
        user_id = update.effective_user.id
        query = None
    
    from translations import get_text
    lang = database.get_user_language(user_id)
    
    user_data = database.get_user(user_id)

    if user_data:
        balance = user_data[2]  # الرصيد
        total_earnings = user_data[3]  # إجمالي الأرباح
    else:
        balance = 0.0
        total_earnings = 0.0

    # جلب رسالة القائمة من الإعدادات
    menu_msg = get_text('welcome_message', lang)
    
    menu_text = f"""
🎊 **{get_text('welcome_back', lang)}**

💰 **{get_text('current_balance', lang)}:** ${balance}
📈 **{get_text('total_earnings', lang)}:** ${total_earnings}

📊 **{menu_msg}**
    """

    # إنشاء Inline Keyboard للأزرار الرئيسية
    # قائمة الأزرار مع callback_data
    buttons_config = [
        ('my_balance', 'balance'),
        ('add_account', 'add_account'),
        ('buy_ready_accounts', 'show_ready_accounts'),
        ('available_countries', 'countries'),
        ('withdraw', 'withdraw'),
        ('recharge_balance', 'show_balance_recharge'),
        ('support', 'support'),
        ('channel', 'channel')
    ]
    
    # بناء الأزرار بناءً على الإعدادات
    enabled_buttons = []
    for button_key, callback in buttons_config:
        # التحقق من حالة الزرار
        is_enabled = database.get_setting(f'button_{button_key}_enabled', 'true') == 'true'
        if is_enabled:
            # الحصول على الاسم المخصص أو الافتراضي
            button_text = database.get_setting(f'button_{button_key}_{lang}', get_text(button_key, lang))
            enabled_buttons.append((button_text, callback))
    
    # ترتيب الأزرار في صفوف (2 زرار في الصف)
    keyboard = []
    temp_row = []
    for text, callback in enabled_buttons:
        temp_row.append(InlineKeyboardButton(text, callback_data=callback))
        if len(temp_row) == 2:
            keyboard.append(temp_row)
            temp_row = []
    
    # إضافة الصف الأخير إذا كان فيه زرار واحد
    if temp_row:
        keyboard.append(temp_row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif hasattr(update, 'message'):
        await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_menu_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة actions القائمة"""
    query = update.callback_query
    await query.answer()

    action = query.data
    user_id = query.from_user.id

    if action == "balance":
        lang = database.get_user_language(user_id)
        user_data = database.get_user(user_id)
        balance = user_data[2] if user_data else 0.0
        
        # جلب إحصائيات الحسابات
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        
        # عدد الحسابات الكلي
        cursor.execute('SELECT COUNT(*) FROM accounts WHERE user_id = ?', (user_id,))
        accounts_count = cursor.fetchone()[0]
        
        # عدد الحسابات المقبولة
        cursor.execute('SELECT COUNT(*) FROM account_reviews WHERE user_id = ? AND status = ?', (user_id, 'approved'))
        approved_count = cursor.fetchone()[0]
        
        # عدد الحسابات المرفوضة
        cursor.execute('SELECT COUNT(*) FROM account_reviews WHERE user_id = ? AND status = ?', (user_id, 'rejected'))
        rejected_count = cursor.fetchone()[0]
        
        conn.close()
        
        # الحصول على التاريخ والوقت الحالي
        from datetime import datetime
        now = datetime.now()
        report_date = now.strftime("%Y/%m/%d - %H:%M:%S")
        
        # إنشاء الرسالة بتصميم جميل
        balance_text = f"""╔══════════════════════════╗
║   <b>📊 {get_text('user_info', lang)}</b>   ║
╚══════════════════════════╝

👤 <b>{get_text('user_id', lang)}:</b> <code>{user_id}</code>

┏━━━━━━━━━━━━━━━━━━━━━━━┓
┃   <b>💰 {get_text('balance', lang)}</b>
┃   💵 {balance}$
┗━━━━━━━━━━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━━━━━━━━┓
┃   <b>📱 {get_text('account_stats', lang)}</b>
┃   
┃   🏦 {get_text('total_accounts', lang)}: {accounts_count}
┃   ✅ {get_text('approved_accounts', lang)}: {approved_count}
┃   ❌ {get_text('rejected_accounts', lang)}: {rejected_count}
┗━━━━━━━━━━━━━━━━━━━━━━━┛

⏰ <b>{get_text('report_date', lang)}:</b> {report_date}"""
        
        # إنشاء زرار الرجوع
        keyboard = [[InlineKeyboardButton(get_text('back', lang), callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(balance_text, reply_markup=reply_markup, parse_mode='HTML')

    elif action == "add_account":
        lang = database.get_user_language(user_id)
        add_account_text = f"""╔═══════════════════════╗
║   <b>{get_text('add_account_title', lang)}</b>   ║
╚═══════════════════════╝

📱 <b>{get_text('enter_phone', lang)}</b>

{get_text('phone_example', lang)}: <code>+20xxxxxxxxx</code>

💡 <i>{get_text('see_countries_hint', lang)}</i>"""
        
        keyboard = [[InlineKeyboardButton(get_text('back', lang), callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(add_account_text, reply_markup=reply_markup, parse_mode='HTML')

    elif action == "countries":
        lang = database.get_user_language(user_id)
        # جلب الدول من الداتابيز
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT country_code, name, price, review_time, capacity, current_count FROM countries WHERE is_active = TRUE')
        countries = cursor.fetchall()
        conn.close()

        # إنشاء أزرار للدول - كل دولة زرار منفصل
        buttons = []
        
        for country in countries:
            country_code, name, price, review_time, capacity, current_count = country
            # جلب علم الدولة من القاموس أو استخدام علم افتراضي
            flag = COUNTRY_FLAGS.get(country_code, '🌍')
            # تحويل الوقت من دقائق إلى ثواني للعرض
            time_in_seconds = review_time * 60
            # عرض السعة
            capacity_text = f"{current_count}/{capacity if capacity > 0 else '∞'}"
            # إنشاء نص الزرار
            button_text = f"{flag} {country_code} | 💰 {price}$ | ⏰ {time_in_seconds}s | 📊 {capacity_text}"
            # إضافة الزرار (كل زرار في صف لوحده)
            buttons.append([InlineKeyboardButton(button_text, callback_data=f"country_{country_code}")])

        total_countries = len(countries)
        
        # إضافة زرار الرجوع
        buttons.append([InlineKeyboardButton(get_text('back', lang), callback_data="back_to_menu")])
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        # الرسالة النهائية
        countries_text = f"""📋 <b>{get_text('available_countries_title', lang)}</b>

🌍 <b>{get_text('total_countries', lang)}:</b> {total_countries}

{get_text('select_country_details', lang)}:"""

        await query.edit_message_text(countries_text, reply_markup=keyboard, parse_mode='HTML')

    elif action == "withdraw":
        lang = database.get_user_language(user_id)
        user_data = database.get_user(user_id)
        balance = user_data[2] if user_data else 0.0
        
        # جلب حدود السحب من الإعدادات
        min_usdt = database.get_setting('min_usdt', '10')
        min_trx = database.get_setting('min_trx', '3')
        min_vodafone = database.get_setting('min_vodafone', '3')
        
        withdraw_text = f"""╔═══════════════════════╗
║   <b>💸 {get_text('withdraw_title', lang)}</b>   ║
╚═══════════════════════╝

💰 <b>{get_text('your_balance', lang)}:</b> {balance}$

📝 <b>{get_text('min_withdraw', lang)}:</b>
• USDT BEP20: {min_usdt}$
• TRX TRC20: {min_trx}$
• {get_text('vodafone_cash', lang)}: {min_vodafone}$

💳 <b>{get_text('select_wallet', lang)}:</b>"""
        
        keyboard = [
            [InlineKeyboardButton("💎 USDT BEP20", callback_data="wallet_usdt")],
            [InlineKeyboardButton("🔷 TRX TRC20", callback_data="wallet_trx")],
            [InlineKeyboardButton(f"📱 {get_text('vodafone_cash', lang)}", callback_data="wallet_vodafone")],
            [InlineKeyboardButton(get_text('back', lang), callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(withdraw_text, reply_markup=reply_markup, parse_mode='HTML')

    elif action == "support":
        lang = database.get_user_language(user_id)
        # جلب معلومات الدعم من الإعدادات
        support_username = database.get_setting('support_username', '@Support')
        support_msg = database.get_setting('support_message', get_text('support_message', lang))
        
        support_text = f"""╔═══════════════════════╗
║   <b>📞 {get_text('support_title', lang)}</b>   ║
╚═══════════════════════╝

💬 <b>{support_msg}</b>

📧 {get_text('contact_support', lang)}:
• {support_username}

📝 <i>{get_text('support_response', lang)}</i>"""
        
        keyboard = [[InlineKeyboardButton(get_text('back', lang), callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(support_text, reply_markup=reply_markup, parse_mode='HTML')

    elif action == "channel":
        lang = database.get_user_language(user_id)
        channel_text = f"""╔═══════════════════════╗
║   <b>📢 {get_text('channel_title', lang)}</b>   ║
╚═══════════════════════╝

🌟 <b>{get_text('channel_message', lang)}</b>

{CHANNEL_USERNAME}"""
        
        keyboard = [
            [InlineKeyboardButton(f"📢 {get_text('join_channel', lang)}", url=CHANNEL_URL)],
            [InlineKeyboardButton(get_text('back', lang), callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(channel_text, reply_markup=reply_markup, parse_mode='HTML')


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الرجوع للقائمة الرئيسية"""
    query = update.callback_query
    await query.answer()
    await show_main_menu(update, context)

async def country_info_display(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات الدولة (للعرض فقط - الزرار غير فعال)"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    # مجرد answer فاضي عشان الزرار يبدو للعرض فقط
    if lang == 'ar':
        await query.answer("📋 للعرض فقط", show_alert=False)
    else:
        await query.answer("📋 Display only", show_alert=False)

async def handle_wallet_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اختيار المحفظة"""
    query = update.callback_query
    await query.answer()
    
    wallet_type = query.data
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    # تحديد نوع المحفظة والحد الأدنى من الإعدادات
    wallet_info = {
        'wallet_usdt': {
            'name': 'USDT BEP20', 
            'min': float(database.get_setting('min_usdt', '10')),
            'max': float(database.get_setting('max_usdt', '1000')),
            'emoji': '💎'
        },
        'wallet_trx': {
            'name': 'TRX TRC20', 
            'min': float(database.get_setting('min_trx', '3')),
            'max': float(database.get_setting('max_trx', '500')),
            'emoji': '🔷'
        },
        'wallet_vodafone': {
            'name': get_text('vodafone_cash', lang), 
            'min': float(database.get_setting('min_vodafone', '3')),
            'max': float(database.get_setting('max_vodafone', '500')),
            'emoji': '📱'
        }
    }
    
    selected = wallet_info.get(wallet_type)
    
    # حفظ نوع المحفظة في context
    context.user_data['withdraw_wallet'] = wallet_type
    context.user_data['withdraw_min'] = selected['min']
    context.user_data['withdraw_name'] = selected['name']
    context.user_data['waiting_for_wallet_address'] = True
    
    if lang == 'ar':
        enter_wallet = 'أدخل عنوان المحفظة'
        verify_msg = 'تأكد من صحة العنوان قبل الإرسال'
    else:
        enter_wallet = 'Enter wallet address'
        verify_msg = 'Make sure the address is correct before sending'
    
    wallet_text = f"""╔═══════════════════════╗
║   <b>{selected['emoji']} {selected['name']}</b>   ║
╚═══════════════════════╝

📝 <b>{enter_wallet}:</b>

⚠️ <b>{get_text('min_withdraw', lang)}:</b> {selected['min']}$

💡 <i>{verify_msg}</i>"""
    
    keyboard = [[InlineKeyboardButton(get_text('cancel', lang), callback_data="withdraw")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(wallet_text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اختيار المبلغ"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    action = query.data
    
    user_data = database.get_user(user_id)
    balance = user_data[2] if user_data else 0.0
    
    wallet_name = context.user_data.get('withdraw_name', get_text('select_wallet', lang))
    wallet_address = context.user_data.get('wallet_address', '')
    min_amount = context.user_data.get('withdraw_min', 0)
    
    if action == "withdraw_full":
        # سحب كامل الرصيد
        if balance < min_amount:
            insufficient_msg = f"⚠️ {get_text('insufficient_balance', lang)}\n{get_text('min_withdraw', lang)}: {min_amount}$"
            await query.answer(insufficient_msg, show_alert=True)
            return
        
        context.user_data['withdraw_amount'] = balance
        # إتمام طلب السحب
        await process_withdrawal(update, context)
        
    elif action == "withdraw_custom":
        # سحب مبلغ مخصص
        context.user_data['waiting_for_amount'] = True
        
        custom_text = f"""╔═══════════════════════╗
║   <b>💰 {get_text('withdraw_title', lang)}</b>   ║
╚═══════════════════════╝

💵 <b>{get_text('your_balance', lang)}:</b> {balance}$

📝 <b>{get_text('min_withdraw', lang)}:</b> {min_amount}$

⚠️ <b>{get_text('please_wait', lang)}</b>"""
        
        keyboard = [[InlineKeyboardButton(get_text('cancel', lang), callback_data="withdraw")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(custom_text, reply_markup=reply_markup, parse_mode='HTML')

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة طلب السحب"""
    if hasattr(update, 'callback_query') and update.callback_query:
        query = update.callback_query
        user_id = query.from_user.id
        chat_id = query.message.chat_id
    else:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
    
    wallet_name = context.user_data.get('withdraw_name', '')
    wallet_address = context.user_data.get('wallet_address', '')
    amount = context.user_data.get('withdraw_amount', 0)
    
    # حفظ طلب السحب في قاعدة البيانات
    database.create_withdrawal(user_id, wallet_name, wallet_address, amount)
    
    success_text = f"""╔═══════════════════════╗
║   <b>✅ تم تقديم الطلب</b>   ║
╚═══════════════════════╝

🎉 <b>تم تقديم طلب السحب بنجاح!</b>

💳 <b>المحفظة:</b> {wallet_name}
📍 <b>العنوان:</b> <code>{wallet_address}</code>
💰 <b>المبلغ:</b> {amount}$

⏳ <b>جاري مراجعة الطلب...</b>

📝 <i>سيتم التواصل معك قريباً</i>"""
    
    keyboard = [[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # مسح البيانات المؤقتة
    context.user_data.clear()
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(success_text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await context.bot.send_message(chat_id=chat_id, text=success_text, reply_markup=reply_markup, parse_mode='HTML')

async def route_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """توجيه الرسائل للمعالج المناسب"""
    from handlers.admin_message_handler import handle_admin_input
    from handlers.admin_panel import handle_admin_message
    import config
    
    user_id = update.effective_user.id
    
    # لو أدمن وعنده admin_action أو editing_button أو editing_setting، نوجه للمعالج بتاع الأدمن
    if (database.is_admin(user_id) or user_id == config.ADMIN_ID):
        if context.user_data.get('admin_action'):
            await handle_admin_input(update, context)
        elif context.user_data.get('editing_button') or context.user_data.get('editing_setting'):
            await handle_admin_message(update, context)
        else:
            # لو أدمن بس مش في وضع إدخال، نوجه للمعالج بتاع المستخدمين
            await handle_message(update, context)
    else:
        # لو مش أدمن في وضع إدخال، نوجه للمعالج بتاع المستخدمين
        await handle_message(update, context)

def setup_start_handlers(app):
    """إعداد جميع handlers البوت"""
    from telegram.ext import MessageHandler, filters
    
    app.add_handler(CallbackQueryHandler(check_subscription, pattern="check_subscription"))
    app.add_handler(CallbackQueryHandler(cancel_verification, pattern="cancel_verification"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^(back_to_menu|back_to_main_menu)$"))
    app.add_handler(CallbackQueryHandler(country_info_display, pattern="^country_"))
    app.add_handler(CallbackQueryHandler(handle_wallet_selection, pattern="^wallet_"))
    app.add_handler(CallbackQueryHandler(handle_withdraw_amount, pattern="^withdraw_(full|custom)$"))
    app.add_handler(CallbackQueryHandler(handle_menu_actions, pattern="^(balance|add_account|withdraw|countries|support|channel)$"))
    app.add_handler(CallbackQueryHandler(handle_language_change, pattern="^lang_(ar|en)$"))
    
    # معالج الرسائل النصية (يوجه للمعالج المناسب حسب نوع المستخدم)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_message))