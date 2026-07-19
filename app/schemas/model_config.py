"""AI 模型配置 Pydantic Schema"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ModelConfigCreate(BaseModel):
    """创建模型配置请求"""
    display_name: str = Field(..., max_length=128, description="展示名称")
    category: str = Field(..., max_length=32, description="模型分类: text / image / video / embedding")
    base_url: str = Field(..., max_length=512, description="API Base URL")
    api_key: str = Field(..., description="API Key")
    model_id: str = Field(..., max_length=128, description="模型 ID")
    is_default: bool = Field(False, description="是否默认模型")
    is_enabled: bool = Field(True, description="是否启用")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="默认温度")
    max_tokens: int = Field(4096, ge=1, le=32768, description="默认最大Token")


class ModelConfigUpdate(BaseModel):
    """更新模型配置请求（全部可选）"""
    display_name: Optional[str] = Field(None, max_length=128)
    category: Optional[str] = Field(None, max_length=32)
    base_url: Optional[str] = Field(None, max_length=512)
    api_key: Optional[str] = Field(None)
    model_id: Optional[str] = Field(None, max_length=128)
    is_default: Optional[bool] = Field(None)
    is_enabled: Optional[bool] = Field(None)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=32768)


class ModelConfigResponse(BaseModel):
    """模型配置响应"""
    id: int
    display_name: str
    category: str
    base_url: str
    model_id: str
    is_default: int
    is_enabled: int
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModelConfigListResponse(BaseModel):
    """模型配置列表（不返回 api_key）"""
    id: int
    display_name: str
    category: str
    base_url: str
    model_id: str
    is_default: int
    is_enabled: int
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModelTestRequest(BaseModel):
    """模型连通性测试请求"""
    model_id: str = Field(..., description="模型 ID")
    api_key: str = Field(..., description="API Key")
    base_url: str = Field(..., description="Base URL")


class ModelTestResponse(BaseModel):
    """模型连通性测试响应"""
    success: bool
    message: str