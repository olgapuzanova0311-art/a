"""Telegram: читаем рабочие чаты от имени твоего аккаунта (Telethon, user-сессия).

Бот здесь не подходит: боты не видят личные переписки и чаты, куда их не добавили.
"""
from __future__ import annotations

import logging
from datetime import datetime

from telethon import TelegramClient, utils
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat, User

from ..config import env
from ..models import Document

log = logging.getLogger(__name__)


def make_client() -> TelegramClient:
    return TelegramClient(
        StringSession(env("TG_SESSION")),
        int(env("TG_API_ID")),
        env("TG_API_HASH"),
    )


def _matches(dialog, patterns: list) -> bool:
    for p in patterns:
        if isinstance(p, int) and dialog.id == p:
            return True
        p = str(p).strip()
        username = getattr(dialog.entity, "username", None)
        if p.startswith("@") and username and username.lower() == p[1:].lower():
            return True
        if p.lstrip("-").isdigit() and dialog.id == int(p):
            return True
        if p.lower() == (dialog.name or "").lower():
            return True
    return False


def _link_template(entity) -> str | None:
    username = getattr(entity, "username", None)
    if isinstance(entity, Channel):
        return f"https://t.me/{username}/{{id}}" if username else f"https://t.me/c/{entity.id}/{{id}}"
    return None  # у личных чатов и старых групп публичных ссылок на сообщения нет


def _media_label(msg) -> str:
    if msg.voice:
        return "[голосовое]"
    if msg.video_note:
        return "[кружок]"
    if msg.photo:
        return "[фото]"
    if msg.document:
        name = msg.file.name if msg.file else None
        return f"[файл {name}]" if name else "[файл]"
    return ""


async def fetch(client: TelegramClient, cfg: dict, since: datetime) -> list[Document]:
    explicit = cfg.get("chats") or []
    exclude = cfg.get("exclude") or []
    all_active = cfg.get("all_active", False)
    include_private = cfg.get("include_private", True)
    max_messages = int(cfg.get("max_messages_per_chat", 2000))
    me = await client.get_me()
    my_name = utils.get_display_name(me)

    docs: list[Document] = []
    async for dialog in client.iter_dialogs():
        if dialog.date and dialog.date < since:
            break  # диалоги отсортированы по последнему сообщению — дальше только старые
        entity = dialog.entity
        if _matches(dialog, exclude):
            continue
        if explicit and _matches(dialog, explicit):
            pass
        elif not all_active:
            continue
        elif isinstance(entity, Channel) and entity.broadcast:
            continue  # каналы-ленты пропускаем, там не ставят задачи
        elif isinstance(entity, User) and (entity.bot or not include_private or entity.is_self):
            continue
        elif not isinstance(entity, (User, Chat, Channel)):
            continue

        lines: list[str] = []
        async for msg in client.iter_messages(entity, limit=max_messages):
            if msg.date < since:
                break
            text = (msg.message or "").strip()
            media = _media_label(msg)
            if not text and not media:
                continue
            author = f"Я ({my_name})" if msg.out else (utils.get_display_name(msg.sender) if msg.sender else "?")
            reply = f" (ответ на #{msg.reply_to_msg_id})" if msg.reply_to_msg_id else ""
            lines.append(f"#{msg.id} [{msg.date:%Y-%m-%d %H:%M}] {author}{reply}: {media} {text}".rstrip())
        if not lines:
            continue
        lines.reverse()  # в хронологическом порядке
        template = _link_template(entity)
        header = f"Чат Telegram «{dialog.name}»."
        if template:
            header += f" Ссылка на сообщение #N: {template.format(id='N')}"
        log.info("Telegram: %s — %d сообщений", dialog.name, len(lines))
        docs.append(
            Document(
                source="telegram",
                title=dialog.name,
                text=header + "\n\n" + "\n".join(lines),
                url=template.replace("/{id}", "") if template else None,
            )
        )
    return docs


async def send_digest(client: TelegramClient, target: str, chunks: list[str]) -> None:
    """Отправляет сводку (HTML) в «Избранное» (target='me') или в указанный чат."""
    entity = "me" if target in (None, "", "me") else target
    for chunk in chunks:
        await client.send_message(entity, chunk, parse_mode="html", link_preview=False)
