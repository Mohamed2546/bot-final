"""
معالج رسائل الأدمن - يتعامل مع جميع الإدخالات النصية
"""
from telegram import Update
from telegram.ext import ContextTypes
import database
import config
import sqlite3
from datetime import datetime, timedelta
from handlers.admin_handlers_extra import search_user_result, send_broadcast
from handlers.admin_ready_accounts import handle_admin_ready_message

def is_admin(user_id):
    """التحقق من صلاحيات الأدمن"""
    return user_id == config.ADMIN_ID or database.is_admin(user_id)

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إدخالات الأدمن النصية"""
    user_id = update.effective_user.id
    
    # فقط الأدمن يمكنهم استخدام هذا المعالج
    if not is_admin(user_id):
        return
    
    # يجب أن يكون هناك إجراء أدمن نشط
    action = context.user_data.get('admin_action')
    if not action:
        return
    
    text = update.message.text.strip()
    
    # البحث عن مستخدم
    if action == 'search_user':
        await search_user_result(update, context, text)
        del context.user_data['admin_action']
        return
    
    # إضافة رصيد
    if action == 'add_balance':
        try:
            parts = text.split()
            target_user_id = int(parts[0])
            amount = float(parts[1])
            
            database.update_user_balance(target_user_id, amount)
            
            await update.message.reply_text(
                f"✅ تم إضافة ${amount} لرصيد المستخدم <code>{target_user_id}</code>",
                parse_mode='HTML'
            )
            
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"🎉 <b>تم إضافة رصيد!</b>\n\n💰 المبلغ: ${amount}\n\n✅ تم إضافته لحسابك بنجاح!",
                    parse_mode='HTML'
                )
            except:
                pass
            
        except (ValueError, IndexError):
            await update.message.reply_text("❌ صيغة خاطئة! استخدم: <code>user_id amount</code>", parse_mode='HTML')
        
        del context.user_data['admin_action']
        return
    
    # خصم رصيد
    if action == 'subtract_balance':
        try:
            parts = text.split()
            target_user_id = int(parts[0])
            amount = float(parts[1])
            
            database.update_user_balance(target_user_id, -amount)
            
            await update.message.reply_text(
                f"✅ تم خصم ${amount} من رصيد المستخدم <code>{target_user_id}</code>",
                parse_mode='HTML'
            )
            
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"ℹ️ <b>تم خصم رصيد</b>\n\n💰 المبلغ: ${amount}\n\nتم خصمه من حسابك.",
                    parse_mode='HTML'
                )
            except:
                pass
            
        except (ValueError, IndexError):
            await update.message.reply_text("❌ صيغة خاطئة! استخدم: <code>user_id amount</code>", parse_mode='HTML')
        
        del context.user_data['admin_action']
        return
    
    # حظر مستخدم
    if action == 'ban_user':
        try:
            target_user_id = int(text)
            
            user = database.get_user(target_user_id)
            if not user:
                await update.message.reply_text("❌ المستخدم غير موجود!")
                del context.user_data['admin_action']
                return
            
            username = user[1]
            database.ban_user(target_user_id, username, user_id, "محظور بواسطة الأدمن")
            
            await update.message.reply_text(f"✅ تم حظر المستخدم <code>{target_user_id}</code>", parse_mode='HTML')
            
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text="⛔ <b>تم حظرك من البوت</b>\n\nللتواصل مع الإدارة راسل الدعم.",
                    parse_mode='HTML'
                )
            except:
                pass
            
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال آي دي رقمي!")
        
        del context.user_data['admin_action']
        return
    
    # فك حظر مستخدم
    if action == 'unban_user':
        try:
            target_user_id = int(text)
            
            if not database.is_banned(target_user_id):
                await update.message.reply_text("❌ المستخدم غير محظور!")
                del context.user_data['admin_action']
                return
            
            database.unban_user(target_user_id)
            
            await update.message.reply_text(f"✅ تم فك حظر المستخدم <code>{target_user_id}</code>", parse_mode='HTML')
            
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text="✅ <b>تم فك حظرك</b>\n\n🎉 يمكنك الآن استخدام البوت!",
                    parse_mode='HTML'
                )
            except:
                pass
            
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال آي دي رقمي!")
        
        del context.user_data['admin_action']
        return
    
    # إضافة أدمن
    if action == 'add_admin':
        try:
            target_user_id = int(text)
            
            if database.is_admin(target_user_id):
                await update.message.reply_text("⚠️ المستخدم أدمن بالفعل!")
                del context.user_data['admin_action']
                return
            
            user = database.get_user(target_user_id)
            username = user[1] if user else "Unknown"
            
            database.add_admin(target_user_id, username, user_id)
            
            await update.message.reply_text(f"✅ تم إضافة الأدمن <code>{target_user_id}</code>", parse_mode='HTML')
            
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text="🎉 <b>مبروك!</b>\n\nتم منحك صلاحيات الأدمن في البوت!\n\nاستخدم /admin للوصول للوحة التحكم.",
                    parse_mode='HTML'
                )
            except:
                pass
            
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال آي دي رقمي!")
        
        del context.user_data['admin_action']
        return
    
    # حذف أدمن
    if action == 'remove_admin':
        try:
            target_user_id = int(text)
            
            if target_user_id == config.ADMIN_ID:
                await update.message.reply_text("❌ لا يمكن حذف الأدمن الرئيسي!")
                del context.user_data['admin_action']
                return
            
            if not database.is_admin(target_user_id):
                await update.message.reply_text("⚠️ المستخدم ليس أدمن!")
                del context.user_data['admin_action']
                return
            
            database.remove_admin(target_user_id)
            
            await update.message.reply_text(f"✅ تم حذف الأدمن <code>{target_user_id}</code>", parse_mode='HTML')
            
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text="ℹ️ <b>تم إزالة صلاحيات الأدمن منك</b>",
                    parse_mode='HTML'
                )
            except:
                pass
            
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال آي دي رقمي!")
        
        del context.user_data['admin_action']
        return
    
    # إضافة بروكسي
    if action == 'add_proxy':
        if database.add_proxy(text, 'socks5', user_id):
            await update.message.reply_text(f"✅ تم إضافة البروكسي:\n<code>{text}</code>", parse_mode='HTML')
        else:
            await update.message.reply_text("❌ البروكسي موجود بالفعل!")
        
        del context.user_data['admin_action']
        return
    
    # حذف بروكسي
    if action == 'remove_proxy':
        try:
            proxy_id = int(text)
            database.remove_proxy(proxy_id)
            await update.message.reply_text(f"✅ تم حذف البروكسي ID: <code>{proxy_id}</code>", parse_mode='HTML')
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال ID رقمي!")
        
        del context.user_data['admin_action']
        return
    
    # رسالة جماعية
    if action == 'broadcast_message':
        await send_broadcast(update, context, text)
        del context.user_data['admin_action']
        return
    
    # رسالة لمستخدم - خطوة 1 (حفظ الآي دي)
    if action == 'send_user_message_step1':
        if text.startswith('@'):
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE username = ?', (text[1:],))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                await update.message.reply_text("❌ المستخدم غير موجود!")
                del context.user_data['admin_action']
                return
            
            context.user_data['target_user_id'] = result[0]
        else:
            try:
                context.user_data['target_user_id'] = int(text)
            except ValueError:
                await update.message.reply_text("❌ يجب إدخال يوزر أو آي دي صحيح!")
                del context.user_data['admin_action']
                return
        
        context.user_data['admin_action'] = 'send_user_message_step2'
        await update.message.reply_text("✅ تم! الآن أرسل الرسالة:")
        return
    
    # رسالة لمستخدم - خطوة 2 (إرسال الرسالة)
    if action == 'send_user_message_step2':
        target_user_id = context.user_data.get('target_user_id')
        
        if not target_user_id:
            await update.message.reply_text("❌ حدث خطأ! حاول مرة أخرى.")
            del context.user_data['admin_action']
            return
        
        try:
            await context.bot.send_message(chat_id=target_user_id, text=text, parse_mode='HTML')
            await update.message.reply_text(f"✅ تم إرسال الرسالة للمستخدم <code>{target_user_id}</code>", parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"❌ فشل الإرسال: {e}")
        
        del context.user_data['admin_action']
        del context.user_data['target_user_id']
        return
    
    # رفض سحب (إدخال السبب)
    if action.startswith('reject_withdrawal_'):
        withdrawal_id = int(action.split('_')[-1])
        admin_id = user_id
        
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id, amount FROM withdrawals WHERE id = ?', (withdrawal_id,))
        result = cursor.fetchone()
        
        if not result:
            await update.message.reply_text("❌ طلب السحب غير موجود!")
            del context.user_data['admin_action']
            conn.close()
            return
        
        target_user_id, amount = result
        
        cursor.execute('''
            UPDATE withdrawals 
            SET status = ?, admin_id = ?, rejection_reason = ?, processed_at = ? 
            WHERE id = ?
        ''', ('rejected', admin_id, text, datetime.now().isoformat(), withdrawal_id))
        
        conn.commit()
        conn.close()
        
        await update.message.reply_text("✅ تم رفض طلب السحب!")
        
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"❌ <b>تم رفض طلب السحب</b>\n\n💰 المبلغ: ${amount}\n📝 السبب: {text}",
                parse_mode='HTML'
            )
        except:
            pass
        
        del context.user_data['admin_action']
        return
    
    # تعديل حدود USDT
    if action == 'edit_usdt_min':
        try:
            min_val = float(text)
            database.update_setting('min_usdt', str(min_val))
            await update.message.reply_text(f"✅ تم تحديث الحد الأدنى لـ USDT: {min_val}$", parse_mode='HTML')
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال رقم صحيح!")
        del context.user_data['admin_action']
        return
    
    if action == 'edit_usdt_max':
        try:
            max_val = float(text)
            database.update_setting('max_usdt', str(max_val))
            await update.message.reply_text(f"✅ تم تحديث الحد الأقصى لـ USDT: {max_val}$", parse_mode='HTML')
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال رقم صحيح!")
        del context.user_data['admin_action']
        return
    
    # تعديل حدود TRX
    if action == 'edit_trx_min':
        try:
            min_val = float(text)
            database.update_setting('min_trx', str(min_val))
            await update.message.reply_text(f"✅ تم تحديث الحد الأدنى لـ TRX: {min_val}$", parse_mode='HTML')
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال رقم صحيح!")
        del context.user_data['admin_action']
        return
    
    if action == 'edit_trx_max':
        try:
            max_val = float(text)
            database.update_setting('max_trx', str(max_val))
            await update.message.reply_text(f"✅ تم تحديث الحد الأقصى لـ TRX: {max_val}$", parse_mode='HTML')
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال رقم صحيح!")
        del context.user_data['admin_action']
        return
    
    # تعديل حدود فودافون
    if action == 'edit_vodafone_min':
        try:
            min_val = float(text)
            database.update_setting('min_vodafone', str(min_val))
            await update.message.reply_text(f"✅ تم تحديث الحد الأدنى لفودافون كاش: {min_val}$", parse_mode='HTML')
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال رقم صحيح!")
        del context.user_data['admin_action']
        return
    
    if action == 'edit_vodafone_max':
        try:
            max_val = float(text)
            database.update_setting('max_vodafone', str(max_val))
            await update.message.reply_text(f"✅ تم تحديث الحد الأقصى لفودافون كاش: {max_val}$", parse_mode='HTML')
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال رقم صحيح!")
        del context.user_data['admin_action']
        return
    
    # تعديل الإعدادات
    if action.startswith('edit_') and not action.startswith('edit_country_') and not action.startswith('edit_flag_') and not action.startswith('edit_capacity_'):
        setting_key = action.replace('edit_', '')
        database.update_setting(setting_key, text)
        
        await update.message.reply_text(
            f"✅ تم تحديث <b>{setting_key}</b>\n\nالقيمة الجديدة: <code>{text}</code>",
            parse_mode='HTML'
        )
        
        del context.user_data['admin_action']
        return
    
    # إضافة دولة
    if action == 'add_country':
        try:
            parts = text.split('|')
            code = parts[0].strip()
            name = parts[1].strip()
            price = float(parts[2].strip())
            review_time = int(parts[3].strip())
            flag = parts[4].strip() if len(parts) > 4 else ''
            
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO countries (country_code, name, price, review_time, flag, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            ''', (code, name, price, review_time, flag))
            conn.commit()
            conn.close()
            
            await update.message.reply_text(
                f"✅ تم إضافة الدولة بنجاح!\n\n{flag} <b>{name}</b>\n🔢 {code}\n💰 ${price}\n⏱ {review_time} دقيقة",
                parse_mode='HTML'
            )
        except (ValueError, IndexError) as e:
            await update.message.reply_text(
                f"❌ صيغة خاطئة! استخدم:\n<code>كود|اسم|سعر|وقت|علم</code>\n\nالخطأ: {e}",
                parse_mode='HTML'
            )
        
        del context.user_data['admin_action']
        return
    
    # تعديل دولة
    if action.startswith('edit_country_'):
        country_code = action.replace('edit_country_', '')
        
        try:
            parts = text.split('|')
            name = parts[0].strip()
            price = float(parts[1].strip())
            review_time = int(parts[2].strip())
            flag = parts[3].strip() if len(parts) > 3 else ''
            
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE countries
                SET name = ?, price = ?, review_time = ?, flag = ?
                WHERE country_code = ?
            ''', (name, price, review_time, flag, country_code))
            conn.commit()
            conn.close()
            
            await update.message.reply_text(
                f"✅ تم تحديث الدولة بنجاح!\n\n{flag} <b>{name}</b>\n🔢 {country_code}\n💰 ${price}\n⏱ {review_time} دقيقة",
                parse_mode='HTML'
            )
        except (ValueError, IndexError) as e:
            await update.message.reply_text(
                f"❌ صيغة خاطئة! استخدم:\n<code>اسم|سعر|وقت|علم</code>\n\nالخطأ: {e}",
                parse_mode='HTML'
            )
        
        del context.user_data['admin_action']
        return
    
    # تعديل علم الدولة
    if action.startswith('edit_flag_'):
        country_code = action.replace('edit_flag_', '')
        
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE countries SET flag = ? WHERE country_code = ?', (text, country_code))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"✅ تم تحديث علم الدولة!\n\n{text} <code>{country_code}</code>",
            parse_mode='HTML'
        )
        
        del context.user_data['admin_action']
        return
    
    # تعديل سعة الدولة
    if action.startswith('edit_capacity_'):
        country_code = action.replace('edit_capacity_', '')
        
        try:
            capacity = int(text)
            
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            cursor.execute('UPDATE countries SET capacity = ? WHERE country_code = ?', (capacity, country_code))
            conn.commit()
            conn.close()
            
            capacity_text = "غير محدودة" if capacity == 0 else str(capacity)
            await update.message.reply_text(
                f"✅ تم تحديث سعة الدولة!\n\n<code>{country_code}</code>\n📊 السعة: {capacity_text}",
                parse_mode='HTML'
            )
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال رقم صحيح!")
        
        del context.user_data['admin_action']
        return
    
    # تعديل وقت الفحص الدوري
    if action == 'edit_monitor_interval':
        try:
            hours = int(text)
            
            if hours < 1 or hours > 24:
                await update.message.reply_text("❌ يجب أن يكون الوقت بين 1 و 24 ساعة!")
                return
            
            # حساب الوقت المتبقي للدورة القادمة قبل التحديث
            import database as db
            
            old_interval = int(database.get_setting('monitor_interval_hours', '2'))
            logs = db.get_monitor_logs(limit=1)
            
            if logs:
                last_check = datetime.fromisoformat(logs[0][5])
                next_check = last_check + timedelta(hours=old_interval)
                now = datetime.now()
                time_left = next_check - now
                
                if time_left.total_seconds() > 0:
                    hours_left = int(time_left.total_seconds() / 3600)
                    minutes_left = int((time_left.total_seconds() % 3600) / 60)
                    time_msg = f"⏳ الدورة القادمة بعد: {hours_left} ساعة و {minutes_left} دقيقة\n\n"
                else:
                    time_msg = "⏳ الدورة القادمة ستبدأ قريباً\n\n"
            else:
                time_msg = "⏳ الدورة الأولى ستبدأ قريباً\n\n"
            
            # الآن نحفظ الإعداد الجديد
            database.update_setting('monitor_interval_hours', str(hours))
            
            await update.message.reply_text(
                f"✅ تم تحديث وقت الفحص!\n\n⏰ الوقت الجديد: كل {hours} ساعة\n\n{time_msg}💡 سيتم تطبيق الوقت الجديد بعد انتهاء الدورة الحالية.",
                parse_mode='HTML'
            )
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال رقم صحيح بين 1 و 24!")
        
        del context.user_data['admin_action']
        return
    
    # تصدير جلسات مستخدم - إدخال الكمية
    if action == 'export_user_sessions_quantity':
        try:
            quantity = int(text)
            
            if quantity < 0:
                await update.message.reply_text("❌ يجب إدخال رقم صحيح!")
                return
            
            target_user_id = context.user_data.get('export_target_user_id')
            country_code = context.user_data.get('export_country_code')
            
            if not target_user_id or not country_code:
                await update.message.reply_text("❌ حدث خطأ! حاول مرة أخرى.")
                del context.user_data['admin_action']
                return
            
            # جلب الجلسات
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            
            if quantity == 0:
                cursor.execute('''
                    SELECT phone_number, session_string FROM accounts 
                    WHERE user_id = ? AND phone_number LIKE ? AND status = "approved"
                ''', (target_user_id, f"{country_code}%"))
            else:
                cursor.execute('''
                    SELECT phone_number, session_string FROM accounts 
                    WHERE user_id = ? AND phone_number LIKE ? AND status = "approved"
                    LIMIT ?
                ''', (target_user_id, f"{country_code}%", quantity))
            
            sessions = cursor.fetchall()
            
            # معلومات الدولة
            cursor.execute('SELECT name, flag FROM countries WHERE country_code = ?', (country_code,))
            country_info = cursor.fetchone()
            conn.close()
            
            if not sessions:
                await update.message.reply_text("❌ لا توجد جلسات متاحة!")
                del context.user_data['admin_action']
                del context.user_data['export_target_user_id']
                del context.user_data['export_country_code']
                return
            
            if country_info:
                name, flag = country_info
                country_display = f"{flag or '🌍'} {name}"
            else:
                country_display = country_code
            
            # إنشاء ملف ZIP
            import io
            import zipfile
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for phone, session_string in sessions:
                    zip_file.writestr(f"{phone}.session", session_string)
            
            zip_buffer.seek(0)
            
            # إرسال الملف
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=zip_buffer,
                filename=f"user_{target_user_id}_{country_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                caption=f"📤 <b>تصدير جلسات المستخدم</b>\n\n👤 <b>المستخدم:</b> <code>{target_user_id}</code>\n🌍 <b>الدولة:</b> {country_display}\n📊 <b>العدد:</b> {len(sessions)}\n📅 <b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                parse_mode='HTML'
            )
            
            await update.message.reply_text(f"✅ تم تصدير {len(sessions)} جلسة بنجاح!")
            
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال رقم صحيح!")
        
        # مسح البيانات المؤقتة
        if 'admin_action' in context.user_data:
            del context.user_data['admin_action']
        if 'export_target_user_id' in context.user_data:
            del context.user_data['export_target_user_id']
        if 'export_country_code' in context.user_data:
            del context.user_data['export_country_code']
        return
    
    # تصدير جلسات دولة - إدخال الكمية
    if action == 'export_country_sessions':
        try:
            quantity = int(text)
            
            if quantity < 0:
                await update.message.reply_text("❌ يجب إدخال رقم صحيح!")
                return
            
            country_code = context.user_data.get('export_country_code')
            export_type = context.user_data.get('export_type', 'zip')
            
            if not country_code:
                await update.message.reply_text("❌ حدث خطأ! حاول مرة أخرى.")
                del context.user_data['admin_action']
                return
            
            # جلب الجلسات
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            
            if quantity == 0:
                cursor.execute('''
                    SELECT phone_number, session_string FROM accounts 
                    WHERE phone_number LIKE ? AND status = "approved"
                ''', (f"{country_code}%",))
            else:
                cursor.execute('''
                    SELECT phone_number, session_string FROM accounts 
                    WHERE phone_number LIKE ? AND status = "approved"
                    LIMIT ?
                ''', (f"{country_code}%", quantity))
            
            sessions = cursor.fetchall()
            
            # معلومات الدولة
            cursor.execute('SELECT name, flag FROM countries WHERE country_code = ?', (country_code,))
            country_info = cursor.fetchone()
            
            # حفظ سجل التصدير
            admin_username = update.effective_user.username or 'Unknown'
            cursor.execute('''
                INSERT INTO import_history (country_code, count, format, admin_username)
                VALUES (?, ?, ?, ?)
            ''', (country_code, len(sessions), export_type.upper(), admin_username))
            conn.commit()
            conn.close()
            
            if not sessions:
                await update.message.reply_text("❌ لا توجد جلسات متاحة!")
                del context.user_data['admin_action']
                del context.user_data['export_country_code']
                del context.user_data['export_type']
                return
            
            if country_info:
                name, flag = country_info
                country_display = f"{flag or '🌍'} {name}"
            else:
                country_display = country_code
            
            # إنشاء ملف حسب النوع
            import io
            
            if export_type == 'zip':
                import zipfile
                zip_buffer = io.BytesIO()
                
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for phone, session_string in sessions:
                        zip_file.writestr(f"{phone}.session", session_string)
                
                zip_buffer.seek(0)
                
                # إرسال الملف
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=zip_buffer,
                    filename=f"{country_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    caption=f"📤 <b>تصدير جلسات</b>\n\n🌍 <b>الدولة:</b> {country_display}\n📊 <b>العدد:</b> {len(sessions)}\n📄 <b>النوع:</b> ZIP\n📅 <b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    parse_mode='HTML'
                )
            else:  # json
                import json
                
                json_data = {
                    "country_code": country_code,
                    "country_name": country_display,
                    "sessions": [{"phone": phone, "session": session_string} for phone, session_string in sessions],
                    "exported_at": datetime.now().isoformat(),
                    "total_count": len(sessions)
                }
                
                json_buffer = io.BytesIO()
                json_buffer.write(json.dumps(json_data, ensure_ascii=False, indent=2).encode('utf-8'))
                json_buffer.seek(0)
                
                # إرسال الملف
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=json_buffer,
                    filename=f"{country_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    caption=f"📤 <b>تصدير جلسات</b>\n\n🌍 <b>الدولة:</b> {country_display}\n📊 <b>العدد:</b> {len(sessions)}\n📄 <b>النوع:</b> JSON\n📅 <b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    parse_mode='HTML'
                )
            
            await update.message.reply_text(f"✅ تم تصدير {len(sessions)} جلسة بنجاح!")
            
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال رقم صحيح!")
        
        # مسح البيانات المؤقتة
        if 'admin_action' in context.user_data:
            del context.user_data['admin_action']
        if 'export_country_code' in context.user_data:
            del context.user_data['export_country_code']
        if 'export_type' in context.user_data:
            del context.user_data['export_type']
        return
    
    # معالجة إدخالات الحسابات الجاهزة
    await handle_admin_ready_message(update, context)
