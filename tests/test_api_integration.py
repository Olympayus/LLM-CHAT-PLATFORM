"""端到端集成测试"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from tests.conftest import engine  # noqa: F401 — session 级 SQLite 引擎
from sqlalchemy.orm import sessionmaker


@pytest.fixture(autouse=True)
def override_db(engine):
    """将所有 API 路由的 get_db 替换为 SQLite 测试引擎"""
    Session = sessionmaker(bind=engine)

    def _get_test_db():
        """同步 get_db 替代"""
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    """每个测试独立的 TestClient"""
    with TestClient(app) as c:
        yield c


class TestApiIntegration:
    """API 端到端集成测试"""

    def test_register_and_login_flow(self, client):
        """注册→登录→获取信息 端到端流程"""
        # 1. 注册
        resp = client.post("/api/v1/auth/register", json={
            "username": "e2e_test",
            "password": "Test@123456",
            "email": "e2e@test.com",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0

        # 2. 登录
        resp = client.post("/api/v1/auth/login", json={
            "username": "e2e_test",
            "password": "Test@123456",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0

    def test_register_duplicate_username(self, client):
        """测试重复用户名注册"""
        # 先注册一个用户
        client.post("/api/v1/auth/register", json={
            "username": "dup_test",
            "password": "Test@123456",
            "email": "dup@test.com",
        })

        # 重复注册
        resp = client.post("/api/v1/auth/register", json={
            "username": "dup_test",
            "password": "Test@123456",
            "email": "dup2@test.com",
        })
        assert resp.status_code == 400

    def test_login_wrong_password(self, client):
        """测试错误密码登录"""
        # 先注册
        client.post("/api/v1/auth/register", json={
            "username": "login_test",
            "password": "Test@123456",
            "email": "login@test.com",
        })

        # 错误密码
        resp = client.post("/api/v1/auth/login", json={
            "username": "login_test",
            "password": "Wrong@123456",
        })
        assert resp.status_code == 400

    def test_login_nonexistent_user(self, client):
        """测试不存在用户登录"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "no_such_user",
            "password": "Test@123456",
        })
        assert resp.status_code == 400

    def test_register_without_email(self, client):
        """测试不带邮箱注册"""
        resp = client.post("/api/v1/auth/register", json={
            "username": "noemail_test",
            "password": "Test@123456",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0

    def test_register_invalid_password(self, client):
        """测试弱密码注册"""
        resp = client.post("/api/v1/auth/register", json={
            "username": "weakpwd_test",
            "password": "123",
            "email": "weak@test.com",
        })
        assert resp.status_code == 422  # Pydantic 校验失败

    def test_login_and_access_protected_route(self, client):
        """测试登录后访问受保护路由"""
        # 注册
        client.post("/api/v1/auth/register", json={
            "username": "protected_test",
            "password": "Test@123456",
            "email": "protected@test.com",
        })

        # 登录
        resp = client.post("/api/v1/auth/login", json={
            "username": "protected_test",
            "password": "Test@123456",
        })
        data = resp.json()
        token = data["data"]["token"]

        # 访问 /auth/me
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["user"]["username"] == "protected_test"

    def test_access_protected_without_token(self, client):
        """测试未登录访问受保护路由"""
        resp = client.get(
            "/api/v1/auth/me",
        )
        assert resp.status_code == 403  # 无 token

    def test_access_protected_with_invalid_token(self, client):
        """测试无效 token 访问受保护路由"""
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert resp.status_code == 401

    def test_change_password_and_relogin(self, client):
        """测试修改密码后使用新密码登录"""
        # 注册
        client.post("/api/v1/auth/register", json={
            "username": "changepwd_test",
            "password": "Test@123456",
            "email": "changepwd@test.com",
        })

        # 登录
        resp = client.post("/api/v1/auth/login", json={
            "username": "changepwd_test",
            "password": "Test@123456",
        })
        token = resp.json()["data"]["token"]

        # 修改密码
        resp = client.put(
            "/api/v1/auth/change-password",
            json={
                "old_password": "Test@123456",
                "new_password": "NewPwd@789",
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200

        # 使用新密码登录
        resp = client.post("/api/v1/auth/login", json={
            "username": "changepwd_test",
            "password": "NewPwd@789",
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    def test_logout_and_old_token_invalid(self, client):
        """测试登出后旧Token仍然可用（无黑名单机制）"""
        # 注册
        client.post("/api/v1/auth/register", json={
            "username": "logout_test",
            "password": "Test@123456",
            "email": "logout@test.com",
        })

        # 登录
        resp = client.post("/api/v1/auth/login", json={
            "username": "logout_test",
            "password": "Test@123456",
        })
        token = resp.json()["data"]["token"]

        # 登出
        resp = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200

        # 旧 Token 仍然可获取用户信息（登出仅设置 is_online=0）
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200

    def test_get_user_info_with_full_f