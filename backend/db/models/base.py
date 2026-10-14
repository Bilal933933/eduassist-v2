"""الفئة الأساسية لنماذج قاعدة البيانات."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """أساس جميع نماذج مخطط الكائنات العلائقية."""

