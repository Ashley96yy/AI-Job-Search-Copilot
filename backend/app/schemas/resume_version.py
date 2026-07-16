from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ResumeVersionBase(BaseModel):
    name: str
    target_role: Optional[str] = None
    resume_text: str
    notes: Optional[str] = None


class ResumeVersionUpsert(ResumeVersionBase):
    pass


class ResumeVersionRead(ResumeVersionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
