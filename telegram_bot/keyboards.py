from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

def get_main_keyboard():
    """Клавиатура для группового чата"""
    keyboard = [[InlineKeyboardButton("📝 Подать заявку", callback_data='create_application')]]
    return InlineKeyboardMarkup(keyboard)

def get_cancel_keyboard():
    """Клавиатура для отмены заполнения заявки"""
    keyboard = [['❌ Отмена']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_application_keyboard(application_id):
    """Клавиатура для принятия заявки"""
    keyboard = [[
        InlineKeyboardButton("✅ Принять заявку", 
                           callback_data=f'accept_{application_id}')
    ]]
    return InlineKeyboardMarkup(keyboard)

def remove_keyboard():
    """Удаление клавиатуры"""
    from telegram import ReplyKeyboardRemove
    return ReplyKeyboardRemove()