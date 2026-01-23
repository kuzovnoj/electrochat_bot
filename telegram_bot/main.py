import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from config import Config
import handlers
from database import db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Запуск бота"""
    # Проверяем подключение к базе данных
    if db is None or db.conn is None:
        logger.error("✗ База данных не инициализирована. Бот не может быть запущен.")
        return
    
    # Создаем приложение для версии 20.x
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Создаем ConversationHandler для заявок
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handlers.create_application_callback, pattern='^create_application$'),
            CommandHandler('start', handlers.start)
        ],
        states={
            Config.ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.get_address)],
            Config.PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.get_phone)],
            Config.TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.get_task)],
            Config.COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.get_comment)],
        },
        fallbacks=[MessageHandler(filters.Regex('^❌ Отмена$'), handlers.cancel)],
    )
    
    # Добавляем обработчики
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handlers.accept_application_callback, pattern='^accept_'))
    application.add_handler(CommandHandler('start', handlers.start))
    application.add_error_handler(handlers.error_handler)
    application.add_handler(CommandHandler('debug', handlers.debug))
    
    # Запускаем бота
    logger.info("✓ Бот запущен и готов к работе...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()