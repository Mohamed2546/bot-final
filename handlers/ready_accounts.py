from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telethon import TelegramClient
from telethon.sessions import StringSession
import database
import json
import asyncio
from datetime import datetime
from translations import get_text

async def show_ready_accounts_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الدول المتاحة للحسابات الجاهزة"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    countries = database.get_countries_with_ready_accounts()
    
    if not countries:
        await query.edit_message_text(
            f"⚠️ **{get_text('no_ready_accounts', lang)}**\n\n"
            f"{get_text('try_later', lang)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(get_text('back', lang), callback_data="back_to_main_menu")
            ]])
        )
        return
    
    keyboard = []
    
    for country in countries:
        country_code = country[0]
        country_name = country[1]
        flag = country[2]
        price = country[3]
        available_count = country[4]
        
        button_text = f"{flag} {country_name} - ${price:.2f} ({available_count} {get_text('available', lang)})"
        keyboard.append([InlineKeyboardButton(
            button_text, 
            callback_data=f"ready_country_{country_code}"
        )])
    
    keyboard.append([InlineKeyboardButton(get_text('back', lang), callback_data="back_to_main_menu")])
    
    await query.edit_message_text(
        f"🛒 **{get_text('buy_ready_accounts', lang)}**\n\n"
        f"{get_text('select_country', lang)}:\n\n"
        f"💰 {get_text('price_quantity', lang)}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_ready_account_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض تفاصيل حساب جاهز من دولة معينة"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    country_code = query.data.replace("ready_country_", "")
    
    accounts = database.get_available_ready_accounts_by_country(country_code)
    
    if not accounts:
        await query.edit_message_text(
            f"⚠️ **{get_text('no_accounts_country', lang)}**",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(get_text('back', lang), callback_data="show_ready_accounts")
            ]])
        )
        return
    
    account = accounts[0]
    account_id = account[0]
    phone_number = account[2]
    created_at = account[8]
    
    price = database.get_ready_account_price(country_code)
    country = database.get_country(country_code)
    country_name = country[1] if country else get_text('unknown', lang)
    flag = country[6] if country else ""
    
    user_balance = database.get_user(update.effective_user.id)
    balance = user_balance[2] if user_balance else 0.0
    
    created_date = datetime.fromisoformat(created_at).strftime("%Y-%m-%d %H:%M")
    
    balance_status = get_text('balance_sufficient', lang) if balance >= price else get_text('balance_insufficient_purchase', lang)
    balance_emoji = "✅" if balance >= price else "❌"
    
    await query.edit_message_text(
        f"📱 **{get_text('account_details_title', lang)}**\n\n"
        f"{flag} **{get_text('country', lang)}:** {country_name}\n"
        f"📞 **{get_text('phone_number', lang)}:** `{phone_number}`\n"
        f"📅 **{get_text('date_added', lang)}:** {created_date}\n\n"
        f"💰 **{get_text('price', lang)}:** ${price:.2f}\n"
        f"💵 **{get_text('current_balance', lang)}:** ${balance:.2f}\n\n"
        f"{balance_emoji} {balance_status}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"✅ {get_text('buy_now', lang)}", callback_data=f"buy_ready_{account_id}")],
            [InlineKeyboardButton(get_text('back', lang), callback_data="show_ready_accounts")]
        ])
    )

async def purchase_ready_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شراء حساب جاهز"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    account_id = int(query.data.replace("buy_ready_", ""))
    username = update.effective_user.username
    
    success, result = database.purchase_ready_account(user_id, username, account_id)
    
    if not success:
        await query.edit_message_text(
            f"❌ **{get_text('purchase_failed', lang)}**\n\n"
            f"{get_text('reason', lang)}: {result}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(get_text('back', lang), callback_data="show_ready_accounts")
            ]])
        )
        return
    
    purchase_id = result
    purchase = database.get_user_purchase(purchase_id)
    
    phone_number = purchase[3]
    session_string = purchase[5]
    price = purchase[6]
    balance_after = purchase[8]
    purchased_at = datetime.fromisoformat(purchase[10]).strftime("%Y-%m-%d %H:%M")
    
    await query.edit_message_text(
        f"⏳ **{get_text('processing_purchase', lang)}**\n\n"
        f"📱 {phone_number}\n"
        f"{get_text('please_wait', lang)}..."
    )
    
    try:
        device_info = json.loads(purchase[14]) if purchase[14] else None
        
        import config
        
        client = TelegramClient(
            StringSession(session_string),
            api_id=config.TELETHON_API_ID,
            api_hash=config.TELETHON_API_HASH,
            device_model=device_info.get('device_model', 'Unknown') if device_info else 'Unknown',
            system_version=device_info.get('system_version', 'Unknown') if device_info else 'Unknown',
            app_version=device_info.get('app_version', '10.0.0') if device_info else '10.0.0'
        )
        
        await client.connect()
        
        if await client.is_user_authorized():
            password_2fa = database.get_setting('2fa_password', config.TWO_FA_PASSWORD)
            try:
                await client.edit_2fa(
                    current_password=password_2fa,
                    new_password=None
                )
                print(f"✅ تم حذف 2FA من الحساب {phone_number} بنجاح")
            except Exception as e:
                error_msg = str(e).lower()
                if 'no password' in error_msg or 'not set' in error_msg:
                    print(f"ℹ️ الحساب {phone_number} لا يحتوي على 2FA بالفعل")
                else:
                    print(f"⚠️ فشل حذف 2FA من الحساب {phone_number}: {e}")
        
        await client.disconnect()
    except Exception as e:
        print(f"❌ خطأ في معالجة الحساب {phone_number}: {e}")
    
    await query.edit_message_text(
        f"✅ **{get_text('purchase_completed', lang)}**\n\n"
        f"📱 **{get_text('phone_number', lang)}:** `{phone_number}`\n"
        f"💰 **{get_text('amount_paid', lang)}:** ${price:.2f}\n"
        f"💵 **{get_text('new_balance', lang)}:** ${balance_after:.2f}\n"
        f"📅 **{get_text('purchase_date', lang)}:** {purchased_at}\n\n"
        f"⚠️ **{get_text('warning', lang)}:** {get_text('register_first', lang)}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📩 {get_text('request_code_btn', lang)}", callback_data=f"request_code_{purchase_id}")],
            [InlineKeyboardButton(get_text('back_main_menu', lang), callback_data="back_to_main_menu")]
        ])
    )

async def request_login_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب كود الدخول للحساب المشترى"""
    query = update.callback_query
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    await query.answer(get_text('searching_code', lang))
    
    purchase_id = int(query.data.replace("request_code_", ""))
    purchase = database.get_user_purchase(purchase_id)
    
    if not purchase:
        await query.edit_message_text(f"❌ {get_text('purchase_not_found', lang)}")
        return
    
    phone_number = purchase[3]
    session_string = purchase[5]
    
    await query.edit_message_text(
        f"🔍 **{get_text('searching_login_code', lang)}**\n\n"
        f"{get_text('please_wait', lang)}..."
    )
    
    try:
        device_info = json.loads(purchase[14]) if purchase[14] else None
        
        import config
        
        client = TelegramClient(
            StringSession(session_string),
            api_id=config.TELETHON_API_ID,
            api_hash=config.TELETHON_API_HASH,
            device_model=device_info.get('device_model', 'Unknown') if device_info else 'Unknown',
            system_version=device_info.get('system_version', 'Unknown') if device_info else 'Unknown',
            app_version=device_info.get('app_version', '10.0.0') if device_info else '10.0.0'
        )
        
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            await query.edit_message_text(
                f"❌ **{get_text('session_invalid', lang)}**\n\n"
                f"{get_text('contact_support_msg', lang)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(get_text('back', lang), callback_data="back_to_main_menu")
                ]])
            )
            return
        
        login_code = None
        found_messages = []
        
        try:
            messages = await client.get_messages(777000, limit=30)
            for msg in messages:
                if msg.text:
                    found_messages.append(f"📩 {msg.text[:100]}")
                    
                    import re
                    code_patterns = [
                        r'Login code:\s*([0-9]{5})',
                        r'code:\s*([0-9]{5})',
                        r'كود:\s*([0-9]{5})',
                        r'رمز:\s*([0-9]{5})',
                        r'\b([0-9]{5})\b'
                    ]
                    
                    for pattern in code_patterns:
                        match = re.search(pattern, msg.text, re.IGNORECASE)
                        if match:
                            potential_code = match.group(1)
                            if potential_code.isdigit() and len(potential_code) == 5:
                                login_code = potential_code
                                break
                    
                    if login_code:
                        break
        except Exception as e:
            print(f"Error reading messages from 777000: {e}")
        
        if not login_code:
            try:
                dialogs = await client.get_dialogs(limit=15)
                for dialog in dialogs:
                    try:
                        messages = await client.get_messages(dialog.entity, limit=10)
                        for msg in messages:
                            if msg.text:
                                import re
                                code_match = re.search(r'\b([0-9]{5})\b', msg.text)
                                if code_match and any(keyword in msg.text.lower() for keyword in ['code', 'login', 'كود', 'رمز', 'تسجيل']):
                                    login_code = code_match.group(1)
                                    break
                        if login_code:
                            break
                    except:
                        continue
            except Exception as e:
                print(f"Error searching in dialogs: {e}")
        
        await client.disconnect()
        
        if login_code:
            database.update_purchase_code(purchase_id, login_code)
            
            await query.edit_message_text(
                f"✅ **{get_text('code_found', lang)}**\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🔐 **{get_text('login_code', lang)}:**\n\n"
                f"        <b><u>{login_code}</u></b>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📱 {get_text('use_code_telegram', lang)}\n\n"
                f"⚠️ **{get_text('logout_question', lang)}**\n"
                f"{get_text('logout_description', lang)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"🚪 {get_text('logout_btn', lang)}", callback_data=f"logout_account_{purchase_id}")],
                    [InlineKeyboardButton(get_text('back', lang), callback_data="back_to_main_menu")]
                ])
            )
        else:
            await query.edit_message_text(
                f"⚠️ **{get_text('code_not_found', lang)}**\n\n"
                f"{get_text('code_may_not_arrived', lang)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"🔄 {get_text('retry', lang)}", callback_data=f"request_code_{purchase_id}")],
                    [InlineKeyboardButton(get_text('back', lang), callback_data="back_to_main_menu")]
                ])
            )
    
    except Exception as e:
        await query.edit_message_text(
            f"❌ **{get_text('error_searching_code', lang)}**\n\n"
            f"{get_text('try_later_support', lang)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(get_text('back', lang), callback_data="back_to_main_menu")
            ]])
        )

async def logout_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تسجيل خروج من الحساب المشترى"""
    query = update.callback_query
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    await query.answer(get_text('logging_out', lang))
    
    purchase_id = int(query.data.replace("logout_account_", ""))
    purchase = database.get_user_purchase(purchase_id)
    
    if not purchase:
        await query.edit_message_text(f"❌ {get_text('purchase_not_found', lang)}")
        return
    
    session_string = purchase[5]
    
    try:
        device_info = json.loads(purchase[14]) if purchase[14] else None
        
        import config
        
        client = TelegramClient(
            StringSession(session_string),
            api_id=config.TELETHON_API_ID,
            api_hash=config.TELETHON_API_HASH,
            device_model=device_info.get('device_model', 'Unknown') if device_info else 'Unknown',
            system_version=device_info.get('system_version', 'Unknown') if device_info else 'Unknown',
            app_version=device_info.get('app_version', '10.0.0') if device_info else '10.0.0'
        )
        
        await client.connect()
        
        if await client.is_user_authorized():
            await client.log_out()
        
        await client.disconnect()
        
        database.logout_purchased_account(purchase_id)
        
        await query.edit_message_text(
            f"✅ **{get_text('logout_success', lang)}**\n\n"
            f"{get_text('account_yours_only', lang)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(get_text('back_main_menu', lang), callback_data="back_to_main_menu")
            ]])
        )
    
    except Exception as e:
        await query.edit_message_text(
            f"❌ **{get_text('error_logout', lang)}**\n\n"
            f"{get_text('try_later', lang)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(get_text('back', lang), callback_data="back_to_main_menu")
            ]])
        )

async def show_balance_recharge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات شحن الرصيد"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = database.get_user_language(user_id)
    
    support_username = database.get_setting('support_username', '@Support')
    
    await query.edit_message_text(
        f"💳 **{get_text('recharge_title', lang)}**\n\n"
        f"{get_text('recharge_message', lang)}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📞 {get_text('contact_support', lang)}", url=f"https://t.me/{support_username.replace('@', '')}")],
            [InlineKeyboardButton(get_text('back', lang), callback_data="back_to_main_menu")]
        ])
    )

def setup_ready_accounts_handlers(app):
    """تسجيل handlers الحسابات الجاهزة"""
    app.add_handler(CallbackQueryHandler(show_ready_accounts_countries, pattern="^show_ready_accounts$"))
    app.add_handler(CallbackQueryHandler(show_ready_account_details, pattern="^ready_country_"))
    app.add_handler(CallbackQueryHandler(purchase_ready_account, pattern="^buy_ready_"))
    app.add_handler(CallbackQueryHandler(request_login_code, pattern="^request_code_"))
    app.add_handler(CallbackQueryHandler(logout_account, pattern="^logout_account_"))
    app.add_handler(CallbackQueryHandler(show_balance_recharge, pattern="^show_balance_recharge$"))
