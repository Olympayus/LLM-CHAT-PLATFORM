"""爬虫任务与数据清洗数据模型

对应表:
- crawler_task:          爬虫任务配置
- crawler_execution_log: 爬虫执行日志
- data_clean_rule:       数据清洗规则
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, JSON, SmallInteger, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CrawlerTask(Base):
    """爬虫任务配置表"""

    __tablename__ = "crawler_task"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="任务ID")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="任务名称")
    request_url: Mapped[str] = mapped_column(String(1024), nullable=False, comment="请求地址")
    request_method: Mapped[str] = mapped_column(
        String(8), nullable=False, default="GET", comment="请求方法: GET/POST"
    )
    request_headers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="请求头")
    request_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="POST 请求体")
    parse_rules: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="解析规则 (XPath/CSS 选择器)")
    output_table: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, comment="入库目标表名")
    schedule_cron: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="Cron 表达式，为空则仅手动触发"
    )
    is_enabled: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, comment="是否启用: 1=是 0=否")
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="创建者用户ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )
    is_deleted: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, comment="软删除: 0=正常 1=已删除")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "request_url": self.request_url,
            "request_method": self.request_method,
            "request_headers": self.request_headers,
            "request_body": self.request_body,
            "parse_rules": self.parse_rules,
            "output_table": self.output_table,
            "schedule_cron": self.schedule_cron,
            "is_enabled": self.is_enabled,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CrawlerExecutionLog(Base):
    """爬虫执行日志表"""

    __tablename__ = "crawler_execution_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="日志ID")
    task_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, comment="关联爬虫任务ID"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="执行状态: success / failed / running"
    )
    rows_collected: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="采集行数")
    rows_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="入库行数")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="开始时间")
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="结束时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")

    __table_args__ = (
        Index("idx_task_id_status", "task_id", "status"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "status": self.status,
            "rows_collected": self.rows_collected,
            "rows_inserted": self.rows_inserted,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DataCleanRule(Base):
    """数据清洗规则表"""

    __tablename__ = "data_clean_rule"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="规则ID")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="规则名称")
    rule_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="规则类型: dedup / normalize / mask / custom"
    )
    config: Mapped[dict] = mapped_column(JSON, nullable=False, comment="规则配置 (JSON)")
    target_field: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, comment="目标字段")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="执行顺序")
    task_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, comment="关联爬虫任务ID"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )
    is_deleted: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, comment="软删除: 0=正常 1=已删除")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "rule_type": self.rule_type,
            "config": self.config,
            "target_field": self.target_field,
            "sort_order": self.sort_order,
            "task_id": self.task_id,
        }
