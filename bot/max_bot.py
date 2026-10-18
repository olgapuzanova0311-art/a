"""
Бот интенсива в MAX: та же регистрация, подарки, рассылки и запись в Google Таблицу, что и в Telegram.

Переменные окружения:
  MAX_TOKEN   токен бота MAX (без него модуль не запускается)
  PUBLIC_URL  https-адрес сервиса, на него MAX присылает события (webhook)
"""
import asyncio, json, logging, os, re, secrets, sqlite3, time
from datetime import datetime, timedelta

import aiohttp
from aiohttp import web

import texts as T

log = logging.getLogger('max')
API = 'https://platform-api.max.ru'
TYPES = ['bot_started', 'message_created', 'message_callback']
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]{2,}$')


class MaxBot:
    def __init__(self, token, db, links, sheet_url, public_url):
        self.token, self.db, self.base_links, self.sheet_url = token, db, links, sheet_url
        self.public_url = public_url.rstrip('/')
        self.hook_path = '/max/' + secrets.token_hex(8)
        self.session = None
        db.executescript('''
        CREATE TABLE IF NOT EXISTS max_users(id INTEGER PRIMARY KEY, first_name TEXT, username TEXT, phone TEXT, email TEXT,
          created INTEGER, source TEXT, vip INTEGER DEFAULT 0, survey TEXT, blocked INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS max_sent(user_id INTEGER, key TEXT, PRIMARY KEY(user_id, key));
        ''')
        db.commit()

    # ---------- база ----------
    def q(self, sql, *a):
        cur = self.db.execute(sql, a)
        self.db.commit()
        return cur

    def user(self, uid):
        return self.q('SELECT * FROM max_users WHERE id=?', uid).fetchone()

    def mark(self, uid, key):
        try:
            self.q('INSERT INTO max_sent(user_id, key) VALUES(?,?)', uid, key)
            return True
        except sqlite3.IntegrityError:
            return False

    # ---------- API ----------
    async def call(self, method, path, params=None, body=None):
        if not self.session:
            self.session = aiohttp.ClientSession(headers={'Authorization': self.token})
        async with self.session.request(method, API + path, params=params, json=body, timeout=aiohttp.ClientTimeout(total=40)) as r:
            data = await r.json(content_type=None)
            if r.status >= 400:
                raise RuntimeError(f'{r.status} {data}')
            return data

    def links(self, u):
        L = dict(self.base_links())
        if u:
            L['PAY'] = L['PAY'] + ('&' if '?' in L['PAY'] else '?') + 'max=' + str(u['id'])
        return L

    def fill(self, text, u):
        name = (u['first_name'] if u and u['first_name'] else 'друг')
        return text.format(name=name, prize=T.MAIN_PRIZE, ref='')

    def keyboard(self, rows, u):
        L, out = self.links(u), []
        for row in rows or []:
            r = []
            for b in row:
                if b[0] == 'url':
                    r.append({'type': 'link', 'text': b[1], 'url': b[2].format(**L)})
                elif b[0] == 'cb':
                    r.append({'type': 'callback', 'text': b[1], 'payload': b[2]})
                elif b[0] == 'contact':
                    r.append({'type': 'request_contact', 'text': b[1]})
            if r:
                out.append(r)
        return out

    async def send(self, uid, text, btns=None, photo=None):
        u = self.user(uid)
        att = []
        if photo:
            att.append({'type': 'image', 'payload': {'url': photo if photo.startswith('http') else T.IMG + photo}})
        rows = self.keyboard(btns, u)
        if rows:
            att.append({'type': 'inline_keyboard', 'payload': {'buttons': rows}})
        body = {'text': self.fill(text, u)[:4000], 'format': 'html'}
        if att:
            body['attachments'] = att
        try:
            await self.call('POST', '/messages', {'user_id': uid, 'disable_link_preview': 'true'}, body)
            return True
        except Exception as e:
            msg = str(e)
            if photo and 'attachment' in msg.lower():
                return await self.send(uid, text, btns)  # картинка не прошла: шлём без неё
            if 'blocked' in msg.lower() or 'not.found' in msg.lower() or '403' in msg:
                self.q('UPDATE max_users SET blocked=1 WHERE id=?', uid)
            log.info('max send %s: %s', uid, msg)
            return False

    async def to_sheet(self, u, event):
        if not self.sheet_url:
            return
        payload = dict(event=event, name=u['first_name'] or '', phone=u['phone'] or '', email=u['email'] or '',
                       tariff='VIP 490 ₽' if u['vip'] else 'Бесплатно 0 ₽', consent_data='да (бот MAX)', consent_mailing='да (бот MAX)',
                       page=f'MAX @{u["username"] or "-"} id {u["id"]} · источник {u["source"] or "-"}' + (f' · опрос: {u["survey"]}' if u['survey'] else ''))
        try:
            async with aiohttp.ClientSession() as s:
                await s.post(self.sheet_url, data=json.dumps(payload, ensure_ascii=False).encode(),
                             headers={'Content-Type': 'text/plain;charset=utf-8'}, timeout=aiohttp.ClientTimeout(total=20))
        except Exception as e:
            log.warning('max sheet: %s', e)

    # ---------- сценарий ----------
    def new_user(self, info, source):
        uid = info['user_id']
        if not self.user(uid):
            name = info.get('first_name') or info.get('name') or ''
            self.q('INSERT INTO max_users(id, first_name, username, created, source) VALUES(?,?,?,?,?)',
                   uid, name, info.get('username') or '', int(time.time()), source or 'max')
            return True
        return False

    async def start(self, info, payload=''):
        first = self.new_user(info, (payload or '').strip()[:40] or 'max')
        u = self.user(info['user_id'])
        if first:
            asyncio.create_task(self.to_sheet(u, 'Регистрация через бота MAX (без телефона)'))
        if u['phone'] and u['email']:
            return await self.send(u['id'], T.ALREADY, self.menu())
        await self.send(u['id'], T.WELCOME, T.WELCOME_BTNS, 'i_hero.jpg')

    def menu(self):
        return [[b for b in row if b[0] != 'app'] for row in T.MENU_BTNS if any(b[0] != 'app' for b in row)]

    async def next_step(self, uid):
        u = self.user(uid)
        if not u['phone']:
            return await self.send(uid, T.ASK_CONTACT.replace('внизу экрана ', ''), [[('contact', '📱 Поделиться номером')]])
        if not u['email']:
            return await self.send(uid, T.ASK_EMAIL)
        await self.give_gifts(u)

    async def give_gifts(self, u):
        gifts = [[('url', '🎁 ' + T.GIFT[k][0], T.GIFT[k][1])] for k in T.REG_GIFTS]
        await self.send(u['id'], T.GIFTS_TEXT.replace(' Смотри в личном кабинете.', ''), gifts + self.menu())

    async def on_contact(self, uid, att):
        p = att.get('payload') or {}
        vcf = p.get('vcf_info') or ''
        m = re.search(r'TEL[^:\n]*:([+\d\s()\-]{6,})', vcf)
        phone = re.sub(r'[^\d+]', '', m.group(1)) if m else re.sub(r'[^\d+]', '', str(p.get('phone') or ''))
        if not phone:
            return await self.send(uid, 'Не получилось прочитать номер 🙈 Нажми кнопку «📱 Поделиться номером» ещё раз.')
        self.q('UPDATE max_users SET phone=? WHERE id=?', phone, uid)
        asyncio.create_task(self.to_sheet(self.user(uid), 'Регистрация через бота MAX: телефон'))
        await self.next_step(uid)

    async def on_text(self, info, text):
        uid = info['user_id']
        if text.startswith('/start'):
            return await self.start(info, text[6:].strip())
        u = self.user(uid)
        if not u:
            return await self.start(info)
        if not u['phone']:
            return await self.next_step(uid)
        if not u['email']:
            mail = text.strip().lower()
            if not EMAIL_RE.match(mail):
                return await self.send(uid, T.BAD_EMAIL)
            self.q('UPDATE max_users SET email=? WHERE id=?', mail, uid)
            u = self.user(uid)
            asyncio.create_task(self.to_sheet(u, 'Регистрация через бота MAX'))
            return await self.give_gifts(u)
        await self.send(uid, 'Если что-то не работает, напиши менеджеру: @puzanovateam\n\nНапиши /start, чтобы открыть меню.')

    async def on_callback(self, cb):
        uid = cb['user']['user_id']
        data = cb.get('payload') or ''
        try:
            await self.call('POST', '/answers', {'callback_id': cb['callback_id']}, {'notification': '👌'})
        except Exception:
            pass
        if not self.user(uid):
            self.new_user(cb['user'], 'max')
        if data == 'gifts':
            return await self.next_step(uid)
        if data.startswith('sv:'):
            return await self.survey(uid, data)

    async def survey(self, uid, data):
        parts = data.split(':')
        if parts[1] == 'start':
            self.q('UPDATE max_users SET survey=NULL WHERE id=?', uid)
            qi = 0
        else:
            qi, ai = int(parts[1]), int(parts[2])
            prev = (self.user(uid)['survey'] or '')
            ans = T.SURVEY[qi][1][ai]
            self.q('UPDATE max_users SET survey=? WHERE id=?', (prev + ' / ' if prev else '') + ans, uid)
            qi += 1
        if qi < len(T.SURVEY):
            qt, opts = T.SURVEY[qi]
            return await self.send(uid, f'<b>Вопрос {qi + 1} из {len(T.SURVEY)}.</b> {qt}', [[('cb', o, f'sv:{qi}:{i}')] for i, o in enumerate(opts)])
        u = self.user(uid)
        asyncio.create_task(self.to_sheet(u, 'Опрос в боте MAX'))
        await self.send(uid, T.SURVEY_DONE, [[('url', '🎁 ' + T.GIFT[T.SURVEY_GIFT][0], T.GIFT[T.SURVEY_GIFT][1])]])

    # ---------- события ----------
    async def handle(self, upd):
        t = upd.get('update_type')
        try:
            if t == 'bot_started':
                info = dict(upd.get('user') or {})
                await self.start(info, upd.get('payload') or '')
            elif t == 'message_created':
                m = upd.get('message') or {}
                info = m.get('sender') or {}
                if info.get('is_bot') or (m.get('recipient') or {}).get('chat_type') not in (None, 'dialog'):
                    return
                body = m.get('body') or {}
                for att in body.get('attachments') or []:
                    if att.get('type') == 'contact':
                        if not self.user(info['user_id']):
                            self.new_user(info, 'max')
                        return await self.on_contact(info['user_id'], att)
                if body.get('text'):
                    await self.on_text(info, body['text'])
            elif t == 'message_callback':
                await self.on_callback(upd.get('callback') or {})
        except Exception:
            log.exception('max update %s', t)

    async def webhook(self, req):
        try:
            upd = await req.json()
        except Exception:
            return web.Response(text='bad')
        asyncio.create_task(self.handle(upd))
        return web.Response(text='ok')

    # ---------- рассылки по расписанию ----------
    def cond_ok(self, u, only):
        if only == 'not_vip': return not u['vip']
        if only == 'vip': return bool(u['vip'])
        if only == 'no_survey': return not u['survey']
        if only == 'no_contact': return not u['phone']
        if only == 'no_email': return bool(u['phone']) and not u['email']
        return True

    def clean_btns(self, btns):
        return [[b for b in row if b[0] != 'app'] for row in (btns or [])]

    async def scheduler(self):
        while True:
            try:
                now = datetime.now(T.MSK)
                nowts = int(time.time())
                r = self.q("SELECT v FROM settings WHERE k='paused'").fetchone()
                pv = r[0] if r else ''
                is_paused = pv == '1' or (pv != '0' and os.environ.get('BOT_PAUSED') == '1')
                if now < T.EVENT_END and not is_paused:
                    for step in T.CHAIN:
                        if step['key'] == 'ref_nudge':
                            continue  # игра с друзьями пока только в Telegram
                        rows = self.q('SELECT * FROM max_users WHERE blocked=0 AND created<=? AND created>=?',
                                      nowts - step['after'] * 60, nowts - step['after'] * 60 - 6 * 3600).fetchall()
                        for u in rows:
                            if self.cond_ok(u, step.get('only')) and self.mark(u['id'], step['key']):
                                btns = [[('contact', '📱 Поделиться номером')]] if step['key'] == 'no_contact' else self.clean_btns(step.get('btns'))
                                await self.send(u['id'], step['text'], btns, step.get('photo')); await asyncio.sleep(0.6)
                for msg in ([] if is_paused else T.SCHEDULE):
                    at = msg['at']
                    if at <= now < at + timedelta(hours=2):
                        for u in self.q('SELECT * FROM max_users WHERE blocked=0 AND created<=?', int(at.timestamp())).fetchall():
                            if self.cond_ok(u, msg.get('only')) and self.mark(u['id'], msg['key']):
                                await self.send(u['id'], msg['text'], self.clean_btns(msg.get('btns')), msg.get('photo')); await asyncio.sleep(0.6)
            except Exception:
                log.exception('max scheduler')
            await asyncio.sleep(30)

    def seg_count(self, where):
        return self.q(f'SELECT COUNT(*) FROM max_users WHERE blocked=0 AND {where}').fetchone()[0]

    async def broadcast(self, text, where='1=1'):
        ok = 0
        for r in self.q(f'SELECT id FROM max_users WHERE blocked=0 AND {where}').fetchall():
            try:
                await self.call('POST', '/messages', {'user_id': r['id']}, {'text': text[:4000], 'format': 'html'})
                ok += 1
            except Exception as e:
                log.info('max bc %s: %s', r['id'], e)
            await asyncio.sleep(0.6)
        return ok

    def count(self):
        c = lambda sql: self.q(sql).fetchone()[0]
        return (c('SELECT COUNT(*) FROM max_users'), c('SELECT COUNT(*) FROM max_users WHERE phone IS NOT NULL'),
                c('SELECT COUNT(*) FROM max_users WHERE email IS NOT NULL'))

    # ---------- запуск ----------
    async def setup(self, app):
        app.router.add_post(self.hook_path, self.webhook)

    async def run(self):
        me = await self.call('GET', '/me')
        log.info('MAX bot started as %s (%s)', me.get('name'), me.get('user_id'))
        try:
            subs = (await self.call('GET', '/subscriptions')).get('subscriptions') or []
            for s in subs:
                if s.get('url', '').startswith(self.public_url + '/max/'):
                    await self.call('DELETE', '/subscriptions', {'url': s['url']})
            await self.call('POST', '/subscriptions', None, {'url': self.public_url + self.hook_path, 'update_types': TYPES})
            log.info('MAX webhook set')
        except Exception:
            log.exception('MAX webhook')
        asyncio.create_task(self.scheduler())
