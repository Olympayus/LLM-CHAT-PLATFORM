"""菜单管理服务测试"""

import pytest
from app.services.auth_service import MenuService, BusinessError, NotFoundError
from app.schemas.auth import MenuCreate, MenuUpdate


class TestMenuService:
    """菜单管理服务测试"""

    def test_create_menu(self, db_session):
        """测试创建菜单"""
        data = MenuCreate(
            parent_id=0,
            name="新菜单",
            permission="new:menu",
            path="/new",
            menu_type="menu",
            sort_order=1,
        )
        menu = MenuService.create_menu(db_session, data)
        assert menu.name == "新菜单"
        assert menu.permission == "new:menu"

    def test_update_menu(self, db_session, sample_menu):
        """测试更新菜单"""
        data = MenuUpdate(name="更新后的菜单")
        menu = MenuService.update_menu(db_session, sample_menu.id, data)
        assert menu.name == "更新后的菜单"

    def test_update_menu_not_found(self, db_session):
        """测试更新不存在的菜单"""
        data = MenuUpdate(name="不存在的菜单")
        with pytest.raises(NotFoundError, match="菜单不存在"):
            MenuService.update_menu(db_session, 99999, data)

    def test_delete_menu(self, db_session, sample_menu):
        """测试删除菜单"""
        MenuService.delete_menu(db_session, sample_menu.id)
        assert sample_menu.is_deleted == 1

    def test_delete_menu_not_found(self, db_session):
        """测试删除不存在的菜单"""
        with pytest.raises(NotFoundError, match="菜单不存在"):
            MenuService.delete_menu(db_session, 99999)

    def test_delete_menu_with_children(self, db_session, sample_menu):
        """测试删除有子菜单的菜单"""
        child_data = MenuCreate(
            parent_id=sample_menu.id,
            name="子菜单",
            permission="child:menu",
            menu_type="button",
            sort_order=1,
        )
        MenuService.create_menu(db_session, child_data)

        with pytest.raises(BusinessError, match="请先删除子菜单"):
            MenuService.delete_menu(db_session, sample_menu.id)

    def test_get_menu_tree(self, db_session, sample_menu):
        """测试获取菜单树"""
        menus = MenuService.get_menu_tree(db_session)
        assert len(menus) >= 1
        assert any(m.id == sample_menu.id for m in menus)

    def test_get_menu_by_id(self, db_session, sample_menu):
        """测试获取菜单详情"""
        menu = MenuService.get_menu_by_id(db_session, sample_menu.id)
        assert menu is not None
        assert menu.id == sample_menu.id

    def test_get_menu_by_id_not_found(self, db_session):
        """测试获取不存在的菜单"""
        menu = MenuService.get_menu_by_id(db_session, 99999)
        assert menu is None

    def test_get_user_menus(self, db_session, sample_user, sample_role, sample_menu):
        """测试获取用户可见菜单"""
        from app.models.user import UserRoleRel, RoleMenuRel
        from app.schemas.auth import UserRoleAssign
        from app.services.auth_service import UserService

        # 分配角色
        data = UserRoleAssign(role_ids=[sample_role.id])
        UserService.assign_roles(db_session, sample_user.id, data)

        # 分配菜单到角色
        rel = RoleMenuRel(role_id=sample_role.id, menu_id=sample_menu.id)
        db_session.add(rel)
        db_session.commit()

        menus = MenuService.get_user_men