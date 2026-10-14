"""مستودعات الوصول إلى بيانات التطبيق."""
from db.repositories.conversation_repository import ConversationRepository
from db.repositories.message_repository import MessageRepository

__all__ = ["ConversationRepository", "MessageRepository"]
