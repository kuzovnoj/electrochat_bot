import logging
from telegram import Update, BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats
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

# Состояния для возврата заявки
RETURN_REASON = 100

async def post_init(application: Application):
    """Установка команд меню после инициализации бота"""
    try:
        # Команды только для личных чатов
        private_commands = [
            BotCommand("start", "Начать работу"),
            BotCommand("new", "Создать новую заявку"),
            BotCommand("help", "Помощь по использованию"),
            BotCommand("cancel", "Отмена текущего действия")
        ]
        
        await application.bot.set_my_commands(
            commands=private_commands,
            scope=BotCommandScopeAllPrivateChats()
        )
        logger.info("✓ Меню команд для личных чатов установлено")
        
        # Для групповых чатов устанавливаем пустой список команд
        await application.bot.set_my_commands(
            commands=[],  # Пустой список - не будет меню команд
            scope=BotCommandScopeAllGroupChats()
        )
        logger.info("✓ Меню команд для групп очищено")
        
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
    
    # Создаем фильтр для отмены
    cancel_filter = filters.Regex(r'^(❌ Отмена|отмена|cancel|Отмена)$')
    
    # Создаем ConversationHandler для создания заявки
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("new", handlers.new_application),
            CallbackQueryHandler(handlers.create_application_callback, pattern='^create_application$')
        ],
        states={
            Config.ADDRESS: [
                MessageHandler(cancel_filter, handlers.handle_cancel_button),
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, handlers.handle_address)
            ],
            Config.PHONE: [
                MessageHandler(cancel_filter, handlers.handle_cancel_button),
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, handlers.handle_phone)
            ],
            Config.TASK: [
                MessageHandler(cancel_filter, handlers.handle_cancel_button),
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, handlers.handle_task)
            ],
            Config.COMMENT: [
                MessageHandler(cancel_filter, handlers.handle_cancel_button),
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, handlers.handle_comment)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", handlers.handle_cancel_button),
            MessageHandler(cancel_filter, handlers.handle_cancel_button)
        ],
        allow_reentry=True
    )
    
    # Создаем обработчик для возврата заявки (без ConversationHandler, так как это один шаг)
    # Добавляем ConversationHandler
    application.add_handler(conv_handler)
    
    # Обработчик кнопки "Принять заявку"
    application.add_handler(CallbackQueryHandler(
        handlers.accept_application_callback, 
        pattern='^accept_'
    ))
    
    # Обработчик кнопки "Вернуть заявку"
    application.add_handler(CallbackQueryHandler(
        handlers.return_application_callback, 
        pattern='^return_app_'
    ))
    
    # Обработчик кнопки "Отмена возврата"
    application.add_handler(CallbackQueryHandler(
        handlers.cancel_return_callback, 
        pattern='^cancel_return_'
    ))
    
    # Обработчик для ввода причины возврата (обрабатывает текст после нажатия кнопки возврата)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handlers.handle_return_reason
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

    # Обработчик кнопки "Закрыть заявку"
    application.add_handler(CallbackQueryHandler(
        handlers.close_application_callback, 
        pattern='^close_app_'
    ))
    
    # Обработчик кнопки "Работа выполнена"
    application.add_handler(CallbackQueryHandler(
        handlers.handle_close_done_callback, 
        pattern='^close_done_'
    ))
    
    # Обработчик кнопки "Клиент отказался"
    application.add_handler(CallbackQueryHandler(
        handlers.handle_close_refused_callback, 
        pattern='^close_refused_'
    ))
    
    # Обработчик кнопки "Отмена закрытия"
    application.add_handler(CallbackQueryHandler(
        handlers.cancel_close_callback, 
        pattern='^cancel_close_'
    ))    
    
    # Базовые команды
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("cancel", handlers.handle_cancel_button))
    
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