"""部门管理服务测试"""

import pytest
from app.services.auth_service import DeptService, BusinessError, NotFoundError
from app.schemas.auth import DeptCreate, DeptUpdate


class TestDeptService:
    """部门管理服务测试"""

    def test_create_dept(self, db_session):
        """测试创建部门"""
        data = DeptCreate(name="新部门", parent_id=0, sort_order=1)
        dept = DeptService.create_dept(db_session, data)
        assert dept.name == "新部门"
        assert dept.parent_id == 0

    def test_update_dept(self, db_session, sample_dept):
        """测试更新部门"""
        data = DeptUpdate(name="更新后的部门")
        dept = DeptService.update_dept(db_session, sample_dept.id, data)
        assert dept.name == "更新后的部门"

    def test_update_dept_not_found(self, db_session):
        """测试更新不存在的部门"""
        data = DeptUpdate(name="不存在的部门")
        with pytest.raises(NotFoundError, match="部门不存在"):
            DeptService.update_dept(db_session, 99999, data)

    def test_delete_dept(self, db_session, sample_dept):
        """测试删除部门"""
        DeptService.delete_dept(db_session, sample_dept.id)
        assert sample_dept.is_deleted == 1

    def test_delete_dept_not_found(self, db_session):
        """测试删除不存在的部门"""
        with pytest.raises(NotFoundError, match="部门不存在"):
            DeptService.delete_dept(db_session, 99999)

    def test_delete_dept_with_children(self, db_session, sample_dept):
        """测试删除有子部门的部门"""
        child_data = DeptCreate(name="子部门", parent_id=sample_dept.id)
        DeptService.create_dept(db_session, child_data)

        with pytest.raises(BusinessError, match="请先删除子部门"):
            DeptService.delete_dept(db_session, sample_dept.id)

    def test_delete_dept_with_users(self, db_session, sample_dept, sample_user):
        """测试删除有用户的部门"""
        sample_user.dept_id = sample_dept.id
        db_session.commit()

        with pytest.raises(BusinessError, match="部门下存在用户"):
            DeptService.delete_dept(db_session, sample_dept.id)

    def test_get_dept_tree(self, db_session, sample_dept):
        """测试获取部门树"""
        depts = DeptService.get_dept_tree(db_session)
        assert len(depts) >= 1
        assert any(d.id == sample_dept.id for d in depts)

    def test_get_dept_by_id(self, db_session, sample_dept):
        """测试获取部门详情"""
        dept = DeptService.get_dept_by_id(db_session, sample_dept.id)
        assert dept is not None
        assert dept.id == sample_dept.id

    def test_get_dept_by_id_not_found(self, db_session):
        """测试获取不存在的部门"""
        dept = DeptService.get_dept_by_id(db_sessi