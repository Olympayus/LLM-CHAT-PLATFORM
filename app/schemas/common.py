"""通用 Pydantic Schema — 统一响应 / 分页"""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel):
    """统一响应格式 { code, message, data }"""
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None


class PageParams(BaseModel):
    """分页参数"""
    page: int = 1
    page_size: int = 20


class PageResult(BaseModel, Generic[T]):
    """分页结果"""
    items: list[T]
    total: int
    page: int
    page_size: int