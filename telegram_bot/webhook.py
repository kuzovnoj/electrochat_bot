# webhook.py
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import uvicorn
import asyncio
import threading
from database import db
from models import Application
from telegram import Bot
from config import Config
from keyboards import get_application_keyboard
import logging

logger = logging.getLogger(__name__)

app = FastAPI()

# Модель данных для вебхука
class SiteApplication(BaseModel):
    name: str
    phone: str
    address: str
    task: str
    comment: Optional[str] = ""
    photo_url: Optional[str] = None
    site_user_id: Optional[str] = None

@app.post("/webhook/application")
async def receive_application(request: Request):
    """Эндпоинт для получения заявок с сайта"""
    try:
        data = await request.json()
        logger.info(f"Получена заявка с сайта: {data}")
        
        # Валидация обязательных полей
        required_fields = ['name', 'phone', 'address', 'task']
        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Отсутствует поле {field}")
        
        # Создаем заявку в формате бота
        user_id = -int(data.get('site_user_id', '0')) or -1
        
        application = Application(
            user_id=user_id,
            username=data['name'],
            address=data['address'],
            phone=data['phone'],
            task=data['task'],
            comment=data.get('comment', ''),
            photo_file_id=None
        )
        
        # Сохраняем в БД
        app_id = db.create_application(application)
        logger.info(f"Заявка #{app_id} сохранена в БД")
        
        # Отправляем в групповой чат (в отдельном потоке)
        threading.Thread(
            target=send_to_group_sync,
            args=(app_id, application, data.get('photo_url'))
        ).start()
        
        return {"status": "success", "application_id": app_id}
        
    except Exception as e:
        logger.error(f"Ошибка обработки заявки: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def send_to_group_sync(app_id: int, application: Application, photo_url: Optional[str] = None):
    """Синхронная обертка для отправки в группу"""
    try:
        # Создаем новый event loop для потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Запускаем асинхронную отправку
        loop.run_until_complete(send_to_group(app_id, application, photo_url))
        loop.close()
    except Exception as e:
        logger.error(f"Ошибка отправки в группу: {e}")

async def send_to_group(app_id: int, application: Application, photo_url: Optional[str] = None):
    """Отправка заявки в групповой чат"""
    bot = Bot(token=Config.BOT_TOKEN)
    
    # Формируем текст заявки
    message_text = (
        f"Новая заявка #{app_id} (с сайта)\n\n"
        f"Адрес: {application.address}\n"
        f"Задача: {application.task}\n"
    )
    
    if application.comment and application.comment.strip():
        message_text += f"Комментарий: {application.comment}\n"
    
    message_text += f"От: {application.username}"
    
    keyboard = get_application_keyboard(app_id)
    
    # Отправляем в группу
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