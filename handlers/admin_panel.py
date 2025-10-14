from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters, CommandHandler
import database
import config
import sqlite3
from datetime import datetime
import io
import zipfile
import json
from translations import get_text

def is_admin(user_id):
    """التحقق من صلاحيات الأدمن"""
    return user_id == config.ADMIN_ID or database.is_admin(user_id)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /admin لفتح لوحة التحكم"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        lang = database.get_user_language(user_id)
        await update.message.reply_text(get_text('no_admin_access', lang))
        return
    
    await show_admin_panel(update, context)

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض لوحة التحكم الرئيسية"""
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    admin_text = f"""
╔══════════════════════════╗
║   {get_text('admin_panel_title', lang)}   ║
╚══════════════════════════╝

{get_text('admin_welcome', lang)}
{get_text('choose_from_menu_below', lang)}
"""
    
    keyboard = [
        [InlineKeyboardButton(get_text('bot_statistics_btn', lang), callback_data="admin_stats")],
        [InlineKeyboardButton("📊 مراقبة الحسابات", callback_data="admin_monitor")],
        [InlineKeyboardButton(get_text('settings_btn', lang), callback_data="admin_settings")],
        [InlineKeyboardButton(get_text('users_control_btn', lang), callback_data="admin_users")],
        [InlineKeyboardButton(get_text('countries_control_btn', lang), callback_data="admin_countries")],
        [InlineKeyboardButton(get_text('accounts_management_btn', lang), callback_data="admin_accounts")],
        [InlineKeyboardButton(get_text('ready_accounts_control_btn', lang), callback_data="ready_admin_panel")],
        [InlineKeyboardButton(get_text('messages_btn', lang), callback_data="admin_messages")],
        [InlineKeyboardButton(get_text('bot_control_btn', lang), callback_data="admin_bot_control")],
        [InlineKeyboardButton(get_text('withdrawals_btn', lang), callback_data="admin_withdrawals")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(admin_text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(admin_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== إحصائيات البوت ====================
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات البوت"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    # إحصائيات المستخدمين
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM banned_users')
    banned_users = cursor.fetchone()[0]
    
    # إحصائيات الحسابات
    cursor.execute('SELECT COUNT(*) FROM accounts')
    total_accounts = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM accounts WHERE status = 'approved'")
    active_accounts = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM account_reviews WHERE status = 'rejected' AND issues LIKE '%مجمد%'")
    frozen_accounts = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM account_reviews WHERE status = 'pending'")
    pending_reviews = cursor.fetchone()[0]
    
    # الجلسات اللي خرجت من البوت (من accounts) + الجلسات المنقطعة (من account_reviews)
    cursor.execute("SELECT COUNT(*) FROM accounts WHERE status = 'logged_out'")
    logged_out_accounts = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM account_reviews WHERE status = 'rejected' AND issues LIKE '%الجلسة%'")
    rejected_sessions = cursor.fetchone()[0]
    
    disconnected_sessions = logged_out_accounts + rejected_sessions
    
    # إحصائيات السحوبات
    cursor.execute("SELECT COUNT(*) FROM withdrawals WHERE status = 'pending'")
    pending_withdrawals = cursor.fetchone()[0]
    
    cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM withdrawals WHERE status = 'approved'")
    total_withdrawn = cursor.fetchone()[0]
    
    cursor.execute("SELECT COALESCE(SUM(balance), 0) FROM users")
    total_user_balance = cursor.fetchone()[0]
    
    # إحصائيات البروكسيات
    cursor.execute("SELECT COUNT(*) FROM proxies WHERE is_connected = 1")
    connected_proxies = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM proxies WHERE is_connected = 0")
    disconnected_proxies = cursor.fetchone()[0]
    
    # إحصائيات الحسابات الجاهزة
    cursor.execute("SELECT COUNT(*) FROM ready_accounts_purchases")
    ready_sold = cursor.fetchone()[0]
    
    cursor.execute("SELECT COALESCE(SUM(price), 0) FROM ready_accounts_purchases")
    ready_revenue = cursor.fetchone()[0]
    
    conn.close()
    
    stats_text = f"""
╔═══════════════════════════╗
║   {get_text('bot_statistics_title', lang)}   ║
╚═══════════════════════════╝

{get_text('users_label', lang)}
├─ {get_text('total_label', lang)} <code>{total_users}</code>
└─ {get_text('banned_label', lang)} <code>{banned_users}</code>

{get_text('accounts_label', lang)}
├─ {get_text('total_label', lang)} <code>{total_accounts}</code>
├─ {get_text('active_accounts', lang)} <code>{active_accounts}</code>
├─ {get_text('frozen_accounts', lang)} <code>{frozen_accounts}</code>
├─ {get_text('pending_review', lang)} <code>{pending_reviews}</code>
└─ {get_text('disconnected_sessions', lang)} <code>{disconnected_sessions}</code>

{get_text('withdrawals_label', lang)}
├─ {get_text('pending_requests', lang)} <code>{pending_withdrawals}</code>
├─ {get_text('total_withdrawn', lang)} <code>${total_withdrawn:.2f}</code>
└─ {get_text('users_balance', lang)} <code>${total_user_balance:.2f}</code>

{get_text('ready_accounts_label', lang)}
├─ {get_text('sold_accounts', lang)} <code>{ready_sold}</code>
└─ {get_text('total_paid_balance', lang)} <code>${ready_revenue:.2f}</code>

{get_text('proxies_label', lang)}
├─ {get_text('connected', lang)} <code>{connected_proxies}</code>
└─ {get_text('disconnected', lang)} <code>{disconnected_proxies}</code>
"""
    
    keyboard = [[InlineKeyboardButton(get_text('back_to_menu', lang), callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== الإعدادات ====================
async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الإعدادات"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    bot_enabled = database.get_setting('bot_enabled', 'true') == 'true'
    accept_accounts = database.get_setting('accept_accounts', 'true') == 'true'
    spam_check = database.get_setting('spam_check', 'true') == 'true'
    session_check = database.get_setting('session_check', 'true') == 'true'
    freeze_check = database.get_setting('freeze_check', 'true') == 'true'
    add_2fa = database.get_setting('add_2fa', 'true') == 'true'
    
    enabled_text = get_text('enabled', lang)
    disabled_text = get_text('disabled', lang)
    
    settings_text = f"""
╔════════════════════════╗
║   {get_text('settings_title', lang)}   ║
╚════════════════════════╝

{get_text('toggle_settings_hint', lang)}
"""
    
    keyboard = [
        [InlineKeyboardButton(
            f"{'🟢' if bot_enabled else '🔴'} {get_text('bot_status', lang)} {enabled_text if bot_enabled else disabled_text}", 
            callback_data="toggle_bot_enabled"
        )],
        [InlineKeyboardButton(
            f"{'🟢' if accept_accounts else '🔴'} {get_text('accept_accounts_status', lang)} {enabled_text if accept_accounts else disabled_text}", 
            callback_data="toggle_accept_accounts"
        )],
        [InlineKeyboardButton(
            f"{'🟢' if spam_check else '🔴'} {get_text('spam_check_status', lang)} {enabled_text if spam_check else disabled_text}", 
            callback_data="toggle_spam_check"
        )],
        [InlineKeyboardButton(
            f"{'🟢' if session_check else '🔴'} {get_text('session_check_status', lang)} {enabled_text if session_check else disabled_text}", 
            callback_data="toggle_session_check"
        )],
        [InlineKeyboardButton(
            f"{'🟢' if freeze_check else '🔴'} {get_text('freeze_check_status', lang)} {enabled_text if freeze_check else disabled_text}", 
            callback_data="toggle_freeze_check"
        )],
        [InlineKeyboardButton(
            f"{'🟢' if add_2fa else '🔴'} {get_text('add_2fa_status', lang)} {enabled_text if add_2fa else disabled_text}", 
            callback_data="toggle_add_2fa"
        )],
        [InlineKeyboardButton(get_text('change_first_message', lang), callback_data="edit_welcome_message")],
        [InlineKeyboardButton(get_text('edit_menu_buttons', lang), callback_data="edit_menu_buttons")],
        [InlineKeyboardButton(get_text('edit_values_responses', lang), callback_data="edit_values")],
        [InlineKeyboardButton(get_text('back_to_menu', lang), callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(settings_text, reply_markup=reply_markup, parse_mode='HTML')

async def toggle_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبديل إعداد معين"""
    query = update.callback_query
    await query.answer()
    
    setting_name = query.data.replace('toggle_', '')
    current_value = database.get_setting(setting_name, 'true')
    new_value = 'false' if current_value == 'true' else 'true'
    
    database.update_setting(setting_name, new_value)
    
    await show_settings(update, context)

async def show_edit_values(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة تعديل القيم"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    values_text = f"""
╔═══════════════════════════╗
║   {get_text('edit_values_title', lang)}   ║
╚═══════════════════════════╝

{get_text('choose_value_to_edit', lang)}
"""
    
    keyboard = [
        [InlineKeyboardButton(get_text('edit_channel', lang), callback_data="edit_channel_username")],
        [InlineKeyboardButton(get_text('edit_welcome', lang), callback_data="edit_welcome_message")],
        [InlineKeyboardButton(get_text('edit_review_msg', lang), callback_data="edit_review_message")],
        [InlineKeyboardButton(get_text('edit_menu_msg', lang), callback_data="edit_menu_message")],
        [InlineKeyboardButton(get_text('edit_support', lang), callback_data="edit_support_username")],
        [InlineKeyboardButton(get_text('usdt_limits', lang), callback_data="edit_usdt_limits")],
        [InlineKeyboardButton(get_text('trx_limits', lang), callback_data="edit_trx_limits")],
        [InlineKeyboardButton(get_text('vodafone_limits', lang), callback_data="edit_vodafone_limits")],
        [InlineKeyboardButton(get_text('2fa_password', lang), callback_data="edit_2fa_password")],
        [InlineKeyboardButton(get_text('spam_bot_username', lang), callback_data="edit_spam_bot_username")],
        [InlineKeyboardButton(get_text('back', lang), callback_data="admin_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(values_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== تعديل أزرار المنيو ====================
async def show_menu_buttons_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة أزرار المنيو للتعديل"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    buttons_text = f"""
╔═══════════════════════════╗
║   {get_text('edit_menu_buttons_title', lang)}   ║
╚═══════════════════════════╝

{get_text('select_button_to_edit', lang)}
"""
    
    # قائمة الأزرار الـ 8
    menu_buttons = [
        ('my_balance', 'my_balance'),
        ('add_account', 'add_account'),
        ('buy_ready_accounts', 'buy_ready_accounts'),
        ('available_countries', 'available_countries'),
        ('withdraw', 'withdraw'),
        ('recharge_balance', 'recharge_balance'),
        ('support', 'support'),
        ('channel', 'channel')
    ]
    
    keyboard = []
    for button_key, button_name in menu_buttons:
        # التحقق من حالة الزرار (مفعل/معطل)
        is_enabled = database.get_setting(f'button_{button_key}_enabled', 'true') == 'true'
        status_icon = '✅' if is_enabled else '❌'
        
        # الحصول على اسم الزرار المخصص أو الافتراضي
        custom_name = database.get_setting(f'button_{button_key}_{lang}', get_text(button_name, lang))
        
        keyboard.append([InlineKeyboardButton(
            f"{status_icon} {custom_name}",
            callback_data=f"edit_btn_{button_key}"
        )])
    
    keyboard.append([InlineKeyboardButton(get_text('back', lang), callback_data="admin_settings")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(buttons_text, reply_markup=reply_markup, parse_mode='HTML')

async def show_button_options(update: Update, context: ContextTypes.DEFAULT_TYPE, button_key: str = None):
    """عرض خيارات تعديل زرار معين"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    # إذا لم يتم تمرير button_key، نستخرجه من query.data
    if button_key is None:
        button_key = query.data.replace('edit_btn_', '')
    
    # الحصول على حالة الزرار
    is_enabled = database.get_setting(f'button_{button_key}_enabled', 'true') == 'true'
    status_text = get_text('button_enabled', lang) if is_enabled else get_text('button_disabled', lang)
    
    # الحصول على الاسم الحالي
    current_name_ar = database.get_setting(f'button_{button_key}_ar', get_text(button_key, 'ar'))
    current_name_en = database.get_setting(f'button_{button_key}_en', get_text(button_key, 'en'))
    
    options_text = f"""
╔═══════════════════════════╗
║   <b>{current_name_ar if lang == 'ar' else current_name_en}</b>   ║
╚═══════════════════════════╝

📊 <b>الحالة:</b> {status_text}
🇸🇦 <b>الاسم بالعربي:</b> {current_name_ar}
🇬🇧 <b>الاسم بالإنجليزي:</b> {current_name_en}
"""
    
    keyboard = [
        [InlineKeyboardButton(get_text('edit_button_name', lang), callback_data=f"edit_name_{button_key}")],
        [InlineKeyboardButton(
            f"{get_text('toggle_button', lang)} ({'✅→❌' if is_enabled else '❌→✅'})",
            callback_data=f"toggle_btn_{button_key}"
        )],
        [InlineKeyboardButton(get_text('back', lang), callback_data="edit_menu_buttons")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(options_text, reply_markup=reply_markup, parse_mode='HTML')

async def toggle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تشغيل/تعطيل زرار من المنيو"""
    query = update.callback_query
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    button_key = query.data.replace('toggle_btn_', '')
    
    # تبديل حالة الزرار
    current_status = database.get_setting(f'button_{button_key}_enabled', 'true')
    new_status = 'false' if current_status == 'true' else 'true'
    database.update_setting(f'button_{button_key}_enabled', new_status)
    
    # إظهار رسالة التأكيد
    await query.answer(get_text('button_status_updated', lang), show_alert=True)
    
    # العودة لخيارات الزرار مع تمرير button_key مباشرة
    await show_button_options(update, context, button_key)

async def edit_menu_button_name_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء تعديل اسم زرار"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    button_key = query.data.replace('edit_name_', '')
    
    # حفظ المفتاح في السياق
    context.user_data['editing_button'] = button_key
    context.user_data['editing_button_step'] = 'arabic'
    
    prompt_text = f"""
╔═══════════════════════════╗
║   <b>{get_text('edit_button_name', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('enter_arabic_name', lang)}

مثال: <code>💰 رصيدي</code>
"""
    
    keyboard = [[InlineKeyboardButton(get_text('cancel', lang), callback_data=f"edit_btn_{button_key}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(prompt_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== معالج الرسائل للإعدادات ====================
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية من الأدمن"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        return
    
    lang = database.get_user_language(user_id)
    
    # تعديل أسماء أزرار المنيو
    if 'editing_button' in context.user_data:
        button_key = context.user_data['editing_button']
        step = context.user_data.get('editing_button_step', 'arabic')
        value = update.message.text.strip()
        
        if step == 'arabic':
            # حفظ الاسم العربي والانتقال للإنجليزي
            context.user_data['button_arabic_name'] = value
            context.user_data['editing_button_step'] = 'english'
            
            prompt_text = f"""
╔═══════════════════════════╗
║   <b>{get_text('edit_button_name', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('enter_english_name', lang)}

Example: <code>💰 My Balance</code>
"""
            keyboard = [[InlineKeyboardButton(get_text('cancel', lang), callback_data=f"edit_btn_{button_key}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(prompt_text, reply_markup=reply_markup, parse_mode='HTML')
        
        elif step == 'english':
            # حفظ الاسم الإنجليزي وإتمام العملية
            arabic_name = context.user_data.get('button_arabic_name', value)
            english_name = value
            
            database.update_setting(f'button_{button_key}_ar', arabic_name)
            database.update_setting(f'button_{button_key}_en', english_name)
            
            success_text = f"""
{get_text('button_name_updated', lang)}

🇸🇦 {arabic_name}
🇬🇧 {english_name}
"""
            await update.message.reply_text(success_text, parse_mode='HTML')
            
            # مسح البيانات المؤقتة
            del context.user_data['editing_button']
            del context.user_data['editing_button_step']
            del context.user_data['button_arabic_name']
    
    elif 'editing_setting' in context.user_data:
        setting_key = context.user_data['editing_setting']
        value = update.message.text.strip()
        
        database.update_setting(setting_key, value)
        
        success_msg = get_text('setting_updated_success', lang).format(setting=setting_key)
        new_value_text = get_text('new_value', lang)
        
        await update.message.reply_text(
            f"{success_msg}\n\n{new_value_text} <code>{value}</code>",
            parse_mode='HTML'
        )
        
        del context.user_data['editing_setting']

# ==================== التحكم في المستخدمين ====================
async def show_users_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة التحكم في المستخدمين"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    users_text = f"""
╔═══════════════════════════╗
║   {get_text('users_control_title', lang)}   ║
╚═══════════════════════════╝

{get_text('choose_from_menu', lang)}
"""
    
    keyboard = [
        [InlineKeyboardButton(get_text('view_all_users', lang), callback_data="view_all_users_1")],
        [InlineKeyboardButton(get_text('search_user', lang), callback_data="search_user")],
        [InlineKeyboardButton(get_text('balance_control', lang), callback_data="balance_control")],
        [InlineKeyboardButton(get_text('ban_user', lang), callback_data="ban_user")],
        [InlineKeyboardButton(get_text('unban_user', lang), callback_data="unban_user")],
        [InlineKeyboardButton(get_text('back_to_menu', lang), callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(users_text, reply_markup=reply_markup, parse_mode='HTML')

async def view_all_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض جميع المستخدمين مع pagination"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    page = int(query.data.split('_')[-1])
    per_page = 10
    offset = (page - 1) * per_page
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT user_id, username, balance, created_at
        FROM users
        LIMIT ? OFFSET ?
    ''', (per_page, offset))
    users = cursor.fetchall()
    
    users_text = f"""
╔══════════════════════════╗
║   {get_text('users_list_title', lang)}   ║
╚══════════════════════════╝

📊 {get_text('page', lang)} {page} {get_text('of', lang)} {(total_users + per_page - 1) // per_page}
👤 {get_text('total_label', lang)} {total_users} {get_text('user', lang)}

"""
    
    for user in users:
        u_id, username, balance, created_at = user
        
        # حساب عدد الحسابات المسجلة
        cursor.execute('SELECT COUNT(*) FROM accounts WHERE user_id = ? AND status = "approved"', (u_id,))
        accounts_count = cursor.fetchone()[0]
        
        # التحقق من حالة المستخدم
        cursor.execute('SELECT user_id FROM banned_users WHERE user_id = ?', (u_id,))
        is_banned_user = cursor.fetchone() is not None
        
        status = get_text('banned_status', lang) if is_banned_user else get_text('active_status', lang)
        
        users_text += f"""
━━━━━━━━━━━━━━━━━━━━━━
👤 @{username or get_text('no_username', lang)}
🆔 <code>{u_id}</code>
💰 {get_text('balance_label', lang)} ${balance:.2f}
📱 {get_text('accounts_count', lang)} {accounts_count}
📊 {status}

"""
    
    conn.close()
    
    # إنشاء أزرار التنقل
    keyboard = []
    nav_buttons = []
    
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(get_text('previous', lang), callback_data=f"view_all_users_{page-1}"))
    
    if offset + per_page < total_users:
        nav_buttons.append(InlineKeyboardButton(get_text('next', lang), callback_data=f"view_all_users_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton(get_text('back', lang), callback_data="admin_users")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(users_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== التحكم في الدول ====================
async def show_countries_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة التحكم في الدول"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    countries_text = f"""
╔═══════════════════════════╗
║   {get_text('countries_control_title', lang)}   ║
╚═══════════════════════════╝

{get_text('choose_from_menu', lang)}
"""
    
    keyboard = [
        [InlineKeyboardButton(get_text('view_all_countries_btn', lang), callback_data="view_all_countries")],
        [InlineKeyboardButton(get_text('add_country', lang), callback_data="add_country")],
        [InlineKeyboardButton(get_text('edit_country', lang), callback_data="edit_country")],
        [InlineKeyboardButton(get_text('delete_country', lang), callback_data="delete_country")],
        [InlineKeyboardButton(get_text('edit_country_flag', lang), callback_data="edit_country_flag")],
        [InlineKeyboardButton(get_text('edit_country_capacity', lang), callback_data="edit_country_capacity")],
        [InlineKeyboardButton(get_text('back_to_menu', lang), callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(countries_text, reply_markup=reply_markup, parse_mode='HTML')

async def view_all_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض جميع الدول"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM countries WHERE is_active = 1')
    countries = cursor.fetchall()
    conn.close()
    
    countries_text = f"""
╔════════════════════════╗
║   {get_text('available_countries_admin', lang)}   ║
╚════════════════════════╝

"""
    
    for country in countries:
        code, name, price, review_time, is_active, flag, capacity, current_count = country
        
        countries_text += f"""
━━━━━━━━━━━━━━━━━━━━━━
{flag or '🌍'} <b>{name}</b>
🔢 {get_text('country_code', lang)} <code>{code}</code>
💰 {get_text('price', lang)}: ${price}
⏱ {get_text('review_time', lang)} {review_time} {get_text('minute', lang)}
📊 {get_text('capacity', lang)} {current_count}/{capacity if capacity > 0 else get_text('infinite', lang)}

"""
    
    keyboard = [[InlineKeyboardButton(get_text('back', lang), callback_data="admin_countries")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(countries_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== إدارة الحسابات ====================
async def show_accounts_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة إدارة الحسابات"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    accounts_text = f"""
╔═══════════════════════════╗
║   {get_text('accounts_management_title', lang)}   ║
╚═══════════════════════════╝

{get_text('choose_from_menu', lang)}
"""
    
    keyboard = [
        [InlineKeyboardButton(get_text('view_all_accounts', lang), callback_data="view_accounts_by_country")],
        [InlineKeyboardButton(get_text('export_zip', lang), callback_data="export_zip")],
        [InlineKeyboardButton(get_text('export_json', lang), callback_data="export_json")],
        [InlineKeyboardButton(get_text('import_history', lang), callback_data="import_history")],
        [InlineKeyboardButton(get_text('back_to_menu', lang), callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(accounts_text, reply_markup=reply_markup, parse_mode='HTML')

async def view_accounts_by_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الحسابات حسب الدولة"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM countries WHERE is_active = 1')
    countries = cursor.fetchall()
    
    accounts_text = f"""
╔════════════════════════╗
║   {get_text('accounts_by_country_title', lang)}   ║
╚════════════════════════╝

{get_text('select_country_label', lang)}
"""
    
    keyboard = []
    for country in countries:
        code, name, price, review_time, is_active, flag, capacity, current_count = country
        
        cursor.execute("SELECT COUNT(*) FROM accounts WHERE phone_number LIKE ?", (f"{code}%",))
        count = cursor.fetchone()[0]
        
        keyboard.append([InlineKeyboardButton(
            f"{flag or '🌍'} {name} ({count})", 
            callback_data=f"view_country_accounts_{code}"
        )])
    
    conn.close()
    
    keyboard.append([InlineKeyboardButton(get_text('back', lang), callback_data="admin_accounts")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(accounts_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== الرسائل ====================
async def show_messages_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الرسائل"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    messages_text = f"""
╔═══════════════════════════╗
║   {get_text('messages_menu_title', lang)}   ║
╚═══════════════════════════╝

{get_text('choose_from_menu', lang)}
"""
    
    keyboard = [
        [InlineKeyboardButton(get_text('broadcast_message', lang), callback_data="broadcast_message")],
        [InlineKeyboardButton(get_text('send_user_message', lang), callback_data="send_user_message")],
        [InlineKeyboardButton(get_text('back_to_menu', lang), callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(messages_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== التحكم في البوت ====================
async def show_bot_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة التحكم في البوت"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    bot_control_text = f"""
╔═══════════════════════════╗
║   {get_text('bot_control_title', lang)}   ║
╚═══════════════════════════╝

{get_text('choose_from_menu', lang)}
"""
    
    keyboard = [
        [InlineKeyboardButton(get_text('manage_admins', lang), callback_data="manage_admins")],
        [InlineKeyboardButton(get_text('manage_proxies', lang), callback_data="manage_proxies")],
        [InlineKeyboardButton(get_text('back_to_menu', lang), callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(bot_control_text, reply_markup=reply_markup, parse_mode='HTML')

async def manage_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة الأدمنز"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    admins_text = f"""
╔═══════════════════════════╗
║   {get_text('admins_management_title', lang)}   ║
╚═══════════════════════════╝

{get_text('choose_from_menu', lang)}
"""
    
    keyboard = [
        [InlineKeyboardButton(get_text('view_admins', lang), callback_data="view_admins")],
        [InlineKeyboardButton(get_text('add_admin', lang), callback_data="add_admin")],
        [InlineKeyboardButton(get_text('remove_admin', lang), callback_data="remove_admin")],
        [InlineKeyboardButton(get_text('back', lang), callback_data="admin_bot_control")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(admins_text, reply_markup=reply_markup, parse_mode='HTML')

async def view_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الأدمنز"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    admins = database.get_all_admins()
    
    admins_text = f"""
╔═══════════════════════════╗
║   {get_text('admins_list_title', lang)}   ║
╚═══════════════════════════╝

📊 {get_text('total_count', lang)} {len(admins)}

"""
    
    for admin in admins:
        admin_user_id, username, added_by, added_at = admin
        admins_text += f"""
━━━━━━━━━━━━━━━━━━━━━━
👤 @{username or get_text('no_username', lang)}
🆔 <code>{admin_user_id}</code>
📅 {get_text('date_added', lang)} {added_at[:10]}

"""
    
    keyboard = [[InlineKeyboardButton(get_text('back', lang), callback_data="manage_admins")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(admins_text, reply_markup=reply_markup, parse_mode='HTML')

async def manage_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة البروكسيات"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    proxies_text = f"""
╔═══════════════════════════╗
║   {get_text('proxies_management_title', lang)}   ║
╚═══════════════════════════╝

{get_text('choose_from_menu', lang)}
"""
    
    keyboard = [
        [InlineKeyboardButton(get_text('view_proxies', lang), callback_data="view_proxies")],
        [InlineKeyboardButton(get_text('add_proxy', lang), callback_data="add_proxy")],
        [InlineKeyboardButton(get_text('remove_proxy', lang), callback_data="remove_proxy")],
        [InlineKeyboardButton(get_text('back', lang), callback_data="admin_bot_control")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(proxies_text, reply_markup=reply_markup, parse_mode='HTML')

async def view_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض البروكسيات"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    proxies = database.get_all_proxies()
    
    proxies_text = f"""
╔═══════════════════════════╗
║   {get_text('proxies_list_title', lang)}   ║
╚═══════════════════════════╝

📊 {get_text('total_count', lang)} {len(proxies)}

"""
    
    if not proxies:
        proxies_text += f"\n{get_text('no_proxies_added', lang)}"
    else:
        for proxy in proxies:
            proxy_id, address, proxy_type, is_connected, added_by, added_at = proxy
            status = get_text('connected_status', lang) if is_connected else get_text('disconnected_status', lang)
            
            proxies_text += f"""
━━━━━━━━━━━━━━━━━━━━━━
🆔 ID: <code>{proxy_id}</code>
🌐 {address}
🔧 {get_text('proxy_type', lang)} {proxy_type}
📊 {get_text('proxy_status', lang)} {status}

"""
    
    keyboard = [[InlineKeyboardButton(get_text('back', lang), callback_data="manage_proxies")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(proxies_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== السحوبات ====================
async def show_withdrawals_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة السحوبات"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    withdrawals_text = f"""
╔═══════════════════════════╗
║   {get_text('withdrawals_menu_title', lang)}   ║
╚═══════════════════════════╝

{get_text('choose_from_menu', lang)}
"""
    
    keyboard = [
        [InlineKeyboardButton(get_text('pending_withdrawals', lang), callback_data="pending_withdrawals")],
        [InlineKeyboardButton(get_text('withdrawals_history', lang), callback_data="withdrawals_history")],
        [InlineKeyboardButton(get_text('back_to_menu', lang), callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(withdrawals_text, reply_markup=reply_markup, parse_mode='HTML')

async def show_pending_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض طلبات السحب المعلقة"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, user_id, username, amount, wallet_address, wallet_name, created_at
        FROM withdrawals
        WHERE status = 'pending'
        ORDER BY created_at DESC
    ''')
    withdrawals = cursor.fetchall()
    conn.close()
    
    if not withdrawals:
        withdrawals_text = f"""
╔═══════════════════════════╗
║   {get_text('pending_withdrawals_title', lang)}   ║
╚═══════════════════════════╝

{get_text('no_pending_requests', lang)}
"""
        keyboard = [[InlineKeyboardButton(get_text('back', lang), callback_data="admin_withdrawals")]]
    else:
        withdrawals_text = f"""
╔═══════════════════════════╗
║   {get_text('pending_withdrawals_title', lang)}   ║
╚═══════════════════════════╝

📊 {get_text('requests_count', lang)} {len(withdrawals)} {get_text('request', lang)}

{get_text('choose_request_review', lang)}
"""
        keyboard = []
        for withdrawal in withdrawals:
            w_id, w_user_id, username, amount, wallet, wallet_name, created_at = withdrawal
            keyboard.append([InlineKeyboardButton(
                f"💰 ${amount} - @{username or w_user_id}",
                callback_data=f"review_withdrawal_{w_id}"
            )])
        
        keyboard.append([InlineKeyboardButton(get_text('back', lang), callback_data="admin_withdrawals")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(withdrawals_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== معالجات تعديل القيم ====================
async def edit_wallet_limits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة تعديل حدود محفظة معينة"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    wallet_type = query.data.replace('edit_', '').replace('_limits', '')
    
    wallet_names = {
        'usdt': get_text('usdt_bep20', lang),
        'trx': get_text('trx_trc20', lang),
        'vodafone': get_text('vodafone_cash', lang)
    }
    
    wallet_name = wallet_names.get(wallet_type, wallet_type)
    min_val = database.get_setting(f'min_{wallet_type}', '0')
    max_val = database.get_setting(f'max_{wallet_type}', '0')
    
    limits_text = f"""╔═══════════════════════╗
║   <b>{wallet_name}</b>   ║
╚═══════════════════════╝

{get_text('current_min_limit', lang)} {min_val}$
{get_text('current_max_limit', lang)} {max_val}$

{get_text('choose_what_to_edit', lang)}"""
    
    keyboard = [
        [InlineKeyboardButton(get_text('edit_min_limit', lang), callback_data=f"set_min_{wallet_type}")],
        [InlineKeyboardButton(get_text('edit_max_limit', lang), callback_data=f"set_max_{wallet_type}")],
        [InlineKeyboardButton(get_text('back', lang), callback_data="edit_values")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(limits_text, reply_markup=reply_markup, parse_mode='HTML')

async def set_wallet_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب قيمة حد المحفظة"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    action_data = query.data  # set_min_usdt أو set_max_usdt
    parts = action_data.split('_')  # ['set', 'min', 'usdt']
    limit_type = parts[1]  # min أو max
    wallet_type = parts[2]  # usdt, trx, vodafone
    
    limit_name = get_text('min_limit', lang) if limit_type == 'min' else get_text('max_limit', lang)
    
    wallet_names = {
        'usdt': get_text('usdt_bep20', lang),
        'trx': get_text('trx_trc20', lang),
        'vodafone': get_text('vodafone_cash', lang)
    }
    
    wallet_name = wallet_names.get(wallet_type, wallet_type)
    
    # حفظ action في context
    context.user_data['admin_action'] = f'edit_{wallet_type}_{limit_type}'
    
    prompt_text = f"""╔═══════════════════════╗
║   <b>{wallet_name}</b>   ║
╚═══════════════════════╝

{get_text('enter_new_limit', lang).format(limit=limit_name)}

{get_text('example', lang)}: <code>10</code>"""
    
    keyboard = [[InlineKeyboardButton(get_text('cancel', lang), callback_data=f"edit_{wallet_type}_limits")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(prompt_text, reply_markup=reply_markup, parse_mode='HTML')

async def edit_setting_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب القيمة الجديدة لإعداد معين"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    setting = query.data
    
    settings_map = {
        'edit_channel_username': ('channel_username', get_text('channel_subscription', lang)),
        'edit_welcome_message': ('welcome_message', get_text('welcome_message_label', lang)),
        'edit_review_message': ('review_message', get_text('review_message_label', lang)),
        'edit_menu_message': ('menu_message', get_text('menu_message_label', lang)),
        'edit_support_username': ('support_username', get_text('support_username_label', lang)),
        'edit_2fa_password': ('2fa_password', get_text('2fa_password_label', lang)),
        'edit_spam_bot_username': ('spam_bot_username', get_text('spam_bot_username_label', lang))
    }
    
    if setting in settings_map:
        key, name = settings_map[setting]
        current_value = database.get_setting(key, '')
        
        context.user_data['admin_action'] = f'edit_{key}'
        
        edit_text = f"""
╔═══════════════════════════╗
║   {get_text('edit_setting_title', lang).format(name=name)}   ║
╚═══════════════════════════╝

{get_text('current_value', lang)}
<code>{current_value}</code>

{get_text('send_new_value', lang)}
"""
        
        keyboard = [[InlineKeyboardButton(get_text('cancel', lang), callback_data="edit_values")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(edit_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== مراقبة الحسابات ====================
async def show_monitor_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات المراقبة الدورية"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    stats = database.get_monitor_stats()
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM account_reviews WHERE status = 'frozen'")
    frozen_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM account_reviews WHERE status = 'invalid_session'")
    invalid_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM account_reviews WHERE status = 'approved'")
    approved_count = cursor.fetchone()[0]
    
    conn.close()
    
    last_check = stats['last_check_time']
    if last_check:
        from datetime import datetime
        last_check_dt = datetime.fromisoformat(last_check)
        last_check_str = last_check_dt.strftime("%Y-%m-%d %H:%M")
    else:
        last_check_str = "لم يتم الفحص بعد"
    
    monitor_enabled = database.get_setting('monitor_enabled', 'true') == 'true'
    monitor_status = "🟢 مفعّل" if monitor_enabled else "🔴 معطّل"
    monitor_interval = database.get_setting('monitor_interval_hours', '2')
    
    monitor_text = f"""
╔═══════════════════════════╗
║   📊 مراقبة الحسابات   ║
╚═══════════════════════════╝

📈 **إحصائيات المراقبة:**
━━━━━━━━━━━━━━━━━━━━━━━━━

✅ حسابات صالحة: {approved_count}
❄️ حسابات متجمدة: {frozen_count}
❌ جلسات غير صالحة: {invalid_count}

━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 **سجل الفحوصات:**
عدد الفحوصات: {stats['total_checks']}
إجمالي المتجمدة: {stats['total_frozen_found']}
إجمالي غير الصالحة: {stats['total_invalid_found']}

⏰ آخر فحص: {last_check_str}

━━━━━━━━━━━━━━━━━━━━━━━━━

⚙️ **حالة النظام:**
{monitor_status} | كل {monitor_interval} ساعة
"""
    toggle_text = "⏸️ إيقاف" if monitor_enabled else "▶️ تشغيل"
    
    keyboard = [
        [InlineKeyboardButton("📋 سجلات الفحص", callback_data="view_monitor_logs")],
        [InlineKeyboardButton("❄️ الحسابات المتجمدة", callback_data="view_frozen_accounts")],
        [InlineKeyboardButton("❌ الجلسات غير الصالحة", callback_data="view_invalid_accounts")],
        [InlineKeyboardButton(f"{toggle_text} المراقبة", callback_data="toggle_monitor")],
        [InlineKeyboardButton("⏱️ تعديل وقت الفحص", callback_data="edit_monitor_interval")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(monitor_text, reply_markup=reply_markup, parse_mode='Markdown')

async def view_monitor_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض آخر سجلات الفحص"""
    query = update.callback_query
    await query.answer()
    
    logs = database.get_monitor_logs(limit=5)
    
    if not logs:
        logs_text = "📋 **سجلات الفحص الدوري**\n\n❌ لا توجد سجلات بعد"
    else:
        logs_text = "📋 **آخر 5 عمليات فحص:**\n\n"
        for log in logs:
            log_id, total, valid, frozen, invalid, checked_at = log
            from datetime import datetime
            dt = datetime.fromisoformat(checked_at)
            date_str = dt.strftime("%Y-%m-%d %H:%M")
            
            logs_text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━
📅 {date_str}
📊 إجمالي: {total}
✅ صالحة: {valid}
❄️ متجمدة: {frozen}
❌ غير صالحة: {invalid}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_monitor")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(logs_text, reply_markup=reply_markup, parse_mode='Markdown')

async def view_frozen_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الحسابات المتجمدة"""
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT phone_number, issues, created_at 
        FROM account_reviews 
        WHERE status = 'frozen' 
        ORDER BY created_at DESC 
        LIMIT 10
    """)
    frozen = cursor.fetchall()
    conn.close()
    
    if not frozen:
        frozen_text = "❄️ **الحسابات المتجمدة**\n\n✅ لا توجد حسابات متجمدة"
    else:
        frozen_text = f"❄️ **الحسابات المتجمدة** ({len(frozen)})\n\n"
        for phone, issues, created_at in frozen:
            from datetime import datetime
            dt = datetime.fromisoformat(created_at)
            date_str = dt.strftime("%Y-%m-%d")
            frozen_text += f"📱 {phone}\n📅 {date_str}\n⚠️ {issues}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_monitor")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(frozen_text, reply_markup=reply_markup, parse_mode='Markdown')

async def view_invalid_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الجلسات غير الصالحة"""
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT phone_number, issues, created_at 
        FROM account_reviews 
        WHERE status = 'invalid_session' 
        ORDER BY created_at DESC 
        LIMIT 10
    """)
    invalid = cursor.fetchall()
    conn.close()
    
    if not invalid:
        invalid_text = "❌ **الجلسات غير الصالحة**\n\n✅ لا توجد جلسات غير صالحة"
    else:
        invalid_text = f"❌ **الجلسات غير الصالحة** ({len(invalid)})\n\n"
        for phone, issues, created_at in invalid:
            from datetime import datetime
            dt = datetime.fromisoformat(created_at)
            date_str = dt.strftime("%Y-%m-%d")
            invalid_text += f"📱 {phone}\n📅 {date_str}\n⚠️ {issues}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_monitor")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(invalid_text, reply_markup=reply_markup, parse_mode='Markdown')

async def toggle_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبديل حالة المراقبة (تشغيل/إيقاف)"""
    query = update.callback_query
    await query.answer()
    
    current = database.get_setting('monitor_enabled', 'true')
    new_value = 'false' if current == 'true' else 'true'
    database.update_setting('monitor_enabled', new_value)
    
    interval = database.get_setting('monitor_interval_hours', '2')
    
    if new_value == 'true':
        status_text = f"✅ تم تشغيل نظام المراقبة\n\n⏱️ سيبدأ الفحص في الدورة القادمة (كل {interval} ساعة)"
    else:
        status_text = f"⏸️ تم إيقاف نظام المراقبة\n\n💡 سيتوقف الفحص في الدورة القادمة"
    
    await query.answer(status_text, show_alert=True)
    
    await show_monitor_stats(update, context)

async def edit_monitor_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل وقت الفحص"""
    query = update.callback_query
    await query.answer()
    
    current_interval = database.get_setting('monitor_interval_hours', '2')
    
    edit_text = f"""
╔═══════════════════════════╗
║   ⏱️ تعديل وقت الفحص   ║
╚═══════════════════════════╝

⏰ **الوقت الحالي:** كل {current_interval} ساعة

📝 **أرسل الوقت الجديد بالساعات:**
مثال: 1 أو 2 أو 3 أو 6 أو 12 أو 24

💡 **ملحوظة:**
- الحد الأدنى: 1 ساعة
- الحد الأقصى: 24 ساعة
"""
    
    context.user_data['admin_action'] = 'edit_monitor_interval'
    
    keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="admin_monitor")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(edit_text, reply_markup=reply_markup, parse_mode='Markdown')

def setup_admin_handlers(app):
    """إعداد معالجات لوحة التحكم"""
    from handlers.admin_handlers_extra import setup_extra_handlers
    from handlers.admin_message_handler import handle_admin_input
    from handlers.admin_countries import setup_countries_handlers
    from handlers.admin_accounts import setup_accounts_handlers
    from telegram.ext import MessageHandler, filters
    
    app.add_handler(CommandHandler("admin", admin_command))
    
    # القائمة الرئيسية
    app.add_handler(CallbackQueryHandler(show_admin_panel, pattern="^admin_panel$"))
    
    # الإحصائيات
    app.add_handler(CallbackQueryHandler(show_stats, pattern="^admin_stats$"))
    
    # الإعدادات
    app.add_handler(CallbackQueryHandler(show_settings, pattern="^admin_settings$"))
    
    # المراقبة (لازم يكون قبل toggle_setting عشان toggle_monitor ياخد الأولوية)
    app.add_handler(CallbackQueryHandler(toggle_monitor, pattern="^toggle_monitor$"))
    
    # تعديل أزرار المنيو (لازم يكون قبل toggle_ العام عشان toggle_btn_ ياخد الأولوية)
    app.add_handler(CallbackQueryHandler(show_menu_buttons_list, pattern="^edit_menu_buttons$"))
    app.add_handler(CallbackQueryHandler(show_button_options, pattern="^edit_btn_"))
    app.add_handler(CallbackQueryHandler(toggle_menu_button, pattern="^toggle_btn_"))
    app.add_handler(CallbackQueryHandler(edit_menu_button_name_start, pattern="^edit_name_"))
    
    app.add_handler(CallbackQueryHandler(toggle_setting, pattern="^toggle_"))
    app.add_handler(CallbackQueryHandler(show_edit_values, pattern="^edit_values$"))
    app.add_handler(CallbackQueryHandler(edit_setting_prompt, pattern="^edit_channel_username$"))
    app.add_handler(CallbackQueryHandler(edit_setting_prompt, pattern="^edit_welcome_message$"))
    app.add_handler(CallbackQueryHandler(edit_setting_prompt, pattern="^edit_review_message$"))
    app.add_handler(CallbackQueryHandler(edit_setting_prompt, pattern="^edit_menu_message$"))
    app.add_handler(CallbackQueryHandler(edit_setting_prompt, pattern="^edit_support_username$"))
    app.add_handler(CallbackQueryHandler(edit_setting_prompt, pattern="^edit_2fa_password$"))
    app.add_handler(CallbackQueryHandler(edit_setting_prompt, pattern="^edit_spam_bot_username$"))
    app.add_handler(CallbackQueryHandler(edit_wallet_limits, pattern="^edit_usdt_limits$"))
    app.add_handler(CallbackQueryHandler(edit_wallet_limits, pattern="^edit_trx_limits$"))
    app.add_handler(CallbackQueryHandler(edit_wallet_limits, pattern="^edit_vodafone_limits$"))
    app.add_handler(CallbackQueryHandler(set_wallet_limit, pattern="^set_min_"))
    app.add_handler(CallbackQueryHandler(set_wallet_limit, pattern="^set_max_"))
    
    # المستخدمين
    app.add_handler(CallbackQueryHandler(show_users_control, pattern="^admin_users$"))
    app.add_handler(CallbackQueryHandler(view_all_users, pattern="^view_all_users_"))
    
    # الدول
    app.add_handler(CallbackQueryHandler(show_countries_control, pattern="^admin_countries$"))
    app.add_handler(CallbackQueryHandler(view_all_countries, pattern="^view_all_countries$"))
    
    # الحسابات
    app.add_handler(CallbackQueryHandler(show_accounts_management, pattern="^admin_accounts$"))
    app.add_handler(CallbackQueryHandler(view_accounts_by_country, pattern="^view_accounts_by_country$"))
    
    # الرسائل
    app.add_handler(CallbackQueryHandler(show_messages_menu, pattern="^admin_messages$"))
    
    # التحكم في البوت
    app.add_handler(CallbackQueryHandler(show_bot_control, pattern="^admin_bot_control$"))
    app.add_handler(CallbackQueryHandler(manage_admins, pattern="^manage_admins$"))
    app.add_handler(CallbackQueryHandler(view_admins, pattern="^view_admins$"))
    app.add_handler(CallbackQueryHandler(manage_proxies, pattern="^manage_proxies$"))
    app.add_handler(CallbackQueryHandler(view_proxies, pattern="^view_proxies$"))
    
    # السحوبات
    app.add_handler(CallbackQueryHandler(show_withdrawals_menu, pattern="^admin_withdrawals$"))
    app.add_handler(CallbackQueryHandler(show_pending_withdrawals, pattern="^pending_withdrawals$"))
    
    # المراقبة (باقي handlers المراقبة - toggle_monitor اتحط فوق)
    app.add_handler(CallbackQueryHandler(show_monitor_stats, pattern="^admin_monitor$"))
    app.add_handler(CallbackQueryHandler(view_monitor_logs, pattern="^view_monitor_logs$"))
    app.add_handler(CallbackQueryHandler(view_frozen_accounts, pattern="^view_frozen_accounts$"))
    app.add_handler(CallbackQueryHandler(view_invalid_accounts, pattern="^view_invalid_accounts$"))
    app.add_handler(CallbackQueryHandler(edit_monitor_interval, pattern="^edit_monitor_interval$"))
    
    # إضافة المعالجات الإضافية
    setup_extra_handlers(app)
    setup_countries_handlers(app)
    setup_accounts_handlers(app)
