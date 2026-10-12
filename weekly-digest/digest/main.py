"""Запуск.

Без ключа Claude API (по умолчанию в GitHub Actions — разбор делает Claude Code по подписке):
    python -m digest.main --collect-only          # скачать переписки в output/sources.txt
    claude -p "$(cat CLAUDE_PROMPT.md)" ...       # Claude Code пишет output/digest.json
    python -m digest.main --deliver output/digest.json

С ключом Claude API (всё одной командой):
    python -m digest.main [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import render
from .config import load_config
from .models import Digest, Document
from .sources import zoom

log = logging.getLogger("digest")


def _notes(cfg: dict, since: datetime) -> list[Document]:
    """Папка с ручными заметками/транскриптами (.txt, .md, .vtt) — для встреч без облачной записи."""
    docs = []
    for p in sorted(Path(cfg["dir"]).glob("**/*")):
        if p.suffix.lower() not in (".txt", ".md", ".vtt") or not p.is_file():
            continue
        if datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc) < since:
            continue
        text = zoom.clean_transcript(p.read_text(encoding="utf-8", errors="replace"))
        docs.append(Document(source="notes", title=p.stem, text=f"Заметки/транскрипт «{p.stem}».\n\n{text}"))
    return docs


async def _collect(cfg: dict, tg_client, since: datetime) -> tuple[list[Document], str, list[str]]:
    errors: list[str] = []
    docs: list[Document] = []
    yougile_open = ""

    async def guard(name: str, awaitable):
        try:
            return await awaitable
        except Exception as e:  # один сломанный источник не должен ронять всю сводку
            log.exception("Источник %s упал", name)
            errors.append(f"{name}: {e}")
            return None

    if (cfg.get("telegram") or {}).get("enabled"):
        from .sources import telegram

        docs += await guard("Telegram", telegram.fetch(tg_client, cfg["telegram"], since)) or []
    if (cfg.get("yougile") or {}).get("enabled"):
        from .sources import yougile

        got = await guard("YouGile", asyncio.to_thread(yougile.fetch, cfg["yougile"], since))
        if got:
            docs += got[0]
            yougile_open = got[1]
    if (cfg.get("sheets") or {}).get("enabled"):
        from .sources import sheets

        docs += await guard("Google Таблицы", asyncio.to_thread(sheets.fetch, cfg["sheets"])) or []
    if (cfg.get("zoom") or {}).get("enabled"):
        docs += await guard("Zoom", asyncio.to_thread(zoom.fetch, cfg["zoom"], since)) or []
    if (cfg.get("notes") or {}).get("enabled"):
        docs += await guard("Заметки", asyncio.to_thread(_notes, cfg["notes"], since)) or []
    log.info("Собрано документов: %d", len(docs))
    return docs, yougile_open, errors


def _write_sources(out_dir: Path, docs: list[Document], yougile_open: str, ctx: dict) -> None:
    parts = []
    for i, d in enumerate(docs, 1):
        head = f"### ИСТОЧНИК {i}: {d.source} — {d.title}"
        if d.url:
            head += f"\nURL: {d.url}"
        parts.append(f"{head}\n{d.text}")
    parts.append("### ОТКРЫТЫЕ ЗАДАЧИ, УЖЕ ЗАВЕДЁННЫЕ В YOUGILE\n" + (yougile_open or "(YouGile не подключён)"))
    (out_dir / "sources.txt").write_text("\n\n".join(parts), encoding="utf-8")
    (out_dir / "context.json").write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Сырые данные сохранены в %s", out_dir / "sources.txt")


async def _deliver(cfg: dict, tg_client, digest: Digest, week: str) -> None:
    deliver_cfg = cfg.get("deliver") or {}
    if deliver_cfg.get("telegram", {}).get("enabled"):
        from .sources import telegram

        await telegram.send_digest(tg_client, deliver_cfg["telegram"].get("to", "me"), render.to_telegram(digest, week))
        log.info("Сводка отправлена в Telegram")
    sh = deliver_cfg.get("sheets") or {}
    if sh.get("enabled"):
        from .sources import sheets

        await asyncio.to_thread(sheets.append_tasks, sh["spreadsheet_id"], sh.get("worksheet", "Задачи"), week, digest.tasks)
        log.info("Задачи дописаны в Google Таблицу")
    yg = deliver_cfg.get("yougile") or {}
    if yg.get("enabled"):
        from .sources import yougile

        n = await asyncio.to_thread(yougile.create_tasks, yg["column_id"], digest.tasks)
        log.info("Заведено задач в YouGile: %d", n)


async def run(args) -> None:
    cfg = load_config(args.config)
    days = args.days or int(cfg.get("days", 7))
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    out_dir = Path(cfg.get("output_dir", "output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    ctx = {
        "me": cfg.get("me", "владелец"),
        "today": now.strftime("%Y-%m-%d"),
        "week": f"{since:%d.%m}–{now:%d.%m.%Y}",
        "errors": [],
    }

    reads = not args.deliver
    sends = not args.collect_only and not args.dry_run
    need_tg = ((cfg.get("telegram") or {}).get("enabled") and reads) or (
        (cfg.get("deliver") or {}).get("telegram", {}).get("enabled") and sends
    )
    tg_client = None
    if need_tg:
        from .sources import telegram

        tg_client = telegram.make_client()
        await tg_client.connect()
        if not await tg_client.is_user_authorized():
            raise RuntimeError("Сессия Telegram недействительна — заново запусти scripts/telegram_login.py")

    try:
        if args.deliver:
            # Сводку уже составил Claude Code — проверяем формат и рассылаем
            ctx_file = out_dir / "context.json"
            if ctx_file.exists():
                ctx = json.loads(ctx_file.read_text(encoding="utf-8"))
            digest = Digest.model_validate_json(Path(args.deliver).read_text(encoding="utf-8"))
        else:
            docs, yougile_open, ctx["errors"] = await _collect(cfg, tg_client, since)
            if args.collect_only:
                _write_sources(out_dir, docs, yougile_open, ctx)
                return
            from . import extract  # нужен только режиму с ключом API

            found = await asyncio.to_thread(extract.extract_all, docs)
            log.info("Найдено задач до склейки: %d", len(found))
            digest = await asyncio.to_thread(extract.build_digest, found, yougile_open, ctx["me"], ctx["today"])

        if ctx.get("errors"):
            digest.summary += "\n\n⚠️ Не удалось прочитать: " + "; ".join(ctx["errors"])
        md = render.to_markdown(digest, ctx["week"])
        (out_dir / f"{ctx['today']}.md").write_text(md, encoding="utf-8")
        if not args.deliver:
            (out_dir / f"{ctx['today']}.json").write_text(
                json.dumps(digest.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
            )
        log.info("Сводка сохранена в %s", out_dir / f"{ctx['today']}.md")
        if args.dry_run:
            print(md)
            return
        await _deliver(cfg, tg_client, digest, ctx["week"])
    finally:
        if tg_client:
            await tg_client.disconnect()


def cli() -> None:
    p = argparse.ArgumentParser(description="Недельная сводка задач")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--days", type=int, help="За сколько дней собирать (по умолчанию из конфига, обычно 7)")
    p.add_argument("--dry-run", action="store_true", help="Показать сводку на экране, никуда не отправлять")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--collect-only", action="store_true", help="Только скачать данные в output/sources.txt")
    mode.add_argument("--deliver", metavar="DIGEST_JSON", help="Разослать готовую сводку (её пишет Claude Code)")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run(args))


if __name__ == "__main__":
    cli()
