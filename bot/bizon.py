"""Отчёт по автовебинарам из Бизона: кто зашёл, сколько смотрел, досмотрел ли, какие кнопки нажал.

Данные берём из кабинета Бизона (те же запросы, что делает страница «Отчёты») по сессии администратора:
BIZON_SID: cookie sid из кабинета (живёт около 30 дней), BIZON_GROUP: номер проекта (102108).
Каждый день в 10:00 МСК бот присылает админам отчёт за вчера; /bizon [ГГГГ-ММ-ДД | сегодня] присылает по запросу.
Зрителей из бота узнаём по метке p1 в ссылке на комнату (avto.web_link добавляет p1=<id в Telegram>).
"""
import asyncio, csv, io, json, logging, os, time
from datetime import datetime, timedelta
from html import escape
from urllib.parse import quote

import aiohttp
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, Message

log = logging.getLogger('bizon')
M = None
router = Router()

SID = os.environ.get('BIZON_SID', '')
GROUP = os.environ.get('BIZON_GROUP', '102108')
SID_EXPIRES = int(os.environ.get('BIZON_SID_EXPIRES', '0') or 0)   # когда истекает сессия (unix-время), чтобы заранее напомнить
BASE = f'https://start.bizon365.ru/admin/report/api/{GROUP}/'
ROOMS = {f'{GROUP}:HlMJLi9E3Mx': 'День 1 · ИИ-агенты', f'{GROUP}:BgOOPkiNnfe': 'День 2 · Контент-завод'}
ROOMS_BY_DAY = {1: f'{GROUP}:HlMJLi9E3Mx', 2: f'{GROUP}:BgOOPkiNnfe'}
FIRST_DAY = datetime(2026, 10, 22)   # первый день автовеба
END_MARGIN = 5 * 60   # досмотрел: был в эфире в последние 5 минут


def init(main_module):
    global M
    M = main_module
    M.db.executescript('''
    CREATE TABLE IF NOT EXISTS bizon_seen(user_id INTEGER, start INTEGER, room TEXT, minutes INTEGER, finished INTEGER,
      PRIMARY KEY(user_id, start, room));
    CREATE TABLE IF NOT EXISTS bizon_done(start INTEGER, room TEXT, PRIMARY KEY(start, room));
    ''')
    M.db.commit()


class Expired(Exception):
    pass


async def get(path, **params):
    url = BASE + path + '?' + '&'.join(f'{k}={quote(str(v), safe="")}' for k, v in params.items())
    async with aiohttp.ClientSession(cookies={'sid': SID}, headers={'User-Agent': 'Mozilla/5.0'}, trust_env=True) as s:
        async with s.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
            txt = await r.text()
    if txt.lstrip().startswith('<'):
        raise Expired()  # вместо данных пришла страница входа: сессия истекла
    return json.loads(txt)


async def sessions(day_from, day_to):
    """Сессии автовебинаров обеих комнат с началом в [day_from, day_to)."""
    out = []
    for room in ROOMS:
        skip = 0
        while True:
            d = await get('getReports', group=GROUP, skip=skip, limit=50, LiveWebinars=0, AutoWebinars=1, search='', room=room, checkReports=1)
            lst = d.get('list') or []
            for r in lst:
                meta = json.loads(r.get('data') or '{}')
                start = datetime.fromtimestamp(meta.get('start', 0) / 1000, M.T.MSK)
                if day_from <= start < day_to:
                    out.append(dict(room=room, start=start, minutes=meta.get('minutes') or 0, webinar=r['webinarId'], peak=r.get('count1', 0)))
            oldest = min((datetime.fromtimestamp(json.loads(r.get('data') or '{}').get('start', 0) / 1000, M.T.MSK) for r in lst), default=None)
            if len(lst) < 50 or (oldest and oldest < day_from):
                break
            skip += 50
    return sorted(out, key=lambda s: (s['start'], list(ROOMS).index(s['room'])))


async def viewers(webinar):
    out, skip = [], 0
    while True:
        d = await get('getReportViewers', group=GROUP, webinarId=webinar, skip=skip, limit=100, devices='')
        v = d.get('viewers') or []
        out += v
        if len(v) < 100:
            return out
        skip += 100


def summarize(v, minutes):
    parts = v.get('vi') or []
    watched = sum(max(0, p.get('e', 0) - p.get('s', 0)) for p in parts)
    last = max((p.get('e', 0) for p in parts), default=0)
    btns = [b.get('id') for b in (v.get('buttons') or []) if b.get('id')] + [b.get('id') for b in (v.get('banners') or []) if b.get('id')]
    return dict(name=v.get('username') or '', phone=v.get('phone') or '', email=v.get('email') or '', city=v.get('city') or '',
                minutes=round(watched / 60), finished=bool(minutes and last >= minutes * 60 - END_MARGIN),
                buttons=btns, uid=(v.get('p1') or '').strip(), mob=bool(v.get('mob')))


async def collect(day_from, day_to):
    """Зрители всех эфиров за период и сами эфиры (в том числе пустые)."""
    rows, sess = [], await sessions(day_from, day_to)
    for s in sess:
        if not s['peak']:
            continue  # в комнату никто не заходил
        for v in await viewers(s['webinar']):
            x = summarize(v, s['minutes'])
            x['session'] = s
            rows.append(x)
    return rows, sess


def remember(rows, sess=()):
    # зрители из бота (метка p1): бот узнаёт, кто был на эфире, и дожимы после эфира становятся точными;
    # bizon_done: по этому эфиру отчёт уже есть, значит кого нет в bizon_seen, тот не заходил
    now = time.time()
    for s in sess:
        if s['start'].timestamp() + s['minutes'] * 60 < now:
            M.q('INSERT OR IGNORE INTO bizon_done VALUES(?,?)', int(s['start'].timestamp()), s['room'])
    for r in rows:
        if r['uid'].isdigit():
            s = r['session']
            M.q('INSERT OR REPLACE INTO bizon_seen VALUES(?,?,?,?,?)', int(r['uid']), int(s['start'].timestamp()), s['room'],
                r['minutes'], int(r['finished']))


def report_text(day_from, rows, sess):
    head = f'📊 <b>Автовеб за {day_from:%d.%m}</b> (Бизон)\n'
    if not sess:
        return head + '\nЭфиров в этот день не было.'
    lines = [head]
    for s in sess:
        rs = [r for r in rows if r['session'] is s]
        fin = sum(r['finished'] for r in rs)
        clk = sum(1 for r in rs if r['buttons'])
        lines.append(f'\n<b>{s["start"]:%H:%M} · {ROOMS.get(s["room"], s["room"])}</b>\n'
                     f'Зашли: <b>{len(rs)}</b> · досмотрели до конца: <b>{fin}</b> · нажали кнопку: <b>{clk}</b>')
        for r in sorted(rs, key=lambda r: -r['minutes'])[:40]:
            contact = ' · '.join(x for x in (r['phone'], r['email']) if x)
            lines.append(f'• {escape(r["name"] or "без имени")}' + (f' ({escape(contact)})' if contact else '')
                         + f' · {r["minutes"]} мин' + (' · ✅ до конца' if r['finished'] else '')
                         + (f' · 🔘 {escape(", ".join(dict.fromkeys(r["buttons"])))}' if r['buttons'] else ''))
    total = len(rows)
    lines.append(f'\n<b>Итого:</b> {total} зрителей, до конца {sum(r["finished"] for r in rows)}, '
                 f'нажали кнопку {sum(1 for r in rows if r["buttons"])}. Полная таблица в файле 👇')
    text = '\n'.join(lines)
    return text if len(text) < 3900 else text[:3800] + '\n…\nПолный список в файле 👇'


def report_csv(rows):
    buf = io.StringIO(); w = csv.writer(buf, delimiter=';')
    w.writerow(['дата', 'время', 'эфир', 'имя', 'телефон', 'почта', 'город', 'минут смотрел', 'досмотрел до конца', 'кнопки', 'id в боте', 'телефон/компьютер'])
    for r in rows:
        s = r['session']
        w.writerow([f'{s["start"]:%d.%m.%Y}', f'{s["start"]:%H:%M}', ROOMS.get(s['room'], s['room']), r['name'], r['phone'], r['email'], r['city'],
                    r['minutes'], 'да' if r['finished'] else 'нет', ', '.join(r['buttons']), r['uid'], 'телефон' if r['mob'] else 'компьютер'])
    return ('﻿' + buf.getvalue()).encode('utf-8')


def period_text(day_from, day_to, rows, sess):
    """Сводка за несколько дней: по дню строка, итог и самые тёплые зрители (досмотрели или нажимали кнопки)."""
    lines = [f'📊 <b>Автовеб с {day_from:%d.%m} по {(day_to - timedelta(days=1)):%d.%m}</b> (Бизон)\n',
             '<b>По дням</b> (зашли · до конца · нажали кнопку)']
    d = day_from
    while d < day_to:
        rs = [r for r in rows if d <= r['session']['start'] < d + timedelta(days=1)]
        if any(d <= s['start'] < d + timedelta(days=1) for s in sess):
            lines.append(f'{d:%d.%m}: {len(rs)} · {sum(r["finished"] for r in rs)} · {sum(1 for r in rs if r["buttons"])}')
        d += timedelta(days=1)
    for day in (1, 2):
        rs = [r for r in rows if r['session']['room'] == ROOMS_BY_DAY[day]]
        lines.append(f'\n<b>{ROOMS[ROOMS_BY_DAY[day]]}</b>: зашли {len(rs)}, до конца {sum(r["finished"] for r in rs)}, '
                     f'нажали кнопку {sum(1 for r in rs if r["buttons"])}')
    hot = sorted([r for r in rows if r['finished'] or r['buttons']], key=lambda r: (-r['finished'], -r['minutes']))
    lines.append(f'\n<b>Итого:</b> {len(rows)} зрителей, до конца {sum(r["finished"] for r in rows)}, '
                 f'нажали кнопку {sum(1 for r in rows if r["buttons"])}.')
    if hot:
        lines.append('\n🔥 <b>Тёплые: досмотрели или нажимали кнопки</b>')
        for r in hot[:30]:
            contact = ' · '.join(x for x in (r['phone'], r['email']) if x)
            lines.append(f'• {r["session"]["start"]:%d.%m %H:%M} {escape(r["name"] or "без имени")}' + (f' ({escape(contact)})' if contact else '')
                         + f' · {r["minutes"]} мин' + (' · ✅' if r['finished'] else '')
                         + (f' · 🔘 {escape(", ".join(dict.fromkeys(r["buttons"])))}' if r['buttons'] else ''))
    lines.append('\nВсе зрители по дням в файле 👇')
    text = '\n'.join(lines)
    return text if len(text) < 3900 else text[:3800] + '\n…\nПолный список в файле 👇'


async def send_report(day_from, chat_ids=None, day_to=None):
    period = day_to is not None
    day_to = day_to or day_from + timedelta(days=1)
    ids = chat_ids or [r['id'] for r in M.q('SELECT id FROM admins').fetchall()]
    try:
        rows, sess = await collect(day_from, day_to)
    except Expired:
        for cid in ids:
            await M.bot.send_message(cid, '⚠️ Сессия Бизона истекла, отчёт по автовебу не собрать. Напиши Claude: «обнови вход в Бизон».')
        return
    except Exception as e:
        log.exception('bizon report')
        for cid in ids:
            await M.bot.send_message(cid, f'⚠️ Не получилось собрать отчёт Бизона: {escape(str(e))[:300]}')
        return
    remember(rows, sess)
    text = period_text(day_from, day_to, rows, sess) if period else report_text(day_from, rows, sess)
    for cid in ids:
        try:
            await M.bot.send_message(cid, text, disable_web_page_preview=True)
            if rows:
                await M.bot.send_document(cid, BufferedInputFile(report_csv(rows), filename=f'avtoveb_{day_from:%Y-%m-%d}' + (f'_{(day_to - timedelta(days=1)):%Y-%m-%d}' if period else '') + '.csv'))
        except Exception as e:
            log.warning('bizon send %s: %s', cid, e)


async def scheduler():
    while True:
        try:
            now = datetime.now(M.T.MSK)
            day = now.strftime('%Y%m%d')
            if SID and not M.setting('bizon_all_v1'):
                M.set_setting('bizon_all_v1', '1')
                await send_report(FIRST_DAY.replace(tzinfo=M.T.MSK), None, now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
            if SID and now.hour == 10 and M.setting('bizon_last') != day:
                M.set_setting('bizon_last', day)
                y = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                await send_report(y)
            # за 3 дня до конца сессии напоминаем, что вход в Бизон пора обновить
            if SID_EXPIRES and SID_EXPIRES - time.time() < 3 * 86400 and now.hour == 11 and M.setting('bizon_warn') != day:
                M.set_setting('bizon_warn', day)
                for r in M.q('SELECT id FROM admins').fetchall():
                    await M.bot.send_message(r['id'], f'⏰ Вход в Бизон для отчёта истекает {datetime.fromtimestamp(SID_EXPIRES, M.T.MSK):%d.%m}. Напиши Claude: «обнови вход в Бизон».')
            # каждые 10 минут подтягиваем свежие отчёты, чтобы бот знал, кто был на только что закончившемся эфире
            if SID and int(time.time()) % 600 < 60:
                today = now.replace(hour=0, minute=0, second=0, microsecond=0)
                try:
                    rows, sess = await collect(today - timedelta(days=1), today + timedelta(days=1))
                    remember(rows, sess)
                    log.info('bizon poll: %s sessions, %s viewers, %s from bot', len(sess), len(rows), sum(1 for r in rows if r['uid'].isdigit()))
                except Expired:
                    log.warning('bizon poll: session expired')
        except Exception:
            log.exception('bizon scheduler')
        await asyncio.sleep(60)


@router.message(Command('bizon'))
async def bizon_cmd(m: Message, command: CommandObject):
    if not M.is_admin(m.from_user.id):
        return
    if not SID:
        return await m.answer('Бизон не подключён: нет BIZON_SID в настройках сервера.')
    arg = (command.args or '').strip().lower()
    now = datetime.now(M.T.MSK).replace(hour=0, minute=0, second=0, microsecond=0)
    if arg in ('все', 'всё', 'all'):
        await m.answer('⏳ Собираю отчёт за все дни автовеба…')
        return await send_report(FIRST_DAY.replace(tzinfo=M.T.MSK), [m.chat.id], now + timedelta(days=1))
    try:
        day = now if arg in ('сегодня', 'today') else (datetime.strptime(arg, '%Y-%m-%d').replace(tzinfo=M.T.MSK) if arg else now - timedelta(days=1))
    except ValueError:
        return await m.answer('Пришли так: /bizon (вчера), /bizon сегодня, /bizon 2026-10-30 или /bizon все')
    await m.answer('⏳ Собираю отчёт из Бизона…')
    await send_report(day, [m.chat.id])
