"""Два шага на Claude: (1) достать задачи из каждого источника, (2) свести всё в недельную сводку."""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor

import anthropic

from .models import Digest, Document, ExtractedTask, ExtractionResult

log = logging.getLogger(__name__)

MODEL = "claude-opus-5-5"
# Если модель откажется отвечать по соображениям безопасности, API сам повторит запрос на запасной модели.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
CHUNK_CHARS = 300_000  # ~100k токенов на кусок; длинные чаты режем, ничего не выбрасываем

EXTRACT_SYSTEM = """Ты помогаешь человеку не терять рабочие договорённости.
Тебе дают переписку, транскрипт встречи или таблицу за последнюю неделю.
Выпиши все задачи, поручения, обещания и договорённости «кто-то что-то должен сделать», которые там прозвучали:
- явные («сделай до пятницы», «беру на себя», «нужно подготовить КП»),
- неявные обещания («пришлю завтра», «посмотрю и вернусь»),
- вопросы, на которые ждут ответа от конкретного человека,
- что-то, что обсудили и отметили как сделанное (status = done).
Не выдумывай задачи, которых нет в тексте, и не превращай в задачи болтовню, мемы и общие обсуждения без действия.
Сообщения автора помечены «Я (Имя)» — это владелец сводки.
Если в шапке есть шаблон ссылки на сообщение — подставь номер сообщения и верни ссылку в поле link.
Относительные сроки («завтра», «в пятницу») переводи в даты по дате сообщения.
Пиши по-русски."""

DIGEST_SYSTEM = """Ты собираешь недельную сводку задач для владельца — {me}.
Тебе дают задачи, вытащенные из разных источников (Telegram, YouGile, Google Таблицы, Zoom), и список уже заведённых открытых задач в YouGile.
Сделай из этого один чистый список:
- склей дубли: одна и та же задача из разных чатов/встреч — одна запись, все источники и ссылки собери вместе;
- bucket: mine — делать владельцу (он сам взял или ему поручили); waiting — владелец ждёт от других или поручил кому-то;
  done — закрыто за неделю; no_owner — обсудили, но никто явно не взял;
- in_yougile = true, только если такая задача явно есть в списке YouGile;
- priority high — горящий срок (в ближайшие дни или уже просрочен), просьба руководителя/клиента, блокирует других;
- срок бери самый свежий из договорённостей;
- выкини мусор и то, что явно не является рабочей задачей.
В summary коротко и по-человечески: что главное на следующей неделе, что горит, что может потеряться.
Сегодня {today}. Пиши по-русски."""


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(max_retries=5)


def _call(client: anthropic.Anthropic, system: str, user: str, schema, effort: str):
    resp = client.beta.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=schema,
        output_config={"effort": effort},
        betas=[FALLBACK_BETA],
        fallbacks="default",
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("Модель отказалась обрабатывать этот фрагмент")
    if resp.stop_reason == "max_tokens":
        log.warning("Ответ обрезан по max_tokens — часть задач могла потеряться")
    return resp.parsed_output


def _chunks(doc: Document) -> list[str]:
    text = doc.text
    if len(text) <= CHUNK_CHARS:
        return [text]
    header = text.split("\n", 1)[0]
    lines, parts, cur = text.split("\n")[1:], [], ""
    for line in lines:
        if len(cur) + len(line) > CHUNK_CHARS and cur:
            parts.append(cur)
            cur = ""
        cur += line + "\n"
    if cur:
        parts.append(cur)
    return [f"{header} (часть {i + 1}/{len(parts)})\n{p}" for i, p in enumerate(parts)]


def extract_all(docs: list[Document], workers: int = 4) -> list[tuple[Document, ExtractedTask]]:
    client = _client()
    jobs = [(doc, chunk) for doc in docs for chunk in _chunks(doc)]

    def run(job):
        doc, chunk = job
        try:
            result: ExtractionResult = _call(client, EXTRACT_SYSTEM, chunk, ExtractionResult, "medium")
            log.info("Claude: %s «%s» — задач: %d", doc.source, doc.title, len(result.tasks))
            return [(doc, t) for t in result.tasks]
        except Exception as e:  # один сломанный чат не должен ронять всю сводку
            log.error("Не удалось разобрать %s «%s»: %s", doc.source, doc.title, e)
            return []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return [pair for batch in pool.map(run, jobs) for pair in batch]


def build_digest(found: list[tuple[Document, ExtractedTask]], yougile_open: str, me: str, today: str) -> Digest:
    payload = [
        {"source": f"{doc.source}: {doc.title}", "source_url": doc.url, **task.model_dump()}
        for doc, task in found
    ]
    user = (
        "Задачи из источников (JSON):\n"
        + json.dumps(payload, ensure_ascii=False, indent=1)
        + "\n\nОткрытые задачи, уже заведённые в YouGile:\n"
        + (yougile_open or "(YouGile не подключён)")
    )
    return _call(_client(), DIGEST_SYSTEM.format(me=me, today=today), user, Digest, "high")
