"""Google Таблицы через сервисный аккаунт (таблицу нужно расшарить на его email)."""
from __future__ import annotations

import json
import logging

import gspread

from ..config import env
from ..models import Document

log = logging.getLogger(__name__)


def client() -> gspread.Client:
    return gspread.service_account_from_dict(json.loads(env("GOOGLE_SERVICE_ACCOUNT_JSON")))


def fetch(cfg: dict) -> list[Document]:
    gc = client()
    max_rows = int(cfg.get("max_rows", 500))
    docs: list[Document] = []
    for item in cfg.get("spreadsheets") or []:
        ss = gc.open_by_key(item["id"]) if "id" in item else gc.open_by_url(item["url"])
        wanted = item.get("worksheets")
        for ws in ss.worksheets():
            if wanted and ws.title not in wanted:
                continue
            rows = ws.get_all_values()[:max_rows]
            rows = [r for r in rows if any(c.strip() for c in r)]
            if not rows:
                continue
            table = "\n".join(" | ".join(c.replace("\n", " ") for c in r) for r in rows)
            note = item.get("note", "")
            docs.append(
                Document(
                    source="sheets",
                    title=f"{ss.title} / {ws.title}",
                    url=ws.url,
                    text=(
                        f"Google Таблица «{ss.title}», лист «{ws.title}» (текущее состояние). {note}\n"
                        f"Ссылка: {ws.url}\n\n{table}"
                    ),
                )
            )
            log.info("Sheets: %s / %s — %d строк", ss.title, ws.title, len(rows))
    return docs


def append_tasks(spreadsheet_id: str, worksheet: str, week_label: str, digest_tasks) -> None:
    gc = client()
    ss = gc.open_by_key(spreadsheet_id)
    try:
        ws = ss.worksheet(worksheet)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(worksheet, rows=1000, cols=9)
        ws.append_row(["Неделя", "Задача", "Детали", "Кто", "Срок", "Категория", "Приоритет", "Источник", "Ссылки"])
    labels = {"mine": "Мне сделать", "waiting": "Жду от других", "done": "Сделано", "no_owner": "Без владельца"}
    ws.append_rows(
        [
            [week_label, t.title, t.details, t.owner or "", t.deadline or "", labels[t.bucket], t.priority,
             "; ".join(t.sources), " ".join(t.links)]
            for t in digest_tasks
        ],
        value_input_option="USER_ENTERED",
    )
