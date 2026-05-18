from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PenpotProject(BaseModel):
    id: str
    name: str
    team_id: str = Field(default="")
    created_at: datetime | None = None
    modified_at: datetime | None = None
    is_default: bool = False


class PenpotProjectList(BaseModel):
    items: list[PenpotProject] = Field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.items)
