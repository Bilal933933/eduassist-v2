"""اختبارات نماذج قاعدة البيانات."""
from db.models import Conversation, Message, User


def test_users_table_has_required_identity_fields() -> None:
    """يحتوي جدول المستخدمين على حقول الهوية والمصادقة المطلوبة."""
    assert set(User.__table__.columns.keys()) == {
        "id",
        "full_name",
        "email",
        "password_hash",
        "role",
        "is_active",
        "created_at",
        "updated_at",
    }
    assert User.email.nullable is False
    assert User.password_hash.nullable is False
    assert User.role.nullable is False


def test_users_email_is_unique() -> None:
    """يمنع تعريف الجدول تكرار البريد الإلكتروني."""
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in User.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("email",) in unique_columns


def test_conversation_belongs_to_user() -> None:
    """تفرض المحادثة وجود مستخدم مالك لها."""
    assert Conversation.user_id.nullable is False
    foreign_keys = {str(key.column) for key in Conversation.user_id.foreign_keys}
    assert foreign_keys == {"users.id"}


def test_conversation_has_minimal_fields() -> None:
    """يقتصر النموذج على حقول المحادثة اللازمة حاليًا."""
    assert set(Conversation.__table__.columns.keys()) == {
        "id",
        "user_id",
        "title",
        "status",
        "created_at",
        "updated_at",
    }


def test_message_has_required_fields() -> None:
    """يحتوي النموذج على الملكية والمحتوى والترتيب."""
    assert set(Message.__table__.columns.keys()) == {
        "id",
        "conversation_id",
        "user_id",
        "sender",
        "content",
        "metadata",
        "sequence_number",
        "created_at",
    }
    assert Message.conversation_id.nullable is False
    assert Message.user_id.nullable is False
    assert Message.content.nullable is False


def test_message_owner_is_bound_to_conversation_owner() -> None:
    """يربط القيد المركب الرسالة بالمحادثة ومالكها معًا."""
    constraints = {
        constraint.name: {
            str(element.target_fullname) for element in constraint.elements
        }
        for constraint in Message.__table__.foreign_key_constraints
    }
    assert constraints["fk_messages_conversation_owner"] == {
        "conversations.id",
        "conversations.user_id",
    }
