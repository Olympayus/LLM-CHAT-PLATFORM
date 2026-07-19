"""IM 即时通讯 + 合规审计 Pydantic Schema

包含:
- 敏感词相关: SensitiveWordCreate, SensitiveWordUpdate, SensitiveWordResponse
- 审计日志相关: AuditLogResponse, AuditLogSearchRequest
- 消息管理相关: MessageSearchRequest, MessageRecallRequest, GroupSystemMessageRequest
- 群组管理相关: GroupListResponse, GroupDetailResponse, GroupMemberResponse
"""

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


# ==================== 敏感词相关 ====================

class SensitiveWordCreate(BaseModel):
    """创建敏感词"""
    word: str = Field(..., min_length=1, max_length=128, description="敏感词")
    level: str = Field(..., pattern="^(block|audit)$", description="级别: block（阻断）/ audit（审计）")
    category: Optional[str] = Field(None, max_length=32, description="分类")


class SensitiveWordUpdate(BaseModel):
    """更新敏感词"""
    word: Optional[str] = Field(None, min_length=1, max_length=128, description="敏感词")
    level: Optional[str] = Field(None, pattern="^(block|audit)$", description="级别")
    category: Optional[str] = Field(None, max_length=32, description="分类")
    is_enabled: Optional[bool] = Field(None, description="是否启用")


class SensitiveWordResponse(BaseModel):
    """敏感词响应"""
    id: int
    word: str
    level: str
    category: Optional[str] = None
    is_enabled: bool
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ==================== 审计日志相关 ====================

class AuditLogResponse(BaseModel):
    """审计日志响应"""
    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    action: str
    resource: str
    resource_id: Optional[int] = None
    detail: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogSearchRequest(BaseModel):
    """审计日志搜索请求"""
    action: Optional[str] = Field(None, description="操作类型筛选")
    resource: Optional[str] = Field(None, description="资源类型筛选")
    user_id: Optional[int] = Field(None, description="操作人ID")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数")


# ==================== 消息管理相关 ====================

class MessageSearchRequest(BaseModel):
    """消息搜索请求"""
    keyword: Optional[str] = Field(None, description="关键词搜索")
    sender_id: Optional[int] = Field(None, description="发送者ID")
    group_id: Optional[int] = Field(None, description="群组ID")
    chat_type: Optional[str] = Field(None, pattern="^(private|group)$", description="会话类型")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数")


class MessageSearchResponse(BaseModel):
    """消息搜索结果"""
    id: int
    chat_type: str
    sender_type: str
    sender_id: int
    receiver_id: Optional[int] = None
    group_id: Optional[int] = None
    msg_type: str
    content: str
    is_recalled: bool
    recall_reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageRecallRequest(BaseModel):
    """消息撤回请求"""
    reason: str = Field(default="违规内容", max_length=256, description="撤回原因")


# ==================== 群组管控相关 ====================

class GroupSystemMessageRequest(BaseModel):
    """群系统消息请求"""
    content: str = Field(..., min_length=1, max_length=1024, description="系统消息内容")


class GroupMemberResponse(BaseModel):
    """群成员响应"""
    id: int
    user_type: str
    user_id: int
    role: str
    joined_at: datetime

    model_config = {"from_attributes": True}


class GroupDetailResponse(BaseModel):
    """群组详情响应"""
    id: int
    group_name: str
    avatar_url: Optional[str] = None
    owner_id: int
    notice: Optional[str] = None
    member_count: int
    max_members: int
    is_bot_enabled: bool
    is_muted_all: bool
    status: int
    created_at: datetime
    members: list[GroupMemberResponse] = []

    model_config = {"from_attributes": True}


class GroupListResponse(BaseModel):
    """群组列表响应（管理端用）"""
    id: int
    group_name: str
    owner_id: int
    member_count: int
    is_muted_all: bool
    status: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== 用户处置相关 ====================

class MuteUserRequest(BaseModel):
    """禁言用户请求"""
    duration_minutes: int = Field(default=30, ge=1, le=1440, description="禁言时长（分钟），最大1440（24小时）")


class BanUserRequest(BaseModel):
    """封号请求"""
    reason: str = Field(default="违规行为", max_length=256, description="封号原因")


# ==================== IM 消息收发相关（成员C 依赖） ====================

class MessageSend(BaseModel):
    """发送消息请求"""
    chat_type: str = Field(..., pattern="^(private|group)$", description="会话类型: private / group")
    receiver_id: int | None = Field(None, description="接收者ID（私聊）")
    group_id: int | None = Field(None, description="群组ID（群聊）")
    msg_type: str = Field(default="text", pattern="^(text|image|file|voice|video|system)$", description="消息类型")
    content: str = Field(..., min_length=1, max_length=10000, description="消息内容")


class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    chat_type: str
    sender_type: str
    sender_id: int
    sender_name: str | None = None
    receiver_id: int | None = None
    group_id: int | None = None
    msg_type: str
    content: str
    extra: dict | None = None
    is_recalled: bool = False
    recall_reason: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== 群组相关（成员C 依赖） ====================

class GroupCreate(BaseModel):
    """创建群组请求"""
    group_name: str = Field(..., min_length=1, max_length=128, description="群名称")
    avatar_url: str | None = Field(None, max_length=512, description="群头像URL")
    notice: str | None = Field(None, max_length=1024, description="群公告")
    member_ids: list[int] = Field(default=[], description="初始成员ID列表")


class GroupUpdate(BaseModel):
    """更新群组请求"""
    group_name: str | None = Field(None, min_length=1, max_length=128, description="群名称")
    avatar_url: str | None = Field(None, max_length=512, description="群头像URL")
    notice: str | None = Field(None, max_length=1024, description="群公告")
    is_bot_enabled: bool | None = Field(None, description="是否允许数字员工应答")


class GroupResponse(BaseModel):
    """群组响应"""
    id: int
    group_name: str
    avatar_url: str | None = None
    owner_id: int
    notice: str | None = None
    member_count: int = 0
    max_members: int = 500
    is_bot_enabled: bool = True
    is_muted_all: bool = False
    status: int = 1
    created_at: datetime
    members: list["GroupMemberResponse"] = []

    model_config = {"from_attributes": True}


class GroupMemberAdd(BaseModel):
    """添加群成员请求"""
    user_type: str = Field(default="user", pattern="^(user|bot)$", description="成员类型")
    user_ids: list[int] = Field(..., min_length=1, max_length=100, description="成员ID列表")


# ==================== 联系人相关（成员C 依赖） ====================

class ContactAdd(BaseModel):
    """添加联系人请求"""
    contact_user_id: int = Field(..., description="联系人用户ID")
    alias: str | None = Field(None, max_length=64, description="备注名")


class ContactResponse(BaseModel):
    """联系人响应"""
    id: int
    user_id: int
    contact_user_id: int
    username: str | None = None
    alias: str | None = None
    is_online: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== 离线消息相关（成员C 依赖） ====================

class OfflineMessageResponse(BaseModel):
    """离线消息响应"""
    messages: list[dict] = []
    has_more: bool = False


# ==================== 通用 ====================

class PageResult(BaseModel):
    """分页结果"""
    items: list[Any]
    total: int
    page: int
    page_size: int
