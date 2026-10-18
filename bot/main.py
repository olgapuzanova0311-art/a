"""Бот регистрации на двухдневник «Собери ИИ-команду за выходные».

Переменные окружения:
  BOT_TOKEN      токен бота (обязательно)
  ADMIN_CODE     секретное слово: /admin <слово> делает пользователя админом
  SHEET_URL      адрес Apps Script для Google Таблицы и уведомлений
  PUBLIC_URL     https-адрес этого сервиса (для личного кабинета)
  TG_URL, MAX_URL, PAY_URL   ссылки на каналы и оплату VIP
  DB_PATH        путь к базе (по умолчанию /data/bot.db)
  PORT           порт веб-сервера (Railway задаёт сам)
"""
import asyncio, re, csv, hashlib, hmac, inspect, io, json, logging, os, secrets, sqlite3, time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, quote

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (BufferedInputFile, CallbackQuery, ChatMemberUpdated, InlineKeyboardButton,
                           InlineKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardMarkup,
                           ReplyKeyboardRemove, WebAppInfo)

import texts as T
from max_bot import MaxBot

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('bot')

BOT_TOKEN = os.environ['BOT_TOKEN']
ADMIN_CODE = os.environ.get('ADMIN_CODE', '')
SHEET_URL = os.environ.get('SHEET_URL', '')
PUBLIC_URL = os.environ.get('PUBLIC_URL', '').rstrip('/')
DB_PATH = os.environ.get('DB_PATH', '/data/bot.db')
MAX_TOKEN = os.environ.get('MAX_TOKEN', '')
MX = None
DEFAULT_LINKS = {
    'TG': os.environ.get('TG_URL', 'https://t.me/+cjxoa6weO0czOWRi'),
    'MAX': os.environ.get('MAX_URL', 'https://max.ru/join/PzpWaFYZ8q-BaFvU1pUAVlj1jycdgZgt9afSZqP9sQA'),
    'PAY': os.environ.get('PAY_URL', 'https://puzanovva.tech/page194999'),
    'SITE': T.SITE,
}

# ---------------- база ----------------
os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)
db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.row_factory = sqlite3.Row
db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA synchronous=FULL')
db.executescript('''
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, phone TEXT,
  created INTEGER, source TEXT, ref_code TEXT UNIQUE, referrer INTEGER,
  credited INTEGER DEFAULT 0, vip INTEGER DEFAULT 0, survey TEXT, blocked INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS sent(user_id INTEGER, key TEXT, PRIMARY KEY(user_id, key));
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS prizes(level INTEGER, user_id INTEGER, PRIMARY KEY(level, user_id));
''')
db.commit()
try:
    db.execute('ALTER TABLE users ADD COLUMN email TEXT'); db.commit()
except sqlite3.OperationalError:
    pass

def q(sql, *a):
    cur = db.execute(sql, a); db.commit(); return cur

def setting(k, default=''):
    r = q('SELECT v FROM settings WHERE k=?', k).fetchone()
    return r['v'] if r else default

def set_setting(k, v):
    q('INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v', k, v)

def paused():
    # пауза автоматических рассылок (цепочка и расписание); BOT_PAUSED=1 включает её по умолчанию, /resume снимает
    v = setting('paused')
    return v == '1' or (v != '0' and os.environ.get('BOT_PAUSED') == '1')

def user(uid):
    return q('SELECT * FROM users WHERE id=?', uid).fetchone()

def is_admin(uid):
    return q('SELECT 1 FROM admins WHERE id=?', uid).fetchone() is not None

def friends_count(uid):
    return q('SELECT COUNT(*) c FROM users WHERE referrer=? AND credited=1', uid).fetchone()['c']

def tickets(u):
    n = friends_count(u['id'])
    t = 1 if u['phone'] else 0
    for lv in T.LEVELS:
        if n >= lv['friends'] and lv.get('ticket'):
            t += 1 + lv.get('extra_tickets', 0)
    return t + (1 if u['vip'] else 0)

# ---------------- ссылки и кнопки ----------------
BOT_USERNAME = ''

def links(u=None):
    d = dict(DEFAULT_LINKS)
    d['STREAM1'] = setting('stream1') or T.STREAM1 or d['TG']
    d['STREAM2'] = setting('stream2') or T.STREAM2 or d['TG']
    d['ANKETA'] = setting('anketa') or 'https://t.me/puzanovateam?text=' + quote('Хочу на курс')
    if u:
        ref = ref_link(u)
        d['REF'] = ref
        d['SHARE'] = 'https://t.me/share/url?url=' + quote(ref) + '&text=' + quote('Иду на бесплатный двухдневник Ольги Пузановой «Собери ИИ-команду за выходные». Регистрируйся по моей ссылке, там подарки 🎁')
        d['PAY'] = d['PAY'] + ('&' if '?' in d['PAY'] else '?') + 'tg=' + str(u['id'])
    return d

def ref_link(u):
    return f'https://t.me/{BOT_USERNAME}?start=r{u["ref_code"]}'

def kb(rows, u=None):
    if not rows: return None
    L = links(u)
    out = []
    for row in rows:
        r = []
        for b in row:
            kind, text = b[0], b[1]
            if kind == 'url':
                r.append(InlineKeyboardButton(text=text, url=b[2].format(**L)))
            elif kind == 'cb':
                r.append(InlineKeyboardButton(text=text, callback_data=b[2]))
            elif kind == 'app':
                if PUBLIC_URL:
                    r.append(InlineKeyboardButton(text=text, web_app=WebAppInfo(url=PUBLIC_URL + '/app')))
                else:
                    r.append(InlineKeyboardButton(text=text, callback_data='cabinet'))
        if r: out.append(r)
    return InlineKeyboardMarkup(inline_keyboard=out)

def fill(text, u):
    name = (u['first_name'] or 'друг') if u else 'друг'
    L = links(u)
    return text.format(name=name, prize=T.MAIN_PRIZE, ref=L.get('REF', ''))

# ---------------- таблица и уведомления ----------------
async def to_sheet(u, event):
    if not SHEET_URL: return
    payload = dict(event=event, name=u['first_name'] or '', phone=u['phone'] or '', email=u['email'] or '',
                   tariff='VIP 490 ₽' if u['vip'] else 'Бесплатно 0 ₽', consent_data='да (бот)', consent_mailing='да (бот)',
                   page=f'Telegram @{u["username"] or "-"} id {u["id"]} · источник {u["source"] or "-"}' + (f' · опрос: {u["survey"]}' if u['survey'] else ''))
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(SHEET_URL, data=json.dumps(payload, ensure_ascii=False).encode(), headers={'Content-Type': 'text/plain;charset=utf-8'}, timeout=aiohttp.ClientTimeout(total=20))
    except Exception as e:
        log.warning('sheet: %s', e)

# ---------------- отправка ----------------
bot: Bot
router = Router()

async def send(uid, text, btns=None, photo=None):
    u = user(uid)
    try:
        markup = kb(btns, u)
        body = fill(text, u)
        if photo:
            url = photo if photo.startswith('http') else T.IMG + photo
            if len(body) <= 1000:
                await bot.send_photo(uid, url, caption=body, reply_markup=markup); return True
            await bot.send_photo(uid, url)
        await bot.send_message(uid, body, reply_markup=markup, disable_web_page_preview=True)
        return True
    except Exception as e:
        msg = str(e)
        if 'blocked' in msg or 'deactivated' in msg or 'chat not found' in msg:
            q('UPDATE users SET blocked=1 WHERE id=?', uid)
        log.info('send %s: %s', uid, msg)
        return False

def mark(uid, key):
    try:
        q('INSERT INTO sent(user_id,key) VALUES(?,?)', uid, key); return True
    except sqlite3.IntegrityError:
        return False

# ---------------- регистрация ----------------
def attach_referrer(u, source):
    # человек уже был в боте и потом открыл ссылку друга: засчитываем, если его ещё никто не пригласил
    if not source.startswith('r') or u['referrer'] or u['credited']: return False
    r = q('SELECT id, referrer FROM users WHERE ref_code=?', source[1:]).fetchone()
    if not r or r['id'] == u['id'] or r['referrer'] == u['id']: return False
    q('UPDATE users SET referrer=? WHERE id=?', r['id'], u['id'])
    return True

def new_user(m: Message, source: str):
    code = secrets.token_hex(4)
    referrer = None
    if source.startswith('r'):
        r = q('SELECT id FROM users WHERE ref_code=?', source[1:]).fetchone()
        if r and r['id'] != m.from_user.id: referrer = r['id']
    q('INSERT INTO users(id,username,first_name,created,source,ref_code,referrer) VALUES(?,?,?,?,?,?,?)',
      m.from_user.id, m.from_user.username, m.from_user.first_name, int(time.time()), source or 'бот', code, referrer)
    return user(m.from_user.id)

@router.message(CommandStart())
async def start(m: Message, command: CommandObject):
    u = user(m.from_user.id)
    if u:
        q('UPDATE users SET blocked=0, username=?, first_name=? WHERE id=?', m.from_user.username, m.from_user.first_name, u['id'])
        if attach_referrer(u, (command.args or '').strip()):
            u = user(u['id'])
            if u['phone']: await credit_referrer(u)
        if u['email']:
            await send(u['id'], T.ALREADY, T.MENU_BTNS)
        else:
            await next_step(u, u['id'])
        return
    u = new_user(m, (command.args or '').strip())
    circle = setting('circle')
    if circle:
        try: await bot.send_video_note(u['id'], circle)
        except Exception as e: log.warning('circle: %s', e)
    await send(u['id'], T.WELCOME, T.WELCOME_BTNS, photo='i_hero.jpg')
    asyncio.create_task(to_sheet(u, 'Регистрация через бота (без телефона)'))

async def ask_contact(uid):
    await bot.send_message(uid, T.ASK_CONTACT, reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='📱 Поделиться номером', request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True))

@router.callback_query(F.data == 'gifts')
async def cb_gifts(c: CallbackQuery):
    await c.answer()
    u = user(c.from_user.id)
    await next_step(u, c.from_user.id)

async def next_step(u, uid):
    if not u or not u['phone']:
        return await ask_contact(uid)
    if not u['email']:
        return await ask_email(uid)
    await give_gifts(u)

async def ask_email(uid):
    await bot.send_message(uid, T.ASK_EMAIL, reply_markup=ReplyKeyboardRemove())

@router.message(Command('podarki'))
async def cmd_gifts(m: Message):
    u = user(m.from_user.id)
    if not u: return await start(m, CommandObject(prefix='/', command='start', args=None))
    await next_step(u, m.from_user.id)

def gift_rows(keys):
    return [[('url', '🎁 ' + T.GIFT[k][0], T.GIFT[k][1])] for k in keys]

async def give_gifts(u, again=False):
    await bot.send_message(u['id'], '🎁', reply_markup=ReplyKeyboardRemove())
    await send(u['id'], T.GIFTS_TEXT, gift_rows(T.REG_GIFTS) + T.MENU_BTNS + [[('url', '🔗 Позвать друга', '{SHARE}')]])

@router.message(F.contact)
async def got_contact(m: Message):
    u = user(m.from_user.id)
    if not u:
        u = new_user(m, 'бот')
    if m.contact.user_id and m.contact.user_id != m.from_user.id:
        return await m.answer('Пришли, пожалуйста, свой номер кнопкой «Поделиться номером» 🙌')
    first_time = not u['phone']
    q('UPDATE users SET phone=? WHERE id=?', m.contact.phone_number, u['id'])
    u = user(u['id'])
    if first_time:
        asyncio.create_task(to_sheet(u, 'Регистрация через бота: телефон'))
        await credit_referrer(u)
    await next_step(u, u['id'])

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]{2,}$')

@router.message(F.text & ~F.text.startswith('/'))
async def got_text(m: Message):
    u = user(m.from_user.id)
    if not u:
        return await start(m, CommandObject(prefix='/', command='start', args=None))
    if u['phone'] and not u['email']:
        mail = m.text.strip().lower()
        if not EMAIL_RE.match(mail):
            return await m.answer(T.BAD_EMAIL)
        q('UPDATE users SET email=? WHERE id=?', mail, u['id'])
        u = user(u['id'])
        asyncio.create_task(to_sheet(u, 'Регистрация через бота'))
        return await give_gifts(u)
    if not u['phone']:
        return await ask_contact(u['id'])
    await m.answer(T.HELP)

# ---------------- друзья ----------------
async def is_channel_member(uid):
    ch = setting('channel_id')
    if not ch: return True
    try:
        st = (await bot.get_chat_member(int(ch), uid)).status
        return st in ('member', 'administrator', 'creator', 'restricted')
    except Exception as e:
        log.info('member check: %s', e); return True

def unlocked_text(uid):
    n = friends_count(uid)
    got = [lv for lv in T.LEVELS if lv['friends'] == n and n > 0]
    nxt = next((lv for lv in T.LEVELS if lv['friends'] > n), None)
    s = ''
    if got: s += '🔓 Открыт новый подарок: <b>' + got[0]['title'] + '</b>\n'
    if nxt: s += f'До следующего подарка («{nxt["title"]}») осталось друзей: <b>{nxt["friends"] - n}</b>.'
    return s or 'Ты открыл все уровни! 🏆'

async def credit_referrer(u, force=False):
    if not u['referrer'] or u['credited']: return
    if not force and not await is_channel_member(u['id']):
        await send(u['id'], 'Последний шаг: подпишись на закрытый канал. Тогда друг, который тебя позвал, получит подарок 🙌',
                   [[('url', '📢 Подписаться', '{TG}')], [('cb', '✅ Я подписался', 'chk')]])
        return
    q('UPDATE users SET credited=1 WHERE id=?', u['id'])
    ref = user(u['referrer'])
    if not ref: return
    n = friends_count(ref['id'])
    for lv in T.LEVELS:
        if lv['friends'] == n and lv.get('prize') == 'vip' and not ref['vip']:
            q('UPDATE users SET vip=1 WHERE id=?', ref['id'])
            await send(ref['id'], T.VIP_ACTIVATED, [[('app', '👤 Личный кабинет')]])
        if lv['friends'] == n and lv.get('limit'):
            taken = q('SELECT COUNT(*) c FROM prizes WHERE level=?', lv['friends']).fetchone()['c']
            if taken < lv['limit']:
                q('INSERT OR IGNORE INTO prizes(level,user_id) VALUES(?,?)', lv['friends'], ref['id'])
                await notify_admins(f'🏆 Приз «{lv["prize"]}» заработал(а) {ref["first_name"]} @{ref["username"] or "-"} ({ref["phone"] or "без телефона"}). Свяжитесь, чтобы вручить.')
    await send(ref['id'], T.FRIEND_JOINED.replace('{friends}', str(n)).replace('{unlocked}', unlocked_text(ref['id'])), [[('app', '👤 Мои подарки')]])

@router.callback_query(F.data == 'chk')
async def cb_check(c: CallbackQuery):
    u = user(c.from_user.id)
    if await is_channel_member(c.from_user.id):
        await c.answer('Готово, спасибо! 🎉', show_alert=False)
        await credit_referrer(u)
    else:
        await c.answer('Пока не вижу подписки. Подпишись и нажми ещё раз 🙌', show_alert=True)

@router.my_chat_member()
async def bot_added(ev: ChatMemberUpdated):
    if ev.chat.type == 'channel' and ev.new_chat_member.status == 'administrator':
        set_setting('channel_id', str(ev.chat.id))
        await notify_admins(f'✅ Бот добавлен админом в канал «{ev.chat.title}». Теперь друзья засчитываются только после подписки.')

# ---------------- опрос ----------------
@router.callback_query(F.data.startswith('sv:'))
async def survey(c: CallbackQuery):
    await c.answer()
    u = user(c.from_user.id)
    if not u: return
    part = c.data[3:]
    if part == 'start':
        step, answers = 0, []
    else:
        step_s, ans = part.split(':', 1)
        step = int(step_s)
        answers = json.loads(setting(f'sv_{u["id"]}', '[]'))
        answers = answers[:step] + [T.SURVEY[step][1][int(ans)]]
        step += 1
    set_setting(f'sv_{u["id"]}', json.dumps(answers, ensure_ascii=False))
    if step < len(T.SURVEY):
        qtext, opts = T.SURVEY[step]
        rows = [[InlineKeyboardButton(text=o, callback_data=f'sv:{step}:{i}')] for i, o in enumerate(opts)]
        await bot.send_message(u['id'], f'<b>Вопрос {step + 1} из {len(T.SURVEY)}.</b> {qtext}', reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    else:
        q('UPDATE users SET survey=? WHERE id=?', ' / '.join(answers), u['id'])
        u = user(u['id'])
        await send(u['id'], T.SURVEY_DONE, gift_rows([T.SURVEY_GIFT]))
        asyncio.create_task(to_sheet(u, 'Опрос в боте'))

# ---------------- кабинет ----------------
@router.message(Command('kabinet'))
@router.callback_query(F.data == 'cabinet')
async def cabinet(ev):
    uid = ev.from_user.id
    if isinstance(ev, CallbackQuery): await ev.answer()
    u = user(uid)
    if not u: return
    text = cabinet_text(u)
    await send(uid, text, [[('app', '👤 Открыть кабинет')], [('url', '🔗 Позвать друга', '{SHARE}')]])

def cabinet_text(u):
    n = friends_count(u['id'])
    lines = [f'👤 <b>Личный кабинет</b>', f'Билет: <b>{"VIP 💛" if u["vip"] else "бесплатный"}</b>', f'Друзей пришло: <b>{n}</b>', f'Билетов в розыгрыш {T.MAIN_PRIZE}: <b>{tickets(u)}</b>', '', '<b>Подарки за друзей:</b>']
    for lv in T.LEVELS:
        lines.append(('✅ ' if n >= lv['friends'] else '🔒 ') + f'{lv["friends"]} · {lv["title"]}')
    lines += ['', 'Твоя ссылка для друзей:', '{ref}']
    return '\n'.join(lines)

@router.message(Command('help'))
async def help_(m: Message):
    await m.answer(T.HELP)

# ---------------- админ ----------------
async def notify_admins(text):
    for r in q('SELECT id FROM admins').fetchall():
        try: await bot.send_message(r['id'], text)
        except Exception: pass

@router.message(Command('admin'))
async def admin(m: Message, command: CommandObject):
    if ADMIN_CODE and (command.args or '').strip() == ADMIN_CODE:
        q('INSERT OR IGNORE INTO admins(id) VALUES(?)', m.from_user.id)
        await m.answer(ADMIN_HELP)
    elif is_admin(m.from_user.id):
        await m.answer(ADMIN_HELP)

ADMIN_HELP = ('🛠 <b>Ты админ.</b> Команды:\n'
  '/stats · статистика\n'
  '/link1 ссылка · ссылка на эфир субботы\n'
  '/link2 ссылка · ссылка на эфир воскресенья\n'
  '/anketa ссылка · анкета предзаписи (сообщение про грант)\n'
  '/vip @ник или телефон или id · отметить оплату VIP\n'
  '/circle · ответь этой командой на кружок, и он станет приветствием\n'
  '/broadcast · ответь этой командой на любое сообщение и выбери, кому разослать\n'
  '/segments · кто «внедряю», кто «зарабатываю», выгрузка по сегментам\n'
  '/users · список всех участников (листается кнопками)\n'
  '/pause · поставить автоматические рассылки на паузу, /resume · включить\n'
  '/sources · откуда пришли люди (по меткам)\n'
  '/find имя, ник, телефон или почта · найти участника\n'
  '/friend id_друга id_пригласившего · засчитать друга вручную\n'
  '/export · выгрузка участников в файл для Excel\n'
  '/backup · прислать бэкап базы (он же приходит каждую ночь)\n'
  '/restore · ответь на файл бэкапа, чтобы восстановить базу\n'
  '/test · прислать себе приветствие\n'
  '/reset_me · забыть тебя, чтобы пройти регистрацию заново\n'
  '/chain · показать все сообщения цепочки по порядку')

def admin_only(fn):
    names = set(inspect.signature(fn).parameters)
    async def w(m: Message, **k):
        if not is_admin(m.from_user.id): return
        return await fn(m, **{x: v for x, v in k.items() if x in names})
    w.__name__ = fn.__name__
    return w

@router.message(Command('pause'))
@admin_only
async def pause_cmd(m: Message):
    set_setting('paused', '1')
    await m.answer('⏸ Автоматические рассылки на паузе (цепочка после регистрации и сообщения по расписанию, Telegram и MAX).\n'
                   'Ручная /broadcast работает. Включить обратно: /resume')

@router.message(Command('resume'))
@admin_only
async def resume_cmd(m: Message):
    set_setting('paused', '0')
    await m.answer('▶️ Автоматические рассылки снова включены. Сообщения, время которых прошло больше 2 часов назад, не отправятся.')

@router.message(Command('stats'))
@admin_only
async def stats(m: Message):
    c = lambda sql: q(sql).fetchone()[0]
    await m.answer(f'📊 Всего: <b>{c("SELECT COUNT(*) FROM users")}</b>\n'
                   f'С телефоном: <b>{c("SELECT COUNT(*) FROM users WHERE phone IS NOT NULL")}</b>\n'
                   f'С почтой: <b>{c("SELECT COUNT(*) FROM users WHERE email IS NOT NULL")}</b>\n'
                   f'VIP: <b>{c("SELECT COUNT(*) FROM users WHERE vip=1")}</b>\n'
                   f'Прошли опрос: <b>{c("SELECT COUNT(*) FROM users WHERE survey IS NOT NULL")}</b>\n'
                   f'Пришли по ссылкам друзей: <b>{c("SELECT COUNT(*) FROM users WHERE credited=1")}</b>\n'
                   f'Заблокировали бота: <b>{c("SELECT COUNT(*) FROM users WHERE blocked=1")}</b>\n'
                   + (f'\n<b>MAX:</b> всего {MX.count()[0]}, с телефоном {MX.count()[1]}, с почтой {MX.count()[2]}\n' if MX else '') + '\n'
                   f'Эфир сб: {setting("stream1") or "не задан"}\nЭфир вс: {setting("stream2") or "не задан"}\nАнкета: {setting("anketa") or "не задана"}')

def source_rows(rows):
    # rows: (source, всего, с телефоном, с почтой); реферальные ссылки r<код> сводим в одну строку
    agg = {}
    for src, n, ph, em in rows:
        key = 'друзья (рефералка)' if re.fullmatch(r'r[0-9a-f]{8}', src or '') else (src or 'бот')
        a = agg.setdefault(key, [0, 0, 0])
        a[0] += n; a[1] += ph; a[2] += em
    return sorted(agg.items(), key=lambda x: -x[1][0])

@router.message(Command('sources'))
@admin_only
async def sources(m: Message):
    sql = 'SELECT source, COUNT(*), COUNT(phone), COUNT(email) FROM {} GROUP BY source'
    out = ['📈 <b>Откуда пришли</b> (всего · с телефоном · с почтой)\n', '<b>Telegram</b>']
    out += [f'{k}: {v[0]} · {v[1]} · {v[2]}' for k, v in source_rows(q(sql.format('users')).fetchall())]
    if MX:
        out += ['', '<b>MAX</b>'] + [f'{k}: {v[0]} · {v[1]} · {v[2]}' for k, v in source_rows(MX.q(sql.format('max_users')).fetchall())]
    out += ['', 'Регистрации с сайта: в таблице, колонка «Страница» (там видно utm_source).']
    await m.answer('\n'.join(out))

for _cmd, _key in (('link1', 'stream1'), ('link2', 'stream2'), ('anketa', 'anketa')):
    def _mk(key):
        @admin_only
        async def h(m: Message, command: CommandObject):
            v = (command.args or '').strip()
            if not v.startswith('http'): return await m.answer('Пришли так: /' + m.text.split()[0][1:] + ' https://...')
            set_setting(key, v); await m.answer('✅ Сохранено: ' + v)
        return h
    router.message(Command(_cmd))(_mk(_key))

@router.message(Command('vip'))
@admin_only
async def vip(m: Message, command: CommandObject):
    a = (command.args or '').strip()
    if not a: return await m.answer('Пришли так: /vip @ник, /vip 79001234567 или /vip id')
    digits = ''.join(ch for ch in a if ch.isdigit())
    r = None
    if a.startswith('@'): r = q('SELECT * FROM users WHERE lower(username)=lower(?)', a[1:]).fetchone()
    if not r and digits:
        r = q('SELECT * FROM users WHERE id=?', int(digits)).fetchone() or \
            q("SELECT * FROM users WHERE replace(replace(replace(phone,'+',''),' ',''),'-','') LIKE ?", '%' + digits[-10:]).fetchone()
    if not r: return await m.answer('Не нашла такого участника. Проверь ник или телефон.')
    q('UPDATE users SET vip=1 WHERE id=?', r['id'])
    await send(r['id'], T.VIP_ACTIVATED, [[('app', '👤 Личный кабинет')]])
    await m.answer(f'✅ VIP отмечен: {r["first_name"]} @{r["username"] or "-"}')
    asyncio.create_task(to_sheet(user(r['id']), 'Оплата VIP (отмечено вручную)'))

@router.message(Command('circle'))
@admin_only
async def circle(m: Message):
    if m.reply_to_message and m.reply_to_message.video_note:
        set_setting('circle', m.reply_to_message.video_note.file_id)
        await m.answer('✅ Кружок сохранён. Его увидит каждый новый участник при старте.')
    else:
        await m.answer('Запиши кружок в этот чат, потом ответь на него командой /circle.')

# Сегменты по опросу «Зачем идёшь на двухдневник?». Кто выбрал «И то, и другое», попадает в оба.
SEGMENTS = {
    'all': ('Всем', '1=1'),
    'in': ('Внедряю к себе', "(survey LIKE '%Внедрить%' OR survey LIKE '%И то, и другое%')"),
    'earn': ('Зарабатываю', "(survey LIKE '%Зарабатывать%' OR survey LIKE '%И то, и другое%')"),
    'none': ('Не прошли опрос', "survey IS NULL"),
}

def seg_count(seg):
    return q(f"SELECT COUNT(*) FROM users WHERE blocked=0 AND {SEGMENTS[seg][1]}").fetchone()[0]

def seg_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f'{v[0]} · {seg_count(k)}', callback_data=f'bc:seg:{k}')] for k, v in SEGMENTS.items()]
                                + [[InlineKeyboardButton(text='Отмена', callback_data='bc:no')]])

@router.message(Command('broadcast'))
@admin_only
async def broadcast(m: Message):
    if not m.reply_to_message:
        return await m.answer('Ответь командой /broadcast на сообщение, которое нужно разослать.')
    set_setting('bc_msg', f'{m.chat.id}:{m.reply_to_message.message_id}')
    set_setting('bc_text', m.reply_to_message.html_text or '')
    await m.answer('Кому отправить? Числа рядом: сколько человек в Telegram.', reply_markup=seg_kb())

@router.callback_query(F.data.startswith('bc:'))
async def bc_go(c: CallbackQuery):
    if not is_admin(c.from_user.id): return await c.answer()
    await c.answer()
    if c.data == 'bc:no': return await c.message.edit_text('Отменено.')
    if c.data.startswith('bc:seg:'):
        seg = c.data[7:]
        set_setting('bc_seg', seg)
        mx = f' + в MAX {MX.seg_count(SEGMENTS[seg][1])}' if MX else ''
        return await c.message.edit_text(f'Аудитория: <b>{SEGMENTS[seg][0]}</b>. В Telegram {seg_count(seg)}{mx}. Отправляем?',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🧪 Сначала себе', callback_data='bc:me')],
                [InlineKeyboardButton(text='✅ Да, отправить', callback_data='bc:go'), InlineKeyboardButton(text='Отмена', callback_data='bc:no')]]))
    chat, mid = setting('bc_msg').split(':')
    if c.data == 'bc:me':
        await bot.copy_message(c.from_user.id, int(chat), int(mid))
        return await bot.send_message(c.from_user.id, '☝️ Так увидят участники. Отправляем?', reply_markup=c.message.reply_markup)
    seg = setting('bc_seg') or 'all'
    where = SEGMENTS.get(seg, SEGMENTS['all'])[1]
    await c.message.edit_text(f'🚀 Рассылка пошла: {SEGMENTS.get(seg, SEGMENTS["all"])[0]}…')
    ok = 0
    for r in q(f'SELECT id FROM users WHERE blocked=0 AND {where}').fetchall():
        try:
            await bot.copy_message(r['id'], int(chat), int(mid)); ok += 1
        except Exception as e:
            if 'blocked' in str(e) or 'deactivated' in str(e): q('UPDATE users SET blocked=1 WHERE id=?', r['id'])
        await asyncio.sleep(0.05)
    await bot.send_message(c.from_user.id, f'✅ Доставлено в Telegram: {ok}')
    if MX and c.data == 'bc:go':
        if setting('bc_text'):
            n = await MX.broadcast(setting('bc_text'), where)
            await bot.send_message(c.from_user.id, f'✅ Доставлено в MAX: {n}')
        else:
            await bot.send_message(c.from_user.id, 'В MAX рассылаю только текст: в этом сообщении его нет, поэтому в MAX не отправила.')

@router.message(Command('segments'))
@admin_only
async def segments_cmd(m: Message):
    c = lambda sql: q(sql).fetchone()[0]
    both = c("SELECT COUNT(*) FROM users WHERE survey LIKE '%И то, и другое%'")
    only_in = c("SELECT COUNT(*) FROM users WHERE survey LIKE '%Внедрить%'")
    only_earn = c("SELECT COUNT(*) FROM users WHERE survey LIKE '%Зарабатывать%'")
    none = c("SELECT COUNT(*) FROM users WHERE survey IS NULL")
    text = ('🧭 <b>Сегменты (Telegram)</b>\n\n'
            f'🏢 Внедряю к себе: <b>{only_in}</b>\n💸 Зарабатываю: <b>{only_earn}</b>\n🔀 И то, и другое: <b>{both}</b>\n🤷 Не прошли опрос: <b>{none}</b>\n')
    if MX:
        text += ('\n<b>MAX</b>: внедряю ' + str(MX.seg_count("survey LIKE '%Внедрить%'")) + ', зарабатываю ' + str(MX.seg_count("survey LIKE '%Зарабатывать%'"))
                 + ', оба ' + str(MX.seg_count("survey LIKE '%И то, и другое%'")) + ', без опроса ' + str(MX.seg_count('survey IS NULL')) + '\n')
    text += '\nВыгрузка сегмента в файл для Excel 👇\nРассылка по сегменту: ответь /broadcast на сообщение и выбери аудиторию.'
    await m.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='📥 ' + v[0], callback_data=f'sx:{k}')] for k, v in SEGMENTS.items() if k != 'all']))

@router.callback_query(F.data.startswith('sx:'))
async def seg_export(c: CallbackQuery):
    if not is_admin(c.from_user.id): return await c.answer()
    await c.answer()
    seg = c.data[3:]
    await bot.send_document(c.from_user.id, BufferedInputFile(export_csv(SEGMENTS[seg][1]), filename=f'segment_{seg}.csv'), caption=SEGMENTS[seg][0])

PAGE = 15

def user_line(r):
    from html import escape
    nick = f"@{r['username']}" if r['username'] else f"<a href=\"tg://user?id={r['id']}\">профиль</a>"
    marks = ('💛 VIP · ' if r['vip'] else '') + ('🚫 заблокировал · ' if r['blocked'] else '')
    fr = friends_count(r['id'])
    return (f"<b>{escape(r['first_name'] or 'без имени')}</b> {nick}\n"
            f"📞 {escape(r['phone'] or '—')} · ✉️ {escape(r['email'] or '—')}\n"
            f"{marks}🕒 {datetime.fromtimestamp(r['created'], T.MSK).strftime('%d.%m %H:%M')}"
            + (f' · 👥 друзей: {fr}' if fr else '') + (f" · {escape(r['source'])}" if r['source'] else '')
            + f"\n🆔 {r['id']}" + ref_status(r)
            + (f"\n📝 {escape(r['survey'])}" if r['survey'] else ''))

def ref_status(r):
    if not r['referrer']: return ''
    from html import escape
    ref = user(r['referrer'])
    who = escape((ref['first_name'] if ref else None) or str(r['referrer']))
    if r['credited']: why = '✅ засчитан'
    elif not r['phone']: why = '⏳ не засчитан: не поделился номером'
    else: why = '⏳ не засчитан: не подписан на канал'
    return f'\n🤝 пришёл от {who} ({r["referrer"]}) · {why}'

def users_page(page):
    total = q('SELECT COUNT(*) FROM users').fetchone()[0]
    pages = max(1, (total + PAGE - 1) // PAGE)
    page = min(max(page, 0), pages - 1)
    rows = q('SELECT * FROM users ORDER BY created DESC LIMIT ? OFFSET ?', PAGE, page * PAGE).fetchall()
    text = f'👥 <b>Участники: {total}</b> · стр. {page + 1} из {pages} (сначала новые)\n\n' + '\n\n'.join(user_line(r) for r in rows)
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text='◀️ Новее', callback_data=f'us:{page - 1}'))
    if page < pages - 1: nav.append(InlineKeyboardButton(text='Старше ▶️', callback_data=f'us:{page + 1}'))
    return text, InlineKeyboardMarkup(inline_keyboard=[nav] if nav else [])

@router.message(Command('users'))
@admin_only
async def users_cmd(m: Message):
    text, kb = users_page(0)
    await m.answer(text, reply_markup=kb, disable_web_page_preview=True)

@router.callback_query(F.data.startswith('us:'))
async def users_nav(c: CallbackQuery):
    if not is_admin(c.from_user.id): return await c.answer()
    await c.answer()
    text, kb = users_page(int(c.data[3:]))
    try: await c.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    except Exception: pass

@router.message(Command('find'))
@admin_only
async def find_cmd(m: Message, command: CommandObject):
    s = (command.args or '').strip().lstrip('@').lower()
    if not s:
        return await m.answer('Напиши, кого искать: /find Анна, /find @nick, /find 9001234567 или /find почта')
    digits = re.sub(r'\D', '', s)[-10:]
    def hit(r):
        txt = ' '.join(str(r[k] or '') for k in ('first_name', 'username', 'email')).lower()
        return s in txt or (len(digits) >= 4 and digits in re.sub(r'\D', '', r['phone'] or ''))
    rows = [r for r in q('SELECT * FROM users ORDER BY created DESC').fetchall() if hit(r)][:20]
    if not rows: return await m.answer('Никого не нашла 🤷‍♀️')
    await m.answer(f'🔎 Нашла: {len(rows)}\n\n' + '\n\n'.join(user_line(r) for r in rows), disable_web_page_preview=True)

@router.message(Command('friend'))
@admin_only
async def friend_cmd(m: Message, command: CommandObject):
    ids = re.findall(r'\d+', command.args or '')
    if len(ids) != 2:
        return await m.answer('Засчитать друга вручную: /friend id_друга id_пригласившего\nid видно в /find (строка 🆔).')
    fr, rf = user(int(ids[0])), user(int(ids[1]))
    if not fr or not rf or fr['id'] == rf['id']:
        return await m.answer('Не нашла кого-то из них в боте. Проверь id через /find.')
    if fr['credited']:
        return await m.answer('Этот друг уже засчитан' + (f' пригласившему {fr["referrer"]}' if fr['referrer'] else '') + '.')
    q('UPDATE users SET referrer=? WHERE id=?', rf['id'], fr['id'])
    await credit_referrer(user(fr['id']), force=True)
    await m.answer(f'Готово ✅ {fr["first_name"]} засчитан(а) для {rf["first_name"]}. Друзей теперь: {friends_count(rf["id"])}.')

@router.message(Command('export'))
@admin_only
async def export(m: Message):
    await m.answer_document(BufferedInputFile(export_csv(), filename='uchastniki.csv'))


@router.message(Command('reset_me'))
@admin_only
async def reset_me(m: Message):
    uid = m.from_user.id
    q('DELETE FROM sent WHERE user_id=?', uid)
    q('DELETE FROM settings WHERE k=?', f'sv_{uid}')
    q('DELETE FROM users WHERE id=?', uid)
    await m.answer('🧹 Готово, я тебя забыла. Нажми /start и пройди регистрацию как новый участник. Админом ты остаёшься.', reply_markup=ReplyKeyboardRemove())

def when_text(step):
    if 'after' in step:
        mins = step['after']
        human = f'{mins} мин' if mins < 60 else (f'{mins // 60} ч' if mins % 60 == 0 else f'{mins // 60} ч {mins % 60} мин')
        return f'через {human} после регистрации'
    return step['at'].strftime('%d.%m в %H:%M МСК')

COND = {'not_vip': 'тем, у кого нет VIP', 'no_survey': 'тем, кто не прошёл опрос', 'no_contact': 'тем, кто не оставил номер',
        'no_email': 'тем, кто оставил номер, но не почту', 'vip': 'только VIP'}

@router.message(Command('chain'))
@admin_only
async def chain_preview(m: Message):
    uid = m.from_user.id
    if not user(uid):
        return await m.answer('Сначала нажми /start, чтобы бот знал твоё имя.')
    steps = [('Цепочка после регистрации', T.CHAIN), ('Рассылки по расписанию', T.SCHEDULE)]
    total = sum(len(x) for _, x in steps)
    await m.answer(f'▶️ Показываю всю цепочку: {total} сообщений. Над каждым серая подпись, когда и кому оно уходит.')
    i = 0
    for title, lst in steps:
        await m.answer(f'<b>━━ {title} ━━</b>')
        for st in lst:
            i += 1
            who = COND.get(st.get('only'), 'всем участникам')
            await m.answer(f'<i>#{i} · {when_text(st)} · {who}</i>')
            await send(uid, st['text'], st.get('btns'), st.get('photo'))
            await asyncio.sleep(0.4)
    await m.answer('✅ Это вся цепочка. Пришли правки к любому номеру, например «#5 поменять текст на…»')

@router.message(Command('test'))
@admin_only
async def test(m: Message):
    await send(m.from_user.id, T.WELCOME, T.WELCOME_BTNS, photo='i_hero.jpg')


# ---------------- бэкап ----------------
def export_csv(where='1=1'):
    buf = io.StringIO(); w = csv.writer(buf, delimiter=';')
    w.writerow(['id', 'ник', 'имя', 'телефон', 'почта', 'дата', 'источник', 'пригласил', 'засчитан', 'VIP', 'друзей', 'опрос', 'заблокировал'])
    for r in q(f'SELECT * FROM users WHERE {where} ORDER BY created').fetchall():
        w.writerow([r['id'], r['username'], r['first_name'], r['phone'], r['email'], datetime.fromtimestamp(r['created'], T.MSK).strftime('%d.%m.%Y %H:%M'),
                    r['source'], r['referrer'], r['credited'], r['vip'], friends_count(r['id']), r['survey'], r['blocked']])
    return ('\ufeff' + buf.getvalue()).encode('utf-8')

def db_bytes():
    path = DB_PATH + '.bak'
    dst = sqlite3.connect(path); db.backup(dst); dst.close()
    with open(path, 'rb') as f: return f.read()

async def send_backup(chat_ids=None):
    ids = chat_ids or [r['id'] for r in q('SELECT id FROM admins').fetchall()]
    if not ids: return
    stamp = datetime.now(T.MSK).strftime('%d.%m_%H-%M')
    n = q('SELECT COUNT(*) FROM users').fetchone()[0]
    data, table = db_bytes(), export_csv()
    for cid in ids:
        try:
            await bot.send_document(cid, BufferedInputFile(data, filename=f'bot_backup_{stamp}.db'),
                                    caption=f'💾 Бэкап базы бота: {n} участников. Сохрани. Если база пропадёт, ответь на этот файл командой /restore.')
            await bot.send_document(cid, BufferedInputFile(table, filename=f'uchastniki_{stamp}.csv'))
        except Exception as e:
            log.warning('backup to %s: %s', cid, e)

@router.message(Command('backup'))
@admin_only
async def backup_cmd(m: Message):
    await send_backup([m.from_user.id])

@router.message(Command('restore'))
@admin_only
async def restore_cmd(m: Message):
    d = m.reply_to_message.document if m.reply_to_message else None
    if not d or not d.file_name.endswith('.db'):
        return await m.answer('Ответь командой /restore на файл бэкапа bot_backup_….db')
    f = await bot.download(d)
    src_path = DB_PATH + '.restore'
    with open(src_path, 'wb') as out: out.write(f.read())
    src = sqlite3.connect(src_path)
    try:
        n = src.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    except Exception:
        src.close(); return await m.answer('Это не похоже на бэкап бота.')
    me = m.from_user.id
    src.backup(db); src.close()
    q('INSERT OR IGNORE INTO admins(id) VALUES(?)', me)
    await m.answer(f'✅ База восстановлена: {n} участников. Рассылки продолжат работать по ней.')

# ---------------- планировщик ----------------
def cond_ok(u, only):
    if only == 'not_vip': return not u['vip']
    if only == 'vip': return bool(u['vip'])
    if only == 'no_survey': return not u['survey']
    if only == 'no_contact': return not u['phone']
    if only == 'no_email': return bool(u['phone']) and not u['email']
    return True

async def scheduler():
    while True:
        try:
            now = datetime.now(T.MSK)
            nowts = int(time.time())
            if now < T.EVENT_END and not paused():
                for step in T.CHAIN:
                    rows = q('SELECT * FROM users WHERE blocked=0 AND created<=? AND created>=?', nowts - step['after'] * 60, nowts - step['after'] * 60 - 6 * 3600).fetchall()
                    for u in rows:
                        if cond_ok(u, step.get('only')) and mark(u['id'], step['key']):
                            await send(u['id'], step['text'], step.get('btns'), step.get('photo')); await asyncio.sleep(0.05)
            for msg in ([] if paused() else T.SCHEDULE):
                at = msg['at']
                if at <= now < at + timedelta(hours=2):
                    rows = q('SELECT * FROM users WHERE blocked=0 AND created<=?', int(at.timestamp())).fetchall()
                    for u in rows:
                        if cond_ok(u, msg.get('only')) and mark(u['id'], msg['key']):
                            await send(u['id'], msg['text'], msg.get('btns'), msg.get('photo')); await asyncio.sleep(0.05)
            # ежедневный бэкап в 03:00 МСК
            day_key = now.strftime('%Y%m%d')
            if now.hour == 3 and setting('last_backup') != day_key:
                set_setting('last_backup', day_key); await send_backup()
            # повторная проверка подписки у друзей
            if setting('channel_id') and int(time.time()) % 3600 < 60:
                for u in q('SELECT * FROM users WHERE referrer IS NOT NULL AND credited=0 AND phone IS NOT NULL').fetchall():
                    if await is_channel_member(u['id']): await credit_referrer(u)
        except Exception:
            log.exception('scheduler')
        await asyncio.sleep(30)

# ---------------- веб: кабинет ----------------
def check_init_data(init_data):
    try:
        data = dict(parse_qsl(init_data, keep_blank_values=True))
        h = data.pop('hash')
        dcs = '\n'.join(f'{k}={v}' for k, v in sorted(data.items()))
        secret = hmac.new(b'WebAppData', BOT_TOKEN.encode(), hashlib.sha256).digest()
        if hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest() != h: return None
        return json.loads(data['user'])['id']
    except Exception:
        return None

async def api_me(req):
    body = await req.json()
    uid = check_init_data(body.get('initData', ''))
    if not uid: return web.json_response({'error': 'auth'}, status=401)
    u = user(uid)
    if not u: return web.json_response({'error': 'nouser'}, status=404)
    n = friends_count(uid)
    L = links(u)
    lv = []
    for x in T.LEVELS:
        item = dict(friends=x['friends'], title=x['title'], open=n >= x['friends'], ticket=bool(x.get('ticket')))
        if x.get('gift') and n >= x['friends']: item['url'] = T.GIFT[x['gift']][1]
        if x.get('limit'):
            item['left'] = max(0, x['limit'] - q('SELECT COUNT(*) c FROM prizes WHERE level=?', x['friends']).fetchone()['c'])
        lv.append(item)
    gifts = [dict(title=T.GIFT[k][0], url=T.GIFT[k][1]) for k in T.REG_GIFTS]
    if u['survey']: gifts.append(dict(title=T.GIFT[T.SURVEY_GIFT][0], url=T.GIFT[T.SURVEY_GIFT][1]))
    return web.json_response(dict(
        name=u['first_name'], vip=bool(u['vip']), phone=bool(u['phone']), friends=n, tickets=tickets(u), prize=T.MAIN_PRIZE,
        ref=L['REF'], share=L['SHARE'], tg=L['TG'], max=L['MAX'], pay=L['PAY'], stream1=setting('stream1') or T.STREAM1, stream2=setting('stream2') or T.STREAM2,
        gifts=gifts, levels=lv, survey=bool(u['survey'])))

async def app_page(req):
    return web.FileResponse(os.path.join(os.path.dirname(__file__), 'cabinet.html'))

async def health(req):
    return web.Response(text='ok')

async def main():
    global bot, BOT_USERNAME
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    me = await bot.get_me(); BOT_USERNAME = me.username
    dp = Dispatcher(); dp.include_router(router)
    app = web.Application()
    app.router.add_get('/', health); app.router.add_get('/app', app_page); app.router.add_post('/api/me', api_me)
    global MX
    if MAX_TOKEN and PUBLIC_URL:
        MX = MaxBot(MAX_TOKEN, db, links, SHEET_URL, PUBLIC_URL)
        await MX.setup(app)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080))).start()
    asyncio.create_task(scheduler())
    if MX: asyncio.create_task(MX.run())
    log.info('started as @%s', BOT_USERNAME)
    await dp.start_polling(bot, allowed_updates=['message', 'callback_query', 'my_chat_member'])

if __name__ == '__main__':
    asyncio.run(main())
