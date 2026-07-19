"""Pydantic 请求/响应 Schema

包含:
- auth.py: 认证 + 用户/部门/角色/菜单 Schema（由 成员A 实现）
- nl2sql.py: NL2SQL 相关 Schema（由 成员E 实现）
- im.py: IM + 合规审计相关 Schema（由 成员D 实现）
- crawler.py: 爬虫任务/执行日志/数据清洗 Schema（由 成员F 实现）
"""

# 认证与用户组织 Schema（成员A 负责）
from app.schemas.auth import (
    LoginRequest, LoginResponse, RegisterRequest, RegisterResponse,
    ChangePasswordRequest, RefreshTokenRequest,
    UserCreate, UserUpdate, UserPasswordReset, AdminPasswordReset,
    UserResponse, UserListResponse, UserRoleAssign,
    DeptCreate, DeptUpdate, DeptResponse,
    RoleCreate, RoleUpdate, RoleMenuAssign, RoleResponse,
    MenuCreate, MenuUpdate, MenuResponse,
)

# 爬虫 Schema（成员F 负责）
from app.schemas.crawler import (
    CrawlerTaskCreate,
    CrawlerTaskUpdate,
    CrawlerTaskResponse,
    CrawlerExecutionLogResponse,
    CrawlerExecutionLogQuery,
    DataCleanRuleCreate,
    DataCleanRuleUpdate,
    DataCleanRuleResponse,
    CrawlResult,
    CrawlerTestRequest,
    CrawlerTestResponse,
)

# 通知 Schema（成员C 负责）
from app.schemas.notification import (
    NotificationResponse,
    NotificationDetailResponse,
    UnreadCountResponse,
)

# IM + 合规审计 Schema（成员D 负责）
from app.schemas.im import (
    SensitiveWordCreate,
    SensitiveWordUpdate,
    SensitiveWordResponse,
    AuditLogResponse,
    AuditLogSearchRequest,
    MessageSearchRequest,
    MessageSearchResponse,
    MessageRecallRequest,
    GroupSystemMessageRequest,
    GroupMemberResponse,
    GroupDetailResponse,
    GroupListResponse,
    MuteUserRequest,
    BanUserRequest,
    MessageSend,
    MessageResponse,
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupMemberAdd,
    ContactAdd,
    ContactResponse,
    OfflineMessageResponse,
    PageResult,
)

# NL2SQL Schema（成员E 负责）
from app.schemas.nl2sql import (
    Nl2sqlAskRequest,
    Nl2sqlAskResponse,
    ColumnInfo,
    TableSchema,
    SchemaInfo,
    SqlValidationResult,
    ChartRecommendation,
    QueryHistoryItem,
    QueryHistoryDetail,
    QueryHistoryListRequest,
    DeleteHistoryRequest,
    FavoriteCreateRequest,
    FavoriteItem,
    FavoriteListRequest,
    FavoriteUpdateRequest,
    SchemaInfoRequest,
    SchemaInfoResponse,
)

__all__ = [
    # Auth
    "LoginRequest", "LoginResponse", "RegisterRequest", "RegisterResponse",
    "ChangePasswordRequest", "RefreshTokenRequest",
    "UserCreate", "UserUpdate", "UserPasswordReset", "AdminPasswordReset",
    "UserResponse", "UserListResponse", "UserRoleAssign",
    "DeptCreate", "DeptUpdate", "DeptResponse",
    "RoleCreate", "RoleUpdate", "RoleMenuAssign", "RoleResponse",
    "MenuCreate", "MenuUpdate", "MenuResponse",
    # Crawler
    "CrawlerTaskCreate",
    "CrawlerTaskUpdate",
    "CrawlerTaskResponse",
    "CrawlerExecutionLogResponse",
    "CrawlerExecutionLogQuery",
    "DataCleanRuleCreate",
    "DataCleanRuleUpdate",
    "DataCleanRuleResponse",
    "CrawlResult",
    "CrawlerTestRequest",
    "CrawlerTestResponse",
    # IM
    "SensitiveWordCreate",
    "SensitiveWordUpdate",
    "SensitiveWordResponse",
    "AuditLogResponse",
    "AuditLogSearchRequest",
    "MessageSearchRequest",
    "MessageSearchResponse",
    "MessageRecallRequest",
    "GroupSystemMessageRequest",
    "GroupMemberResponse",
    "GroupDetailResponse",
    "GroupListResponse",
    "MuteUserRequest",
    "BanUserRequest",
    "MessageSend",
    "MessageResponse",
    "GroupCreate",
    "GroupUpdate",
    "GroupResponse",
    "GroupMemberAdd",
    "ContactAdd",
    "ContactResponse",
    "OfflineMessageResponse",
    "PageResult",
    # NL2SQL
    "Nl2sqlAskRequest",
    "Nl2sqlAskResponse",
    "ColumnInfo",
    "TableSchema",
    "SchemaInfo",
    "SqlValidationResult",
    "ChartRecommendation",
    "QueryHistoryItem",
    "QueryHistoryDetail",
    "QueryHistoryListRequest",
    "DeleteHistoryRequest",
    "FavoriteCreateRequest",
    "FavoriteItem",
    "FavoriteListRequest",
    "FavoriteUpdateRequest",
    "SchemaInfoRequest",
    "SchemaInfoResponse",
    # Notification
    "NotificationResponse",
    "NotificationDetailResponse",
    "UnreadCountResponse",

]
