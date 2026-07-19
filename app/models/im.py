"""IM 即时通讯数据模型 + 敏感词模型

包含:
- ImGroup:           群组表
- ImGroupMember:     群成员表
- ImMessage:         消息表
- ImContact:         联系人/好友表
- ImSensitiveWord:   敏感词库表
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    SmallInteger,
    String,
    Text,
    BigInteger,
    ForeignKey,
    Index,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ImGroup(Base):
    """群组表"""

    __tablename__ = "im_group"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    group_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="群名称")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, comment="群头像")
    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="群主ID")
    notice: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True, comment="群公告")
    member_count: Mapped[int] = mapped_column(Integer, default=0, comment="成员数")
    max_members: Mapped[int] = mapped_column(Integer, default=500, comment="成员上限")
    is_bot_enabled: Mapped[int] = mapped_column(SmallInteger, default=1, comment="是否允许数字员工应答")
    is_muted_all: Mapped[int] = mapped_column(SmallInteger, default=0, comment="全员禁言")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, comment="1=正常, 0=已解散")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    is_deleted: Mapped[int] = mapped_column(SmallInteger, default=0, comment="软删除标记")

    __table_args__ = (
        Index("idx_owner_id", "owner_id"),
        Index("idx_group_status", "status"),
    )


class ImGroupMember(Base):
    """群成员表"""

    __tablename__ = "im_group_member"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="群ID")
    user_type: Mapped[str] = mapped_column(String(16), nullable=False, comment="成员类型: user / bot")
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="用户ID或数字员工ID")
    role: Mapped[str] = mapped_column(String(16), default="member", comment="owner / admin / member")
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="加入时间")

    __table_args__ = (
        UniqueConstraint("group_id", "user_type", "user_id", name="uk_group_member"),
        Index("idx_group_member_group", "group_id"),
    )


class ImMessage(Base):
    """消息表"""

    __tablename__ = "im_message"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, comment="消息ID（雪花算法生成，非自增）")
    chat_type: Mapped[str] = mapped_column(String(16), nullable=False, comment="会话类型: private / group")
    sender_type: Mapped[str] = mapped_column(String(16), nullable=False, comment="发送者类型: user / bot")
    sender_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="发送者ID")
    receiver_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="接收者ID（私聊）")
    group_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True, comment="群组ID（群聊）")
    msg_type: Mapped[str] = mapped_column(String(16), nullable=False, comment="消息类型: text / image / file / voice / video / system")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    extra: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="扩展字段")
    is_recalled: Mapped[int] = mapped_column(SmallInteger, default=0, comment="是否撤回")
    recall_reason: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, comment="撤回原因")
    recalled_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="撤回操作人")
    is_read: Mapped[int] = mapped_column(SmallInteger, default=0, comment="(私聊)是否已读")
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="已读时间")
    need_audit: Mapped[int] = mapped_column(SmallInteger, default=0, comment="是否需要审计标记")
    is_deleted: Mapped[int] = mapped_column(SmallInteger, default=0, comment="软删除标记")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="发送时间")

    __table_args__ = (
        Index("idx_chat_type_sender", "chat_type", "sender_id"),
        Index("idx_group_id_created", "group_id", "created_at"),
        Index("idx_sender_receiver", "sender_id", "receiver_id"),
        Index("idx_created_at", "created_at"),
    )


class ImContact(Base):
    """联系人/好友表"""

    __tablename__ = "im_contact"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="用户ID")
    contact_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="联系人用户ID")
    alias: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, comment="备注名")
    is_deleted: Mapped[int] = mapped_column(SmallInteger, default=0, comment="软删除标记")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        UniqueConstraint("user_id", "contact_user_id", name="uk_contact"),
    )


class ImSensitiveWord(Base):
    """敏感词库表"""

    __tablename__ = "im_sensitive_word"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, comment="敏感词")
    level: Mapped[str] = mapped_column(String(16), nullable=False, comment="级别: block（阻断）/ audit（审计）")
    category: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, comment="分类")
    is_enabled: Mapped[int] = mapped_column(SmallInteger, default=1, comment="是否启用")
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True, comment="创建者")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")