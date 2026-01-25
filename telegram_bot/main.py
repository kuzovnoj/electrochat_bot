import logging
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import Config
import handlers
from database import db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def post_init(application: Application):
    """Установка команд меню после инициализации бота"""
    # Команды для меню
    commands = [
        BotCommand("start", "Начать работу"),
        BotCommand("new", "Создать новую заявку"),
        BotCommand("help", "Помощь по использованию бота"),
        BotCommand("cancel", "Отмена текущего действия")
    ]
    
    try:
        await application.bot.set_my_commands(commands)
        logger.info("✓ Меню команд установлено")
    except Exception as e:
        logger.error(f"✗ Ошибка установки меню: {e}")

def main():
    """Запуск бота"""
    if db is None or db.conn is None:
        logger.error("✗ База данных не инициализирована.")
        return
    
    try:
        # Создаем приложение - все в одной строке или с правильными отступами
        application = (Application.builder()
            .token(Config.BOT_TOKEN)
            .pool_timeout(30)
            .connect_timeout(30)
            .read_timeout(30)
            .write_timeout(30)
            .post_init(post_init)  # Добавляем post_init
            .build())
    except Exception as e:
        logger.error(f"✗ Ошибка: {e}")
        return
    
    # Обработчик кнопки "Подать заявку"
    application.add_handler(CallbackQueryHandler(
        handlers.create_application_callback, 
        pattern='^create_application$'
    ))
    
    # Обработчик ВСЕХ сообщений в личном чате
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handlers.handle_private_message
    ))
    
    # Обработчик кнопки "Принять заявку"
    application.add_handler(CallbackQueryHandler(
        handlers.accept_application_callback, 
        pattern='^accept_'
    ))
    
    # Команды
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("new", handlers.new_application))  # Новая команда
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("cancel", handlers.handle_cancel))
    
    # Обработчик ошибок
    application.add_error_handler(handlers.error_handler)
    
    logger.info("✓ Бот запущен...")
    logger.info("✓ Готов к работе!")
    
    # Запускаем бота
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False
    )

if __name__ == '__main__':
    main()