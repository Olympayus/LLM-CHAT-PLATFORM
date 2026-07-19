"""技能管理 ORM 模型"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, JSON, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Skill(Base):
    """技能表"""

    __tablename__ = "skill"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="技能名称")
    type: Mapped[str] = mapped_column(String(32), nullable=False, comment="技能类型: function_call / skill_md")
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="技能描述（给 LLM 的 function description）")
    category: Mapped[str] = mapped_column(String(32), nullable=True, comment="分类标签")
    params_schema: Mapped[dict] = mapped_column(JSON, nullable=True, comment="参数定义 (JSON Schema)，Function Call 类型使用")
    python_code: Mapped[str] = mapped_column(Text, nullable=True, comment="Function Call 执行的 Python 代码")
    skill_md_content: Mapped[str] = mapped_column(Text, nullable=True, comment="SKILL.md 内容，Skill 类型使用")
    is_enabled: Mapped[int] = mapped_column(SmallInteger, default=1, comment="是否启用")
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=True, index=True, comment="创建者")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    is_deleted: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, comment="软删除")

    def __repr__(self) -> str:
        return f"<Skill(id={self.id}, name={self.name}, type={self.type})>"


class SkillParam(Base):
    """技能参数表"""

    __tablename__ = "skill_param"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    skill_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="技能ID")
    param_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="参数名")
    param_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="参数类型: string / number / boolean / object / array")
    is_required: Mapped[int] = mapped_column(SmallInteger, default=1, comment="是否必填")
    description: Mapped[str] = mapped_column(String(256), nullable=True, comment="参数说明")
    default_value: Mapped[str] = mapped_column(String(256), nullable=True, comment="默认值")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")

    def __repr__(self) -> str:
        return f"<SkillParam(id={self.id}, skill_id={self.skill_id}, name={self.param_name})>"