"""NL2SQL 智能问数数据模型

包含:
- Nl2sqlQueryHistory: 查询历史记录
- Nl2sqlFavorite:     查询收藏
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    BigInteger,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Nl2sqlQueryHistory(Base):
    """NL2SQL 查询历史"""

    __tablename__ = "nl2sql_query_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="查询用户ID")
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="自然语言问题")
    generated_sql: Mapped[str] = mapped_column(Text, nullable=False, comment="生成的SQL")
    is_valid: Mapped[int] = mapped_column(
        Integer, default=0, comment="安全校验是否通过: 0=未校验 1=通过 -1=失败"
    )
    execution_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="执行耗时(ms)"
    )
    result_rows: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="返回行数"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="错误信息"
    )
    chart_type: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, comment="推荐的图表类型: bar/line/pie/table"
    )
    interpretation: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="AI 数据解读文本"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="创建时间"
    )

    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_created_at", "created_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "question": self.question,
            "generated_sql": self.generated_sql,
            "is_valid": self.is_valid,
            "execution_time_ms": self.execution_time_ms,
            "result_rows": self.result_rows,
            "error_message": self.error_message,
            "chart_type": self.chart_type,
            "interpretation": self.interpretation,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Nl2sqlFavorite(Base):
    """NL2SQL 收藏的查询"""

    __tablename__ = "nl2sql_favorite"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="用户ID")
    query_history_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("nl2sql_query_history.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联的查询历史ID",
    )
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="收藏的问题")
    sql: Mapped[str] = mapped_column(Text, nullable=False, comment="收藏的SQL")
    chart_type: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, comment="图表类型"
    )
    note: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True, comment="收藏备注"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="创建时间"
    )

    __table_args__ = (
        Index("idx_fav_user_id", "user_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "query_history_id": self.query_history_id,
            "question": self.question,
            "sql": self.sql,
            "chart_type": self.chart_type,
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }