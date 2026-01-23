from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from config import Config
from models import Application
from database import db
from keyboards import *

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    if update.message.chat.type in ['group', 'supergroup']:
        keyboard = get_main_keyboard()
        await update.message.reply_text(
            "👋 Привет! Я бот для управления заявками.\n"
            "Нажмите кнопку ниже, чтобы создать новую заявку.",
            reply_markup=keyboard
        )
    return ConversationHandler.END

async def create_application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия на кнопку 'Подать заявку'"""
    query = update.callback_query
    await query.answer()
    
    # Проверяем, что пользователь нажал из группового чата
    if query.message.chat.type in ['group', 'supergroup']:
        # Отправляем пользователю сообщение в личку для начала заполнения
        try:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text="Давайте создадим заявку. Пожалуйста, введите адрес:",
                reply_markup=get_cancel_keyboard()
            )
            context.user_data['creating_application'] = True
            context.user_data['username'] = query.from_user.username or query.from_user.full_name
            return Config.ADDRESS
        except Exception as e:
            await query.message.reply_text(
                "⚠️ Пожалуйста, начните диалог со мной в личных сообщениях, "
                "чтобы я мог отправить вам форму для заявки. "
                "Напишите мне @electrochat_bot в личку."
            )
            return ConversationHandler.END
    
    return ConversationHandler.END

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение адреса"""
    if update.message.text == '❌ Отмена':
        await update.message.reply_text("Создание заявки отменено.", reply_markup=remove_keyboard())
        return ConversationHandler.END
    
    context.user_data['address'] = update.message.text
    await update.message.reply_text("Введите номер телефона:")
    return Config.PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение телефона"""
    if update.message.text == '❌ Отмена':
        await update.message.reply_text("Создание заявки отменено.", reply_markup=remove_keyboard())
        return ConversationHandler.END
    
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("Опишите задачу:")
    return Config.TASK

async def get_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение описания задачи"""
    if update.message.text == '❌ Отмена':
        await update.message.reply_text("Создание заявки отменено.", reply_markup=remove_keyboard())
        return ConversationHandler.END
    
    context.user_data['task'] = update.message.text
    await update.message.reply_text("Введите комментарий (если необходимо):")
    return Config.COMMENT

async def get_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение комментария и сохранение заявки"""
    if update.message.text == '❌ Отмена':
        await update.message.reply_text("Создание заявки отменено.", reply_markup=remove_keyboard())
        return ConversationHandler.END
    
    context.user_data['comment'] = update.message.text
    
    # Создаем объект заявки
    application = Application(
        user_id=update.effective_user.id,
        username=context.user_data['username'],
        address=context.user_data['address'],
        phone=context.user_data['phone'],
        task=context.user_data['task'],
        comment=context.user_data['comment']
    )
    
    # Сохраняем в БД
    app_id = db.create_application(application)
    
    # Отправляем подтверждение пользователю
    await update.message.reply_text(
        "✅ Ваша заявка успешно создана и отправлена в общий чат!",
        reply_markup=remove_keyboard()
    )
    
    # Отправляем заявку в общий чат (только адрес и задача)
    keyboard = get_application_keyboard(app_id)
    message_text = (
        f"📋 Новая заявка #{app_id}\n\n"
        f"📍 Адрес: {application.address}\n"
        f"📝 Задача: {application.task}\n"
        f"👤 От: {application.username}"
    )
    
    sent_message = await context.bot.send_message(
        chat_id=Config.ADMIN_GROUP_CHAT_ID,
        text=message_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    # Сохраняем ID сообщения для возможности редактирования
    db.set_message_id(app_id, sent_message.message_id)
    
    # Очищаем данные пользователя
    context.user_data.clear()
    
    return ConversationHandler.END

async def accept_application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик принятия заявки"""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем ID заявки из callback_data
    app_id = int(query.data.split('_')[1])
    
    # Получаем данные заявки
    application = db.get_application(app_id)
    
    if not application:
        await query.edit_message_text("Заявка не найдена или уже принята.")
        return
    
    # Пытаемся принять заявку
    success = db.accept_application(
        app_id, 
        query.from_user.id,
        query.from_user.username or query.from_user.full_name
    )
    
    if success:
        # Редактируем сообщение в групповом чате
        new_text = (
            f"📋 Заявка #{app_id} ПРИНЯТА\n\n"
            f"📍 Адрес: {application['address']}\n"
            f"📝 Задача: {application['task']}\n"
            f"👤 От: {application['username']}\n"
            f"✅ Принял: {query.from_user.username or query.from_user.full_name}"
        )
        
        await query.edit_message_text(
            text=new_text,
            parse_mode=ParseMode.HTML
        )
        
        # Отправляем полные данные принявшему пользователю в личку
        full_info = (
            f"🎉 Вы приняли заявку #{app_id}!\n\n"
            f"📍 Адрес: {application['address']}\n"
            f"📞 Телефон: {application['phone']}\n"
            f"📝 Задача: {application['task']}\n"
            f"💬 Комментарий: {application['comment'] or 'нет'}\n"
            f"👤 Клиент: {application['username']}\n\n"
            f"⚠️ Не забудьте связаться с клиентом!"
        )
        
        try:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=full_info,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            # Если не удалось отправить в личку, сообщаем в группе
            await query.message.reply_text(
                f"@{query.from_user.username}, я не могу отправить вам личное сообщение. "
                "Пожалуйста, напишите мне в личку, чтобы получить данные заявки."
            )
    else:
        await query.answer("Заявка уже принята кем-то другим!", show_alert=True)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена создания заявки"""
    await update.message.reply_text(
        "Создание заявки отменено.",
        reply_markup=remove_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    print(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка. Пожалуйста, попробуйте позже."
        )

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отладочная команда"""
    chat_id = update.message.chat.id
    chat_type = update.message.chat.type
    chat_title = update.message.chat.title
    
    await update.message.reply_text(
        f"📊 Отладка:\n"
        f"Chat ID: {chat_id}\n"
        f"Тип чата: {chat_type}\n"
        f"Название: {chat_title}\n"
        f"Пользователь: {update.effective_user.username}"
    )