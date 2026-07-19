"""System config model (F-SC) — Member F"""

from datetime import datetime
from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class SysConfig(Base):
    __tablename__ = "sys_config"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, comment="配置键")
    config_value: Mapped[str] = mapped_column(Text, nullable=False, comment="配置值(JSON)")
    description: Mapped[str] = mapped_column(String(256), nullable=True, comment="配置说明")
    category: Mapped[str] = mapped_column(String(64), nullable=False, comment="site/storage/login/log/notification")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")
