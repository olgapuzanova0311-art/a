"""
Claude Code в Telegram для Ольги Пузановой.

Принимает текст, голосовые, кружки, фото и файлы. Голос расшифровывает на сервере (faster-whisper),
задачу отдаёт Claude Code в рабочей папке проекта. Claude Code раздаёт задачи ИИ-офису через agent/office.py.

Переменные окружения:
  TG_TOKEN           токен Telegram-бота
  ANTHROPIC_API_KEY  ключ Claude (или CLAUDE_CODE_OAUTH_TOKEN для подписки)
  TG_OWNERS          id чатов, которым бот отвечает (через запятую)
  OFFICE_URL, OFFICE_PASSWORD  доступ к ИИ-офису
  MODEL              модель Claude Code (по умолчанию claude-opus-5-5)
  WHISPER_MODEL      модель расшифровки (по умолчанию small)
"""
import asyncio, json, logging, os, re, shutil, subprocess, time
from pathlib import Path

import aiohttp

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('agent')

TOKEN = os.environ.get('TG_TOKEN', '')
OWNERS = {int(x) for x in re.findall(r'-?\d+', os.environ.get('TG_OWNERS', '749890854'))}
PASSWORD = os.environ.get('OFFICE_PASSWORD', '')
MODEL = os.environ.get('MODEL', 'claude-opus-5-5')
WHISPER = os.environ.get('WHISPER_MODEL', 'small')
DATA = Path(os.environ.get('DATA', '/data'))
REPO = Path(__file__).resolve().parent.parent
WS = DATA / 'ws'
STATE = DATA / 'state.json'
API = f'https://api.telegram.org/bot{TOKEN}/'
FILE_API = f'https://api.telegram.org/file/bot{TOKEN}/'
PORT = int(os.environ.get('PORT', '8080'))

SYSTEM = """Ты Claude Code, рабочая копия Claude Ольги Пузановой. Ольга пишет тебе из Telegram, часто голосом: текст расшифрован автоматически и может содержать ошибки, понимай по смыслу.
Ты одновременно главный в её ИИ-офисе: команда агентов на Claude, которые берут задачи и пишут отчёты.

Как работаешь:
1. В начале каждого нового разговора прочитай agent/MEMORY.md: там проекты, сервисы, ссылки, договорённости и голос Ольги. Новые важные факты и решения дописывай туда сам.
2. Простое делай сам: тексты, разбор, расчёты, работа с файлами проекта.
3. Большое раскладывай и поручай агентам офиса:
   python agent/office.py team                       посмотреть команду
   python agent/office.py task "Имя агента" "задача"  поручить (агенты не видят вашу переписку, клади в задачу весь контекст и формат результата)
   python agent/office.py wait <id> <id>              дождаться отчётов
   python agent/office.py hire "Имя" "роль" "инструкция"  нанять агента, если роли не хватает
   Поручай нескольким агентам сразу, потом жди всех. Проверь отчёты, доработай слабое и сведи в один итог.
4. Файлы, которые прислала Ольга, лежат в inbox/. Готовые файлы для Ольги (видео, картинки, документы) клади в outbox/: бот сам отправит их ей после твоего ответа. Для монтажа роликов используй навык reel-montage (фирменный стиль Ольги), для простых задач с видео навык montage.
5. Отвечай для Telegram: коротко, по делу, без markdown-таблиц и заголовков, списки через «•» или цифры. В конце итога: что нужно от Ольги, если нужно.
Доступы сервера (проверь `env`, какие ключи заданы):
• GH_TOKEN: GitHub ко всем репозиториям Ольги через gh и git. Основной проект: olgapuzanova0311-art/a, рабочая ветка claude/busy-noether-jpca9m. Изменения сайта и ботов делай в клоне: `gh repo clone olgapuzanova0311-art/a ~/repo -- -b claude/busy-noether-jpca9m` (или `git -C ~/repo pull`), правь, коммить, `git push`. Railway сам выкладывает сайт, ботов и офис после пуша в эту ветку. Папка ws/ это копия для чтения, в git её не пушь.
• RAILWAY_API_TOKEN: Railway CLI (`railway`), проект ii-komanda-bot: сервисы bot, site, office, agent.
Если нужного ключа нет, подготовь всё и скажи Ольге, какой доступ нужен.
Перед пушем проверяй изменения (синтаксис, что ничего не сломано), не удаляй сервисы и данные без прямой просьбы Ольги, не публикуй ключи и токены в коде."""


# ---------------- состояние ----------------
def load():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def save(st):
    STATE.write_text(json.dumps(st, ensure_ascii=False))


state = load()
http: aiohttp.ClientSession = None
busy: dict[int, asyncio.subprocess.Process] = {}
locks: dict[int, asyncio.Lock] = {}


def owners():
    return OWNERS | set(state.get('owners', []))


# ---------------- telegram ----------------
async def tg(method, **data):
    try:
        async with http.post(API + method, json=data, timeout=aiohttp.ClientTimeout(total=70)) as r:
            return await r.json(content_type=None)
    except Exception as e:
        log.warning('tg %s: %s', method, e)
        return {}


def plain(text):
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.M)
    text = re.sub(r'`{3}\w*\n?', '', text)
    return text.strip()


async def say(cid, text):
    text = plain(text) or '…'
    last = None
    for i in range(0, len(text), 4000):
        last = await tg('sendMessage', chat_id=cid, text=text[i:i + 4000], disable_web_page_preview=True)
    return last


async def download(file_id, dest: Path):
    info = await tg('getFile', file_id=file_id)
    path = (info.get('result') or {}).get('file_path')
    if not path:
        raise RuntimeError('Telegram отдаёт ботам файлы только до 20 МБ. Большое видео пришли ссылкой на Яндекс Диск или Google Drive')
    dest.parent.mkdir(parents=True, exist_ok=True)
    async with http.get(FILE_API + path, timeout=aiohttp.ClientTimeout(total=300)) as r:
        dest.write_bytes(await r.read())
    return dest


# ---------------- расшифровка ----------------
_whisper = None


def warm_whisper():
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        _whisper = WhisperModel(WHISPER, device='cpu', compute_type='int8', download_root=str(DATA / 'models'))


def transcribe_sync(path):
    warm_whisper()
    segs, _ = _whisper.transcribe(str(path), language='ru', vad_filter=True, beam_size=1)
    return ' '.join(s.text.strip() for s in segs).strip()


async def transcribe(path):
    return await asyncio.to_thread(transcribe_sync, path)


# ---------------- Claude Code ----------------
TOOL_RU = {'Read': '📖 читаю', 'Write': '✍️ пишу файл', 'Edit': '✏️ правлю', 'Bash': '⚙️ выполняю', 'Grep': '🔎 ищу',
           'Glob': '🔎 ищу файлы', 'WebSearch': '🌐 ищу в интернете', 'WebFetch': '🌐 читаю страницу', 'Task': '🤖 подключаю помощника',
           'Agent': '🤖 подключаю помощника', 'TodoWrite': '🗒 составляю план'}


def tool_line(name, inp):
    if name == 'Bash':
        cmd = inp.get('command', '')
        m = re.search(r'office\.py (task|wait|team|hire|tasks)\s*"?([^"]*)', cmd)
        if m:
            return {'task': f'🏢 поручаю: {m.group(2)}', 'wait': '🏢 жду отчёты офиса', 'team': '🏢 смотрю команду',
                    'hire': f'🏢 нанимаю: {m.group(2)}', 'tasks': '🏢 смотрю задачи'}[m.group(1)]
        return '⚙️ ' + (inp.get('description') or cmd)[:60]
    target = inp.get('file_path') or inp.get('pattern') or inp.get('query') or inp.get('url') or inp.get('description') or ''
    return f"{TOOL_RU.get(name, '🔧 ' + name)} {Path(target).name if '/' in str(target) else target}"[:80]


async def run_claude(cid, prompt):
    sid = state.get('sessions', {}).get(str(cid))
    args = ['claude', '-p', prompt, '--output-format', 'stream-json', '--verbose', '--model', MODEL,
            '--permission-mode', 'bypassPermissions', '--append-system-prompt', SYSTEM]
    if sid:
        args += ['--resume', sid]
    env = dict(os.environ, HOME=str(DATA / 'home'), CLAUDE_CODE_DISABLE_AUTOUPDATER='1')
    env.pop('TG_TOKEN', None)
    status = await tg('sendMessage', chat_id=cid, text='⏳ Взяла в работу')
    mid = (status.get('result') or {}).get('message_id')
    steps, last_edit, result, new_sid, failed = [], 0.0, '', None, False
    started = time.time()
    proc = await asyncio.create_subprocess_exec(*args, cwd=WS, env=env, stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.PIPE, limit=16 * 1024 * 1024)
    busy[cid] = proc
    try:
        async for raw in proc.stdout:
            try:
                ev = json.loads(raw)
            except Exception:
                continue
            if ev.get('session_id'):
                new_sid = ev['session_id']
            if ev.get('type') == 'assistant':
                for b in ev.get('message', {}).get('content', []):
                    if b.get('type') == 'tool_use':
                        steps.append(tool_line(b.get('name', ''), b.get('input') or {}))
                if mid and steps and time.time() - last_edit > 4:
                    last_edit = time.time()
                    await tg('editMessageText', chat_id=cid, message_id=mid,
                             text='⏳ Работаю\n\n' + '\n'.join(steps[-8:]))
            elif ev.get('type') == 'result':
                result = ev.get('result') or ''
                failed = ev.get('is_error', False)
        await proc.wait()
    finally:
        busy.pop(cid, None)
    if proc.returncode and not result:
        err = (await proc.stderr.read()).decode(errors='ignore')[-500:]
        if sid and 'session' in err.lower():
            state.setdefault('sessions', {}).pop(str(cid), None); save(state)
            return await run_claude(cid, prompt)
        result, failed = f'⚠️ Не получилось: {err or "процесс остановлен"}', True
    if new_sid:
        state.setdefault('sessions', {})[str(cid)] = new_sid; save(state)
    if mid:
        await tg('editMessageText', chat_id=cid, message_id=mid,
                 text=('⚠️ Остановилась' if failed else '✅ Готово') + (f' · шагов: {len(steps)}' if steps else ''))
    await say(cid, result)
    await send_outbox(cid, started)


async def send_file(cid, path: Path):
    kind = {'.mp4': ('sendVideo', 'video'), '.mov': ('sendVideo', 'video'), '.jpg': ('sendPhoto', 'photo'),
            '.jpeg': ('sendPhoto', 'photo'), '.png': ('sendPhoto', 'photo'), '.mp3': ('sendAudio', 'audio')}
    method, field = kind.get(path.suffix.lower(), ('sendDocument', 'document'))
    if path.stat().st_size > 49 * 1024 * 1024:
        return await say(cid, f'⚠️ {path.name} больше 50 МБ, Telegram не пропустит. Попроси сжать или порезать.')
    form = aiohttp.FormData()
    form.add_field('chat_id', str(cid))
    if method == 'sendVideo':
        form.add_field('supports_streaming', 'true')
    with open(path, 'rb') as f:
        form.add_field(field, f, filename=path.name)
        try:
            async with http.post(API + method, data=form, timeout=aiohttp.ClientTimeout(total=600)) as r:
                res = await r.json(content_type=None)
            if not res.get('ok') and method != 'sendDocument':
                f.seek(0)
                form2 = aiohttp.FormData(); form2.add_field('chat_id', str(cid)); form2.add_field('document', f, filename=path.name)
                async with http.post(API + 'sendDocument', data=form2, timeout=aiohttp.ClientTimeout(total=600)) as r:
                    res = await r.json(content_type=None)
            if not res.get('ok'):
                await say(cid, f'⚠️ Не получилось отправить {path.name}: {res.get("description", "")}')
        except Exception as e:
            await say(cid, f'⚠️ Не получилось отправить {path.name}: {e}')


async def send_outbox(cid, since):
    out = WS / 'outbox'
    if not out.exists():
        return
    for p in sorted(out.iterdir(), key=lambda x: x.stat().st_mtime):
        if p.is_file() and p.stat().st_mtime >= since - 1:
            await tg('sendChatAction', chat_id=cid, action='upload_document')
            await send_file(cid, p)


async def work(cid, prompt):
    lock = locks.setdefault(cid, asyncio.Lock())
    if lock.locked():
        await tg('sendMessage', chat_id=cid, text='Записала, возьму сразу после текущей задачи. Остановить текущую: /stop')
    async with lock:
        await run_claude(cid, prompt)


# ---------------- сообщения ----------------
HELLO = ('Привет, это твой Claude Code в Telegram 🧭\n\n'
         'Пиши или надиктовывай голосом. Можно присылать фото, файлы и пересылать переписки. '
         'Простое сделаю сама, большое раздам команде ИИ-офиса и пришлю итог.\n\n'
         '/new начать новый разговор\n/stop остановить текущую задачу\n/office ссылка на офис')


async def handle(msg):
    cid = msg['chat']['id']
    text = (msg.get('text') or msg.get('caption') or '').strip()
    if cid not in owners():
        if PASSWORD and text.startswith('/start') and text.split()[-1] == PASSWORD:
            state['owners'] = sorted(set(state.get('owners', [])) | {cid}); save(state)
            return await say(cid, HELLO)
        return await say(cid, 'Это личный бот. Если ты из команды Ольги, отправь: /start пароль_офиса')
    if text.startswith('/'):
        cmd = text.split()[0].split('@')[0].lower()
        if cmd == '/new':
            state.setdefault('sessions', {}).pop(str(cid), None); save(state)
            return await say(cid, 'Начинаем новый разговор. Память из agent/MEMORY.md остаётся.')
        if cmd == '/stop':
            p = busy.get(cid)
            if p:
                p.terminate()
                return await say(cid, 'Остановила.')
            return await say(cid, 'Сейчас ничего не выполняется.')
        if cmd == '/office':
            return await say(cid, os.environ.get('OFFICE_URL', 'https://office-production-833a.up.railway.app'))
        return await say(cid, HELLO)

    parts = []
    fwd = msg.get('forward_origin') or {}
    who = (fwd.get('sender_user') or {}).get('first_name') or fwd.get('sender_user_name') or (fwd.get('chat') or {}).get('title')
    voice = msg.get('voice') or msg.get('audio') or msg.get('video_note')
    try:
        if voice:
            await tg('sendChatAction', chat_id=cid, action='typing')
            f = await download(voice['file_id'], DATA / 'voice' / f"{voice['file_unique_id']}.ogg")
            heard = await transcribe(f)
            f.unlink(missing_ok=True)
            if not heard:
                return await say(cid, 'Не расслышала, повтори, пожалуйста 🙏')
            await say(cid, '🎙 ' + heard)
            parts.append(heard)
        if msg.get('photo'):
            ph = msg['photo'][-1]
            f = await download(ph['file_id'], WS / 'inbox' / f"photo_{ph['file_unique_id']}.jpg")
            parts.append(f'[Ольга прислала фото: inbox/{f.name}]')
        if msg.get('document'):
            d = msg['document']
            name = re.sub(r'[^\w.\-]+', '_', d.get('file_name') or d['file_unique_id'])
            f = await download(d['file_id'], WS / 'inbox' / name)
            parts.append(f'[Ольга прислала файл: inbox/{f.name}]')
    except Exception as e:
        log.exception('media')
        return await say(cid, f'⚠️ Не получилось обработать вложение: {e}')
    if text:
        parts.append(text)
    if not parts:
        return await say(cid, 'Пока понимаю текст, голосовые, кружки, фото и файлы.')
    prompt = '\n'.join(parts)
    if who:
        prompt = f'[Пересланное сообщение от {who}]\n{prompt}'
    asyncio.create_task(work(cid, prompt))


async def poll():
    await tg('deleteWebhook')
    await tg('setMyCommands', commands=[{'command': 'new', 'description': 'Новый разговор'},
                                        {'command': 'stop', 'description': 'Остановить задачу'},
                                        {'command': 'office', 'description': 'Ссылка на ИИ-офис'}])
    offset = 0
    while True:
        try:
            r = await tg('getUpdates', offset=offset, timeout=50, allowed_updates=['message'])
            for u in r.get('result', []):
                offset = u['update_id'] + 1
                if 'message' in u:
                    asyncio.create_task(handle(u['message']))
            if not r.get('ok'):
                await asyncio.sleep(5)
        except Exception:
            log.exception('poll')
            await asyncio.sleep(5)


async def health_server():
    from aiohttp import web
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text='ok'))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()


def prepare_workspace():
    # файлы проекта приезжают с каждым деплоем; правки агента в рабочей папке сохраняются, если они новее
    WS.mkdir(parents=True, exist_ok=True)
    (DATA / 'home').mkdir(parents=True, exist_ok=True)
    for src in REPO.rglob('*'):
        rel = src.relative_to(REPO)
        if src.is_dir() or rel.parts[0] == '.git' or '__pycache__' in rel.parts:
            continue
        dst = WS / rel
        if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    skills = WS / '.claude' / 'skills'
    if (REPO / 'agent' / 'skills').exists():
        shutil.copytree(REPO / 'agent' / 'skills', skills, dirs_exist_ok=True)
    if (REPO / 'agent' / 'agents').exists():
        shutil.copytree(REPO / 'agent' / 'agents', WS / '.claude' / 'agents', dirs_exist_ok=True)
    for d in ('inbox', 'outbox', 'work'):
        (WS / d).mkdir(exist_ok=True)
    if os.environ.get('GH_TOKEN'):
        subprocess.run(['gh', 'auth', 'setup-git'], check=False)
        subprocess.run(['git', 'config', '--global', 'user.name', 'Claude (Telegram)'], check=False)
        subprocess.run(['git', 'config', '--global', 'user.email', 'noreply@anthropic.com'], check=False)
    if not (WS / '.git').exists():
        subprocess.run(['git', 'init', '-q'], cwd=WS, check=False)


async def main():
    global http
    prepare_workspace()
    http = aiohttp.ClientSession()
    await health_server()
    if not TOKEN:
        log.warning('TG_TOKEN не задан, жду токен')
        while True:
            await asyncio.sleep(3600)
    asyncio.create_task(asyncio.to_thread(warm_whisper))
    log.info('agent started, model=%s, claude=%s', MODEL, shutil.which('claude'))
    await poll()


if __name__ == '__main__':
    asyncio.run(main())
