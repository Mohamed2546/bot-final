from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
import database
from datetime import datetime
import config
from translations import get_text

async def show_ready_accounts_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض لوحة التحكم في الحسابات الجاهزة"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    if user_id != config.ADMIN_ID and not database.is_admin(user_id):
        await query.answer(f"⛔ {get_text('not_authorized', lang)}", show_alert=True)
        return
    
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton(f"💲 {get_text('edit_prices', lang)}", callback_data="ready_edit_prices")],
        [InlineKeyboardButton(f"➕ {get_text('add_ready_accounts', lang)}", callback_data="ready_add_accounts")],
        [InlineKeyboardButton(f"🔄 {get_text('import_connected_accounts', lang)}", callback_data="ready_import_connected")],
        [InlineKeyboardButton(f"🔗 {get_text('api_link', lang)}", callback_data="ready_api_link")],
        [InlineKeyboardButton(f"📊 {get_text('statistics', lang)}", callback_data="ready_stats")],
        [InlineKeyboardButton(f"🔍 {get_text('search_number', lang)}", callback_data="ready_search")],
        [InlineKeyboardButton(f"🔙 {get_text('back_admin', lang)}", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text(
        f"🎛 **{get_text('ready_accounts_control', lang)}**\n\n"
        f"{get_text('choose_from_menu', lang)}:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_ready_prices_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الدول لتعديل الأسعار"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id != config.ADMIN_ID and not database.is_admin(user_id):
        await query.answer("⛔ غير مصرح لك", show_alert=True)
        return
    
    await query.answer()
    
    import sqlite3
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM countries WHERE is_active = TRUE')
    countries = cursor.fetchall()
    conn.close()
    
    if not countries:
        await query.edit_message_text(
            "⚠️ لا توجد دول متاحة",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="ready_admin_panel")
            ]])
        )
        return
    
    keyboard = []
    for country in countries:
        country_code = country[0]
        country_name = country[1]
        flag = country[6]
        current_price = database.get_ready_account_price(country_code)
        available_count = database.get_ready_accounts_count_by_country(country_code)
        
        button_text = f"{flag} {country_name} - ${current_price:.2f} ({available_count} متاح)"
        keyboard.append([InlineKeyboardButton(
            button_text, 
            callback_data=f"ready_edit_price_{country_code}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="ready_admin_panel")])
    
    await query.edit_message_text(
        "💲 **تعديل أسعار الحسابات الجاهزة**\n\n"
        "اختر الدولة لتعديل سعرها:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def prompt_new_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب السعر الجديد"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id != config.ADMIN_ID and not database.is_admin(user_id):
        await query.answer("⛔ غير مصرح لك", show_alert=True)
        return
    
    await query.answer()
    
    country_code = query.data.replace("ready_edit_price_", "")
    country = database.get_country(country_code)
    
    if not country:
        await query.edit_message_text("❌ الدولة غير موجودة")
        return
    
    country_name = country[1]
    flag = country[6]
    current_price = database.get_ready_account_price(country_code)
    
    context.user_data['admin_action'] = 'ready_set_price'
    context.user_data['ready_country_code'] = country_code
    
    await query.edit_message_text(
        f"💲 **تعديل سعر {flag} {country_name}**\n\n"
        f"السعر الحالي: ${current_price:.2f}\n\n"
        f"📝 أرسل السعر الجديد (بالدولار):",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ إلغاء", callback_data="ready_edit_prices")
        ]])
    )

async def show_ready_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات الحسابات الجاهزة"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id != config.ADMIN_ID and not database.is_admin(user_id):
        await query.answer("⛔ غير مصرح لك", show_alert=True)
        return
    
    await query.answer()
    
    stats = database.get_total_purchases_stats()
    
    page = int(query.data.replace("ready_stats_page_", "").replace("ready_stats", "0"))
    
    purchases = database.get_all_purchases(limit=5, offset=page*5)
    
    stats_text = (
        f"📊 **إحصائيات الحسابات المباعة**\n\n"
        f"🔢 عدد الحسابات المباعة: {stats['total_sold']}\n"
        f"👥 عدد المشترين: {stats['total_buyers']}\n"
        f"💰 إجمالي الرصيد المدفوع: ${stats['total_revenue']:.2f}\n\n"
    )
    
    if purchases:
        stats_text += "📋 **آخر المشتريات:**\n\n"
        for purchase in purchases:
            purchase_id = purchase[0]
            username = purchase[2] or "غير معروف"
            phone = purchase[3]
            price = purchase[6]
            purchased_at = datetime.fromisoformat(purchase[10]).strftime("%Y-%m-%d")
            login_code = purchase[9] or "لم يُطلب"
            
            stats_text += (
                f"🆔 **ID:** {purchase_id}\n"
                f"👤 **المشتري:** @{username}\n"
                f"📱 **الرقم:** `{phone}`\n"
                f"💰 **السعر:** ${price:.2f}\n"
                f"🔐 **الكود:** `{login_code}`\n"
                f"📅 **التاريخ:** {purchased_at}\n"
                f"{'─'*30}\n"
            )
    
    keyboard = []
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"ready_stats_page_{page-1}"))
    if len(purchases) == 5:
        nav_buttons.append(InlineKeyboardButton("التالي ▶️", callback_data=f"ready_stats_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="ready_admin_panel")])
    
    await query.edit_message_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def prompt_search_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب رقم الهاتف للبحث"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id != config.ADMIN_ID and not database.is_admin(user_id):
        await query.answer("⛔ غير مصرح لك", show_alert=True)
        return
    
    await query.answer()
    
    context.user_data['admin_action'] = 'ready_search_phone'
    
    await query.edit_message_text(
        "🔍 **البحث عن رقم**\n\n"
        "📝 أرسل رقم الهاتف (مع كود الدولة):",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ إلغاء", callback_data="ready_admin_panel")
        ]])
    )

async def show_ready_add_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض خيارات إضافة حسابات جاهزة"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id != config.ADMIN_ID and not database.is_admin(user_id):
        await query.answer("⛔ غير مصرح لك", show_alert=True)
        return
    
    await query.answer()
    
    await query.edit_message_text(
        "➕ **إضافة حسابات جاهزة**\n\n"
        "اختر طريقة الإضافة:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📁 رفع ملف جلسات", callback_data="ready_upload_sessions")],
            [InlineKeyboardButton("✏️ إضافة يدوية", callback_data="ready_manual_add")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="ready_admin_panel")]
        ])
    )

async def prompt_upload_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب رفع ملف الجلسات"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id != config.ADMIN_ID and not database.is_admin(user_id):
        await query.answer("⛔ غير مصرح لك", show_alert=True)
        return
    
    await query.answer()
    
    context.user_data['admin_action'] = 'ready_upload_sessions'
    
    await query.edit_message_text(
        "📁 **رفع ملف جلسات**\n\n"
        "📝 أرسل ملف الجلسات بصيغة:\n"
        "- JSON: قائمة بالجلسات\n"
        "- TXT: كل سطر session string\n\n"
        "مثال JSON:\n"
        "```json\n"
        '[\n'
        '  {"phone": "+201234567890", "session": "string_here"},\n'
        '  {"phone": "+966123456789", "session": "string_here"}\n'
        ']\n'
        "```",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ إلغاء", callback_data="ready_add_accounts")
        ]])
    )

async def prompt_manual_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب إضافة حساب يدوياً"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id != config.ADMIN_ID and not database.is_admin(user_id):
        await query.answer("⛔ غير مصرح لك", show_alert=True)
        return
    
    await query.answer()
    
    context.user_data['admin_action'] = 'ready_manual_add'
    
    await query.edit_message_text(
        "✏️ **إضافة حساب يدوياً**\n\n"
        "📝 أرسل بيانات الحساب بالصيغة:\n\n"
        "`رقم_الهاتف|session_string`\n\n"
        "مثال:\n"
        "`+201234567890|1AQAAAAAE...session_string_here`",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ إلغاء", callback_data="ready_add_accounts")
        ]])
    )

async def import_connected_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استيراد الأرقام المتصلة بالبوت إلى الحسابات الجاهزة"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = database.get_user_language(user_id)
    
    if user_id != config.ADMIN_ID and not database.is_admin(user_id):
        await query.answer(f"⛔ {get_text('not_authorized', lang)}", show_alert=True)
        return
    
    await query.answer()
    
    await query.edit_message_text(
        f"⏳ **{get_text('importing_numbers', lang)}**\n\n"
        f"{get_text('please_wait', lang)}..."
    )
    
    result = database.import_accounts_to_ready(user_id)
    
    message = (
        f"✅ **{get_text('import_success', lang)}**\n\n"
        f"📊 **{get_text('results', lang)}:**\n"
        f"✅ {get_text('imported_new', lang)}: {result['imported']} {get_text('new_number', lang)}\n"
        f"🔄 {get_text('restored_deleted', lang)}: {result['restored']} {get_text('deleted_number', lang)}\n"
        f"⚠️ {get_text('already_exists', lang)}: {result['already_exists']} {get_text('number', lang)}\n"
        f"🔍 {get_text('total_scanned', lang)}: {result['total_scanned']} {get_text('number', lang)}\n\n"
    )
    
    if result['imported'] > 0 or result['restored'] > 0:
        if result['imported'] > 0 and result['restored'] > 0:
            message += f"🎉 {get_text('import_restore_success', lang)}"
        elif result['imported'] > 0:
            message += f"🎉 {get_text('import_only_success', lang)}"
        else:
            message += f"🎉 {get_text('restore_only_success', lang)}"
    elif result['already_exists'] > 0:
        message += f"ℹ️ {get_text('all_numbers_exist', lang)}"
    else:
        message += f"⚠️ {get_text('no_numbers_to_import', lang)}"
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"🔙 {get_text('back', lang)}", callback_data="ready_admin_panel")
        ]])
    )

async def show_api_link_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض خيارات ربط API"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id != config.ADMIN_ID and not database.is_admin(user_id):
        await query.answer("⛔ غير مصرح لك", show_alert=True)
        return
    
    await query.answer()
    
    await query.edit_message_text(
        "🔗 **ربط API للحسابات الجاهزة**\n\n"
        "📝 أرسل رابط API بالصيغة:\n\n"
        "`https://api.example.com/accounts`\n\n"
        "⚠️ يجب أن يرجع API البيانات بصيغة JSON:\n"
        "```json\n"
        '[\n'
        '  {"phone": "+201234567890", "session": "string"},\n'
        '  {"phone": "+966123456789", "session": "string"}\n'
        ']\n'
        "```",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ إلغاء", callback_data="ready_admin_panel")]
        ])
    )
    
    context.user_data['admin_action'] = 'ready_api_link'

async def handle_admin_ready_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية للأدمن في نظام الحسابات الجاهزة"""
    user_id = update.effective_user.id
    
    if user_id != config.ADMIN_ID and not database.is_admin(user_id):
        return
    
    action = context.user_data.get('admin_action')
    
    if action == 'ready_set_price':
        try:
            new_price = float(update.message.text)
            if new_price < 0:
                await update.message.reply_text("❌ السعر يجب أن يكون موجب")
                return
            
            country_code = context.user_data.get('ready_country_code')
            database.set_ready_account_price(country_code, new_price)
            
            country = database.get_country(country_code)
            country_name = country[1]
            flag = country[6]
            
            await update.message.reply_text(
                f"✅ تم تحديث سعر {flag} {country_name}\n"
                f"السعر الجديد: ${new_price:.2f}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 رجوع", callback_data="ready_edit_prices")
                ]])
            )
            
            context.user_data.pop('admin_action', None)
            context.user_data.pop('ready_country_code', None)
        
        except ValueError:
            await update.message.reply_text("❌ يرجى إدخال رقم صحيح")
    
    elif action == 'ready_search_phone':
        phone_number = update.message.text.strip()
        result = database.search_ready_account_by_phone(phone_number)
        
        review = result['review']
        purchase = result['purchase']
        
        if not review and not purchase:
            await update.message.reply_text(
                "❌ **لم يتم العثور على الرقم**",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 رجوع", callback_data="ready_admin_panel")
                ]])
            )
            context.user_data.pop('admin_action', None)
            return
        
        result_text = f"🔍 **نتائج البحث عن:** `{phone_number}`\n\n"
        
        if review:
            review_status = review[3]
            created_at = datetime.fromisoformat(review[8]).strftime("%Y-%m-%d %H:%M")
            submitter_id = review[1]
            sold = review[10] if len(review) > 10 else False
            
            result_text += (
                f"📋 **معلومات في المراجعة:**\n"
                f"🆔 المُسجل: {submitter_id}\n"
                f"📅 تاريخ التسجيل: {created_at}\n"
                f"✅ الحالة: {review_status}\n"
                f"🛒 مباع: {'نعم' if sold else 'لا'}\n\n"
            )
        
        if purchase:
            buyer_id = purchase[1]
            buyer_username = purchase[2] or "غير معروف"
            price = purchase[6]
            login_code = purchase[9] or "لم يُطلب"
            purchased_at = datetime.fromisoformat(purchase[10]).strftime("%Y-%m-%d %H:%M")
            
            result_text += (
                f"💰 **معلومات الشراء:**\n"
                f"👤 المشتري: @{buyer_username} ({buyer_id})\n"
                f"💵 السعر: ${price:.2f}\n"
                f"🔐 الكود: `{login_code}`\n"
                f"📅 تاريخ الشراء: {purchased_at}\n"
            )
        
        await update.message.reply_text(
            result_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="ready_admin_panel")
            ]])
        )
        
        context.user_data.pop('admin_action', None)
    
    elif action == 'ready_api_link':
        api_url = update.message.text.strip()
        
        await update.message.reply_text(
            f"🔗 تم حفظ رابط API:\n`{api_url}`\n\n"
            f"⚠️ لاحقاً سيتم تفعيل الاستيراد التلقائي",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="ready_admin_panel")
            ]])
        )
        
        context.user_data.pop('admin_action', None)
    
    elif action == 'ready_manual_add':
        text = update.message.text.strip()
        
        if '|' not in text:
            await update.message.reply_text(
                "❌ **صيغة خاطئة**\n\n"
                "يرجى الإرسال بالصيغة:\n"
                "`رقم_الهاتف|session_string`",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ إلغاء", callback_data="ready_add_accounts")
                ]])
            )
            return
        
        parts = text.split('|', 1)
        phone_number = parts[0].strip()
        session_string = parts[1].strip()
        
        if not phone_number.startswith('+'):
            await update.message.reply_text(
                "❌ **رقم الهاتف يجب أن يبدأ بـ +**\n\n"
                "مثال: `+201234567890`",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ إلغاء", callback_data="ready_add_accounts")
                ]])
            )
            return
        
        try:
            import sqlite3
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO account_reviews 
                (user_id, phone_number, status, session_string, created_at, sold_as_ready, reviewed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                phone_number,
                'approved',
                session_string,
                datetime.now().isoformat(),
                False,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            await update.message.reply_text(
                f"✅ **تم إضافة الحساب بنجاح**\n\n"
                f"📱 الرقم: `{phone_number}`\n\n"
                f"الحساب أصبح جاهزاً للبيع",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ إضافة حساب آخر", callback_data="ready_manual_add"),
                    InlineKeyboardButton("🔙 رجوع", callback_data="ready_add_accounts")
                ]])
            )
            
            context.user_data.pop('admin_action', None)
        
        except Exception as e:
            await update.message.reply_text(
                f"❌ **خطأ في الإضافة**\n\n"
                f"الخطأ: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 رجوع", callback_data="ready_add_accounts")
                ]])
            )

def setup_admin_ready_handlers(app):
    """تسجيل handlers الأدمن للحسابات الجاهزة"""
    app.add_handler(CallbackQueryHandler(show_ready_accounts_admin_panel, pattern="^ready_admin_panel$"))
    app.add_handler(CallbackQueryHandler(show_ready_prices_edit, pattern="^ready_edit_prices$"))
    app.add_handler(CallbackQueryHandler(prompt_new_price, pattern="^ready_edit_price_"))
    app.add_handler(CallbackQueryHandler(show_ready_stats, pattern="^ready_stats"))
    app.add_handler(CallbackQueryHandler(prompt_search_phone, pattern="^ready_search$"))
    app.add_handler(CallbackQueryHandler(show_ready_add_accounts, pattern="^ready_add_accounts$"))
    app.add_handler(CallbackQueryHandler(prompt_upload_sessions, pattern="^ready_upload_sessions$"))
    app.add_handler(CallbackQueryHandler(prompt_manual_add, pattern="^ready_manual_add$"))
    app.add_handler(CallbackQueryHandler(import_connected_accounts, pattern="^ready_import_connected$"))
    app.add_handler(CallbackQueryHandler(show_api_link_options, pattern="^ready_api_link$"))
