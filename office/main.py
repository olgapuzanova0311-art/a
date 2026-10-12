"""
ИИ-офис Ольги Пузановой: агенты живут в пиксельном офисе, получают задачи,
переписываются между собой и отвечают через OpenRouter.

Переменные окружения:
  OPENROUTER_API_KEY  ключ OpenRouter (без него агенты отвечают заглушкой)
  OFFICE_PASSWORD     пароль входа в офис
  MODEL               модель по умолчанию, например anthropic/claude-sonnet-4.5
  DB_PATH             путь к базе SQLite (по умолчанию /data/office.db)
  PORT                порт веб-сервера
"""
import asyncio, hashlib, hmac, json, logging, os, re, sqlite3, time
from pathlib import Path

import aiohttp
import anthropic
from aiohttp import web

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('office')

API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
PASSWORD = os.environ.get('OFFICE_PASSWORD', '')
MODEL = os.environ.get('MODEL', 'anthropic/claude-sonnet-4.5')
DB_PATH = os.environ.get('DB_PATH', '/data/office.db')
PORT = int(os.environ.get('PORT', '8080'))
CLAUDE_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
CLAUDE_MODEL = os.environ.get('CLAUDE_MODEL', 'claude-opus-5-5')
CLAUDE_EFFORT = os.environ.get('CLAUDE_EFFORT', 'medium')
claude = anthropic.AsyncAnthropic(api_key=CLAUDE_KEY, timeout=300.0) if CLAUDE_KEY else None
HERE = Path(__file__).parent
COOKIE = 'office_s'
TOKEN = hmac.new(b'ii-office', PASSWORD.encode(), hashlib.sha256).hexdigest()

Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.row_factory = sqlite3.Row
db.executescript('''
CREATE TABLE IF NOT EXISTS agents(id INTEGER PRIMARY KEY, name TEXT, role TEXT, color TEXT, prompt TEXT,
  model TEXT DEFAULT '', is_main INTEGER DEFAULT 0, status TEXT DEFAULT 'idle', created REAL);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, agent_id INTEGER, role TEXT, author TEXT, text TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY, agent_id INTEGER, title TEXT, status TEXT, result TEXT,
  from_agent INTEGER, created REAL, updated REAL);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, type TEXT, a INTEGER, b INTEGER, text TEXT, ts REAL);
''')
db.commit()


def q(sql, *a):
    cur = db.execute(sql, a)
    db.commit()
    return cur


def row(r):
    return dict(r) if r else None


# ---------------- шаблоны агентов ----------------
TEMPLATES = [
    dict(name='Администратор', role='Отвечает клиентам и записывает на услуги', color='#1009F6',
         prompt='Ты администратор [бизнес]. Материалы: прайс, график, адрес, частые вопросы. Отвечай коротко и тепло, записывай только на свободное время, недовольных клиентов передавай человеку. Результат: ответ клиенту и карточка записи: имя, телефон, услуга, дата.'),
    dict(name='Аналитик продаж', role='Сводка по продажам с выводами', color='#2BB673',
         prompt='Ты аналитик продаж. Тебе дают выгрузку продаж за день и за прошлую неделю. Сравнивай с прошлой неделей, ищи причины, пиши цифрами. Результат: главные цифры, 3 вывода, 1 действие на день.'),
    dict(name='Агент по отзывам', role='Разбирает отзывы и готовит ответы', color='#FF7A45',
         prompt='Ты менеджер по отзывам бренда. Благодари конкретно, на вопросы отвечай по фактам, жалобы не обрабатывай сам. Результат: ответы на отзывы и список жалоб для владельца.'),
    dict(name='Рекрутер', role='Отбирает кандидатов из откликов', color='#8E5CF7',
         prompt='Ты рекрутер. Тебе дают описание вакансии, критерии и отклики. Оценивай строго по критериям, не додумывай опыт. Результат: оценка 1–10 по каждому кандидату, топ-3, вопросы для собеседования.'),
    dict(name='Контент-стратег', role='Темы и контент-план на месяц', color='#FFBA09',
         prompt='Ты контент-стратег. Бери темы из реальных вопросов клиентов, используй 4 рубрики, держи баланс пользы и продаж. Результат: контент-план на месяц таблицей.'),
    dict(name='Сценарист роликов', role='Сценарии рилс в голосе автора', color='#E8467C',
         prompt='Ты сценарист коротких роликов. Начало цепляет за 3 секунды, один ролик = одна мысль, призыв в конце. Результат: сценарий по секундам, текст обложки, описание.'),
    dict(name='Редактор', role='Проверяет тексты перед публикацией', color='#14A3C7',
         prompt='Ты редактор. Убирай воду и канцелярит, проверяй, что есть польза и призыв. Правь, сохраняя голос автора. Без длинных тире. Результат: исправленный текст и список правок.'),
    dict(name='Помощник по почте', role='Разбирает входящие и пишет черновики', color='#6B7280',
         prompt='Ты личный помощник по почте. Срочное поднимай наверх, решения по деньгам и срокам оставляй владельцу. Результат: список «что ответить» и готовые черновики.'),
    dict(name='Составитель КП', role='Коммерческие предложения по шаблону', color='#0B06B8',
         prompt='Ты менеджер по продажам. Пиши проблему клиента его словами, результат в цифрах, КП на одну страницу. Результат: готовое КП и сопроводительное письмо.'),
    dict(name='Планировщик', role='План на завтра и что отдать агентам', color='#3DBE8B',
         prompt='Ты личный ассистент. Не больше 3 главных задач в день, остальное по возможности. Результат: план на завтра и что можно отдать агентам.'),
]

VOICE = ('Пиши по-русски, коротко и по делу, на «ты». Без длинных тире, без противопоставлений «не X, а Y», без воды и канцелярита. '
         'Если данных не хватает, задай 1–2 уточняющих вопроса. ')

TEAM = [
    dict(name='AI-ассистент', main=1, color='#1009F6',
         role='Разбирает сообщения и почту, сообщает только о срочном, остальное в дайджест',
         prompt='Ты личный AI-ассистент Ольги Пузановой и главный в её ИИ-офисе. Ольга присылает тебе сообщения, письма и задачи. '
                'Разбирай входящие по правилу: СРОЧНО только то, что требует решения Ольги сегодня (деньги, договорённости с ключевыми клиентами и партнёрами, сроки на сегодня-завтра, проблемы на запуске, семья). '
                'Срочное выдавай сразу: что случилось, что нужно от Ольги, готовый ответ, если уместно. '
                'Всё остальное собирай в дайджест по группам: команда, клиенты и ученики, партнёры и реклама, можно не отвечать. По каждому пункту одна строка и предложенное действие. '
                'Задачи по сфере других агентов поручай им. ' + VOICE),
    dict(name='AI-операционный директор', color='#2BB673',
         role='Следит за задачами, дедлайнами и статусами команды',
         prompt='Ты AI-операционный директор в команде Ольги Пузановой. Ведёшь реестр рабочих задач: задача, ответственный, дедлайн, статус, риск. '
                'Когда тебе присылают переписку, планёрку или список дел, вытаскивай из них задачи и обновляй реестр. '
                'Отмечай просроченное и то, что горит в ближайшие 2 дня, и предлагай, кому и что напомнить, с готовым текстом напоминания. '
                'Результат: таблица задач и блок «Что требует внимания Ольги» не длиннее 5 пунктов. ' + VOICE),
    dict(name='AI-тайм-менеджер', color='#FFBA09',
         role='Защищает 90 минут фокуса в день и не даёт перегрузить календарь',
         prompt='Ты AI-тайм-менеджер Ольги Пузановой. Главное правило: каждый рабочий день у Ольги есть 90 минут фокуса без встреч и переписок на главную задачу. '
                'Ты получаешь календарь, список задач и новые запросы на встречи. Проверяй перегруз: не больше 3 главных задач в день, буферы между встречами, нет встреч в блоке фокуса. '
                'Если день перегружен, предложи, что перенести, сократить или поручить агентам, с готовыми текстами переноса встреч. '
                'Результат: план дня по времени с блоком фокуса и список «что убрать». ' + VOICE),
    dict(name='AI-трендхантер', color='#E8467C',
         role='Анализирует конкурентов и вирусные темы, предлагает идеи для блога',
         prompt='Ты AI-трендхантер блога Ольги Пузановой: нейросети, ИИ-агенты, маркетплейсы, ИИ-профессии и бизнес. Аудитория: собственники бизнеса, селлеры, специалисты в найме и те, кто осваивает ИИ с нуля, 30–49 лет. '
                'Тебе присылают ссылки, тексты и описания постов конкурентов и трендов. Своего доступа в интернет у тебя нет, поэтому работай с присланным и с тем, что знаешь сам, и честно помечай, что нужно проверить. '
                'Разбирай, почему контент залетел: хук, боль, формат, эмоция. '
                'Результат: 5 идей для блога Ольги, по каждой: тема, почему сработает, хук для первых 3 секунд, формат (рилс, пост, карусель), как связать с её продуктом. ' + VOICE),
    dict(name='AI-контент-продюсер', color='#FF7A45',
         role='Превращает идеи в сценарии роликов и посты',
         prompt='Ты AI-контент-продюсер Ольги Пузановой. Превращаешь её идеи, голосовые и заметки в готовый контент её голосом: коротко, с цифрами, бытовые метафоры, лёгкая самоирония. '
                'Приёмы: «Привет, это Оля», «Скажи честно:», «Представь:», «Смотри, что…», «Даже если ты никогда…», стрелки →, 👇 перед призывом. '
                'Рилс: хук на 3 секунды, одна мысль, сценарий по секундам с текстом на экране, призыв в конце, текст обложки и описание. '
                'Пост: хук, история или ситуация, польза по пунктам, призыв. Без капслока и давления, без обещаний гарантированного дохода. ' + VOICE),
]

q('CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT)')
if not q("SELECT v FROM settings WHERE k='team_v2'").fetchone():
    # стартовая команда: заменяем демо-агентов на команду Ольги
    q('DELETE FROM agents'); q('DELETE FROM messages'); q('DELETE FROM tasks'); q('DELETE FROM events')
    now = time.time()
    for t in TEAM:
        q('INSERT INTO agents(name, role, color, prompt, is_main, created) VALUES(?,?,?,?,?,?)',
          t['name'], t['role'], t['color'], t['prompt'], t.get('main', 0), now)
    q("INSERT INTO settings(k, v) VALUES('team_v2', '1')")
q("UPDATE agents SET status='idle'")
q("UPDATE tasks SET status='error', result='Офис перезапускался, задачу нужно поставить заново' WHERE status IN ('queued','working')")


def event(type_, a=None, b=None, text=''):
    q('INSERT INTO events(type, a, b, text, ts) VALUES(?,?,?,?,?)', type_, a, b, text[:200], time.time())


def add_msg(agent_id, role, author, text):
    q('INSERT INTO messages(agent_id, role, author, text, ts) VALUES(?,?,?,?,?)', agent_id, role, author, text, time.time())


def set_status(agent_id, status):
    q('UPDATE agents SET status=? WHERE id=?', status, agent_id)
    event('status', agent_id, None, status)


# ---------------- нейросеть ----------------
SEM = asyncio.Semaphore(3)


async def llm(messages, model=None):
    if CLAUDE_KEY:
        return await llm_claude(messages, model)
    if not API_KEY:
        await asyncio.sleep(1.5)
        return ('🔌 Мозги ещё не подключены. Добавь ключ ANTHROPIC_API_KEY или OPENROUTER_API_KEY в настройках Railway, '
                'и я начну отвечать по-настоящему.')
    async with SEM:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post('https://openrouter.ai/api/v1/chat/completions',
                                  headers={'Authorization': f'Bearer {API_KEY}', 'HTTP-Referer': 'https://olgapuzanovva.ru',
                                           'X-Title': 'II Office'},
                                  json={'model': model or MODEL, 'messages': messages, 'max_tokens': 2000},
                                  timeout=aiohttp.ClientTimeout(total=180)) as r:
                    data = await r.json(content_type=None)
            if 'choices' not in data:
                log.warning('openrouter error: %s', data)
                return '⚠️ Нейросеть не ответила: ' + str(data.get('error', {}).get('message', data))[:300]
            return (data['choices'][0]['message'].get('content') or '').strip() or '…'
        except Exception as e:
            log.exception('llm')
            return f'⚠️ Не получилось связаться с нейросетью: {e}'


async def llm_claude(messages, model=None):
    """Claude напрямую через Anthropic API. При отказе модели сервер сам повторяет запрос на запасной модели."""
    system = '\n\n'.join(m['content'] for m in messages if m['role'] == 'system')
    convo = [m for m in messages if m['role'] != 'system'] or [{'role': 'user', 'content': 'Начни.'}]
    use_model = model if (model or '').startswith('claude-') else CLAUDE_MODEL
    async with SEM:
        try:
            resp = await claude.beta.messages.create(
                model=use_model, max_tokens=16000, system=system, messages=convo,
                output_config={'effort': CLAUDE_EFFORT},
                betas=['server-side-fallback-2026-07-01'], fallbacks='default',
            )
        except anthropic.RateLimitError:
            return '⚠️ Слишком много запросов к Claude. Повтори через минуту.'
        except anthropic.APIStatusError as e:
            log.warning('claude %s: %s', e.status_code, e)
            return f'⚠️ Claude не ответил (ошибка {e.status_code}). Проверь ключ и баланс в консоли Anthropic.'
        except anthropic.APIConnectionError as e:
            return f'⚠️ Не получилось связаться с Claude: {e}'
    if resp.stop_reason == 'refusal':
        return '⚠️ Claude отказался выполнять эту задачу. Переформулируй запрос.'
    text = '\n'.join(b.text for b in resp.content if b.type == 'text').strip()
    return text or '…'


def team_context(main):
    others = q('SELECT id, name, role FROM agents WHERE id != ? ORDER BY id', main['id']).fetchall()
    lines = '\n'.join(f'- {a["name"]}: {a["role"]}' for a in others) or '- (пока никого)'
    return (f'\n\nТвоя команда:\n{lines}\n\n'
            'Чтобы поручить задачу агенту, напиши отдельной строкой: @Имя агента: что сделать (с нужными данными). '
            'Можно поручить нескольким агентам. Когда они закончат, их отчёты придут тебе. '
            'Если задача простая, ответь сам без поручений.')


def history(agent_id, limit=16):
    rows = q('SELECT role, author, text FROM messages WHERE agent_id=? ORDER BY id DESC LIMIT ?', agent_id, limit).fetchall()[::-1]
    out = []
    for r in rows:
        if r['role'] == 'user':
            out.append({'role': 'user', 'content': r['text']})
        elif r['role'] == 'agent':
            out.append({'role': 'assistant', 'content': r['text']})
        else:
            out.append({'role': 'user', 'content': f'[{r["author"]}] {r["text"]}'})
    return out


DELEGATE_RE = re.compile(r'^\s*@([^:\n]{2,60}):\s*(.+)$', re.M)


async def agent_reply(agent_id):
    a = row(q('SELECT * FROM agents WHERE id=?', agent_id).fetchone())
    if not a:
        return
    set_status(agent_id, 'working')
    system = a['prompt'] + (team_context(a) if a['is_main'] else '')
    text = await llm([{'role': 'system', 'content': system}] + history(agent_id), a['model'])
    add_msg(agent_id, 'agent', a['name'], text)
    set_status(agent_id, 'idle')
    if a['is_main']:
        await delegate(a, text)


async def delegate(main, text):
    agents = {r['name'].lower(): row(r) for r in q('SELECT * FROM agents WHERE id != ?', main['id']).fetchall()}
    jobs = []
    for name, task in DELEGATE_RE.findall(text):
        target = agents.get(name.strip().lower())
        if not target:
            continue
        tid = q('INSERT INTO tasks(agent_id, title, status, from_agent, created, updated) VALUES(?,?,?,?,?,?)',
                target['id'], task.strip(), 'queued', main['id'], time.time(), time.time()).lastrowid
        event('talk', main['id'], target['id'], task.strip())
        jobs.append(run_task(tid))
    for j in jobs:
        asyncio.create_task(j)


async def run_task(task_id):
    t = row(q('SELECT * FROM tasks WHERE id=?', task_id).fetchone())
    a = row(q('SELECT * FROM agents WHERE id=?', t['agent_id']).fetchone()) if t else None
    if not a:
        return
    await asyncio.sleep(2.5)  # даём роботу дойти до стола
    q("UPDATE tasks SET status='working', updated=? WHERE id=?", time.time(), task_id)
    set_status(a['id'], 'working')
    add_msg(a['id'], 'system', 'Задача', t['title'])
    result = await llm([{'role': 'system', 'content': a['prompt']}, {'role': 'user', 'content': t['title']}], a['model'])
    q("UPDATE tasks SET status=?, result=?, updated=? WHERE id=?", 'error' if result.startswith('⚠️') else 'done', result, time.time(), task_id)
    add_msg(a['id'], 'agent', a['name'], result)
    set_status(a['id'], 'idle')
    if t['from_agent']:
        event('talk', a['id'], t['from_agent'], 'готово')
        add_msg(t['from_agent'], 'system', a['name'], f'Отчёт по задаче «{t["title"][:80]}»:\n\n{result}')


# ---------------- веб ----------------
def authed(req):
    return not PASSWORD or req.cookies.get(COOKIE) == TOKEN


@web.middleware
async def auth_mw(req, handler):
    if req.path.startswith('/api/') and req.path != '/api/login' and not authed(req):
        return web.json_response({'error': 'auth'}, status=401)
    return await handler(req)


async def index(req):
    return web.FileResponse(HERE / 'index.html', headers={'Cache-Control': 'no-cache'})


async def health(req):
    return web.Response(text='ok')


async def login(req):
    d = await req.json()
    if PASSWORD and not hmac.compare_digest(str(d.get('password', '')), PASSWORD):
        await asyncio.sleep(1)
        return web.json_response({'ok': False}, status=403)
    r = web.json_response({'ok': True})
    r.set_cookie(COOKIE, TOKEN, max_age=60 * 60 * 24 * 90, httponly=True, samesite='Lax', secure=req.secure)
    return r


async def state(req):
    since = int(req.query.get('since', 0) or 0)
    agents = [dict(r) for r in q('SELECT id, name, role, color, prompt, model, is_main, status FROM agents ORDER BY is_main DESC, id').fetchall()]
    tasks = [dict(r) for r in q('SELECT * FROM tasks ORDER BY id DESC LIMIT 40').fetchall()]
    events = [dict(r) for r in q('SELECT * FROM events WHERE id > ? ORDER BY id LIMIT 200', since).fetchall()]
    last = q('SELECT COALESCE(MAX(id),0) FROM events').fetchone()[0]
    return web.json_response({'agents': agents, 'tasks': tasks, 'events': events if since else [], 'last': last,
                              'brain': bool(CLAUDE_KEY or API_KEY), 'model': CLAUDE_MODEL if CLAUDE_KEY else MODEL})


async def messages(req):
    aid = int(req.query['agent_id'])
    rows = q('SELECT * FROM messages WHERE agent_id=? ORDER BY id DESC LIMIT 80', aid).fetchall()[::-1]
    return web.json_response([dict(r) for r in rows])


async def chat(req):
    d = await req.json()
    aid, text = int(d['agent_id']), str(d.get('text', '')).strip()
    if not text:
        return web.json_response({'ok': False})
    add_msg(aid, 'user', 'Оля', text[:8000])
    asyncio.create_task(agent_reply(aid))
    return web.json_response({'ok': True})


async def new_task(req):
    d = await req.json()
    aid, title = int(d['agent_id']), str(d.get('title', '')).strip()
    if not title:
        return web.json_response({'ok': False})
    tid = q('INSERT INTO tasks(agent_id, title, status, created, updated) VALUES(?,?,?,?,?)', aid, title[:8000], 'queued', time.time(), time.time()).lastrowid
    asyncio.create_task(run_task(tid))
    return web.json_response({'ok': True, 'id': tid})


async def save_agent(req):
    d = await req.json()
    name = str(d.get('name', '')).strip()[:40]
    if not name:
        return web.json_response({'ok': False, 'error': 'Нужно имя'}, status=400)
    vals = (name, str(d.get('role', ''))[:120], str(d.get('color', '#1009F6'))[:9], str(d.get('prompt', ''))[:8000], str(d.get('model', ''))[:80])
    if d.get('id'):
        q('UPDATE agents SET name=?, role=?, color=?, prompt=?, model=? WHERE id=?', *vals, int(d['id']))
        aid = int(d['id'])
    else:
        aid = q('INSERT INTO agents(name, role, color, prompt, model, created) VALUES(?,?,?,?,?,?)', *vals, time.time()).lastrowid
        event('hire', aid, None, name)
    return web.json_response({'ok': True, 'id': aid})


async def delete_agent(req):
    aid = int(req.match_info['id'])
    a = q('SELECT is_main FROM agents WHERE id=?', aid).fetchone()
    if not a or a['is_main']:
        return web.json_response({'ok': False}, status=400)
    q('DELETE FROM agents WHERE id=?', aid)
    q('DELETE FROM messages WHERE agent_id=?', aid)
    event('fire', aid)
    return web.json_response({'ok': True})


async def templates(req):
    return web.json_response(TEMPLATES)


def make_app():
    app = web.Application(middlewares=[auth_mw], client_max_size=2 * 1024 * 1024)
    app.add_routes([
        web.get('/', index), web.get('/health', health),
        web.post('/api/login', login), web.get('/api/state', state), web.get('/api/messages', messages),
        web.post('/api/chat', chat), web.post('/api/tasks', new_task), web.post('/api/agents', save_agent),
        web.delete('/api/agents/{id}', delete_agent), web.get('/api/templates', templates),
    ])
    return app


if __name__ == '__main__':
    log.info('office on :%s, claude=%s, openrouter=%s', PORT, bool(CLAUDE_KEY), bool(API_KEY))
    web.run_app(make_app(), port=PORT)
