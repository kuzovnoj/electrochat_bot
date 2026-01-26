import logging
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
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
        # Создаем приложение
        application = (Application.builder()
            .token(Config.BOT_TOKEN)
            .pool_timeout(30)
            .connect_timeout(30)
            .read_timeout(30)
            .write_timeout(30)
            .post_init(post_init)
            .build())
    except Exception as e:
        logger.error(f"✗ Ошибка: {e}")
        return
    
    # Создаем ConversationHandler для создания заявки
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("new", handlers.new_application),
            CallbackQueryHandler(handlers.create_application_callback, pattern='^create_application$')
        ],
        states={
            Config.ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_address)],
            Config.PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_phone)],
            Config.TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_task)],
            Config.COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_comment)],
        },
        fallbacks=[
            CommandHandler("cancel", handlers.handle_cancel),
            MessageHandler(filters.Regex('^(❌ Отмена|cancel)$'), handlers.handle_cancel)
        ],
    )
    
    # Добавляем ConversationHandler
    application.add_handler(conv_handler)
    
    # Обработчик кнопки "Принять заявку"
    application.add_handler(CallbackQueryHandler(
        handlers.accept_application_callback, 
        pattern='^accept_'
    ))
    
    # Обработчик кнопки "Сохранить контакт"
    application.add_handler(CallbackQueryHandler(
        handlers.save_contact_callback, 
        pattern='^save_contact_'
    ))
    
    # Обработчик кнопок копирования данных
    application.add_handler(CallbackQueryHandler(
        handlers.copy_data_callback, 
        pattern='^copy_'
    ))
    
    # Базовые команды
    application.add_handler(CommandHandler("start", handlers.start))
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