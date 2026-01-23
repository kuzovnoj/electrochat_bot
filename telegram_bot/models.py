from enum import Enum

class ApplicationStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    COMPLETED = "completed"

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