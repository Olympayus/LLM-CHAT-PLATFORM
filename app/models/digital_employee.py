"""数字员工管理 ORM 模型"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, DECIMAL, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DigitalEmployee(Base):
    """数字员工表"""

    __tablename__ = "digital_employee"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="员工名称")
    avatar_url: Mapped[str] = mapped_column(String(512), nullable=True, comment="头像 URL")
    role_description: Mapped[str] = mapped_column(String(256), nullable=True, comment="角色描述（如数据分析师）")
    model_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="绑定的基础模型 (FK → model_config)")
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, comment="系统提示词")
    temperature: Mapped[float] = mapped_column(DECIMAL(3, 2), default=0.70, comment="模型温度参数")
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096, comment="最大输出 Token")
    is_enabled: Mapped[int] = mapped_column(SmallInteger, default=1, comment="是否启用")
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=True, index=True, comment="创建者")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    is_deleted: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, comment="软删除")

    def __repr__(self) -> str:
        return f"<DigitalEmployee(id={self.id}, name={self.name})>"


class EmployeeSkillRel(Base):
    """数字员工-技能关联表"""

    __tablename__ = "employee_skill_rel"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="数字员工ID")
    skill_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="技能ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")

    def __repr__(self) -> str:
        return f"<EmployeeSkillRel(employee_id={self.employee_id}, skill_id={self.skill_id})>"


class DigitalEmployeeConversation(Base):
    """数字员工对话记录表"""

    __tablename__ = "digital_employee_conversation"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="数字员工ID")
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="对话用户ID")
    user_message: Mapped[str] = mapped_column(Text, nullable=False, comment="用户消息")
    bot_response: Mapped[str] = mapped_column(Text, nullable=False, comment="AI回复")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")

    def __repr__(self) -> str:
        return f"<DigitalEmployeeConversation(id={self.id}, employee_id={self.employee_id})>"
