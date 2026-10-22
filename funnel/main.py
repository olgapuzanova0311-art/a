"""Бот автоворонки: человек пишет кодовое слово в Instagram, попадает в бот, выбирает время автовебинара
(каждый день в 12:00 и 19:00 МСК), получает дожимы до эфира, после эфира записывается на консультацию.
Всё, что человек пишет в бот, приходит команде; ответ реплаем уходит человеку.

Переменные окружения:
  BOT_TOKEN   токен бота (обязательно)
  ADMIN_CODE  секретное слово: /admin <слово> делает пользователя админом
  PUBLIC_URL  https-адрес этого сервиса (для ссылок на эфир с отметкой «перешёл»)
  SHEET_URL   адрес Apps Script для Google Таблицы (необязательно)
  DB_PATH     путь к базе (по умолчанию /data/funnel.db)
  PORT        порт веб-сервера (Railway задаёт сам)
"""
import asyncio, csv, hashlib, hmac, io, json, logging, os, sqlite3, time
from datetime import datetime, timedelta
from html import escape

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove)

import texts as T

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('funnel')

BOT_TOKEN = os.environ['BOT_TOKEN']
ADMIN_CODE = os.environ.get('ADMIN_CODE', '')
PUBLIC_URL = os.environ.get('PUBLIC_URL', '').rstrip('/')
SHEET_URL = os.environ.get('SHEET_URL', '')
DB_PATH = os.environ.get('DB_PATH', '/data/funnel.db')

# ---------------- база ----------------
os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)
db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.row_factory = sqlite3.Row
db.execute('PRAGMA journal_mode=WAL')
db.executescript('''
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, phone TEXT, created INTEGER, source TEXT,
  slot INTEGER, slot_at INTEGER, consult INTEGER DEFAULT 0, consult_time TEXT, form TEXT, blocked INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS clicks(user_id INTEGER, ts INTEGER);
CREATE TABLE IF NOT EXISTS sent(user_id INTEGER, key TEXT, PRIMARY KEY(user_id, key));
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS msgmap(chat_id INTEGER, msg_id INTEGER, user_id INTEGER, PRIMARY KEY(chat_id, msg_id));
''')
db.commit()

def q(sql, *a):
    cur = db.execute(sql, a); db.commit(); return cur

def setting(k, default=''):
    r = q('SELECT v FROM settings WHERE k=?', k).fetchone()
    return r['v'] if r else default

def set_setting(k, v):
    q('INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v', k, v)

def user(uid):
    return q('SELECT * FROM users WHERE id=?', uid).fetchone()

def is_admin(uid):
    return q('SELECT 1 FROM admins WHERE id=?', uid).fetchone() is not None

def mark(uid, key):
    try:
        q('INSERT INTO sent(user_id,key) VALUES(?,?)', uid, key); return True
    except sqlite3.IntegrityError:
        return False

def web_len():
    return int(setting('len') or T.WEB_LEN)

# ---------------- время эфиров ----------------
def now_msk():
    return datetime.now(T.MSK)

def slot_dt(ts):
    return datetime.fromtimestamp(ts, T.MSK)

def free_slots(now=None):
    # ближайшие эфиры: сегодня и завтра; если сегодня уже всё прошло, добавляем послезавтра, чтобы выбор был из двух
    now = now or now_msk()
    out = []
    for d in range(3):
        day = (now + timedelta(days=d)).date()
        for h in T.SLOT_HOURS:
            dt = datetime(day.year, day.month, day.day, h, tzinfo=T.MSK)
            if dt > now + timedelta(minutes=2): out.append(dt)
        if d >= 1 and len(out) >= 2: break
    return out

def day_word(dt, now=None):
    n = (dt.date() - (now or now_msk()).date()).days
    return {0: 'сегодня', 1: 'завтра', 2: 'послезавтра'}.get(n, dt.strftime('%d.%m'))

def slot_label(dt):
    return f'{day_word(dt)} в {dt:%H:%M}'

def web_link(u):
    h = slot_dt(u['slot']).hour if u and u['slot'] else None
    return (h and setting(f'web{h}')) or setting('web')

def go_link(uid):
    sig = hmac.new(BOT_TOKEN.encode(), str(uid).encode(), hashlib.sha256).hexdigest()[:12]
    return f'{PUBLIC_URL}/go/{uid}/{sig}'

def clicked(u):
    s = u['slot']
    return q('SELECT 1 FROM clicks WHERE user_id=? AND ts>=? AND ts<=?', u['id'], s - 30 * 60, s + (web_len() + 30) * 60).fetchone() is not None

# ---------------- кнопки и текст ----------------
def kb(rows, u=None):
    if not rows: return None
    out = []
    for row in rows:
        r = []
        for b in row:
            kind = b[0]
            if kind == 'slots':
                out += [[InlineKeyboardButton(text='📅 ' + slot_label(dt).capitalize(), callback_data=f'slot:{int(dt.timestamp())}')] for dt in free_slots()]
            elif kind == 'web':
                link = web_link(u)
                if link and PUBLIC_URL and u: r.append(InlineKeyboardButton(text=b[1], url=go_link(u['id'])))
                elif link: r.append(InlineKeyboardButton(text=b[1], url=link))
                else: r.append(InlineKeyboardButton(text=b[1], callback_data='noweb'))
            elif kind == 'consult':
                r.append(InlineKeyboardButton(text=b[1], callback_data='consult'))
            elif kind == 'cb':
                r.append(InlineKeyboardButton(text=b[1], callback_data=b[2]))
            elif kind == 'url':
                r.append(InlineKeyboardButton(text=b[1], url=b[2]))
        if r: out.append(r)
    return InlineKeyboardMarkup(inline_keyboard=out) if out else None

def fill(text, u):
    dt = slot_dt(u['slot']) if u and u['slot'] else None
    return text.format(name=escape((u['first_name'] if u else None) or 'друг'), title=escape(setting('title') or T.TITLE),
                       points=escape(setting('points') or T.POINTS), time=slot_label(dt) if dt else '', hour=f'{dt:%H:%M}' if dt else '')

bot: Bot
router = Router()

async def send(uid, text, btns=None, circle_key=None):
    u = user(uid)
    try:
        c = circle_key and setting('circle_' + circle_key)
        if c: await bot.send_video_note(uid, c)
        await bot.send_message(uid, fill(text, u), reply_markup=kb(btns, u), disable_web_page_preview=True)
        return True
    except Exception as e:
        msg = str(e)
        if 'blocked' in msg or 'deactivated' in msg or 'chat not found' in msg:
            q('UPDATE users SET blocked=1 WHERE id=?', uid)
        log.info('send %s: %s', uid, msg)
        return False

async def to_sheet(u, event):
    if not SHEET_URL: return
    slot = slot_label(slot_dt(u['slot'])) if u['slot'] else '-'
    payload = dict(event=event, name=u['first_name'] or '', phone=u['phone'] or '', email='', tariff='Автоворонка',
                   consent_data='да (бот)', consent_mailing='да (бот)',
                   page=f'Telegram @{u["username"] or "-"} id {u["id"]} · источник {u["source"] or "-"} · эфир {slot}')
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(SHEET_URL, data=json.dumps(payload, ensure_ascii=False).encode(),
                         headers={'Content-Type': 'text/plain;charset=utf-8'}, timeout=aiohttp.ClientTimeout(total=20))
    except Exception as e:
        log.warning('sheet: %s', e)

# ---------------- команда: уведомления и переписка ----------------
def team_chats():
    sup = setting('support')
    return [int(sup)] if sup else [r['id'] for r in q('SELECT id FROM admins').fetchall()]

def user_head(u):
    nick = f'@{u["username"]}' if u['username'] else f'<a href="tg://user?id={u["id"]}">профиль</a>'
    slot = slot_label(slot_dt(u['slot'])) if u['slot'] else 'не выбрал'
    return (f'<b>{escape(u["first_name"] or "без имени")}</b> {nick} · 🆔 {u["id"]}\n'
            f'🎬 эфир: {slot} · 🏷 {escape(u["source"] or "-")}' + (f' · 📞 {escape(u["phone"])}' if u['phone'] else ''))

async def to_team(u, text, copy_from=None):
    for cid in team_chats():
        try:
            m = await bot.send_message(cid, text + '\n' + user_head(u) + '\n<i>Ответь реплаем, и сообщение уйдёт человеку.</i>', disable_web_page_preview=True)
            q('INSERT OR REPLACE INTO msgmap VALUES(?,?,?)', cid, m.message_id, u['id'])
            if copy_from:
                c = await bot.copy_message(cid, copy_from.chat.id, copy_from.message_id, reply_to_message_id=m.message_id)
                q('INSERT OR REPLACE INTO msgmap VALUES(?,?,?)', cid, c.message_id, u['id'])
        except Exception as e:
            log.warning('to_team %s: %s', cid, e)

# ---------------- вход ----------------
@router.message(CommandStart())
async def start(m: Message, command: CommandObject):
    src = (command.args or '').strip()
    u = user(m.from_user.id)
    if not u:
        q('INSERT INTO users(id,username,first_name,created,source) VALUES(?,?,?,?,?)',
          m.from_user.id, m.from_user.username, m.from_user.first_name, int(time.time()), src or 'бот')
        u = user(m.from_user.id)
        asyncio.create_task(to_sheet(u, 'Автоворонка: пришёл в бот'))
    else:
        q('UPDATE users SET blocked=0, username=?, first_name=? WHERE id=?', m.from_user.username, m.from_user.first_name, u['id'])
    if u['slot'] and u['slot'] > time.time() - web_len() * 60:
        return await send(u['id'], 'Ты записан(а) на эфир <b>{time}</b> 🙌', [[T.WEB], [('cb', '🔁 Выбрать другое время', 'reslot')]])
    await send(u['id'], T.WELCOME, [[T.SLOTS]], 'welcome')
    gift = src and setting('gift_' + src.lower())
    if gift:
        await send(u['id'], T.WELCOME_GIFT, [[('url', '🎁 Забрать подарок', gift)]])

@router.callback_query(F.data.startswith('slot:'))
async def pick_slot(c: CallbackQuery):
    await c.answer()
    u = user(c.from_user.id)
    if not u: return
    ts = int(c.data[5:])
    if ts <= time.time():
        return await send(u['id'], 'Этот эфир уже начался 🙂 Выбери ближайшее время 👇', [[T.SLOTS]])
    q('UPDATE users SET slot=?, slot_at=? WHERE id=?', ts, int(time.time()), u['id'])
    u = user(u['id'])
    try: await c.message.edit_reply_markup(reply_markup=None)
    except Exception: pass
    await send(u['id'], T.PICKED, T.PICKED_BTNS, 'picked')
    asyncio.create_task(to_sheet(u, 'Автоворонка: выбрал время эфира'))

@router.callback_query(F.data == 'reslot')
async def reslot(c: CallbackQuery):
    await c.answer()
    await send(c.from_user.id, T.CHOOSE_AGAIN if free_slots() else T.NO_SLOTS, [[T.SLOTS]])

@router.callback_query(F.data == 'yes')
async def yes(c: CallbackQuery):
    await c.answer('Жду тебя 🙌')
    if mark(c.from_user.id, 'yes:' + str((user(c.from_user.id) or {'slot': 0})['slot'])):
        await send(c.from_user.id, T.YES)

@router.callback_query(F.data == 'noweb')
async def noweb(c: CallbackQuery):
    await c.answer('Ссылка появится здесь перед началом эфира 🙌', show_alert=True)

@router.callback_query(F.data == 'ask')
async def ask(c: CallbackQuery):
    await c.answer()
    await send(c.from_user.id, T.ASK)

# ---------------- консультация ----------------
@router.callback_query(F.data == 'consult')
async def consult(c: CallbackQuery):
    await c.answer()
    u = user(c.from_user.id)
    if not u: return
    if u['consult']:
        return await send(u['id'], T.CONSULT_ALREADY)
    link = setting('consult')
    if link:
        q('UPDATE users SET consult=1 WHERE id=?', u['id'])
        await send(u['id'], T.CONSULT_LINK, [[('url', '📅 Выбрать время', link)]])
        await to_team(user(u['id']), '📞 <b>Перешёл к записи на консультацию</b> (по ссылке)')
        return
    if not u['phone']:
        q("UPDATE users SET form='phone' WHERE id=?", u['id'])
        return await bot.send_message(u['id'], T.CONSULT_ASK_PHONE, reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=T.CONSULT_PHONE_BTN, request_contact=True)]], resize_keyboard=True, one_time_keyboard=True))
    await ask_time(u['id'])

async def ask_time(uid):
    q("UPDATE users SET form='ctime' WHERE id=?", uid)
    await bot.send_message(uid, T.CONSULT_ASK_TIME, reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=f'ct:{i}')] for i, t in enumerate(T.CONSULT_TIMES)]))

@router.message(F.contact)
async def got_contact(m: Message):
    u = user(m.from_user.id)
    if not u: return
    if m.contact.user_id and m.contact.user_id != m.from_user.id:
        return await m.answer('Пришли, пожалуйста, свой номер кнопкой «Поделиться номером» 🙌')
    q('UPDATE users SET phone=? WHERE id=?', m.contact.phone_number, u['id'])
    await m.answer('Спасибо 🙌', reply_markup=ReplyKeyboardRemove())
    await ask_time(u['id'])

@router.callback_query(F.data.startswith('ct:'))
async def consult_time(c: CallbackQuery):
    await c.answer()
    u = user(c.from_user.id)
    if not u or u['consult']: return
    t = T.CONSULT_TIMES[int(c.data[3:])]
    q("UPDATE users SET consult=1, consult_time=?, form=NULL WHERE id=?", t, u['id'])
    u = user(u['id'])
    try: await c.message.edit_text(T.CONSULT_ASK_TIME + '\n\n✅ ' + t)
    except Exception: pass
    await send(u['id'], T.CONSULT_DONE)
    was = 'да' if u['slot'] and clicked(u) else 'нет'
    await to_team(u, f'📞 <b>Новая запись на консультацию</b>\nУдобно: {t} · был на эфире: {was}')
    asyncio.create_task(to_sheet(u, f'Автоворонка: консультация ({t})'))

# ---------------- переписка ----------------
@router.message(F.chat.type == 'private', ~F.text.startswith('/'))
async def private_msg(m: Message):
    # админ ответил реплаем на сообщение человека: пересылаем ответ человеку
    if is_admin(m.from_user.id) and m.reply_to_message:
        return await relay_reply(m)
    u = user(m.from_user.id)
    if not u:
        return await start(m, CommandObject(prefix='/', command='start', args=None))
    if u['form'] == 'phone' and m.text:
        q('UPDATE users SET form=NULL WHERE id=?', u['id'])
        await m.answer('Записала 🙌', reply_markup=ReplyKeyboardRemove())
        q('UPDATE users SET phone=? WHERE id=?', m.text.strip()[:40], u['id'])
        return await ask_time(u['id'])
    await to_team(u, '💬 <b>Сообщение в боте</b>', copy_from=m)
    if mark(u['id'], 'ack:' + datetime.now(T.MSK).strftime('%Y%m%d%H')):
        await m.answer(T.GOT_MSG)

@router.message(F.chat.type.in_({'group', 'supergroup'}), F.reply_to_message)
async def group_reply(m: Message):
    if is_admin(m.from_user.id) and str(m.chat.id) == setting('support'):
        await relay_reply(m)

async def relay_reply(m: Message):
    r = q('SELECT user_id FROM msgmap WHERE chat_id=? AND msg_id=?', m.chat.id, m.reply_to_message.message_id).fetchone()
    if not r:
        return await m.reply('Не поняла, кому ответить: отвечай реплаем на сообщение человека из бота.')
    try:
        await bot.copy_message(r['user_id'], m.chat.id, m.message_id)
        await m.reply('✅ Отправлено')
    except Exception as e:
        await m.reply(f'Не доставлено: {e}')

# ---------------- ссылка на эфир с отметкой ----------------
async def go(req):
    uid, sig = req.match_info['uid'], req.match_info['sig']
    if not hmac.compare_digest(go_link(int(uid)).rsplit('/', 1)[1], sig):
        raise web.HTTPNotFound()
    u = user(int(uid))
    link = web_link(u)
    if not link:
        return web.Response(text='Ссылка на эфир появится в боте перед началом.', content_type='text/plain', charset='utf-8')
    q('INSERT INTO clicks(user_id, ts) VALUES(?,?)', int(uid), int(time.time()))
    raise web.HTTPFound(link)

# ---------------- дожимы ----------------
def planned(step, u):
    S = slot_dt(u['slot'])
    w = step['when']
    if w[0] == 'rel':
        v = w[1]
        if v == 'end': return S + timedelta(minutes=web_len())
        if v == 'end+180': return S + timedelta(minutes=web_len() + 180)
        return S + timedelta(minutes=v)
    if w[0] == 'eve':
        d = S - timedelta(days=1)
        return d.replace(hour=20, minute=0)
    if w[0] == 'morn':
        return S.replace(hour=9 if S.hour < 14 else 10, minute=30 if S.hour < 14 else 0)
    if w[0] == 'next':
        return (S + timedelta(days=1)).replace(hour=w[1], minute=0)

def cond_ok(u, only):
    if not only: return True
    c = clicked(u)
    if only == 'clicked': return c
    if only == 'not_clicked': return not c
    if only == 'clicked_no_consult': return c and not u['consult']
    return True

async def scheduler():
    while True:
        try:
            now = now_msk()
            if setting('paused') != '1':
                for u in q('SELECT * FROM users WHERE blocked=0 AND slot IS NOT NULL AND slot>?', int(time.time()) - 3 * 86400).fetchall():
                    chosen = slot_dt(u['slot_at'])
                    for st in T.STEPS:
                        if st.get('hours') and slot_dt(u['slot']).hour not in st['hours']: continue
                        at = planned(st, u)
                        if at < chosen or not (at <= now < at + timedelta(minutes=st.get('window', 30))): continue
                        if cond_ok(u, st.get('only')) and mark(u['id'], f'{st["key"]}:{u["slot"]}'):
                            await send(u['id'], st['text'], st.get('btns'), st['key']); await asyncio.sleep(0.05)
            day = now.strftime('%Y%m%d')
            if now.hour == 3 and setting('last_backup') != day:
                set_setting('last_backup', day); await send_backup()
        except Exception:
            log.exception('scheduler')
        await asyncio.sleep(20)

# ---------------- админ ----------------
ADMIN_HELP = ('🛠 <b>Ты админ.</b> Команды:\n'
  '/stats · статистика воронки\n'
  '/web ссылка · ссылка на автовебинар (для всех эфиров)\n'
  '/web12 ссылка, /web19 ссылка · отдельные ссылки на эфир в 12:00 и в 19:00\n'
  '/consult ссылка · запись на консультацию по ссылке (/consult off · запись внутри бота)\n'
  '/title текст · тема эфира\n'
  '/points текст · что будет на эфире (3 строки)\n'
  '/len минуты · сколько идёт эфир\n'
  '/gift СЛОВО ссылка · подарок за кодовое слово (ссылка t.me/бот?start=СЛОВО)\n'
  '/support · напиши в группе команды, и сообщения людей будут приходить туда\n'
  '/circle ключ · ответь на кружок: welcome, picked или ключ дожима (eve, morn, m60, p0…)\n'
  '/broadcast · ответь на сообщение, чтобы разослать всем\n'
  '/chain · показать все сообщения воронки по порядку\n'
  '/export · выгрузка в файл для Excel · /backup · бэкап базы\n'
  '/pause, /resume · остановить или включить дожимы\n'
  '/reset_me · забыть тебя, чтобы пройти воронку заново\n\n'
  'Чтобы ответить человеку, ответь реплаем на его сообщение.')

def admin_only(fn):
    async def w(m: Message, command: CommandObject = None):
        if not is_admin(m.from_user.id): return
        return await fn(m, command)
    w.__name__ = fn.__name__
    return w

@router.message(Command('admin'))
async def admin(m: Message, command: CommandObject):
    if ADMIN_CODE and (command.args or '').strip() == ADMIN_CODE:
        q('INSERT OR IGNORE INTO admins(id) VALUES(?)', m.from_user.id)
    if is_admin(m.from_user.id):
        await m.answer(ADMIN_HELP)

def _setter(cmd, key, need_url=True):
    @admin_only
    async def h(m: Message, command):
        v = (command.args or '').strip()
        if cmd == 'consult' and v == 'off':
            set_setting(key, ''); return await m.answer('✅ Запись на консультацию теперь внутри бота.')
        if not v or (need_url and not v.startswith('http')):
            return await m.answer(f'Пришли так: /{cmd} ' + ('https://...' if need_url else 'текст'))
        if cmd == 'len' and not v.isdigit():
            return await m.answer('Пришли число минут: /len 90')
        set_setting(key, v); await m.answer('✅ Сохранено:\n' + escape(v))
    router.message(Command(cmd))(h)

for _c, _k, _u in (('web', 'web', True), ('web12', 'web12', True), ('web19', 'web19', True), ('consult', 'consult', True),
                   ('title', 'title', False), ('points', 'points', False), ('len', 'len', False)):
    _setter(_c, _k, _u)

@router.message(Command('gift'))
@admin_only
async def gift_cmd(m: Message, command):
    a = (command.args or '').split()
    if len(a) != 2 or not a[1].startswith('http'):
        return await m.answer('Пришли так: /gift ВАЙБ https://ссылка-на-подарок')
    set_setting('gift_' + a[0].lower(), a[1])
    await m.answer(f'✅ Подарок за слово {escape(a[0])} сохранён.\nСсылка для Instagram: https://t.me/{BOT_USERNAME}?start={escape(a[0])}\n'
                   'В ссылке только латиница, цифры, _ и -. Кодовое слово в Instagram может быть по-русски, а в ссылке пиши латиницей: vaib.')

@router.message(Command('support'))
async def support_cmd(m: Message):
    if not is_admin(m.from_user.id): return
    if m.chat.type == 'private':
        set_setting('support', '')
        return await m.answer('✅ Сообщения людей будут приходить тебе и другим админам в личку. Чтобы получать их в группе, добавь бота в группу и напиши там /support')
    set_setting('support', str(m.chat.id))
    await m.answer('✅ Теперь сообщения людей и записи на консультацию приходят в эту группу. Отвечай реплаем.')

@router.message(Command('circle'))
@admin_only
async def circle(m: Message, command):
    key = (command.args or '').strip()
    keys = ['welcome', 'picked'] + [s['key'] for s in T.STEPS]
    if not (m.reply_to_message and m.reply_to_message.video_note) or key not in keys:
        return await m.answer('Запиши кружок в этот чат и ответь на него: /circle ключ\nКлючи: ' + ', '.join(keys))
    set_setting('circle_' + key, m.reply_to_message.video_note.file_id)
    await m.answer(f'✅ Кружок перед сообщением «{key}» сохранён.')

@router.message(Command('pause'))
@admin_only
async def pause_cmd(m: Message, command):
    set_setting('paused', '1'); await m.answer('⏸ Дожимы на паузе. Включить: /resume')

@router.message(Command('resume'))
@admin_only
async def resume_cmd(m: Message, command):
    set_setting('paused', '0'); await m.answer('▶️ Дожимы снова работают.')

@router.message(Command('stats'))
@admin_only
async def stats(m: Message, command):
    c = lambda sql, *a: q(sql, *a).fetchone()[0]
    now = int(time.time())
    came = c('SELECT COUNT(DISTINCT c.user_id) FROM clicks c JOIN users u ON u.id=c.user_id WHERE c.ts>=u.slot-1800')
    picked = c('SELECT COUNT(*) FROM users WHERE slot IS NOT NULL')
    text = (f'📊 <b>Воронка</b>\n'
            f'Пришли в бот: <b>{c("SELECT COUNT(*) FROM users")}</b>\n'
            f'Выбрали время: <b>{picked}</b>\n'
            f'Перешли на эфир: <b>{came}</b>' + (f' ({came * 100 // picked}%)' if picked else '') + '\n'
            f'Записались на консультацию: <b>{c("SELECT COUNT(*) FROM users WHERE consult=1")}</b>\n'
            f'Заблокировали бота: <b>{c("SELECT COUNT(*) FROM users WHERE blocked=1")}</b>\n\n<b>Ближайшие эфиры</b>\n')
    for r in q('SELECT slot, COUNT(*) n FROM users WHERE slot>? AND blocked=0 GROUP BY slot ORDER BY slot', now - web_len() * 60).fetchall():
        text += f'{slot_label(slot_dt(r["slot"]))}: {r["n"]} чел.\n'
    text += '\n<b>Кодовые слова</b>\n' + '\n'.join(f'{escape(r["source"] or "-")}: {r["n"]}' for r in
                                                 q('SELECT source, COUNT(*) n FROM users GROUP BY source ORDER BY n DESC LIMIT 15').fetchall())
    text += (f'\n\nСсылка на эфир: {escape(setting("web") or "не задана")}' + (f'\n12:00: {escape(setting("web12"))}' if setting('web12') else '')
             + (f'\n19:00: {escape(setting("web19"))}' if setting('web19') else '') + f'\nКонсультация: {escape(setting("consult") or "запись в боте")}')
    await m.answer(text, disable_web_page_preview=True)

@router.message(Command('chain'))
@admin_only
async def chain(m: Message, command):
    uid = m.from_user.id
    if not user(uid) or not user(uid)['slot']:
        return await m.answer('Сначала нажми /start и выбери время, чтобы в текстах подставилось твоё имя и время.')
    await send(uid, T.WELCOME, [[T.SLOTS]]); await send(uid, T.PICKED, T.PICKED_BTNS)
    names = {'eve': 'накануне в 20:00', 'morn': 'в день эфира утром', 'next': 'на следующий день'}
    for i, st in enumerate(T.STEPS, 1):
        w = st['when']
        when = names.get(w[0], '') + (f' в {w[1]}:00' if w[0] == 'next' else '')
        if w[0] == 'rel':
            v = w[1]
            when = {'end': 'после эфира', 'end+180': 'через 3 часа после эфира'}.get(v) or (f'за {-v} мин до начала' if v < 0 else f'через {v} мин после начала' if v else 'в начале эфира')
        who = {'not_clicked': 'кто не перешёл на эфир', 'clicked': 'кто был на эфире', 'clicked_no_consult': 'кто был на эфире и не записался'}.get(st.get('only'), 'всем')
        await m.answer(f'<i>#{i} · {st["key"]} · {when} · {who}</i>')
        await send(uid, st['text'], st.get('btns')); await asyncio.sleep(0.3)
    await m.answer('✅ Это вся воронка. Правки присылай по номеру или ключу.')

@router.message(Command('broadcast'))
@admin_only
async def broadcast(m: Message, command):
    if not m.reply_to_message:
        return await m.answer('Ответь командой /broadcast на сообщение, которое нужно разослать всем.')
    set_setting('bc_msg', f'{m.chat.id}:{m.reply_to_message.message_id}')
    n = q('SELECT COUNT(*) FROM users WHERE blocked=0').fetchone()[0]
    await m.answer(f'Разослать всем ({n} чел.)?', reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text='✅ Да', callback_data='bc:go'), InlineKeyboardButton(text='Отмена', callback_data='bc:no')]]))

@router.callback_query(F.data.startswith('bc:'))
async def bc_go(c: CallbackQuery):
    if not is_admin(c.from_user.id): return await c.answer()
    await c.answer()
    if c.data == 'bc:no': return await c.message.edit_text('Отменено.')
    chat, mid = setting('bc_msg').split(':')
    await c.message.edit_text('🚀 Рассылка пошла…')
    ok = 0
    for r in q('SELECT id FROM users WHERE blocked=0').fetchall():
        try:
            await bot.copy_message(r['id'], int(chat), int(mid)); ok += 1
        except Exception as e:
            if 'blocked' in str(e) or 'deactivated' in str(e): q('UPDATE users SET blocked=1 WHERE id=?', r['id'])
        await asyncio.sleep(0.05)
    await bot.send_message(c.from_user.id, f'✅ Доставлено: {ok}')

def export_csv():
    buf = io.StringIO(); w = csv.writer(buf, delimiter=';')
    w.writerow(['id', 'ник', 'имя', 'телефон', 'пришёл', 'кодовое слово', 'эфир', 'перешёл на эфир', 'консультация', 'удобное время', 'заблокировал'])
    for r in q('SELECT * FROM users ORDER BY created').fetchall():
        w.writerow([r['id'], r['username'], r['first_name'], r['phone'], datetime.fromtimestamp(r['created'], T.MSK).strftime('%d.%m.%Y %H:%M'),
                    r['source'], slot_dt(r['slot']).strftime('%d.%m %H:%M') if r['slot'] else '', 'да' if r['slot'] and clicked(r) else '',
                    'да' if r['consult'] else '', r['consult_time'], r['blocked']])
    return ('﻿' + buf.getvalue()).encode('utf-8')

@router.message(Command('export'))
@admin_only
async def export(m: Message, command):
    await m.answer_document(BufferedInputFile(export_csv(), filename='avtovoronka.csv'))

async def send_backup(chat_ids=None):
    ids = chat_ids or [r['id'] for r in q('SELECT id FROM admins').fetchall()]
    path = DB_PATH + '.bak'
    dst = sqlite3.connect(path); db.backup(dst); dst.close()
    with open(path, 'rb') as f: data = f.read()
    stamp = now_msk().strftime('%d.%m_%H-%M')
    for cid in ids:
        try:
            await bot.send_document(cid, BufferedInputFile(data, filename=f'funnel_backup_{stamp}.db'), caption='💾 Бэкап базы автоворонки')
            await bot.send_document(cid, BufferedInputFile(export_csv(), filename=f'avtovoronka_{stamp}.csv'))
        except Exception as e:
            log.warning('backup to %s: %s', cid, e)

@router.message(Command('backup'))
@admin_only
async def backup_cmd(m: Message, command):
    await send_backup([m.from_user.id])

@router.message(Command('reset_me'))
@admin_only
async def reset_me(m: Message, command):
    uid = m.from_user.id
    for t in ('sent', 'clicks'): q(f'DELETE FROM {t} WHERE user_id=?', uid)
    q('DELETE FROM users WHERE id=?', uid)
    await m.answer('🧹 Готово, я тебя забыла. Нажми /start и пройди воронку как новый человек.', reply_markup=ReplyKeyboardRemove())

# ---------------- запуск ----------------
BOT_USERNAME = ''

async def health(req):
    return web.Response(text='ok')

async def main():
    global bot, BOT_USERNAME
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    BOT_USERNAME = (await bot.get_me()).username
    dp = Dispatcher(); dp.include_router(router)
    app = web.Application()
    app.router.add_get('/', health); app.router.add_get('/go/{uid}/{sig}', go)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080))).start()
    asyncio.create_task(scheduler())
    log.info('started as @%s', BOT_USERNAME)
    await dp.start_polling(bot, allowed_updates=['message', 'callback_query'])

if __name__ == '__main__':
    asyncio.run(main())
