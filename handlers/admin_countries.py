"""
معالجات التحكم في الدول
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import sqlite3
from datetime import datetime
import database
from translations import get_text

# ==================== تاريخ السحوبات ====================
async def show_withdrawals_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة تاريخ السحوبات"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    history_text = f"""
╔═══════════════════════════╗
║   📜 <b>{get_text('withdrawals_history_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('choose_withdrawal_type', lang)}
"""
    
    keyboard = [
        [InlineKeyboardButton(f"✅ {get_text('approved_withdrawals', lang)}", callback_data="approved_withdrawals_1")],
        [InlineKeyboardButton(f"❌ {get_text('rejected_withdrawals', lang)}", callback_data="rejected_withdrawals_1")],
        [InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data="admin_withdrawals")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(history_text, reply_markup=reply_markup, parse_mode='HTML')

async def show_approved_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض السحوبات المقبولة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    page = int(query.data.split('_')[-1])
    per_page = 10
    offset = (page - 1) * per_page
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM withdrawals WHERE status = "approved"')
    total = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT user_id, username, amount, wallet_address, created_at, processed_at, admin_id
        FROM withdrawals
        WHERE status = "approved"
        ORDER BY processed_at DESC
        LIMIT ? OFFSET ?
    ''', (per_page, offset))
    
    withdrawals = cursor.fetchall()
    conn.close()
    
    withdrawals_text = f"""
╔═══════════════════════════╗
║   ✅ <b>{get_text('approved_withdrawals', lang)}</b>   ║
╚═══════════════════════════╝

📄 {get_text('page', lang)} {page} {get_text('of', lang)} {(total + per_page - 1) // per_page}
📊 {get_text('total_label_short', lang)} {total}

"""
    
    for w in withdrawals:
        user_id, username, amount, wallet, created_at, processed_at, admin_id = w
        withdrawals_text += f"""
━━━━━━━━━━━━━━━━━━━━━━
👤 @{username or user_id}
💰 {get_text('amount_label', lang)} ${amount}
📍 {get_text('wallet_label', lang)} <code>{wallet[:20]}...</code>
📅 {get_text('request_date', lang)} {created_at[:16]}
✅ {get_text('approval_date', lang)} {processed_at[:16]}
👨‍💼 {get_text('by_admin', lang)} <code>{admin_id}</code>

"""
    
    # أزرار التنقل
    keyboard = []
    nav_buttons = []
    
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(f"⬅️ {get_text('previous', lang)}", callback_data=f"approved_withdrawals_{page-1}"))
    
    if offset + per_page < total:
        nav_buttons.append(InlineKeyboardButton(f"➡️ {get_text('next', lang)}", callback_data=f"approved_withdrawals_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data="withdrawals_history")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(withdrawals_text, reply_markup=reply_markup, parse_mode='HTML')

async def show_rejected_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض السحوبات المرفوضة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    page = int(query.data.split('_')[-1])
    per_page = 10
    offset = (page - 1) * per_page
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM withdrawals WHERE status = "rejected"')
    total = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT user_id, username, amount, rejection_reason, created_at, processed_at, admin_id
        FROM withdrawals
        WHERE status = "rejected"
        ORDER BY processed_at DESC
        LIMIT ? OFFSET ?
    ''', (per_page, offset))
    
    withdrawals = cursor.fetchall()
    conn.close()
    
    withdrawals_text = f"""
╔═══════════════════════════╗
║   ❌ <b>{get_text('rejected_withdrawals', lang)}</b>   ║
╚═══════════════════════════╝

📄 {get_text('page', lang)} {page} {get_text('of', lang)} {(total + per_page - 1) // per_page}
📊 {get_text('total_label_short', lang)} {total}

"""
    
    for w in withdrawals:
        user_id, username, amount, reason, created_at, processed_at, admin_id = w
        withdrawals_text += f"""
━━━━━━━━━━━━━━━━━━━━━━
👤 @{username or user_id}
💰 {get_text('amount_label', lang)} ${amount}
📝 {get_text('reason', lang)} {reason}
📅 {get_text('request_date', lang)} {created_at[:16]}
❌ {get_text('rejection_date', lang)} {processed_at[:16]}
👨‍💼 {get_text('by_admin', lang)} <code>{admin_id}</code>

"""
    
    # أزرار التنقل
    keyboard = []
    nav_buttons = []
    
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(f"⬅️ {get_text('previous', lang)}", callback_data=f"rejected_withdrawals_{page-1}"))
    
    if offset + per_page < total:
        nav_buttons.append(InlineKeyboardButton(f"➡️ {get_text('next', lang)}", callback_data=f"rejected_withdrawals_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data="withdrawals_history")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(withdrawals_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== إدارة الدول ====================
async def add_country_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب بيانات إضافة دولة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    context.user_data['admin_action'] = 'add_country'
    
    add_country_text = f"""
╔═══════════════════════════╗
║   ➕ <b>{get_text('add_country_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('add_country_format', lang)}
<code>{get_text('add_country_format_text', lang)}</code>

{get_text('add_country_example', lang)} <code>+20|مصر|0.50|5|🇪🇬</code>
"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('cancel', lang)}", callback_data="admin_countries")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(add_country_text, reply_markup=reply_markup, parse_mode='HTML')

async def edit_country_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختيار دولة للتعديل"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM countries WHERE is_active = 1')
    countries = cursor.fetchall()
    conn.close()
    
    select_text = f"""
╔═══════════════════════════╗
║   ✏️ <b>{get_text('edit_country_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('select_country_to_edit', lang)}
"""
    
    keyboard = []
    for country in countries:
        code, name, price, review_time, is_active, flag, capacity, current_count = country
        keyboard.append([InlineKeyboardButton(
            f"{flag or '🌍'} {name}",
            callback_data=f"edit_country_data_{code}"
        )])
    
    keyboard.append([InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data="admin_countries")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(select_text, reply_markup=reply_markup, parse_mode='HTML')

async def edit_country_data_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب البيانات الجديدة للدولة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    country_code = query.data.replace('edit_country_data_', '')
    context.user_data['admin_action'] = f'edit_country_{country_code}'
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM countries WHERE country_code = ?', (country_code,))
    country = cursor.fetchone()
    conn.close()
    
    if not country:
        await query.edit_message_text(f"❌ {get_text('country_not_found', lang)}")
        return
    
    code, name, price, review_time, is_active, flag, capacity, current_count = country
    
    edit_text = f"""
╔═══════════════════════════╗
║   ✏️ <b>{get_text('edit_country_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('current_data', lang)}
{flag or '🌍'} <b>{name}</b>
🔢 {get_text('country_code_label', lang)} <code>{code}</code>
💰 {get_text('price_label', lang)} ${price}
⏱ {get_text('review_time_short', lang)} {review_time} {get_text('minute', lang)}

{get_text('send_new_data', lang)}
<code>{get_text('edit_country_format', lang)}</code>

{get_text('add_country_example', lang)} <code>مصر|0.75|7|🇪🇬</code>
"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('cancel', lang)}", callback_data="edit_country")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(edit_text, reply_markup=reply_markup, parse_mode='HTML')

async def delete_country_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختيار دولة للحذف"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM countries WHERE is_active = 1')
    countries = cursor.fetchall()
    conn.close()
    
    select_text = f"""
╔═══════════════════════════╗
║   🗑️ <b>{get_text('delete_country_title', lang)}</b>   ║
╚═══════════════════════════╝

⚠️ {get_text('select_country_to_delete', lang)}
"""
    
    keyboard = []
    for country in countries:
        code, name, price, review_time, is_active, flag, capacity, current_count = country
        keyboard.append([InlineKeyboardButton(
            f"{flag or '🌍'} {name}",
            callback_data=f"confirm_delete_country_{code}"
        )])
    
    keyboard.append([InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data="admin_countries")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(select_text, reply_markup=reply_markup, parse_mode='HTML')

async def confirm_delete_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأكيد حذف الدولة"""
    query = update.callback_query
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    await query.answer(f"✅ {get_text('country_deleted', lang)}")
    
    country_code = query.data.replace('confirm_delete_country_', '')
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE countries SET is_active = 0 WHERE country_code = ?', (country_code,))
    conn.commit()
    conn.close()
    
    await query.edit_message_text(f"✅ {get_text('country_deleted', lang)} <code>{country_code}</code>!", parse_mode='HTML')

async def edit_country_flag_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختيار دولة لتعديل علمها"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM countries WHERE is_active = 1')
    countries = cursor.fetchall()
    conn.close()
    
    select_text = f"""
╔═══════════════════════════╗
║   🏴 <b>{get_text('edit_country_flag_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('select_country_for_flag', lang)}
"""
    
    keyboard = []
    for country in countries:
        code, name, price, review_time, is_active, flag, capacity, current_count = country
        keyboard.append([InlineKeyboardButton(
            f"{flag or '🌍'} {name}",
            callback_data=f"edit_flag_{code}"
        )])
    
    keyboard.append([InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data="admin_countries")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(select_text, reply_markup=reply_markup, parse_mode='HTML')

async def edit_country_flag_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب العلم الجديد"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    country_code = query.data.replace('edit_flag_', '')
    context.user_data['admin_action'] = f'edit_flag_{country_code}'
    
    flag_text = f"""
╔═══════════════════════════╗
║   🏴 <b>{get_text('edit_flag_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('country_label', lang)} <code>{country_code}</code>

{get_text('send_new_flag', lang)}
{get_text('add_country_example', lang)} 🇪🇬
"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('cancel', lang)}", callback_data="edit_country_flag")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(flag_text, reply_markup=reply_markup, parse_mode='HTML')

async def edit_country_capacity_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختيار دولة لتعديل سعتها"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM countries WHERE is_active = 1')
    countries = cursor.fetchall()
    conn.close()
    
    select_text = f"""
╔═══════════════════════════╗
║   📊 <b>{get_text('edit_capacity_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('select_country_for_flag', lang)}
"""
    
    keyboard = []
    for country in countries:
        code, name, price, review_time, is_active, flag, capacity, current_count = country
        keyboard.append([InlineKeyboardButton(
            f"{flag or '🌍'} {name} ({current_count}/{capacity})",
            callback_data=f"edit_capacity_{code}"
        )])
    
    keyboard.append([InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data="admin_countries")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(select_text, reply_markup=reply_markup, parse_mode='HTML')

async def edit_country_capacity_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب السعة الجديدة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    country_code = query.data.replace('edit_capacity_', '')
    context.user_data['admin_action'] = f'edit_capacity_{country_code}'
    
    capacity_text = f"""
╔═══════════════════════════╗
║   📊 <b>{get_text('edit_capacity_short', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('country_label', lang)} <code>{country_code}</code>

{get_text('send_new_capacity', lang)}
{get_text('add_country_example', lang)} <code>100</code>

{get_text('capacity_zero_unlimited', lang)}
"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('cancel', lang)}", callback_data="edit_country_capacity")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(capacity_text, reply_markup=reply_markup, parse_mode='HTML')

def setup_countries_handlers(app):
    """إعداد معالجات الدول"""
    from telegram.ext import CallbackQueryHandler
    
    # تاريخ السحوبات
    app.add_handler(CallbackQueryHandler(show_withdrawals_history, pattern="^withdrawals_history$"))
    app.add_handler(CallbackQueryHandler(show_approved_withdrawals, pattern="^approved_withdrawals_"))
    app.add_handler(CallbackQueryHandler(show_rejected_withdrawals, pattern="^rejected_withdrawals_"))
    
    # إدارة الدول
    app.add_handler(CallbackQueryHandler(add_country_prompt, pattern="^add_country$"))
    app.add_handler(CallbackQueryHandler(edit_country_select, pattern="^edit_country$"))
    app.add_handler(CallbackQueryHandler(edit_country_data_prompt, pattern="^edit_country_data_"))
    app.add_handler(CallbackQueryHandler(delete_country_select, pattern="^delete_country$"))
    app.add_handler(CallbackQueryHandler(confirm_delete_country, pattern="^confirm_delete_country_"))
    app.add_handler(CallbackQueryHandler(edit_country_flag_select, pattern="^edit_country_flag$"))
    app.add_handler(CallbackQueryHandler(edit_country_flag_prompt, pattern="^edit_flag_"))
    app.add_handler(CallbackQueryHandler(edit_country_capacity_select, pattern="^edit_country_capacity$"))
    app.add_handler(CallbackQueryHandler(edit_country_capacity_prompt, pattern="^edit_capacity_"))
