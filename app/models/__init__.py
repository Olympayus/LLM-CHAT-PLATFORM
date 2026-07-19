"""模型导入入口

包含:
- user.py:           SysUser, SysDept, SysRole, SysMenu, UserRoleRel, RoleMenuRel（成员A）
- model_config.py:   ModelConfig（成员B）
- skill.py:          Skill, SkillParam（成员B）
- digital_employee.py: DigitalEmployee, EmployeeSkillRel（成员B）
- im.py:             ImGroup, ImGroupMember, ImMessage, ImContact, ImSensitiveWord（成员C/D）
- nl2sql.py:         Nl2sqlQueryHistory, Nl2sqlFavorite（成员E）
- crawler.py:        CrawlerTask, CrawlerExecutionLog, DataCleanRule（成员F）
- audit_log.py:      SysAuditLog（成员D）
"""

# 认证与用户组织（成员A）
from app.models.user import SysUser, SysDept, SysRole, SysMenu, UserRoleRel, RoleMenuRel

# 模型管理（成员B）
from app.models.model_config import ModelConfig

# 技能管理（成员B）
from app.models.skill import Skill, SkillParam

# 数字员工管理（成员B）
from app.models.digital_employee import DigitalEmployee, EmployeeSkillRel

# IM 模型（成员C + 成员D）
from app.models.im import ImGroup, ImGroupMember, ImMessage, ImContact, ImSensitiveWord

# 审计日志模型（成员D）
from app.models.audit_log import SysAuditLog

# NL2SQL 模型（成员E）
from app.models.nl2sql import Nl2sqlQueryHistory, Nl2sqlFavorite

# 爬虫模型（成员F）
from app.models.crawler import CrawlerTask, CrawlerExecutionLog, DataCleanRule

__all__ = [
    # 认证与用户组织（成员A）
    "SysUser",
    "SysDept",
    "SysRole",
    "SysMenu",
    "UserRoleRel",
    "RoleMenuRel",
    # 模型管理
    "ModelConfig",
    # 技能管理
    "Skill",
    "SkillParam",
    # 数字员工管理
    "DigitalEmployee",
    "EmployeeSkillRel",
    # IM
    "ImGroup",
    "ImGroupMember",
    "ImMessage",
    "ImContact",
    "ImSensitiveWord",
    # 审计
    "SysAuditLog",
    # NL2SQL
    "Nl2sqlQueryHistory",
    "Nl2sqlFavorite",
    # 爬虫
    "CrawlerTask",
    "CrawlerExecutionLog",
    "DataCleanRule",
]
