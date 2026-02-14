from enum import Enum

class ApplicationStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    CLOSED = "closed"

class Application:
    def __init__(self, user_id, username, address, phone, task, comment, status=ApplicationStatus.PENDING.value):
        self.user_id = user_id
        self.username = username
        self.address = address
        self.phone = phone
        self.task = task
        self.comment = comment
        self.status = status
        self.accepted_by = None
    
    @staticmethod
    def get_status_text(status):
        """Получить читаемый текст статуса"""
        status_texts = {
            'pending': '⏳ Ожидает',
            'accepted': '✅ Принята',
            'closed': '🔒 Закрыта'
        }
        return status_texts.get(status, status)