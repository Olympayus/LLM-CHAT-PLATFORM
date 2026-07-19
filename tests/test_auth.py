"""认证模块测试"""

import pytest
from app.services.auth_service import AuthService, UserService, DeptService, RoleService, AuthError, BusinessError, NotFoundError
from app.core.security import verify_password


class TestAuthService:
    """认证服务测试"""

    def test_register_success(self, db_session):
        """测试注册成功"""
        user_data = {
            "username": "newuser",
            "password": "Test@123456",
            "email": "new@example.com",
            "real_name": "新用户",
        }
        user = AuthService.register(db_session, user_data)
        assert user.id is not None
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.status == 1

    def test_register_duplicate_username(self, db_session, sample_user):
        """测试重复用户名注册"""
        user_data = {
            "username": "testuser",
            "password": "Test@123456",
        }
        with pytest.raises(BusinessError, match="用户名已存在"):
            AuthService.register(db_session, user_data)

    def test_register_duplicate_email(self, db_session, sample_user):
        """测试重复邮箱注册"""
        user_data = {
            "username": "another",
            "password": "Test@123456",
            "email": "test@example.com",
        }
        with pytest.raises(BusinessError, match="邮箱已被注册"):
            AuthService.register(db_session, user_data)

    def test_authenticate_success(self, db_session, sample_user):
        """测试登录成功"""
        user, token = AuthService.authenticate(db_session, "testuser", "Test@123456")
        assert user.id == sample_user.id
        assert token is not None
        assert len(token) > 0

    def test_authenticate_wrong_password(self, db_session, sample_user):
        """测试密码错误"""
        with pytest.raises(AuthError, match="用户名或密码错误"):
            AuthService.authenticate(db_session, "testuser", "Wrong@123")

    def test_authenticate_user_not_found(self, db_session):
        """测试用户不存在"""
        with pytest.raises(AuthError, match="用户名或密码错误"):
            AuthService.authenticate(db_session, "nonexistent", "Test@123456")

    def test_authenticate_disabled_user(self, db_session, sample_user):
        """测试禁用账号登录"""
        sample_user.status = 0
        db_session.commit()
        with pytest.raises(AuthError, match="账号已被禁用"):
            AuthService.authenticate(db_session, "testuser", "Test@123456")

    def test_logout(self, db_session, sample_user):
        """测试登出"""
        sample_user.is_online = 1
        db_session.commit()
        AuthService.logout(db_session, sample_user.id)
        assert sample_user.is_online == 0

    def test_get_current_user_success(self, db_session, sample_user):
        """测试获取当前用户"""
        user = AuthService.get_current_user(db_session, sample_user.id)
        assert user.id == sample_user.id

    def test_get_current_user_disabled(self, db_session, sample_user):
        """测试获取已禁用用户"""
        sample_user.status = 0
        db_session.commit()
        with pytest.raises(AuthError, match="账号已被禁用"):
            AuthService.get_current_user(db_session, sample_user.id)

    def test_change_password_success(self, db_session, sample_user):
        """测试修改密码成功"""
        from app.schemas.auth import ChangePasswordRequest
        data = ChangePasswordRequest(old_password="Test@123456", new_password="NewPwd@789")
        AuthService.change_password(db_session, sample_user.id, data)
        db_session.refresh(sample_user)
        assert verify_password("NewPwd@789", sample_user.password_hash)

    def test_change_password_wrong_old(self, db_session, sample_user):
        """测试原密码错误"""
        from app.schemas.auth import ChangePasswordRequest
        data = ChangePasswordRequest(old_password="Wrong@123", new_password="NewPwd@789")
        with pytest.raises(BusinessError, match="原密码错误"):
            AuthService.change_password(db_session, sample_user.id, data)

    def test_login_update_last_login(self, db_session, sample_user):
        """测试登录后 last_login_at 更新"""
        from datetime import datetime
        before = datetime.now()
        AuthService.authenticate(db_session, "testuser", "Test@123456")
        db_session.refresh(sample_user)
        assert sample_user.last_login_at is not None

    def test_login_banned_user(self, db_session, sample_user):
        """测试封号用户登录"""
        sample_user.status = 2
        db_session.commit()
        with pytest.raises(AuthError, match="账号已被封号"):
            AuthService.authenticate(db_session, "testuser", "Test@123456")

    def test_refresh_token(self, db_session, sample_user):
        """测试 Token 刷新"""
        access_token, refresh_token = AuthService.refresh_token(db_session, sample_user.id)
        assert access_token is not None
        assert refresh_token is not None
        assert len(access_token) > 0
        assert len(refresh_token) > 0

    def test_get_current_user_not_found(self, db_session):
        """测试获取不存在的用户"""
        with pytest.raises(AuthError, match="用户不存在或已注销"):
            AuthService.get_current_user(db_session, 99999)


class TestUserService:
    """用户管理服务测试"""

    def test_create_user(self, db_session):
        """测试创建用户"""
        from app.schemas.auth import UserCreate
        data = UserCreate(
            username="admin_created",
            password="Test@123456",
            email="admin@example.com",
            real_name="管理员创建",
        )
        user = UserService.create_user(db_session, data)
        assert user.username == "admin_created"
        assert user.status == 1

    def test_update_user(self, db_session, sample_user):
        """测试更新用户"""
        from app.schemas.auth import UserUpdate
        data = UserUpdate(real_name="更新后的名字", email="newemail@example.com")
        user = UserService.update_user(db_session, sample_user.id, data)
        assert user.real_name == "更新后的名字"
        assert user.email == "newemail@example.com"

    def test_delete_user(self, db_session, sample_user):
        """测试删除用户（软删除）"""
        UserService.delete_user(db_session, sample_user.id)
        db_session.refresh(sample_user)
        assert sample_user.is_deleted == 1

    def test_list_users(self, db_session, sample_user):
        """测试用户列表"""
        users, total = UserService.list_users(db_session)
        assert total >= 1
        assert any(u.id == sample_user.id for u in users)

    def test_list_users_with_keyword(self, db_session, sample_user):
        """测试关键字搜索"""
        users, total = UserService.list_users(db_session, keyword="testuser")
        assert total >= 1

    def test_admin_reset_password(self, db_session, sample_user):
        """测试管理员重置密码"""
        from app.schemas.auth import AdminPasswordReset
        data = AdminPasswordReset(new_password="Admin@123456")
        UserService.admin_reset_password(db_session, sample_user.id, data)
        db_session.refresh(sample_user)
        assert verify_password("Admin@123456", sample_user.password_hash)

    def test_assign_roles(self, db_session, sample_user, sample_role):
        """测试分配角色"""
        from app.schemas.auth import UserRoleAssign
        data = UserRoleAssign(role_ids=[sample_role.id])
        UserService.assign_roles(db_session, sample_user.id, data)

        roles = UserService.get_user_roles(db_session, sample_user.id)
        assert len(roles) == 1
        assert roles[0].id == sample_role.id

    def test_get_user_permissions(self, db_session, sample_user, sample_role, sample_menu):
        """测试获取用户权限"""
        from app.models.user import RoleMenuRel
        from app.schemas.auth import UserRoleAssign

        # 分配角色
        data = UserRoleAssign(role_ids=[sample_role.id])
        UserService.assign_roles(db_session, sample_user.id, data)

        # 分配菜单权限到角色
        rel = RoleMenuRel(role_id=sample_role.id, menu_id=sample_menu.id)
        db_session.add(rel)
        db_session.commit()

        permissions = UserService.get_user_permissions(db_session, sample_user.id)
        assert "test:menu" in permissions

    def test_create_user_duplicate_username(self, db_session, sample_user):
        """测试管理员创建重复用户名"""
        from app.schemas.auth import UserCreate
        data = UserCreate(username="testuser", password="Test@123456")
        with pytest.raises(BusinessError, match="用户名已存在"):
            UserService.create_user(db_session, data)

    def test_update_user_not_found(self, db_session):
        """测试更新不存在的用户"""
        from app.schemas.auth import UserUpdate
        data = UserUpdate(real_name="不存在")
        with pytest.raises(NotFoundError, match="用户不存在"):
            UserService.update_user(db_session, 99999, data)

    def test_delete_user_not_found(self, db_session):
        """测试删除不存在的用户"""
        with pytest.raises(NotFoundError, match="用户不存在"):
            UserService.delete_user(db_session, 99999)

    def test_list_users_filter_by_status(self, db_session, sample_user):
        """测试按状态过滤用户列表"""
        users, total = UserService.list_users(db_session, status=1)
        assert total >= 1

    def test_list_users_filter_by_dept(self, db_session, sample_user, sample_dept):
        """测试按部门过滤用户列表"""
        sample_user.dept_id = sample_dept.id
        db_session.commit()
        users, total = UserService.list_users(db_session, dept_id=sample_dept.id)
        assert total >= 1

    def test_get_user_permissions_empty(self, db_session, sample_user):
        """测试无角色用户的权限为空"""
        permissions = UserService.get_user_permissions(db_session, sample_user.id)
        assert permissions == []


class TestDeptService:
    """部门管理服务测试"""

    def test_create_dept(self, db_session):
        """测试创建部门"""
        from app.schemas.auth import DeptCreate
        data = DeptCreate(name="新部门", parent_id=0, sort_order=1)
        dept = DeptService.create_dept(db_session, data)

        assert dept.name == "新部门"

    def test_delete_dept_with_children(self, db_session, sample_dept):
        """测试删除有子部门的部门"""
        from app.schemas.auth import DeptCreate

        # 创建子部门
        child_data = DeptCreate(name="子部门", parent_id=sample_dept.id)
        DeptService.create_dept(db_session, child_data)

        with pytest.raises(BusinessError, match="请先删除子部门"):
            DeptService.delete_dept(db_session, sample_dept.id)


class TestRoleService:
    """角色管理服务测试"""

    def test_create_role(self, db_session):
        """测试创建角色"""
        from app.schemas.auth import RoleCreate

        data = RoleCreate(name="新角色", code="new_role")
        role = RoleService.create_role(db_session, data)
        assert role.name == "新角色"
        assert role.code == "new_role"

    def test_assign_menus(self, db_session, sample_role, sample_menu):
        """测试分配菜单"""
        from app.schemas.auth import RoleMenuAssign

        data = RoleM