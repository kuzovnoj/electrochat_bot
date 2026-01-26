from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from config import Config
from models import Application
from database import db
from keyboards import *
import logging

logger = logging.getLogger(__name__)

# Простое хранилище состояний
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    chat_type = update.message.chat.type
    
    if chat_type in ['group', 'supergroup']:
        keyboard = get_main_keyboard()
        await update.message.reply_text(
            "Привет! Я бот для управления заявками.\n"
            "Используйте меню команд или кнопку ниже, чтобы создать новую заявку.\n\n"
            "⚠️ *Внимание:* Заполнение заявки будет происходить в личном чате с ботом.",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # В личном чате - просто приветствуем
        await update.message.reply_text(
            "Привет! Я бот для управления заявками.\n\n"
            "Теперь вы можете создать заявку. Вернитесь в группу и используйте команду /new или нажмите '📝 Подать заявку'.",
            reply_markup=remove_keyboard()
        )
    return ConversationHandler.END

async def new_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /new - создание заявки из меню"""
    chat_type = update.message.chat.type
    
    if chat_type not in ['group', 'supergroup']:
        await update.message.reply_text(
            "Для создания заявки вернитесь в групповой чат и используйте команду /new там.",
            reply_markup=remove_keyboard()
        )
        return ConversationHandler.END
    
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.full_name
    
    print(f"DEBUG: Команда /new от пользователя {user_id} ({username})")
    
    try:
        # Сохраняем данные для начала процесса
        user_states[user_id] = {
            'step': 'address',
            'username': username,
            'group_message_id': update.message.message_id,
            'group_chat_id': update.message.chat.id
        }
        
        # Отправляем первый вопрос в личку
        await context.bot.send_message(
            chat_id=user_id,
            text=f"Привет {username}, давайте создадим заявку!\n\n"
                 "Введите адрес:\n"
                 "(или отправьте '❌ Отмена' для отмены)",
            reply_markup=get_cancel_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        
        print(f"DEBUG: Сообщение отправлено пользователю {user_id}")
        '''
        # Уведомляем в группе
        await update.message.reply_text(
            f"👤 {username} начал заполнение заявки.\n"
            "Данные запрашиваются в личном чате с ботом."
        )
        '''
        return Config.ADDRESS
        
    except Exception as e:
        print(f"DEBUG: Ошибка при отправке сообщения: {e}")
        
        # Если не удалось отправить - пользователь не начинал диалог
        keyboard = [[
            InlineKeyboardButton(
                "💬 Написать боту в личку", 
                url=f"https://t.me/{context.bot.username}"
            )
        ]]
        
        await update.message.reply_text(
            f"👋 {username},\n\n"
            "Чтобы создать заявку:\n"
            "1. Нажмите кнопку ниже\n"
            "2. Напишите `/start` боту\n"
            "3. Используйте команду /new снова",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Очищаем состояние, если было создано
        if user_id in user_states:
            del user_states[user_id]
        
        return ConversationHandler.END

async def create_application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия на кнопку 'Подать заявку' в группе"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.full_name
    
    print(f"DEBUG: Пользователь {user_id} ({username}) нажал кнопку")
    
    try:
        # Сохраняем данные для начала процесса
        user_states[user_id] = {
            'step': 'address',
            'username': username,
            'group_message_id': query.message.message_id,
            'group_chat_id': query.message.chat.id
        }
        
        # Отправляем первый вопрос в личку
        await context.bot.send_message(
            chat_id=user_id,
            text=f"Привет {username}, давайте создадим заявку!\n\n"
                 "📍 *Введите адрес:*\n"
                 "(или отправьте '❌ Отмена' для отмены)",
            reply_markup=get_cancel_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        
        print(f"DEBUG: Сообщение отправлено пользователю {user_id}")
        '''
        # Уведомляем в группе
        await query.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text=f"👤 {username} начал заполнение заявки.\n"
                 "Данные запрашиваются в личном чате с ботом.",
            reply_to_message_id=query.message.message_id
        )
        '''
        return Config.ADDRESS
        
    except Exception as e:
        print(f"DEBUG: Ошибка при отправке сообщения: {e}")
        
        # Если не удалось отправить - пользователь не начинал диалог
        await query.answer(
            "⚠️ Сначала напишите мне в личные сообщения!",
            show_alert=True
        )
        
        keyboard = [[
            InlineKeyboardButton(
                "💬 Написать боту в личку", 
                url=f"https://t.me/{context.bot.username}"
            )
        ]]
        
        await query.message.reply_text(
            f"👋 {username},\n\n"
            "Чтобы создать заявку:\n"
            "1. Нажмите кнопку ниже\n"
            "2. Напишите `/start` боту\n"
            "3. Нажмите 'Подать заявку' снова",
            reply_markup=InlineKeyboardMarkup(keyboard),
            reply_to_message_id=query.message.message_id
        )
        
        # Очищаем состояние, если было создано
        if user_id in user_states:
            del user_states[user_id]
        
        return ConversationHandler.END


async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех сообщений в личном чате"""
    # Проверяем, что это личный чат
    if update.message.chat.type != 'private':
        return ConversationHandler.END
    
    user_id = update.effective_user.id
    text = update.message.text
    
    print(f"DEBUG: Личное сообщение от {user_id}: {text}")
    print(f"DEBUG: Текущее состояние: {user_states.get(user_id)}")
    
    # Проверяем, есть ли у пользователя активный процесс
    if user_id not in user_states:
        print(f"DEBUG: У пользователя {user_id} нет активного процесса")
        # Если пользователь просто пишет что-то в личку
        if text.lower() in ['/start', 'начать', 'start']:
            await update.message.reply_text(
                "Привет! Я бот для управления заявками.\n\n"
                "Чтобы создать заявку:\n"
                "1. Вернитесь в группу\n"
                "2. Нажмите кнопку '📝 Подать заявку'\n"
                "3. Заполните данные здесь",
                reply_markup=remove_keyboard()
            )
        return ConversationHandler.END
    
    # Проверяем отмену
    if text == '❌ Отмена':
        await handle_cancel(update, context)
        return ConversationHandler.END
    
    # Получаем текущий шаг
    user_data = user_states[user_id]
    current_step = user_data.get('step')
    
    print(f"DEBUG: Текущий шаг: {current_step}")
    
    # Обрабатываем в зависимости от шага
    if current_step == 'address':
        return await process_address(update, context, user_data, text)
    elif current_step == 'phone':
        return await process_phone(update, context, user_data, text)
    elif current_step == 'task':
        return await process_task(update, context, user_data, text)
    elif current_step == 'comment':
        return await process_comment(update, context, user_data, text)
    
    return ConversationHandler.END

async def process_address(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data, text):
    """Обработка адреса"""
    user_id = update.effective_user.id
    
    print(f"DEBUG: Сохраняем адрес: {text}")
    
    # Сохраняем адрес
    user_data['address'] = text
    user_data['step'] = 'phone'
    
    await update.message.reply_text(
        "Введите номер телефона:\n"
        "(или отправьте '❌ Отмена' для отмены)",
        reply_markup=get_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    print(f"DEBUG: Перешли к шагу 'phone'")
    return Config.PHONE

async def process_phone(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data, text):
    """Обработка телефона"""
    user_id = update.effective_user.id
    
    print(f"DEBUG: Сохраняем телефон: {text}")
    
    # Сохраняем телефон
    user_data['phone'] = text
    user_data['step'] = 'task'
    
    await update.message.reply_text(
        "📝 *Опишите задачу:*\n"
        "(или отправьте '❌ Отмена' для отмены)",
        reply_markup=get_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    print(f"DEBUG: Перешли к шагу 'task'")
    return Config.TASK

async def process_task(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data, text):
    """Обработка задачи"""
    user_id = update.effective_user.id
    
    print(f"DEBUG: Сохраняем задачу: {text}")
    
    # Сохраняем задачу
    user_data['task'] = text
    user_data['step'] = 'comment'
    
    await update.message.reply_text(
        "Введите комментарий (или отправьте '-' если комментария нет):\n"
        "(или отправьте '❌ Отмена' для отмены)",
        reply_markup=get_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    print(f"DEBUG: Перешли к шагу 'comment'")
    return Config.COMMENT

async def process_comment(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data, text):
    """Обработка комментария и сохранение заявки"""
    user_id = update.effective_user.id
    
    print(f"DEBUG: Сохраняем комментарий: {text}")
    
    # Сохраняем комментарий
    comment = text if text != '-' else ""
    user_data['comment'] = comment
    
    # Проверяем, что все данные собраны
    required_fields = ['address', 'phone', 'task', 'username']
    if not all(field in user_data for field in required_fields):
        print(f"DEBUG: Не все данные собраны: {user_data}")
        await update.message.reply_text(
            "❌ Ошибка: не все данные собраны. Начните заново.",
            reply_markup=remove_keyboard()
        )
        # Очищаем состояние
        if user_id in user_states:
            del user_states[user_id]
        return ConversationHandler.END
    
    try:
        # Создаем заявку
        application = Application(
            user_id=user_id,
            username=user_data['username'],
            address=user_data['address'],
            phone=user_data['phone'],
            task=user_data['task'],
            comment=user_data['comment']
        )
        
        # Сохраняем в БД
        app_id = db.create_application(application)
        print(f"DEBUG: Заявка #{app_id} создана")
        
        # Подтверждение пользователю
        await update.message.reply_text(
            f"Заявка #{app_id} успешно создана!\n\n"
            f"\n"
            f"Адрес: {application.address}\n"
            f"Телефон: {application.phone}\n"
            f"Задача: {application.task}\n"
            f"Комментарий: {application.comment or 'нет'}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=remove_keyboard()
        )
        
        # Отправляем заявку в общий чат
        keyboard = get_application_keyboard(app_id)
        message_text = (
            f"Новая заявка #{app_id}\n\n"
            f"Адрес: {application.address}\n"
            f"Задача: {application.task}\n"
            f"От: @{application.username}"
        )
        
        sent_message = await context.bot.send_message(
            chat_id=Config.ADMIN_GROUP_CHAT_ID,
            text=message_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
        
        db.set_message_id(app_id, sent_message.message_id)
        
        # Уведомление в исходной группе (если это не та же группа)
        group_chat_id = user_data.get('group_chat_id')
        if group_chat_id and group_chat_id != Config.ADMIN_GROUP_CHAT_ID:
            try:
                await context.bot.send_message(
                    chat_id=group_chat_id,
                    text=f"{application.username} создал заявку #{app_id}."
                )
            except:
                pass
                
    except Exception as e:
        print(f"DEBUG: Ошибка при сохранении заявки: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при создании заявки.\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=remove_keyboard()
        )
    
    # Очищаем состояние
    if user_id in user_states:
        del user_states[user_id]
    
    print(f"DEBUG: Процесс завершен для пользователя {user_id}")
    return ConversationHandler.END

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка отмены"""
    user_id = update.effective_user.id
    
    print(f"DEBUG: Отмена для пользователя {user_id}")
    
    await update.message.reply_text(
        "❌ Создание заявки отменено.",
        reply_markup=remove_keyboard()
    )
    
    # Уведомляем в группе (если есть данные)
    if user_id in user_states:
        user_data = user_states[user_id]
        if user_data.get('group_chat_id') and user_data.get('username'):
            try:
                await context.bot.send_message(
                    chat_id=user_data['group_chat_id'],
                    text=f"❌ {user_data['username']} отменил создание заявки."
                )
            except:
                pass
    
    # Очищаем состояние
    if user_id in user_states:
        del user_states[user_id]
    
    return ConversationHandler.END

async def accept_application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик принятия заявки"""
    query = update.callback_query
    await query.answer()
    
    app_id = int(query.data.split('_')[1])
    application = db.get_application(app_id)
    
    if not application:
        await query.edit_message_text("❌ Заявка не найдена.")
        return
    
    success = db.accept_application(
        app_id, 
        query.from_user.id,
        query.from_user.username or query.from_user.full_name
    )
    
    if success:
        new_text = (
            f"Заявка #{app_id} ПРИНЯТА\n\n"
            f"Адрес: {application['address']}\n"
            f"Задача: {application['task']}\n"
            f"От: {application['username']}\n"
            f"Принял: {query.from_user.username or query.from_user.full_name}"
        )
        
        await query.edit_message_text(text=new_text, parse_mode=ParseMode.MARKDOWN)
        
        # Отправляем данные в личку
        full_info = (
            f"Вы приняли заявку #{app_id}!\n\n"
            f"Данные заявки:\n"
            f"Адрес: {application['address']}\n"
            f"Телефон: {application['phone']}\n"
            f"Задача: {application['task']}\n"
            f"Комментарий: {application['comment'] or 'нет'}\n"
            f"Клиент: {application['username']}"
        )
        
        try:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=full_info,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            await query.message.reply_text(
                f"@{query.from_user.username}, напишите мне в личку для получения данных."
            )
        
        # Уведомляем создателя
        if query.from_user.id != application['user_id']:
            try:
                await context.bot.send_message(
                    chat_id=application['user_id'],
                    text=f"Ваша заявка #{app_id} принята!\n"
                         f"Исполнитель: {query.from_user.username or query.from_user.full_name}"
                )
            except:
                pass
    else:
        await query.answer("⚠️ Заявка уже принята!", show_alert=True)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда помощи"""
    help_text = (
        "Помощь по использованию бота:\n\n"
        "*В группе:*\n"
        "Нажмите 'Подать заявку' для создания новой заявки\n"
        "Нажмите 'Принять заявку' чтобы взять задание\n\n"
        "В личном чате:\n"
        "Здесь вы заполняете данные заявки\n"
        "Используйте '❌ Отмена' для отмены\n\n"
        "*Команды:*\n"
        "`/start` - начать работу\n"
        "`/help` - помощь\n"
        "`/cancel` - отмена"
    )
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}", exc_info=True)
    try:
        await update.effective_message.reply_text("⚠️ Произошла ошибка.")
    except:
        pass