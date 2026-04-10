import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # Только DATABASE_URL, не формируем из частей
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL must be set in .env file")
    
    ADMIN_GROUP_CHAT_ID = int(os.getenv('ADMIN_GROUP_CHAT_ID', -1001234567890))

    API_KEY = os.getenv('BOT_API_KEY', 'your-secret-api-key-here')  #
    
    SITE_DOMAIN = os.getenv('SITE_DOMAIN', 'domain_name')

    # States для ConversationHandler
    ADDRESS, PHONE, TASK, COMMENT, PHOTO = range(5)  # Добавили PHOTO

    # Исходящие запросы к api.telegram.org через прокси (HTTP / HTTPS / SOCKS5).
    # Примеры: http://127.0.0.1:8118  socks5://127.0.0.1:1080
    # В Docker 127.0.0.1 — это контейнер; прокси на хосте: socks5://host.docker.internal:1080
    # (в docker-compose ниже добавлен extra_hosts для host.docker.internal).
    _proxy = os.getenv("PROXY_URL", "").strip()
    PROXY_URL = _proxy if _proxy else None


def telegram_http_request():
    """HTTPXRequest с теми же таймаутами и опциональным PROXY_URL (для Bot вне Application, напр. webhook)."""
    from telegram.request import HTTPXRequest

    kwargs = {
        "connect_timeout": 30.0,
        "read_timeout": 30.0,
        "write_timeout": 30.0,
        "pool_timeout": 30.0,
    }
    if Config.PROXY_URL:
        kwargs["proxy"] = Config.PROXY_URL
    return HTTPXRequest(**kwargs)