from __future__ import annotations

from html import escape

from .models import Digest, DigestTask

SECTIONS = [
    ("mine", "🔥 Мне сделать"),
    ("waiting", "⏳ Жду от других"),
    ("no_owner", "❓ Обсудили, но никто не взял"),
    ("done", "✅ Сделано за неделю"),
]
PRIO = {"high": 0, "normal": 1, "low": 2}


def _sorted(tasks: list[DigestTask]) -> list[DigestTask]:
    return sorted(tasks, key=lambda t: (PRIO[t.priority], t.deadline or "9999"))


def to_markdown(d: Digest, week: str) -> str:
    out = [f"# Задачи за неделю {week}", "", d.summary, ""]
    for bucket, title in SECTIONS:
        items = _sorted([t for t in d.tasks if t.bucket == bucket])
        if not items:
            continue
        out += [f"## {title} ({len(items)})", ""]
        for t in items:
            meta = [x for x in [t.owner, f"до {t.deadline}" if t.deadline else None,
                                "уже в YouGile" if t.in_yougile else None] if x]
            mark = "❗ " if t.priority == "high" else ""
            out.append(f"- {mark}**{t.title}**" + (f" — {', '.join(meta)}" if meta else ""))
            out.append(f"  {t.details}")
            src = "; ".join(t.sources)
            links = " ".join(f"[ссылка]({u})" for u in t.links)
            out.append(f"  _{src}_ {links}".rstrip())
        out.append("")
    return "\n".join(out)


def to_telegram(d: Digest, week: str, limit: int = 4000) -> list[str]:
    """HTML для Telegram, порезанный на сообщения до 4096 символов."""
    blocks = [f"<b>📋 Задачи за неделю {escape(week)}</b>\n\n{escape(d.summary)}"]
    for bucket, title in SECTIONS:
        items = _sorted([t for t in d.tasks if t.bucket == bucket])
        if not items:
            continue
        blocks.append(f"\n<b>{title} ({len(items)})</b>")
        for t in items:
            mark = "❗ " if t.priority == "high" else ""
            meta = [x for x in [t.owner, f"до {t.deadline}" if t.deadline else None,
                                "в YouGile" if t.in_yougile else None] if x]
            line = f"• {mark}<b>{escape(t.title)}</b>"
            if meta:
                line += f" — {escape(', '.join(meta))}"
            line += f"\n  <i>{escape('; '.join(t.sources))}</i>"
            if t.links:
                line += " " + " ".join(f'<a href="{escape(u, quote=True)}">↗</a>' for u in t.links[:3])
            blocks.append(line)

    chunks, cur = [], ""
    for b in blocks:
        if len(cur) + len(b) + 1 > limit and cur:
            chunks.append(cur)
            cur = ""
        cur += b + "\n"
    if cur:
        chunks.append(cur)
    return chunks
