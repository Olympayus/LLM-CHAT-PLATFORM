"""System config schema (F-SC) — Member F"""

from typing import Optional
from pydantic import BaseModel, Field


class SysConfigUpdate(BaseModel):
    config_key: str = Field(..., max_length=128)
    config_value: str
    category: str = Field(..., max_length=64)
    description: Optional[str] = Field(None, max_length=256)


class SysConfigResponse(BaseModel):
    config_key: str
    config_value: str
    category: str
    description: Optional[str] = None
    class Config: from_attributes = True


class SiteInfoResponse(BaseModel):
    site_name: str = "LLM Platform"
    logo_url: Optional[str] = None
    icp_number: Optional[str] = None
