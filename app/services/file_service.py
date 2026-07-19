"""File service (F-FL) — Member F"""

import os
import hashlib
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.file_record import FileRecord, FileShare


class FileService:
    UPLOAD_DIR = "uploads"
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_files(self, upload_by: int, category: Optional[str] = None,
                        page: int = 1, page_size: int = 20):
        """List user files with pagination"""
        q = select(FileRecord).where(FileRecord.upload_by == upload_by, FileRecord.is_deleted == 0)
        if category:
            q = q.where(FileRecord.category == category)
        q = q.order_by(FileRecord.created_at.desc())
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        result = await self.db.execute(q.offset((page-1)*page_size).limit(page_size))
        return result.scalars().all(), total

    async def save_file(self, filename: str, content: bytes, content_type: str,
                        upload_by: int) -> FileRecord:
        """Save uploaded file to disk and create DB record"""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        date_path = datetime.now().strftime("%Y/%m/%d")
        full_path = os.path.join(self.UPLOAD_DIR, date_path)
        os.makedirs(full_path, exist_ok=True)

        stored_name = f"{uuid.uuid4().hex}.{ext}"
        with open(os.path.join(full_path, stored_name), "wb") as f:
            f.write(content)

        category = self._guess_category(ext)
        file_record = FileRecord(
            original_name=filename, stored_name=stored_name,
            file_path=os.path.join(date_path, stored_name),
            file_size=len(content), file_type=content_type,
            category=category, md5=hashlib.md5(content).hexdigest(),
            upload_by=upload_by,
        )
        self.db.add(file_record)
        await self.db.flush()
        return file_record

    async def get_file(self, file_id: int) -> Optional[FileRecord]:
        result = await self.db.execute(
            select(FileRecord).where(FileRecord.id == file_id, FileRecord.is_deleted == 0))
        return result.scalar_one_or_none()

    async def delete_file(self, file_id: int) -> bool:
        f = await self.get_file(file_id)
        if not f: return False
        f.is_deleted = 1
        await self.db.flush()
        return True

    async def create_share(self, file_id: int, created_by: int, password: Optional[str] = None,
                           expire_days: int = 7) -> Optional[FileShare]:
        f = await self.get_file(file_id)
        if not f: return None
        share = FileShare(
            file_id=file_id, share_code=uuid.uuid4().hex[:12],
            password=password, expire_at=datetime.now(),
            created_by=created_by,
        )
        self.db.add(share)
        await self.db.flush()
        return share

    def _guess_category(self, ext: str) -> str:
        if ext in ("jpg","jpeg","png","gif","bmp","webp","svg"): return "image"
        if ext in ("pdf","doc","docx","xls","xlsx","ppt","pptx","txt","csv"): return "document"
        if ext in ("py","js","ts","jsx","tsx","vue","java","go","rs"): return "code"
        return "other"
