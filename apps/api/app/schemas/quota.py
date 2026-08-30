"""Privacy-minimal anonymous usage response contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class UsageAllowanceResponse(BaseModel):
    category: Literal["analysis", "index", "question"]
    limit: int
    remaining: int
    retry_at: datetime | None


class UsageResponse(BaseModel):
    enforced: bool
    allowances: list[UsageAllowanceResponse]
