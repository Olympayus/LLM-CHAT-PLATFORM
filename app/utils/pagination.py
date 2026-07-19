"""分页工具函数"""
from typing import Any


def paginate_response(items: list[Any], total: int, page: int, page_size: int) -> dict:
    """构建分页响应"""
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }
