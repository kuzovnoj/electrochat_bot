import os
from dotenv import load_dotenv

load_dotenv()


def _float_env(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    return float(v)


def _int_env(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    return int(float(v))


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

    # Таймауты HTTP к api.telegram.org (отправка сообщений, getMe и т.д.)
    # Значения по умолчанию — «медленный канал»; при нормальной сети можно уменьшить через env.
    TG_CONNECT_TIMEOUT = _float_env("TG_CONNECT_TIMEOUT", 30.0)
    TG_READ_TIMEOUT = _float_env("TG_READ_TIMEOUT", 90.0)
    TG_WRITE_TIMEOUT = _float_env("TG_WRITE_TIMEOUT", 90.0)
    TG_POOL_TIMEOUT = _float_env("TG_POOL_TIMEOUT", 45.0)

    # Long polling: getUpdates ждёт на стороне Telegram до TG_LONG_POLL_TIMEOUT с (макс. 50).
    # HTTP read для этого запроса должен быть > максимального ожидания long poll + запас.
    TG_LONG_POLL_TIMEOUT = max(0, min(50, _int_env("TG_LONG_POLL_TIMEOUT", 40)))
    TG_GET_UPDATES_CONNECT_TIMEOUT = _float_env("TG_GET_UPDATES_CONNECT_TIMEOUT", 30.0)
    TG_GET_UPDATES_READ_TIMEOUT = _float_env("TG_GET_UPDATES_READ_TIMEOUT", 95.0)
    TG_GET_UPDATES_WRITE_TIMEOUT = _float_env("TG_GET_UPDATES_WRITE_TIMEOUT", 90.0)
    TG_GET_UPDATES_POOL_TIMEOUT = _float_env("TG_GET_UPDATES_POOL_TIMEOUT", 45.0)

    # Повторы при старте polling, пока не удастся связаться с Telegram (<0 = бесконечно, как в PTB).
    TG_BOOTSTRAP_RETRIES = _int_env("TG_BOOTSTRAP_RETRIES", -1)


def telegram_http_request():
    """HTTPXRequest с теми же таймаутами и опциональным PROXY_URL (для Bot вне Application, напр. webhook)."""
    from telegram.request import HTTPXRequest

    kwargs = {
        "connect_timeout": Config.TG_CONNECT_TIMEOUT,
        "read_timeout": Config.TG_READ_TIMEOUT,
        "write_timeout": Config.TG_WRITE_TIMEOUT,
        "pool_timeout": Config.TG_POOL_TIMEOUT,
    }
    if Config.PROXY_URL:
        kwargs["proxy"] = Config.PROXY_URL
    return HTTPXRequest(**kwargs)