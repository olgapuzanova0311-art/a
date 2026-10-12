"""Zoom: транскрипты облачных записей и (если есть) саммари AI Companion.

Нужно Server-to-Server OAuth приложение в Zoom Marketplace и включённые
облачная запись + «Audio transcript» в настройках Zoom (платный тариф).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx

from ..config import env
from ..models import Document

log = logging.getLogger(__name__)

API = "https://api.zoom.us/v2"


def _token() -> str:
    r = httpx.post(
        "https://zoom.us/oauth/token",
        params={"grant_type": "account_credentials", "account_id": env("ZOOM_ACCOUNT_ID")},
        auth=(env("ZOOM_CLIENT_ID"), env("ZOOM_CLIENT_SECRET")),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _vtt_to_text(vtt: str) -> str:
    """WEBVTT → «Спикер: реплика», склеивая подряд идущие реплики одного человека."""
    out: list[str] = []
    for line in vtt.splitlines():
        line = line.strip()
        if not line or line == "WEBVTT" or line.isdigit() or "-->" in line:
            continue
        speaker, _, text = line.partition(": ")
        if not text:
            speaker, text = "", line
        if out and speaker and out[-1].startswith(speaker + ": "):
            out[-1] += " " + text
        else:
            out.append(f"{speaker}: {text}" if speaker else text)
    return "\n".join(out)


def _uuid_path(uuid: str) -> str:
    # UUID, начинающиеся с «/» или содержащие «//», Zoom требует кодировать дважды
    return quote(quote(uuid, safe=""), safe="") if uuid.startswith("/") or "//" in uuid else quote(uuid, safe="")


def fetch(cfg: dict, since: datetime) -> list[Document]:
    token = _token()
    http = httpx.Client(headers={"Authorization": f"Bearer {token}"}, timeout=120, follow_redirects=True)
    user = cfg.get("user", "me")
    now = datetime.now(timezone.utc)
    r = http.get(
        f"{API}/users/{quote(user)}/recordings",
        params={"from": (since - timedelta(days=1)).strftime("%Y-%m-%d"), "to": now.strftime("%Y-%m-%d"), "page_size": 300},
    )
    r.raise_for_status()
    docs: list[Document] = []
    for meeting in r.json().get("meetings", []):
        start = meeting.get("start_time", "")
        try:
            if datetime.fromisoformat(start.replace("Z", "+00:00")) < since:
                continue
        except ValueError:
            pass
        topic = meeting.get("topic", "Встреча")
        parts: list[str] = []

        if cfg.get("use_ai_summary", True):
            s = http.get(f"{API}/meetings/{_uuid_path(meeting['uuid'])}/meeting_summary")
            if s.status_code == 200:
                data = s.json()
                summary = data.get("summary_overview") or ""
                for d in data.get("summary_details") or []:
                    summary += f"\n{d.get('label', '')}: {d.get('summary', '')}"
                steps = data.get("next_steps") or []
                if steps:
                    summary += "\nNext steps:\n" + "\n".join(f"- {x}" for x in steps)
                if summary.strip():
                    parts.append("Саммари Zoom AI Companion:\n" + summary.strip())

        for f in meeting.get("recording_files", []):
            if f.get("file_type") == "TRANSCRIPT" and f.get("download_url"):
                t = http.get(f["download_url"])
                if t.status_code == 200:
                    parts.append("Транскрипт:\n" + _vtt_to_text(t.text))
                break

        if not parts:
            log.info("Zoom: «%s» — нет транскрипта и саммари, пропускаю", topic)
            continue
        log.info("Zoom: «%s» (%s)", topic, start)
        docs.append(
            Document(
                source="zoom",
                title=f"{topic} ({start[:10]})",
                url=meeting.get("share_url"),
                text=f"Встреча Zoom «{topic}», {start}.\n\n" + "\n\n".join(parts),
            )
        )
    return docs


# Транскрипт может прийти и вручную (например, из другого сервиса) — общий помощник для main.py
def clean_transcript(text: str) -> str:
    return _vtt_to_text(text) if text.lstrip().startswith("WEBVTT") else re.sub(r"\n{3,}", "\n\n", text)
