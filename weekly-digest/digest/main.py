"""Запуск: python -m digest.main [--config config.yaml] [--days 7] [--dry-run] [--collect-only]"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import extract, render
from .config import load_config
from .models import Document
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


async def run(args) -> None:
    cfg = load_config(args.config)
    days = args.days or int(cfg.get("days", 7))
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    week = f"{since:%d.%m}–{now:%d.%m.%Y}"
    me = cfg.get("me", "владелец")
    errors: list[str] = []
    docs: list[Document] = []
    yougile_open = ""

    tg_cfg = cfg.get("telegram") or {}
    deliver_cfg = cfg.get("deliver") or {}
    need_tg = tg_cfg.get("enabled") or (deliver_cfg.get("telegram", {}).get("enabled") and not args.dry_run)
    tg_client = None
    if need_tg:
        from .sources import telegram

        tg_client = telegram.make_client()
        await tg_client.connect()
        if not await tg_client.is_user_authorized():
            raise RuntimeError("Сессия Telegram недействительна — заново запусти scripts/telegram_login.py")

    async def collect(name: str, awaitable):
        try:
            return await awaitable
        except Exception as e:
            log.exception("Источник %s упал", name)
            errors.append(f"{name}: {e}")
            return None

    try:
        if tg_cfg.get("enabled"):
            from .sources import telegram

            got = await collect("Telegram", telegram.fetch(tg_client, tg_cfg, since))
            docs += got or []
        if (cfg.get("yougile") or {}).get("enabled"):
            from .sources import yougile

            got = await collect("YouGile", asyncio.to_thread(yougile.fetch, cfg["yougile"], since))
            if got:
                docs += got[0]
                yougile_open = got[1]
        if (cfg.get("sheets") or {}).get("enabled"):
            from .sources import sheets

            docs += await collect("Google Таблицы", asyncio.to_thread(sheets.fetch, cfg["sheets"])) or []
        if (cfg.get("zoom") or {}).get("enabled"):
            docs += await collect("Zoom", asyncio.to_thread(zoom.fetch, cfg["zoom"], since)) or []
        if (cfg.get("notes") or {}).get("enabled"):
            docs += await collect("Заметки", asyncio.to_thread(_notes, cfg["notes"], since)) or []

        log.info("Собрано документов: %d", len(docs))
        out_dir = Path(cfg.get("output_dir", "output"))
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = now.strftime("%Y-%m-%d")

        if args.collect_only:
            dump = out_dir / f"{stamp}-sources.txt"
            dump.write_text("\n\n=====\n\n".join(f"[{d.source}] {d.title}\n{d.text}" for d in docs), encoding="utf-8")
            log.info("Сырые данные сохранены в %s (Claude не вызывался)", dump)
            return

        found = await asyncio.to_thread(extract.extract_all, docs)
        log.info("Найдено задач до склейки: %d", len(found))
        digest = await asyncio.to_thread(extract.build_digest, found, yougile_open, me, now.strftime("%Y-%m-%d"))
        if errors:
            digest.summary += "\n\n⚠️ Не удалось прочитать: " + "; ".join(errors)

        md = render.to_markdown(digest, week)
        (out_dir / f"{stamp}.md").write_text(md, encoding="utf-8")
        (out_dir / f"{stamp}.json").write_text(
            json.dumps(digest.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        log.info("Сводка сохранена в %s", out_dir / f"{stamp}.md")
        if args.dry_run:
            print(md)
            return

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
    finally:
        if tg_client:
            await tg_client.disconnect()


def cli() -> None:
    p = argparse.ArgumentParser(description="Недельная сводка задач")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--days", type=int, help="За сколько дней собирать (по умолчанию из конфига, обычно 7)")
    p.add_argument("--dry-run", action="store_true", help="Собрать и показать сводку, никуда не отправлять")
    p.add_argument("--collect-only", action="store_true", help="Только скачать данные, без Claude — проверить доступы")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run(args))


if __name__ == "__main__":
    cli()
