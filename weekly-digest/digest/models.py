from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from pydantic import BaseModel, Field


@dataclass
class Document:
    """Кусок переписки/встречи/таблицы, из которого Claude достаёт задачи."""

    source: str  # "telegram" | "yougile" | "sheets" | "zoom"
    title: str  # название чата, задачи, встречи или листа
    text: str
    url: Optional[str] = None
    meta: dict = field(default_factory=dict)


Status = Literal["new", "in_progress", "done", "blocked", "unclear"]


class ExtractedTask(BaseModel):
    title: str = Field(description="Короткая формулировка задачи, начинается с глагола")
    details: str = Field(description="Контекст: что именно нужно сделать, 1-3 предложения")
    owner: Optional[str] = Field(description="Кто должен сделать (имя как в переписке), null если непонятно")
    requested_by: Optional[str] = Field(description="Кто поставил/попросил, null если непонятно")
    deadline: Optional[str] = Field(description="Срок в формате YYYY-MM-DD, null если не назван")
    status: Status
    quote: str = Field(description="Дословная короткая цитата из источника, где это обсуждалось")
    discussed_at: Optional[str] = Field(description="Дата обсуждения YYYY-MM-DD, если видна")
    link: Optional[str] = Field(description="Ссылка на сообщение/задачу, если есть в тексте")


class ExtractionResult(BaseModel):
    tasks: list[ExtractedTask]


Bucket = Literal[
    "mine",  # мне надо сделать
    "waiting",  # жду от других / делегировано
    "done",  # закрыто за неделю
    "no_owner",  # обсудили, но никто не взял
]


class DigestTask(BaseModel):
    title: str
    details: str
    owner: Optional[str]
    deadline: Optional[str] = Field(description="YYYY-MM-DD или null")
    bucket: Bucket
    priority: Literal["high", "normal", "low"]
    in_yougile: bool = Field(description="true, если такая задача уже заведена в YouGile")
    sources: list[str] = Field(description="Откуда: 'Telegram: Название чата', 'Zoom: Тема встречи' и т.п.")
    links: list[str] = Field(description="Ссылки на сообщения/задачи/записи, если есть")


class Digest(BaseModel):
    summary: str = Field(description="3-6 предложений: главное за неделю, что горит, на что обратить внимание")
    tasks: list[DigestTask]
