import json
from telegram.ext import ApplicationBuilder
import logging
import nest_asyncio
from uuid import uuid4
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from config import TOKEN, SUPER_ADMIN_ID, CHANNEL_ID

nest_asyncio.apply()

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

ADMIN_FILE = 'data.json'

def load_admins():
    try:
        with open(ADMIN_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_admins(admins):
    with open(ADMIN_FILE, 'w') as f:
        json.dump(admins, f)

admins = load_admins()
pending_posts = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == SUPER_ADMIN_ID or user_id in admins:
        keyboard = [
            [InlineKeyboardButton("Post Yuborish", callback_data='post')],
            [InlineKeyboardButton("Admin Qo'shish", callback_data='add_admin')],
            [InlineKeyboardButton("Admin O'chirish", callback_data='remove_admin')],
            [InlineKeyboardButton("👥 Adminlar ro'yxati", callback_data='list_admins')],
        ]
        await update.message.reply_text("Admin Paneli:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("Assalomu alaykum! Xush kelibsiz.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if query.data == 'post':
        if user_id == SUPER_ADMIN_ID or user_id in admins:
            pending_posts[user_id] = {'step': 'awaiting_post'}
            await query.message.reply_text("Post matnini yuboring:")
        else:
            await query.message.reply_text("Ruxsat yo‘q.")

    elif query.data == 'add_admin' and user_id == SUPER_ADMIN_ID:
        pending_posts[user_id] = {'step': 'awaiting_add_admin'}
        await query.message.reply_text("Admin ID ni yuboring:")

    elif query.data == 'remove_admin' and user_id == SUPER_ADMIN_ID:
        pending_posts[user_id] = {'step': 'awaiting_remove_admin'}
        await query.message.reply_text("O‘chirmoqchi bo‘lgan admin ID ni yuboring:")

    elif query.data.startswith('get_credentials_'):
        key = query.data.split('_')[-1]
        if await is_subscribed(user_id, context):
            data = context.bot_data.get(f'credentials_{key}')
            if data:
                await query.answer(text=f"🆔 ID: {data['id']}\n🔐 PAROL: {data['password']}", show_alert=True)
            else:
                await query.answer(text="Ma'lumot topilmadi.", show_alert=True)
        else:
            await query.answer(text="⛔ Iltimos, avval kanalga obuna bo‘ling.", show_alert=True)

    elif query.data.startswith('check_subscription_'):
        key = query.data.split('_')[-1]
        if await is_subscribed(user_id, context):
            data = context.bot_data.get(f'credentials_{key}')
            if data:
                await query.answer(text=f"🆔 ID: {data['id']}\n🔐 PAROL: {data['password']}", show_alert=True)
            else:
                await query.answer(text="Ma'lumot yo‘q.", show_alert=True)
        else:
            await query.answer(text="⛔ Hali obuna bo‘lmagansiz.", show_alert=True)
            
            async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
                query = update.callback_query
    user_id = query.from_user.id

    if query.data == 'post':
        ...
    elif query.data == 'list_admins':
        text_lines = []
        for i, admin_id in enumerate(admins, 1):
            try:
                user = await context.bot.get_chat(admin_id)
                name = user.full_name
                username = f"@{user.username}" if user.username else "(username yo‘q)"
                text_lines.append(f"{i}. {name} {username}")
            except:
                text_lines.append(f"{i}. ❓ Noma’lum foydalanuvchi (ID: {admin_id})")

        text = "\n".join(text_lines) or "👥 Hozircha adminlar yo‘q."
        await query.message.reply_text(f"📋 Adminlar ro‘yxati:\n\n{text}")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in pending_posts:
        return

    step = pending_posts[user_id]['step']

    if step == 'awaiting_post':
        pending_posts[user_id]['post'] = text
        pending_posts[user_id]['step'] = 'awaiting_id'
        await update.message.reply_text("ID ni yuboring:")

    elif step == 'awaiting_id':
        pending_posts[user_id]['id'] = text
        pending_posts[user_id]['step'] = 'awaiting_password'
        await update.message.reply_text("PAROL ni yuboring:")

    elif step == 'awaiting_password':
        post_text = pending_posts[user_id]['post']
        id_text = pending_posts[user_id]['id']
        password_text = text
        key = str(uuid4())

        context.bot_data[f'credentials_{key}'] = {
            'id': id_text,
            'password': password_text,
            'post_text': post_text
        }

        keyboard = [[InlineKeyboardButton("ID va PAROL", callback_data=f'get_credentials_{key}')]]
        await context.bot.send_message(chat_id=CHANNEL_ID, text=post_text, reply_markup=InlineKeyboardMarkup(keyboard))

        await update.message.reply_text("✅ Post kanalga yuborildi. Tugmani bosgan foydalanuvchilarga ID va PAROL kichik oynada ko‘rsatiladi.")
        del pending_posts[user_id]

    elif step == 'awaiting_add_admin':
        try:
            new_id = int(text)

            if new_id in admins:
                await update.message.reply_text("⚠️ Bu foydalanuvchi allaqachon admin.")
                del pending_posts[user_id]
                return

            # Foydalanuvchi ma'lumotini olish
            try:
                user = await context.bot.get_chat(new_id)
                name = user.full_name
                username = f"@{user.username}" if user.username else "(username yo‘q)"

                admins.append(new_id)
                save_admins(admins)

                await update.message.reply_text(f"✅ Admin qo‘shildi: {name} {username}")
            except:
                await update.message.reply_text("❌ Bu ID ostida foydalanuvchi topilmadi.")

        except ValueError:
            await update.message.reply_text("❌ Noto‘g‘ri ID kiritdingiz.")
        del pending_posts[user_id]


    elif step == 'awaiting_remove_admin':
        try:
            rem_id = int(text)
            if rem_id in admins:
                admins.remove(rem_id)
                save_admins(admins)
                await update.message.reply_text("✅ Admin o‘chirildi.")
            else:
                await update.message.reply_text("⚠️ Bu foydalanuvchi admin emas.")
        except:
            await update.message.reply_text("❌ Noto‘g‘ri ID kiritingiz.")
        del pending_posts[user_id]

async def is_subscribed(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def run_bot():
    from asyncio import get_event_loop, set_event_loop, new_event_loop
    try:
        loop = get_event_loop()
        if loop.is_running():
            loop = new_event_loop()
            set_event_loop(loop)
    except RuntimeError:
        loop = new_event_loop()
        set_event_loop(loop)

    async def start_bot():
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        await app.run_polling()

    loop.run_until_complete(start_bot())

if __name__ == '__main__':
    run_bot()
