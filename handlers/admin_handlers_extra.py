"""
وظائف إضافية للوحة التحكم - معالجات الإدخالات والعمليات المعقدة
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database
import config
import sqlite3
from datetime import datetime
import io
import zipfile
import json
import asyncio
from translations import get_text

# ==================== معالجة البحث عن مستخدم ====================
async def search_user_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب اليوزر أو الآي دي للبحث"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    context.user_data['admin_action'] = 'search_user'
    
    search_text = f"""
╔═══════════════════════════╗
║   🔍 <b>{get_text('search_user_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('send_username_or_id', lang)}

{get_text('add_country_example', lang)}
{get_text('example_username', lang)}
{get_text('example_id', lang)}
"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('cancel', lang)}", callback_data="admin_users")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(search_text, reply_markup=reply_markup, parse_mode='HTML')

async def search_user_result(update: Update, context: ContextTypes.DEFAULT_TYPE, search_term):
    """عرض نتائج البحث عن مستخدم"""
    import logging
    logger = logging.getLogger(__name__)
    
    admin_id = update.effective_user.id
    lang = database.get_user_language(admin_id)
    
    logger.info(f"🔍 البحث عن: {search_term}")
    
    conn = sqlite3.connect('bot.db')
    try:
        cursor = conn.cursor()
        
        if search_term.startswith('@'):
            username = search_term[1:]
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        else:
            try:
                user_id = int(search_term)
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            except ValueError:
                await update.message.reply_text(f"❌ {get_text('invalid_username_id', lang)}")
                return
        
        user = cursor.fetchone()
        
        if not user:
            logger.info(f"❌ المستخدم غير موجود: {search_term}")
            await update.message.reply_text(f"❌ {get_text('user_not_found', lang)}")
            return
        
        logger.info(f"✅ تم العثور على المستخدم: {user[0]}")
        
        user_id, username, balance, total_earnings, subscribed, passed_captcha, completed_onboarding, created_at, language = user
        
        cursor.execute('SELECT COUNT(*) FROM accounts WHERE user_id = ? AND status = "approved"', (user_id,))
        successful = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM account_reviews WHERE user_id = ? AND status = "rejected"', (user_id,))
        failed = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM account_reviews WHERE user_id = ? AND status = "pending"', (user_id,))
        pending = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM withdrawals WHERE user_id = ? AND status = 'pending'", (user_id,))
        pending_withdrawals = cursor.fetchone()[0]
        
        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM withdrawals WHERE user_id = ? AND status = 'approved'", (user_id,))
        total_withdrawn = cursor.fetchone()[0]
        
        cursor.execute('SELECT user_id FROM banned_users WHERE user_id = ?', (user_id,))
        is_banned = cursor.fetchone() is not None
        
        cursor.execute('''
            SELECT phone_number 
            FROM accounts 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 10
        ''', (user_id,))
        recent_accounts = cursor.fetchall()
    finally:
        conn.close()
    
    status_text = f"❌ {get_text('banned_status', lang)}" if is_banned else f"✅ {get_text('active_status', lang)}"
    
    result_text = f"""
╔═══════════════════════════╗
║   👤 <b>{get_text('user_data_title', lang)}</b>   ║
╚═══════════════════════════╝

👤 <b>{get_text('username_label', lang)}</b> @{username or get_text('no_username', lang)}
🆔 <b>{get_text('id_label', lang)}</b> <code>{user_id}</code>
💰 <b>{get_text('balance_short', lang)}</b> ${balance:.2f}
📊 <b>{get_text('status_label', lang)}</b> {status_text}
📅 <b>{get_text('join_date', lang)}</b> {created_at[:10]}

💸 <b>{get_text('withdrawals_section', lang)}</b>
├─ ⏳ {get_text('pending_short', lang)} {pending_withdrawals}
└─ ✅ {get_text('withdrawn_total', lang)} ${total_withdrawn:.2f}

📱 <b>{get_text('accounts_section', lang)}</b>
├─ ✅ {get_text('successful_short', lang)} {successful}
├─ ❌ {get_text('failed_short', lang)} {failed}
└─ ⏳ {get_text('pending_review_short', lang)} {pending}

📋 <b>{get_text('last_10_accounts', lang)}</b>
"""
    
    if recent_accounts:
        for idx, (phone,) in enumerate(recent_accounts, 1):
            result_text += f"{idx}. <code>{phone}</code>\n"
    else:
        result_text += f"{get_text('no_accounts_registered', lang)}\n"
    
    keyboard = [
        [InlineKeyboardButton(f"📤 {get_text('export_sessions_btn', lang)}", callback_data=f"export_user_sessions_{user_id}")],
        [InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data="admin_users")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    logger.info(f"📤 إرسال نتائج البحث للمستخدم {user_id}")
    await update.message.reply_text(result_text, reply_markup=reply_markup, parse_mode='HTML')
    logger.info(f"✅ تم إرسال نتائج البحث بنجاح")

# ==================== معالجة الرصيد ====================
async def balance_control_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قائمة التحكم في الرصيد"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    balance_text = f"""
╔═══════════════════════════╗
║   💰 <b>{get_text('balance_control_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('choose_operation', lang)}
"""
    
    keyboard = [
        [InlineKeyboardButton(f"➕ {get_text('add_balance_btn', lang)}", callback_data="add_balance")],
        [InlineKeyboardButton(f"➖ {get_text('subtract_balance_btn', lang)}", callback_data="subtract_balance")],
        [InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data="admin_users")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(balance_text, reply_markup=reply_markup, parse_mode='HTML')

async def add_balance_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب بيانات إضافة الرصيد"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    context.user_data['admin_action'] = 'add_balance'
    
    prompt_text = f"""
╔═══════════════════════════╗
║   ➕ <b>{get_text('add_balance_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('send_data_format', lang)}
<code>user_id amount</code>

{get_text('balance_example', lang)}
"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('cancel', lang)}", callback_data="balance_control")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(prompt_text, reply_markup=reply_markup, parse_mode='HTML')

async def subtract_balance_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب بيانات خصم الرصيد"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    context.user_data['admin_action'] = 'subtract_balance'
    
    prompt_text = f"""
╔═══════════════════════════╗
║   ➖ <b>{get_text('subtract_balance_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('send_data_format', lang)}
<code>user_id amount</code>

{get_text('balance_example', lang)}
"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('cancel', lang)}", callback_data="balance_control")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(prompt_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== معالجة الحظر ====================
async def ban_user_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب بيانات حظر المستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    context.user_data['admin_action'] = 'ban_user'
    
    ban_text = f"""
╔═══════════════════════════╗
║   🚫 <b>{get_text('ban_user_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('send_user_id', lang)}
{get_text('id_example', lang)}
"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('cancel', lang)}", callback_data="admin_users")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(ban_text, reply_markup=reply_markup, parse_mode='HTML')

async def unban_user_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب بيانات فك حظر المستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    context.user_data['admin_action'] = 'unban_user'
    
    unban_text = f"""
╔═══════════════════════════╗
║   ✅ <b>{get_text('unban_user_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('send_user_id', lang)}
{get_text('id_example', lang)}
"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('cancel', lang)}", callback_data="admin_users")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(unban_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== معالجة الأدمنز ====================
async def add_admin_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب بيانات إضافة أدمن"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    context.user_data['admin_action'] = 'add_admin'
    
    add_admin_text = f"""
╔═══════════════════════════╗
║   ➕ <b>{get_text('add_admin_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('send_user_id', lang)}
{get_text('id_example', lang)}
"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('cancel', lang)}", callback_data="manage_admins")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(add_admin_text, reply_markup=reply_markup, parse_mode='HTML')

async def remove_admin_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب بيانات حذف أدمن"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    context.user_data['admin_action'] = 'remove_admin'
    
    remove_admin_text = f"""
╔═══════════════════════════╗
║   ➖ <b>{get_text('remove_admin_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('send_admin_id', lang)}
{get_text('id_example', lang)}
"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('cancel', lang)}", callback_data="manage_admins")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(remove_admin_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== معالجة البروكسيات ====================
async def add_proxy_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب بيانات إضافة بروكسي"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    context.user_data['admin_action'] = 'add_proxy'
    
    add_proxy_text = f"""
╔═══════════════════════════╗
║   ➕ <b>{get_text('add_proxy_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('send_proxy_format', lang)}
{get_text('proxy_format', lang)}

{get_text('proxy_example', lang)}
"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('cancel', lang)}", callback_data="manage_proxies")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(add_proxy_text, reply_markup=reply_markup, parse_mode='HTML')

async def remove_proxy_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب بيانات حذف بروكسي"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    context.user_data['admin_action'] = 'remove_proxy'
    
    remove_proxy_text = f"""
╔═══════════════════════════╗
║   ➖ <b>{get_text('remove_proxy_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('send_proxy_id', lang)}
{get_text('proxy_id_example', lang)}
"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('cancel', lang)}", callback_data="manage_proxies")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(remove_proxy_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== معالجة الرسائل ====================
async def broadcast_message_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب الرسالة الجماعية"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    context.user_data['admin_action'] = 'broadcast_message'
    
    broadcast_text = f"""
╔═══════════════════════════╗
║   📢 <b>{get_text('broadcast_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('send_broadcast_message', lang)}

{get_text('html_formatting_hint', lang)}
"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('cancel', lang)}", callback_data="admin_messages")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(broadcast_text, reply_markup=reply_markup, parse_mode='HTML')

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text):
    """إرسال رسالة جماعية"""
    admin_id = update.effective_user.id
    lang = database.get_user_language(admin_id)
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()
    
    sent = 0
    failed = 0
    
    status_msg = await update.message.reply_text(f"📤 {get_text('sending_in_progress', lang)}\n✅ {get_text('sent_label', lang)} {sent}\n❌ {get_text('failed_label', lang)} {failed}")
    
    for (user_id,) in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message_text, parse_mode='HTML')
            sent += 1
            
            if sent % 10 == 0:
                await status_msg.edit_text(f"📤 {get_text('sending_in_progress', lang)}\n✅ {get_text('sent_label', lang)} {sent}\n❌ {get_text('failed_label', lang)} {failed}")
            
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    
    await status_msg.edit_text(f"✅ <b>{get_text('sending_complete', lang)}</b>\n\n📊 {get_text('statistics_label', lang)}\n✅ {get_text('sent_count', lang)} {sent}\n❌ {get_text('failed_label', lang)} {failed}", parse_mode='HTML')

async def send_user_message_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب بيانات إرسال رسالة لمستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    context.user_data['admin_action'] = 'send_user_message_step1'
    
    send_msg_text = f"""
╔═══════════════════════════╗
║   📤 <b>{get_text('send_user_message_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('send_user_id_username', lang)}
{get_text('username_or_id_example', lang)}
"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('cancel', lang)}", callback_data="admin_messages")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(send_msg_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== معالجة مراجعة السحوبات ====================
async def review_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض تفاصيل طلب سحب"""
    query = update.callback_query
    await query.answer()
    
    admin_id = query.from_user.id
    lang = database.get_user_language(admin_id)
    
    withdrawal_id = int(query.data.split('_')[-1])
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, username, amount, wallet_address, wallet_name, created_at
        FROM withdrawals
        WHERE id = ?
    ''', (withdrawal_id,))
    
    withdrawal = cursor.fetchone()
    conn.close()
    
    if not withdrawal:
        await query.edit_message_text(f"❌ {get_text('withdrawal_not_found', lang)}")
        return
    
    user_id, username, amount, wallet_address, wallet_name, created_at = withdrawal
    
    withdrawal_text = f"""
╔═══════════════════════════╗
║   💸 <b>{get_text('withdrawal_details_title', lang)}</b>   ║
╚═══════════════════════════╝

👤 <b>{get_text('user_label', lang)}</b> @{username or user_id}
🆔 <b>{get_text('id_label', lang)}</b> <code>{user_id}</code>
💰 <b>{get_text('amount_short', lang)}</b> ${amount}
📍 <b>{get_text('wallet_short', lang)}</b> {wallet_name}
📝 <b>{get_text('address_label', lang)}</b> <code>{wallet_address}</code>
📅 <b>{get_text('date_short', lang)}</b> {created_at}

{get_text('choose_action', lang)}
"""
    
    keyboard = [
        [InlineKeyboardButton(f"✅ {get_text('approve_btn', lang)}", callback_data=f"approve_withdrawal_{withdrawal_id}")],
        [InlineKeyboardButton(f"❌ {get_text('reject_btn', lang)}", callback_data=f"reject_withdrawal_{withdrawal_id}")],
        [InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data="pending_withdrawals")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(withdrawal_text, reply_markup=reply_markup, parse_mode='HTML')

async def approve_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الموافقة على طلب سحب"""
    query = update.callback_query
    
    admin_id = query.from_user.id
    lang = database.get_user_language(admin_id)
    
    await query.answer(f"✅ {get_text('withdrawal_approved', lang)}")
    
    withdrawal_id = int(query.data.split('_')[-1])
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id, amount FROM withdrawals WHERE id = ?', (withdrawal_id,))
    user_id, amount = cursor.fetchone()
    
    cursor.execute('UPDATE withdrawals SET status = ?, admin_id = ?, processed_at = ? WHERE id = ?',
                  ('approved', admin_id, datetime.now().isoformat(), withdrawal_id))
    
    cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, user_id))
    
    conn.commit()
    conn.close()
    
    # Get user's language for notification
    user_lang = database.get_user_language(user_id)
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ <b>{get_text('withdrawal_approved_msg', user_lang)}</b>\n\n💰 {get_text('amount_short', user_lang)} ${amount}\n\n🎉 {get_text('transfer_soon', user_lang)}",
            parse_mode='HTML'
        )
    except:
        pass
    
    await query.edit_message_text(f"✅ {get_text('approval_complete', lang)}")

async def reject_withdrawal_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب سبب الرفض"""
    query = update.callback_query
    await query.answer()
    
    admin_id = query.from_user.id
    lang = database.get_user_language(admin_id)
    
    withdrawal_id = query.data.split('_')[-1]
    context.user_data['admin_action'] = f'reject_withdrawal_{withdrawal_id}'
    
    reject_text = f"""
╔═══════════════════════════╗
║   ❌ <b>{get_text('reject_withdrawal_title', lang)}</b>   ║
╚═══════════════════════════╝

{get_text('send_rejection_reason', lang)}
"""
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('cancel', lang)}", callback_data="pending_withdrawals")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(reject_text, reply_markup=reply_markup, parse_mode='HTML')

def setup_extra_handlers(app):
    """إعداد المعالجات الإضافية"""
    from telegram.ext import CallbackQueryHandler
    
    # البحث
    app.add_handler(CallbackQueryHandler(search_user_prompt, pattern="^search_user$"))
    
    # الرصيد
    app.add_handler(CallbackQueryHandler(balance_control_menu, pattern="^balance_control$"))
    app.add_handler(CallbackQueryHandler(add_balance_prompt, pattern="^add_balance$"))
    app.add_handler(CallbackQueryHandler(subtract_balance_prompt, pattern="^subtract_balance$"))
    
    # الحظر
    app.add_handler(CallbackQueryHandler(ban_user_prompt, pattern="^ban_user$"))
    app.add_handler(CallbackQueryHandler(unban_user_prompt, pattern="^unban_user$"))
    
    # الأدمنز
    app.add_handler(CallbackQueryHandler(add_admin_prompt, pattern="^add_admin$"))
    app.add_handler(CallbackQueryHandler(remove_admin_prompt, pattern="^remove_admin$"))
    
    # البروكسيات
    app.add_handler(CallbackQueryHandler(add_proxy_prompt, pattern="^add_proxy$"))
    app.add_handler(CallbackQueryHandler(remove_proxy_prompt, pattern="^remove_proxy$"))
    
    # الرسائل
    app.add_handler(CallbackQueryHandler(broadcast_message_prompt, pattern="^broadcast_message$"))
    app.add_handler(CallbackQueryHandler(send_user_message_prompt, pattern="^send_user_message$"))
    
    # السحوبات
    app.add_handler(CallbackQueryHandler(review_withdrawal, pattern="^review_withdrawal_"))
    app.add_handler(CallbackQueryHandler(approve_withdrawal, pattern="^approve_withdrawal_"))
    app.add_handler(CallbackQueryHandler(reject_withdrawal_prompt, pattern="^reject_withdrawal_"))
