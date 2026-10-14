"""تهيئة بيئة ترحيلات قاعدة البيانات."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from config.settings import settings
from db.models import Base


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

LANGGRAPH_TABLES = {
    "checkpoint_blobs",
    "checkpoint_migrations",
    "checkpoint_writes",
    "checkpoints",
}


def include_object(object_, name: str | None, type_: str, reflected: bool, compare_to):
    """استبعاد جداول لانغ غراف المُدارة خارجيًا من مقارنة الترحيلات."""
    _ = object_, compare_to
    return not (reflected and name in LANGGRAPH_TABLES)


def sqlalchemy_url() -> str:
    """تحويل رابط PostgreSQL إلى مشغل psycopg المتزامن للترحيلات."""
    return settings.DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )


def run_migrations_offline() -> None:
    """إنشاء أوامر الترحيل دون فتح اتصال بقاعدة البيانات."""
    context.configure(
        url=sqlalchemy_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """تشغيل الترحيلات عبر اتصال مباشر بقاعدة البيانات."""
    engine = create_engine(sqlalchemy_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
