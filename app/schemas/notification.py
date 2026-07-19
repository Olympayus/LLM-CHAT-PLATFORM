"""通知中心 Pydantic Schema（成员C）

包含通知列表、已读管理等请求/响应模型。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    """通知响应模型"""
    id: int
    type: str
    title: str
    content: str
    link: Optional[str] = None
    is_read: int = 0
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class NotificationDetailResponse(BaseModel):
    """通知详情响应模型"""
    id: int
    type: str
    title: str
    content: str
    link: Optional[str] = None
    sender_id: Optional[int] = None
    is_global: int = 0
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class UnreadCountResponse(BaseModel):
    """未读通知数响应"""
    count: int