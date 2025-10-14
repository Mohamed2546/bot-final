"""
معالجات إدارة الحسابات
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import sqlite3
from datetime import datetime
import io
import zipfile
import json
import database
from translations import get_text

# ==================== عرض تفاصيل حسابات الدولة ====================
async def view_country_accounts_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض تفاصيل حسابات دولة معينة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    country_code = query.data.replace('view_country_accounts_', '')
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    # الحسابات الناجحة
    cursor.execute('SELECT COUNT(*) FROM accounts WHERE phone_number LIKE ? AND status = "approved"', (f"{country_code}%",))
    successful = cursor.fetchone()[0]
    
    # الحسابات الفاشلة
    cursor.execute('SELECT COUNT(*) FROM account_reviews WHERE phone_number LIKE ? AND status = "rejected"', (f"{country_code}%",))
    failed = cursor.fetchone()[0]
    
    # الحسابات المجمدة
    cursor.execute('SELECT COUNT(*) FROM account_reviews WHERE phone_number LIKE ? AND status = "rejected" AND issues LIKE "%مجمد%"', (f"{country_code}%",))
    frozen = cursor.fetchone()[0]
    
    # خروج من جلسة البوت
    cursor.execute('SELECT COUNT(*) FROM account_reviews WHERE phone_number LIKE ? AND status = "rejected" AND issues LIKE "%الجلسة%"', (f"{country_code}%",))
    disconnected = cursor.fetchone()[0]
    
    # معلومات الدولة
    cursor.execute('SELECT name, flag FROM countries WHERE country_code = ?', (country_code,))
    country_info = cursor.fetchone()
    
    conn.close()
    
    if not country_info:
        await query.edit_message_text(f"❌ {get_text('country_not_found', lang)}")
        return
    
    name, flag = country_info
    
    details_text = f"""
╔═══════════════════════════╗
║   {flag or '🌍'} <b>{name}</b>   ║
╚═══════════════════════════╝

📊 <b>{get_text('account_statistics_title', lang)}</b>

✅ <b>{get_text('successful_accounts', lang)}</b> {successful}
❌ <b>{get_text('failed_accounts', lang)}</b> {failed}
🧊 <b>{get_text('frozen_accounts_label', lang)}</b> {frozen}
🔌 <b>{get_text('disconnected_sessions_label', lang)}</b> {disconnected}

📈 <b>{get_text('total_short', lang)}</b> {successful + failed}
"""
    
    keyboard = [
        [InlineKeyboardButton(f"📤 {get_text('export_country_sessions', lang)}", callback_data=f"export_for_{country_code}")],
        [InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data="view_accounts_by_country")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(details_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== تاريخ التصدير ====================
async def show_import_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض تاريخ التصدير حسب الدولة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    conn = sqlite3.connect('bot.db')
    try:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT country_code, SUM(count) as total
            FROM import_history
            GROUP BY country_code
        ''')
        countries_import = cursor.fetchall()
        
        history_text = f"""
╔═══════════════════════════╗
║   📜 <b>{get_text('export_history_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('select_country_export_history', lang)}
"""
        
        keyboard = []
        for country_code, total in countries_import:
            cursor.execute('SELECT name, flag FROM countries WHERE country_code = ?', (country_code,))
            country_info = cursor.fetchone()
            
            if country_info:
                name, flag = country_info
                keyboard.append([InlineKeyboardButton(
                    f"{flag or '🌍'} {name} ({total})",
                    callback_data=f"import_history_{country_code}"
                )])
        
        if not keyboard:
            history_text += f"\n⚠️ {get_text('no_export_history', lang)}"
        
        keyboard.append([InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data="admin_accounts")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(history_text, reply_markup=reply_markup, parse_mode='HTML')
    finally:
        conn.close()

async def show_country_import_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض تاريخ تصدير دولة معينة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    country_code = query.data.replace('import_history_', '')
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT name, flag FROM countries WHERE country_code = ?', (country_code,))
    country_info = cursor.fetchone()
    
    cursor.execute('''
        SELECT count, format, admin_username, imported_at
        FROM import_history
        WHERE country_code = ?
        ORDER BY imported_at DESC
        LIMIT 10
    ''', (country_code,))
    imports = cursor.fetchall()
    
    conn.close()
    
    if not country_info:
        await query.edit_message_text(f"❌ {get_text('country_not_found', lang)}")
        return
    
    name, flag = country_info
    
    history_text = f"""
╔═══════════════════════════╗
║   {flag or '🌍'} <b>{name}</b>   ║
╚═══════════════════════════╝

📜 <b>{get_text('last_10_exports', lang)}</b>

"""
    
    if not imports:
        history_text += f"⚠️ {get_text('no_exports', lang)}"
    else:
        for count, format_type, admin_username, imported_at in imports:
            history_text += f"""
━━━━━━━━━━━━━━━━━━━━━━
📦 {get_text('count_label', lang)} {count}
📄 {get_text('format_label', lang)} {format_type}
👨‍💼 {get_text('by_label', lang)} @{admin_username}
📅 {get_text('date_label', lang)} {imported_at[:16]}

"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data="import_history")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(history_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== تصدير جلسات دولة معينة ====================
async def export_country_sessions_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختيار نوع التصدير لدولة معينة"""
    query = update.callback_query
    await query.answer()
    
    admin_id = query.from_user.id
    lang = database.get_user_language(admin_id)
    
    country_code = query.data.replace('export_for_', '')
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    # جلب معلومات الدولة
    cursor.execute('SELECT name, flag FROM countries WHERE country_code = ?', (country_code,))
    country_info = cursor.fetchone()
    
    # عدد الحسابات المتاحة
    cursor.execute('SELECT COUNT(*) FROM accounts WHERE phone_number LIKE ? AND status = "approved"', (f"{country_code}%",))
    available_count = cursor.fetchone()[0]
    
    conn.close()
    
    if not country_info:
        await query.edit_message_text(f"❌ {get_text('country_not_found', lang)}")
        return
    
    name, flag = country_info
    
    if available_count == 0:
        await query.edit_message_text(
            f"❌ {get_text('no_sessions_export', lang)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data=f"view_country_accounts_{country_code}")]])
        )
        return
    
    # حفظ الدولة المختارة
    context.user_data['export_country_code'] = country_code
    
    text = f"""
╔═══════════════════════════╗
║   📤 <b>تصدير جلسات</b>   ║
╚═══════════════════════════╝

🌍 <b>الدولة:</b> {flag or '🌍'} {name}
📊 <b>العدد المتاح:</b> {available_count}

📝 <b>اختر نوع التصدير:</b>
"""
    
    keyboard = [
        [InlineKeyboardButton("📦 ZIP", callback_data=f"export_country_type_zip_{country_code}")],
        [InlineKeyboardButton("📄 JSON", callback_data=f"export_country_type_json_{country_code}")],
        [InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data=f"view_country_accounts_{country_code}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def export_country_sessions_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب الكمية المطلوبة للتصدير"""
    query = update.callback_query
    await query.answer()
    
    admin_id = query.from_user.id
    lang = database.get_user_language(admin_id)
    
    # استخراج النوع والدولة من callback_data
    parts = query.data.split('_')
    export_type = parts[3]  # zip أو json
    country_code = parts[4]
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    # جلب معلومات الدولة
    cursor.execute('SELECT name, flag FROM countries WHERE country_code = ?', (country_code,))
    country_info = cursor.fetchone()
    
    # عدد الحسابات المتاحة
    cursor.execute('SELECT COUNT(*) FROM accounts WHERE phone_number LIKE ? AND status = "approved"', (f"{country_code}%",))
    available_count = cursor.fetchone()[0]
    
    conn.close()
    
    if not country_info:
        await query.edit_message_text(f"❌ {get_text('country_not_found', lang)}")
        return
    
    name, flag = country_info
    
    # حفظ معلومات التصدير
    context.user_data['export_country_code'] = country_code
    context.user_data['export_type'] = export_type
    context.user_data['admin_action'] = 'export_country_sessions'
    
    text = f"""
╔═══════════════════════════╗
║   📤 <b>تصدير جلسات</b>   ║
╚═══════════════════════════╝

🌍 <b>الدولة:</b> {flag or '🌍'} {name}
📊 <b>العدد المتاح:</b> {available_count}
📄 <b>النوع:</b> {export_type.upper()}

📝 <b>أرسل الكمية المطلوبة:</b>
(أرسل 0 لتصدير الكل)
"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data=f"export_for_{country_code}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== تصدير الجلسات ====================
async def export_zip_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تصدير الجلسات بصيغة ZIP"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    await query.edit_message_text(f"⏳ {get_text('preparing_sessions', lang)}")
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    # جلب جميع الحسابات المقبولة
    cursor.execute('SELECT phone_number, session_string FROM accounts WHERE status = "approved"')
    accounts = cursor.fetchall()
    conn.close()
    
    if not accounts:
        await query.edit_message_text(
            f"❌ {get_text('no_sessions_export', lang)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data="admin_accounts")]])
        )
        return
    
    # إنشاء ملف ZIP في الذاكرة
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for phone, session_string in accounts:
            # حفظ كل جلسة كملف .session
            zip_file.writestr(f"{phone}.session", session_string)
    
    zip_buffer.seek(0)
    
    # إرسال الملف
    await context.bot.send_document(
        chat_id=query.message.chat_id,
        document=zip_buffer,
        filename=f"sessions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
        caption=f"📤 <b>{get_text('sessions_export_title', lang)}</b>\n\n📊 {get_text('count_label', lang)} {len(accounts)}\n📅 {get_text('date_label', lang)} {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        parse_mode='HTML'
    )
    
    await query.message.reply_text(
        f"✅ {get_text('sessions_exported', lang)}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data="admin_accounts")]])
    )

async def export_json_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تصدير الجلسات بصيغة JSON"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    await query.edit_message_text(f"⏳ {get_text('preparing_sessions', lang)}")
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    # جلب جميع الحسابات المقبولة مع تجميعها حسب الدولة
    cursor.execute('SELECT phone_number, session_string FROM accounts WHERE status = "approved"')
    accounts = cursor.fetchall()
    conn.close()
    
    if not accounts:
        await query.edit_message_text(
            f"❌ {get_text('no_sessions_export', lang)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data="admin_accounts")]])
        )
        return
    
    # تجميع الجلسات حسب الدولة
    sessions_by_country = {}
    for phone, session_string in accounts:
        # استخراج رمز الدولة من الرقم (أول 3-4 أرقام)
        country_code = None
        for i in range(2, 5):
            potential_code = phone[:i]
            if potential_code.startswith('+'):
                country_code = potential_code
        
        if country_code not in sessions_by_country:
            sessions_by_country[country_code] = []
        
        sessions_by_country[country_code].append({
            "phone": phone,
            "session": session_string
        })
    
    # إنشاء ملفات JSON لكل دولة
    json_files = []
    for country_code, sessions in sessions_by_country.items():
        json_data = {
            "country_code": country_code,
            "sessions": sessions,
            "exported_at": datetime.now().isoformat(),
            "total_count": len(sessions)
        }
        
        json_buffer = io.BytesIO()
        json_buffer.write(json.dumps(json_data, ensure_ascii=False, indent=2).encode('utf-8'))
        json_buffer.seek(0)
        json_files.append((country_code, json_buffer, len(sessions)))
    
    # إرسال الملفات
    for country_code, json_buffer, count in json_files:
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=json_buffer,
            filename=f"sessions_{country_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            caption=f"📤 <b>{get_text('export_sessions_country', lang).format(code=country_code)}</b>\n\n📊 {get_text('count_label', lang)} {count}",
            parse_mode='HTML'
        )
    
    await query.message.reply_text(
        f"✅ {get_text('sessions_exported', lang)}\n\n📊 {get_text('total_sessions', lang)} {len(accounts)}\n📁 {get_text('files_count', lang)} {len(json_files)}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data="admin_accounts")]])
    )

# ==================== تصدير جلسات مستخدم معين ====================
async def export_user_sessions_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الدول المتاحة لتصدير جلسات مستخدم معين"""
    query = update.callback_query
    await query.answer()
    
    admin_id = query.from_user.id
    lang = database.get_user_language(admin_id)
    
    target_user_id = int(query.data.replace('export_user_sessions_', ''))
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    # جلب الدول المتاحة للمستخدم
    cursor.execute('''
        SELECT DISTINCT SUBSTR(phone_number, 1, 
            CASE 
                WHEN phone_number LIKE '+1%' THEN 2
                WHEN phone_number LIKE '+2%' THEN 3
                WHEN phone_number LIKE '+3%' THEN 3
                WHEN phone_number LIKE '+4%' THEN 3
                WHEN phone_number LIKE '+5%' THEN 3
                WHEN phone_number LIKE '+6%' THEN 3
                WHEN phone_number LIKE '+7%' THEN 2
                WHEN phone_number LIKE '+8%' THEN 3
                WHEN phone_number LIKE '+9%' THEN 3
                ELSE 3
            END
        ) as country_code,
        COUNT(*) as count
        FROM accounts 
        WHERE user_id = ? AND status = "approved"
        GROUP BY country_code
        ORDER BY count DESC
    ''', (target_user_id,))
    
    countries_data = cursor.fetchall()
    conn.close()
    
    if not countries_data:
        await query.edit_message_text(
            f"❌ لا توجد حسابات معتمدة لهذا المستخدم!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"🔙 رجوع", callback_data="admin_users")]])
        )
        return
    
    # حفظ الـ user_id في context
    context.user_data['export_target_user_id'] = target_user_id
    
    text = f"""
╔═══════════════════════════╗
║   📤 <b>تصدير جلسات المستخدم</b>   ║
╚═══════════════════════════╝

👤 <b>معرف المستخدم:</b> <code>{target_user_id}</code>

🌍 <b>اختر الدولة للتصدير:</b>
"""
    
    keyboard = []
    for country_code, count in countries_data:
        # محاولة الحصول على معلومات الدولة
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT name, flag FROM countries WHERE country_code = ?', (country_code,))
        country_info = cursor.fetchone()
        conn.close()
        
        if country_info:
            name, flag = country_info
            btn_text = f"{flag or '🌍'} {name} ({count})"
        else:
            btn_text = f"{country_code} ({count})"
        
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"export_user_country_{country_code}")])
    
    keyboard.append([InlineKeyboardButton(f"🔙 رجوع", callback_data="admin_users")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def export_user_sessions_country_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب الكمية بعد اختيار الدولة"""
    query = update.callback_query
    await query.answer()
    
    admin_id = query.from_user.id
    lang = database.get_user_language(admin_id)
    
    country_code = query.data.replace('export_user_country_', '')
    target_user_id = context.user_data.get('export_target_user_id')
    
    if not target_user_id:
        await query.edit_message_text("❌ حدث خطأ! حاول مرة أخرى.")
        return
    
    # حساب العدد المتاح
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM accounts 
        WHERE user_id = ? AND phone_number LIKE ? AND status = "approved"
    ''', (target_user_id, f"{country_code}%"))
    available_count = cursor.fetchone()[0]
    
    # معلومات الدولة
    cursor.execute('SELECT name, flag FROM countries WHERE country_code = ?', (country_code,))
    country_info = cursor.fetchone()
    conn.close()
    
    if country_info:
        name, flag = country_info
        country_display = f"{flag or '🌍'} {name}"
    else:
        country_display = country_code
    
    # حفظ الدولة المختارة
    context.user_data['export_country_code'] = country_code
    context.user_data['admin_action'] = f'export_user_sessions_quantity'
    
    text = f"""
╔═══════════════════════════╗
║   📤 <b>تصدير جلسات</b>   ║
╚═══════════════════════════╝

👤 <b>المستخدم:</b> <code>{target_user_id}</code>
🌍 <b>الدولة:</b> {country_display}
📊 <b>العدد المتاح:</b> {available_count}

📝 <b>أرسل الكمية المطلوبة:</b>
(أرسل 0 لتصدير الكل)
"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 إلغاء", callback_data=f"export_user_sessions_{target_user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

def setup_accounts_handlers(app):
    """إعداد معالجات الحسابات"""
    from telegram.ext import CallbackQueryHandler
    
    # عرض تفاصيل الحسابات
    app.add_handler(CallbackQueryHandler(view_country_accounts_details, pattern="^view_country_accounts_"))
    
    # تاريخ الاستيراد
    app.add_handler(CallbackQueryHandler(show_import_history, pattern="^import_history$"))
    app.add_handler(CallbackQueryHandler(show_country_import_history, pattern="^import_history_"))
    
    # تصدير الجلسات
    app.add_handler(CallbackQueryHandler(export_zip_sessions, pattern="^export_zip$"))
    app.add_handler(CallbackQueryHandler(export_json_sessions, pattern="^export_json$"))
    
    # تصدير جلسات دولة معينة
    app.add_handler(CallbackQueryHandler(export_country_sessions_options, pattern="^export_for_"))
    app.add_handler(CallbackQueryHandler(export_country_sessions_quantity, pattern="^export_country_type_"))
    
    # تصدير جلسات مستخدم معين
    app.add_handler(CallbackQueryHandler(export_user_sessions_countries, pattern="^export_user_sessions_"))
    app.add_handler(CallbackQueryHandler(export_user_sessions_country_selected, pattern="^export_user_country_"))
