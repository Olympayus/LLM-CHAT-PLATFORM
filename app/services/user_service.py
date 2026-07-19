"""用户组织管理服务层 - F-01 用户组织管理

说明：所有用户/部门/角色/菜单的服务实现已统一在 auth_service.py 中。
本文件仅重新导出，保持模块结构清晰，避免重复类定义导致的异常捕获失效。
"""

from app.services.auth_service import (
    AuthError,
    BusinessError,
    NotFoundError,
    AuthService,
    UserService,
    DeptService,
    RoleService,
    MenuService,
)

__all__ = [
    "AuthError",
    "BusinessError",
    "NotFoundError",
    "AuthService",
    "UserService",
    "DeptService",
    "RoleService",
    "MenuService",
]
