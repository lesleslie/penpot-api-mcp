from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PenpotObject(BaseModel):
    id: str
    name: str
    type: str = ""
    parent_id: str | None = None
    frame_id: str | None = None
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None
    children: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PenpotObjectTree(BaseModel):
    file_id: str
    objects: dict[str, PenpotObject] = Field(default_factory=dict)

    def search(self, query: str) -> list[PenpotObject]:
        q = query.lower()
        return [
            obj for obj in self.objects.values()
            if q in obj.name.lower() or q in obj.type.lower()
        ]
