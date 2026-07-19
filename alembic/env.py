"""Alembic 数据库迁移环境配置"""

import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# Alembic Config 对象
config = context.config

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 添加项目根目录到 Python 路径
sys.path.insert(0, ".")

# 导入 Base 元数据（后续模型创建后取消注释）
# from app.core.database import Base
# target_metadata = Base.metadata

target_metadata = None


def run_migrations_offline() -> None:
    """离线模式迁移"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式迁移"""
    url = config.get_main_option("sqlalchemy.url")
    from app.config import settings
    connectable = create_engine(
        url,
        connect_args=settings.pymysql_connect_args,
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
