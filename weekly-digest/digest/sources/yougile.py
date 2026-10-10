"""YouGile REST API v2: задачи, чаты задач и групповые чаты.

Документация: https://ru.yougile.com/api-v2
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from ..config import env
from ..models import Document

log = logging.getLogger(__name__)

BASE = "https://ru.yougile.com/api-v2"


class YouGile:
    def __init__(self) -> None:
        self.http = httpx.Client(
            base_url=BASE,
            headers={"Authorization": f"Bearer {env('YOUGILE_API_KEY')}"},
            timeout=60,
        )

    def _list(self, path: str, **params) -> list[dict]:
        items, offset = [], 0
        while True:
            r = self.http.get(path, params={"limit": 1000, "offset": offset, **params})
            r.raise_for_status()
            data = r.json()
            items += data.get("content", [])
            paging = data.get("paging") or {}
            if not paging.get("next"):
                return items
            offset += paging.get("limit", 1000)

    def users(self) -> dict[str, str]:
        return {u["id"]: u.get("realName") or u.get("email") or u["id"] for u in self._list("/users")}

    def columns(self) -> dict[str, dict]:
        return {c["id"]: c for c in self._list("/columns")}

    def boards(self) -> dict[str, dict]:
        return {b["id"]: b for b in self._list("/boards")}

    def tasks(self) -> list[dict]:
        return self._list("/tasks")

    def group_chats(self) -> list[dict]:
        return self._list("/group-chats")

    def messages(self, chat_id: str, since_ms: int) -> list[dict]:
        try:
            return self._list(f"/chats/{chat_id}/messages", since=since_ms)
        except httpx.HTTPStatusError as e:
            log.warning("YouGile: не удалось прочитать чат %s: %s", chat_id, e.response.status_code)
            return []

    def create_task(self, column_id: str, title: str, description: str, deadline_ms: int | None) -> str:
        body: dict = {"title": title, "columnId": column_id, "description": description}
        if deadline_ms:
            body["deadline"] = {"deadline": deadline_ms}
        r = self.http.post("/tasks", json=body)
        r.raise_for_status()
        return r.json()["id"]


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _fmt_ms(ms: int | None) -> str:
    if not ms:
        return ""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def fetch(cfg: dict, since: datetime) -> tuple[list[Document], str]:
    """Возвращает (документы с обсуждениями за неделю, список уже заведённых открытых задач)."""
    yg = YouGile()
    since_ms = _ms(since)
    users = yg.users()
    columns = yg.columns()
    boards = yg.boards()
    board_filter = {b.lower() for b in cfg.get("boards") or []}

    def board_name(task: dict) -> str:
        col = columns.get(task.get("columnId") or "", {})
        return boards.get(col.get("boardId") or "", {}).get("title", "")

    def column_name(task: dict) -> str:
        return columns.get(task.get("columnId") or "", {}).get("title", "")

    tasks = [t for t in yg.tasks() if not t.get("archived") and not t.get("deleted")]
    if board_filter:
        tasks = [t for t in tasks if board_name(t).lower() in board_filter]

    # Список открытых задач — чтобы Claude отметил, что уже заведено, и не дублировал.
    open_lines = []
    for t in tasks:
        if t.get("completed"):
            continue
        who = ", ".join(users.get(u, u) for u in t.get("assigned") or [])
        dl = _fmt_ms((t.get("deadline") or {}).get("deadline"))
        open_lines.append(
            f"- {t.get('title')} | доска: {board_name(t)} / {column_name(t)}"
            + (f" | исполнитель: {who}" if who else "")
            + (f" | срок: {dl}" if dl else "")
        )

    docs: list[Document] = []
    max_task_chats = int(cfg.get("max_task_chats", 300))
    # Чаты задач: смотрим созданные/изменённые недавно и открытые (у задачи chatId == id задачи).
    candidates = [t for t in tasks if not t.get("completed") or (t.get("timestamp") or 0) >= since_ms]
    candidates.sort(key=lambda t: t.get("timestamp") or 0, reverse=True)
    for t in candidates[:max_task_chats]:
        msgs = [m for m in yg.messages(t["id"], since_ms) if not m.get("deleted")]
        created_now = (t.get("timestamp") or 0) >= since_ms
        if not msgs and not created_now:
            continue
        lines = [
            f"Задача YouGile «{t.get('title')}» (доска {board_name(t)} / колонка {column_name(t)}, "
            f"{'выполнена' if t.get('completed') else 'открыта'}"
            f"{', создана на этой неделе' if created_now else ''})."
        ]
        if t.get("description"):
            lines.append(f"Описание: {t['description'][:3000]}")
        for m in msgs:
            lines.append(f"[{_fmt_ms(m.get('id'))}] {users.get(m.get('fromUserId'), '?')}: {m.get('text', '')}")
        docs.append(Document(source="yougile", title=t.get("title", ""), text="\n".join(lines)))

    for chat in yg.group_chats():
        if chat.get("deleted"):
            continue
        msgs = [m for m in yg.messages(chat["id"], since_ms) if not m.get("deleted")]
        if not msgs:
            continue
        lines = [f"Групповой чат YouGile «{chat.get('title')}»."]
        lines += [f"[{_fmt_ms(m.get('id'))}] {users.get(m.get('fromUserId'), '?')}: {m.get('text', '')}" for m in msgs]
        docs.append(Document(source="yougile", title=chat.get("title", ""), text="\n".join(lines)))

    log.info("YouGile: %d обсуждений, %d открытых задач", len(docs), len(open_lines))
    return docs, "\n".join(open_lines)


def create_tasks(column_id: str, digest_tasks) -> int:
    yg = YouGile()
    created = 0
    for t in digest_tasks:
        if t.in_yougile or t.bucket not in ("mine", "no_owner"):
            continue
        deadline_ms = None
        if t.deadline:
            try:
                deadline_ms = _ms(datetime.fromisoformat(t.deadline).replace(tzinfo=timezone.utc))
            except ValueError:
                pass
        desc = t.details + ("\n\nИсточник: " + "; ".join(t.sources) if t.sources else "")
        desc += "".join(f"\n{link}" for link in t.links)
        yg.create_task(column_id, t.title, desc, deadline_ms)
        created += 1
    return created
