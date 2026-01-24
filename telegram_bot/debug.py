import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BOT_TOKEN = "ВАШ_ТОКЕН"

async def debug_message(update: Update, context):
    """Отладочный обработчик"""
    print(f"\n{'='*60}")
    print(f"📨 Новое сообщение:")
    print(f"├ Чат ID: {update.effective_chat.id}")
    print(f"├ Тип чата: {update.effective_chat.type}")
    print(f"├ User ID: {update.effective_user.id}")
    print(f"├ Username: {update.effective_user.username}")
    print(f"└ Текст: {update.message.text}")
    print(f"{'='*60}\n")

async def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL, debug_message))
    
    print("🔍 Отладочный бот запущен...")
    print("Все сообщения будут выводиться в консоль")
    
    application.run_polling()

if __name__ == '__main__':
    main()