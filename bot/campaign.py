"""Разовые рассылки с картинкой и именем. Сначала STAGE='test' (только TEST_USERNAMES), после «ок» Ольги STAGE='all'.
Каждое сообщение уходит человеку один раз (отметка в sent / max_sent), поэтому перезапуск бота ничего не дублирует.
"""
import asyncio, html, logging, time

from aiohttp import web
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message

log = logging.getLogger('campaign')
router = Router()
M_ = None

# Клики: кнопка ведёт на свой домен (agent.olgapuzanovva.ru/c/<рассылка>/<id>, открывается в России без VPN),
# сайт пересылает запрос боту (docs/Caddyfile.template), бот записывает клик и сразу перекидывает на нужную ссылку.
TRACK_BASE = 'https://agent.olgapuzanovva.ru/c'


def track_url(key, uid, link):
    if not M_:
        return link
    M_.q('INSERT OR REPLACE INTO campaign_links(key, url) VALUES(?,?)', key, link)
    return f'{TRACK_BASE}/{key}/{uid}'


async def click(req):
    key, uid = req.match_info['key'], req.match_info['uid'][:24]
    try:
        r = M_.q('SELECT url FROM campaign_links WHERE key=?', key).fetchone() if M_ else None
    except Exception:
        log.exception('click link')
        r = None
    if not r:
        raise web.HTTPFound('https://t.me/aivwb')
    now = int(time.time())
    try:  # клик считаем, но человек уходит по ссылке в любом случае
        M_.q('INSERT INTO btn_clicks(key, uid, first, last, n) VALUES(?,?,?,?,1) '
             'ON CONFLICT(key, uid) DO UPDATE SET last=excluded.last, n=n+1', key, uid, now, now)
    except Exception:
        log.exception('click')
    raise web.HTTPFound(r['url'])


def setup_web(app, main_module):
    global M_
    M_ = main_module
    M_.db.executescript('''
    CREATE TABLE IF NOT EXISTS campaign_links(key TEXT PRIMARY KEY, url TEXT);
    CREATE TABLE IF NOT EXISTS btn_clicks(key TEXT, uid TEXT, first INTEGER, last INTEGER, n INTEGER, PRIMARY KEY(key, uid));
    ''')
    M_.db.commit()
    app.router.add_get('/c/{key}/{uid}', click)


def clicks_text():
    rows = M_.q('SELECT key, url FROM campaign_links ORDER BY rowid DESC LIMIT 15').fetchall()
    if not rows:
        return 'Кликов пока нет: счёт идёт с рассылок, отправленных после 24.11.'
    out = ['👆 Клики по кнопкам рассылок (уникальные люди)\n']
    for r in rows:
        k = r['key']
        tg = M_.q("SELECT COUNT(*) FROM sent WHERE key=?", k + ':all').fetchone()[0]
        mx = M_.MX.q("SELECT COUNT(*) FROM max_sent WHERE key=?", k + ':all').fetchone()[0] if M_.MX else 0
        ct = M_.q("SELECT COUNT(*) FROM btn_clicks WHERE key=? AND uid NOT LIKE 'm%'", k).fetchone()[0]
        cm = M_.q("SELECT COUNT(*) FROM btn_clicks WHERE key=? AND uid LIKE 'm%'", k).fetchone()[0]
        sent = tg + mx
        pct = f'{(ct + cm) * 100 / sent:.0f}%' if sent else '—'
        out.append(f'• {k}: отправлено {sent}, нажали {ct + cm} ({pct}); Telegram {ct}, MAX {cm}')
    return '\n'.join(out)


@router.message(Command('clicks'))
async def clicks_cmd(m: Message, command: CommandObject):
    if not M_.is_admin(m.from_user.id):
        return
    await m.answer(clicks_text())

# Каждая рассылка ждёт своего START и уходит один раз. Несколько штук можно запланировать сразу.
CAMPAIGNS = [
    dict(
        KEY='bf_onair',
        TITLE='Мы в эфире, начинаем',
        STAGE='all',                    # 'test…' → только тест; 'all' → всем в Telegram и MAX; 'done' → закончена
        START=1795708800,               # 26.11.2026 19:00 МСК
        UNTIL=1795711200,               # 26.11.2026 19:40 МСК
        PHOTO=None,
        PHOTO_URL=None,
        TEXT=(
            '🔴🔴🔴 МЫ В ЭФИРЕ, НАЧИНАЕМ\n\n'
            'Сегодня у вас на глазах собираю ИИ-офис из 10 агентов по отделам, а по дороге раздам два кодовых слова на подарки. '
            'Записывать их придётся самим, в записи эфира их не будет'
        ),
        NAMED=False,
        LINK='https://start.bizon365.ru/room/olgapuzanova/7fc56ae89e9d',
        BUTTON='➡️ ПОДКЛЮЧИТЬСЯ',
        TRACK=False,
    ),
    dict(
        KEY='bf_onair_hours',
        TITLE='Сколько часов в неделю вы отдаёте рутине',
        STAGE='all',
        START=1795710000,               # 26.11.2026 19:20 МСК
        UNTIL=1795712400,               # 26.11.2026 20:00 МСК
        PHOTO=None,
        PHOTO_URL=None,
        TEXT=(
            '🔥🔥🔥 СКОЛЬКО ЧАСОВ В НЕДЕЛЮ ВЫ ОТДАЁТЕ РУТИНЕ? ⏳\n\n'
            'Сейчас на эфире считаем это вместе:\n'
            'какие задачи можно отдать агенту уже сегодня\n'
            'сколько часов они вернут\n'
            'куда эти часы потратить с пользой'
        ),
        NAMED=False,
        LINK='https://start.bizon365.ru/room/olgapuzanova/7fc56ae89e9d',
        BUTTON='➡️ ПОДКЛЮЧАЙТЕСЬ, сейчас покажу на примерах',
        TRACK=False,
    ),
    dict(
        KEY='bf_onair_skills',
        TITLE='Вы всё ещё пишете промпты с нуля',
        STAGE='all',
        START=1795710900,               # 26.11.2026 19:35 МСК
        UNTIL=1795713300,               # 26.11.2026 20:15 МСК
        PHOTO=None,
        PHOTO_URL=None,
        TEXT=(
            '🔖🔖 ВЫ ВСЁ ЕЩЁ ПИШЕТЕ ПРОМПТЫ С НУЛЯ? 🤯\n\n'
            'Рассказываю, почему главное теперь скиллы, и скоро назову кодовое слово на яйцо со скиллами. Внутри:\n'
            'шаблон скилла и промпты\n'
            'маркетплейсы скиллов, где их можно брать\n'
            'аудит вашей рутины'
        ),
        NAMED=False,
        LINK='https://start.bizon365.ru/room/olgapuzanova/7fc56ae89e9d',
        BUTTON='➡️ БЕГИТЕ НА ЭФИР, слово скажу только голосом',
        TRACK=False,
    ),
    dict(
        KEY='bf_onair_office',
        TITLE='Как выглядит ИИ-офис из 10 агентов',
        STAGE='all',
        START=1795711500,               # 26.11.2026 19:45 МСК
        UNTIL=1795713900,               # 26.11.2026 20:25 МСК
        PHOTO='ofis_live.jpg',          # скриншот офиса-небоскрёба
        PHOTO_URL='https://agent.olgapuzanovva.ru/img/ofis_live.jpg',
        TEXT=(
            'КАК ВЫГЛЯДИТ ИИ-ОФИС ИЗ 10 АГЕНТОВ? 🏢\n\n'
            'Собираю его вживую: раскладываю по отделам и показываю, какой агент за что отвечает и как они работают вместе. '
            'Можно смотреть и сразу примерять на свой бизнес'
        ),
        NAMED=False,
        LINK='https://start.bizon365.ru/room/olgapuzanova/7fc56ae89e9d',
        BUTTON='➡️ СМОТРЕТЬ, КАК СОБИРАЮ',
        TRACK=False,
    ),
    dict(
        KEY='bf_onair_lots',
        TITLE='Рассказываю про лоты Чёрной пятницы',
        STAGE='all',
        START=1795713600,               # 26.11.2026 20:20 МСК
        UNTIL=1795716000,               # 26.11.2026 21:00 МСК
        PHOTO=None,
        PHOTO_URL=None,
        TEXT=(
            '🥚🥚🥚🥚🥚 РАССКАЗЫВАЮ ПРО ЛОТЫ ЧЁРНОЙ ПЯТНИЦЫ\n\n'
            'Что внутри и как взять в рассрочку до 12 месяцев (Царь лот от 6 111 ₽ в месяц). '
            'Подарки первых суток: стратсессия со мной, 3 ИИ-агента под ключ и спринт 5 дней по соцсетям. Сгорают завтра в 19:00'
        ),
        NAMED=False,
        LINK='https://start.bizon365.ru/room/olgapuzanova/7fc56ae89e9d',
        BUTTON='➡️ СМОТРЕТЬ ЛОТЫ',
        TRACK=False,
    ),
]
TEST_USERNAMES = ('olgapuzanovva', 'olgapuzanovvva')


def text_for(c, first_name):
    if not c['NAMED']:
        return c['TEXT']
    name = (first_name or '').strip()
    if 'HELLO' in c:
        if name:
            return c['TEXT'].format(hello=c['HELLO'].format(name=html.escape(name)))
        t = c['TEXT'].format(hello='')
        i = next((k for k, ch in enumerate(t) if ch.isalpha()), 0)  # первая буква может стоять после эмодзи
        return t[:i] + t[i:i + 1].upper() + t[i + 1:]
    return c['TEXT'].format(hello=f'{html.escape(name)}, п' if name else 'П')


async def run(M):
    """M: модуль main (q, mark, bot, notify_admins, MX)."""
    await asyncio.gather(*(run_one(M, c) for c in CAMPAIGNS))


async def run_one(M, c):
    KEY, TITLE, STAGE, START, UNTIL = c['KEY'], c['TITLE'], c['STAGE'], c['START'], c['UNTIL']
    PHOTO, PHOTO_URL, LINK, BUTTON = c['PHOTO'], c['PHOTO_URL'], c['LINK'], c['BUTTON']
    if STAGE not in ('all',) and not STAGE.startswith('test'):
        return  # рассылка закончена: новые люди в боте её не получают
    if UNTIL and M.time.time() > UNTIL:
        return  # событие уже прошло
    if START and M.time.time() < START:
        log.info('campaign %s: ждём до %s', KEY, START)
        await asyncio.sleep(START - M.time.time())
    try:
        if STAGE.startswith('test'):
            names = [n.lower() for n in TEST_USERNAMES]
            rows = [r for r in M.q('SELECT * FROM users WHERE blocked=0').fetchall() if (r['username'] or '').lower() in names]
        else:
            rows = M.q('SELECT * FROM users WHERE blocked=0 ORDER BY id').fetchall()
        log.info('campaign %s %s: matched %s users', KEY, STAGE, len(rows))
        mark_key = f'{KEY}:{STAGE}'
        # кто уже получил тест, второй раз то же сообщение не получает
        done = "key = ?" if STAGE.startswith('test') else "(key = ? OR key LIKE '" + KEY + ":test%')"
        todo = [r for r in rows if not M.q(f'SELECT 1 FROM sent WHERE user_id=? AND {done}', r['id'], mark_key).fetchone()]
        if not todo:
            return
        photo = None
        if PHOTO:
            with open(M.os.path.join(M.os.path.dirname(__file__), PHOTO), 'rb') as f:
                photo = BufferedInputFile(f.read(), filename=PHOTO)
        ok = fail = 0
        for r in todo:
            if not M.mark(r['id'], mark_key):
                continue
            try:
                url = track_url(KEY, r['id'], LINK) if c.get('TRACK') else LINK
                kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BUTTON, url=url)] for _ in range(c.get('REPEAT', 1))])
                text = text_for(c, r['first_name'])
                if photo and len(text) > 1024:
                    # подпись к фото в Telegram не длиннее 1024 символов: картинку шлём отдельно, текст с кнопкой следом
                    m = await M.bot.send_photo(r['id'], photo)
                    photo = m.photo[-1].file_id
                    await M.bot.send_message(r['id'], text, reply_markup=kb, disable_web_page_preview=True)
                elif photo:
                    m = await M.bot.send_photo(r['id'], photo, caption=text, reply_markup=kb)
                    photo = m.photo[-1].file_id  # дальше шлём уже загруженную картинку
                else:
                    await M.bot.send_message(r['id'], text_for(c, r['first_name']), reply_markup=kb, disable_web_page_preview=True)
                ok += 1
            except Exception as e:
                fail += 1
                if 'blocked' in str(e) or 'deactivated' in str(e) or 'chat not found' in str(e):
                    M.q('UPDATE users SET blocked=1 WHERE id=?', r['id'])
                log.info('campaign %s: %s', r['id'], e)
            await asyncio.sleep(0.05)
        mx = 0
        if STAGE == 'all' and M.MX:
            for r in M.MX.q('SELECT * FROM max_users WHERE blocked=0 ORDER BY id').fetchall():
                if M.MX.q('SELECT 1 FROM max_sent WHERE user_id=? AND key=?', r['id'], mark_key).fetchone():
                    continue
                M.MX.q('INSERT OR IGNORE INTO max_sent(user_id, key) VALUES(?,?)', r['id'], mark_key)
                if await M.MX.send(r['id'], text_for(c, r['first_name']).replace('{', '{{').replace('}', '}}'),
                                   [[('url', BUTTON, (track_url(KEY, f"m{r['id']}", LINK) if c.get('TRACK') else LINK).replace('{', '{{').replace('}', '}}'))]] * c.get('REPEAT', 1), photo=PHOTO_URL or None):
                    mx += 1
                await asyncio.sleep(0.6)
        what = 'Тест рассылки' if STAGE.startswith('test') else 'Рассылка'
        log.info('campaign %s %s: ok=%s fail=%s max=%s', KEY, STAGE, ok, fail, mx)
        # всего с учётом прошлых запусков: если бот перезапускался посреди рассылки, первая часть ушла раньше
        total = M.q('SELECT COUNT(*) FROM sent WHERE key=?', mark_key).fetchone()[0]
        mx_total = M.MX.q('SELECT COUNT(*) FROM max_sent WHERE key=?', mark_key).fetchone()[0] if (M.MX and STAGE == 'all') else 0
        extra = f' (с прошлого запуска: всего отмечено {total})' if total > ok + fail else ''
        await M.notify_admins(f'📨 {what} «{TITLE}»: доставлено в Telegram {ok}, не доставлено {fail}{extra}'
                              + (f', в MAX {mx_total}' if STAGE == 'all' else '') + '.')
    except Exception:
        log.exception('campaign')
