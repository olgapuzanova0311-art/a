"""Автовебинар в боте регистрации: новый человек выбирает время (12:00 или 19:00 МСК), второй день идёт на следующий день
в то же время. Дожимы до и после эфира, запись на консультацию, переписка с командой.
Старые участники интенсива (funnel=0) сюда не попадают: их сообщения и /start обрабатывает main.py как раньше.

Подключение в main.py: avto.init(модуль main), dp.include_router(avto.router) до основного роутера, avto.setup_web(app),
asyncio.create_task(avto.scheduler()).
"""
import asyncio, csv, hashlib, hmac, io, logging, sqlite3, time
from datetime import datetime, timedelta
from html import escape

from aiohttp import web
from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove)

import avto_texts as A

log = logging.getLogger('avto')
M = None          # модуль main: q, setting, set_setting, user, is_admin, mark, to_sheet, bot
router = Router()

def init(main_module):
    global M
    M = main_module
    for col, typ in (('funnel', 'INTEGER DEFAULT 0'), ('slot', 'INTEGER'), ('slot_at', 'INTEGER'), ('slot2', 'INTEGER'),
                     ('consult', 'INTEGER DEFAULT 0'), ('consult_time', 'TEXT'), ('form', 'TEXT')):
        try: M.db.execute(f'ALTER TABLE users ADD COLUMN {col} {typ}')
        except sqlite3.OperationalError: pass
    M.db.executescript('''
    CREATE TABLE IF NOT EXISTS clicks(user_id INTEGER, ts INTEGER);
    CREATE TABLE IF NOT EXISTS msgmap(chat_id INTEGER, msg_id INTEGER, user_id INTEGER, PRIMARY KEY(chat_id, msg_id));
    ''')
    M.db.commit()

def q(*a): return M.q(*a)
def setting(*a): return M.setting(*a)
def user(uid): return M.user(uid)

def is_funnel(uid):
    u = user(uid)
    return bool(u and u['funnel'])

def web_len():
    return int(setting('avto_len') or A.WEB_LEN)

# ---------------- время эфиров ----------------
def now_msk():
    return datetime.now(A.MSK)

def dt(ts):
    return datetime.fromtimestamp(ts, A.MSK)

def free_slots(after=None):
    # ближайшие эфиры на сегодня и завтра; если сегодня всё прошло, добавляем послезавтра, чтобы выбор был из двух
    now = now_msk()
    base = max(now, after) if after else now
    out = []
    for d in range(4):
        day = (base + timedelta(days=d)).date()
        for h in A.SLOT_HOURS:
            x = datetime(day.year, day.month, day.day, h, tzinfo=A.MSK)
            if x > base + timedelta(minutes=2): out.append(x)
        if d >= 1 and len(out) >= 2: break
    return out

def label(x):
    n = (x.date() - now_msk().date()).days
    return f'{ {0: "сегодня", 1: "завтра", 2: "послезавтра"}.get(n, x.strftime("%d.%m"))} в {x:%H:%M}'

def cur_day(u):
    # какой день эфира сейчас актуален для ссылки: после конца первого дня ведём на второй
    return 2 if u['slot2'] and time.time() > u['slot'] + (web_len() + 120) * 60 else 1

def web_link(u):
    day = cur_day(u)
    h = dt(u['slot2'] if day == 2 else u['slot']).hour
    p = 'avto_web2' if day == 2 else 'avto_web'
    return setting(f'{p}{h}') or setting(p) or (A.WEB2 if day == 2 else A.WEB1)

def sig(uid):
    return hmac.new(M.BOT_TOKEN.encode(), f'go{uid}'.encode(), hashlib.sha256).hexdigest()[:12]

def go_link(uid):
    return f'{M.PUBLIC_URL}/go/{uid}/{sig(uid)}'

def clicked(u, day):
    s = u['slot2'] if day == 2 else u['slot']
    if not s: return False
    return q('SELECT 1 FROM clicks WHERE user_id=? AND ts>=? AND ts<=?', u['id'], s - 90 * 60, s + (web_len() + 30) * 60).fetchone() is not None

# ---------------- кнопки и текст ----------------
def kb(rows, u):
    if not rows: return None
    out = []
    for row in rows:
        r = []
        for b in row:
            kind = b[0]
            if kind == 'slots':
                out += [[InlineKeyboardButton(text='📅 ' + label(x).capitalize(), callback_data=f'av:slot:{int(x.timestamp())}')] for x in free_slots()]
            elif kind == 'slots2':
                after = dt(u['slot']) + timedelta(minutes=web_len()) if u and u['slot'] else None
                out += [[InlineKeyboardButton(text='📅 ' + label(x).capitalize(), callback_data=f'av:slot2:{int(x.timestamp())}')] for x in free_slots(after)]
            elif kind == 'web':
                link = u and u['slot'] and web_link(u)
                if link and M.PUBLIC_URL: r.append(InlineKeyboardButton(text=b[1], url=go_link(u['id'])))
                elif link: r.append(InlineKeyboardButton(text=b[1], url=link))
                else: r.append(InlineKeyboardButton(text=b[1], callback_data='av:noweb'))
            elif kind == 'consult':
                r.append(InlineKeyboardButton(text=b[1], callback_data='av:consult'))
            elif kind == 'cb':
                r.append(InlineKeyboardButton(text=b[1], callback_data='av:' + b[2]))
            elif kind == 'url':
                r.append(InlineKeyboardButton(text=b[1], url=b[2]))
        if r: out.append(r)
    return InlineKeyboardMarkup(inline_keyboard=out) if out else None

def fill(text, u):
    d1 = dt(u['slot']) if u and u['slot'] else None
    d2 = dt(u['slot2']) if u and u['slot2'] else None
    return text.format(name=escape((u['first_name'] if u else None) or 'друг'),
                       time=label(d1) if d1 else '', hour=f'{d1:%H:%M}' if d1 else '',
                       time2=label(d2) if d2 else '', hour2=f'{d2:%H:%M}' if d2 else '')

async def send(uid, text, btns=None, circle_key=None):
    u = user(uid)
    try:
        c = circle_key and setting('avto_circle_' + circle_key)
        if c: await M.bot.send_video_note(uid, c)
        await M.bot.send_message(uid, fill(text, u), reply_markup=kb(btns, u), disable_web_page_preview=True)
        return True
    except Exception as e:
        msg = str(e)
        if 'blocked' in msg or 'deactivated' in msg or 'chat not found' in msg:
            q('UPDATE users SET blocked=1 WHERE id=?', uid)
        log.info('send %s: %s', uid, msg)
        return False

def sheet(u, event):
    asyncio.create_task(M.to_sheet(u, event + (f' · эфир {label(dt(u["slot"]))}' if u['slot'] else '')))

# ---------------- команда: уведомления и переписка ----------------
def team_chats():
    sup = setting('avto_support')
    return [int(sup)] if sup else [r['id'] for r in q('SELECT id FROM admins').fetchall()]

def head(u):
    nick = f'@{u["username"]}' if u['username'] else f'<a href="tg://user?id={u["id"]}">профиль</a>'
    s1 = label(dt(u['slot'])) if u['slot'] else 'не выбрал'
    return (f'<b>{escape(u["first_name"] or "без имени")}</b> {nick} · 🆔 {u["id"]}\n'
            f'🎬 день 1: {s1} · был: {"да" if clicked(u, 1) else "нет"} · день 2: {"был" if clicked(u, 2) else "нет"}\n'
            f'🏷 {escape(u["source"] or "-")}' + (f' · 📞 {escape(u["phone"])}' if u['phone'] else ''))

async def to_team(u, text, copy_from=None):
    for cid in team_chats():
        try:
            m = await M.bot.send_message(cid, text + '\n' + head(u) + '\n<i>Ответь реплаем, и сообщение уйдёт человеку.</i>', disable_web_page_preview=True)
            q('INSERT OR REPLACE INTO msgmap VALUES(?,?,?)', cid, m.message_id, u['id'])
            if copy_from:
                c = await M.bot.copy_message(cid, copy_from.chat.id, copy_from.message_id, reply_to_message_id=m.message_id)
                q('INSERT OR REPLACE INTO msgmap VALUES(?,?,?)', cid, c.message_id, u['id'])
        except Exception as e:
            log.warning('to_team %s: %s', cid, e)

def mapped(m: Message):
    r = m.reply_to_message and q('SELECT user_id FROM msgmap WHERE chat_id=? AND msg_id=?', m.chat.id, m.reply_to_message.message_id).fetchone()
    return r['user_id'] if r else None

# ---------------- вход ----------------
@router.message(CommandStart())
async def start(m: Message, command: CommandObject):
    u = user(m.from_user.id)
    if u and not u['funnel']:
        raise SkipHandler()          # старый участник интенсива: обычное меню бота
    if not u:
        src = (command.args or '').strip()
        q('INSERT INTO users(id,username,first_name,created,source,ref_code,funnel) VALUES(?,?,?,?,?,?,1)',
          m.from_user.id, m.from_user.username, m.from_user.first_name, int(time.time()), src or 'бот', M.secrets.token_hex(4))
        u = user(m.from_user.id)
        sheet(u, 'Автовеб: пришёл в бот')
    else:
        q('UPDATE users SET blocked=0, username=?, first_name=? WHERE id=?', m.from_user.username, m.from_user.first_name, u['id'])
    last = u['slot2'] or u['slot']
    if last and last > time.time() - web_len() * 60:
        return await send(u['id'], A.ALREADY, [[A.WEB], [A.OTHER_TIME]])
    await send(u['id'], A.WELCOME, [[A.SLOTS]], 'welcome')

@router.callback_query(F.data.startswith('av:slot:'))
async def pick(c: CallbackQuery):
    await c.answer()
    u = user(c.from_user.id)
    if not u: return
    ts = int(c.data.split(':')[2])
    if ts <= time.time():
        return await send(u['id'], 'Этот эфир уже начался 🙂 Выбери ближайшее время 👇', [[A.SLOTS]])
    first = not u['slot']
    q('UPDATE users SET slot=?, slot2=?, slot_at=? WHERE id=?', ts, ts + 86400, int(time.time()), u['id'])
    u = user(u['id'])
    try: await c.message.edit_reply_markup(reply_markup=None)
    except Exception: pass
    await send(u['id'], A.PICKED, A.PICKED_BTNS, 'picked')
    if first:
        await send(u['id'], A.PICKED_GIFTS, [[('url', '🎁 ' + t, l)] for t, l in A.GIFTS])
    sheet(u, 'Автовеб: выбрал время')

@router.callback_query(F.data.startswith('av:slot2:'))
async def pick2(c: CallbackQuery):
    await c.answer()
    u = user(c.from_user.id)
    if not u: return
    ts = int(c.data.split(':')[2])
    if ts <= time.time():
        return await send(u['id'], 'Этот эфир уже начался 🙂 Выбери ближайшее время 👇', [[A.SLOTS2]])
    q('UPDATE users SET slot2=? WHERE id=?', ts, u['id'])
    try: await c.message.edit_reply_markup(reply_markup=None)
    except Exception: pass
    await send(u['id'], A.PICKED2)

@router.callback_query(F.data == 'av:reslot')
async def reslot(c: CallbackQuery):
    await c.answer()
    await send(c.from_user.id, A.CHOOSE_AGAIN, [[A.SLOTS]])

@router.callback_query(F.data == 'av:reslot2')
async def reslot2(c: CallbackQuery):
    await c.answer()
    await send(c.from_user.id, A.CHOOSE_AGAIN2, [[A.SLOTS2]])

@router.callback_query(F.data == 'av:yes')
async def yes(c: CallbackQuery):
    await c.answer('Жду тебя 🙌')
    u = user(c.from_user.id)
    if u and M.mark(u['id'], f'av_yes:{u["slot"]}'):
        await send(u['id'], A.YES)

@router.callback_query(F.data == 'av:noweb')
async def noweb(c: CallbackQuery):
    await c.answer('Ссылка появится здесь перед началом эфира 🙌', show_alert=True)

@router.callback_query(F.data == 'av:ask')
async def ask(c: CallbackQuery):
    await c.answer()
    await send(c.from_user.id, A.ASK)

# ---------------- консультация ----------------
@router.callback_query(F.data == 'av:consult')
async def consult(c: CallbackQuery):
    await c.answer()
    u = user(c.from_user.id)
    if not u: return
    if u['consult']:
        return await send(u['id'], A.CONSULT_ALREADY)
    link = setting('avto_consult')
    if link:
        q('UPDATE users SET consult=1 WHERE id=?', u['id'])
        await send(u['id'], A.CONSULT_LINK, [[('url', '📅 Выбрать время', link)]])
        return await to_team(user(u['id']), '📞 <b>Перешёл к записи на консультацию</b> (по ссылке)')
    if not u['phone']:
        q("UPDATE users SET form='phone' WHERE id=?", u['id'])
        return await M.bot.send_message(u['id'], A.CONSULT_ASK_PHONE, reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=A.CONSULT_PHONE_BTN, request_contact=True)]], resize_keyboard=True, one_time_keyboard=True))
    await ask_time(u['id'])

async def ask_time(uid):
    q("UPDATE users SET form='ctime' WHERE id=?", uid)
    await M.bot.send_message(uid, A.CONSULT_ASK_TIME, reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=f'av:ct:{i}')] for i, t in enumerate(A.CONSULT_TIMES)]))

@router.message(F.contact, F.from_user.func(lambda u: is_funnel(u.id)))
async def got_contact(m: Message):
    if m.contact.user_id and m.contact.user_id != m.from_user.id:
        return await m.answer('Пришли, пожалуйста, свой номер кнопкой «Поделиться номером» 🙌')
    q('UPDATE users SET phone=? WHERE id=?', m.contact.phone_number, m.from_user.id)
    await m.answer('Спасибо 🙌', reply_markup=ReplyKeyboardRemove())
    await ask_time(m.from_user.id)

@router.callback_query(F.data.startswith('av:ct:'))
async def consult_time(c: CallbackQuery):
    await c.answer()
    u = user(c.from_user.id)
    if not u or u['consult']: return
    t = A.CONSULT_TIMES[int(c.data.split(':')[2])]
    q('UPDATE users SET consult=1, consult_time=?, form=NULL WHERE id=?', t, u['id'])
    u = user(u['id'])
    try: await c.message.edit_text(A.CONSULT_ASK_TIME + '\n\n✅ ' + t)
    except Exception: pass
    await send(u['id'], A.CONSULT_DONE)
    await to_team(u, f'📞 <b>Новая запись на консультацию</b>\nУдобно: {t}')
    sheet(u, f'Автовеб: консультация ({t})')

# ---------------- переписка ----------------
@router.message(F.chat.type == 'private', ~F.text.startswith('/'), F.func(lambda m: M.is_admin(m.from_user.id) and mapped(m)))
async def admin_reply(m: Message):
    await relay(m)

@router.message(F.chat.type.in_({'group', 'supergroup'}), F.reply_to_message)
async def group_reply(m: Message):
    if M.is_admin(m.from_user.id) and str(m.chat.id) == setting('avto_support'):
        await relay(m)

async def relay(m: Message):
    uid = mapped(m)
    if not uid:
        return await m.reply('Не поняла, кому ответить: отвечай реплаем на сообщение человека из бота.')
    try:
        await M.bot.copy_message(uid, m.chat.id, m.message_id)
        await m.reply('✅ Отправлено')
    except Exception as e:
        await m.reply(f'Не доставлено: {e}')

@router.message(F.chat.type == 'private', ~F.text.startswith('/'), F.from_user.func(lambda u: is_funnel(u.id)))
async def from_user(m: Message):
    u = user(m.from_user.id)
    if u['form'] == 'phone' and m.text:
        q('UPDATE users SET phone=?, form=NULL WHERE id=?', m.text.strip()[:40], u['id'])
        await m.answer('Записала 🙌', reply_markup=ReplyKeyboardRemove())
        return await ask_time(u['id'])
    await to_team(u, '💬 <b>Сообщение в боте</b>', copy_from=m)
    if M.mark(u['id'], 'av_ack:' + now_msk().strftime('%Y%m%d%H')):
        await m.answer(A.GOT_MSG)

# ---------------- ссылка на эфир с отметкой «перешёл» ----------------
async def go(req):
    uid = int(req.match_info['uid'])
    if not hmac.compare_digest(sig(uid), req.match_info['sig']):
        raise web.HTTPNotFound()
    u = user(uid)
    link = u and u['slot'] and web_link(u)
    if not link:
        return web.Response(text='Ссылка на эфир появится в боте перед началом.', content_type='text/plain', charset='utf-8')
    q('INSERT INTO clicks(user_id, ts) VALUES(?,?)', uid, int(time.time()))
    raise web.HTTPFound(link)

def setup_web(app):
    app.router.add_get('/go/{uid}/{sig}', go)

# ---------------- дожимы ----------------
def planned(st, u):
    S = dt(u['slot2'] if st['day'] == 2 else u['slot'])
    w = st['when']
    if w[0] == 'rel': return S + timedelta(minutes=w[1])
    if w[0] == 'end': return S + timedelta(minutes=web_len() + w[1])
    if w[0] == 'eve': return (S - timedelta(days=1)).replace(hour=20, minute=0)
    if w[0] == 'morn': return S.replace(hour=9, minute=30) if S.hour < 14 else S.replace(hour=10, minute=0)
    if w[0] == 'next': return (S + timedelta(days=1)).replace(hour=w[1], minute=0)

def cond_ok(u, st):
    only = st.get('only')
    if not only: return True
    if only == 'nocons': return not u['consult']
    if only in ('any_nocons', 'none'):
        any_c = clicked(u, 1) or clicked(u, 2)
        return (any_c and not u['consult']) if only == 'any_nocons' else not any_c
    c = clicked(u, st['day'])
    if only == 'c': return c
    if only == 'nc': return not c
    if only == 'c_nocons': return c and not u['consult']
    return True

async def tick(now=None):
    now = now or now_msk()
    for u in q('SELECT * FROM users WHERE funnel=1 AND blocked=0 AND slot IS NOT NULL AND slot2>?', int(time.time()) - 3 * 86400).fetchall():
        chosen = dt(u['slot_at'])
        for st in A.STEPS:
            S = u['slot2'] if st['day'] == 2 else u['slot']
            if st.get('hours') and dt(S).hour not in st['hours']: continue
            at = planned(st, u)
            if at < chosen or not (at <= now < at + timedelta(minutes=st.get('window', 30))): continue
            if cond_ok(u, st) and M.mark(u['id'], f'av{st["day"]}_{st["key"]}:{S}'):
                await send(u['id'], st['text'], st.get('btns'), f'{st["day"]}_{st["key"]}'); await asyncio.sleep(0.05)

async def scheduler():
    while True:
        try:
            if setting('avto_paused') != '1': await tick()
        except Exception:
            log.exception('avto scheduler')
        await asyncio.sleep(20)

# ---------------- админ ----------------
HELP = ('🎬 <b>Автовеб</b>\n'
  '/avto · статистика автовеба\n'
  '/web ссылка · ссылка на день 1 (/web12, /web19 · отдельно на 12:00 и 19:00)\n'
  '/web2 ссылка · ссылка на день 2 (/web2_12, /web2_19)\n'
  '/consult ссылка · запись на консультацию по ссылке (/consult off · запись внутри бота)\n'
  '/len минуты · сколько идёт эфир\n'
  '/support · напиши в группе команды, и сообщения людей будут приходить туда\n'
  '/avtocircle ключ · ответь на кружок, он придёт перед сообщением (welcome, picked, 1_m5, 2_p0…)\n'
  '/avtochain · показать все сообщения автовеба по порядку\n'
  '/avtoexport · выгрузка автовеба в Excel\n'
  '/avtopause, /avtoresume · остановить или включить дожимы\n\n'
  'Ссылка для Instagram: t.me/{bot}?start=слово (слово латиницей, по нему видно источник).\n'
  'Чтобы ответить человеку, ответь реплаем на его сообщение.')

def admin_cmd(*names):
    def deco(fn):
        async def h(m: Message, command: CommandObject):
            if M.is_admin(m.from_user.id): await fn(m, (command.args or '').strip())
        h.__name__ = fn.__name__
        router.message(Command(*names))(h)
        return fn
    return deco

@admin_cmd('avtohelp')
async def help_cmd(m, arg):
    await m.answer(HELP.format(bot=M.BOT_USERNAME))

def _setter(cmd, key, kind='url'):
    @admin_cmd(cmd)
    async def h(m, v):
        if cmd == 'consult' and v == 'off':
            M.set_setting(key, ''); return await m.answer('✅ Запись на консультацию теперь внутри бота.')
        if kind == 'url' and not v.startswith('http'): return await m.answer(f'Пришли так: /{cmd} https://...')
        if kind == 'int' and not v.isdigit(): return await m.answer(f'Пришли число: /{cmd} 90')
        M.set_setting(key, v); await m.answer('✅ Сохранено:\n' + escape(v))

for _c, _k, _t in (('web', 'avto_web', 'url'), ('web12', 'avto_web12', 'url'), ('web19', 'avto_web19', 'url'),
                   ('web2', 'avto_web2', 'url'), ('web2_12', 'avto_web212', 'url'), ('web2_19', 'avto_web219', 'url'),
                   ('consult', 'avto_consult', 'url'), ('len', 'avto_len', 'int')):
    _setter(_c, _k, _t)

@router.message(Command('support'))
async def support_cmd(m: Message):
    if not M.is_admin(m.from_user.id): return
    if m.chat.type == 'private':
        M.set_setting('avto_support', '')
        return await m.answer('✅ Сообщения людей приходят тебе и другим админам в личку. Чтобы получать их в группе, добавь бота в группу и напиши там /support')
    M.set_setting('avto_support', str(m.chat.id))
    await m.answer('✅ Теперь сообщения людей и записи на консультацию приходят в эту группу. Отвечай реплаем.')

def circle_keys():
    return ['welcome', 'picked'] + [f'{s["day"]}_{s["key"]}' for s in A.STEPS]

@admin_cmd('avtocircle')
async def circle(m, key):
    if not (m.reply_to_message and m.reply_to_message.video_note) or key not in circle_keys():
        return await m.answer('Запиши кружок в этот чат и ответь на него: /avtocircle ключ\nКлючи: ' + ', '.join(circle_keys()))
    M.set_setting('avto_circle_' + key, m.reply_to_message.video_note.file_id)
    await m.answer(f'✅ Кружок перед сообщением «{key}» сохранён.')

@admin_cmd('avtopause')
async def pause(m, a):
    M.set_setting('avto_paused', '1'); await m.answer('⏸ Дожимы автовеба на паузе. Включить: /avtoresume')

@admin_cmd('avtoresume')
async def resume(m, a):
    M.set_setting('avto_paused', '0'); await m.answer('▶️ Дожимы автовеба снова работают.')

@admin_cmd('avto')
async def stats(m, a):
    c = lambda sql, *x: q(sql, *x).fetchone()[0]
    rows = q('SELECT * FROM users WHERE funnel=1').fetchall()
    picked = [r for r in rows if r['slot']]
    d1 = sum(clicked(r, 1) for r in picked); d2 = sum(clicked(r, 2) for r in picked)
    pct = lambda n: f' ({n * 100 // len(picked)}%)' if picked else ''
    text = (f'🎬 <b>Автовеб</b>\n'
            f'Пришли в бот: <b>{len(rows)}</b>\n'
            f'Выбрали время: <b>{len(picked)}</b>\n'
            f'Дошли на день 1: <b>{d1}</b>{pct(d1)}\n'
            f'Дошли на день 2: <b>{d2}</b>{pct(d2)}\n'
            f'Записались на консультацию: <b>{sum(1 for r in rows if r["consult"])}</b>\n'
            f'Заблокировали бота: <b>{sum(1 for r in rows if r["blocked"])}</b>\n\n<b>Ближайшие эфиры (день 1)</b>\n')
    for r in q('SELECT slot, COUNT(*) n FROM users WHERE funnel=1 AND slot>? AND blocked=0 GROUP BY slot ORDER BY slot', int(time.time()) - web_len() * 60).fetchall():
        text += f'{label(dt(r["slot"]))}: {r["n"]} чел.\n'
    text += '\n<b>Источники</b>\n' + '\n'.join(f'{escape(r["source"] or "-")}: {r["n"]}' for r in
                                             q('SELECT source, COUNT(*) n FROM users WHERE funnel=1 GROUP BY source ORDER BY n DESC LIMIT 15').fetchall())
    links = [(k, setting('avto_' + k) or {'web': A.WEB1, 'web2': A.WEB2}.get(k, '')) for k in ('web', 'web12', 'web19', 'web2', 'web212', 'web219', 'consult')]
    text += '\n\n<b>Ссылки</b>\n' + '\n'.join(f'{k}: {escape(v)}' for k, v in links if v) if any(v for _, v in links) else '\n\n⚠️ Ссылка на эфир не задана: /web https://...'
    await m.answer(text, disable_web_page_preview=True)

@admin_cmd('avtochain')
async def chain(m, a):
    uid = m.from_user.id
    u = user(uid)
    if not u or not u['slot']:
        return await m.answer('Чтобы в текстах подставились имя и время: /reset_me, потом /start и выбери время. Потом снова /avtochain.')
    await send(uid, A.WELCOME, [[A.SLOTS]]); await send(uid, A.PICKED, A.PICKED_BTNS)
    await send(uid, A.PICKED_GIFTS, [[('url', '🎁 ' + t, l)] for t, l in A.GIFTS])
    names = {'eve': 'накануне в 20:00', 'morn': 'утром в день эфира'}
    who_map = {'any_nocons': 'кто был хоть на одном дне и не записался', 'none': 'кто не был ни на одном дне', 'nc': 'кто не перешёл на эфир', 'c': 'кто был на эфире', 'c_nocons': 'кто был и не записался на консультацию', 'nocons': 'кто не записался на консультацию'}
    for i, st in enumerate(A.STEPS, 1):
        w = st['when']
        if w[0] == 'rel': when = f'за {-w[1]} мин до начала' if w[1] < 0 else (f'через {w[1]} мин после начала' if w[1] else 'в начале эфира')
        elif w[0] == 'end': when = 'сразу после эфира' if not w[1] else f'через {w[1] // 60} ч после эфира'
        elif w[0] == 'next': when = f'на следующий день в {w[1]}:00'
        else: when = names[w[0]]
        await m.answer(f'<i>#{i} · день {st["day"]} · {when} · {who_map.get(st.get("only"), "всем")} · ключ {st["day"]}_{st["key"]}</i>')
        await send(uid, st['text'], st.get('btns')); await asyncio.sleep(0.3)
    await m.answer('✅ Это весь автовеб. Правки присылай по номеру.')

@admin_cmd('avtoexport')
async def export(m, a):
    buf = io.StringIO(); w = csv.writer(buf, delimiter=';')
    w.writerow(['id', 'ник', 'имя', 'телефон', 'пришёл', 'источник', 'день 1', 'был на дне 1', 'день 2', 'был на дне 2', 'консультация', 'удобное время', 'заблокировал'])
    for r in q('SELECT * FROM users WHERE funnel=1 ORDER BY created').fetchall():
        w.writerow([r['id'], r['username'], r['first_name'], r['phone'], dt(r['created']).strftime('%d.%m.%Y %H:%M'), r['source'],
                    dt(r['slot']).strftime('%d.%m %H:%M') if r['slot'] else '', 'да' if clicked(r, 1) else '',
                    dt(r['slot2']).strftime('%d.%m %H:%M') if r['slot2'] else '', 'да' if clicked(r, 2) else '',
                    'да' if r['consult'] else '', r['consult_time'], r['blocked']])
    await m.answer_document(BufferedInputFile(('﻿' + buf.getvalue()).encode('utf-8'), filename='avtoveb.csv'))
