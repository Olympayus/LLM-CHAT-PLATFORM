"""NL2SQL 智能问数 Pydantic 请求/响应 Schema

包含:
- 问数请求/响应
- 查询历史 & 收藏 CRUD
- 安全校验结果
- 图表推荐
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ==================== 问数（核心） ====================


class Nl2sqlAskRequest(BaseModel):
    """智能问数请求"""

    question: str = Field(..., min_length=1, max_length=2000, description="自然语言问题")
    execute_sql: bool = Field(True, description="是否执行 SQL 并返回结果")
    need_interpretation: bool = Field(True, description="是否需要 AI 数据解读")
    database_name: str = Field("llm_platform", description="查询的目标数据库名称")


class ColumnInfo(BaseModel):
    """列信息"""

    name: str = Field(..., description="列名")
    type: str = Field(..., description="数据类型")
    nullable: bool = Field(True, description="是否可为空")
    comment: str = Field("", description="列注释")
    is_primary_key: bool = Field(False, description="是否主键")


class TableSchema(BaseModel):
    """表结构信息"""

    table_name: str = Field(..., description="表名")
    table_comment: str = Field("", description="表注释")
    columns: list[ColumnInfo] = Field(default_factory=list, description="列列表")


class SchemaInfo(BaseModel):
    """数据库 Schema 信息"""

    tables: list[TableSchema] = Field(default_factory=list, description="表列表")
    database_name: str = Field("llm_platform", description="数据库名")


class SqlValidationResult(BaseModel):
    """SQL 安全校验结果"""

    is_valid: bool = Field(..., description="是否通过校验")
    is_readonly: bool = Field(True, description="是否为只读查询")
    sql_type: str = Field("SELECT", description="SQL 类型")
    error: Optional[str] = Field(None, description="校验失败原因")
    warning: Optional[str] = Field(None, description="警告信息")


class ChartRecommendation(BaseModel):
    """图表类型推荐"""

    chart_type: str = Field(
        ..., description="推荐图表类型: bar(柱状图)/line(折线图)/pie(饼图)/table(表格)"
    )
    title: str = Field("", description="图表标题")
    x_axis: Optional[str] = Field(None, description="X轴字段")
    y_axis: Optional[list[str]] = Field(None, description="Y轴字段列表")
    reasoning: str = Field("", description="推荐理由")


class Nl2sqlAskResponse(BaseModel):
    """智能问数响应"""

    question: str = Field(..., description="原始问题")
    generated_sql: str = Field(..., description="生成的 SQL")
    validation: SqlValidationResult = Field(..., description="安全校验结果")
    execution_time_ms: Optional[int] = Field(None, description="执行耗时(ms)")
    columns: Optional[list[str]] = Field(None, description="结果列名")
    rows: Optional[list[list[Any]]] = Field(None, description="结果数据行")
    row_count: Optional[int] = Field(None, description="结果行数")
    chart_recommendation: Optional[ChartRecommendation] = Field(
        None, description="图表推荐"
    )
    interpretation: Optional[str] = Field(None, description="AI 数据解读")
    error_message: Optional[str] = Field(None, description="错误信息")


# ==================== 查询历史 ====================


class QueryHistoryItem(BaseModel):
    """查询历史条目（列表用）"""

    id: int
    user_id: int
    question: str
    generated_sql: str
    is_valid: int
    execution_time_ms: Optional[int] = None
    result_rows: Optional[int] = None
    error_message: Optional[str] = None
    chart_type: Optional[str] = None
    interpretation: Optional[str] = None
    created_at: Optional[str] = None


class QueryHistoryDetail(BaseModel):
    """查询历史详情"""

    id: int
    user_id: int
    question: str
    generated_sql: str
    is_valid: int
    execution_time_ms: Optional[int] = None
    result_rows: Optional[int] = None
    columns: Optional[list[str]] = None
    rows: Optional[list[list[Any]]] = None
    chart_type: Optional[str] = None
    interpretation: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None


class QueryHistoryListRequest(BaseModel):
    """查询历史列表请求"""

    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页条数")
    keyword: Optional[str] = Field(None, description="关键词搜索")


class DeleteHistoryRequest(BaseModel):
    """删除历史请求"""

    ids: list[int] = Field(..., min_length=1, description="要删除的历史记录ID列表")


# ==================== 收藏 ====================


class FavoriteCreateRequest(BaseModel):
    """创建收藏请求"""

    query_history_id: int = Field(..., description="查询历史ID")
    note: Optional[str] = Field(None, max_length=256, description="备注")


class FavoriteItem(BaseModel):
    """收藏条目"""

    id: int
    user_id: int
    query_history_id: Optional[int] = None
    question: str
    sql: str
    chart_type: Optional[str] = None
    note: Optional[str] = None
    created_at: Optional[str] = None


class FavoriteListRequest(BaseModel):
    """收藏列表请求"""

    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页条数")


class FavoriteUpdateRequest(BaseModel):
    """更新收藏请求"""

    note: Optional[str] = Field(None, max_length=256, description="备注")


# ==================== Schema 信息 ====================


class SchemaInfoRequest(BaseModel):
    """Schema 信息请求"""

    database_name: str = Field("llm_platform", description="数据库名")


class SchemaInfoResponse(BaseModel):
    """Schema 信息响应"""

    tables: list[TableSchema] = Field(default_factory=list, description="所有表结构")
    table_count: int = Field(0, description="表数量")