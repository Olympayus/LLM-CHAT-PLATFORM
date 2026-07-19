"""璁よ瘉妯″潡 Pydantic Schema"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re


# ============================================================
# 瀵嗙爜寮哄害鏍￠獙鍏叡鍑芥暟
# ============================================================

def validate_password_strength(v: str) -> str:
    """鏍￠獙瀵嗙爜寮哄害锛?-64浣嶏紝鍖呭惈澶у啓+灏忓啓+鏁板瓧+鐗规畩瀛楃"""
    if len(v) < 8 or len(v) > 64:
        raise ValueError("瀵嗙爜闀垮害闇€鍦?-64浣嶄箣闂?)
    if not re.search(r"[A-Z]", v):
        raise ValueError("瀵嗙爜闇€鍖呭惈澶у啓瀛楁瘝")
    if not re.search(r"[a-z]", v):
        raise ValueError("瀵嗙爜闇€鍖呭惈灏忓啓瀛楁瘝")
    if not re.search(r"\d", v):
        raise ValueError("瀵嗙爜闇€鍖呭惈鏁板瓧")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
        raise ValueError("瀵嗙爜闇€鍖呭惈鐗规畩瀛楃")
    return v


# ============================================================
# 閫氱敤 Schema
# ============================================================

class ApiResponse(BaseModel):
    """缁熶竴鍝嶅簲鏍煎紡"""
    code: int = Field(default=0, description="閿欒鐮? 0=鎴愬姛")
    message: str = Field(default="success", description="鎻愮ず淇℃伅")
    data: Optional[object] = None


class PageResponse(BaseModel):
    """鍒嗛〉鍝嶅簲"""
    items: List = Field(..., description="鏁版嵁鍒楄〃")
    total: int = Field(..., description="鎬绘暟")
    page: int = Field(..., description="褰撳墠椤电爜")
    page_size: int = Field(..., description="姣忛〉鏉℃暟")


class TokenResponse(BaseModel):
    """Token 鍝嶅簲"""
    access_token: str = Field(..., description="JWT Token")
    token_type: str = Field(default="bearer", description="Token 绫诲瀷")
    expires_in: int = Field(..., description="杩囨湡鏃堕棿(绉?")


# ============================================================
# 璁よ瘉璇锋眰
# ============================================================

class LoginRequest(BaseModel):
    """鐧诲綍璇锋眰"""
    username: str = Field(..., min_length=2, max_length=64, description="鐢ㄦ埛鍚?)
    password: str = Field(..., min_length=8, max_length=64, description="瀵嗙爜")


class RegisterRequest(BaseModel):
    """娉ㄥ唽璇锋眰"""
    username: str = Field(..., min_length=2, max_length=64, description="鐢ㄦ埛鍚?)
    password: str = Field(..., min_length=8, max_length=64, description="瀵嗙爜")
    email: Optional[str] = Field(None, max_length=128, description="閭")
    mobile: Optional[str] = Field(None, max_length=20, description="鎵嬫満鍙?)
    real_name: Optional[str] = Field(None, max_length=64, description="鐪熷疄濮撳悕")

    _validate_password = field_validator("password")(validate_password_strength)


class ChangePasswordRequest(BaseModel):
    """淇敼瀵嗙爜璇锋眰"""
    old_password: str = Field(..., min_length=8, max_length=64)
    new_password: str = Field(..., min_length=8, max_length=64)

    _validate_new_password = field_validator("new_password")(validate_password_strength)


# ============================================================
# 璁よ瘉鍝嶅簲
# ============================================================

class LoginResponse(BaseModel):
    """鐧诲綍鍝嶅簲"""
    code: int = 0
    message: str = "success"
    data: Optional[dict] = None


class RegisterResponse(BaseModel):
    """娉ㄥ唽鍝嶅簲"""
    code: int = 0
    message: str = "success"
    data: Optional[dict] = None


# ============================================================
# 鐢ㄦ埛璇锋眰
# ============================================================

class UserCreate(BaseModel):
    """鍒涘缓鐢ㄦ埛"""
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=8, max_length=64)
    email: Optional[str] = Field(None, max_length=128)
    mobile: Optional[str] = Field(None, max_length=20)
    real_name: Optional[str] = Field(None, max_length=64)
    dept_id: Optional[int] = Field(None, description="閮ㄩ棬ID")
    status: int = Field(default=1, description="鐘舵€? 1=姝ｅ父 0=绂佺敤")

    _validate_password = field_validator("password")(validate_password_strength)


class UserUpdate(BaseModel):
    """鏇存柊鐢ㄦ埛"""
    email: Optional[str] = Field(None, max_length=128)
    mobile: Optional[str] = Field(None, max_length=20)
    real_name: Optional[str] = Field(None, max_length=64)
    avatar_url: Optional[str] = Field(None, max_length=512)
    dept_id: Optional[int] = None
    status: Optional[int] = None


class UserPasswordReset(BaseModel):
    """瀵嗙爜閲嶇疆锛堢敤鎴疯嚜宸变慨鏀瑰瘑鐮侊級"""
    old_password: str = Field(..., min_length=8, max_length=64)
    new_password: str = Field(..., min_length=8, max_length=64)

    _validate_new_password = field_validator("new_password")(validate_password_strength)


class AdminPasswordReset(BaseModel):
    """绠＄悊鍛橀噸缃敤鎴峰瘑鐮?""
    new_password: str = Field(..., min_length=8, max_length=64)
    _validate_password = field_validator("new_password")(validate_password_strength)


class UserRoleAssign(BaseModel):
    """鐢ㄦ埛鍒嗛厤瑙掕壊"""
    role_ids: List[int] = Field(..., description="瑙掕壊ID鍒楄〃")


class UserListRequest(BaseModel):
    """鐢ㄦ埛鍒楄〃鏌ヨ鍙傛暟"""
    keyword: Optional[str] = Field(None, max_length=64, description="鍏抽敭瀛楁悳绱?)
    dept_id: Optional[int] = Field(None, description="閮ㄩ棬ID")
    status: Optional[int] = Field(None, description="鐘舵€佽繃婊?)
    page: int = Field(default=1, ge=1, description="椤电爜")
    page_size: int = Field(default=20, ge=1, le=100, description="姣忛〉鏉℃暟")


# ============================================================
# 鐢ㄦ埛鍝嶅簲
# ============================================================

class UserInfo(BaseModel):
    """鐢ㄦ埛淇℃伅鍝嶅簲"""
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
    """鐢ㄦ埛淇℃伅鍝嶅簲锛堣矾鐢辩敤锛?""
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
    """鐢ㄦ埛鍒楄〃鍝嶅簲"""
    code: int = 0
    message: str = "ok"
    data: Optional[dict] = None


# ============================================================
# 閮ㄩ棬
# ============================================================

class DeptCreate(BaseModel):
    """鍒涘缓閮ㄩ棬"""
    name: str = Field(..., min_length=1, max_length=64)
    parent_id: int = Field(default=0, description="鐖堕儴闂↖D")
    sort_order: int = Field(default=0)
    leader_id: Optional[int] = None


class DeptUpdate(BaseModel):
    """鏇存柊閮ㄩ棬"""
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None
    leader_id: Optional[int] = None


class DeptInfo(BaseModel):
    """閮ㄩ棬淇℃伅鍝嶅簲"""
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
    """閮ㄩ棬鍝嶅簲"""
    id: int
    parent_id: int
    name: str
    sort_order: int
    leader_id: Optional[int] = None
    created_at: datetime
    children: List["DeptResponse"] = []

    class Config:
        from_attributes = True


# ============================================================
# 瑙掕壊
# ============================================================

class RoleCreate(BaseModel):
    """鍒涘缓瑙掕壊"""
    name: str = Field(..., min_length=1, max_length=64)
    code: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = Field(None, max_length=256)
    is_enabled: int = Field(default=1)


class RoleUpdate(BaseModel):
    """鏇存柊瑙掕壊"""
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    description: Optional[str] = Field(None, max_length=256)
    is_enabled: Optional[int] = None


class RoleInfo(BaseModel):
    """瑙掕壊淇℃伅鍝嶅簲"""
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
    """瑙掕壊鍝嶅簲"""
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
    """瑙掕壊鍒嗛厤鑿滃崟"""
    menu_ids: List[int] = Field(..., description="鑿滃崟ID鍒楄〃")


# ============================================================
# 鑿滃崟
# ============================================================

class MenuCreate(BaseModel):
    """鍒涘缓鑿滃崟"""
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
    """鏇存柊鑿滃崟"""
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
    """鑿滃崟淇℃伅鍝嶅簲"""
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
    """鑿滃崟鍝嶅簲"""
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
