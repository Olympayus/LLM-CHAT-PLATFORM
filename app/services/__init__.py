"""业务逻辑层 Services

包含:
- auth_service.py: 认证 + 用户/部门/角色/菜单服务（由 成员A 实现）
- nl2sql_service.py: NL2SQL 智能问数服务（由 成员E 实现）
- elasticsearch_service.py: ES 消息检索服务（由 成员D 实现）
- compliance_service.py: 合规审计服务（由 成员D 实现）
"""

# 认证与用户组织服务（成员A 负责）
from app.services.auth_service import AuthService, UserService, DeptService, RoleService, MenuService
from app.services.audit_service import AuditService

# NL2SQL 服务（成员E 负责）
from app.services.nl2sql_service import Nl2sqlService, nl2sql_service

# ES 消息检索服务（成员D 负责）
from app.services.elasticsearch_service import ElasticsearchService, es_service

# 合规审计服务（成员D 负责）
from app.services.compliance_service import ComplianceService, compliance_service

__all__ = [
    # 认证与用户组织（成员A）
    "AuthService",
    "UserService",
    "DeptService",
    "RoleService",
    "MenuService",
    "AuditService",
    # NL2SQL
    "Nl2sqlService",
    "nl2sql_service",
    # ES
    "ElasticsearchService",
    "es_service",
    # 合规
    "ComplianceService",
    "compliance_service",
]
