import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # Используем DATABASE_URL из .env или формируем из отдельных переменных
    DATABASE_URL = os.getenv('DATABASE_URL') or \
        f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@" \
        f"{os.getenv('POSTGRES_HOST', 'postgres')}:{os.getenv('POSTGRES_PORT', '5432')}/" \
        f"{os.getenv('POSTGRES_DB')}"
    
    ADMIN_GROUP_CHAT_ID = int(os.getenv('ADMIN_GROUP_CHAT_ID', -1001234567890))
    
    # States для ConversationHandler
    ADDRESS, PHONE, TASK, COMMENT = range(4)