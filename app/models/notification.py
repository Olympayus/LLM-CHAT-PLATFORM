"""通知中心数据模型（成员C）

包含:
- Notification:      通知表
- NotificationRead:  通知已读记录表
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Notification(Base):
    """通知表"""

    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False, comment="通知类型: system/announcement/task/approval")
    title: Mapped[str] = mapped_column(String(256), nullable=False, comment="通知标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="通知内容")
    link: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, comment="跳转链接")
    sender_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True, comment="发送者ID（系统通知可为空）")
    is_global: Mapped[int] = mapped_column(SmallInteger, default=0, comment="是否全平台发送")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_notification_type", "type"),
        Index("idx_notification_created", "created_at"),
    )


class NotificationRead(Base):
    """通知已读记录表"""

    __tablename__ = "notification_read"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    notification_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="通知ID")
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="用户ID")
    read_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="已读时间")

    __table_args__ = (
        UniqueConstraint("notification_id", "user_id", name="uk_notification_user"),
        Index("idx_notification_read_user", "user_id"),
    )