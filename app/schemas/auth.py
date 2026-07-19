"""认证模块 Pydantic Schema"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re


def validate_password_strength(v: str) -> str:
    """验证密码强度：8-64位，包含大写+小写+数字+特殊字符"""
    if len(v) < 8 or len(v) > 64:
        raise ValueError("密码长度需在8-64位之间")
    if not re.search(r"[A-Z]", v):
        raise ValueError("密码需包含大写字母")
    if not re.search(r"[a-z]", v):
        raise ValueError("密码需包含小写字母")
    if not re.search(r"\d", v):
        raise ValueError("密码需包含数字")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
        raise ValueError("密码需包含特殊字符")
    return v


class ApiResponse(BaseModel):
    """统一响应格式"""
    code: int = Field(default=0, description="错误码 0=成功")
    message: str = Field(default="success", description="提示信息")
    data: Optional[object] = None


class PageResponse(BaseModel):
    """分页响应"""
    items: List = Field(..., description="数据列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str = Field(..., description="JWT Token")
    token_type: str = Field(default="bearer", description="Token 类型")
    expires_in: int = Field(..., description="过期时间(秒)")


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=2, max_length=64, description="用户名")
    password: str = Field(..., min_length=8, max_length=64, description="密码")


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=2, max_length=64, description="用户名")
    password: str = Field(..., min_length=8, max_length=64, description="密码")
    email: Optional[str] = Field(None, max_length=128, description="邮箱")
    mobile: Optional[str] = Field(None, max_length=20, description="手机号")
    real_name: Optional[str] = Field(None, max_length=64, description="真实姓名")
    _validate_password = field_validator("password")(validate_password_strength)


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求"""
    refresh_token: str = Field(..., description="刷新令牌")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., min_length=8, max_length=64)
    new_password: str = Field(..., min_length=8, max_length=64)
    _validate_new_password = field_validator("new_password")(validate_password_strength)


class LoginResponse(BaseModel):
    """登录响应"""
    code: int = 0
    message: str = "success"
    data: Optional[dict] = None


class RegisterResponse(BaseModel):
    """注册响应"""
    code: int = 0
    message: str = "success"
    data: Optional[dict] = None


class UserCreate(BaseModel):
    """创建用户"""
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=8, max_length=64)
    email: Optional[str] = Field(None, max_length=128)
    mobile: Optional[str] = Field(None, max_length=20)
    real_name: Optional[str] = Field(None, max_length=64)
    dept_id: Optional[int] = Field(None, description="部门ID")
    status: int = Field(default=1, description="状态 1=正常 0=禁用")
    _validate_password = field_validator("password")(validate_password_strength)


class UserUpdate(BaseModel):
    """更新用户"""
    email: Optional[str] = Field(None, max_length=128)
    mobile: Optional[str] = Field(None, max_length=20)
    real_name: Optional[str] = Field(None, max_length=64)
    avatar_url: Optional[str] = Field(None, max_length=512)
    dept_id: Optional[int] = None
    status: Optional[int] = None


class UserPasswordReset(BaseModel):
    """密码重置（用户自己修改密码）"""
    old_password: str = Field(..., min_length=8, max_length=64)
    new_password: str = Field(..., min_length=8, max_length=64)
    _validate_new_password = field_validator("new_password")(validate_password_strength)


class AdminPasswordReset(BaseModel):
    """管理员重置用户密码"""
    new_password: str = Field(..., min_length=8, max_length=64)
    _validate_password = field_validator("new_password")(validate_password_strength)


class UserRoleAssign(BaseModel):
    """用户分配角色"""
    role_ids: List[int] = Field(..., description="角色ID列表")


class UserListRequest(BaseModel):
    """用户列表查询参数"""
    keyword: Optional[str] = Field(None, max_length=64, description="关键词搜索")
    dept_id: Optional[int] = Field(None, description="部门ID")
    status: Optional[int] = Field(None, description="状态过滤")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数")


class UserInfo(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    email: Optional[str] = None
    mobile: Optional[str] = None
    real_name: Optional[str] = None
    avatar_url: Optional[str] = None
    dept_id: Optional[int] = None
    dept_name: Optional[str] = None
    status: int
    is_online: int
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    created_at: datetime
    roles: List[str] = []
    permissions: List[str] = []
    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """用户信息响应（路由用）"""
    id: int
    username: str
    email: Optional[str] = None
    mobile: Optional[str] = None
    real_name: Optional[str] = None
    avatar_url: Optional[str] = None
    dept_id: Optional[int] = None
    dept_name: Optional[str] = None
    status: int
    is_online: int
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    created_at: datetime
    roles: List[str] = []
    permissions: List[str] = []
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """用户列表响应"""
    code: int = 0
    message: str = "ok"
    data: Optional[dict] = None


class DeptCreate(BaseModel):
    """创建部门"""
    name: str = Field(..., min_length=1, max_length=64)
    parent_id: int = Field(default=0, description="父部门ID")
    sort_order: int = Field(default=0)
    leader_id: Optional[int] = None


class DeptUpdate(BaseModel):
    """更新部门"""
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None
    leader_id: Optional[int] = None


class DeptInfo(BaseModel):
    """部门信息响应"""
    id: int
    parent_id: int
    name: str
    sort_order: int
    leader_id: Optional[int] = None
    created_at: datetime
    children: List["DeptInfo"] = []
    class Config:
        from_attributes = True


class DeptResponse(BaseModel):
    """部门响应"""
    id: int
    parent_id: int
    name: str
    sort_order: int
    leader_id: Optional[int] = None
    created_at: datetime
    children: List["DeptResponse"] = []
    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    """创建角色"""
    name: str = Field(..., min_length=1, max_length=64)
    code: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = Field(None, max_length=256)
    is_enabled: int = Field(default=1)


class RoleUpdate(BaseModel):
    """更新角色"""
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    description: Optional[str] = Field(None, max_length=256)
    is_enabled: Optional[int] = None


class RoleInfo(BaseModel):
    """角色信息响应"""
    id: int
    name: str
    code: str
    description: Optional[str] = None
    is_enabled: int
    created_at: datetime
    menu_ids: List[int] = []
    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    """角色响应"""
    id: int
    name: str
    code: str
    description: Optional[str] = None
    is_enabled: int
    created_at: datetime
    menu_ids: List[int] = []
    class Config:
        from_attributes = True


class RoleMenuAssign(BaseModel):
    """角色分配菜单"""
    menu_ids: List[int] = Field(..., description="菜单ID列表")


class MenuCreate(BaseModel):
    """创建菜单"""
    parent_id: int = Field(default=0)
    name: str = Field(..., min_length=1, max_length=64)
    permission: Optional[str] = Field(None, max_length=128)
    path: Optional[str] = Field(None, max_length=256)
    component: Optional[str] = Field(None, max_length=256)
    icon: Optional[str] = Field(None, max_length=64)
    menu_type: str = Field(default="menu", pattern="^(menu|directory|button)$")
    sort_order: int = Field(default=0)
    is_enabled: int = Field(default=1)
    is_visible: int = Field(default=1)


class MenuUpdate(BaseModel):
    """更新菜单"""
    parent_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    permission: Optional[str] = Field(None, max_length=128)
    path: Optional[str] = Field(None, max_length=256)
    component: Optional[str] = Field(None, max_length=256)
    icon: Optional[str] = Field(None, max_length=64)
    menu_type: Optional[str] = Field(None, pattern="^(menu|directory|button)$")
    sort_order: Optional[int] = None
    is_enabled: Optional[int] = None
    is_visible: Optional[int] = None


class MenuInfo(BaseModel):
    """菜单信息响应"""
    id: int
    parent_id: int
    name: str
    permission: Optional[str] = None
    path: Optional[str] = None
    component: Optional[str] = None
    icon: Optional[str] = None
    menu_type: str
    sort_order: int
    is_enabled: int
    is_visible: int
    created_at: datetime
    children: List["MenuInfo"] = []
    class Config:
        from_attributes = True


class MenuResponse(BaseModel):
    """菜单响应"""
    id: int
    parent_id: int
    name: str
    permission: Optional[str] = None
    path: Optional[str] = None
    component: Optional[str] = None
    icon: Optional[str] = None
    menu_type: str
    sort_order: int
    is_enabled: int
    is_visible: int
    created_at: datetime
    children: List["MenuResponse"] = []
    class Config:
        from_attributes = True
