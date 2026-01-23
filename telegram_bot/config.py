import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    DATABASE_URL = os.getenv('DATABASE_URL')
    ADMIN_GROUP_CHAT_ID = int(os.getenv('ADMIN_GROUP_CHAT_ID', -1001234567890))
    
    # States для ConversationHandler
    ADDRESS, PHONE, TASK, COMMENT = range(4)