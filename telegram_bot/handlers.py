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
                    
                    # Удаляем использованный токен
                    del context.bot_data['app_tokens'][token_data]
                
                    # Добавляем кнопку для сохранения контакта
                    contact_keyboard = [
                        [InlineKeyboardButton("📝 Создать свою заявку", callback_data='create_application')],
                        [InlineKeyboardButton("📞 Сохранить контакт", callback_data=f'save_contact_{app_data}')]
                    ]
                    '''
                    await update.message.reply_text(
                        "Что вы хотите сделать дальше?",
                        reply_markup=InlineKeyboardMarkup(contact_keyboard)
                    )
                    '''
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
                
                # Добавляем кнопку для сохранения контакта
                contact_keyboard = [
                    [InlineKeyboardButton("📝 Создать свою заявку", callback_data='create_application')],
                    [InlineKeyboardButton("📞 Сохранить контакт", callback_data=f'save_contact_{app_data}')]
                ]
                '''
                await update.message.reply_text(
                    "Что вы хотите сделать дальше?",
                    reply_markup=InlineKeyboardMarkup(contact_keyboard)
                )
                '''
                return ConversationHandler.END
        
        # Стандартное приветствие
        await update.message.reply_text(
            welcome_text + "Чтобы создать заявку, нажмите кнопку ниже:",
            reply_markup=InlineKeyboardMarkup(keyboard),
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
        "Шаг 1 из 4: Введите адрес:\n"
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
        "Шаг 1 из 4: Введите адрес:\n"
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

# Удаляем старую функцию handle_private_message и заменяем ее на ConversationHandler
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
        "Шаг 2 из 4: Введите номер телефона:\n"
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
        "Шаг 3 из 4: Опишите задачу:\n"
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
        "Шаг 4 из 4: Введите комментарий:\n"
        "(дополнительная информация, особенности и т.д.)\n"
        "(отправьте '-' если комментария нет)\n"
        "(или отправьте '❌ Отмена' для отмены)",
        reply_markup=get_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    print(f"DEBUG: Перешли к шагу 'comment'")
    return Config.COMMENT

async def handle_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка комментария и сохранение заявки"""
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
    
    # Проверяем, что все данные собраны
    required_fields = ['address', 'phone', 'task', 'username']
    if not all(field in user_states[user_id] for field in required_fields):
        print(f"DEBUG: Не все данные собраны: {user_states[user_id]}")
        await update.message.reply_text(
            "❌ Ошибка: не все данные собраны. Начните заново.",
            reply_markup=remove_keyboard()
        )
        # Очищаем состояние
        if user_id in user_states:
            del user_states[user_id]
        return ConversationHandler.END
    
    try:
        user_data = user_states[user_id]
        
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
            f"Детали заявки:\n"
            f"Адрес: {application.address}\n"
            f"Телефон: {application.phone}\n"
            f"Задача: {application.task}\n"
            f"Комментарий: {application.comment or 'нет'}\n\n"
            f"Заявка отправлена в группу исполнителей.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=remove_keyboard()
        )
        
        # Создаем кнопку для новой заявки
        keyboard = [[InlineKeyboardButton("📝 Создать еще одну заявку", callback_data='create_application')]]
        '''
        await update.message.reply_text(
            "Что вы хотите сделать дальше?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        '''
        # Отправляем заявку в группу
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
    
    if not application:
        await query.edit_message_text("❌ Заявка не найдена.")
        return
    
    success = db.accept_application(
        app_id, 
        user_id,
        query.from_user.username or query.from_user.full_name
    )
    
    if success:
        # Обновляем сообщение в группе БЕЗ кнопок
        new_text = (
            f"Заявка #{app_id} ПРИНЯТА\n\n"
            f"Адрес: {application['address']}\n"
            f"Задача: {application['task']}\n"
            f"От: @{application['username']}\n"
            f"Принял: @{query.from_user.username or query.from_user.full_name}"
        )
        
        # В ГРУППЕ убираем все кнопки после принятия
        await query.edit_message_text(
            text=new_text, 
            reply_markup=None,  # Убираем клавиатуру в группе
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Пытаемся отправить данные в личку с кнопками
        try:
            # Создаем кнопки ТОЛЬКО для личных сообщений
            return_keyboard = [
                [InlineKeyboardButton("🔄 Вернуть заявку", callback_data=f'return_app_{app_id}')],
#                [InlineKeyboardButton("📞 Сохранить контакт", callback_data=f'save_contact_{app_id}')]
            ]
            
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
            
            # Отправляем сообщение в личку с кнопками
            await context.bot.send_message(
                chat_id=user_id,
                text=full_info,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(return_keyboard)
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
            
            # Создаем ссылку с временным токеном или параметром пользователя
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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда помощи"""
    chat_type = update.message.chat.type
    
    if chat_type == 'private':
        help_text = (
            "Помощь по использованию бота\n\n"
            "В личном чате:\n"
            "• Используйте команду `/new` или кнопку 'Создать заявку' для создания новой заявки\n"
            "• Вы получите уведомления о статусе ваших заявок\n\n"
            "В группе:\n"
            "• Отображаются новые заявки\n"
            "• Нажмите 'Принять заявку' чтобы взять задание\n\n"
            "Команды:\n"
            "`/start` - начать работу\n"
            "`/new` - создать новую заявку\n"
            "`/help` - помощь\n"
            "`/cancel` - отмена текущего действия"
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
    
    if user_id not in return_states:
        await update.message.reply_text("❌ Нет активного процесса возврата заявки.")
        return ConversationHandler.END
    
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
        keyboard = get_application_keyboard(app_id)
        message_text = (
            f"🔄 Заявка #{app_id} ВОЗВРАЩЕНА\n\n"
            f"Адрес: {application['address']}\n"
            f"Задача: {application['task']}\n"
            f"От: @{application['username']}\n"
            f"Причина возврата: {reason}\n"
            f"Вернул: @{update.effective_user.username or update.effective_user.full_name}"
        )
        
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
        [InlineKeyboardButton("📞 Сохранить контакт", callback_data=f'save_contact_{app_id}')]
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
                InlineKeyboardButton("📞 Сохранить контакт", callback_data=f'save_contact_{app_id}')
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