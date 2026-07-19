"""AI 模型配置 ORM 模型"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, DECIMAL, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ModelConfig(Base):
    """AI 模型配置表"""

    __tablename__ = "model_config"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="展示名称（如阿里百炼-Qwen-Max）")
    category: Mapped[str] = mapped_column(String(32), nullable=False, comment="模型分类: text / image / video / embedding")
    base_url: Mapped[str] = mapped_column(String(512), nullable=False, comment="API Base URL")
    api_key: Mapped[str] = mapped_column(Text, nullable=False, comment="API Key (加密存储)")
    model_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="模型 ID（如 qwen-max）")
    is_default: Mapped[int] = mapped_column(SmallInteger, default=0, comment="是否默认模型")
    is_enabled: Mapped[int] = mapped_column(SmallInteger, default=1, comment="是否启用")
    temperature: Mapped[float] = mapped_column(DECIMAL(3, 2), default=0.70, comment="默认温度")
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096, comment="默认最大Token")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    is_deleted: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, comment="软删除")

    def __repr__(self) -> str:
        return f"<ModelConfig(id={self.id}, display_name={self.display_name}, model_id={self.model_id})>"