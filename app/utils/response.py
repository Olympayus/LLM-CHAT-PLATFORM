"""统一响应格式工具

所有 API 响应统一使用此格式返回:
    {
        "code": 0,          # 0=成功, 非0=错误码
        "message": "ok",    # 提示信息
        "data": {}          # 响应数据
    }
"""

from typing import Any, Optional, TypeVar

from fastapi import status
from fastapi.responses import JSONResponse

T = TypeVar("T")


def success(data: Optional[Any] = None, message: str = "ok") -> dict:
    """成功响应"""
    return {
        "code": 0,
        "message": message,
        "data": data,
    }


def error(code: int = -1, message: str = "error", data: Optional[Any] = None) -> dict:
    """错误响应"""
    return {
        "code": code,
        "message": message,
        "data": data,
    }


def paginate(items: list, total: int, page: int, page_size: int) -> dict:
    """分页响应"""
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        },
    }


def json_response(data: Any = None, message: str = "ok", status_code: int = status.HTTP_200_OK):
    """快速返回 JSONResponse"""
    return JSONResponse(
        content={"code": 0, "message": message, "data": data},
        status_code=status_code,
    )