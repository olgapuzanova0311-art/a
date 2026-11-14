"""Воронка ВАЙБ за 1 490 ₽: подарок → оффер с личным таймером 48 ч → дожимы → оплата GetCourse → доступы в Telegram.

Человек попадает сюда по ссылке t.me/<бот>?start=vibe (или vibe_<номер рилса>) из автоответа ВАЙБ в Instagram.
Остальных пользователей бота модуль не трогает (SkipHandler). Своя база: VIBE_DB_PATH (по умолчанию /data/vibe.db).

Подключение в main.py: vibe.init(модуль main), dp.include_router(vibe.router) первым, vibe.setup_web(app),
asyncio.create_task(vibe.scheduler()), в allowed_updates добавить 'chat_member'.

Переменные окружения (все необязательные, без них соответствующая часть просто молчит):
  VIBE_PAY_1490, VIBE_PAY_1990   ссылки на предложения GetCourse
  VIBE_CANCEL_URL                где отключить автопродление клуба
  VIBE_CLUB_RETURN_URL           оплата клуба для тех, кто выпал
  VIBE_GC_SECRET                 секрет в адресе вебхука GetCourse: PUBLIC_URL/vibe/gc/<секрет>
  VIBE_COURSE_CHAT, VIBE_CLUB_CHANNEL, VIBE_CLUB_CHAT   id закрытых каналов и чата (-100...), бот в них админ
  VIBE_TEAM_CHAT                 куда вопросы и отчёт (по умолчанию группа поддержки автовеба)
  VIBE_POLICY_URL, VIBE_MINIAPP_URL
  VIBE_TIME_SCALE                для теста: 60 превращает часы в минуты и выключает ночное окно
"""
import asyncio
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from aiohttp import web
from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (CallbackQuery, ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, Message, ReactionTypeEmoji, ReplyKeyboardMarkup)

import vibe_db as db
import vibe_texts as T

log = logging.getLogger('vibe')
M = None
router = Router()


def _env(k, d=''):
    return os.environ.get(k, d).strip()


def _int(k):
    v = _env(k)
    return int(v) if v.lstrip('-').isdigit() else 0


PAY_1490, PAY_1990 = _env('VIBE_PAY_1490'), _env('VIBE_PAY_1990')
CANCEL_URL, CLUB_RETURN_URL = _env('VIBE_CANCEL_URL'), _env('VIBE_CLUB_RETURN_URL')
GC_SECRET = _env('VIBE_GC_SECRET')
CHAT_ENV = {'course': 'VIBE_COURSE_CHAT', 'club': 'VIBE_CLUB_CHANNEL', 'clubchat': 'VIBE_CLUB_CHAT'}
CHAT_NAMES = {'course': 'канал мини-курса', 'club': 'канал клуба', 'clubchat': 'чат клуба'}


def chat_id(kind):
    """id канала: из переменной окружения или привязанный командой /vibechannel."""
    v = _int(CHAT_ENV[kind]) or db.setting('chat_' + kind)
    return int(v) if str(v).lstrip('-').isdigit() else 0
TEAM_CHAT = _int('VIBE_TEAM_CHAT')
POLICY_URL = _env('VIBE_POLICY_URL', 'https://puzanovva.tech/privacypolicy3')
MINIAPP_URL = _env('VIBE_MINIAPP_URL', 'https://olgapuzanova0311-art.github.io/motion-reel/vibe-hours/')
SCALE = max(1, _int('VIBE_TIME_SCALE') or 1)

MSK = timezone(timedelta(hours=3))
H = 3600 / SCALE
ACCESS_BTN = '🔑 МОИ ДОСТУПЫ'
ACCESS_KB = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=ACCESS_BTN)]], resize_keyboard=True, is_persistent=True)


def init(main_module):
    global M
    M = main_module


def bot():
    return M.bot


def public():
    return M.PUBLIC_URL


def is_vibe(uid):
    return db.user(uid) is not None


def admin(uid):
    return M.is_admin(uid)


# ---------- время ----------

def msk(ts):
    return datetime.fromtimestamp(ts, MSK)


def is_night(ts):
    return SCALE == 1 and (msk(ts).hour >= 23 or msk(ts).hour < 9)


def day_shift(ts):
    """Дожимы не шлём с 23:00 до 9:00 мск, переносим на 9:00."""
    if not is_night(ts):
        return ts
    d = msk(ts)
    if d.hour >= 23:
        d += timedelta(days=1)
    return d.replace(hour=9, minute=0, second=0, microsecond=0).timestamp()


def evening_before(ts):
    d = msk(ts)
    if d.hour < 9:
        d -= timedelta(days=1)
    return d.replace(hour=22, minute=0, second=0, microsecond=0).timestamp()


# ---------- кнопки ----------

def link(uid, key):
    return f'{public()}/vibe/r/{uid}/{key}'


def kb(*rows):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, url=v) if k == 'url' else InlineKeyboardButton(text=t, callback_data=v)
         for t, k, v in row] for row in rows])


def pay_kb(uid, key, text):
    return kb([(text, 'url', link(uid, 'pay_' + key))])


def first_name(u):
    n = (u.first_name or '').strip()
    return n if n and re.fullmatch(r'[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё\- ]{0,30}', n) else ''


def price(u, now=None):
    now = now or time.time()
    return 1490 if (now < (u['expires_at'] or 0) or now < (u['second_until'] or 0)) else 1990


def pay_url(u):
    base = PAY_1490 if price(u) == 1490 else PAY_1990
    params = {'utm_source': 'instagram' if (u['src'] or '').startswith('vibe') else (u['src'] or 'telegram'),
              'utm_medium': 'vibe_bot', 'utm_term': f'tg{u["id"]}'}
    if u['reel']:
        params['utm_content'] = u['reel']
    return base + ('&' if '?' in base else '?') + urlencode(params)


# ---------- отправка ----------

async def send(uid, text, markup=None, key=''):
    try:
        await bot().send_message(uid, text, reply_markup=markup, disable_web_page_preview=True)
        if key:
            db.event(uid, 'sent', key)
        return True
    except TelegramForbiddenError:
        db.run('UPDATE users SET stopped=1 WHERE id=?', uid)
        db.tag(uid, 'stop')
        db.event(uid, 'blocked', key)
    except TelegramBadRequest as e:
        log.warning('send %s %s: %s', uid, key, e)
    return False


def team_ids():
    if TEAM_CHAT:
        return [TEAM_CHAT]
    try:
        return M.avto.team_chats()
    except Exception:
        return []


async def team(text):
    sent = []
    for cid in team_ids():
        try:
            sent.append(await bot().send_message(cid, text, disable_web_page_preview=True))
        except Exception as e:
            log.warning('team %s: %s', cid, e)
    return sent


async def invite(chat_id, uid):
    if not chat_id:
        return None
    try:
        r = await bot().create_chat_invite_link(chat_id, name=f'u{uid}', member_limit=1,
                                                expire_date=int(time.time() + 72 * 3600))
        return r.invite_link
    except Exception as e:
        log.warning('invite %s: %s', chat_id, e)
        await team(f'⚠️ ВАЙБ: не смогла создать ссылку в чат {chat_id}: {e}')


async def access_kb(uid):
    u = db.user(uid)
    rows = []
    course = await invite(chat_id('course'), uid)
    if course:
        rows.append([('🎓 МИНИ-КУРС', 'url', course)])
    if u['club_active']:
        ch, chat = await invite(chat_id('club'), uid), await invite(chat_id('clubchat'), uid)
        if ch:
            rows.append([('🧠 КАНАЛ КЛУБА', 'url', ch)])
        if chat:
            rows.append([('💬 ЧАТ КЛУБА', 'url', chat)])
    elif CLUB_RETURN_URL:
        rows.append([('🧠 ВЕРНУТЬСЯ В КЛУБ', 'url', CLUB_RETURN_URL)])
    return kb(*rows) if rows else None


# ---------- старт ----------

def plan_funnel(uid, t0):
    exp = t0 + 48 * H
    db.run('UPDATE users SET started_at=?, expires_at=? WHERE id=?', t0, exp, uid)
    db.schedule(uid, 'm2', t0 + 4 * 60 / SCALE)
    db.schedule(uid, 'm3', t0 + 40 * 60 / SCALE)
    db.schedule(uid, 'm4', day_shift(t0 + 3 * H))
    if SCALE == 1:
        eve = msk(t0).replace(hour=20, minute=0, second=0, microsecond=0).timestamp()
        if eve - t0 > 2 * 3600:
            db.schedule(uid, 'm5', eve)
    else:
        db.schedule(uid, 'm5', t0 + 8 * H)
    db.schedule(uid, 'm6', day_shift(t0 + 20 * H))
    db.schedule(uid, 'm7', day_shift(t0 + 28 * H))
    t8, t9 = exp - 6 * H, exp - 1 * H
    if is_night(exp) or is_night(t9):
        eve = evening_before(t9)
        if eve > t0 + 28 * H:
            db.schedule(uid, 'm8n', eve)
    else:
        db.schedule(uid, 'm8', evening_before(t8) if is_night(t8) else t8)
        db.schedule(uid, 'm9', t9)
    db.schedule(uid, 'm10', day_shift(t0 + 50 * H))
    db.schedule(uid, 'm11', day_shift(t0 + 120 * H))
    db.schedule(uid, 'k', day_shift(t0 + 144 * H))


@router.message(CommandStart())
async def on_start(m: Message, command: CommandObject):
    uid, arg = m.from_user.id, (command.args or '').strip()
    u = db.user(uid)
    if arg.startswith('vorder_'):
        return await bind_order(m, arg[7:])
    in_main = M.user(uid) is not None  # уже в автовебе или интенсиве: обычный /start остаётся за ними
    if not arg.startswith('vibe') and arg != 'vaccess' and not (u and (arg == 'vprompt' or (arg == '' and not in_main))):
        raise SkipHandler()
    if u and arg == 'vprompt':
        db.tag(uid, 'prompt_opened')
        return await send_prompt(uid)
    if arg == 'vaccess':
        if not u:
            db.run('INSERT INTO users(id,name,username,src,started_at,expires_at) VALUES(?,?,?,?,?,?)',
                   uid, first_name(m.from_user), m.from_user.username, 'getcourse', time.time(), time.time())
        return await on_access(m)
    if u:
        if u['stopped']:
            db.run('UPDATE users SET stopped=0 WHERE id=?', uid)
            db.untag(uid, 'stop')
        return await send_start(uid)
    reel = arg[5:] if arg.startswith('vibe_') else ''
    db.run('INSERT INTO users(id,name,username,src,reel) VALUES(?,?,?,?,?)',
           uid, first_name(m.from_user), m.from_user.username, 'vibe_ig', reel)
    db.tag(uid, 'vibe_start')
    db.event(uid, 'start', reel)
    plan_funnel(uid, time.time())
    await send_start(uid)


async def send_start(uid):
    u = db.user(uid)
    await send(uid, T.start(u['name'], POLICY_URL), kb(
        [('🔥 ПОСЧИТАТЬ МОИ ЧАСЫ', 'url', link(uid, 'app'))],
        [('⚡️ ХОЧУ ПРОМПТ СРАЗУ', 'cb', 'vb:prompt')]), 'm1')


async def send_prompt(uid):
    if await send(uid, T.prompt_msg(), key='m2'):
        db.tag(uid, 'prompt_sent')


@router.callback_query(F.data == 'vb:prompt')
async def cb_prompt(c: CallbackQuery):
    db.tag(c.from_user.id, 'prompt_opened')
    db.event(c.from_user.id, 'click', 'prompt')
    await c.answer()
    await send_prompt(c.from_user.id)


@router.callback_query(F.data == 'vb:gift')
async def cb_gift(c: CallbackQuery):
    db.tag(c.from_user.id, 'gift_opened')
    db.event(c.from_user.id, 'click', 'gift')
    await c.answer()
    await send_prompt(c.from_user.id)


@router.callback_query(F.data == 'vb:inside')
async def cb_inside(c: CallbackQuery):
    uid = c.from_user.id
    u = db.user(uid)
    db.event(uid, 'click', 'inside')
    await c.answer()
    if not u:
        return
    db.tag(uid, 'inside_seen')
    left = max(u['expires_at'] or 0, u['second_until'] or 0) - time.time()
    await send(uid, T.inside_now(T.left_text(left)), pay_kb(uid, 'm6', '🚀 ЗАБРАТЬ ЗА 1 490 ₽'), 'm6')


# ---------- плановые сообщения ----------

async def run_job(j):
    uid, key = j['user_id'], j['key']
    u = db.user(uid)
    if not u or u['stopped']:
        return
    name = u['name']
    if key.startswith('m') and u['paid_at'] is not None:
        return
    if key == 'm2':
        if not db.has(uid, 'prompt_sent'):
            await send_prompt(uid)
    elif key == 'm3':
        if await send(uid, T.offer(name), kb(
                [('🚀 ЗАБРАТЬ ЗА 1 490 ₽', 'url', link(uid, 'pay_m3'))],
                [('🤔 А ЧТО ВНУТРИ?', 'cb', 'vb:inside')]), 'm3'):
            db.tag(uid, 'offer_seen')
    elif key == 'm4':
        if not (db.has(uid, 'gift_opened') or db.has(uid, 'prompt_opened')):
            await send(uid, T.no_gift(name), kb([('⚡️ ОТКРЫТЬ ПОДАРОК', 'cb', 'vb:gift')]), key)
    elif key == 'm5':
        await send(uid, T.story(), pay_kb(uid, key, '🚀 ХОЧУ ТАК ЖЕ'), key)
    elif key == 'm6':
        if not db.has(uid, 'inside_seen'):
            await send(uid, T.inside(name, T.left_text(u['expires_at'] - time.time())),
                       pay_kb(uid, key, '🚀 ЗАБРАТЬ ЗА 1 490 ₽'), key)
    elif key == 'm7':
        await send(uid, T.fears(), pay_kb(uid, key, '🚀 ЛАДНО, УГОВОРИЛА'), key)
    elif key == 'm8':
        hours = max(1, round((u['expires_at'] - time.time()) / H))
        await send(uid, T.six_hours(name, hours), pay_kb(uid, key, '⚡️ УСПЕТЬ ЗА 1 490 ₽'), key)
    elif key == 'm8n':
        await send(uid, T.night_last(), pay_kb(uid, key, '🔥 ЗАБРАТЬ, ПОКА 1 490 ₽'), key)
    elif key == 'm9':
        await send(uid, T.last_hour(), pay_kb(uid, key, '🔥 ЗАБРАТЬ, ПОКА 1 490 ₽'), key)
    elif key == 'm10':
        if time.time() >= (u['second_until'] or 0):
            await send(uid, T.price_up(), pay_kb(uid, key, '🚀 ЗАБРАТЬ ЗА 1 990 ₽'), key)
    elif key == 'm11':
        db.run('UPDATE users SET second_until=? WHERE id=?', time.time() + 24 * H, uid)
        await send(uid, T.second_chance(name), pay_kb(uid, key, '🎟 ЗАБРАТЬ ЗА 1 490 ₽'), key)
    elif key == 'k':
        await send_content(u)
    elif key == 'p2':
        if not db.has(uid, 'course_joined'):
            course = await invite(chat_id('course'), uid)
            await send(uid, T.p2(name), kb([('▶️ ОТКРЫТЬ УРОК 1', 'url', course)]) if course else None, key)
    elif key == 'p3':
        await send(uid, T.p3(), key=key)
    elif key == 'p4':
        await send(uid, T.p4(name), key=key)
    elif key.startswith('p5'):
        if u['club_active']:
            await send(uid, T.p5(db.setting('next_month'), CANCEL_URL), key='p5')
    elif key == 'club_off':
        await club_off(uid)


async def send_content(u):
    uid = u['id']
    posts = db.q('SELECT * FROM posts ORDER BY id')
    n = db.one("SELECT COUNT(*) c FROM events WHERE user_id=? AND kind='sent' AND key LIKE 'k%'", uid)['c']
    if n >= len(posts):
        db.schedule(uid, 'k', time.time() + 24 * H)  # новых постов нет, проверим завтра
        return
    p = posts[n]
    try:
        await bot().copy_message(uid, p['chat_id'], p['message_id'])
        db.event(uid, 'sent', f'k{p["id"]}')
        if n % 3 == 2 and u['paid_at'] is None:
            pr = f'{price(u):,}'.replace(',', ' ')
            await send(uid, f'Мини-курс по вайбкодингу + месяц клуба сейчас за {pr} ₽' + T.STOP_LINE,
                       pay_kb(uid, 'k', f'🚀 ЗАБРАТЬ ЗА {pr} ₽'))
    except TelegramForbiddenError:
        db.run('UPDATE users SET stopped=1 WHERE id=?', uid)
        return
    except Exception as e:
        log.warning('content %s: %s', uid, e)
    db.schedule(uid, 'k', day_shift(time.time() + 72 * H))


async def scheduler():
    while True:
        try:
            if db.setting('paused') != '1':
                for j in db.q('SELECT * FROM jobs WHERE done=0 AND due<=? ORDER BY due LIMIT 100', time.time()):
                    db.run('UPDATE jobs SET done=1 WHERE id=?', j['id'])
                    try:
                        await run_job(j)
                    except Exception:
                        log.exception('job %s', dict(j))
                    await asyncio.sleep(0.05)
            await daily()
        except Exception:
            log.exception('vibe scheduler')
        await asyncio.sleep(15)


# ---------- оплата и доступы ----------

async def mark_paid(uid, cost, deal=''):
    u = db.user(uid)
    if not u:
        db.run('INSERT INTO users(id,name,src,started_at,expires_at) VALUES(?,?,?,?,?)',
               uid, '', 'getcourse', time.time(), time.time())
        u = db.user(uid)
    if u['paid_at']:
        return
    now = time.time()
    p = 1990 if cost >= 1900 else 1490
    db.run('UPDATE users SET paid_at=?, paid_price=?, next_charge=?, club_active=1, stopped=0 WHERE id=?',
           now, p, now + 30 * 24 * H, uid)
    db.tag(uid, f'paid_{p}')
    db.tag(uid, 'club_active')
    db.event(uid, 'paid', str(p))
    db.cancel(uid, 'm')
    await send(uid, T.paid(CANCEL_URL), await access_kb(uid), 'p1')
    try:
        await bot().send_message(uid, 'Кнопка с доступами всегда тут 👇', reply_markup=ACCESS_KB)
    except Exception:
        pass
    db.schedule(uid, 'p2', day_shift(now + 24 * H))
    db.schedule(uid, 'p3', day_shift(now + 72 * H))
    db.schedule(uid, 'p4', day_shift(now + 240 * H))
    db.schedule(uid, 'p5_1', day_shift(now + 27 * 24 * H))
    who = f'@{u["username"]}' if u['username'] else (u['name'] or uid)
    await team(f'💰 ВАЙБ: оплата {p} ₽, {who} (id {uid}){", заказ " + deal if deal else ""}')


async def club_off(uid):
    u = db.user(uid)
    if not u or not u['club_active']:
        return
    db.run('UPDATE users SET club_active=0 WHERE id=?', uid)
    db.untag(uid, 'club_active')
    db.tag(uid, 'club_cancelled')
    await kick(uid)
    await send(uid, T.CLUB_PAUSED, kb([('🧠 ВЕРНУТЬСЯ В КЛУБ', 'url', CLUB_RETURN_URL)]) if CLUB_RETURN_URL else None,
               'club_off')


async def kick(uid):
    if admin(uid):
        return
    for chat in (chat_id('club'), chat_id('clubchat')):
        if chat:
            try:
                await bot().ban_chat_member(chat, uid)
                await bot().unban_chat_member(chat, uid, only_if_banned=True)
            except Exception as e:
                log.warning('kick %s from %s: %s', uid, chat, e)


@router.message(Command('access'))
async def on_access_cmd(m: Message):
    if not is_vibe(m.from_user.id):
        raise SkipHandler()
    await on_access(m)


@router.message(F.text == ACCESS_BTN)
async def on_access(m: Message):
    u = db.user(m.from_user.id)
    if not u or not u['paid_at']:
        if u:
            db.tag(u['id'], 'await_email')
        return await m.answer(T.ASK_EMAIL)
    await m.answer(T.ACCESS, reply_markup=await access_kb(u['id']))


async def bind_order(m: Message, deal):
    uid = m.from_user.id
    o = db.one('SELECT * FROM orders WHERE deal=?', deal)
    who = f'@{m.from_user.username}' if m.from_user.username else uid
    if not o or (o['user_id'] and o['user_id'] != uid):
        await m.answer(T.ORDER_NOT_FOUND)
        return await team(f'⚠️ ВАЙБ: {who} пришёл с заказом {deal}, но '
                          + ('оплаты нет в базе' if not o else 'заказ уже привязан к другому аккаунту'))
    db.run('UPDATE orders SET user_id=? WHERE deal=?', uid, deal)
    if not db.user(uid):
        db.run('INSERT INTO users(id,name,username,src,started_at,expires_at) VALUES(?,?,?,?,?,?)',
               uid, first_name(m.from_user), m.from_user.username, 'getcourse', time.time(), time.time())
    await mark_paid(uid, o['cost'] or 1490, deal)


@router.my_chat_member()
async def on_bot_added(e: ChatMemberUpdated):
    """Бота добавили админом после /vibechannel: это канал воронки, основной бот его не трогает."""
    wait = db.setting('await_chat')
    kind, _, ts = wait.partition(':')
    if not wait or e.new_chat_member.status != 'administrator' or time.time() - float(ts or 0) > 3600:
        raise SkipHandler()
    db.set_setting('chat_' + kind, str(e.chat.id))
    db.set_setting('await_chat', '')
    r = e.new_chat_member
    ok = r.can_invite_users and (e.chat.type == 'channel' or r.can_restrict_members)
    await team(f'✅ ВАЙБ: «{e.chat.title}» привязан как {CHAT_NAMES[kind]} (id {e.chat.id})'
               + ('' if ok else '\n⚠️ Дай боту права приглашать и удалять участников'))


async def bind_email(m: Message, email):
    uid = m.from_user.id
    o = db.one("SELECT * FROM orders WHERE lower(email)=? AND (user_id IS NULL OR user_id=?) ORDER BY ts DESC", email, uid)
    if not o:
        who = f'@{m.from_user.username}' if m.from_user.username else uid
        await team(f'⚠️ ВАЙБ: {who} просит доступ, почта {email}, оплаты по ней не вижу. Проверь в GetCourse')
        return await m.answer(T.EMAIL_NOT_FOUND)
    db.untag(uid, 'await_email')
    db.run('UPDATE orders SET user_id=? WHERE deal=?', uid, o['deal'])
    await mark_paid(uid, o['cost'] or 1490, o['deal'])


@router.chat_member()
async def on_member(e: ChatMemberUpdated):
    if chat_id('course') and e.chat.id == chat_id('course') and e.new_chat_member.status in ('member', 'restricted'):
        db.tag(e.new_chat_member.user.id, 'course_joined')
    raise SkipHandler()


# ---------- команда ----------

@router.message(Command('id'))
async def on_id(m: Message):
    await m.answer(f'id этого чата: <code>{m.chat.id}</code>\nтвой id: <code>{m.from_user.id}</code>')


def admin_cmd(name):
    def deco(fn):
        async def h(m: Message, command: CommandObject):
            if admin(m.from_user.id) or (m.chat.id in team_ids()):
                await fn(m, (command.args or '').strip())
        h.__name__ = fn.__name__
        router.message(Command(name))(h)
        return fn
    return deco


@admin_cmd('vibe')
async def c_help(m, a):
    await m.answer('🎁 <b>Воронка ВАЙБ</b>\n'
                   f'Ссылка для Instagram: t.me/{M.BOT_USERNAME}?start=vibe (или vibe_номеррилса)\n'
                   '/vibechannel · привязать канал курса, канал клуба или чат клуба\n'
                   '/vibestats · цифры воронки\n'
                   '/vibepost · ответь на пост, бот будет присылать такие раз в 3 дня с 7-го дня\n'
                   '/vibemonth темы · темы следующего месяца для напоминания о продлении\n'
                   '/vibepause, /viberesume · остановить или включить дожимы\n'
                   '/vibereset · стереть себя из воронки для теста\n'
                   '/vibepaytest · имитировать свою оплату 1 490 ₽ без денег\n'
                   '/id · id чата, нужен для настройки каналов')


@admin_cmd('vibechannel')
async def c_channel(m, a):
    kind = {'курс': 'course', 'course': 'course', 'клуб': 'club', 'club': 'club', 'чат': 'clubchat', 'clubchat': 'clubchat'}.get(a.lower())
    if not kind:
        now = '\n'.join(f'{CHAT_NAMES[k]}: {chat_id(k) or "не привязан"}' for k in CHAT_NAMES)
        return await m.answer('Напиши /vibechannel курс, /vibechannel клуб или /vibechannel чат, '
                              'потом в течение часа добавь бота администратором в этот канал или чат\n\n' + now)
    db.set_setting('await_chat', f'{kind}:{time.time()}')
    await m.answer(f'Жду: добавь @{M.BOT_USERNAME} администратором в {CHAT_NAMES[kind]} '
                   '(права: приглашать по ссылкам и удалять участников). Я привяжу его и напишу сюда')


@admin_cmd('vibestats')
async def c_stats(m, a):
    await m.answer(report())


@admin_cmd('vibepost')
async def c_post(m, a):
    if not m.reply_to_message:
        return await m.answer('Ответь командой /vibepost на пост, который бот будет присылать раз в 3 дня')
    db.run('INSERT INTO posts(chat_id,message_id,ts) VALUES(?,?,?)', m.chat.id, m.reply_to_message.message_id, time.time())
    n = db.one('SELECT COUNT(*) c FROM posts')['c']
    await m.answer(f'Добавила в контент, в очереди {n} {T.plural(n, "пост", "поста", "постов")}')


@admin_cmd('vibemonth')
async def c_month(m, a):
    db.set_setting('next_month', a)
    await m.answer('Темы следующего месяца сохранила')


@admin_cmd('vibepause')
async def c_pause(m, a):
    db.set_setting('paused', '1')
    await m.answer('Дожимы ВАЙБ на паузе')


@admin_cmd('viberesume')
async def c_resume(m, a):
    db.set_setting('paused', '0')
    await m.answer('Дожимы ВАЙБ снова идут')


@admin_cmd('vibereset')
async def c_reset(m, a):
    uid = m.from_user.id
    for t in ('users WHERE id', 'tags WHERE user_id', 'jobs WHERE user_id', 'events WHERE user_id'):
        db.run(f'DELETE FROM {t}=?', uid)
    await m.answer(f'Стёрла тебя из воронки ВАЙБ. Заходи заново: t.me/{M.BOT_USERNAME}?start=vibe')


@admin_cmd('vibepaytest')
async def c_paytest(m, a):
    await mark_paid(m.from_user.id, 1490, 'test')


# ---------- переписка ----------

@router.message(F.reply_to_message)
async def on_team_reply(m: Message):
    r = db.one('SELECT user_id FROM fwd WHERE chat_id=? AND msg=?', m.chat.id, m.reply_to_message.message_id)
    if not r:
        raise SkipHandler()
    try:
        await m.copy_to(r['user_id'])
        await m.react([ReactionTypeEmoji(emoji='👌')])
    except Exception as e:
        await m.answer(f'Не доставила: {e}')


@router.message(F.chat.type == 'private')
async def on_text(m: Message):
    uid = m.from_user.id
    if not is_vibe(uid) or (m.text or '').startswith('/'):
        raise SkipHandler()
    if M.user(uid) is not None and not db.has(uid, 'await_email'):
        raise SkipHandler()  # кто есть и в автовебе, тот пишет команде через автовеб, как раньше
    txt = (m.text or m.caption or '').strip().lower()
    if db.has(uid, 'await_email') and re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]{2,}', txt):
        return await bind_email(m, txt)
    if txt in ('стоп', 'stop'):
        db.run('UPDATE users SET stopped=1 WHERE id=?', uid)
        db.tag(uid, 'stop')
        return await m.answer(T.STOPPED)
    who = f'@{m.from_user.username}' if m.from_user.username else m.from_user.full_name
    if 'вайбкодер' in txt:
        db.event(uid, 'lead', 'vibecoder')
        await team(f'🔥 ВАЙБ: хочет ВАЙБкодер, {who} (id {uid})')
        return await m.answer(T.VIBECODER)
    for cid in team_ids():
        try:
            h = await bot().send_message(cid, f'✉️ ВАЙБ: {who} (id {uid}) пишет. Ответь реплаем, бот перешлёт')
            c = await bot().copy_message(cid, m.chat.id, m.message_id, reply_to_message_id=h.message_id)
            db.run('INSERT OR REPLACE INTO fwd VALUES(?,?,?)', cid, h.message_id, uid)
            db.run('INSERT OR REPLACE INTO fwd VALUES(?,?,?)', cid, c.message_id, uid)
        except Exception as e:
            log.warning('to team %s: %s', cid, e)
    await m.answer(T.GOT_IT)


# ---------- отчёт и сверка клуба ----------

def report():
    now = time.time()

    def cnt(sql, *a):
        return db.one(sql, *a)['c']

    lines = []
    for title, since in (('За сутки', now - 86400), ('За всё время', 0)):
        st = cnt("SELECT COUNT(*) c FROM users WHERE started_at>=? AND src LIKE 'vibe%'", since)
        gift = cnt("SELECT COUNT(DISTINCT t.user_id) c FROM tags t JOIN users u ON u.id=t.user_id "
                   "WHERE u.started_at>=? AND t.tag IN ('gift_opened','prompt_opened')", since)
        offer = cnt("SELECT COUNT(*) c FROM tags t JOIN users u ON u.id=t.user_id WHERE u.started_at>=? AND t.tag='offer_seen'", since)
        p1 = cnt('SELECT COUNT(*) c FROM users WHERE paid_at>=? AND paid_price=1490', since)
        p2 = cnt('SELECT COUNT(*) c FROM users WHERE paid_at>=? AND paid_price=1990', since)
        ren = cnt("SELECT COUNT(*) c FROM events WHERE kind='renewed' AND ts>=?", since)
        stop = cnt("SELECT COUNT(*) c FROM tags WHERE tag='stop' AND ts>=?", since)
        conv = f'{(p1 + p2) / st * 100:.1f}%' if st else '0%'
        lines.append(f'<b>{title}</b>\nЗашли в бота: {st}\nОткрыли подарок: {gift}\nУвидели оффер: {offer}\n'
                     f'Оплатили: 1 490 ₽ {p1}, 1 990 ₽ {p2} (конверсия {conv})\nПродлили клуб: {ren}\nОтписались: {stop}')
    by = {}
    for u in db.q('SELECT id, paid_at FROM users WHERE paid_at IS NOT NULL'):
        e = db.one("SELECT key FROM events WHERE user_id=? AND kind='sent' AND key LIKE 'm%' AND ts<=? "
                   'ORDER BY ts DESC LIMIT 1', u['id'], u['paid_at'])
        if e:
            by[e['key']] = by.get(e['key'], 0) + 1
    rows = []
    for k in ('m3', 'm4', 'm5', 'm6', 'm7', 'm8', 'm8n', 'm9', 'm10', 'm11'):
        sent = cnt("SELECT COUNT(*) c FROM events WHERE kind='sent' AND key=?", k)
        if sent:
            clicks = cnt("SELECT COUNT(DISTINCT user_id) c FROM events WHERE kind='click' AND key=?", 'pay_' + k)
            rows.append(f'{k}: отправлено {sent}, нажали «купить» {clicks}, оплата после него {by.get(k, 0)}')
    if rows:
        lines.append('<b>Дожимы</b>\n' + '\n'.join(rows))
    lines.append('Сколько написали ВАЙБ в директ, смотри в Chatplace')
    return '📊 <b>Воронка ВАЙБ</b>\n\n' + '\n\n'.join(lines)


async def daily():
    d = msk(time.time())
    today = d.strftime('%Y-%m-%d')
    if d.hour >= 10 and db.setting('report_day') != today:
        db.set_setting('report_day', today)
        if db.one('SELECT COUNT(*) c FROM users')['c']:
            await team(report())
    if d.hour >= 4 and db.setting('sync_day') != today:
        db.set_setting('sync_day', today)
        for u in db.q('SELECT id FROM users WHERE paid_at IS NOT NULL AND club_active=0'):
            for chat in (chat_id('club'), chat_id('clubchat')):
                if not chat or admin(u['id']):
                    continue
                try:
                    if (await bot().get_chat_member(chat, u['id'])).status in ('member', 'restricted'):
                        await kick(u['id'])
                except Exception:
                    pass
                await asyncio.sleep(0.1)


# ---------- веб ----------

async def r_redirect(req: web.Request):
    uid, key = int(req.match_info['uid']), req.match_info['key']
    u = db.user(uid)
    if u:
        db.event(uid, 'click', key)
    if key == 'app':
        if u:
            db.tag(uid, 'gift_opened')
        return web.HTTPFound(MINIAPP_URL + f'?bot={M.BOT_USERNAME}')
    if key.startswith('pay') and u:
        if u['paid_at']:
            return web.HTTPFound(f'https://t.me/{M.BOT_USERNAME}?start=vaccess')
        if (price(u) == 1490 and PAY_1490) or (price(u) == 1990 and PAY_1990):
            return web.HTTPFound(pay_url(u))
    return web.HTTPFound(f'https://t.me/{M.BOT_USERNAME}')


async def r_getcourse(req: web.Request):
    if not GC_SECRET or req.match_info['secret'] != GC_SECRET:
        return web.Response(status=403)
    data = dict(req.query)
    if req.method == 'POST':
        try:
            data.update(dict(await req.post()))
        except Exception:
            pass
    ev = data.get('event', 'paid')
    found = re.search(r'\d{5,}', data.get('tg', '') or '')
    uid = int(found.group()) if found else None
    deal = str(data.get('deal', '')).strip()
    try:
        cost = int(float(str(data.get('cost', '0')).replace(' ', '').replace(',', '.') or 0))
    except ValueError:
        cost = 0
    log.info('getcourse %s', data)
    email = (data.get('email') or '').strip().lower()
    if ev == 'paid' and uid and (db.user(uid) or {'paid_at': None})['paid_at'] and \
            (cost >= 2300 or 'продлен' in (data.get('offers') or '').lower()):
        ev = 'renewed'
    if ev == 'paid':
        if deal:
            db.run('INSERT OR IGNORE INTO orders VALUES(?,?,?,?,?)', deal, uid, email, cost, time.time())
        if uid:
            db.run('UPDATE orders SET user_id=? WHERE deal=?', uid, deal)
            await mark_paid(uid, cost, deal)
    elif uid and ev == 'renewed':
        u = db.user(uid)
        if u:
            nxt = max(time.time(), u['next_charge'] or 0) + 30 * 24 * H
            was_off = not u['club_active']
            db.run('UPDATE users SET next_charge=?, club_active=1 WHERE id=?', nxt, uid)
            db.tag(uid, 'club_active')
            db.untag(uid, 'club_cancelled')
            db.event(uid, 'renewed')
            db.cancel(uid, 'club_off')
            db.schedule(uid, f'p5_{int(nxt)}', day_shift(nxt - 3 * 24 * H))
            if was_off:
                await send(uid, 'Ты снова в клубе 🎉 Держи ссылки 👇', await access_kb(uid), 'club_back')
    elif uid and ev == 'club_failed':
        db.schedule(uid, 'club_off', time.time() + 3 * 24 * H)
    elif uid and ev == 'club_cancelled':
        u = db.user(uid)
        if u:
            db.cancel(uid, 'p5')
            db.schedule(uid, 'club_off', max(time.time(), u['next_charge'] or 0))
    return web.json_response({'ok': True})


def setup_web(app):
    app.router.add_get('/vibe/r/{uid:\\d+}/{key}', r_redirect)
    app.router.add_route('*', '/vibe/gc/{secret}', r_getcourse)
