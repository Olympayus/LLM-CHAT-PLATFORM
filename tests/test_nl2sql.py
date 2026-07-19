"""NL2SQL 模块测试

测试覆盖:
1. SQL 安全校验器（核心）
2. 沙箱执行器 Mock
3. NL2SQL Prompt 工程
4. 图表推荐逻辑
5. API 端点
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.nl2sql import Nl2sqlEngine, nl2sql_engine
from app.sandbox.sql_validator import SqlValidator, sql_validator
from app.sandbox.executor import SqlSandboxExecutor, PythonSandboxExecutor
from app.sandbox.sql_validator import MAX_LIMIT
from app.schemas.nl2sql import (
    ChartRecommendation,
    Nl2sqlAskRequest,
    Nl2sqlAskResponse,
    SqlValidationResult,
    TableSchema,
    ColumnInfo,
)


# ==================== 测试数据 ====================

@pytest.fixture
def mock_tables():
    """Mock 表结构"""
    return [
        TableSchema(
            table_name="sys_user",
            table_comment="用户表",
            columns=[
                ColumnInfo(name="id", type="bigint", nullable=False, comment="ID", is_primary_key=True),
                ColumnInfo(name="username", type="varchar(64)", nullable=False, comment="用户名"),
                ColumnInfo(name="email", type="varchar(128)", nullable=True, comment="邮箱"),
            ],
        ),
        TableSchema(
            table_name="sys_dept",
            table_comment="部门表",
            columns=[
                ColumnInfo(name="id", type="bigint", nullable=False, comment="ID", is_primary_key=True),
                ColumnInfo(name="name", type="varchar(64)", nullable=False, comment="部门名称"),
            ],
        ),
    ]


# ==================== SQL 安全校验器测试 ====================

class TestSqlValidator:
    """SQL 安全校验器测试"""

    def setup_method(self):
        self.validator = SqlValidator()

    def test_valid_select(self):
        """测试合法的 SELECT 语句"""
        sql = "SELECT * FROM sys_user WHERE id = 1"
        result = self.validator.validate(sql)
        assert result.is_valid is True
        assert result.is_readonly is True
        assert result.sql_type == "SELECT"

    def test_valid_select_with_limit(self):
        """测试带 LIMIT 的 SELECT"""
        sql = "SELECT username, email FROM sys_user LIMIT 10"
        result = self.validator.validate(sql)
        assert result.is_valid is True

    def test_valid_select_with_join(self):
        """测试 JOIN 查询"""
        sql = "SELECT u.username, d.name FROM sys_user u JOIN sys_dept d ON u.dept_id = d.id"
        result = self.validator.validate(sql)
        assert result.is_valid is True

    def test_valid_select_with_group_by(self):
        """测试 GROUP BY 查询"""
        sql = "SELECT dept_id, COUNT(*) as cnt FROM sys_user GROUP BY dept_id"
        result = self.validator.validate(sql)
        assert result.is_valid is True

    def test_invalid_insert(self):
        """测试 INSERT 被拒绝"""
        sql = "INSERT INTO sys_user (username) VALUES ('test')"
        result = self.validator.validate(sql)
        assert result.is_valid is False
        assert "不允许" in (result.error or "")

    def test_invalid_update(self):
        """测试 UPDATE 被拒绝"""
        sql = "UPDATE sys_user SET username = 'test' WHERE id = 1"
        result = self.validator.validate(sql)
        assert result.is_valid is False

    def test_invalid_delete(self):
        """测试 DELETE 被拒绝"""
        sql = "DELETE FROM sys_user WHERE id = 1"
        result = self.validator.validate(sql)
        assert result.is_valid is False

    def test_invalid_drop(self):
        """测试 DROP 被拒绝"""
        sql = "DROP TABLE sys_user"
        result = self.validator.validate(sql)
        assert result.is_valid is False

    def test_invalid_alter(self):
        """测试 ALTER 被拒绝"""
        sql = "ALTER TABLE sys_user ADD COLUMN test VARCHAR(64)"
        result = self.validator.validate(sql)
        assert result.is_valid is False

    def test_invalid_truncate(self):
        """测试 TRUNCATE 被拒绝"""
        sql = "TRUNCATE TABLE sys_user"
        result = self.validator.validate(sql)
        assert result.is_valid is False

    def test_invalid_create(self):
        """测试 CREATE 被拒绝"""
        sql = "CREATE TABLE test (id INT)"
        result = self.validator.validate(sql)
        assert result.is_valid is False

    def test_multi_statement_injection(self):
        """测试多语句注入被拒绝"""
        sql = "SELECT * FROM sys_user; DROP TABLE sys_user"
        result = self.validator.validate(sql)
        assert result.is_valid is False
        assert "多条" in (result.error or "")

    def test_forbidden_function_sleep(self):
        """测试 SLEEP 函数被拒绝"""
        sql = "SELECT * FROM sys_user WHERE SLEEP(5)"
        result = self.validator.validate(sql)
        assert result.is_valid is False
        assert "SLEEP" in (result.error or "")

    def test_forbidden_function_benchmark(self):
        """测试 BENCHMARK 函数被拒绝"""
        sql = "SELECT BENCHMARK(1000000, MD5(1))"
        result = self.validator.validate(sql)
        assert result.is_valid is False

    def test_forbidden_into_outfile(self):
        """测试 INTO OUTFILE 被拒绝"""
        sql = "SELECT * INTO OUTFILE '/tmp/out' FROM sys_user"
        result = self.validator.validate(sql)
        assert result.is_valid is False

    def test_forbidden_load_file(self):
        """测试 LOAD_FILE 被拒绝"""
        sql = "SELECT LOAD_FILE('/etc/passwd')"
        result = self.validator.validate(sql)
        assert result.is_valid is False

    def test_empty_sql(self):
        """测试空 SQL"""
        result = self.validator.validate("")
        assert result.is_valid is False

    def test_limit_injection(self):
        """测试自动注入 LIMIT"""
        sql = "SELECT * FROM sys_user"
        sanitized = self.validator.sanitize_sql(sql)
        assert "LIMIT" in sanitized.upper()

    def test_limit_max_check(self):
        """测试 LIMIT 超过最大值"""
        sql = f"SELECT * FROM sys_user LIMIT {MAX_LIMIT + 1}"
        result = self.validator.validate(sql)
        assert result.is_valid is False

    def test_sql_with_comment(self):
        """测试带注释的 SQL"""
        sql = "SELECT * FROM sys_user -- 这是一个注释"
        result = self.validator.validate(sql)
        assert result.is_valid is True

    def test_sanitize_removes_dangerous(self):
        """测试 sanitize 移除危险 SQL"""
        sql = "SELECT 1; DROP TABLE users"
        sanitized = self.validator.sanitize_sql(sql)
        assert sanitized == ""

    def test_complex_select_with_functions(self):
        """测试复杂 SELECT（聚合函数、日期函数）"""
        sql = "SELECT DATE_FORMAT(created_at, '%Y-%m') as month, COUNT(*) as cnt FROM sys_user GROUP BY DATE_FORMAT(created_at, '%Y-%m')"
        result = self.validator.validate(sql)
        assert result.is_valid is True

    def test_select_with_subquery(self):
        """测试子查询"""
        sql = "SELECT * FROM sys_user WHERE dept_id IN (SELECT id FROM sys_dept WHERE name LIKE '%技术%')"
        result = self.validator.validate(sql)
        assert result.is_valid is True


# ==================== Mock 沙箱执行器测试 ====================

class TestSqlSandboxExecutor:
    """Mock SQL 沙箱执行器测试"""

    def setup_method(self):
        self.executor = SqlSandboxExecutor()

    @pytest.mark.asyncio
    async def test_mock_count_execution(self):
        """测试 Mock COUNT 查询"""
        result = await self.executor.execute("SELECT COUNT(*) FROM sys_user")
        assert "columns" in result
        assert "rows" in result
        assert result["row_count"] > 0

    @pytest.mark.asyncio
    async def test_mock_group_by_execution(self):
        """测试 Mock GROUP BY 查询"""
        result = await self.executor.execute("SELECT dept_id, COUNT(*) FROM sys_user GROUP BY dept_id")
        assert result["row_count"] > 0
        assert "columns" in result
        assert "rows" in result

    @pytest.mark.asyncio
    async def test_mock_select_execution(self):
        """测试 Mock SELECT 查询"""
        result = await self.executor.execute("SELECT * FROM sys_user LIMIT 5")
        assert result["row_count"] > 0
        assert "columns" in result

    @pytest.mark.asyncio
    async def test_execution_time_present(self):
        """测试执行时间存在"""
        result = await self.executor.execute("SELECT * FROM sys_user")
        assert result["execution_time_ms"] > 0


# ==================== NL2SQL 引擎测试 ====================

class TestNl2sqlEngine:
    """NL2SQL 引擎测试"""

    def setup_method(self):
        self.engine = Nl2sqlEngine()

    def test_build_system_prompt(self, mock_tables):
        """测试系统提示词构建"""
        prompt = self.engine.build_system_prompt(mock_tables)
        assert "sys_user" in prompt
        assert "sys_dept" in prompt
        assert "username" in prompt
        assert "SELECT" in prompt

    def test_build_few_shot_messages(self):
        """测试 Few-shot 消息构建"""
        messages = self.engine.build_few_shot_messages()
        assert len(messages) > 0
        assert all("role" in msg and "content" in msg for msg in messages)
        # 验证是成对的 (user, assistant)
        assert len(messages) % 2 == 0

    def test_format_schemas(self, mock_tables):
        """测试 Schema 格式化"""
        formatted = self.engine._format_schemas(mock_tables)
        assert "sys_user" in formatted
        assert "用户名" in formatted
        assert "| 列名 | 类型 |" in formatted

    def test_clean_sql_output(self):
        """测试 SQL 清理"""
        # 测试移除 markdown 代码块
        raw = "```sql\nSELECT * FROM sys_user\n```"
        cleaned = self.engine._clean_sql_output(raw)
        assert cleaned == "SELECT * FROM sys_user"

        # 测试移除非 sql 代码块
        raw = "```\nSELECT * FROM sys_user\n```"
        cleaned = self.engine._clean_sql_output(raw)
        assert cleaned == "SELECT * FROM sys_user"

        # 测试移除多余分号
        raw = "SELECT * FROM sys_user; SELECT * FROM sys_dept"
        cleaned = self.engine._clean_sql_output(raw)
        assert "; " not in cleaned

    def test_recommend_chart_table(self):
        """测试图表推荐 - 表格"""
        chart = self.engine.recommend_chart(
            columns=["name"],
            rows=[["A"], ["B"]],
            question="测试",
        )
        assert chart.chart_type == "table"

    def test_recommend_chart_bar(self):
        """测试图表推荐 - 柱状图（11+分类避免饼图）"""
        rows = [[chr(65 + i), i * 10] for i in range(12)]  # A-L, 12 categories
        chart = self.engine.recommend_chart(
            columns=["name", "count"],
            rows=rows,
            question="测试",
        )
        assert chart.chart_type == "bar"

    def test_recommend_chart_pie(self):
        """测试图表推荐 - 饼图"""
        chart = self.engine.recommend_chart(
            columns=["category", "value"],
            rows=[["A", 30], ["B", 20], ["C", 10]],
            question="测试",
        )
        assert chart.chart_type == "pie"

    def test_recommend_chart_line(self):
        """测试图表推荐 - 折线图（时间序列）"""
        chart = self.engine.recommend_chart(
            columns=["created_at", "count"],
            rows=[
                ["2024-01-01", 10],
                ["2024-02-01", 20],
                ["2024-03-01", 15],
                ["2024-04-01", 30],
            ],
            question="测试",
        )
        assert chart.chart_type == "line"

    def test_build_result_summary(self):
        """测试结果摘要构建"""
        summary = self.engine._build_result_summary(
            columns=["name", "age"],
            rows=[["张三", 25], ["李四", 30]],
        )
        assert "总行数: 2" in summary
        assert "age" in summary
        assert "平均值" in summary

    def test_is_numeric(self):
        """测试数值判断"""
        assert self.engine._is_numeric(42) is True
        assert self.engine._is_numeric(3.14) is True
        assert self.engine._is_numeric("123") is True
        assert self.engine._is_numeric("abc") is False
        assert self.engine._is_numeric(None) is False

    @pytest.mark.asyncio
    async def test_generate_sql_with_mock(self):
        """测试使用 Mock LLM 生成 SQL"""
        # 使用 Mock LLM（模拟 OpenAI 响应对象）
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "SELECT * FROM sys_user LIMIT 10"
        mock_response.choices = [mock_choice]

        mock_llm = MagicMock()
        mock_llm.chat = AsyncMock(return_value=mock_response)

        engine = Nl2sqlEngine(llm=mock_llm)
        sql = await engine.generate_sql("查询所有用户")
        assert "SELECT" in sql
        assert mock_llm.chat.called

    @pytest.mark.asyncio
    async def test_interpret_results_no_data(self):
        """测试数据解读 - 无数据"""
        interpretation = await self.engine.interpret_results(
            question="测试",
            sql="SELECT * FROM sys_user",
            columns=[],
            rows=[],
        )
        # 检查返回值包含"无数据"相关描述
        assert interpretation and len(interpretation) > 0
        assert "未返回数据" in interpretation or "无数据" in interpretation


# ==================== Python 沙箱执行器测试 ====================

class TestPythonSandboxExecutor:
    """Python 沙箱执行器测试"""

    def setup_method(self):
        self.executor = PythonSandboxExecutor()

    @pytest.mark.asyncio
    async def test_simple_code_execution(self):
        """测试简单代码执行"""
        code = """
result = 1 + 2
"""
        output = await self.executor.execute(code)
        assert output["error"] is None
        assert output["result"] == 3

    @pytest.mark.asyncio
    async def test_code_with_input_data(self):
        """测试带输入数据的代码执行"""
        code = """
result = input_data["a"] + input_data["b"]
"""
        output = await self.executor.execute(code, input_data={"a": 10, "b": 20})
        assert output["error"] is None
        assert output["result"] == 30

    @pytest.mark.asyncio
    async def test_invalid_syntax(self):
        """测试语法错误"""
        code = """
result = 1 +
"""
        output = await self.executor.execute(code)
        assert output["error"] is not None

    @pytest.mark.asyncio
    async def test_list_comprehension(self):
        """测试列表推导式"""
        code = """
numbers = [1, 2, 3, 4, 5]
result = [x * x for x in numbers]
"""
        output = await self.executor.execute(code)
        assert output["result"] == [1, 4, 9, 16, 25]

    @pytest.mark.asyncio
    async def test_string_operation(self):
        """测试字符串操作"""
        code = """
s = "hello, world"
result = s.upper()
"""
        output = await self.executor.execute(code)
        assert output["result"] == "HELLO, WORLD"


# ==================== API Schema 测试 ====================

class TestNl2sqlSchemas:
    """NL2SQL Schema 测试"""

    def test_ask_request_valid(self):
        """测试有效问数请求"""
        request = Nl2sqlAskRequest(question="查询所有用户")
        assert request.question == "查询所有用户"
        assert request.execute_sql is True
        assert request.need_interpretation is True

    def test_ask_request_empty_question(self):
        """测试空问题被拒绝"""
        with pytest.raises(Exception):
            Nl2sqlAskRequest(question="")

    def test_ask_response_basic(self):
        """测试问数响应构建"""
        response = Nl2sqlAskResponse(
            question="测试",
            generated_sql="SELECT 1",
            validation=SqlValidationResult(
                is_valid=True,
                is_readonly=True,
                sql_type="SELECT",
            ),
        )
        assert response.question == "测试"
        assert response.generated_sql == "SELECT 1"
        assert response.validation.is_valid is True

    def test_table_schema(self):
        """测试表结构 Schema"""
        table = TableSchema(
            table_name="test",
            table_comment="测试表",
            columns=[
                ColumnInfo(name="id", type="int", nullable=False, is_primary_key=True, comment="ID"),
            ],
        )
        assert table.table_name == "test"
        assert len(table.columns) == 1
        assert table.columns[0].is_primary_key is True


# ==================== 集成测试 ====================

class TestNl2sqlIntegration:
    """NL2SQL 集成测试"""

    @pytest.mark.asyncio
    async def test_full_flow_with_mocks(self):
        """测试完整流程（使用 Mock）"""
        from app.services.nl2sql_service import Nl2sqlService

        # Mock 所有依赖 - 使用真实的 Pydantic 模型
        mock_engine = MagicMock()
        mock_engine.generate_sql = AsyncMock(return_value="SELECT * FROM sys_user LIMIT 10")
        mock_engine.recommend_chart = MagicMock(return_value=ChartRecommendation(
            chart_type="table",
            title="测试",
            reasoning="测试",
        ))

        mock_validator = MagicMock()
        mock_validator.validate.return_value = SqlValidationResult(
            is_valid=True,
            is_readonly=True,
            sql_type="SELECT",
        )

        mock_executor = AsyncMock()
        mock_executor.execute.return_value = {
            "columns": ["id", "username"],
            "rows": [[1, "admin"], [2, "user"]],
            "row_count": 2,
            "execution_time_ms": 5,
        }

        service = Nl2sqlService(
            engine=mock_en