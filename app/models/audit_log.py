"""审计日志数据模型

包含:
- SysAuditLog: 审计日志表
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    String,
    Text,
    BigInteger,
    JSON,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SysAuditLog(Base):
    """审计日志表"""

    __tablename__ = "sys_audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True, comment="操作人ID")
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, comment="操作人用户名（冗余，防用户删除）")
    action: Mapped[str] = mapped_column(String(64), nullable=False, comment="操作类型: login / logout / query / delete / ...")
    resource: Mapped[str] = mapped_column(String(64), nullable=False, comment="资源类型: user / group / message / model / ...")
    resource_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="资源ID")
    detail: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="操作详情")
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, comment="操作IP")
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, comment="User Agent")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_audit_user_created", "user_id", "created_at"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_resource", "resource"),
    )