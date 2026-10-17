"""تجميع نماذج جداول بيانات التطبيق."""
from db.models.auth_session import AuthSession
from db.models.base import Base
from db.models.conversation import Conversation
from db.models.message import Message
from db.models.teacher_profile import TeacherProfile
from db.models.user import User

__all__ = [
    "AuthSession",
    "Base",
    "Conversation",
    "Message",
    "TeacherProfile",
    "User",
]
