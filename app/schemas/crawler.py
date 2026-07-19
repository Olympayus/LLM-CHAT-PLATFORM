"""爬虫模块 Pydantic Schema

包含:
- CrawlerTask:      任务配置的创建/更新/响应模型
- CrawlerExecutionLog:  执行日志的响应/查询模型
- DataCleanRule:     清洗规则的创建/更新/响应模型
- CrawlResult:        单次爬取的结果模型
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ==================== CrawlerTask Schema ====================


class CrawlerTaskCreate(BaseModel):
    """创建爬虫任务请求"""

    name: str = Field(..., min_length=1, max_length=128, description="任务名称")
    request_url: str = Field(..., min_length=1, max_length=1024, description="请求地址")
    request_method: str = Field("GET", description="请求方法: GET / POST")
    request_headers: Optional[dict[str, str]] = Field(None, description="请求头")
    request_body: Optional[str] = Field(None, description="POST 请求体")
    parse_rules: Optional[dict[str, Any]] = Field(
        None,
        description="解析规则，支持 XPath / CSS 选择器",
        examples=[
            {
                "type": "xpath",  # 或 "css"
                "fields": {
                    "title": "//h1/text()",
                    "link": "//a/@href",
                },
            }
        ],
    )
    output_table: Optional[str] = Field(None, max_length=64, description="入库目标表名")
    schedule_cron: Optional[str] = Field(
        None, max_length=64, description="Cron 表达式，为空则仅手动触发"
    )
    is_enabled: int = Field(1, ge=0, le=1, description="是否启用: 1=是 0=否")
    clean_rule_ids: Optional[list[int]] = Field(None, description="关联的清洗规则 ID 列表")


class CrawlerTaskUpdate(BaseModel):
    """更新爬虫任务请求（全部字段可选）"""

    name: Optional[str] = Field(None, min_length=1, max_length=128, description="任务名称")
    request_url: Optional[str] = Field(None, min_length=1, max_length=1024, description="请求地址")
    request_method: Optional[str] = Field(None, description="请求方法")
    request_headers: Optional[dict[str, str]] = Field(None, description="请求头")
    request_body: Optional[str] = Field(None, description="POST 请求体")
    parse_rules: Optional[dict[str, Any]] = Field(None, description="解析规则")
    output_table: Optional[str] = Field(None, max_length=64, description="入库目标表名")
    schedule_cron: Optional[str] = Field(None, max_length=64, description="Cron 表达式")
    is_enabled: Optional[int] = Field(None, ge=0, le=1, description="是否启用")
    clean_rule_ids: Optional[list[int]] = Field(None, description="关联的清洗规则 ID 列表")


class CrawlerTaskResponse(BaseModel):
    """爬虫任务响应"""

    id: int
    name: str
    request_url: str
    request_method: str
    request_headers: Optional[dict[str, str]] = None
    request_body: Optional[str] = None
    parse_rules: Optional[dict[str, Any]] = None
    output_table: Optional[str] = None
    schedule_cron: Optional[str] = None
    is_enabled: int
    created_by: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    clean_rules: list["DataCleanRuleResponse"] = Field(
        default_factory=list, description="关联的清洗规则"
    )

    class Config:
        from_attributes = True


# ==================== CrawlerExecutionLog Schema ====================


class CrawlerExecutionLogResponse(BaseModel):
    """爬虫执行日志响应"""

    id: int
    task_id: int
    status: str  # success / failed / running
    rows_collected: int
    rows_inserted: int
    error_message: Optional[str] = None
    started_at: str
    finished_at: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class CrawlerExecutionLogQuery(BaseModel):
    """执行日志查询参数"""

    task_id: Optional[int] = Field(None, description="按任务ID筛选")
    status: Optional[str] = Field(None, description="按状态筛选: success / failed / running")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页条数")


# ==================== DataCleanRule Schema ====================


class DataCleanRuleCreate(BaseModel):
    """创建数据清洗规则请求"""

    name: str = Field(..., min_length=1, max_length=128, description="规则名称")
    rule_type: str = Field(
        ..., description="规则类型: dedup / normalize / mask / custom"
    )
    config: dict[str, Any] = Field(
        ..., description="规则配置 (JSON)",
        examples=[
            {"mode": "strict", "keys": ["title"]},
            {"mode": "lowercase", "field": "name"},
            {"pattern": "phone", "replacement": "***"},
        ],
    )
    target_field: Optional[str] = Field(None, max_length=64, description="目标字段名")
    sort_order: int = Field(0, description="执行顺序，数值越小越先执行")
    task_id: int = Field(..., description="关联的爬虫任务ID")


class DataCleanRuleUpdate(BaseModel):
    """更新数据清洗规则请求"""

    name: Optional[str] = Field(None, min_length=1, max_length=128, description="规则名称")
    rule_type: Optional[str] = Field(None, description="规则类型")
    config: Optional[dict[str, Any]] = Field(None, description="规则配置")
    target_field: Optional[str] = Field(None, max_length=64, description="目标字段名")
    sort_order: Optional[int] = Field(None, description="执行顺序")
    task_id: Optional[int] = Field(None, description="关联的爬虫任务ID")


class DataCleanRuleResponse(BaseModel):
    """数据清洗规则响应"""

    id: int
    name: str
    rule_type: str
    config: dict[str, Any]
    target_field: Optional[str] = None
    sort_order: int
    task_id: int

    class Config:
        from_attributes = True


# ==================== 爬取结果 Schema ====================


class CrawlResult(BaseModel):
    """单次爬取结果"""

    task_id: int
    task_name: str
    status: str  # success / failed
    rows_collected: int = 0
    rows_inserted: int = 0
    error_message: Optional[str] = None
    started_at: str
    finished_at: Optional[str] = None
    sample_data: Optional[list[dict[str, Any]]] = Field(
        None, description="前 N 条样本数据（用于调试）"
    )


class CrawlerTestRequest(BaseModel):
    """测试解析规则请求"""

    request_url: str = Field(..., min_length=1, max_length=1024, description="请求地址")
    request_method: str = Field("GET", description="请求方法")
    request_headers: Optional[dict[str, str]] = Field(None, description="请求头")
    request_body: Optional[str] = Field(None, description="POST 请求体")
    parse_rules: dict[str, Any] = Field(..., description="解析规则")


class CrawlerTestResponse(BaseModel):
    """测试解析规则响应"""

    html_snippet: Optional[str] = Field(None, description="HTML 片段（前 2000 字符）")
    parsed_data: Optional[list[dict[str, Any]]] = Field(None, description="解析结果")
    parsed_count: int = 0
    error_message: Optional[str] = None


# 更新 forward reference
CrawlerTaskResponse.model_rebuild()
