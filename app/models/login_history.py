"""登录历史模型 - F-PF 个人中心"""

from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class LoginHistory(Base):
    """登录历史记录"""
    __tablename__ = "login_history"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="记录ID"
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="用户ID"
    )
    login_ip: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", comment="登录IP"
    )
    user_agent: Mapped[str] = mapped_column(
        String(512), nullable=False, default="", comment="浏览器UA"
    )
    login_status: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="登录状态 1=成功 0=失败"
    )
    fail_reason: Mapped[str] = mapped_column(
        String(256), nullable=False, default="", comment="失败原因"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="登录时间"
    )