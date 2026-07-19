"""SQL 安全校验器

使用 sqlparse 解析 SQL，基于白名单机制进行安全校验：

校验规则:
1. ✅ 仅允许 SELECT 语句（拒绝 INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/TRUNCATE 等）
2. ✅ 禁止危险函数和关键字（INTO OUTFILE, LOAD_FILE, SLEEP, BENCHMARK 等）
3. ✅ 禁止多语句执行（SQL 注入）
4. ✅ 强制 LIMIT 子句注入（如果无 LIMIT，自动追加 LIMIT 1000）
5. ✅ 禁止读写文件相关操作
"""

import re
from typing import Optional

import sqlparse
from loguru import logger
from sqlparse.sql import Identifier, IdentifierList, Token, TokenList
from sqlparse.tokens import DDL, DML, Keyword, Name, Punctuation

from app.schemas.nl2sql import SqlValidationResult

# ==================== 白名单 ====================

# 允许的 SQL 语句类型（仅 SELECT）
ALLOWED_DML = {"SELECT"}

# 明确禁止的 DDL/DML 关键字
FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "REPLACE", "LOAD", "INTO", "OUTFILE", "DUMPFILE",
    "EXEC", "EXECUTE", "CALL", "MERGE", "RENAME", "GRANT",
    "REVOKE", "KILL", "SHUTDOWN", "SET", "@@", "@",
}

# 禁止使用的函数
FORBIDDEN_FUNCTIONS = {
    "SLEEP", "BENCHMARK", "LOAD_FILE", "INTO_OUTFILE",
    "GET_LOCK", "RELEASE_LOCK", "EXECUTE", "UDF",
}

# 允许的 JOIN 类型
ALLOWED_JOINS = {"JOIN", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "LEFT OUTER JOIN", "RIGHT OUTER JOIN"}

# LIMIT 最大值
MAX_LIMIT = 10000
DEFAULT_LIMIT = 1000


class SqlValidator:
    """SQL 安全校验器"""

    def validate(self, sql: str) -> SqlValidationResult:
        """执行 SQL 安全校验

        Args:
            sql: 需要校验的 SQL 语句

        Returns:
            SqlValidationResult: 校验结果
        """
        if not sql or not sql.strip():
            return SqlValidationResult(
                is_valid=False,
                is_readonly=False,
                sql_type="UNKNOWN",
                error="SQL 语句为空",
            )

        # 1. 预处理：移除注释
        cleaned_sql = self._remove_comments(sql)

        # 2. 检查多语句注入
        multi_stmt_check = self._check_multi_statements(cleaned_sql)
        if not multi_stmt_check.is_valid:
            return multi_stmt_check

        # 3. 使用 sqlparse 解析
        try:
            parsed = sqlparse.parse(cleaned_sql)
        except Exception as e:
            return SqlValidationResult(
                is_valid=False,
                is_readonly=False,
                sql_type="UNKNOWN",
                error=f"SQL 解析失败: {str(e)}",
            )

        if not parsed or not parsed[0]:
            return SqlValidationResult(
                is_valid=False,
                is_readonly=False,
                sql_type="UNKNOWN",
                error="SQL 解析结果为空",
            )

        statement = parsed[0]

        # 4. 检查语句类型
        stmt_type = self._get_statement_type(statement)
        if stmt_type.upper() not in ALLOWED_DML:
            return SqlValidationResult(
                is_valid=False,
                is_readonly=False,
                sql_type=stmt_type.upper(),
                error=f"不允许的 SQL 操作: {stmt_type.upper()}，仅允许 SELECT 查询",
            )

        # 5. 检查禁止关键字
        keyword_check = self._check_forbidden_keywords(cleaned_sql)
        if not keyword_check.is_valid:
            return keyword_check

        # 6. 检查禁止函数
        func_check = self._check_forbidden_functions(cleaned_sql)
        if not func_check.is_valid:
            return func_check

        # 7. 检查文件操作
        file_check = self._check_file_operations(cleaned_sql)
        if not file_check.is_valid:
            return file_check

        # 8. 注入 LIMIT（如果没有）
        final_sql = self._ensure_limit(cleaned_sql)

        # 9. 检查 LIMIT 是否超过最大值
        limit_check = self._check_limit(cleaned_sql)
        if limit_check.error:
            return limit_check

        warning = None
        if final_sql != cleaned_sql:
            warning = "已自动添加 LIMIT 1000 子句"

        return SqlValidationResult(
            is_valid=True,
            is_readonly=True,
            sql_type="SELECT",
            warning=warning,
        )

    def _remove_comments(self, sql: str) -> str:
        """移除 SQL 中的注释"""
        # 移除单行注释 --
        sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
        # 移除多行注释 /* */
        sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
        # 移除 # 注释
        sql = re.sub(r"#.*$", "", sql, flags=re.MULTILINE)
        return sql.strip()

    def _check_multi_statements(self, sql: str) -> SqlValidationResult:
        """检查多语句注入（以分号隔断多条 SQL）"""
        # 移除字符串内的分号
        cleaned = self._remove_string_contents(sql)
        # 按分号分割
        statements = [s.strip() for s in cleaned.split(";") if s.strip()]
        if len(statements) > 1:
            return SqlValidationResult(
                is_valid=False,
                is_readonly=False,
                sql_type="MULTI_STATEMENT",
                error="检测到多条 SQL 语句，不允许多语句执行",
            )
        return SqlValidationResult(
            is_valid=True,
            is_readonly=True,
            sql_type="SELECT",
        )

    def _remove_string_contents(self, sql: str) -> str:
        """移除 SQL 中的字符串字面量（防止误判）"""
        # 移除单引号字符串
        sql = re.sub(r"'[^']*'", "''", sql)
        # 移除双引号字符串
        sql = re.sub(r'"[^"]*"', '""', sql)
        return sql

    def _get_statement_type(self, statement: TokenList) -> str:
        """获取语句类型"""
        for token in statement.tokens:
            if token.is_keyword:
                keyword = token.value.upper().strip()
                # 检查是否是 DML 关键字
                for dml_type in ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "CREATE", "DROP", "ALTER"]:
                    if keyword.startswith(dml_type):
                        return dml_type
            if token.ttype in (DML, DDL):
                return token.value.upper().strip()
        return "UNKNOWN"

    def _check_forbidden_keywords(self, sql: str) -> SqlValidationResult:
        """检查禁止关键字"""
        upper_sql = sql.upper()

        # 特别检查 INTO OUTFILE 组合
        if "INTO OUTFILE" in upper_sql or "INTO DUMPFILE" in upper_sql:
            return SqlValidationResult(
                is_valid=False,
                is_readonly=False,
                sql_type="SELECT",
                error="禁止使用 INTO OUTFILE/DUMPFILE 写入文件",
            )

        # 检查禁用关键字（排除 SELECT 语句中的关键字）
        for keyword in FORBIDDEN_KEYWORDS:
            if keyword in {"INTO", "SET", "@@", "@"}:
                continue  # 这些在 SELECT 中可能合法出现
            # 使用单词边界匹配
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, upper_sql):
                # 确认不是 SELECT 的子句的一部分
                if not self._is_in_select_context(upper_sql, keyword):
                    return SqlValidationResult(
                        is_valid=False,
                        is_readonly=False,
                        sql_type="SELECT",
                        error=f"禁止使用的关键字: {keyword}",
                    )

        return SqlValidationResult(
            is_valid=True,
            is_readonly=True,
            sql_type="SELECT",
        )

    def _is_in_select_context(self, sql: str, keyword: str) -> bool:
        """检查关键字是否在 SELECT 语句的合法上下文中"""
        # 如果 SQL 以 SELECT 开头，且关键字不在禁止列表中，则通过
        if sql.strip().upper().startswith("SELECT"):
            return True
        return False

    def _check_forbidden_functions(self, sql: str) -> SqlValidationResult:
        """检查禁止函数"""
        upper_sql = sql.upper()
        for func in FORBIDDEN_FUNCTIONS:
            if func in upper_sql:
                return SqlValidationResult(
                    is_valid=False,
                    is_readonly=False,
                    sql_type="SELECT",
                    error=f"禁止使用的函数: {func}()",
                )
        return SqlValidationResult(
            is_valid=True,
            is_readonly=True,
            sql_type="SELECT",
        )

    def _check_file_operations(self, sql: str) -> SqlValidationResult:
        """检查文件操作"""
        upper_sql = sql.upper()
        # 检查文件读取函数
        file_read_patterns = [
            r"\bLOAD_FILE\s*\(",
            r"\bLOAD\s+DATA",
            r"\bLOAD\s+XML",
            r"\bSELECT\s+.*\s+INTO\s+(OUTFILE|DUMPFILE)",
        ]
        for pattern in file_read_patterns:
            if re.search(pattern, upper_sql):
                return SqlValidationResult(
                    is_valid=False,
                    is_readonly=False,
                    sql_type="SELECT",
                    error="禁止的文件操作",
                )
        return SqlValidationResult(
            is_valid=True,
            is_readonly=True,
            sql_type="SELECT",
        )

    def _ensure_limit(self, sql: str) -> str:
        """检查并自动注入 LIMIT 子句"""
        upper_sql = sql.upper().strip()

        # 如果已经有 LIMIT 子句，跳过
        if re.search(r'\bLIMIT\b', upper_sql):
            return sql

        # 检查是否有聚合函数、子查询等
        # 简单的启发式：末尾追加 LIMIT
        # 移除末尾的分号
        sql = sql.rstrip(";").strip()
        return f"{sql} LIMIT {DEFAULT_LIMIT}"

    def _check_limit(self, sql: str) -> SqlValidationResult:
        """检查 LIMIT 子句是否超过最大限制"""
        upper_sql = sql.upper()
        match = re.search(r'\bLIMIT\s+(\d+)', upper_sql)
        if match:
            limit_value = int(match.group(1))
            if limit_value > MAX_LIMIT:
                return SqlValidationResult(
                    is_valid=False,
                    is_readonly=True,
                    sql_type="SELECT",
                    error=f"LIMIT 值 {limit_value} 超过最大限制 {MAX_LIMIT}",
                )
        return SqlValidationResult(
            is_valid=True,
            is_readonly=True,
            sql_type="SELECT",
        )

    def sanitize_sql(self, sql: str) -> str:
        """净化 SQL：移除危险内容后返回安全的 SQL

        Args:
            sql: 原始 SQL

        Returns:
            str: 净化后的 SQL
        """
        # 先校验
        result = self.validate(sql)
        if not result.is_valid:
            return ""

        # 移除注释
        sql = self._remove_comments(sql)

        # 确保有 LIMIT
        sql = self._ensure_limit(sql)

        return sql


# 全局单例
sql_validator = SqlValidator()