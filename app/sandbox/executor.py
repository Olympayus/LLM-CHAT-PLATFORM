"""沙箱执行器

提供安全隔离的代码执行环境:

功能:
1. SQL 只读执行 — 使用独立数据库连接、只读事务、超时控制、自动回滚
2. Python Function Call 执行 — 使用 RestrictedPython 隔离执行

注意:
- 在没有数据库连接时，使用 Mock 执行器返回模拟数据
- Docker 沙箱需要在有 Docker 环境的机器上使用
"""

import asyncio
import time
from typing import Any, Optional

from loguru import logger

from app.config import settings

# ==================== 配置 ====================

SQL_TIMEOUT_SECONDS = 30  # SQL 执行超时（秒）
PYTHON_TIMEOUT_SECONDS = 10  # Python 代码执行超时（秒）
MAX_RESULT_ROWS = 10000  # 最大返回行数


class SqlSandboxExecutor:
    """SQL 沙箱执行器

    在只读事务中安全执行 SQL 查询。
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or settings.DATABASE_URL

    async def execute(
        self,
        sql: str,
        params: Optional[dict[str, Any]] = None,
        timeout: int = SQL_TIMEOUT_SECONDS,
        max_rows: int = MAX_RESULT_ROWS,
    ) -> dict:
        """在只读事务中执行 SQL

        注意：此方法需要数据库连接。
        在无数据库环境下调用会返回模拟数据。

        Args:
            sql: 要执行的 SQL 语句（必须是 SELECT）
            params: 查询参数
            timeout: 超时秒数
            max_rows: 最大返回行数

        Returns:
            dict: {
                "columns": ["col1", "col2", ...],
                "rows": [["val1", "val2"], ...],
                "row_count": 100,
                "execution_time_ms": 12,
            }
        """
        # 在无数据库时返回 Mock 数据
        if not self.db_url or "localhost" in self.db_url:
            logger.warning("使用 Mock SQL 执行器（无数据库连接）")
            return self._mock_execute(sql)

        start_time = time.time()

        try:
            # 使用 aiomysql 直接连接，确保完全隔离
            import aiomysql

            conn = await asyncio.wait_for(
                aiomysql.connect(
                    host=self._get_host(),
                    port=self._get_port(),
                    user=self._get_user(),
                    password=self._get_password(),
                    db=self._get_database(),
                    autocommit=False,
                    cursorclass=aiomysql.DictCursor,
                ),
                timeout=10,
            )

            try:
                async with conn.cursor() as cursor:
                    # 设置为只读事务
                    await cursor.execute("SET SESSION TRANSACTION READ ONLY")
                    await conn.begin()

                    # 执行查询
                    await asyncio.wait_for(
                        cursor.execute(sql, params or {}),
                        timeout=timeout,
                    )

                    # 获取结果
                    rows = await cursor.fetchmany(size=max_rows)
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []

                    # 转换为列表格式
                    result_rows = []
                    for row in rows:
                        result_rows.append([row.get(col) for col in columns])

                    await conn.rollback()  # 确保回滚

            finally:
                conn.close()

            execution_time_ms = int((time.time() - start_time) * 1000)

            return {
                "columns": columns,
                "rows": result_rows,
                "row_count": len(result_rows),
                "execution_time_ms": execution_time_ms,
            }

        except asyncio.TimeoutError:
            logger.error(f"SQL 执行超时（{timeout}秒）: {sql[:200]}")
            return {
                "columns": [],
                "rows": [],
                "row_count": 0,
                "execution_time_ms": timeout * 1000,
                "error": f"SQL 执行超时（超过 {timeout} 秒）",
            }
        except ImportError:
            logger.warning("aiomysql 未安装，使用 Mock 执行器")
            return self._mock_execute(sql)
        except Exception as e:
            logger.error(f"SQL 执行失败: {e}")
            return {
                "columns": [],
                "rows": [],
                "row_count": 0,
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "error": str(e),
            }

    def _get_host(self) -> str:
        """从 DATABASE_URL 解析 host"""
        url = self.db_url
        try:
            # mysql+aiomysql://user:password@host:port/db
            import re
            match = re.search(r"@([^:]+)", url)
            return match.group(1) if match else "localhost"
        except Exception:
            return "localhost"

    def _get_port(self) -> int:
        """从 DATABASE_URL 解析 port"""
        url = self.db_url
        try:
            import re
            match = re.search(r":(\d+)/", url)
            return int(match.group(1)) if match else 3306
        except Exception:
            return 3306

    def _get_user(self) -> str:
        """从 DATABASE_URL 解析 user"""
        url = self.db_url
        try:
            import re
            match = re.search(r"://([^:]+):", url)
            return match.group(1) if match else "root"
        except Exception:
            return "root"

    def _get_password(self) -> str:
        """从 DATABASE_URL 解析 password"""
        url = self.db_url
        try:
            import re
            match = re.search(r":([^@]+)@", url)
            return match.group(1) if match else ""
        except Exception:
            return ""

    def _get_database(self) -> str:
        """从 DATABASE_URL 解析 database"""
        url = self.db_url
        try:
            import re
            match = re.search(r"/([^/?]+)(?:\?|$)", url)
            return match.group(1) if match else "llm_platform"
        except Exception:
            return "llm_platform"

    def _mock_execute(self, sql: str) -> dict:
        """Mock SQL 执行（无数据库时使用）"""
        upper_sql = sql.upper().strip()

        # 根据 SQL 内容返回不同的模拟数据
        if "COUNT" in upper_sql:
            if "USER" in upper_sql or "sys_user" in sql:
                return {
                    "columns": ["total"],
                    "rows": [[42]],
                    "row_count": 1,
                    "execution_time_ms": 3,
                }
            elif "DEPT" in upper_sql or "sys_dept" in sql:
                return {
                    "columns": ["total"],
                    "rows": [[5]],
                    "row_count": 1,
                    "execution_time_ms": 2,
                }
            elif "MESSAGE" in upper_sql or "im_message" in sql:
                return {
                    "columns": ["total"],
                    "rows": [[1024]],
                    "row_count": 1,
                    "execution_time_ms": 5,
                }
            elif "SKILL" in upper_sql:
                return {
                    "columns": ["total"],
                    "rows": [[12]],
                    "row_count": 1,
                    "execution_time_ms": 2,
                }
            else:
                return {
                    "columns": ["total"],
                    "rows": [[100]],
                    "row_count": 1,
                    "execution_time_ms": 3,
                }

        if "GROUP BY" in upper_sql:
            if "DEPT" in upper_sql or "dept" in sql:
                return {
                    "columns": ["部门名称", "人数"],
                    "rows": [
                        ["技术部", 15],
                        ["市场部", 10],
                        ["财务部", 8],
                        ["人事部", 5],
                        ["运营部", 4],
                    ],
                    "row_count": 5,
                    "execution_time_ms": 4,
                }
            elif "STATUS" in upper_sql or "status" in sql:
                return {
                    "columns": ["status", "count"],
                    "rows": [[1, 35], [0, 5], [2, 2]],
                    "row_count": 3,
                    "execution_time_ms": 3,
                }
            else:
                return {
                    "columns": ["category", "count"],
                    "rows": [["A", 20], ["B", 15], ["C", 7]],
                    "row_count": 3,
                    "execution_time_ms": 3,
                }

        if "ORDER BY" in upper_sql or "LIMIT" in upper_sql:
            if "USER" in upper_sql or "sys_user" in sql:
                return {
                    "columns": ["id", "username", "email", "real_name", "created_at"],
                    "rows": [
                        [1, "admin", "admin@example.com", "管理员", "2024-01-01 00:00:00"],
                        [2, "zhangsan", "zhangsan@example.com", "张三", "2024-01-02 00:00:00"],
                        [3, "lisi", "lisi@example.com", "李四", "2024-01-03 00:00:00"],
                        [4, "wangwu", "wangwu@example.com", "王五", "2024-01-04 00:00:00"],
                        [5, "zhaoliu", "zhaoliu@example.com", "赵六", "2024-01-05 00:00:00"],
                    ],
                    "row_count": 5,
                    "execution_time_ms": 3,
                }
            elif "GROUP" in upper_sql or "im_group" in sql:
                return {
                    "columns": ["id", "group_name", "member_count", "created_at"],
                    "rows": [
                        [1, "技术交流群", 50, "2024-01-01 00:00:00"],
                        [2, "产品讨论组", 30, "2024-01-02 00:00:00"],
                        [3, "全员群", 200, "2024-01-03 00:00:00"],
                    ],
                    "row_count": 3,
                    "execution_time_ms": 2,
                }
            else:
                return {
                    "columns": ["id", "name", "description", "created_at"],
                    "rows": [
                        [1, "示例项1", "这是一个示例", "2024-01-01"],
                        [2, "示例项2", "这是另一个示例", "2024-01-02"],
                    ],
                    "row_count": 2,
                    "execution_time_ms": 2,
                }

        # 通用 SELECT
        if "SELECT" in upper_sql:
            return {
                "columns": ["id", "name", "value"],
                "rows": [
                    [1, "示例A", 100],
                    [2, "示例B", 200],
                    [3, "示例C", 300],
                ],
                "row_count": 3,
                "execution_time_ms": 2,
            }

        return {
            "columns": ["result"],
            "rows": [["OK"]],
            "row_count": 1,
            "execution_time_ms": 1,
        }


class PythonSandboxExecutor:
    """Python 沙箱执行器

    使用 RestrictedPython 安全执行 Python 代码（Function Call）。
    注意: RestrictedPython 需要在环境中安装。
    """

    def __init__(self, timeout: int = PYTHON_TIMEOUT_SECONDS):
        self.timeout = timeout

    async def execute(
        self,
        code: str,
        input_data: Optional[dict] = None,
    ) -> dict:
        """安全执行 Python 代码

        Args:
            code: Python 代码字符串
            input_data: 输入数据（作为全局变量传入）

        Returns:
            dict: {"result": ..., "error": ...}
        """
        try:
            # 尝试导入 RestrictedPython（v8.x 包名大写）
            try:
                from RestrictedPython import compile_restricted
                has_restricted = True
            except ImportError:
                try:
                    from restrictedpython import compile_restricted
                    has_restricted = True
                except ImportError:
                    logger.warning("RestrictedPython 未安装，使用基本安全模式")
                    has_restricted = False

            safe_builtins = self._get_safe_builtins()
            # RestrictedPython guards 必须在顶层 globals 中，不能嵌套在 __builtins__ 里
            safe_globals = {
                "__builtins__": safe_builtins,
                "_getitem_": safe_builtins["_getitem_"],
                "_getiter_": safe_builtins["_getiter_"],
                "_getattr_": safe_builtins["_getattr_"],
            }

            if input_data:
                safe_globals["input_data"] = input_data

            # 编译代码
            if has_restricted:
                compiled_code = compile_restricted(code, "<sandbox>", "exec")
            else:
                compiled_code = compile(code, "<sandbox>", "exec")

            # 创建受限执行命名空间
            local_namespace = {}

            # 在单独线程中执行，支持超时
            loop = asyncio.get_event_loop()

            def run_code():
                exec(compiled_code, safe_globals, local_namespace)
                return local_namespace

            result = await asyncio.wait_for(
                loop.run_in_executor(None, run_code),
                timeout=self.timeout,
            )

            # 提取 result 变量
            output = result.get("result", result.get("output", None))

            return {
                "result": output,
                "error": None,
            }

        except asyncio.TimeoutError:
            logger.error(f"Python 代码执行超时（{self.timeout}秒）")
            return {
                "result": None,
                "error": f"代码执行超时（超过 {self.timeout} 秒）",
            }
        except Exception as e:
            logger.error(f"Python 代码执行失败: {e}")
            return {
                "result": None,
                "error": str(e),
            }

    def _get_safe_builtins(self) -> dict:
        """获取安全的 builtins"""
        safe_list = {
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "enumerate": enumerate,
            "filter": filter,
            "float": float,
            "int": int,
            "isinstance": isinstance,
            "len": len,
            "list": list,
            "map": map,
            "max": max,
            "min": min,
            "print": lambda *args: None,  # 禁止输出
            "range": range,
            "round": round,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "type": type,
            "zip": zip,
            "True": True,
            "False": False,
            "None": None,
            # RestrictedPython 需要的 guards（v8.x）
            "_getitem_": lambda ob, key: ob[key],
            "_getiter_": lambda ob: iter(ob),
            "_getattr_": lambda ob, name: getattr(ob, name),
            "_inplace_add_": lambda ob, val: ob + val,
            "_inplace_sub_": lambda ob, val: ob - val,
            "_inplace_mul_": lambda ob, val: ob * val,
        }
        return safe_list


# 全局单例
sql_executor = SqlSandboxExecutor()
python_executor = PythonSandboxExecutor()