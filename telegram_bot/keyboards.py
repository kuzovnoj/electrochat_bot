from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

def get_main_keyboard():
    """Клавиатура для группового чата"""
    keyboard = [
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='show_help')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_private_chat_keyboard():
    """Основная клавиатура для личного чата"""
    keyboard = [
        [InlineKeyboardButton("📝 Создать заявку", callback_data='create_application')],
        [InlineKeyboardButton("📋 Взятые заявки", callback_data='my_accepted_apps')],
        [InlineKeyboardButton("📨 Отправленные заявки", callback_data='my_created_apps')],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='show_help')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_cancel_keyboard():
    """Клавиатура для отмены заполнения заявки"""
    keyboard = [['❌ Отмена']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_application_keyboard(application_id):
    """Клавиатура для принятия заявки"""
    keyboard = [[
        InlineKeyboardButton("✅ Принять заявку", callback_data=f'accept_{application_id}')
    ]]
    return InlineKeyboardMarkup(keyboard)

def get_application_management_keyboard(app_id):
    """Клавиатура для управления принятой заявкой"""
    keyboard = [
        [
            InlineKeyboardButton("🔄 Вернуть заявку", callback_data=f'return_app_{app_id}'),
            InlineKeyboardButton("🔒 Закрыть заявку", callback_data=f'close_app_{app_id}')
        ],
#        [InlineKeyboardButton("📞 Сохранить контакт", callback_data=f'save_contact_{app_id}')]
    ]
    return InlineKeyboardMarkup(keyboard)

def remove_keyboard():
    """Удаление клавиатуры"""
    from telegram import ReplyKeyboardRemove
    return ReplyKeyboardRemove()