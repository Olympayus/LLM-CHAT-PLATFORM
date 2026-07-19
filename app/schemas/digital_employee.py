"""数字员工管理 Pydantic Schema"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class DigitalEmployeeCreate(BaseModel):
    """创建数字员工请求"""
    name: str = Field(..., max_length=64, description="员工名称")
    avatar_url: Optional[str] = Field(None, max_length=512, description="头像 URL")
    role_description: Optional[str] = Field(None, max_length=256, description="角色描述")
    model_id: int = Field(..., description="绑定的基础模型 ID")
    system_prompt: str = Field(..., description="系统提示词")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="模型温度参数")
    max_tokens: int = Field(4096, ge=1, le=32768, description="最大输出 Token")
    is_enabled: bool = Field(True, description="是否启用")
    skill_ids: Optional[list[int]] = Field(None, description="绑定的技能 ID 列表")


class DigitalEmployeeUpdate(BaseModel):
    """更新数字员工请求"""
    name: Optional[str] = Field(None, max_length=64)
    avatar_url: Optional[str] = Field(None, max_length=512)
    role_description: Optional[str] = Field(None, max_length=256)
    model_id: Optional[int] = Field(None)
    system_prompt: Optional[str] = Field(None)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=32768)
    is_enabled: Optional[bool] = Field(None)


class DigitalEmployeeResponse(BaseModel):
    """数字员工详情响应"""
    id: int
    name: str
    avatar_url: Optional[str] = None
    role_description: Optional[str] = None
    model_id: int
    system_prompt: str
    temperature: Decimal
    max_tokens: int
    is_enabled: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DigitalEmployeeListItem(BaseModel):
    """数字员工列表项"""
    id: int
    name: str
    avatar_url: Optional[str] = None
    role_description: Optional[str] = None
    model_id: int
    is_enabled: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmployeeSkillBindRequest(BaseModel):
    """绑定/解绑技能请求"""
    skill_ids: list[int] = Field(..., description="技能 ID 列表")


class TestChatRequest(BaseModel):
    """测试对话请求"""
    message: str = Field(..., description="测试消息内容")


class TestChatResponse(BaseModel):
    """测试对话响应"""
    reply: str = Field(..., description="AI 回复内容")
    model_id: int = Field(..., description="使用的模型 ID")
    tokens_used: Optional[int] = Field(None, description="消耗的 Token 数")


class ConversationItemResponse(BaseModel):
    """对话记录项"""
    id: int
    user_message: str
    bot_response: str
    created_at: datetime

    model_config = {"from_attributes": True}
