from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PenpotFile(BaseModel):
    id: str
    name: str
    project_id: str = Field(default="")
    team_id: str = Field(default="")
    created_at: datetime | None = None
    modified_at: datetime | None = None
    revn: int = 0
    is_shared: bool = False


class PenpotFileList(BaseModel):
    items: list[PenpotFile] = Field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.items)
