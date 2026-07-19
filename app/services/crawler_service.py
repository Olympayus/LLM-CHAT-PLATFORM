"""爬虫业务服务

编排爬虫任务的生命周期:
- 任务 CRUD
- HTTP 数据采集（httpx）
- HTML 解析（BeautifulSoup / lxml — XPath & CSS Selector）
- 数据清洗流水线（dedup / normalize / mask / custom）
- 执行日志记录
- 爬取结果入库
"""

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from lxml import etree
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crawler import CrawlerExecutionLog, CrawlerTask, DataCleanRule
from app.schemas.crawler import (
    CrawlerExecutionLogQuery,
    CrawlerTaskCreate,
    CrawlerTaskResponse,
    CrawlerTaskUpdate,
    CrawlResult,
    CrawlerTestRequest,
    CrawlerTestResponse,
    DataCleanRuleCreate,
    DataCleanRuleResponse,
    DataCleanRuleUpdate,
)


# ==================== HTML 解析工具 ====================


class HtmlParser:
    """HTML 解析器，支持 XPath 和 CSS 选择器"""

    @staticmethod
    def parse(html: str, parse_rules: dict[str, Any]) -> list[dict[str, Any]]:
        """根据解析规则从 HTML 中提取结构化数据。

        Args:
            html: 原始 HTML 字符串
            parse_rules: 解析规则，格式:
                {
                    "type": "xpath" | "css",           # 选择器类型
                    "item_selector": "//div[@class='item']",  # 列表项选择器
                    "fields": {                         # 字段映射
                        "title": "./h2/text()",         # XPath: 相对于 item
                        "url": "./a/@href",             # XPath: 属性
                    },
                    # CSS 模式:
                    "type": "css",
                    "item_selector": "div.item",        # CSS 列表项选择器
                    "fields": {
                        "title": "h2::text",            # CSS: 文本
                        "url": "a::attr(href)",         # CSS: 属性
                    },
                }

        Returns:
            list[dict]: 解析出的结构化数据列表
        """
        selector_type = parse_rules.get("type", "xpath")
        item_selector = parse_rules.get("item_selector", "")
        fields = parse_rules.get("fields", {})

        if not item_selector or not fields:
            logger.warning("解析规则缺少 item_selector 或 fields")
            return []

        if selector_type == "xpath":
            return HtmlParser._parse_xpath(html, item_selector, fields)
        elif selector_type == "css":
            return HtmlParser._parse_css(html, item_selector, fields)
        else:
            logger.error(f"不支持的解析类型: {selector_type}")
            return []

    @staticmethod
    def _parse_xpath(
        html: str, item_selector: str, fields: dict[str, str]
    ) -> list[dict[str, Any]]:
        """使用 lxml XPath 解析"""
        results: list[dict[str, Any]] = []
        try:
            tree = etree.HTML(html)
            items = tree.xpath(item_selector)
        except etree.XPathEvalError as e:
            logger.error(f"XPath 表达式错误: {e}")
            return []

        for item in items:
            row: dict[str, Any] = {}
            # item 可能是 Element 或字符串
            is_element = isinstance(item, etree._Element)
            for field_name, xpath_expr in fields.items():
                try:
                    if is_element:
                        values = item.xpath(xpath_expr)
                    else:
                        values = []
                    # 取第一个结果，去除首尾空白
                    raw = str(values[0]).strip() if values else ""
                    row[field_name] = raw
                except etree.XPathEvalError as e:
                    logger.warning(f"字段 '{field_name}' XPath 错误: {e}")
                    row[field_name] = ""
            if row:
                results.append(row)
        return results

    @staticmethod
    def _parse_css(
        html: str, item_selector: str, fields: dict[str, str]
    ) -> list[dict[str, Any]]:
        """使用 BeautifulSoup CSS 选择器解析"""
        results: list[dict[str, Any]] = []
        soup = BeautifulSoup(html, "lxml")
        items = soup.select(item_selector)

        for item in items:
            row: dict[str, Any] = {}
            for field_name, css_expr in fields.items():
                value = HtmlParser._extract_css_value(item, css_expr)
                row[field_name] = value
            if row:
                results.append(row)
        return results

    @staticmethod
    def _extract_css_value(element, css_expr: str) -> str:
        """从 CSS 表达式中提取值，支持:
        - "selector::text"       → 文本内容
        - "selector::attr(href)" → 属性值
        - "selector"             → 默认取文本
        """
        # 解析属性提取语法: ::attr(name)
        attr_match = re.match(r"^(.+?)::attr\((\w+)\)$", css_expr.strip())
        if attr_match:
            selector = attr_match.group(1).strip()
            attr_name = attr_match.group(2).strip()
            selected = element.select_one(selector)
            if selected:
                return (selected.get(attr_name) or "").strip()
            return ""

        # 解析文本提取语法: ::text
        if css_expr.endswith("::text"):
            selector = css_expr[:-6].strip()
            selected = element.select_one(selector)
            if selected:
                return selected.get_text(strip=True)
            return ""

        # 默认：取文本
        selected = element.select_one(css_expr)
        if selected:
            return selected.get_text(strip=True)
        return ""


# ==================== 数据清洗引擎 ====================


class DataCleanEngine:
    """数据清洗引擎，按 sort_order 顺序执行清洗规则"""

    # 支持的去重模式
    DEDUP_MODES = {"strict", "loose", "field"}

    @staticmethod
    async def clean(
        data: list[dict[str, Any]],
        rules: list[DataCleanRule],
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """按规则顺序清洗数据。

        Args:
            data: 原始数据列表
            rules: 已按 sort_order 排序的清洗规则列表

        Returns:
            (清洗后数据, 统计信息{"dedup_removed": 0, ...})
        """
        stats: dict[str, int] = {
            "input_count": len(data),
            "output_count": 0,
            "dedup_removed": 0,
            "normalized": 0,
            "masked": 0,
            "custom_applied": 0,
        }

        cleaned = list(data)

        for rule in rules:
            if not cleaned:
                break
            try:
                if rule.rule_type == "dedup":
                    before = len(cleaned)
                    cleaned = DataCleanEngine._apply_dedup(cleaned, rule.config)
                    stats["dedup_removed"] += before - len(cleaned)
                elif rule.rule_type == "normalize":
                    cleaned, count = DataCleanEngine._apply_normalize(cleaned, rule)
                    stats["normalized"] += count
                elif rule.rule_type == "mask":
                    cleaned, count = DataCleanEngine._apply_mask(cleaned, rule)
                    stats["masked"] += count
                elif rule.rule_type == "custom":
                    cleaned, count = DataCleanEngine._apply_custom(cleaned, rule)
                    stats["custom_applied"] += count
            except Exception as e:
                logger.error(f"清洗规则 '{rule.name}' (id={rule.id}) 执行异常: {e}")

        stats["output_count"] = len(cleaned)
        return cleaned, stats

    @staticmethod
    def _apply_dedup(
        data: list[dict[str, Any]], config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """去重逻辑

        config:
            mode: "strict" | "loose" | "field"
            keys: ["field1", "field2"]   # mode=field 时必填
        """
        mode = config.get("mode", "strict")
        seen: set[str] = set()
        result: list[dict[str, Any]] = []

        for row in data:
            if mode == "field":
                keys = config.get("keys", [])
                if not keys:
                    result.append(row)
                    continue
                fingerprint = json.dumps(
                    {k: row.get(k) for k in keys}, sort_keys=True, default=str
                )
            else:
                # strict / loose
                fingerprint = json.dumps(row, sort_keys=True, default=str)

            if fingerprint not in seen:
                seen.add(fingerprint)
                result.append(row)

        return result

    @staticmethod
    def _apply_normalize(
        data: list[dict[str, Any]], rule: DataCleanRule
    ) -> tuple[list[dict[str, Any]], int]:
        """规范化处理

        config:
            mode: "trim" | "lowercase" | "strip_html" | "whitespace"
            fields: ["field1", "field2"]  # 不指定则全部字段
        """
        config = rule.config
        mode = config.get("mode", "trim")
        target = config.get("fields") or list(data[0].keys()) if data else []
        count = 0

        for row in data:
            for field in target:
                if field not in row or not isinstance(row[field], str):
                    continue
                original = row[field]
                if mode == "trim":
                    row[field] = original.strip()
                elif mode == "lowercase":
                    row[field] = original.lower()
                elif mode == "strip_html":
                    row[field] = re.sub(r"<[^>]+>", "", original)
                elif mode == "whitespace":
                    row[field] = re.sub(r"\s+", " ", original).strip()
                if row[field] != original:
                    count += 1
        return data, count

    @staticmethod
    def _apply_mask(
        data: list[dict[str, Any]], rule: DataCleanRule
    ) -> tuple[list[dict[str, Any]], int]:
        """数据脱敏

        config:
            pattern: "phone" | "email" | "id_card" | "custom_regex"
            replacement: "***"       # 替换文本
            fields: ["field1"]       # 目标字段
            custom_regex: "..."      # pattern=custom_regex 时使用
        """
        config = rule.config
        pattern_type = config.get("pattern", "phone")
        replacement = config.get("replacement", "***")
        targets = config.get("fields", [])
        custom_regex = config.get("custom_regex", "")
        count = 0

        # 常用脱敏正则
        patterns = {
            "phone": r"1[3-9]\d{9}",
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "id_card": r"\d{17}[\dXx]",
        }

        regex = custom_regex if pattern_type == "custom_regex" else patterns.get(pattern_type, "")
        if not regex:
            return data, count

        compiled = re.compile(regex)
        for row in data:
            for field in targets:
                if field not in row or not isinstance(row[field], str):
                    continue
                original = row[field]
                row[field] = compiled.sub(replacement, original)
                if row[field] != original:
                    count += 1
        return data, count

    @staticmethod
    def _apply_custom(
        data: list[dict[str, Any]], rule: DataCleanRule
    ) -> tuple[list[dict[str, Any]], int]:
        """自定义清洗（预留扩展）

        config:
            action: "replace" | "filter" | "transform"
            field: "field_name"
            old_value / new_value  (replace)
            condition              (filter)
        """
        config = rule.config
        action = config.get("action", "replace")
        count = 0

        if action == "replace":
            field = config.get("field", "")
            old_val = config.get("old_value")
            new_val = config.get("new_value", "")
            for row in data:
                if field in row and row[field] == old_val:
                    row[field] = new_val
                    count += 1
        elif action == "filter":
            field = config.get("field", "")
            condition = config.get("condition")
            if condition and field:
                # 简单条件过滤：保留符合条件的行
                filtered = []
                for row in data:
                    val = row.get(field)
                    # 支持简单判断：empty / not_empty / equals:value
                    op = condition.get("op", "not_empty")
                    target_val = condition.get("value")
                    if op == "empty" and (val is None or val == ""):
                        filtered.append(row)
                    elif op == "not_empty" and val is not None and val != "":
                        filtered.append(row)
                    elif op == "equals" and str(val) == str(target_val):
                        filtered.append(row)
                    elif op == "not_equals" and str(val) != str(target_val):
                        filtered.append(row)
                    else:
                        count += 1
                data[:] = filtered
        elif action == "transform":
            # 预留：更复杂的转换逻辑
            field = config.get("field", "")
            transform_type = config.get("transform_type", "")
            for row in data:
                if field in row and isinstance(row[field], str):
                    if transform_type == "strip_prefix":
                        prefix = config.get("prefix", "")
                        if row[field].startswith(prefix):
                            row[field] = row[field][len(prefix):]
                            count += 1
                    elif transform_type == "strip_suffix":
                        suffix = config.get("suffix", "")
                        if row[field].endswith(suffix):
                            row[field] = row[field][:-len(suffix)]
                            count += 1

        return data, count


# ==================== 爬虫服务 ====================


class CrawlerService:
    """爬虫核心业务服务

    编排采集全流程：HTTP 请求 → HTML 解析 → 数据清洗 → 结果入库 → 日志记录
    """

    def __init__(self, http_timeout: int = 30):
        self.http_timeout = http_timeout
        self.parser = HtmlParser()
        self.cleaner = DataCleanEngine()

    # ---------- HTTP 请求 ----------

    async def _fetch(self, task: CrawlerTask) -> tuple[str, Optional[str]]:
        """发送 HTTP 请求，返回 (html, error)"""
        headers = task.request_headers or {}
        headers.setdefault("User-Agent", (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ))

        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                if task.request_method.upper() == "POST":
                    body = task.request_body or ""
                    resp = await client.post(
                        task.request_url,
                        headers=headers,
                        content=body,
                        follow_redirects=True,
                    )
                else:
                    resp = await client.get(
                        task.request_url,
                        headers=headers,
                        follow_redirects=True,
                    )
                resp.raise_for_status()
                return resp.text, None
        except httpx.TimeoutException:
            return "", f"请求超时 ({self.http_timeout}s): {task.request_url}"
        except httpx.HTTPStatusError as e:
            return "", f"HTTP 错误 {e.response.status_code}: {task.request_url}"
        except Exception as e:
            return "", f"请求异常: {str(e)}"

    # ---------- 完整采集流水线 ----------

    async def execute_task(
        self,
        task_id: int,
        db: AsyncSession,
    ) -> CrawlResult:
        """执行一次完整的爬取任务。

        Args:
            task_id: 爬虫任务 ID
            db: 数据库会话

        Returns:
            CrawlResult: 本次爬取结果摘要
        """
        started_at = datetime.now(timezone.utc)

        # 1. 获取任务配置
        task = await self._get_task_or_none(db, task_id)
        if task is None:
            return CrawlResult(
                task_id=task_id,
                task_name="unknown",
                status="failed",
                error_message=f"任务 {task_id} 不存在",
                started_at=started_at.isoformat(),
            )

        # 2. HTTP 请求
        html, fetch_error = await self._fetch(task)
        if fetch_error:
            # 记录失败日志
            log = CrawlerExecutionLog(
                task_id=task.id,
                status="failed",
                rows_collected=0,
                rows_inserted=0,
                error_message=fetch_error,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
            )
            db.add(log)
            await db.commit()

            return CrawlResult(
                task_id=task.id,
                task_name=task.name,
                status="failed",
                error_message=fetch_error,
                started_at=started_at.isoformat(),
                finished_at=datetime.now(timezone.utc).isoformat(),
            )

        # 3. HTML 解析
        parse_rules = task.parse_rules or {}
        rows = self.parser.parse(html, parse_rules)
        rows_collected = len(rows)

        # 4. 数据清洗
        clean_rules_query = (
            select(DataCleanRule)
            .where(
                DataCleanRule.task_id == task.id,
                DataCleanRule.is_deleted == 0,
            )
            .order_by(DataCleanRule.sort_order)
        )
        result = await db.execute(clean_rules_query)
        rules = result.scalars().all()
        cleaned_rows, clean_stats = await self.cleaner.clean(rows, list(rules))
        rows_inserted = len(cleaned_rows)

        # 5. Write to dynamic table
        if task.output_table and cleaned_rows:
            try:
                await self._ensure_table_exists(db, task.output_table, cleaned_rows[0])
                actual_inserted = await self._write_to_table(db, task.output_table, cleaned_rows)
                rows_inserted = actual_inserted
                logger.info("Task written: {} rows to {}".format(rows_inserted, task.output_table))
            except Exception as e:
                logger.error("Dynamic table write failed: {}".format(e))
                fetch_error = "Write failed: {}".format(e)

        # 6. 记录执行日志
        finished_at = datetime.now(timezone.utc)
        log = CrawlerExecutionLog(
            task_id=task.id,
            status="success",
            rows_collected=rows_collected,
            rows_inserted=rows_inserted,
            started_at=started_at,
            finished_at=finished_at,
        )
        db.add(log)
        await db.commit()

        return CrawlResult(
            task_id=task.id,
            task_name=task.name,
            status="success",
            rows_collected=rows_collected,
            rows_inserted=rows_inserted,
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            sample_data=cleaned_rows[:10],
        )



    # ---- Dynamic Table Write Helpers ----

    @staticmethod
    async def _ensure_table_exists(db, table_name, sample_row):
        import re
        from sqlalchemy import text as sa_text
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
            raise ValueError("Invalid table name: {}".format(repr(table_name)))
        safe = re.sub(r"[^a-zA-Z0-9_]", "", table_name)
        rctx = await db.execute(sa_text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = :tbl"
        ), {"tbl": safe})
        if rctx.scalar():
            return
        parts = ["id BIGINT PRIMARY KEY AUTO_INCREMENT", "crawler_task_id BIGINT NOT NULL"]
        for k, v in sample_row.items():
            cn = re.sub(r"[^a-zA-Z0-9_]", "", k) or "_col_{}".format(hash(k) % 10000)
            parts.append("`{}` {}".format(cn, CrawlerService._infer_mysql_type(v)))
        parts.append("created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP")
        parts.append("updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
        ddl = "CREATE TABLE `{}` ({}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4".format(
            safe, ", ".join(parts))
        await db.execute(sa_text(ddl))
        logger.success("Auto-created table: {} ({} cols)".format(safe, len(sample_row)))

    @staticmethod
    def _infer_mysql_type(value):
        if value is None:
            return "VARCHAR(512)"
        if isinstance(value, bool):
            return "TINYINT(1)"
        if isinstance(value, int):
            return "BIGINT" if abs(value) > 2147483647 else "INT"
        if isinstance(value, float):
            return "DOUBLE"
        if isinstance(value, (bytes, bytearray)):
            return "BLOB"
        s = str(value)
        if len(s) <= 255:
            return "VARCHAR(255)"
        if len(s) <= 4000:
            return "VARCHAR(4000)"
        return "TEXT"

    @staticmethod
    async def _write_to_table(db, table_name, rows):
        import re
        from sqlalchemy import text as sa_text
        if not rows:
            return 0
        safe = re.sub(r"[^a-zA-Z0-9_]", "", table_name)
        keys = list(rows[0].keys())
        cols = [re.sub(r"[^a-zA-Z0-9_]", "", k) or "_col_{}".format(hash(k) % 10000) for k in keys]
        total = 0
        for i in range(0, len(rows), 100):
            batch = rows[i:i + 100]
            placeholders = []
            params = {}
            for ri, row in enumerate(batch):
                vals = []
                for ci, k in enumerate(keys):
                    pn = "r{}_c{}".format(ri, ci)
                    vals.append(":" + pn)
                    params[pn] = row.get(k, "")
                placeholders.append("(" + ", ".join(vals) + ")")
            sql = "INSERT INTO `{}` ({}, `created_at`, `updated_at`) VALUES {}".format(
                safe, ", ".join("`{}`".format(c) for c in cols), ", ".join(placeholders))
            await db.execute(sa_text(sql), params)
            total += len(batch)
        await db.commit()
        logger.info("Dynamic write: {} rows -> {}".format(total, safe))
        return total

    async def test_parse(self, request: CrawlerTestRequest) -> CrawlerTestResponse:
        """测试解析规则（不存库）。

        Args:
            request: 测试请求（URL + 解析规则）

        Returns:
            CrawlerTestResponse: HTML 片段 + 解析结果
        """
        headers = request.request_headers or {}
        headers.setdefault("User-Agent", (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ))

        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                if request.request_method.upper() == "POST":
                    resp = await client.post(
                        request.request_url,
                        headers=headers,
                        content=request.request_body or "",
                        follow_redirects=True,
                    )
                else:
                    resp = await client.get(
                        request.request_url,
                        headers=headers,
                        follow_redirects=True,
                    )
                resp.raise_for_status()
                html = resp.text
        except Exception as e:
            return CrawlerTestResponse(error_message=str(e))

        rows = self.parser.parse(html, request.parse_rules)
        return CrawlerTestResponse(
            html_snippet=html[:2000],
            parsed_data=rows[:20],
            parsed_count=len(rows),
        )

    # ==================== CrawlerTask CRUD ====================

    async def _get_task_or_none(
        self, db: AsyncSession, task_id: int
    ) -> Optional[CrawlerTask]:
        """获取单个任务（包含未删除的）"""
        from sqlalchemy import select as sa_select

        stmt = sa_select(CrawlerTask).where(
            CrawlerTask.id == task_id, CrawlerTask.is_deleted == 0
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_task_with_rules(
        self, db: AsyncSession, task_id: int
    ) -> Optional[tuple[CrawlerTask, list[DataCleanRule]]]:
        """获取任务及其关联的清洗规则"""
        task = await self._get_task_or_none(db, task_id)
        if task is None:
            return None

        stmt = (
            select(DataCleanRule)
            .where(
                DataCleanRule.task_id == task_id,
                DataCleanRule.is_deleted == 0,
            )
            .order_by(DataCleanRule.sort_order)
        )
        result = await db.execute(stmt)
        rules = list(result.scalars().all())
        return task, rules

    async def create_task(
        self, db: AsyncSession, create: CrawlerTaskCreate, created_by: Optional[int] = None
    ) -> CrawlerTaskResponse:
        """创建爬虫任务"""
        task = CrawlerTask(
            name=create.name,
            request_url=create.request_url,
            request_method=create.request_method,
            request_headers=create.request_headers,
            request_body=create.request_body,
            parse_rules=create.parse_rules,
            output_table=create.output_table,
            schedule_cron=create.schedule_cron,
            is_enabled=create.is_enabled,
            created_by=created_by,
        )
        db.add(task)
        await db.flush()

        # 如果有预选清洗规则，关联到任务
        # 注意：clean_rule_ids 只是预设，实际规则仍然独立关联 task_id
        # 这里任务已创建，规则可通过独立 API 关联

        await db.commit()
        await db.refresh(task)

        resp = CrawlerTaskResponse(
            id=task.id,
            name=task.name,
            request_url=task.request_url,
            request_method=task.request_method,
            request_headers=task.request_headers,
            request_body=task.request_body,
            parse_rules=task.parse_rules,
            output_table=task.output_table,
            schedule_cron=task.schedule_cron,
            is_enabled=task.is_enabled,
            created_by=task.created_by,
            created_at=task.created_at.isoformat() if task.created_at else None,
            updated_at=task.updated_at.isoformat() if task.updated_at else None,
        )
        return resp

    async def get_task(
        self, db: AsyncSession, task_id: int
    ) -> Optional[CrawlerTaskResponse]:
        """获取单个爬虫任务"""
        pair = await self._get_task_with_rules(db, task_id)
        if pair is None:
            return None

        task, rules = pair
        return CrawlerTaskResponse(
            id=task.id,
            name=task.name,
            request_url=task.request_url,
            request_method=task.request_method,
            request_headers=task.request_headers,
            request_body=task.request_body,
            parse_rules=task.parse_rules,
            output_table=task.output_table,
            schedule_cron=task.schedule_cron,
            is_enabled=task.is_enabled,
            created_by=task.created_by,
            created_at=task.created_at.isoformat() if task.created_at else None,
            updated_at=task.updated_at.isoformat() if task.updated_at else None,
            clean_rules=[
                DataCleanRuleResponse(
                    id=r.id,
                    name=r.name,
                    rule_type=r.rule_type,
                    config=r.config,
                    target_field=r.target_field,
                    sort_order=r.sort_order,
                    task_id=r.task_id,
                )
                for r in rules
            ],
        )

    async def list_tasks(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
    ) -> dict:
        """分页查询爬虫任务列表"""
        base = select(CrawlerTask).where(CrawlerTask.is_deleted == 0)
        count_base = select(func.count(CrawlerTask.id)).where(CrawlerTask.is_deleted == 0)

        if keyword:
            like = f"%{keyword}%"
            base = base.where(CrawlerTask.name.ilike(like))
            count_base = count_base.where(CrawlerTask.name.ilike(like))

        # 总数
        total_result = await db.execute(count_base)
        total = total_result.scalar() or 0

        # 分页
        query = (
            base.order_by(desc(CrawlerTask.updated_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(query)
        tasks = result.scalars().all()

        items = []
        for t in tasks:
            items.append(
                CrawlerTaskResponse(
                    id=t.id,
                    name=t.name,
                    request_url=t.request_url,
                    request_method=t.request_method,
                    request_headers=t.request_headers,
                    request_body=t.request_body,
                    parse_rules=t.parse_rules,
                    output_table=t.output_table,
                    schedule_cron=t.schedule_cron,
                    is_enabled=t.is_enabled,
                    created_by=t.created_by,
                    created_at=t.created_at.isoformat() if t.created_at else None,
                    updated_at=t.updated_at.isoformat() if t.updated_at else None,
                )
            )

        return {
            "items": [item.model_dump() for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        }

    async def update_task(
        self, db: AsyncSession, task_id: int, update_data: CrawlerTaskUpdate
    ) -> Optional[CrawlerTaskResponse]:
        """更新爬虫任务（部分更新）"""
        task = await self._get_task_or_none(db, task_id)
        if task is None:
            return None

        changed = update_data.model_dump(exclude_unset=True)
        if not changed:
            return await self.get_task(db, task_id)

        for key, value in changed.items():
            setattr(task, key, value)

        task.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(task)

        return await self.get_task(db, task_id)

    async def delete_task(self, db: AsyncSession, task_id: int) -> bool:
        """软删除爬虫任务"""
        task = await self._get_task_or_none(db, task_id)
        if task is None:
            return False

        task.is_deleted = 1
        task.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return True

    # ==================== CrawlerExecutionLog 查询 ====================

    async def get_logs(
        self,
        db: AsyncSession,
        query: CrawlerExecutionLogQuery,
    ) -> dict:
        """分页查询执行日志"""
        base = select(CrawlerExecutionLog)
        count_base = select(func.count(CrawlerExecutionLog.id))

        if query.task_id:
            base = base.where(CrawlerExecutionLog.task_id == query.task_id)
            count_base = count_base.where(CrawlerExecutionLog.task_id == query.task_id)
        if query.status:
            base = base.where(CrawlerExecutionLog.status == query.status)
            count_base = count_base.where(CrawlerExecutionLog.status == query.status)

        total_result = await db.execute(count_base)
        total = total_result.scalar() or 0

        query_stmt = (
            base.order_by(desc(CrawlerExecutionLog.started_at))
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
        result = await db.execute(query_stmt)
        logs = result.scalars().all()

        items = [
            CrawlerExecutionLogResponse(
                id=log.id,
                task_id=log.task_id,
                status=log.status,
                rows_collected=log.rows_collected,
                rows_inserted=log.rows_inserted,
                error_message=log.error_message,
                started_at=log.started_at.isoformat() if log.started_at else "",
                finished_at=log.finished_at.isoformat() if log.finished_at else None,
                created_at=log.created_at.isoformat() if log.created_at else None,
            )
            for log in logs
        ]

        return {
            "items": [item.model_dump() for item in items],
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
            "total_pages": (total + query.page_size - 1) // query.page_size if query.page_size > 0 else 0,
        }

    # ==================== DataCleanRule CRUD ====================

    async def create_clean_rule(
        self, db: AsyncSession, create: DataCleanRuleCreate
    ) -> DataCleanRuleResponse:
        """创建清洗规则"""
        rule = DataCleanRule(
            name=create.name,
            rule_type=create.rule_type,
            config=create.config,
            target_field=create.target_field,
            sort_order=create.sort_order,
            task_id=create.task_id,
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)

        return DataCleanRuleResponse(
            id=rule.id,
            name=rule.name,
            rule_type=rule.rule_type,
            config=rule.config,
            target_field=rule.target_field,
            sort_order=rule.sort_order,
            task_id=rule.task_id,
        )

    async def get_clean_rule(
        self, db: AsyncSession, rule_id: int
    ) -> Optional[DataCleanRuleResponse]:
        """获取单个清洗规则"""
        stmt = select(DataCleanRule).where(
            DataCleanRule.id == rule_id, DataCleanRule.is_deleted == 0
        )
        result = await db.execute(stmt)
        rule = result.scalar_one_or_none()
        if rule is None:
            return None

        return DataCleanRuleResponse(
            id=rule.id,
            name=rule.name,
            rule_type=rule.rule_type,
            config=rule.config,
            target_field=rule.target_field,
            sort_order=rule.sort_order,
            task_id=rule.task_id,
        )

    async def list_clean_rules(
        self,
        db: AsyncSession,
        task_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """分页查询清洗规则列表"""
        base = select(DataCleanRule).where(DataCleanRule.is_deleted == 0)
        count_base = select(func.count(DataCleanRule.id)).where(DataCleanRule.is_deleted == 0)

        if task_id:
            base = base.where(DataCleanRule.task_id == task_id)
            count_base = count_base.where(DataCleanRule.task_id == task_id)

        total_result = await db.execute(count_base)
        total = total_result.scalar() or 0

        query = (
            base.order_by(DataCleanRule.sort_order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(query)
        rules = result.scalars().all()

        items = [
            DataCleanRuleResponse(
                id=r.id,
                name=r.name,
                rule_type=r.rule_type,
                config=r.config,
                target_field=r.target_field,
                sort_order=r.sort_order,
                task_id=r.task_id,
            )
            for r in rules
        ]

        return {
            "items": [item.model_dump() for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        }

    async def update_clean_rule(
        self, db: AsyncSession, rule_id: int, update_data: DataCleanRuleUpdate
    ) -> Optional[DataCleanRuleResponse]:
        """更新清洗规则"""
        stmt = select(DataCleanRule).where(
            DataCleanRule.id == rule_id, DataCleanRule.is_deleted == 0
        )
        result = await db.execute(stmt)
        rule = result.scalar_one_or_none()
        if rule is None:
            return None

        changed = update_data.model_dump(exclude_unset=True)
        for key, value in changed.items():
            setattr(rule, key, value)

        rule.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(rule)

        return DataCleanRuleResponse(
            id=rule.id,
            name=rule.name,
            rule_type=rule.rule_type,
            config=rule.config,
            target_field=rule.target_field,
            sort_order=rule.sort_order,
            task_id=rule.task_id,
        )

    async def delete_clean_rule(self, db: AsyncSession, rule_id: int) -> bool:
        """软删除清洗规则"""
        stmt = select(DataCleanRule).where(
            DataCleanRule.id == rule_id, DataCleanRule.is_deleted == 0
        )
        result = await db.execute(stmt)
        rule = result.scalar_one_or_none()
        if rule is None:
            return False

        rule.is_deleted = 1
        rule.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return True


# 全局单例
crawler_service = CrawlerService()
