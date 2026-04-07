from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from config import Config
from models import Application
from database import db
from keyboards import *
import logging
from site_api import notify_site_assign
import httpx

logger = logging.getLogger(__name__)

# Простое хранилище состояний
user_states = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    chat_type = update.message.chat.type
    args = context.args  # Получаем аргументы команды
    user_id = update.effective_user.id
    
    if chat_type == 'private':
        # Проверяем, если есть параметр с номером заявки (app_123) или токен (token_xxxx)
        app_data = None
        token_data = None
        
        if args and len(args) > 0:
            for arg in args:
                if arg.startswith('app_'):
                    try:
                        app_data = int(arg.split('_')[1])
                        break
                    except:
                        pass
                elif arg.startswith('token_'):
                    token_data = arg.split('_')[1]
                    break
        
        from keyboards import get_private_chat_keyboard

        keyboard = [[InlineKeyboardButton("Создать заявку", callback_data='create_application')]]
        
        welcome_text = (
            "Привет! Я бот для управления заявками.\n\n"
            "В этом чате вы можете:\n"
            "Создать новую заявку\n"
            "Получить уведомления о статусе ваших заявок\n"
            "Получать данные принятых заявок\n\n"
        )
        
        # Если пользователь пришел по токену
        if token_data and 'app_tokens' in context.bot_data:
            token_info = context.bot_data['app_tokens'].get(token_data)
            
            if token_info:
                # Проверяем срок действия токена
                import time
                if time.time() > token_info['expires']:
                    await update.message.reply_text(
                        "❌ Срок действия ссылки истек.\n"
                        "Пожалуйста, примите заявку заново в группе.",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    # Удаляем просроченный токен
                    del context.bot_data['app_tokens'][token_data]
                    return ConversationHandler.END
                
                # Проверяем, что токен предназначен этому пользователю
                if token_info['user_id'] != user_id:
                    await update.message.reply_text(
                        "❌ Эта ссылка предназначена другому пользователю.\n"
                        "Только пользователь, принявший заявку, может получить данные.",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return ConversationHandler.END
                
                # Получаем данные заявки
                app_data = token_info['app_id']
                application = db.get_application(app_data)
                
                if application:
                    # Проверяем, принял ли этот пользователь заявку
                    is_accepted_by_user = db.check_application_owner(app_data, user_id)
                    
                    if not is_accepted_by_user:
                        await update.message.reply_text(
                            "❌ У вас нет доступа к данным этой заявки.",
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode=ParseMode.MARKDOWN
                        )
                        return ConversationHandler.END
                    
                    welcome_text += f"✅ Вы приняли заявку #{app_data}\n\n"
                    
                    await update.message.reply_text(
                        welcome_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    # Добавляем данные заявки
                    full_info = (
                        f"Данные заявки #{app_data}:\n\n"
                        f"Адрес: {application['address']}\n"
                        f"Телефон: {application['phone']}\n"
                        f"Задача: {application['task']}\n"
                        f"Комментарий: {application['comment'] or 'нет'}\n"
                        f"Отправитель: @{application['username']}"
                    )
                    
                    await update.message.reply_text(
                        full_info,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    # Если есть фото, отправляем его
                    if application.get('photo_file_id'):
                        await context.bot.send_photo(
                            chat_id=user_id,
                            photo=application['photo_file_id'],
                            caption=f"Фото к заявке #{app_data}"
                        )
                    
                    # Удаляем использованный токен
                    del context.bot_data['app_tokens'][token_data]
                
                    # Добавляем кнопку для сохранения контакта
                    contact_keyboard = [
                        [InlineKeyboardButton("📝 Создать свою заявку", callback_data='create_application')],
                    ]
                    return ConversationHandler.END
        
        # Если пользователь пришел по прямой ссылке с номером заявки
        if app_data:
            application = db.get_application(app_data)
            if application:
                # Проверяем, принял ли этот пользователь заявку
                is_accepted_by_user = db.check_application_owner(app_data, user_id)
                
                if not is_accepted_by_user:
                    await update.message.reply_text(
                        "❌ У вас нет доступа к данным этой заявки.\n"
                        "Только пользователь, принявший заявку, может просматривать ее данные.",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return ConversationHandler.END
                
                welcome_text += f"✅ Вы приняли заявку #{app_data}\n\n"
                
                await update.message.reply_text(
                    welcome_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Добавляем данные заявки
                full_info = (
                    f"Данные заявки #{app_data}:\n\n"
                    f"Адрес: {application['address']}\n"
                    f"Телефон: {application['phone']}\n"
                    f"Задача: {application['task']}\n"
                    f"Комментарий: {application['comment'] or 'нет'}\n"
                    f"Клиент: {application['username']}"
                )
                
                await update.message.reply_text(
                    full_info,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Если есть фото, отправляем его
                if application.get('photo_file_id'):
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=application['photo_file_id'],
                        caption=f"Фото к заявке #{app_data}"
                    )
                
                # Добавляем кнопку для сохранения контакта
                contact_keyboard = [
                    [InlineKeyboardButton("📝 Создать свою заявку", callback_data='create_application')],
                ]
                return ConversationHandler.END
        
        
        # Стандартное приветствие
        await update.message.reply_text(
            "Привет! Я бот для управления заявками.\n\n"
            "В этом чате вы можете:\n"
            "• Создать новую заявку\n"
            "• Просмотреть взятые вами заявки\n"
            "• Просмотреть ваши отправленные заявки\n"
            "• Получить уведомления о статусе заявок\n\n"
            "Выберите действие:",
            reply_markup=get_private_chat_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # В групповом чате - просто приветствуем
        await update.message.reply_text(
            "Привет! Я бот для управления заявками.\n\n"
            "Здесь отображаются новые заявки, которые можно принять.\n"
            "Для создания заявки напишите мне в личные сообщения.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    return ConversationHandler.END

async def new_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /new - создание заявки"""
    chat_type = update.message.chat.type
    
    if chat_type != 'private':
        await update.message.reply_text(
            "❌ Для создания заявки напишите мне в личные сообщения (@Electrochat).",
            reply_markup=remove_keyboard()
        )
        return ConversationHandler.END
    
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.full_name
    
    print(f"DEBUG: Команда /new от пользователя {user_id} ({username}) в личном чате")
    
    # Начинаем процесс создания заявки
    user_states[user_id] = {
        'step': 'address',
        'username': username,
        'chat_type': 'private'
    }
    
    # Отправляем первый вопрос
    await update.message.reply_text(
        f"Создание новой заявки\n\n"
        "Шаг 1 из 5: Введите адрес:\n"
        "(или отправьте '❌ Отмена' для отмены)",
        reply_markup=get_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    return Config.ADDRESS

async def create_application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия на кнопку 'Создать заявку' в личном чате"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.full_name
    
    # Проверяем, что это личный чат
    if query.message.chat.type != 'private':
        await query.answer(
            "❌ Эта кнопка работает только в личном чате с ботом",
            show_alert=True
        )
        return
    
    print(f"DEBUG: Пользователь {user_id} ({username}) начал создание заявки")
    
    # Начинаем процесс создания заявки
    user_states[user_id] = {
        'step': 'address',
        'username': username,
        'chat_type': 'private'
    }
    
    # Отправляем первый вопрос
    await query.message.edit_text(
        f"Создание новой заявки\n\n"
        "Шаг 1 из 5: Введите адрес:\n"
        "(или отправьте '❌ Отмена' для отмены)",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Отправляем новое сообщение с клавиатурой для ввода
    await context.bot.send_message(
        chat_id=user_id,
        text="Введите адрес выполнения работ:",
        reply_markup=get_cancel_keyboard()
    )
    
    return Config.ADDRESS

async def handle_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка адреса"""
    user_id = update.effective_user.id
    
    # Проверяем, есть ли у пользователя активный процесс
    if user_id not in user_states:
        await update.message.reply_text(
            "❌ Нет активного процесса создания заявки.\n"
            "Используйте /new или кнопку 'Создать заявку'",
            reply_markup=remove_keyboard()
        )
        return ConversationHandler.END
    
    text = update.message.text
    print(f"DEBUG: Сохраняем адрес: {text}")
    
    # Сохраняем адрес
    user_states[user_id]['address'] = text
    user_states[user_id]['step'] = 'phone'
    
    await update.message.reply_text(
        "Шаг 2 из 5: Введите номер телефона:\n"
        "(формат: +7XXXXXXXXXX или 8XXXXXXXXXX)\n"
        "(или отправьте '❌ Отмена' для отмены)",
        reply_markup=get_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    print(f"DEBUG: Перешли к шагу 'phone'")
    return Config.PHONE

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка телефона"""
    user_id = update.effective_user.id
    
    if user_id not in user_states:
        await update.message.reply_text(
            "❌ Нет активного процесса создания заявки.",
            reply_markup=remove_keyboard()
        )
        return ConversationHandler.END
    
    text = update.message.text
    print(f"DEBUG: Сохраняем телефон: {text}")
    
    # Простая валидация номера телефона
    phone = text.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    # Сохраняем телефон
    user_states[user_id]['phone'] = phone
    user_states[user_id]['step'] = 'task'
    
    await update.message.reply_text(
        "Шаг 3 из 5: Опишите задачу:\n"
        "(подробно опишите, что нужно сделать)\n"
        "(или отправьте '❌ Отмена' для отмены)",
        reply_markup=get_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    print(f"DEBUG: Перешли к шагу 'task'")
    return Config.TASK

async def handle_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка задачи"""
    user_id = update.effective_user.id
    
    if user_id not in user_states:
        await update.message.reply_text(
            "❌ Нет активного процесса создания заявки.",
            reply_markup=remove_keyboard()
        )
        return ConversationHandler.END
    
    text = update.message.text
    print(f"DEBUG: Сохраняем задачу: {text}")
    
    # Сохраняем задачу
    user_states[user_id]['task'] = text
    user_states[user_id]['step'] = 'comment'
    
    await update.message.reply_text(
        "Шаг 4 из 5: Введите комментарий:\n"
        "(дополнительная информация, особенности и т.д.)\n"
        "(отправьте '-' если комментария нет)\n"
        "(или отправьте '❌ Отмена' для отмены)",
        reply_markup=get_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    print(f"DEBUG: Перешли к шагу 'comment'")
    return Config.COMMENT

async def handle_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка комментария"""
    user_id = update.effective_user.id
    
    if user_id not in user_states:
        await update.message.reply_text(
            "❌ Нет активного процесса создания заявки.",
            reply_markup=remove_keyboard()
        )
        return ConversationHandler.END
    
    text = update.message.text
    print(f"DEBUG: Сохраняем комментарий: {text}")
    
    # Сохраняем комментарий
    comment = text if text != '-' else ""
    user_states[user_id]['comment'] = comment
    user_states[user_id]['step'] = 'photo_choice'
    
    # Спрашиваем, нужно ли добавить фото
    await update.message.reply_text(
        "Шаг 5 из 5: Хотите добавить фото к заявке?\n"
        "(фото поможет исполнителю лучше понять задачу)",
        reply_markup=get_photo_choice_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    print(f"DEBUG: Перешли к шагу 'photo_choice'")
    return Config.PHOTO

async def handle_photo_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора - добавлять фото или нет"""
    user_id = update.effective_user.id
    
    if user_id not in user_states:
        await update.message.reply_text(
            "❌ Нет активного процесса создания заявки.",
            reply_markup=remove_keyboard()
        )
        return ConversationHandler.END
    
    choice = update.message.text.lower()
    
    if choice in ['да', '✅ да', 'yes']:
        # Пользователь хочет добавить фото
        user_states[user_id]['need_photo'] = True
        await update.message.reply_text(
            "📸 Отправьте фото:",
            reply_markup=get_cancel_keyboard()
        )
        return Config.PHOTO  # Остаемся в том же состоянии, но теперь ожидаем фото
    else:
        # Пользователь не хочет добавлять фото
        user_states[user_id]['need_photo'] = False
        user_states[user_id]['photo_file_id'] = None
        # Сохраняем заявку без фото
        return await save_application(update, context)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка получения фото"""
    user_id = update.effective_user.id
    
    if user_id not in user_states:
        await update.message.reply_text(
            "❌ Нет активного процесса создания заявки.",
            reply_markup=remove_keyboard()
        )
        return ConversationHandler.END
    
    # Получаем фото
    if update.message.photo:
        # Берем фото в максимальном размере (последнее в списке)
        photo_file_id = update.message.photo[-1].file_id
        user_states[user_id]['photo_file_id'] = photo_file_id
        
        # Подтверждаем получение фото
        await update.message.reply_text(
            "✅ Фото получено!",
            reply_markup=remove_keyboard()
        )
        
        # Сохраняем заявку с фото
        return await save_application(update, context)
    else:
        # Если прислали не фото
        await update.message.reply_text(
            "❌ Пожалуйста, отправьте фото или нажмите '❌ Отмена'",
            reply_markup=get_cancel_keyboard()
        )
        return Config.PHOTO

async def save_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение заявки"""
    user_id = update.effective_user.id
    
    try:
        user_data = user_states[user_id]
        
        # Проверяем, что все необходимые данные собраны
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
        
        # Создаем заявку
        application = Application(
            user_id=user_id,
            username=user_data['username'],
            address=user_data['address'],
            phone=user_data['phone'],
            task=user_data['task'],
            comment=user_data.get('comment', ''),
            photo_file_id=user_data.get('photo_file_id')
        )
        
        # Сохраняем в БД
        app_id = db.create_application(application)
        print(f"DEBUG: Заявка #{app_id} создана")
        
        # Подтверждение пользователю
        photo_text = "\n📸 Фото приложено" if application.photo_file_id else ""
        await update.message.reply_text(
            f"✅ Заявка #{app_id} успешно создана!\n\n"
            f"Детали заявки:\n"
            f"Адрес: {application.address}\n"
            f"Телефон: {application.phone}\n"
            f"Задача: {application.task}\n"
            f"Комментарий: {application.comment or 'нет'}{photo_text}\n\n"
            f"Заявка отправлена в группу исполнителей.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=remove_keyboard()
        )
        
        # Создаем клавиатуру для заявки
        keyboard = get_application_keyboard(app_id)
        
        # Формируем текст с комментарием
        message_text = (
            f"Новая заявка #{app_id}\n\n"
            f"Адрес: {application.address}\n"
            f"Задача: {application.task}\n"
        )
        
        # Добавляем комментарий, если он есть
        if application.comment and application.comment.strip():
            message_text += f"Комментарий: {application.comment}\n"
        
        # Добавляем информацию об отправителе
        message_text += f"От: @{application.username}"
        
        # Отправляем заявку в группу
        try:
            if application.photo_file_id:
                # Если есть фото - отправляем с caption
                sent_message = await context.bot.send_photo(
                    chat_id=Config.ADMIN_GROUP_CHAT_ID,
                    photo=application.photo_file_id,
                    caption=message_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN
                )
                # Сохраняем информацию, что это сообщение с фото
                context.bot_data[f'app_{app_id}_has_photo'] = True
            else:
                # Если нет фото - отправляем текстовое сообщение
                sent_message = await context.bot.send_message(
                    chat_id=Config.ADMIN_GROUP_CHAT_ID,
                    text=message_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN
                )
                context.bot_data[f'app_{app_id}_has_photo'] = False
            
            # Сохраняем ID сообщения в базе данных
            db.set_message_id(app_id, sent_message.message_id)
            
        except Exception as e:
            print(f"DEBUG: Ошибка при отправке в группу: {e}")
            await update.message.reply_text(
                "❌ Ошибка при отправке заявки в группу. Администратор уведомлен."
            )
                
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
    
    # Создаем кнопку для новой заявки
    keyboard = [[InlineKeyboardButton("📝 Создать заявку", callback_data='create_application')]]
    
    await update.message.reply_text(
        "Можете создать новую заявку:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
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
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.full_name
    
    if not application:
        await query.edit_message_text("❌ Заявка не найдена.")
        return

    # Проверяем, не взята ли уже
    if application['status'] == 'accepted':
        await query.answer("⚠️ Эту заявку уже кто-то взял!", show_alert=True)
        return
    
    # Получаем ID заявки на сайте
    site_order_id = application.get('site_order_id')
    if site_order_id:
        # Заявка с сайта — уведомляем сайт
        success, error_msg = await notify_site_assign(
            site_order_id=site_order_id,
            telegram_user_id=user_id,
            telegram_username=username
        )
        
        if not success:
            await query.answer(error_msg, show_alert=True)
            return
    else:
        # Заявка из бота — не синхронизируем с сайтом
        logger.info(f"Заявка #{app_id} создана в боте, site_order_id отсутствует")
        
    success = db.accept_application(
        app_id, 
        user_id,
        query.from_user.username or query.from_user.full_name
    )
    
    if success:
        # Формируем новый текст для сообщения
        new_text = (
            f"Заявка #{app_id} ПРИНЯТА\n\n"
            f"Адрес: {application['address']}\n"
            f"Задача: {application['task']}\n"
        )
        
        # Добавляем комментарий, если он есть
        if application['comment'] and application['comment'].strip():
            new_text += f"Комментарий: {application['comment']}\n"
        
        # Добавляем информацию об отправителе и исполнителе
        new_text += f"От: @{application['username']}\n"
        new_text += f"Принял: @{query.from_user.username or query.from_user.full_name}"
        
        try:
            # Проверяем, было ли сообщение с фото или текстом
            if application.get('photo_file_id'):
                # Если это было сообщение с фото, редактируем caption
                await query.edit_message_caption(
                    caption=new_text,
                    reply_markup=None  # Убираем клавиатуру
                )
            else:
                # Если это было текстовое сообщение, редактируем текст
                await query.edit_message_text(
                    text=new_text,
                    reply_markup=None,  # Убираем клавиатуру
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            print(f"DEBUG: Ошибка при редактировании сообщения: {e}")
            # Если не удалось отредактировать, пробуем отправить новое сообщение
            try:
                if application.get('photo_file_id'):
                    await context.bot.send_photo(
                        chat_id=Config.ADMIN_GROUP_CHAT_ID,
                        photo=application['photo_file_id'],
                        caption=new_text,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await context.bot.send_message(
                        chat_id=Config.ADMIN_GROUP_CHAT_ID,
                        text=new_text,
                        parse_mode=ParseMode.MARKDOWN
                    )
            except Exception as e2:
                print(f"DEBUG: Не удалось отправить новое сообщение: {e2}")
        
        # Пытаемся отправить данные в личку с кнопками
        try:
            # Импортируем клавиатуру управления заявкой
            from keyboards import get_application_management_keyboard
            
            full_info = (
                f"Вы приняли заявку #{app_id}!\n\n"
                f"Данные заявки:\n"
                f"Адрес: {application['address']}\n"
                f"Телефон: {application['phone']}\n"
                f"Задача: {application['task']}\n"
                f"Комментарий: {application['comment'] or 'нет'}\n"
                f"Отправитель: @{application['username']}\n\n"
                f"Если по какой-то причине вы не можете выполнить заявку, "
                f"вы можете вернуть ее в общий чат или закрыть после выполнения."
            )
            
            # Отправляем сообщение в личку с кнопками управления
            await context.bot.send_message(
                chat_id=user_id,
                text=full_info,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_application_management_keyboard(app_id)
            )
            
            # Если есть фото, отправляем его в личку
            if application.get('photo_file_id'):
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=application['photo_file_id'],
                    caption=f"Фото к заявке #{app_id}"
                )
            
            # Сообщение в группе, что данные отправлены
            await query.message.reply_text(
                f"{query.from_user.username or query.from_user.full_name}, "
                f"данные заявки #{app_id} отправлены вам в личные сообщения.",
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=query.message.message_id
            )
            
        except Exception as e:
            print(f"DEBUG: Не удалось отправить в личку: {e}")
            
            # Создаем ссылку с временным токеном
            import hashlib
            import time
            
            # Создаем уникальный токен для этой заявки и пользователя
            token_data = f"{app_id}_{user_id}_{int(time.time())}"
            token_hash = hashlib.md5(token_data.encode()).hexdigest()[:8]
            
            # Сохраняем в контексте временную связку токен-пользователь-заявка
            if 'app_tokens' not in context.bot_data:
                context.bot_data['app_tokens'] = {}
            
            # Сохраняем на 1 час (3600 секунд)
            context.bot_data['app_tokens'][token_hash] = {
                'app_id': app_id,
                'user_id': user_id,
                'expires': time.time() + 3600
            }
            
            # Создаем кнопку для начала диалога с ботом
            start_button = InlineKeyboardButton(
                "💬 Получить данные заявки", 
                url=f"https://t.me/{context.bot.username}?start=token_{token_hash}"
            )
            keyboard = InlineKeyboardMarkup([[start_button]])
            
            reply_msg = await query.message.reply_text(
                f"{query.from_user.username or query.from_user.full_name}, "
                f"вы приняли заявку #{app_id}, но у вас нет диалога с ботом.\n\n"
                f"Чтобы получить данные заявки:\n"
                f"1. Нажмите кнопку ниже\n"
                f"2. Напишите `/start` боту\n"
                f"3. Данные заявки будут отправлены автоматически\n\n"
                f"⚠️ *Внимание:* Эта ссылка действительна только для вас в течение 1 часа.",
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=query.message.message_id
            )
            
            # Сохраняем ID сообщения
            context.bot_data[f'app_{app_id}_message'] = {
                'message_id': reply_msg.message_id,
                'chat_id': query.message.chat.id,
                'user_id': user_id
            }
        
        # Уведомляем создателя заявки
        if user_id != application['user_id']:
            try:
                await context.bot.send_message(
                    chat_id=application['user_id'],
                    text=f"✅ Ваша заявка #{app_id} принята!\n"
                         f"Исполнитель: @{query.from_user.username or query.from_user.full_name}\n\n"
                         f"Скоро с вами свяжутся для уточнения деталей."
                )
            except Exception as e:
                print(f"DEBUG: Не удалось уведомить создателя: {e}")
    else:
        await query.answer("⚠️ Не удалось принять заявку!", show_alert=True)


async def handle_cancel_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия кнопки "Отмена" в процессе создания заявки"""
    user_id = update.effective_user.id
    text = update.message.text
    
    print(f"DEBUG: Кнопка отмены нажата пользователем {user_id}")
    
    # Очищаем состояние пользователя
    if user_id in user_states:
        del user_states[user_id]
    
    await update.message.reply_text(
        "❌ Создание заявки отменено.",
        reply_markup=remove_keyboard()
    )
    
    # Создаем кнопку для новой заявки
    keyboard = [[InlineKeyboardButton("📝 Создать заявку", callback_data='create_application')]]
    
    await update.message.reply_text(
        "Можете создать новую заявку:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда помощи"""
    chat_type = update.message.chat.type
    
    if chat_type == 'private':
        from keyboards import get_private_chat_keyboard
        help_text = (
            "📋 *Меню бота:*\n\n"
            "• */start* - начать работу с ботом\n"
            "• */new* или кнопка 'Создать заявку' - создать новую заявку\n"
            "• */myapps* или кнопка 'Взятые заявки' - показать заявки, которые вы приняли\n"
            "• */myrequests* или кнопка 'Отправленные заявки' - показать ваши созданные заявки\n"
            "• */help* - помощь по использованию\n"
            "• */cancel* - отмена текущего действия\n\n"
            "📌 *Как работать с заявками:*\n"
            "1. Создайте заявку через кнопку 'Создать заявку'\n"
            "2. Ваша заявка появится в группе исполнителей\n"
            "3. Когда заявку примут, вы получите уведомление\n"
            "4. Исполнитель свяжется с вами по указанным контактам\n\n"
            "Для исполнителей:\n"
            "• Принимайте заявки в группе кнопкой 'Принять заявку'\n"
            "• Данные заявки придут вам в личные сообщения\n"
            "• Управляйте заявкой через кнопки в личных сообщениях"
        )
        
        await update.message.reply_text(
            help_text, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_private_chat_keyboard()
        )
    else:
        help_text = (
            "Помощь по использованию бота\n\n"
            "В этой группе:\n"
            "• Отображаются новые заявки\n"
            "• Нажмите 'Принять заявку' чтобы взять задание\n\n"
            "Для создания заявки:\n"
            "Напишите боту в личные сообщения и используйте команду `/new`"
        )
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}", exc_info=True)
    try:
        await update.effective_message.reply_text("⚠️ Произошла ошибка.")
    except:
        pass


async def save_contact_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик сохранения контакта"""
    query = update.callback_query
    await query.answer()
    
    try:
        app_id = int(query.data.split('_')[2])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ Ошибка: неверный ID заявки.")
        return
    
    # Проверяем, имеет ли пользователь доступ к этой заявке
    user_id = query.from_user.id
    is_accepted_by_user = db.check_application_owner(app_id, user_id)
    
    if not is_accepted_by_user:
        await query.answer("❌ У вас нет доступа к этой заявке", show_alert=True)
        return
    
    application = db.get_application(app_id)
    
    if not application:
        await query.edit_message_text("❌ Заявка не найдена.")
        return
    
    contact_info = (
        f"Контактные данные заявки #{app_id}:\n\n"
        f"Адрес: {application['address']}\n"
        f"Телефон: {application['phone']}\n"
        f"Задача: {application['task']}\n"
        f"Клиент: {application['username']}"
    )
    
    await query.message.edit_text(
        contact_info,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Добавляем кнопки для копирования данных
    keyboard = [
        [InlineKeyboardButton("📞 Скопировать номер", callback_data=f'copy_phone_{app_id}')],
        [InlineKeyboardButton("📍 Скопировать адрес", callback_data=f'copy_address_{app_id}')],
        [
            InlineKeyboardButton("🔄 Вернуть заявку", callback_data=f'return_app_{app_id}'),
            InlineKeyboardButton("🔒 Закрыть заявку", callback_data=f'close_app_{app_id}')
        ],
        [InlineKeyboardButton("📝 Создать свою заявку", callback_data='create_application')]
    ]
    
    await query.message.reply_text(
        "Вы можете скопировать данные:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def copy_data_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик копирования данных"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    if len(data) < 3:
        await query.answer("❌ Ошибка данных", show_alert=True)
        return
    
    action = data[1]  # phone или address
    app_id = int(data[2])
    
    # Проверяем, имеет ли пользователь доступ к этой заявке
    user_id = query.from_user.id
    is_accepted_by_user = db.check_application_owner(app_id, user_id)
    
    if not is_accepted_by_user:
        await query.answer("❌ У вас нет доступа к этой заявке", show_alert=True)
        return
    
    application = db.get_application(app_id)
    
    if not application:
        await query.answer("❌ Заявка не найдена", show_alert=True)
        return
    
    if action == 'phone':
        text_to_copy = application['phone']
        message = f"📞 Номер телефона скопирован: `{text_to_copy}`"
    elif action == 'address':
        text_to_copy = application['address']
        message = f"📍 Адрес скопирован: `{text_to_copy}`"
    else:
        await query.answer("❌ Неизвестное действие", show_alert=True)
        return
    
    await query.answer(f"✅ {text_to_copy}", show_alert=True)
    
    # Можно также отправить сообщение с подсветкой
    await query.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN
    )


# Глобальные переменные для состояний возврата заявки
return_states = {}

async def return_application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Вернуть заявку'"""
    query = update.callback_query
    await query.answer()
    
    try:
        app_id = int(query.data.split('_')[2])
    except (IndexError, ValueError):
        await query.answer("❌ Ошибка: неверный ID заявки", show_alert=True)
        return
    
    # Проверяем, принял ли этот пользователь заявку
    user_id = query.from_user.id
    is_accepted_by_user = db.check_application_owner(app_id, user_id)
    
    if not is_accepted_by_user:
        await query.answer("❌ Только исполнитель, принявший заявку, может вернуть ее", show_alert=True)
        return
    
    # Сохраняем состояние возврата
    return_states[user_id] = {
        'app_id': app_id,
        'message_id': query.message.message_id,
        'chat_id': query.message.chat.id
    }
    
    # Запрашиваем причину возврата
    keyboard = [[InlineKeyboardButton("❌ Отмена возврата", callback_data=f'cancel_return_{app_id}')]]
    
    # Отправляем запрос причины в ЛИЧНЫЕ сообщения
    try:
        msg = await context.bot.send_message(
            chat_id=user_id,
            text=f"📝 Возврат заявки #{app_id}\n\n"
                 f"Пожалуйста, укажите причину возврата заявки в общий чат:\n"
                 f"(или нажмите кнопку отмены в группе)",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # Сохраняем ID личного сообщения
        return_states[user_id]['private_message_id'] = msg.message_id
        await query.answer("💬 Проверьте личные сообщения для указания причины", show_alert=True)
    except Exception as e:
        print(f"DEBUG: Не удалось отправить запрос в личку: {e}")
        # Если не удалось в личку, просим в группе
        reply_msg = await query.message.reply_text(
            f"📝 Возврат заявки #{app_id}\n\n"
            f"Пожалуйста, укажите причину возврата заявки в общий чат:\n"
            f"(или нажмите '❌ Отмена возврата')",
            reply_markup=InlineKeyboardMarkup(keyboard),
            reply_to_message_id=query.message.message_id
        )
        return_states[user_id]['group_message_id'] = reply_msg.message_id

async def handle_return_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка причины возврата заявки"""
    user_id = update.effective_user.id
    
    # Дополнительная проверка, что это личный чат
    if update.effective_chat.type != 'private':
        return  # Просто игнорируем сообщения в группах
    
    if user_id not in return_states:
        # Не отправляем сообщение, если нет активного процесса
        return
    
    reason = update.message.text
    app_data = return_states[user_id]
    app_id = app_data['app_id']
    
    # Проверяем, имеет ли пользователь право вернуть заявку
    is_accepted_by_user = db.check_application_owner(app_id, user_id)
    if not is_accepted_by_user:
        await update.message.reply_text("❌ Вы не можете вернуть эту заявку.")
        # Очищаем состояние
        if user_id in return_states:
            del return_states[user_id]
        return ConversationHandler.END
    
    # Обновляем заявку в базе данных
    success = db.return_application(
        app_id, 
        user_id,
        update.effective_user.username or update.effective_user.full_name,
        reason
    )
    
    if success:
        # Удаляем старое сообщение в группе (если возможно)
        try:
            await context.bot.delete_message(
                chat_id=Config.ADMIN_GROUP_CHAT_ID,
                message_id=app_data['message_id']
            )
        except Exception as e:
            print(f"DEBUG: Не удалось удалить старое сообщение: {e}")
        
        # Получаем обновленные данные заявки
        application = db.get_application(app_id)
        
        # Отправляем новое сообщение в группу с причиной возврата
        # Отправляем новое сообщение в группу с причиной возврата
        keyboard = get_application_keyboard(app_id)
        message_text = (
            f"🔄 Заявка #{app_id} ВОЗВРАЩЕНА\n\n"
            f"Адрес: {application['address']}\n"
            f"Задача: {application['task']}\n"
        )
        
        # Добавляем комментарий, если он есть
        if application['comment'] and application['comment'].strip():
            message_text += f"Комментарий: {application['comment']}\n"
        
        # Добавляем информацию о возврате
        message_text += f"От: @{application['username']}\n"
        message_text += f"Причина возврата: {reason}\n"
        message_text += f"Вернул: @{update.effective_user.username or update.effective_user.full_name}"
        
        sent_message = await context.bot.send_message(
            chat_id=Config.ADMIN_GROUP_CHAT_ID,
            text=message_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Обновляем message_id в базе данных
        db.set_message_id(app_id, sent_message.message_id)
        
        # Уведомляем создателя заявки
        if user_id != application['user_id']:
            try:
                await context.bot.send_message(
                    chat_id=application['user_id'],
                    text=f"⚠️ Ваша заявка #{app_id} возвращена в общий чат.\n"
                         f"Причина: {reason}\n"
                         f"Заявка будет доступна другим исполнителям."
                )
            except Exception as e:
                print(f"DEBUG: Не удалось уведомить создателя: {e}")
        
        # Подтверждение пользователю
        await update.message.reply_text(
            f"✅ Заявка #{app_id} успешно возвращена в общий чат.\n"
            f"Причина: {reason}"
        )
        try:
            # Удаляем сообщение с кнопками возврата
            await context.bot.delete_message(
                chat_id=user_id,
                message_id=app_data.get('private_message_id', 0)
            )
        except Exception as e:
            print(f"DEBUG: Не удалось удалить сообщение с кнопками: {e}")

    else:
        await update.message.reply_text("❌ Ошибка при возврате заявки.")
    
    # Очищаем состояние
    if user_id in return_states:
        del return_states[user_id]
    
    return ConversationHandler.END


async def cancel_return_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик отмены возврата заявки"""
    query = update.callback_query
    await query.answer()
    
    try:
        app_id = int(query.data.split('_')[2])
    except (IndexError, ValueError):
        await query.answer("❌ Ошибка", show_alert=True)
        return
    
    user_id = query.from_user.id
    
    # Очищаем состояние возврата
    if user_id in return_states:
        del return_states[user_id]
    
    await query.edit_message_text("❌ Возврат заявки отменен.")

async def update_application_message_with_return_button(app_id, user_id, context):
    """Обновляет сообщение с заявкой, добавляя кнопку возврата"""
    application = db.get_application(app_id)
    
    if not application or application['status'] != 'accepted':
        return
    
    # Проверяем, является ли пользователь исполнителем
    is_accepted_by_user = db.check_application_owner(app_id, user_id)
    if not is_accepted_by_user:
        return
    
    # Обновляем сообщение с кнопкой возврата
    new_text = (
        f"Заявка #{app_id} ПРИНЯТА\n\n"
        f"Адрес: {application['address']}\n"
        f"Задача: {application['task']}\n"
        f"От: @{application['username']}\n"
        f"Принял: @{application['accepted_username']}"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Вернуть заявку", callback_data=f'return_app_{app_id}')],
#        [InlineKeyboardButton("📞 Сохранить контакт", callback_data=f'save_contact_{app_id}')]
    ]
    
    # Пытаемся найти и обновить сообщение
    if application.get('message_id'):
        try:
            await context.bot.edit_message_text(
                chat_id=Config.ADMIN_GROUP_CHAT_ID,
                message_id=application['message_id'],
                text=new_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print(f"DEBUG: Не удалось обновить сообщение: {e}")
    
    # Также обновляем сообщение в личке пользователя, если оно есть
    try:
        # Ищем последние сообщения бота пользователю
        async with context.bot:
            # Отправляем обновленное сообщение с кнопкой возврата
            return_keyboard = [[
                InlineKeyboardButton("🔄 Вернуть заявку", callback_data=f'return_app_{app_id}'),
 #               InlineKeyboardButton("📞 Сохранить контакт", callback_data=f'save_contact_{app_id}')
            ]]
            
            full_info = (
                f"Вы приняли заявку #{app_id}!\n\n"
                f"Данные заявки:\n"
                f"Адрес: {application['address']}\n"
                f"Телефон: {application['phone']}\n"
                f"Задача: {application['task']}\n"
                f"Комментарий: {application['comment'] or 'нет'}\n"
                f"Отправитель: @{application['username']}\n\n"
                f"Если по какой-то причине вы не можете выполнить заявку, "
                f"вы можете вернуть ее в общий чат."
            )
            
            # Пытаемся отправить сообщение с кнопкой возврата
            await context.bot.send_message(
                chat_id=user_id,
                text=full_info,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(return_keyboard)
            )
    except Exception as e:
        print(f"DEBUG: Не удалось отправить сообщение с кнопкой возврата: {e}")

# Глобальные переменные для состояний закрытия заявки
close_states = {}

async def close_application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Закрыть заявку'"""
    query = update.callback_query
    await query.answer()
    
    try:
        app_id = int(query.data.split('_')[2])
    except (IndexError, ValueError):
        await query.answer("❌ Ошибка: неверный ID заявки", show_alert=True)
        return
    
    # Проверяем, принял ли этот пользователь заявку
    user_id = query.from_user.id
    is_accepted_by_user = db.check_application_owner(app_id, user_id)
    
    if not is_accepted_by_user:
        await query.answer("❌ Только исполнитель, принявший заявку, может закрыть ее", show_alert=True)
        return
    
    # Сохраняем состояние закрытия
    close_states[user_id] = {
        'app_id': app_id,
        'message_id': query.message.message_id,
        'chat_id': query.message.chat.id
    }
    
    # Создаем клавиатуру с вариантами закрытия
    keyboard = [
        [InlineKeyboardButton("✅ Работа выполнена", callback_data=f'close_done_{app_id}')],
        [InlineKeyboardButton("❌ Клиент отказался", callback_data=f'close_refused_{app_id}')],
        [InlineKeyboardButton("❌ Отмена закрытия", callback_data=f'cancel_close_{app_id}')]
    ]
    
    # Отправляем запрос причины закрытия в личные сообщения
    try:
        msg = await context.bot.send_message(
            chat_id=user_id,
            text=f"🔒 Закрытие заявки #{app_id}\n\n"
                 f"Пожалуйста, выберите причину закрытия заявки:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # Сохраняем ID личного сообщения
        close_states[user_id]['private_message_id'] = msg.message_id
        await query.answer("💬 Проверьте личные сообщения", show_alert=True)
    except Exception as e:
        print(f"DEBUG: Не удалось отправить запрос в личку: {e}")
        # Если не удалось в личку, спрашиваем в текущем чате
        await query.message.edit_text(
            text=f"🔒 Закрытие заявки #{app_id}\n\n"
                 f"Пожалуйста, выберите причину закрытия заявки:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_close_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Работа выполнена'"""
    query = update.callback_query
    await query.answer()
    
    try:
        app_id = int(query.data.split('_')[2])
    except (IndexError, ValueError):
        await query.answer("❌ Ошибка", show_alert=True)
        return
    
    # Закрываем заявку с причиной "Работа выполнена"
    success = await close_application_with_reason(app_id, query.from_user, "Работа выполнена", context)
    
    if success:
        # Возвращаемся к списку заявок
        await show_my_accepted_applications(update, context)
    else:
        # Оставляем на текущем экране
        await query.answer("❌ Не удалось закрыть заявку", show_alert=True)

async def handle_close_refused_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Клиент отказался'"""
    query = update.callback_query
    await query.answer()
    
    try:
        app_id = int(query.data.split('_')[2])
    except (IndexError, ValueError):
        await query.answer("❌ Ошибка", show_alert=True)
        return
    
    # Закрываем заявку с причиной "Клиент отказался"
    success = await close_application_with_reason(app_id, query.from_user, "Клиент отказался", context)
    
    if success:
        # Возвращаемся к списку заявок
        await show_my_accepted_applications(update, context)
    else:
        # Оставляем на текущем экране
        await query.answer("❌ Не удалось закрыть заявку", show_alert=True)

async def close_application_with_reason(app_id, user, reason, context):
    """Закрытие заявки с указанной причиной, возвращает True при успехе"""
    user_id = user.id
    username = user.username or user.full_name
    
    # Проверяем, имеет ли пользователь право закрыть заявку
    is_accepted_by_user = db.check_application_owner(app_id, user_id)
    if not is_accepted_by_user:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Вы не можете закрыть эту заявку."
            )
        except:
            pass
        return False
    
    # Закрываем заявку в базе данных
    success = db.close_application(app_id, user_id, username, reason)
    
    if success:
        # Получаем обновленные данные заявки
        application = db.get_application(app_id)
        
        # УДАЛЯЕМ сообщение о заявке из группы
        try:
            if application.get('message_id'):
                await context.bot.delete_message(
                    chat_id=Config.ADMIN_GROUP_CHAT_ID,
                    message_id=application['message_id']
                )
        except Exception as e:
            print(f"DEBUG: Не удалось удалить сообщение из группы: {e}")
        
        # Уведомляем создателя заявки
        if user_id != application['user_id']:
            try:
                await context.bot.send_message(
                    chat_id=application['user_id'],
                    text=f"🔒 Ваша заявка #{app_id} закрыта!\n\n"
                         f"Исполнитель: @{application['accepted_username']}\n"
                         f"Причина: {reason}\n\n"
                         f"Спасибо за использование нашего сервиса!"
                )
            except Exception as e:
                print(f"DEBUG: Не удалось уведомить создателя: {e}")
        
        # Очищаем состояние
        if user_id in close_states:
            del close_states[user_id]
        
        return True
    else:
        return False

async def cancel_close_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик отмены закрытия заявки"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Пытаемся получить app_id из callback_data
        parts = query.data.split('_')
        if len(parts) >= 3:
            app_id = int(parts[2])
            
            user_id = query.from_user.id
            # Очищаем состояние закрытия
            if user_id in close_states:
                del close_states[user_id]
            
            # Возвращаемся к списку заявок
            await show_my_accepted_applications(update, context)
        else:
            # Если нет app_id, просто показываем меню
            from keyboards import get_private_chat_keyboard
            await query.edit_message_text(
                text="❌ Закрытие заявки отменено.",
                reply_markup=get_private_chat_keyboard()
            )
    except (IndexError, ValueError):
        # Если ошибка, просто показываем меню
        from keyboards import get_private_chat_keyboard
        await query.edit_message_text(
            text="❌ Закрытие заявки отменено.",
            reply_markup=get_private_chat_keyboard()
        )

async def show_my_accepted_applications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать заявки, принятые пользователем"""
    query = update.callback_query
    if query:
        await query.answer()
        user_id = query.from_user.id
        message = query.message
    else:
        user_id = update.effective_user.id
        message = update.message
    
    # Получаем принятые пользователем заявки
    applications = db.get_user_accepted_applications(user_id)
    
    if not applications:
        text = "📋 У вас нет принятых заявок."
        keyboard = get_private_chat_keyboard()
        
        if query:
            await query.edit_message_text(text=text, reply_markup=keyboard)
        else:
            await message.reply_text(text=text, reply_markup=keyboard)
        return
    
    text = f"📋 Ваши принятые заявки ({len(applications)}):\n\n"
    
    # Создаем клавиатуру с кнопками "Закрыть" для каждой заявки
    keyboard = []
    
    for i, app in enumerate(applications, 1):
        # Формируем текст для заявки
        text += f"{i}. Заявка #{app['id']}\n"
        text += f"   📍 Адрес: {app['address'][:50]}" + ("..." if len(app['address']) > 50 else "") + "\n"
        text += f"   📝 Задача: {app['task'][:50]}" + ("..." if len(app['task']) > 50 else "") + "\n"
        text += f"   🕐 Создана: {app['created_at'].strftime('%d.%m.%Y %H:%M')}\n"
        
        # Добавляем кнопку "Закрыть" рядом с номером заявки
        keyboard.append([
            InlineKeyboardButton(
                f"🔒 Закрыть #{app['id']}", 
                callback_data=f'close_from_list_{app["id"]}'
            )
        ])
        
        text += "\n"  # Отступ между заявками
    
    # Добавляем кнопку возврата в меню
    keyboard.append([
        InlineKeyboardButton("🔙 Назад в меню", callback_data='back_to_menu')
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(
            text=text, 
            reply_markup=reply_markup, 
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.reply_text(
            text=text, 
            reply_markup=reply_markup, 
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_close_from_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Закрыть' из списка заявок"""
    query = update.callback_query
    await query.answer()
    
    try:
        app_id = int(query.data.split('_')[3])
    except (IndexError, ValueError):
        await query.answer("❌ Ошибка: неверный ID заявки", show_alert=True)
        return
    
    # Проверяем, принял ли этот пользователь заявку
    user_id = query.from_user.id
    is_accepted_by_user = db.check_application_owner(app_id, user_id)
    
    if not is_accepted_by_user:
        await query.answer("❌ Только исполнитель, принявший заявку, может закрыть ее", show_alert=True)
        return
    
    # Сохраняем состояние закрытия
    close_states[user_id] = {
        'app_id': app_id,
        'message_id': query.message.message_id,
        'chat_id': query.message.chat.id
    }
    
    # Создаем клавиатуру с вариантами закрытия
    keyboard = [
        [InlineKeyboardButton("✅ Работа выполнена", callback_data=f'close_done_{app_id}')],
        [InlineKeyboardButton("❌ Клиент отказался", callback_data=f'close_refused_{app_id}')],
        [InlineKeyboardButton("🔙 Назад к списку", callback_data='my_accepted_apps')]
    ]
    
    # Получаем данные заявки для информации
    application = db.get_application(app_id)
    
    info_text = ""
    if application:
        info_text = (
            f"🔒 Закрытие заявки #{app_id}\n\n"
            f"📍 Адрес: {application['address']}\n"
            f"📝 Задача: {application['task']}\n\n"
        )
    
    await query.edit_message_text(
        text=info_text + "Пожалуйста, выберите причину закрытия заявки:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_my_created_applications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать заявки, созданные пользователем"""
    query = update.callback_query
    if query:
        await query.answer()
        user_id = query.from_user.id
        message = query.message
    else:
        user_id = update.effective_user.id
        message = update.message
    
    # Получаем созданные пользователем заявки
    applications = db.get_user_created_applications(user_id)
    
    if not applications:
        text = "📨 У вас нет активных отправленных заявок."
        keyboard = get_private_chat_keyboard()
        
        if query:
            await query.edit_message_text(text=text, reply_markup=keyboard)
        else:
            await message.reply_text(text=text, reply_markup=keyboard)
        return
    
    pending_count = len([a for a in applications if a['status'] == 'pending'])
    accepted_count = len([a for a in applications if a['status'] == 'accepted'])
    
    text = f"📨 Ваши отправленные заявки ({len(applications)}):\n"
    text += f"⏳ Ожидают: {pending_count}\n"
    text += f"✅ Приняты: {accepted_count}\n\n"
    
    for i, app in enumerate(applications, 1):
        status_emoji = '⏳' if app['status'] == 'pending' else '✅'
        accepted_by = f" (@{app['accepted_username']})" if app['accepted_username'] else ""
        
        text += f"{i}. {status_emoji} Заявка #{app['id']}\n"
        text += f"   Адрес: {app['address'][:50]}...\n"
        text += f"   Задача: {app['task'][:50]}...\n"
        text += f"   Статус: {Application.get_status_text(app['status'])}{accepted_by}\n"
        text += f"   Создана: {app['created_at'].strftime('%d.%m.%Y %H:%M')}\n\n"
    
    keyboard = get_private_chat_keyboard()
    
    if query:
        await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply_text(text=text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

async def show_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки помощи"""
    query = update.callback_query
    await query.answer()
    
    help_text = (
        "📋 *Меню бота:*\n\n"
        "• *Создать заявку* - подать новую заявку на выполнение работ\n"
        "• *Взятые заявки* - показать заявки, которые вы приняли\n"
        "• *Отправленные заявки* - показать заявки, которые вы создали\n\n"
        "📌 *Как работать с заявками:*\n"
        "1. Создайте заявку через кнопку 'Создать заявку'\n"
        "2. Ваша заявка появится в группе исполнителей\n"
        "3. Когда заявку примут, вы получите уведомление\n"
        "4. Исполнитель свяжется с вами по указанным контактам\n\n"
        "Для исполнителей:\n"
        "• Принимайте заявки в группе кнопкой 'Принять заявку'\n"
        "• Данные заявки придут вам в личные сообщения\n"
        "• Управляйте заявкой через кнопки в личных сообщениях"
    )
    
    keyboard = get_private_chat_keyboard()
    await query.edit_message_text(text=help_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки возврата в меню"""
    query = update.callback_query
    await query.answer()
    
    from keyboards import get_private_chat_keyboard
    
    menu_text = (
        "Привет! Я бот для управления заявками.\n\n"
        "В этом чате вы можете:\n"
        "• Создать новую заявку\n"
        "• Просмотреть взятые вами заявки\n"
        "• Просмотреть ваши отправленные заявки\n"
        "• Получить уведомления о статусе заявок\n\n"
        "Выберите действие:"
    )
    
    await query.edit_message_text(
        text=menu_text,
        reply_markup=get_private_chat_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )