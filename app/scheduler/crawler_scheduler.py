# crawler_scheduler.py - 爬虫定时调度器
import json
from typing import Optional

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.crawler import CrawlerTask
from app.services.crawler_service import crawler_service


class CrawlerScheduler:
    """爬虫定时任务调度器"""

    def __init__(self):
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._job_prefix = "crawler_task_"

    @property
    def scheduler(self) -> AsyncIOScheduler:
        if self._scheduler is None:
            raise RuntimeError("Scheduler not initialized")
        return self._scheduler

    async def init(self) -> None:
        if self._scheduler is not None:
            logger.warning("Scheduler already initialized")
            return

        # 使用 config 中预定义的同步连接串（PyMySQL SSL 统一由 settings 控制）
        sync_db_url = settings.DATABASE_URL_SYNC

        jobstores = {"default": SQLAlchemyJobStore(
            url=sync_db_url,
            engine_options={"connect_args": settings.pymysql_connect_args}
        )}
        executors = {"default": AsyncIOExecutor()}
        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 300},
        )
        self._scheduler.start()
        logger.success("APScheduler with SQLAlchemyJobStore started")

    async def shutdown(self) -> None:
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
            logger.info("APScheduler shutdown")

    async def load_all_from_db(self, db: AsyncSession) -> int:
        stmt = select(CrawlerTask).where(
            CrawlerTask.is_deleted == 0,
            CrawlerTask.is_enabled == 1,
            CrawlerTask.schedule_cron.isnot(None),
            CrawlerTask.schedule_cron != "",
        )
        result = await db.execute(stmt)
        tasks = result.scalars().all()
        count = 0
        for task in tasks:
            try:
                self.add_job(task.id, task.schedule_cron, task.name)
                count += 1
                logger.info(f"Loaded task: {task.id} {task.name}")
            except Exception as e:
                logger.error(f"Failed to load task {task.id}: {e}")
        logger.success(f"Loaded {count} crawler tasks")
        return count

    def _job_id(self, task_id: int) -> str:
        return f"{self._job_prefix}{task_id}"

    async def _execute_task(self, task_id: int) -> None:
        from app.core.database import async_session_factory
        logger.info(f"Scheduled task triggered: {task_id}")
        async with async_session_factory() as db:
            try:
                result = await crawler_service.execute_task(task_id, db)
                if result.status == "success":
                    logger.success(f"Task done: {task_id} collected={result.rows_collected}")
                else:
                    logger.error(f"Task failed: {task_id} {result.error_message}")
            except Exception as e:
                logger.error(f"Task error: {task_id} {e}")
                await db.rollback()

    def add_job(self, task_id: int, cron_expr: str, name: str = "") -> str:
        job_id = self._job_id(task_id)
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron: {cron_expr}")
        trigger = CronTrigger(
            minute=parts[0], hour=parts[1], day=parts[2],
            month=parts[3], day_of_week=parts[4],
        )
        self._scheduler.add_job(
            self._execute_task, trigger=trigger, id=job_id,
            args=[task_id], name=name or f"crawler-{task_id}", replace_existing=True,
        )
        logger.info(f"Job registered: {job_id} cron={cron_expr}")
        return job_id

    def remove_job(self, task_id: int) -> bool:
        job_id = self._job_id(task_id)
        try:
            self._scheduler.remove_job(job_id)
            logger.info(f"Job removed: {job_id}")
            return True
        except Exception:
            return False

    def pause_job(self, task_id: int) -> bool:
        job_id = self._job_id(task_id)
        job = self._scheduler.get_job(job_id)
        if job is None:
            return False
        self._scheduler.pause_job(job_id)
        logger.info(f"Job paused: {job_id}")
        return True

    def resume_job(self, task_id: int) -> bool:
        job_id = self._job_id(task_id)
        job = self._scheduler.get_job(job_id)
        if job is None:
            return False
        self._scheduler.resume_job(job_id)
        logger.info(f"Job resumed: {job_id}")
        return True

    def list_jobs(self) -> list[dict]:
        jobs = self._scheduler.get_jobs()
        result = []
        for job in jobs:
            nxt = str(job.next_run_time) if job.next_run_time else None
            trg = str(job.trigger)
            result.append({"job_id": job.id, "name": job.name, "next_run_time": nxt, "trigger": trg})
        return result

    async def refresh_task(self, db: AsyncSession, task_id: int) -> None:
        stmt = select(CrawlerTask).where(
            CrawlerTask.id == task_id, CrawlerTask.is_deleted == 0
        )
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()
        if task and task.is_enabled == 1 and task.schedule_cron:
            self.add_job(task.id, task.schedule_cron, task.name)
        else:
            self.remove_job(task_id)


crawler_scheduler = CrawlerScheduler()