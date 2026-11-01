"""Разовые рассылки с картинкой и именем. Сначала STAGE='test' (только TEST_USERNAMES), после «ок» Ольги STAGE='all'.
Каждое сообщение уходит человеку один раз (отметка в sent / max_sent), поэтому перезапуск бота ничего не дублирует.
"""
import asyncio, html, logging

from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup

log = logging.getLogger('campaign')

KEY = 'dr_wish'
TITLE = 'Твоё желание исполнено (план на 2027)'
STAGE = 'all'                       # 'test…' → только тест; 'all' → всем пользователям Telegram и MAX; 'done' → рассылка закончена
UNTIL = 1793696400                  # 03.11.2026 12:00 МСК: после начала эфира рассылка не уходит (и новым людям в боте тоже)
TEST_USERNAMES = ('olgapuzanovva', 'olgapuzanovvva')
PHOTO = None                        # без картинки
PHOTO_URL = None

TEXT = (
    'Твоё желание исполнено ☑️ …ну почти 😉\n\n'
    '{hello} спрашивала, что бы вы хотели на свой день рождения: время для себя, рост дохода или просто выспаться. '
    'И поняла, что могу немного помочь 😄\n\n'
    '3 ноября в 12:00, в мой день рождения, покажу на эфире, как сама вернула себе и время, и сон с помощью ИИ. '
    'А ещё расскажу 23 вывода, которые поняла к 23 годам.\n\n'
    'Подарок уже сейчас: мой шаблон плана на 2027, чтобы желание сбылось быстрее. Всё считается само 👇\n'
    'https://olgapuzanova0311-art.github.io/perezagruzka/dr/plan/\n\n'
    'До встречи на эфире 💙'
)
LINK = 'https://olgapuzanova0311-art.github.io/perezagruzka/dr/'
BUTTON = '🎟 ЗАБРАТЬ ПРИГЛАШЕНИЕ 🎟'


def text_for(first_name):
    name = (first_name or '').strip()
    return TEXT.format(hello=f'{html.escape(name)}, я тут' if name else 'Я тут')


async def run(M):
    """M: модуль main (q, mark, bot, notify_admins, MX)."""
    if STAGE not in ('all',) and not STAGE.startswith('test'):
        return  # рассылка закончена: новые люди в боте её не получают
    if UNTIL and M.time.time() > UNTIL:
        return  # событие уже прошло
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
                kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BUTTON, url=LINK)]])
                if photo:
                    m = await M.bot.send_photo(r['id'], photo, caption=text_for(r['first_name']), reply_markup=kb)
                    photo = m.photo[-1].file_id  # дальше шлём уже загруженную картинку
                else:
                    await M.bot.send_message(r['id'], text_for(r['first_name']), reply_markup=kb, disable_web_page_preview=True)
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
                if await M.MX.send(r['id'], text_for(r['first_name']).replace('{', '{{').replace('}', '}}'),
                                   [[('url', BUTTON, LINK.replace('{', '{{').replace('}', '}}'))]], photo=PHOTO_URL or None):
                    mx += 1
                await asyncio.sleep(0.6)
        what = 'Тест рассылки' if STAGE.startswith('test') else 'Рассылка'
        log.info('campaign %s %s: ok=%s fail=%s max=%s', KEY, STAGE, ok, fail, mx)
        await M.notify_admins(f'📨 {what} «{TITLE}»: доставлено в Telegram {ok}, не доставлено {fail}'
                              + (f', в MAX {mx}' if STAGE == 'all' else '') + '.')
    except Exception:
        log.exception('campaign')
