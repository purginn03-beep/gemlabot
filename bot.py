import logging
import os
import asyncio
from datetime import datetime
from typing import Dict, Set

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHANNEL_LINK = os.getenv("TARGET_CHANNEL_LINK", "https://t.me/your_channel")
TARGET_CHANNEL_ID = os.getenv("TARGET_CHANNEL_ID", "@your_channel")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# Настройка логирования
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logs/redirect_bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Хранилище статистики (в памяти, для продакшена замените на БД)
stats: Dict[str, dict] = {
    "total_clicks": 0,
    "unique_users": set(),
    "user_clicks": {}
}


def save_stats():
    """Сохранить статистику в файл"""
    try:
        with open("logs/stats.txt", "w", encoding="utf-8") as f:
            f.write(f"Total clicks: {stats['total_clicks']}\n")
            f.write(f"Unique users: {len(stats['unique_users'])}\n")
            f.write(f"Last updated: {datetime.now()}\n")
    except Exception as e:
        logger.error(f"Ошибка сохранения статистики: {e}")


def load_stats():
    """Загрузить статистику из файла"""
    global stats
    try:
        if os.path.exists("logs/stats.txt"):
            with open("logs/stats.txt", "r", encoding="utf-8") as f:
                # Простое восстановление, для полноценной статистики нужна БД
                logger.info("Статистика загружена из файла")
    except Exception as e:
        logger.error(f"Ошибка загрузки статистики: {e}")


# ==================== КОМАНДЫ БОТА ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    username = user.username or f"{user.first_name}"
    
    # Логируем переход
    logger.info(f"Пользователь {user_id} (@{username}) открыл бота")
    
    # Проверяем, есть ли реферальный параметр
    args = context.args
    referrer = None
    if args:
        referrer = args[0]
        logger.info(f"Реферальный переход от {referrer} -> {user_id}")
        context.user_data["referrer"] = referrer
    
    # Текст приветствия
    welcome_text = (
        f"🔥 **Добро пожаловать, {user.first_name}!** 🔥\n\n"
        f"Я проведу тебя в **VIP-канал**, где публикуются эксклюзивные материалы, "
        f"бонусы и актуальные схемы заработка.\n\n"
        f"⚠️ **Внимание:** канал закрытый. После перехода обязательно подпишись, "
        f"чтобы не потерять доступ!\n\n"
        f"👇 **Нажми на кнопку ниже, чтобы перейти** 👇"
    )
    
    # Клавиатура с кнопкой перехода
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🔓 ПЕРЕЙТИ В КАНАЛ 🔓",
            url=TARGET_CHANNEL_LINK
        )],
        [InlineKeyboardButton(
            "❓ Что меня ждет?",
            callback_data="about"
        )],
        [InlineKeyboardButton(
            "📊 Статистика канала",
            callback_data="stats"
        )]
    ])
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )
    
    # Обновляем статистику
    stats["total_clicks"] += 1
    if user_id not in stats["unique_users"]:
        stats["unique_users"].add(user_id)
        stats["user_clicks"][user_id] = 1
    else:
        stats["user_clicks"][user_id] = stats["user_clicks"].get(user_id, 0) + 1
    
    save_stats()


async def about_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Информация о канале"""
    query = update.callback_query
    await query.answer()
    
    about_text = (
        "📢 **Что вас ждет в канале?**\n\n"
        "✅ **Ежедневные прогнозы** с высокой проходимостью\n"
        "✅ **Эксклюзивные бонусы** и промокоды\n"
        "✅ **Разбор стратегий** от профи\n"
        "✅ **VIP-чат** с единомышленниками\n"
        "✅ **Закрытые стримы** и разборы\n\n"
        "🔥 **Все это — абсолютно бесплатно!**\n\n"
        "👇 Нажми на кнопку ниже, чтобы присоединиться 👇"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🔓 ПЕРЕЙТИ В КАНАЛ 🔓",
            url=TARGET_CHANNEL_LINK
        )],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_start")]
    ])
    
    await query.edit_message_text(
        about_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )


async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать статистику перехода"""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    # Только админ видит полную статистику
    if user_id == ADMIN_ID:
        stats_text = (
            "📊 **Статистика переходов**\n\n"
            f"👥 Всего переходов: **{stats['total_clicks']}**\n"
            f"👤 Уникальных пользователей: **{len(stats['unique_users'])}**\n"
            f"🎯 Конверсия: **{stats['total_clicks'] / len(stats['unique_users']) if stats['unique_users'] else 0:.1f}** кликов на пользователя\n\n"
            f"📅 Обновлено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    else:
        stats_text = (
            "📊 **Статистика канала**\n\n"
            f"👥 Количество переходов: **{stats['total_clicks']}**\n"
            f"👤 Уникальных посетителей: **{len(stats['unique_users'])}**\n\n"
            f"🔥 Присоединяйся к нам — стань частью сообщества!"
        )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_start")],
        [InlineKeyboardButton("🔓 Перейти в канал", url=TARGET_CHANNEL_LINK)]
    ])
    
    await query.edit_message_text(
        stats_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )


async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Вернуться к начальному сообщению"""
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    welcome_text = (
        f"🔥 **Добро пожаловать, {user.first_name}!** 🔥\n\n"
        f"Я проведу тебя в **VIP-канал**, где публикуются эксклюзивные материалы, "
        f"бонусы и актуальные схемы заработка.\n\n"
        f"⚠️ **Внимание:** канал закрытый. После перехода обязательно подпишись, "
        f"чтобы не потерять доступ!\n\n"
        f"👇 **Нажми на кнопку ниже, чтобы перейти** 👇"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🔓 ПЕРЕЙТИ В КАНАЛ 🔓",
            url=TARGET_CHANNEL_LINK
        )],
        [InlineKeyboardButton(
            "❓ Что меня ждет?",
            callback_data="about"
        )],
        [InlineKeyboardButton(
            "📊 Статистика канала",
            callback_data="stats"
        )]
    ])
    
    await query.edit_message_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /help"""
    help_text = (
        "❓ **Помощь**\n\n"
        "Я бот-переходник в основной Telegram-канал.\n\n"
        "**Как пользоваться:**\n"
        "1️⃣ Нажми на кнопку \"ПЕРЕЙТИ В КАНАЛ\"\n"
        "2️⃣ Подпишись на канал\n"
        "3️⃣ Получай эксклюзивный контент\n\n"
        "**Доступные команды:**\n"
        "/start — начать заново\n"
        "/help — эта справка\n"
        "/stats — статистика переходов\n"
        "/link — получить ссылку на канал\n\n"
        "📞 По вопросам: @support_username"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN
    )


async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправить прямую ссылку на канал"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🔗 ПЕРЕЙТИ В КАНАЛ 🔗",
            url=TARGET_CHANNEL_LINK
        )]
    ])
    
    await update.message.reply_text(
        f"🔗 **Ссылка на канал:**\n{TARGET_CHANNEL_LINK}\n\n"
        f"Нажми на кнопку ниже, чтобы подписаться 👇",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /stats — статистика для админа"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "📊 **Статистика канала**\n\n"
            f"👥 Количество переходов: **{stats['total_clicks']}**\n"
            f"👤 Уникальных посетителей: **{len(stats['unique_users'])}**\n\n"
            f"🔥 Присоединяйся — и ты будешь в плюсе!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Полная статистика для админа
    stats_text = (
        "📊 **Полная статистика бота**\n\n"
        f"👥 Всего переходов: **{stats['total_clicks']}**\n"
        f"👤 Уникальных пользователей: **{len(stats['unique_users'])}**\n"
        f"🎯 Среднее кол-во кликов: **{stats['total_clicks'] / len(stats['unique_users']) if stats['unique_users'] else 0:.1f}**\n\n"
        f"🔗 Целевой канал: {TARGET_CHANNEL_ID}\n"
        f"📅 Обновлено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"💡 *Совет:* используй реферальную ссылку для отслеживания источников:\n"
        f"`https://t.me/{context.bot.username}?start=ref_ID`"
    )
    
    # Добавляем топ пользователей
    if stats["user_clicks"]:
        top_users = sorted(stats["user_clicks"].items(), key=lambda x: x[1], reverse=True)[:5]
        if top_users:
            stats_text += "\n\n🏆 **Топ переходов:**\n"
            for uid, clicks in top_users:
                stats_text += f"• `{uid}` — {clicks} переходов\n"
    
    await update.message.reply_text(
        stats_text,
        parse_mode=ParseMode.MARKDOWN
    )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Админ-панель (только для админа)"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ У вас нет доступа.")
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Полная статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Сделать рассылку", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📤 Экспорт данных", callback_data="admin_export")],
        [InlineKeyboardButton("🔧 Настройки", callback_data="admin_settings")]
    ])
    
    await update.message.reply_text(
        "🔐 **Админ-панель**\n\nВыберите действие:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка админских callback'ов"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id != ADMIN_ID:
        await query.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await query.answer()
    
    if query.data == "admin_stats":
        # Детальная статистика
        stats_text = (
            "📊 **Детальная статистика**\n\n"
            f"📈 Всего переходов: {stats['total_clicks']}\n"
            f"👥 Уникальных: {len(stats['unique_users'])}\n"
            f"🎯 Конверсия: {stats['total_clicks'] / len(stats['unique_users']) if stats['unique_users'] else 0:.2f}\n\n"
            f"📝 Всего пользователей в системе: {len(stats['unique_users'])}\n"
            f"🔗 Целевой канал: {TARGET_CHANNEL_ID}"
        )
        
        await query.edit_message_text(
            stats_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]
            ])
        )
    
    elif query.data == "admin_back":
        # Возврат в админ-панель
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Полная статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("📢 Сделать рассылку", callback_data="admin_broadcast")],
            [InlineKeyboardButton("📤 Экспорт данных", callback_data="admin_export")],
            [InlineKeyboardButton("🔧 Настройки", callback_data="admin_settings")]
        ])
        
        await query.edit_message_text(
            "🔐 **Админ-панель**\n\nВыберите действие:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    elif query.data == "admin_export":
        # Экспорт данных
        if stats["unique_users"]:
            # Формируем список пользователей
            users_list = "\n".join([str(uid) for uid in stats["unique_users"]])
            text = f"📤 **Экспорт данных**\n\nВсего пользователей: {len(stats['unique_users'])}\n\nСписок ID:\n{users_list[:3000]}"
        else:
            text = "📭 Нет данных для экспорта"
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]
            ])
        )


async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработка новых участников (если бот добавлен в группу)
    Можно отправить приветственное сообщение
    """
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            # Бота добавили в группу
            welcome_msg = (
                f"🤖 Бот-переходник активирован!\n\n"
                f"🔗 Основной канал: {TARGET_CHANNEL_LINK}\n\n"
                f"Отправьте /start для получения ссылки."
            )
            await update.message.reply_text(welcome_msg)
            break


# ==================== WEBHOOK + FLASK ====================

# Создаем Flask приложение
flask_app = Flask(__name__)

# Глобальная переменная для Application Telegram
telegram_app = None


async def setup_webhook():
    """Установка вебхука при запуске"""
    global telegram_app
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_URL')}/webhook/{BOT_TOKEN}"
    
    await telegram_app.bot.set_webhook(url=webhook_url)
    logger.info(f"✅ Webhook установлен: {webhook_url}")
    
    # Устанавливаем команды бота
    await telegram_app.bot.set_my_commands([
        BotCommand("start", "Перейти в основной канал"),
        BotCommand("help", "Помощь"),
        BotCommand("link", "Получить ссылку на канал"),
        BotCommand("stats", "Статистика переходов"),
        BotCommand("admin", "Админ-панель (только для админа)"),
    ])
    
    logger.info("Бот-переходник запущен на Webhook!")


@flask_app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    """Принимает обновления от Telegram"""
    global telegram_app
    
    try:
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        await telegram_app.process_update(update)
        return "ok", 200
    except Exception as e:
        logger.error(f"Ошибка в вебхуке: {e}")
        return "error", 500


@flask_app.route("/")
def index():
    return "Бот работает!", 200


@flask_app.route("/health")
def health():
    return "OK", 200


# ==================== ЗАПУСК ====================

def main():
    """Запуск бота с Webhook"""
    global telegram_app
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не указан в .env файле")
        print("❌ Ошибка: BOT_TOKEN не указан в .env файле")
        return
    
    if not TARGET_CHANNEL_LINK:
        logger.warning("TARGET_CHANNEL_LINK не указан")
    
    # Загружаем статистику
    load_stats()
    
    # Создаем приложение Telegram (без updater)
    telegram_app = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("link", link_command))
    telegram_app.add_handler(CommandHandler("stats", stats_command))
    telegram_app.add_handler(CommandHandler("admin", admin_panel))
    
    # Регистрируем callback обработчики
    telegram_app.add_handler(CallbackQueryHandler(about_callback, pattern="^about$"))
    telegram_app.add_handler(CallbackQueryHandler(stats_callback, pattern="^stats$"))
    telegram_app.add_handler(CallbackQueryHandler(back_to_start, pattern="^back_to_start$"))
    telegram_app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
    
    # Обработка новых участников в группе
    telegram_app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        handle_new_member
    ))
    
    # Устанавливаем вебхук (в синхронном контексте)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setup_webhook())
    
    # Запускаем Flask сервер
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Запуск Flask сервера на порту {port}")
    flask_app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
