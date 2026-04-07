# site_api.py
import httpx
import logging
from config import Config

logger = logging.getLogger(__name__)

async def notify_site_assign(site_order_id: int, telegram_user_id: int, telegram_username: str = None):
    """
    Уведомить сайт о том, что мастер взял заявку
    Возвращает (success, error_message)
    """
    url = f"https://{Config.SITE_DOMAIN}/api/bot/assign-order/"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": Config.API_KEY
    }
    payload = {
        "order_id": site_order_id,
        "telegram_user_id": telegram_user_id
    }
    if telegram_username:
        payload["telegram_username"] = telegram_username
    
    logger.info(f"Вызов API сайта: {url}, order_id={site_order_id}, user_id={telegram_user_id}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
        logger.info(f"Ответ сайта: status={response.status_code}, body={response.text}")
        
    except httpx.TimeoutException:
        logger.error(f"Таймаут при вызове API сайта: {url}")
        return False, "Сайт не ответил вовремя. Попробуйте позже."
    except httpx.ConnectError as e:
        logger.error(f"Ошибка подключения к сайту: {e}")
        return False, "Не удалось подключиться к сайту. Проверьте соединение."
    except Exception as e:
        logger.error(f"Неизвестная ошибка при вызове API: {e}")
        return False, f"Ошибка связи: {str(e)}"
    
    # Обработка статусов ответа
    if response.status_code == 200:
        logger.info(f"Заявка #{site_order_id} успешно назначена мастеру {telegram_user_id}")
        return True, None
        
    elif response.status_code == 403:
        logger.error(f"Ошибка аутентификации: неверный API_KEY")
        return False, "Ошибка аутентификации бота на сайте. Сообщите администратору."
        
    elif response.status_code == 404:
        try:
            data = response.json()
            detail = data.get('detail', '')
        except:
            detail = response.text
            
        if 'master_not_linked' in detail:
            return False, "❌ Ваш Telegram не привязан к аккаунту на сайте.\n\nПожалуйста, в личном кабинете на сайте укажите ваш Telegram username (без @) и повторите попытку."
        elif 'order_not_found' in detail:
            return False, "❌ Заявка на сайте не найдена. Возможно, она была удалена."
        else:
            return False, f"❌ Ошибка на сайте: {detail}"
            
    elif response.status_code == 409:
        try:
            data = response.json()
            detail = data.get('detail', '')
        except:
            detail = response.text
            
        if 'already_assigned' in detail:
            return False, "⚠️ Эта заявка уже назначена другому мастеру."
        elif 'telegram_id_mismatch' in detail:
            return False, "⚠️ Конфликт привязки аккаунта. Обратитесь к администратору."
        else:
            return False, f"⚠️ Конфликт: {detail}"
            
    else:
        return False, f"❌ Ошибка сайта (код {response.status_code}). Попробуйте позже."