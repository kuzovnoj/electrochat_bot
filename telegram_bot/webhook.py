from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Optional
import uvicorn
import asyncio
import threading
import base64
import tempfile
import os
from database import db
from models import Application
from telegram import Bot, InputFile
from config import Config
from keyboards import get_application_keyboard
import logging
import aiofiles

logger = logging.getLogger(__name__)

app = FastAPI()

# 👇 Настройка заголовка для API ключа
api_key_header = APIKeyHeader(name='X-API-Key', auto_error=False)

# 👇 Функция проверки ключа
async def verify_api_key(api_key: str = Depends(api_key_header)):
    if not api_key:
        logger.warning("Запрос без API ключа")
        raise HTTPException(
            status_code=403,
            detail="API ключ отсутствует"
        )
    
    if api_key != Config.API_KEY:
        logger.warning(f"Неверный API ключ: {api_key}")
        raise HTTPException(
            status_code=403,
            detail="Неверный API ключ"
        )
    
    return api_key

class SiteApplication(BaseModel):
    name: str
    phone: str
    address: str
    task: str
    comment: Optional[str] = ""
    photo_base64: Optional[str] = None
    photo_filename: Optional[str] = None
    site_user_id: Optional[str] = None

# 👇 Добавьте зависимость verify_api_key к эндпоинту
@app.post("/webhook/application")
async def receive_application(
    request: Request,
    api_key: str = Depends(verify_api_key)  # 👈 Проверка ключа
):
    """Эндпоинт для получения заявок с сайта"""
    try:
        data = await request.json()
        logger.info(f"Получена заявка с сайта: {data.get('name')}, фото: {'есть' if data.get('photo_base64') else 'нет'}")
        
        # Валидация обязательных полей
        required_fields = ['name', 'phone', 'address', 'task']
        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Отсутствует поле {field}")
        
        # Создаем заявку в формате бота
        user_id = -int(data.get('site_user_id', '0')) or -1
        
        # Если есть фото в base64 - сохраняем временно и получаем file_id
        photo_file_id = None
        if data.get('photo_base64'):
            try:
                photo_file_id = await save_base64_photo(data['photo_base64'])
                logger.info(f"Фото сохранено, file_id: {photo_file_id}")
            except Exception as e:
                logger.error(f"Ошибка сохранения фото: {e}")
        
        application = Application(
            user_id=user_id,
            username=data['name'],
            address=data['address'],
            phone=data['phone'],
            task=data['task'],
            comment=data.get('comment', ''),
            photo_file_id=photo_file_id
        )
        
        # Сохраняем в БД
        app_id = db.create_application(application)
        logger.info(f"Заявка #{app_id} сохранена в БД")
        
        # Отправляем в групповой чат
        threading.Thread(
            target=send_to_group_sync,
            args=(app_id, application, photo_file_id)
        ).start()
        
        return {"status": "success", "application_id": app_id}
        
    except HTTPException:
        raise  # Пробрасываем HTTP исключения
    except Exception as e:
        logger.error(f"Ошибка обработки заявки: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 👇 Добавьте защищенный эндпоинт для проверки
@app.get("/health")
async def health(api_key: str = Depends(verify_api_key)):
    """Проверка работоспособности с аутентификацией"""
    return {"status": "healthy", "authenticated": True}

# 👇 Открытый эндпоинт (без аутентификации) для базовой проверки
@app.get("/ping")
async def ping():
    """Проверка что сервер жив (без аутентификации)"""
    return {"status": "alive"}

async def save_base64_photo(base64_string: str) -> str:
    """Сохраняет фото из base64 и возвращает file_id для Telegram"""
    try:
        # Декодируем base64
        photo_data = base64.b64decode(base64_string)
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            tmp_file.write(photo_data)
            tmp_path = tmp_file.name
        
        # Отправляем фото в Telegram (как временный файл)
        bot = Bot(token=Config.BOT_TOKEN)
        
        # Отправляем фото в специальный чат для получения file_id
        # Можно отправить в любой чат, но лучше создать отдельный для хранения фото
        chat_id = Config.ADMIN_GROUP_CHAT_ID  # Или специальный чат для медиа
        
        with open(tmp_path, 'rb') as f:
            message = await bot.send_photo(
                chat_id=chat_id,
                photo=InputFile(f, filename='photo.jpg'),
                caption="Временное фото для заявки"
            )
        
        # Получаем file_id
        file_id = message.photo[-1].file_id
        
        # Удаляем временный файл
        os.unlink(tmp_path)
        
        return file_id
        
    except Exception as e:
        logger.error(f"Ошибка сохранения фото: {e}")
        raise

def send_to_group_sync(app_id: int, application: Application, photo_file_id: Optional[str] = None):
    """Синхронная обертка для отправки в группу"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_to_group(app_id, application, photo_file_id))
        loop.close()
    except Exception as e:
        logger.error(f"Ошибка отправки в группу: {e}")

async def send_to_group(app_id: int, application: Application, photo_file_id: Optional[str] = None):
    """Отправка заявки в групповой чат"""
    bot = Bot(token=Config.BOT_TOKEN)
    
    # Формируем текст заявки
    message_text = (
        f"Новая заявка #{app_id} \nВнимание!\nЗаявка напрямую от клиента. Не забудьте сделать скидку 10%\n\n"
        f"Адрес: {application.address}\n"
        f"Задача: {application.task}\n"
    )
    
    if application.comment and application.comment.strip():
        message_text += f"Комментарий: {application.comment}\n"
    
    if photo_file_id:
        message_text += f"📸 Фото приложено\n"
    
    message_text += f"От: {application.username}"
    
    keyboard = get_application_keyboard(app_id)
    
    # Отправляем с фото или без
    if photo_file_id:
        sent_message = await bot.send_photo(
            chat_id=Config.ADMIN_GROUP_CHAT_ID,
            photo=photo_file_id,
            caption=message_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    else:
        sent_message = await bot.send_message(
            chat_id=Config.ADMIN_GROUP_CHAT_ID,
            text=message_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    # Сохраняем message_id
    db.set_message_id(app_id, sent_message.message_id)
    logger.info(f"Заявка #{app_id} отправлена в группу")

def run_webhook_server():
    """Запуск FastAPI сервера"""
    uvicorn.run(app, host="0.0.0.0", port=7000)

if __name__ == "__main__":
    run_webhook_server()