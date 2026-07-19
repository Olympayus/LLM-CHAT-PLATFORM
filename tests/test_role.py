"""角色管理服务测试"""

import pytest
from app.services.auth_service import RoleService, BusinessError, NotFoundError
from app.schemas.auth import RoleCreate, RoleUpdate


class TestRoleService:
    """角色管理服务测试"""

    def test_create_role(self, db_session):
        """测试创建角色"""
        data = RoleCreate(name="新角色", code="new_role")
        role = RoleService.create_role(db_session, data)
        assert role.name == "新角色"
        assert role.code == "new_role"

    def test_create_role_duplicate_name(self, db_session, sample_role):
        """测试重复角色名称"""
        data = RoleCreate(name="测试角色", code="another_code")
        with pytest.raises(BusinessError, match="角色名称已存在"):
            RoleService.create_role(db_session, data)

    def test_create_role_duplicate_code(self, db_session, sample_role):
        """测试重复角色编码"""
        data = RoleCreate(name="另一个角色", code="test_role")
        with pytest.raises(BusinessError, match="角色编码已存在"):
            RoleService.create_role(db_session, data)

    def test_update_role(self, db_session, sample_role):
        """测试更新角色"""
        data = RoleUpdate(name="更新后的角色")
        role = RoleService.update_role(db_session, sample_role.id, data)
        assert role.name == "更新后的角色"

    def test_update_role_not_found(self, db_session):
        """测试更新不存在的角色"""
        data = RoleUpdate(name="不存在的角色")
        with pytest.raises(NotFoundError, match="角色不存在"):
            RoleService.update_role(db_session, 99999, data)

    def test_delete_role(self, db_session, sample_role):
        """测试删除角色"""
        RoleService.delete_role(db_session, sample_role.id)
        assert sample_role.is_deleted == 1

    def test_delete_role_not_found(self, db_session):
        """测试删除不存在的角色"""
        with pytest.raises(NotFoundError, match="角色不存在"):
            RoleService.delete_role(db_session, 99999)

    def test_delete_role_with_users(self, db_session, sample_role, sample_user):
        """测试删除有用户关联的角色"""
        from app.models.user import UserRoleRel
        rel = UserRoleRel(user_id=sample_user.id, role_id=sample_role.id)
        db_session.add(rel)
        db_session.commit()

        with pytest.raises(BusinessError, match="角色下存在用户关联"):
            RoleService.delete_role(db_session, sample_role.id)

    def test_list_roles(self, db_session, sample_role):
        """测试角色列表"""
        roles = RoleService.list_roles(db_session)
        assert len(roles) >= 1
        assert any(r.id == sample_role.id for r in roles)

    def test_get_role_by_id(self, db_session, sample_role):
        """测试获取角色详情"""
        role = RoleService.get_role_by_id(db_session, sample_role.id)
        assert role is not None
        assert role.id == sample_role.id

    def test_get_role_by_id_not_found(self, db_session):
        """测试获取不存在的角色"""
        role = RoleService.get_role_by_id(db