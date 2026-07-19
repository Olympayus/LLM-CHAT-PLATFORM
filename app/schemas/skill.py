"""技能管理 Pydantic Schema"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SkillParamSchema(BaseModel):
    """技能参数 Schema"""
    param_name: str = Field(..., max_length=64, description="参数名")
    param_type: str = Field(..., max_length=32, description="参数类型: string / number / boolean / object / array")
    is_required: bool = Field(True, description="是否必填")
    description: Optional[str] = Field(None, max_length=256, description="参数说明")
    default_value: Optional[str] = Field(None, max_length=256, description="默认值")


class SkillCreate(BaseModel):
    """创建技能请求"""
    name: str = Field(..., max_length=128, description="技能名称")
    type: str = Field(..., max_length=32, description="技能类型: function_call / skill_md")
    description: str = Field(..., description="技能描述")
    category: Optional[str] = Field(None, max_length=32, description="分类标签")
    params_schema: Optional[dict] = Field(None, description="参数定义 (JSON Schema)")
    python_code: Optional[str] = Field(None, description="Function Call 执行的 Python 代码")
    skill_md_content: Optional[str] = Field(None, description="SKILL.md 内容")
    is_enabled: bool = Field(True, description="是否启用")
    params: Optional[list[SkillParamSchema]] = Field(None, description="技能参数列表（可选）")


class SkillUpdate(BaseModel):
    """更新技能请求"""
    name: Optional[str] = Field(None, max_length=128)
    type: Optional[str] = Field(None, max_length=32)
    description: Optional[str] = Field(None)
    category: Optional[str] = Field(None, max_length=32)
    params_schema: Optional[dict] = Field(None)
    python_code: Optional[str] = Field(None)
    skill_md_content: Optional[str] = Field(None)
    is_enabled: Optional[bool] = Field(None)


class SkillResponse(BaseModel):
    """技能详情响应"""
    id: int
    name: str
    type: str
    description: str
    category: Optional[str] = None
    params_schema: Optional[dict] = None
    python_code: Optional[str] = None
    skill_md_content: Optional[str] = None
    is_enabled: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SkillListItem(BaseModel):
    """技能列表项（不含代码内容）"""
    id: int
    name: str
    type: str
    description: str
    category: Optional[str] = None
    is_enabled: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SkillAiGenerateRequest(BaseModel):
    """AI 辅助生成技能请求"""
    requirement: str = Field(..., description="自然语言需求描述")
    model_id: int = Field(..., description="使用的模型配置 ID")
    skill_type: str = Field("function_call", max_length=32, description="技能类型: function_call / skill_md")


class SkillTestResponse(BaseModel):
    """技能测试响应"""
    success: bool = Field(..., description="是否执行成功")
    result: Optional[str] = Field(None, description="执行结果")


class SkillAiGenerateResponse(BaseModel):
    """AI 辅助生成技能响应 — 流式生成的内容片段"""
    name: str = Field("", description="预生成的技能名称")
    description: str = Field("", description="预生成的技能描述")
    params_schema: Optional[dict] = Field(None, description="预生成的参数 Schema")
    python_code: Optional[str] = Field(None, description="预生成的 Python 代码")
    is_complete: bool = Field(False, description="是否生成完成")
    full_content: Optional[str] = Field(None, description="完整生成内容（skill_md 类型时使用）")