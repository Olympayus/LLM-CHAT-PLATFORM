"""认证与用户管理服务层"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from sqlalchemy import or_, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import (
    SysUser, SysRole, SysMenu, SysDept,
    UserRoleRel, RoleMenuRel
)
from app.schemas.auth import (
    UserCreate, UserUpdate, UserPasswordReset, AdminPasswordReset,
    ChangePasswordRequest,
    DeptCreate, DeptUpdate,
    RoleCreate, RoleUpdate, RoleMenuAssign, UserRoleAssign,
    MenuCreate, MenuUpdate
)
from app.core.security import (
    hash_password, verify_password,
    create_access_token,
)


class AuthError(Exception):
    pass


class BusinessError(Exception):
    pass


class NotFoundError(Exception):
    pass


# ==================== 认证 ====================

class AuthService:
    """认证服务"""

    @staticmethod
    async def authenticate(db: AsyncSession, username: str, password: str) -> Tuple[SysUser, str]:
        """用户认证，返回(user, token)"""
        result = await db.execute(
            select(SysUser).where(
                SysUser.username == username,
                SysUser.is_deleted == 0
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            raise AuthError("用户名或密码错误")

        if user.status == 0:
            raise AuthError("账号已被禁用")

        if user.status == 2:
            raise AuthError("账号已被封号")

        if not verify_password(password, user.password_hash):
            raise AuthError("用户名或密码错误")

        # 更新登录信息
        user.last_login_at = datetime.now()
        user.is_online = 1
        await db.commit()

        # 生成 Token
        token = create_access_token(
            data={"sub": str(user.id), "username": user.username}
        )

        return user, token

    @staticmethod
    async def register(db: AsyncSession, user_data: dict) -> SysUser:
        """用户注册"""
        # 检查用户名是否已存在
        result = await db.execute(
            select(SysUser).where(
                SysUser.username == user_data["username"],
                SysUser.is_deleted == 0
            )
        )
        if result.scalar_one_or_none():
            raise BusinessError("用户名已存在")

        # 检查邮箱是否已存在
        if user_data.get("email"):
            result = await db.execute(
                select(SysUser).where(
                    SysUser.email == user_data["email"],
                    SysUser.is_deleted == 0
                )
            )
            if result.scalar_one_or_none():
                raise BusinessError("邮箱已被注册")

        # 创建用户
        user = SysUser(
            username=user_data["username"],
            password_hash=hash_password(user_data["password"]),
            email=user_data.get("email"),
            mobile=user_data.get("mobile"),
            real_name=user_data.get("real_name"),
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def logout(db: AsyncSession, user_id: int):
        """用户登出"""
        result = await db.execute(
            select(SysUser).where(
                SysUser.id == user_id,
                SysUser.is_deleted == 0
            )
        )
        user = result.scalar_one_or_none()
        if user:
            user.is_online = 0
            await db.commit()

    @staticmethod
    async def get_current_user(db: AsyncSession, user_id: int) -> SysUser:
        """获取当前登录用户"""
        result = await db.execute(
            select(SysUser).where(
                SysUser.id == user_id,
                SysUser.is_deleted == 0
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise AuthError("用户不存在或已注销")
        if user.status == 0:
            raise AuthError("账号已被禁用")
        return user

    @staticmethod
    async def change_password(db: AsyncSession, user_id: int, data: ChangePasswordRequest):
        """修改密码"""
        result = await db.execute(
            select(SysUser).where(
                SysUser.id == user_id,
                SysUser.is_deleted == 0
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise AuthError("用户不存在")

        if not verify_password(data.old_password, user.password_hash):
            raise BusinessError("原密码错误")

        user.password_hash = hash_password(data.new_password)
        user.updated_at = datetime.now()
        await db.commit()

    @staticmethod
    async def refresh_token(db: AsyncSession, user_id: int) -> Tuple[str, str]:
        """刷新 Token"""
        result = await db.execute(
            select(SysUser).where(
                SysUser.id == user_id,
                SysUser.is_deleted == 0,
                SysUser.status == 1
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise AuthError("用户不存在或已禁用")

        access_token = create_access_token(
            data={"sub": str(user.id), "username": user.username}
        )
        # TODO(成员A): 接入 refresh_token 逻辑
        refresh_token = create_access_token(
            data={"sub": str(user.id), "type": "refresh"},
            expires_delta=timedelta(days=7),
        )
        return access_token, refresh_token


# ==================== 用户管理 ====================

class UserService:
    """用户管理服务"""

    @staticmethod
    async def create_user(db: AsyncSession, data: UserCreate) -> SysUser:
        """创建用户（管理员）"""
        result = await db.execute(
            select(SysUser).where(
                SysUser.username == data.username,
                SysUser.is_deleted == 0
            )
        )
        if result.scalar_one_or_none():
            raise BusinessError("用户名已存在")

        user = SysUser(
            username=data.username,
            password_hash=hash_password(data.password),
            email=data.email,
            mobile=data.mobile,
            real_name=data.real_name,
            dept_id=data.dept_id,
            status=data.status,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def update_user(db: AsyncSession, user_id: int, data: UserUpdate) -> SysUser:
        """更新用户信息"""
        result = await db.execute(
            select(SysUser).where(
                SysUser.id == user_id,
                SysUser.is_deleted == 0
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("用户不存在")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(user, key, value)
        user.updated_at = datetime.now()

        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def reset_password(db: AsyncSession, user_id: int, data: UserPasswordReset):
        """重置密码"""
        result = await db.execute(
            select(SysUser).where(
                SysUser.id == user_id,
                SysUser.is_deleted == 0
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("用户不存在")

        if not verify_password(data.old_password, user.password_hash):
            raise BusinessError("原密码错误")

        user.password_hash = hash_password(data.new_password)
        user.updated_at = datetime.now()
        await db.commit()

    @staticmethod
    async def admin_reset_password(db: AsyncSession, user_id: int, data: AdminPasswordReset):
        """管理员重置用户密码"""
        result = await db.execute(
            select(SysUser).where(
                SysUser.id == user_id,
                SysUser.is_deleted == 0
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("用户不存在")

        user.password_hash = hash_password(data.new_password)
        user.updated_at = datetime.now()
        await db.commit()

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: int):
        """删除用户（软删除）"""
        result = await db.execute(
            select(SysUser).where(
                SysUser.id == user_id,
                SysUser.is_deleted == 0
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("用户不存在")

        user.is_deleted = 1
        user.is_online = 0
        user.updated_at = datetime.now()
        await db.commit()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[SysUser]:
        """根据ID获取用户"""
        result = await db.execute(
            select(SysUser).where(
                SysUser.id == user_id,
                SysUser.is_deleted == 0
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_users(
        db: AsyncSession,
        keyword: Optional[str] = None,
        dept_id: Optional[int] = None,
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[SysUser], int]:
        """用户列表（分页）"""
        query = select(SysUser).where(SysUser.is_deleted == 0)

        if keyword:
            query = query.where(
                or_(
                    SysUser.username.ilike(f"%{keyword}%"),
                    SysUser.real_name.ilike(f"%{keyword}%"),
                    SysUser.email.ilike(f"%{keyword}%"),
                    SysUser.mobile.ilike(f"%{keyword}%")
                )
            )

        if dept_id is not None:
            query = query.where(SysUser.dept_id == dept_id)

        if status is not None:
            query = query.where(SysUser.status == status)

        # 获取总数
        count_result = await db.execute(select(SysUser.id).where(SysUser.is_deleted == 0))
        total = len(count_result.all())

        # 分页查询
        result = await db.execute(
            query.order_by(SysUser.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        users = list(result.scalars().all())

        return users, total

    @staticmethod
    async def assign_roles(db: AsyncSession, user_id: int, data: UserRoleAssign):
        """分配用户角色"""
        result = await db.execute(
            select(SysUser).where(
                SysUser.id == user_id,
                SysUser.is_deleted == 0
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("用户不存在")

        # 删除原有角色关联
        await db.execute(
            delete(UserRoleRel).where(UserRoleRel.user_id == user_id)
        )

        # 添加新角色关联
        for role_id in data.role_ids:
            rel = UserRoleRel(user_id=user_id, role_id=role_id)
            db.add(rel)

        await db.commit()

    @staticmethod
    async def get_user_roles(db: AsyncSession, user_id: int) -> List[SysRole]:
        """获取用户角色列表"""
        result = await db.execute(
            select(UserRoleRel).where(UserRoleRel.user_id == user_id)
        )
        rels = result.scalars().all()

        roles = []
        for rel in rels:
            role_result = await db.execute(
                select(SysRole).where(
                    SysRole.id == rel.role_id,
                    SysRole.is_deleted == 0
                )
            )
            role = role_result.scalar_one_or_none()
            if role:
                roles.append(role)
        return roles

    @staticmethod
    async def get_user_permissions(db: AsyncSession, user_id: int) -> List[str]:
        """获取用户权限标识列表"""
        roles = await UserService.get_user_roles(db, user_id)
        role_ids = [r.id for r in roles]

        if not role_ids:
            return []

        result = await db.execute(
            select(RoleMenuRel).where(RoleMenuRel.role_id.in_(role_ids))
        )
        rels = result.scalars().all()

        menu_ids = list(set(rel.menu_id for rel in rels))
        if not menu_ids:
            return []

        result = await db.execute(
            select(SysMenu).where(
                SysMenu.id.in_(menu_ids),
                SysMenu.is_deleted == 0,
                SysMenu.is_enabled == 1,
                SysMenu.permission.isnot(None),
                SysMenu.permission != ""
            )
        )
        menus = result.scalars().all()

        return list(set(m.permission for m in menus))


# ==================== 部门管理 ====================

class DeptService:
    """部门管理服务"""

    @staticmethod
    async def create_dept(db: AsyncSession, data: DeptCreate) -> SysDept:
        """创建部门"""
        dept = SysDept(
            name=data.name,
            parent_id=data.parent_id,
            sort_order=data.sort_order,
            leader_id=data.leader_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(dept)
        await db.commit()
        await db.refresh(dept)
        return dept

    @staticmethod
    async def update_dept(db: AsyncSession, dept_id: int, data: DeptUpdate) -> SysDept:
        """更新部门"""
        result = await db.execute(
            select(SysDept).where(
                SysDept.id == dept_id,
                SysDept.is_deleted == 0
            )
        )
        dept = result.scalar_one_or_none()
        if not dept:
            raise NotFoundError("部门不存在")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(dept, key, value)
        dept.updated_at = datetime.now()

        await db.commit()
        await db.refresh(dept)
        return dept

    @staticmethod
    async def delete_dept(db: AsyncSession, dept_id: int):
        """删除部门"""
        result = await db.execute(
            select(SysDept).where(
                SysDept.id == dept_id,
                SysDept.is_deleted == 0
            )
        )
        dept = result.scalar_one_or_none()
        if not dept:
            raise NotFoundError("部门不存在")

        # 检查是否有子部门
        result = await db.execute(
            select(SysDept).where(
                SysDept.parent_id == dept_id,
                SysDept.is_deleted == 0
            )
        )
        if len(result.all()) > 0:
            raise BusinessError("请先删除子部门")

        # 检查部门下是否有用户
        result = await db.execute(
            select(SysUser).where(
                SysUser.dept_id == dept_id,
                SysUser.is_deleted == 0
            )
        )
        if len(result.all()) > 0:
            raise BusinessError("部门下存在用户，无法删除")

        dept.is_deleted = 1
        dept.updated_at = datetime.now()
        await db.commit()

    @staticmethod
    async def get_dept_tree(db: AsyncSession) -> List[SysDept]:
        """获取部门树"""
        result = await db.execute(
            select(SysDept).where(
                SysDept.is_deleted == 0
            ).order_by(SysDept.sort_order)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_dept_by_id(db: AsyncSession, dept_id: int) -> Optional[SysDept]:
        """根据ID获取部门"""
        result = await db.execute(
            select(SysDept).where(
                SysDept.id == dept_id,
                SysDept.is_deleted == 0
            )
        )
        return result.scalar_one_or_none()


# ==================== 角色管理 ====================

class RoleService:
    """角色管理服务"""

    @staticmethod
    async def create_role(db: AsyncSession, data: RoleCreate) -> SysRole:
        """创建角色"""
        result = await db.execute(
            select(SysRole).where(
                SysRole.name == data.name,
                SysRole.is_deleted == 0
            )
        )
        if result.scalar_one_or_none():
            raise BusinessError("角色名称已存在")

        result = await db.execute(
            select(SysRole).where(
                SysRole.code == data.code,
                SysRole.is_deleted == 0
            )
        )
        if result.scalar_one_or_none():
            raise BusinessError("角色编码已存在")

        role = SysRole(
            name=data.name,
            code=data.code,
            description=data.description,
            is_enabled=data.is_enabled,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(role)
        await db.commit()
        await db.refresh(role)
        return role

    @staticmethod
    async def update_role(db: AsyncSession, role_id: int, data: RoleUpdate) -> SysRole:
        """更新角色"""
        result = await db.execute(
            select(SysRole).where(
                SysRole.id == role_id,
                SysRole.is_deleted == 0
            )
        )
        role = result.scalar_one_or_none()
        if not role:
            raise NotFoundError("角色不存在")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(role, key, value)
        role.updated_at = datetime.now()

        await db.commit()
        await db.refresh(role)
        return role

    @staticmethod
    async def delete_role(db: AsyncSession, role_id: int):
        """删除角色"""
        result = await db.execute(
            select(SysRole).where(
                SysRole.id == role_id,
                SysRole.is_deleted == 0
            )
        )
        role = result.scalar_one_or_none()
        if not role:
            raise NotFoundError("角色不存在")

        # 检查是否有用户关联
        result = await db.execute(
            select(UserRoleRel).where(UserRoleRel.role_id == role_id)
        )
        if len(result.all()) > 0:
            raise BusinessError("角色下存在用户关联，无法删除")

        role.is_deleted = 1
        role.updated_at = datetime.now()
        await db.commit()

    @staticmethod
    async def list_roles(db: AsyncSession) -> List[SysRole]:
        """角色列表"""
        result = await db.execute(
            select(SysRole).where(
                SysRole.is_deleted == 0
            ).order_by(SysRole.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_role_by_id(db: AsyncSession, role_id: int) -> Optional[SysRole]:
        """根据ID获取角色"""
        result = await db.execute(
            select(SysRole).where(
                SysRole.id == role_id,
                SysRole.is_deleted == 0
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def assign_menus(db: AsyncSession, role_id: int, data: RoleMenuAssign):
        """分配角色菜单权限"""
        result = await db.execute(
            select(SysRole).where(
                SysRole.id == role_id,
                SysRole.is_deleted == 0
            )
        )
        role = result.scalar_one_or_none()
        if not role:
            raise NotFoundError("角色不存在")

        # 删除原有菜单关联
        await db.execute(
            delete(RoleMenuRel).where(RoleMenuRel.role_id == role_id)
        )

        # 添加新菜单关联
        for menu_id in data.menu_ids:
            rel = RoleMenuRel(role_id=role_id, menu_id=menu_id)
            db.add(rel)

        await db.commit()

    @staticmethod
    async def get_role_menus(db: AsyncSession, role_id: int) -> List[SysMenu]:
        """获取角色的菜单列表"""
        result = await db.execute(
            select(RoleMenuRel).where(RoleMenuRel.role_id == role_id)
        )
        rels = result.scalars().all()

        menus = []
        for rel in rels:
            menu_result = await db.execute(
                select(SysMenu).where(
                    SysMenu.id == rel.menu_id,
                    SysMenu.is_deleted == 0
                )
            )
            menu = menu_result.scalar_one_or_none()
            if menu:
                menus.append(menu)
        return menus


# ==================== 菜单管理 ====================

class MenuService:
    """菜单管理服务"""

    @staticmethod
    async def create_menu(db: AsyncSession, data: MenuCreate) -> SysMenu:
        """创建菜单"""
        menu = SysMenu(
            parent_id=data.parent_id,
            name=data.name,
            permission=data.permission,
            path=data.path,
            component=data.component,
            icon=data.icon,
            menu_type=data.menu_type,
            sort_order=data.sort_order,
            is_enabled=data.is_enabled,
            is_visible=data.is_visible,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(menu)
        await db.commit()
        await db.refresh(menu)
        return menu

    @staticmethod
    async def update_menu(db: AsyncSession, menu_id: int, data: MenuUpdate) -> SysMenu:
        """更新菜单"""
        result = await db.execute(
            select(SysMenu).where(
                SysMenu.id == menu_id,
                SysMenu.is_deleted == 0
            )
        )
        menu = result.scalar_one_or_none()
        if not menu:
            raise NotFoundError("菜单不存在")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(menu, key, value)
        menu.updated_at = datetime.now()

        await db.commit()
        await db.refresh(menu)
        return menu

    @staticmethod
    async def delete_menu(db: AsyncSession, menu_id: int):
        """删除菜单"""
        result = await db.execute(
            select(SysMenu).where(
                SysMenu.id == menu_id,
                SysMenu.is_deleted == 0
            )
        )
        menu = result.scalar_one_or_none()
        if not menu:
            raise NotFoundError("菜单不存在")

        # 检查是否有子菜单
        result = await db.execute(
            select(SysMenu).where(
                SysMenu.parent_id == menu_id,
                SysMenu.is_deleted == 0
            )
        )
        if len(result.all()) > 0:
            raise BusinessError("请先删除子菜单")

        menu.is_deleted = 1
        menu.updated_at = datetime.now()
        await db.commit()

    @staticmethod
    async def get_menu_tree(db: AsyncSession) -> List[SysMenu]:
        """获取菜单树"""
        result = await db.execute(
            select(SysMenu).where(
                SysMenu.is_deleted == 0
            ).order_by(SysMenu.sort_order)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_menu_by_id(db: AsyncSession, menu_id: int) -> Optional[SysMenu]:
        """根据ID获取菜单"""
        result = await db.execute(
            select(SysMenu).where(
                SysMenu.id == menu_id,
                SysMenu.is_deleted == 0
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_menus(db: AsyncSession, user_id: int) -> List[SysMenu]:
        """获取用户可见的菜单树"""
        permissions = await UserService.get_user_permissions(db, user_id)
        if not permissions:
            return []

        result = await db.execute(
            select(SysMenu).where(
                SysMenu.permission.in_(permissions),
                SysMenu.is_deleted == 0,
                SysMenu.is_enabled == 1,
                SysMenu.is_visible == 1
            ).order_by(SysMenu.sort_order)
        )
        return list(result.scalars().all())