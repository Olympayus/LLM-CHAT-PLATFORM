"""File Schema (F-FL) — Member F"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class FileResponse(BaseModel):
    id: int
    original_name: str
    file_size: int
    file_type: Optional[str] = None
    category: Optional[str] = None
    created_at: Optional[str] = None
    class Config: from_attributes = True


class FileShareCreate(BaseModel):
    password: Optional[str] = Field(None, max_length=128)
    expire_days: int = Field(7, ge=1, le=30)


class FileShareResponse(BaseModel):
    share_code: str
    expire_at: Optional[str] = None
