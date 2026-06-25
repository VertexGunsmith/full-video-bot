import logging
import asyncio
import sqlite3
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram import InputMediaPhoto

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_ID = 7014721682
TOKEN = "8816201288:AAFF2t8lBAygLwNc6LWfbSJb8uxhEtsZ6hA"

VIDEOS = [
    {
        "id": 1,
        "title": "ПРИСЕДАНИЯ",
        "description": "Как правильно приседать",
        "duration": "10 минут",
        "price": 3000,
        "price_str": "3 000",
        "photo_id": "AgACAgIAAxkBAAEftNVqPJwoaaHdBWwS1Kfrg8TEgJ9M-AACWCFrG23J4UmyTDevczUdDwEAAwIAA3gAAzwE",
        "file_id": "AAMCAgADGQEDQS37ajyVePh8Jn534YBGHULxOJnKuccAAkqUAAJ6selJbdIHc_ZjXcQBAAdtAAM8BA"
    },
    # Добавь остальные видео по той же схеме
]

BUNDLE_PRICE = 10000
BUNDLE_PRICE_STR = "10 000"

def init_db():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS purchases
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, video_id TEXT, amount INTEGER, created_at TEXT)''')
    conn.commit()
    conn.close()

def add_user(user):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT user_id FROM users WHERE user_id=?', (user.id,))
    if not c.fetchone():
        c.execute('INSERT INTO users VALUES (?,?,?,?)', (user.id, user.username, user.first_name, datetime.now().isoformat()))
        conn.commit()
    conn.close()

def add_purchase(user_id, video_id, amount):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('INSERT INTO purchases VALUES (?,?,?,?,?)', (None, user_id, video_id, amount, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user_purchases(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT video_id FROM purchases WHERE user_id=?', (user_id,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_video_keyboard(index, user_id):
    video = VIDEOS[index]
    purchases = get_user_purchases(user_id)
    bought = str(video['id']) in purchases or 'bundle' in purchases
    
    buttons = []
    
    nav = []
    if index > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"nav_{index-1}"))
    nav.append(InlineKeyboardButton(f"{index+1}/{len(VIDEOS)}", callback_data="count"))
    if index < len(VIDEOS) - 1:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"nav_{index+1}"))
    buttons.append(nav)
    
    if bought:
        buttons.append([InlineKeyboardButton("✅ УЖЕ КУПЛЕНО", callback_data="bought")])
    else:
        buttons.append([InlineKeyboardButton(f"🔒 КУПИТЬ — {video['price_str']} ₽", callback_data=f"buy_{video['id']}")])
    
    buttons.append([InlineKeyboardButton(f"🎁 ВСЕ ВИДЕО — {BUNDLE_PRICE_STR} ₽", callback_data="buy_bundle")])
    
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    add_user(user)
    
    keyboard = [
        [KeyboardButton("🎬 Каталог видео")],
        [KeyboardButton("📋 Мои покупки")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        f"Здесь ты можешь купить обучающие видео.\n\n"
        f"Нажми 🎬 Каталог видео чтобы начать!",
        reply_markup=reply_markup
    )

async def show_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    await send_video_card(update, context, 0, user_id)

async def send_video_card(update, context, index, user_id):
    video = VIDEOS[index]
    text = (
        f"🎬 {video['title']}\n"
        f"⏱ Длительность: {video['duration']}\n"
        f"📝 {video['description']}\n\n"
        f"💰 Цена: {video['price_str']} ₽"
    )
    keyboard = get_video_keyboard(index, user_id)
    
    if update.message:
        if video.get('photo_id'):
            await update.message.reply_photo(
                photo=video['photo_id'],
                caption=text,
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(text, reply_markup=keyboard)
    else:
        if video.get('photo_id'):
            await update.callback_query.edit_message_media(
                media=InputMediaPhoto(media=video['photo_id'], caption=text),
                reply_markup=keyboard
            )
        else:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard)

async def show_my_purchases(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    purchases = get_user_purchases(user_id)
    
    if not purchases:
        await update.message.reply_text("📋 У вас пока нет покупок.\n\nНажмите 🎬 Каталог видео чтобы выбрать!")
        return
    
    if 'bundle' in purchases:
        await update.message.reply_text("🎁 У вас есть доступ ко всем видео!\n\nНапишите /start чтобы получить видео.")
        return
    
    text = "📋 Ваши покупки:\n\n"
    for p in purchases:
        for v in VIDEOS:
            if str(v['id']) == p:
                text += f"✅ {v['title']}\n"
    
    await update.message.reply_text(text)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("nav_"):
        index = int(data.split("_")[1])
        video = VIDEOS[index]
        text = (
            f"🎬 {video['title']}\n"
            f"⏱ Длительность: {video['duration']}\n"
            f"📝 {video['description']}\n\n"
            f"💰 Цена: {video['price_str']} ₽"
        )
        keyboard = get_video_keyboard(index, user_id)
        await query.edit_message_text(text, reply_markup=keyboard)
    
    elif data.startswith("buy_"):
        video_id = data.split("_")[1]
        
        if video_id == "bundle":
            context.user_data['buying'] = 'bundle'
            context.user_data['buying_price'] = BUNDLE_PRICE_STR
            text = (
                f"🎁 Все видео — {BUNDLE_PRICE_STR} ₽\n\n"
                f"Способ оплаты: На карту Т-Банк\n"
                f"К оплате: {BUNDLE_PRICE_STR} 🇷🇺RUB\n\n"
                f"Реквизиты:\n"
                f"2200701046225592\n"
                f"Т-банк\n"
                f"Наталия💖\n"
                f"__________________________\n"
                f"После оплаты отправьте чек боту"
            )
        else:
            video = next((v for v in VIDEOS if str(v['id']) == video_id), None)
            if not video:
                return
            context.user_data['buying'] = video_id
            context.user_data['buying_price'] = video['price_str']
            text = (
                f"🎬 {video['title']}\n\n"
                f"Способ оплаты: На карту Т-Банк\n"
                f"К оплате: {video['price_str']} 🇷🇺RUB\n\n"
                f"Реквизиты:\n"
                f"2200701046225592\n"
                f"Т-банк\n"
                f"Наталия💖\n"
                f"__________________________\n"
                f"После оплаты отправьте чек боту"
            )
        
        keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Я ОПЛАТИЛ", callback_data="paid")],
    [InlineKeyboardButton("👈 НАЗАД", callback_data="nav_0")]
])
        await query.edit_message_text(text, reply_markup=keyboard)
    
    elif data == "paid":
        await query.edit_message_text(
            "👌 Отправьте скриншот оплаты картинкой \n\n"
            "На скриншоте должны быть видны дата, время и сумма."
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    buying = context.user_data.get('buying', 'Не указано')
    buying_price = context.user_data.get('buying_price', '0')
    photo = update.message.photo[-1]
    
    if buying == 'bundle':
        item_name = f"Все видео — {buying_price}₽"
    else:
        video = next((v for v in VIDEOS if str(v['id']) == buying), None)
        item_name = f"{video['title']} — {buying_price}₽" if video else buying
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{user.id}_{buying}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user.id}")
    ]])
    
    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo.file_id,
            caption=f"💳 Новый чек:\n\n"
                    f"👤 {user.first_name} @{user.username or 'нет'}\n"
                    f"ID: {user.id}\n"
                    f"Покупка: {item_name}",
            reply_markup=keyboard
        )
        await update.message.reply_text("✅ Чек получен! Ожидайте подтверждения.")
    except Exception as e:
        logger.error(f"Ошибка: {e}")

async def handle_approve_reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data.split('_', 2)
    action = data[0]
    user_id = int(data[1])
    
    if action == "approve":
        video_id = data[2]
        
        if video_id == "bundle":
            add_purchase(user_id, 'bundle', BUNDLE_PRICE)
            for video in VIDEOS:
                try:
                    await context.bot.send_video(
                        chat_id=user_id,
                        video=video['file_id'],
                        caption=f"🎬 {video['title']}\n⏱ {video['duration']}\n\nСпасибо за покупку! 🎉"
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки видео: {e}")
        else:
            video = next((v for v in VIDEOS if str(v['id']) == video_id), None)
            if video:
                add_purchase(user_id, video_id, video['price'])
                try:
                    await context.bot.send_video(
                        chat_id=user_id,
                        video=video['file_id'],
                        caption=f"🎬 {video['title']}\n⏱ {video['duration']}\n\nСпасибо за покупку! 🎉"
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки видео: {e}")
        
        await query.edit_message_caption(
            caption=query.message.caption + "\n\n✅ ОДОБРЕНО",
            reply_markup=None
        )
        await context.bot.send_message(chat_id=user_id, text="🎉 Оплата подтверждена! Видео отправлено выше.")
    
    elif action == "reject":
        await query.edit_message_caption(
            caption=query.message.caption + "\n\n❌ ОТКЛОНЕНО",
            reply_markup=None
        )
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Оплата не подтверждена.\nСвяжитесь с администратором."
        )

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    users = c.fetchone()[0]
    c.execute('SELECT COUNT(*), SUM(amount) FROM purchases')
    row = c.fetchone()
    purchases = row[0]
    revenue = row[1] or 0
    conn.close()
    await update.message.reply_text(
        f"📊 СТАТИСТИКА\n\n"
        f"👥 Пользователей: {users}\n"
        f"💰 Покупок: {purchases}\n"
        f"💵 Выручка: {revenue:,}₽"
    )

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(MessageHandler(filters.Regex("^🎬 Каталог видео$"), show_catalog))
    app.add_handler(MessageHandler(filters.Regex("^📋 Мои покупки$"), show_my_purchases))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_approve_reject, pattern="^(approve|reject)_"))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
